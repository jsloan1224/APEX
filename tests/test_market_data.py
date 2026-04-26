import logging
import os
import tempfile
import types
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.market_data_agent import MarketDataAgent
from core.bar_buffer import BufferManager
from core.database import DatabaseManager

RISK_CFG = {
    'max_daily_loss_usd': 500,
    'max_drawdown_usd': 300,
    'max_consecutive_losses': 3,
    'cool_off_minutes': 30,
    'news_window_minutes': 10,
    'max_open_positions': 1,
}


def make_agent():
    config = {
        'traded_instrument': 'ES',
        'context_instruments': ['NQ', 'YM'],
        'fvg_detection_timeframes': [240, 60, 15, 5, 3, 1],
        'market_data': {
            'bar_buffer_size': 500,
            'bar_timestamp_convention': 'close',
            'persist_historical_bars': True,
        },
        'ibkr': {
            'reconnect_attempts': 3,
            'reconnect_delay': 5,
        },
        'risk': RISK_CFG,
    }
    mock_ibkr = MagicMock()
    mock_ibkr._ib = None
    mock_db = MagicMock()
    mock_db.log_event = AsyncMock()
    mock_db.insert_historical_bars = AsyncMock(return_value=1)
    buffer_manager = BufferManager(
        instruments=['ES', 'NQ', 'YM'],
        timeframes=[240, 60, 15, 5, 3, 1],
        max_size=500,
    )
    return MarketDataAgent(config, mock_ibkr, mock_db, buffer_manager)


def make_raw_bar(date_val, open_=4500.0, high=4510.0, low=4490.0, close=4505.0, volume=1000):
    bar = types.SimpleNamespace()
    bar.date = date_val
    bar.open = open_
    bar.high = high
    bar.low = low
    bar.close = close
    bar.volume = volume
    return bar


def make_bar_dict(instrument, timeframe, timestamp,
                  open_=4500.0, high=4510.0, low=4490.0, close=4505.0, volume=1000):
    return {
        'instrument': instrument,
        'timeframe': timeframe,
        'timestamp': timestamp,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }


def test_normalize_bar_15m_close_time():
    agent = make_agent()
    raw = make_raw_bar(datetime(2026, 4, 26, 10, 0, 0, tzinfo=timezone.utc))
    result = agent._normalize_bar(raw, 'ES', 15)
    assert result['timestamp'] == '2026-04-26T10:15:00Z'
    assert result['instrument'] == 'ES'
    assert result['timeframe'] == 15


def test_normalize_bar_240m_close_time():
    agent = make_agent()
    raw = make_raw_bar(datetime(2026, 4, 26, 10, 0, 0, tzinfo=timezone.utc))
    result = agent._normalize_bar(raw, 'NQ', 240)
    assert result['timestamp'] == '2026-04-26T14:00:00Z'
    assert result['timeframe'] == 240


def test_normalize_bar_none_date_raises():
    agent = make_agent()
    raw = make_raw_bar(None)
    with pytest.raises(ValueError):
        agent._normalize_bar(raw, 'ES', 15)


def test_check_gap_no_gap_no_warning(caplog):
    agent = make_agent()
    prev = make_bar_dict('ES', 15, '2026-04-26T10:15:00Z')
    agent._buffer_manager.push('ES', 15, prev)
    next_bar = make_bar_dict('ES', 15, '2026-04-26T10:30:00Z')
    with caplog.at_level(logging.WARNING, logger='apex.agents.market_data'):
        agent._check_gap('ES', 15, next_bar)
    assert not any('GAP DETECTED' in r.message for r in caplog.records)


def test_check_gap_detects_missing_bar(caplog):
    agent = make_agent()
    prev = make_bar_dict('ES', 15, '2026-04-26T10:15:00Z')
    agent._buffer_manager.push('ES', 15, prev)
    # Skip one 15m bar — gap of 30m
    next_bar = make_bar_dict('ES', 15, '2026-04-26T11:00:00Z')
    with caplog.at_level(logging.WARNING, logger='apex.agents.market_data'):
        agent._check_gap('ES', 15, next_bar)
    gap_records = [r for r in caplog.records if 'GAP DETECTED' in r.message]
    assert gap_records, 'Expected GAP DETECTED warning'
    assert '30' in gap_records[0].message  # gap = 30 minutes


@pytest.mark.asyncio
async def test_insert_historical_bars_returns_count():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        db = DatabaseManager(db_path)
        await db.init()
        bars = [
            {
                'instrument': 'ES', 'timeframe': 15,
                'timestamp': '2026-04-26T10:15:00Z',
                'open': 4500.0, 'high': 4510.0, 'low': 4490.0, 'close': 4505.0,
                'volume': 1000, 'session_date': '2026-04-25',
            },
            {
                'instrument': 'ES', 'timeframe': 15,
                'timestamp': '2026-04-26T10:30:00Z',
                'open': 4505.0, 'high': 4515.0, 'low': 4495.0, 'close': 4510.0,
                'volume': 1200, 'session_date': '2026-04-25',
            },
        ]
        count = await db.insert_historical_bars(bars)
        assert count == 2
        await db.close()


@pytest.mark.asyncio
async def test_insert_historical_bars_duplicate_ignored():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        db = DatabaseManager(db_path)
        await db.init()
        bar = {
            'instrument': 'NQ', 'timeframe': 60,
            'timestamp': '2026-04-26T14:00:00Z',
            'open': 18000.0, 'high': 18100.0, 'low': 17950.0, 'close': 18050.0,
            'volume': 500, 'session_date': '2026-04-25',
        }
        count1 = await db.insert_historical_bars([bar])
        count2 = await db.insert_historical_bars([bar])
        assert count1 == 1
        assert count2 == 0
        await db.close()


@pytest.mark.asyncio
async def test_database_creates_nine_tables():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        db = DatabaseManager(db_path)
        await db.init()
        all_tables = set(await db.get_tables())
        tables = {t for t in all_tables if not t.startswith('sqlite_')}
        assert 'historical_bars' in tables
        assert len(tables) == 9
        await db.close()
