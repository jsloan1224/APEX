import asyncio
from datetime import datetime, timezone

import aiosqlite


class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def init(self):
        self._conn = await aiosqlite.connect(self.db_path)
        await self._create_tables()

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def _create_tables(self):
        assert self._conn is not None
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS signal_candidates (
                id                          INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id                   TEXT UNIQUE NOT NULL,
                created_at                  TEXT NOT NULL,
                traded_instrument           TEXT NOT NULL,
                direction                   TEXT NOT NULL,
                model_name                  TEXT NOT NULL,
                bias_timeframes_json        TEXT NOT NULL,
                bias_per_timeframe_json     TEXT NOT NULL,
                bias_alignment              INTEGER NOT NULL,
                bias_alignment_checked_at   TEXT NOT NULL,
                fvg_timeframe               INTEGER,
                fvg_high                    REAL,
                fvg_low                     REAL,
                fvg_midpoint                REAL,
                fvg_size_ticks              INTEGER,
                fvg_first_touch             INTEGER,
                prev_day_high               REAL,
                prev_day_low                REAL,
                daily_high                  REAL,
                daily_low                   REAL,
                midnight_open               REAL,
                ny_open                     REAL,
                weekly_open                 REAL,
                liquidity_level_swept       REAL,
                sweep_direction             TEXT,
                sweep_time                  TEXT,
                mss_confirmed               INTEGER,
                mss_bar_index               INTEGER,
                liquidity_swept             INTEGER,
                fvg_identified              INTEGER,
                entry_price                 REAL,
                stop_loss_price             REAL,
                take_profit_price           REAL,
                stop_ticks                  INTEGER,
                target_ticks                INTEGER,
                contracts                   INTEGER,
                session                     TEXT,
                kill_zone_active            INTEGER,
                sister_1_symbol             TEXT,
                sister_1_bias               TEXT,
                sister_1_smt_divergence     INTEGER,
                sister_2_symbol             TEXT,
                sister_2_bias               TEXT,
                sister_2_smt_divergence     INTEGER,
                ai_gate_displacement_score  INTEGER,
                ai_gate_sweep_score         INTEGER,
                ai_gate_environment_score   INTEGER,
                ai_gate_average             REAL,
                ai_gate_result              TEXT,
                ai_gate_reason              TEXT,
                ai_gate_latency_ms          INTEGER,
                discard_reason              TEXT,
                executed                    INTEGER DEFAULT 0,
                order_id                    TEXT
            );

            CREATE TABLE IF NOT EXISTS trades (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id         TEXT,
                traded_instrument TEXT NOT NULL,
                direction         TEXT,
                entry_price       REAL,
                exit_price        REAL,
                stop_loss_price   REAL,
                take_profit_price REAL,
                contracts         INTEGER,
                pnl_usd           REAL,
                outcome           TEXT,
                entry_time        TEXT,
                exit_time         TEXT,
                duration_seconds  INTEGER,
                FOREIGN KEY (signal_id) REFERENCES signal_candidates(signal_id)
            );

            CREATE TABLE IF NOT EXISTS system_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time  TEXT NOT NULL,
                event_type  TEXT NOT NULL,
                detail      TEXT
            );

            CREATE TABLE IF NOT EXISTS news_events (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                scraped_at      TEXT NOT NULL,
                headline        TEXT,
                source          TEXT,
                sentiment_score REAL,
                impact_rating   TEXT
            );

            CREATE TABLE IF NOT EXISTS performance_daily (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date        TEXT NOT NULL,
                traded_instrument TEXT NOT NULL,
                total_trades      INTEGER DEFAULT 0,
                wins              INTEGER DEFAULT 0,
                losses            INTEGER DEFAULT 0,
                pnl_usd           REAL DEFAULT 0.0,
                win_rate          REAL,
                avg_r             REAL,
                UNIQUE(trade_date, traded_instrument)
            );

            CREATE TABLE IF NOT EXISTS fvg_registry (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at     TEXT NOT NULL,
                instrument      TEXT NOT NULL,
                is_traded       INTEGER NOT NULL,
                timeframe       INTEGER NOT NULL,
                direction       TEXT NOT NULL,
                high            REAL NOT NULL,
                low             REAL NOT NULL,
                midpoint        REAL NOT NULL,
                size_ticks      INTEGER,
                fvg_type        TEXT DEFAULT 'FVG',
                status          TEXT DEFAULT 'open',
                filled_at       TEXT,
                used_for_signal INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS key_levels (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at      TEXT NOT NULL,
                instrument       TEXT NOT NULL,
                level_date       TEXT NOT NULL,
                prev_day_high    REAL,
                prev_day_low     REAL,
                prev_day_close   REAL,
                current_day_open REAL,
                daily_high       REAL,
                daily_low        REAL,
                midnight_open    REAL,
                ny_open          REAL,
                weekly_open      REAL
            );

            CREATE TABLE IF NOT EXISTS smt_events (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                detected_at         TEXT NOT NULL,
                traded_instrument   TEXT NOT NULL,
                sister_instrument   TEXT NOT NULL,
                timeframe           INTEGER NOT NULL,
                divergence_type     TEXT NOT NULL,
                traded_swing_price  REAL,
                sister_swing_price  REAL,
                detail              TEXT
            );
        """)
        await self._conn.commit()

    async def log_event(self, event_type: str, detail: str | None = None):
        assert self._conn is not None
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            "INSERT INTO system_events (event_time, event_type, detail) VALUES (?, ?, ?)",
            (now, event_type, detail),
        )
        await self._conn.commit()

    async def get_tables(self) -> list[str]:
        assert self._conn is not None
        cursor = await self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_columns(self, table: str) -> list[str]:
        assert self._conn is not None
        cursor = await self._conn.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        return [row[1] for row in rows]
