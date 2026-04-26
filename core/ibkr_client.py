import asyncio

from core.logger import get_logger

logger = get_logger(__name__)


class IBKRConnectionError(Exception):
    pass


class IBKRClient:
    def __init__(self, config: dict):
        self._config = config
        profile_mode = config.get('mode', 'paper')
        ibkr_cfg = config.get('ibkr', {})
        conn_cfg = ibkr_cfg.get(profile_mode, ibkr_cfg.get('paper', {}))

        self._host = conn_cfg.get('host', '127.0.0.1')
        self._port = int(conn_cfg.get('port', 7497))
        self._client_id = conn_cfg.get('client_id', 1)
        self._mode = profile_mode
        self._timeout = ibkr_cfg.get('connection_timeout', 30)

        self._ib = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, dry_run: bool = False) -> None:
        if dry_run:
            logger.info('Dry-run mode: skipping IBKR connection')
            return

        if self._port == 7496 and self._mode != 'live':
            raise IBKRConnectionError(
                f'Refusing connection to live port 7496: mode is "{self._mode}", '
                'must be "live" to connect to port 7496.'
            )

        try:
            from ib_insync import IB
            self._ib = IB()
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._ib.connect(self._host, self._port, clientId=self._client_id),
                ),
                timeout=self._timeout,
            )
            self._connected = True
            logger.info('Connected to IBKR at %s:%s', self._host, self._port)
        except IBKRConnectionError:
            raise
        except Exception as exc:
            raise IBKRConnectionError(f'Failed to connect to IBKR: {exc}') from exc

    async def disconnect(self) -> None:
        if self._ib is not None:
            try:
                self._ib.disconnect()
            except Exception:
                pass
            self._ib = None
        self._connected = False
        logger.info('Disconnected from IBKR')

    async def test_connection(self) -> bool:
        if not self._connected or self._ib is None:
            return False
        try:
            return self._ib.isConnected()
        except Exception:
            return False
