import asyncio
import tempfile
import os
import pytest
import pytest_asyncio

from core.database import DatabaseManager

EXPECTED_TABLES = {
    'signal_candidates', 'trades', 'system_events', 'news_events',
    'performance_daily', 'fvg_registry', 'key_levels', 'smt_events',
}

SIGNAL_CANDIDATES_REQUIRED_COLUMNS = {
    # Core
    'signal_id', 'created_at', 'traded_instrument', 'direction', 'model_name',
    # Bias
    'bias_timeframes_json', 'bias_per_timeframe_json', 'bias_alignment', 'bias_alignment_checked_at',
    # FVG
    'fvg_timeframe', 'fvg_high', 'fvg_low', 'fvg_midpoint', 'fvg_size_ticks', 'fvg_first_touch',
    # Key levels
    'prev_day_high', 'prev_day_low', 'daily_high', 'daily_low',
    'midnight_open', 'ny_open', 'weekly_open',
    # Sweep / MSS
    'liquidity_level_swept', 'sweep_direction', 'sweep_time',
    'mss_confirmed', 'mss_bar_index', 'liquidity_swept', 'fvg_identified',
    # Entry
    'entry_price', 'stop_loss_price', 'take_profit_price',
    'stop_ticks', 'target_ticks', 'contracts',
    # Session
    'session', 'kill_zone_active',
    # SMT context
    'sister_1_symbol', 'sister_1_bias', 'sister_1_smt_divergence',
    'sister_2_symbol', 'sister_2_bias', 'sister_2_smt_divergence',
    # AI gate
    'ai_gate_displacement_score', 'ai_gate_sweep_score', 'ai_gate_environment_score',
    'ai_gate_average', 'ai_gate_result', 'ai_gate_reason', 'ai_gate_latency_ms',
    # Outcome
    'discard_reason', 'executed', 'order_id',
}


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / 'test_apex.db')


@pytest.fixture
def db(db_path):
    return DatabaseManager(db_path)


@pytest.mark.asyncio
async def test_all_eight_tables_created(db):
    await db.init()
    all_tables = set(await db.get_tables())
    # Exclude SQLite internal tables (e.g. sqlite_sequence created by AUTOINCREMENT)
    tables = {t for t in all_tables if not t.startswith('sqlite_')}
    assert EXPECTED_TABLES == tables, f'Missing tables: {EXPECTED_TABLES - tables}'
    await db.close()


@pytest.mark.asyncio
async def test_signal_candidates_has_required_columns(db):
    await db.init()
    columns = set(await db.get_columns('signal_candidates'))
    missing = SIGNAL_CANDIDATES_REQUIRED_COLUMNS - columns
    assert not missing, f'Missing columns: {missing}'
    await db.close()


@pytest.mark.asyncio
async def test_log_event_inserts_system_event(db):
    await db.init()
    await db.log_event('STARTUP', '{"profile": "paper_default"}')
    import aiosqlite
    async with aiosqlite.connect(db.db_path) as conn:
        cursor = await conn.execute('SELECT event_type, detail FROM system_events')
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == 'STARTUP'
    await db.close()
