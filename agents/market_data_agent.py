"""
agents/market_data_agent.py

Market Data Agent — Phase 2.
Responsibilities:
- Resolve IBKR Contract objects dynamically via reqContractDetails() at session start.
- Request real-time bar streams for 3 instruments × 6 timeframes = 18 streams.
- Normalize each bar: convert timestamp to bar-close UTC, validate fields.
- Push normalized bars to BarBuffer (in-memory).
- Persist completed-session bars to historical_bars table.
- Detect and log bar gaps without filling them.
- Handle reconnection per ibkr.reconnect_attempts config.
"""
import asyncio
import json
from datetime import date, datetime, timedelta, timezone

import pytz

from agents.risk_manager import KillSwitch
from core.bar_buffer import BarBuffer, BufferManager
from core.database import DatabaseManager
from core.ibkr_client import IBKRClient
from core.logger import get_logger


class MarketDataError(Exception):
    pass


class MarketDataAgent:
    _TIMEFRAME_TO_BAR_SIZE = {
        1: '1 min',
        3: '3 mins',
        5: '5 mins',
        15: '15 mins',
        60: '1 hour',
        240: '4 hours',
    }

    def __init__(self, config: dict, ibkr_client: IBKRClient,
                 db: DatabaseManager, buffer_manager: BufferManager):
        self._config = config
        self._ibkr_client = ibkr_client
        self._db = db
        self._buffer_manager = buffer_manager
        self._logger = get_logger('apex.agents.market_data')

        traded = config['traded_instrument']
        context = config.get('context_instruments', [])
        self._instruments = [traded] + context
        self._timeframes = config.get('fvg_detection_timeframes', [240, 60, 15, 5, 3, 1])

        mda_cfg = config.get('market_data', {})
        self._persist = mda_cfg.get('persist_historical_bars', True)

        ibkr_cfg = config.get('ibkr', {})
        self._reconnect_attempts = ibkr_cfg.get('reconnect_attempts', 3)
        self._reconnect_delay = ibkr_cfg.get('reconnect_delay', 5)

        self._n_instruments = len(self._instruments)
        self._n_timeframes = len(self._timeframes)
        self._n_streams = self._n_instruments * self._n_timeframes

        self._contracts: dict = {}
        self._active_bars: dict = {}
        self._ib = None

        self._kill_switch = KillSwitch(config)

    async def _resolve_contracts(self) -> dict:
        from ib_insync import Contract

        resolved = {}
        today = date.today()

        for instrument in self._instruments:
            exchange = 'CBOT' if instrument == 'YM' else 'CME'
            c = Contract(symbol=instrument, secType='FUT', exchange=exchange, currency='USD')

            try:
                details_list = await self._ibkr_client._ib.reqContractDetailsAsync(c)
            except Exception as exc:
                raise MarketDataError(
                    f'Contract resolution failed for {instrument}: {exc}'
                ) from exc

            if not details_list:
                raise MarketDataError(f'No contracts found for {instrument}')

            candidates = []
            for details in details_list:
                expiry_str = details.contract.lastTradeDateOrContractMonth
                if len(expiry_str) == 6:
                    expiry_str += '01'
                try:
                    expiry_date = date(
                        int(expiry_str[:4]), int(expiry_str[4:6]), int(expiry_str[6:8])
                    )
                    if expiry_date >= today:
                        candidates.append((expiry_date, details.contract))
                except (ValueError, IndexError):
                    continue

            if not candidates:
                raise MarketDataError(f'No valid front-month contract for {instrument}')

            candidates.sort(key=lambda x: x[0])
            front_month = candidates[0][1]
            resolved[instrument] = front_month

            self._logger.info(
                'Resolved %s: %s expiry %s',
                instrument,
                front_month.localSymbol,
                front_month.lastTradeDateOrContractMonth,
            )

        return resolved

    def _normalize_bar(self, raw_bar, instrument: str, timeframe: int) -> dict:
        if raw_bar.date is None:
            raise ValueError(f'Bar date is None for {instrument} {timeframe}m')

        if isinstance(raw_bar.date, str):
            date_str = raw_bar.date.strip()
            # Handle IBKR format "20260426  10:00:00"
            if '  ' in date_str:
                date_str = date_str.replace('  ', 'T')
            try:
                dt = datetime.fromisoformat(date_str)
            except ValueError as exc:
                raise ValueError(
                    f'Cannot parse bar date {raw_bar.date!r}: {exc}'
                ) from exc
        else:
            dt = raw_bar.date

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        close_dt = dt + timedelta(minutes=timeframe)
        timestamp = close_dt.strftime('%Y-%m-%dT%H:%M:%SZ')

        return {
            'instrument': instrument,
            'timeframe': timeframe,
            'timestamp': timestamp,
            'open': float(raw_bar.open),
            'high': float(raw_bar.high),
            'low': float(raw_bar.low),
            'close': float(raw_bar.close),
            'volume': int(raw_bar.volume),
        }

    def _on_bar_update(self, bars, has_new_bar: bool, instrument: str, timeframe: int):
        if not bars:
            return

        try:
            normalized = self._normalize_bar(bars[-1], instrument, timeframe)

            if has_new_bar:
                # bars[-1] is the newly completed bar; check gap before pushing
                self._check_gap(instrument, timeframe, normalized)
                self._buffer_manager.push(instrument, timeframe, normalized)
                self._logger.debug(
                    'Bar: %s %dm %s O=%.2f H=%.2f L=%.2f C=%.2f V=%d',
                    instrument, timeframe, normalized['timestamp'],
                    normalized['open'], normalized['high'],
                    normalized['low'], normalized['close'], normalized['volume'],
                )
                if self._persist:
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(self._persist_bar(normalized))
                    except RuntimeError:
                        pass
            else:
                # Update current forming bar in place
                self._buffer_manager.get(instrument, timeframe).replace_last(normalized)

        except ValueError as exc:
            self._logger.warning(
                'Bar normalization error for %s %dm: %s', instrument, timeframe, exc
            )
        except Exception as exc:
            self._logger.error(
                'Unexpected error in bar callback %s %dm: %s', instrument, timeframe, exc
            )

    def _check_gap(self, instrument: str, timeframe: int, new_bar: dict) -> None:
        buf = self._buffer_manager.get(instrument, timeframe)
        prev = buf.latest()
        if prev is None:
            return

        prev_close = datetime.fromisoformat(prev['timestamp'].replace('Z', '+00:00'))
        expected_next = prev_close + timedelta(minutes=timeframe)
        actual_close = datetime.fromisoformat(new_bar['timestamp'].replace('Z', '+00:00'))

        if actual_close != expected_next:
            gap_minutes = int((actual_close - expected_next).total_seconds() / 60)
            self._logger.warning(
                'GAP DETECTED: %s %dm — expected %s, got %s, gap=%dm',
                instrument, timeframe,
                expected_next.strftime('%Y-%m-%dT%H:%M:%SZ'),
                actual_close.strftime('%Y-%m-%dT%H:%M:%SZ'),
                gap_minutes,
            )
            gap_info = json.dumps({
                'instrument': instrument,
                'timeframe': timeframe,
                'expected': expected_next.isoformat(),
                'actual': actual_close.isoformat(),
                'gap_minutes': gap_minutes,
            })
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._db.log_event('bar_gap', gap_info))
            except RuntimeError:
                pass  # No running event loop in test context

    async def _persist_bar(self, bar: dict) -> None:
        ny_tz = pytz.timezone('America/New_York')
        close_dt = datetime.fromisoformat(bar['timestamp'].replace('Z', '+00:00'))
        session_date = close_dt.astimezone(ny_tz).strftime('%Y-%m-%d')
        bar_with_session = dict(bar)
        bar_with_session['session_date'] = session_date
        await self._db.insert_historical_bars([bar_with_session])

    def _setup_disconnect_handler(self) -> None:
        if self._ib is None:
            return

        def on_disconnect():
            try:
                asyncio.create_task(self._reconnect())
            except RuntimeError:
                pass

        self._ib.disconnectedEvent += on_disconnect

    async def _start_subscriptions(self) -> None:
        self._ib = self._ibkr_client._ib
        self._active_bars.clear()

        for instrument, contract in self._contracts.items():
            for timeframe in self._timeframes:
                bar_size = self._TIMEFRAME_TO_BAR_SIZE[timeframe]
                bars = self._ib.reqHistoricalData(
                    contract,
                    endDateTime='',
                    durationStr='2 D',
                    barSizeSetting=bar_size,
                    whatToShow='TRADES',
                    useRTH=False,
                    keepUpToDate=True,
                )

                def make_callback(inst, tf):
                    def callback(b, h):
                        self._on_bar_update(b, h, inst, tf)
                    return callback

                bars.updateEvent += make_callback(instrument, timeframe)
                self._active_bars[(instrument, timeframe)] = bars
                self._logger.debug('Subscribed %s %dm', instrument, timeframe)

        self._setup_disconnect_handler()

    async def _reconnect(self) -> None:
        for attempt in range(1, self._reconnect_attempts + 1):
            self._logger.error(
                'IBKR disconnected — attempting reconnect %d/%d',
                attempt, self._reconnect_attempts,
            )
            await self._db.log_event('RECONNECT_ATTEMPT', json.dumps({
                'attempt': attempt,
                'max_attempts': self._reconnect_attempts,
            }))
            await asyncio.sleep(self._reconnect_delay)
            try:
                await self._ibkr_client.connect(dry_run=False)
                self._contracts = await self._resolve_contracts()
                await self._start_subscriptions()
                self._logger.info(
                    'IBKR reconnected — %d streams re-subscribed', self._n_streams
                )
                await self._db.log_event(
                    'RECONNECT_SUCCESS', f'{self._n_streams} streams re-subscribed'
                )
                return
            except Exception as exc:
                self._logger.error('Reconnect attempt %d failed: %s', attempt, exc)

        self._logger.critical('IBKR reconnect exhausted — triggering kill switch')
        self._kill_switch.trigger('IBKR reconnect exhausted')
        raise MarketDataError(
            f'IBKR reconnect exhausted after {self._reconnect_attempts} attempts'
        )

    async def start(self) -> None:
        self._logger.info(
            'MarketDataAgent starting — %d instruments, %d timeframes, %d streams',
            self._n_instruments, self._n_timeframes, self._n_streams,
        )
        await self._db.log_event('MARKET_DATA_START', json.dumps({
            'instruments': self._instruments,
            'timeframes': self._timeframes,
            'streams': self._n_streams,
        }))
        self._contracts = await self._resolve_contracts()
        await self._start_subscriptions()

    async def stop(self) -> None:
        if self._ib is not None:
            for bars_obj in self._active_bars.values():
                try:
                    self._ib.cancelHistoricalData(bars_obj)
                except Exception:
                    pass
        self._active_bars.clear()
        await self._db.log_event('MARKET_DATA_SHUTDOWN', 'MarketDataAgent stopped')
        self._logger.info('MarketDataAgent stopped')

    def get_buffer(self, instrument: str, timeframe: int) -> BarBuffer:
        return self._buffer_manager.get(instrument, timeframe)
