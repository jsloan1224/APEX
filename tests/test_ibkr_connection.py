import pytest
import pytest_asyncio

from core.ibkr_client import IBKRClient, IBKRConnectionError


def make_config(mode: str = 'paper', port: int = 7497) -> dict:
    return {
        'mode': mode,
        'ibkr': {
            'paper': {'host': '127.0.0.1', 'port': 7497, 'client_id': 1},
            'live':  {'host': '127.0.0.1', 'port': 7496, 'client_id': 1},
            'connection_timeout': 5,
            'reconnect_attempts': 3,
            'reconnect_delay': 5,
        },
    }


def test_ibkr_client_instantiates():
    client = IBKRClient(make_config())
    assert client is not None
    assert not client.is_connected()


@pytest.mark.asyncio
async def test_dry_run_skips_connection():
    client = IBKRClient(make_config())
    await client.connect(dry_run=True)
    assert not client.is_connected()


@pytest.mark.asyncio
async def test_live_port_guard_raises_when_not_live():
    live_cfg = make_config(mode='paper')
    # Force the client to target port 7496 even though mode is 'paper'
    live_cfg['ibkr']['paper']['port'] = 7496
    client = IBKRClient(live_cfg)
    with pytest.raises(IBKRConnectionError, match='7496'):
        await client.connect(dry_run=False)


@pytest.mark.asyncio
async def test_live_mode_does_not_raise_guard():
    """Guard should NOT fire when mode is 'live' targeting port 7496."""
    live_cfg = make_config(mode='live')
    client = IBKRClient(live_cfg)
    # Will fail because no TWS is running, but NOT because of the guard
    with pytest.raises(Exception) as exc_info:
        await client.connect(dry_run=False)
    # The error should NOT be the guard message
    assert 'Refusing connection' not in str(exc_info.value)
