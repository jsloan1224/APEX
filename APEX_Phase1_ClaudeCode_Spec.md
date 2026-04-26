# APEX — Phase 1 Claude Code Build Spec
**Foundation: Scaffold · Config · Database · IBKR · Kill Switch · Logger · CLI**
**Version 1.3 | Single-Instrument Trading + Quality-Gate AI | April 2026**

---

## How to Use This Document

Paste the build instructions from Section 3 as your first message to Claude Code. Claude Code must build exactly what is specified. No additional features. No assumptions. After Claude Code completes Phase 1, return this document to Claude (design) for audit.

---

## 1. Phase 1 Scope

Phase 1 builds the foundation only. No trading logic. No signal detection. No chart. No order execution. No SMT detection. No AI gate.

1. Project scaffold — exact folder structure
2. config.yaml — single-instrument selection, per-instrument trade params, separated bias/FVG/SMT timeframes
3. SQLite database — all 8 tables including fvg_registry, key_levels, smt_events
4. IBKR paper trading connection via ib_insync
5. Kill switch skeleton — KillSwitch class, limits from config
6. Logger — file + console, rotating
7. Telegram bot skeleton
8. CLI entry point (main.py) with argparse, including `--market` flag
9. .env.template — never hardcode credentials, all keys spelled out
10. .gitignore
11. requirements.txt
12. pytest skeleton — six test files, one passing test each

---

## 2. What Changed — v1.3

| Component | Change |
|---|---|
| Trading model | Single-instrument per run. `traded_instrument` (string) replaces `markets` (list). CLI `--market` flag added. |
| Models | Model 4 "CL Liquidity Sweep" removed. CL removed from tick_values. |
| Timeframe roles | `bias_timeframes` is `[240, 60, 15]` only. New `fvg_detection_timeframes: [240, 60, 15, 5, 3, 1]`. New `smt_check_timeframes: [5, 1]`. |
| Trade params | Per-instrument `instrument_params` block — contracts, stop_ticks, target_ticks, min_target_ticks, min_fvg_size_ticks. Flat 1:1 R:R defaults. |
| Risk rules | `max_consecutive_losses` added. `signal_cutoff_minutes_before_kz_close` added. |
| AI gate | Model is `claude-haiku-4-5-20251001`, temperature 0, hard 2s timeout. Prompt redesigned for quality scoring (judgment), not rule rechecking. |
| Database | New table `smt_events`. `fvg_registry` gets `instrument` column. `key_levels` gets `instrument` column. |
| Logger | New `core/logger.py` — file + console, rotating. Required in Phase 1. |
| Timezone | Documented: UTC in DB, America/New_York for session math and display. |
| Async | Confirmed: aiosqlite + ib_insync, asyncio throughout. |
| .env.template | All required keys spelled out: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IBKR_ACCOUNT_ID. |
| .gitignore | Added — excludes data/*.db, .env, __pycache__, logs/*.log. |
| Folder | New `logs/` folder. New `agents/smt_agent.py` stub. New `tests/test_smt.py`. |

---

## 3. Phase 1 Build Instructions — Paste to Claude Code

### 3a. Preamble

```
APEX TRADING SYSTEM — PHASE 1 BUILD INSTRUCTIONS v1.3

You are building Phase 1 of APEX, a fully autonomous futures trading system.
Build exactly what is specified. No additional features. No assumptions.
Follow the folder structure precisely.
This is foundation only. No trading logic. No chart. No signal detection.
No SMT logic beyond stub. No AI gate logic beyond stub.

KEY ARCHITECTURAL FACTS:
- APEX trades ONE instrument per run, selected via --market CLI flag or
  config (ES, NQ, or YM). The other two are streamed as context only.
- bias_timeframes is [240, 60, 15] — three timeframes, not five.
- 5m and 3m are FVG-detection timeframes only, not bias timeframes.
- All timestamps stored as UTC ISO 8601 in SQLite.
- Async throughout — aiosqlite + ib_insync.
```

---

### 3b. Exact Folder Structure

```
apex/
├── main.py
├── config.yaml
├── .env.template
├── .gitignore
├── requirements.txt
├── README.md
│
├── agents/
│   ├── __init__.py
│   ├── market_data_agent.py      # stub — Phase 2
│   ├── session_clock_agent.py    # stub — Phase 2
│   ├── news_scraper_agent.py     # stub — Phase 3
│   ├── sentiment_agent.py        # stub — Phase 3
│   ├── smt_agent.py              # stub — Phase 4
│   ├── validation_gate.py        # stub — Phase 5
│   ├── risk_manager.py           # BUILD NOW — KillSwitch class
│   ├── execution_agent.py        # stub — Phase 7
│   ├── audit_agent.py            # stub — Phase 8
│   └── chart_agent.py            # stub — Phase 9
│
├── models/
│   ├── __init__.py
│   ├── base_model.py             # stub — Phase 4
│   ├── silver_bullet.py          # stub — Phase 4
│   ├── ifvg_smt.py               # stub — Phase 10
│   ├── power_of_three.py         # stub — Phase 10
│   └── news_catalyst.py          # stub — Phase 10
│
├── core/
│   ├── __init__.py
│   ├── signal.py                 # BUILD NOW — SignalCandidate dataclass
│   ├── indicators.py             # stub — Phase 2
│   ├── ibkr_client.py            # BUILD NOW
│   ├── claude_client.py          # stub — Phase 5
│   ├── database.py               # BUILD NOW — async aiosqlite
│   └── logger.py                 # BUILD NOW
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py                    # stub — Phase 9
│   ├── layout.py                 # stub — Phase 9
│   ├── charts.py                 # stub — Phase 9
│   ├── overlays.py               # stub — Phase 9
│   └── callbacks.py              # stub — Phase 9
│
├── prompts/
│   ├── sentiment_prompt.txt      # stub — Phase 3
│   └── validation_prompt.txt     # BUILD NOW — quality scoring prompt
│
├── data/
│   └── .gitkeep
│
├── logs/
│   └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── test_database.py          # BUILD NOW
    ├── test_ibkr_connection.py   # BUILD NOW
    ├── test_kill_switch.py       # BUILD NOW
    ├── test_signal.py            # BUILD NOW
    ├── test_smt.py               # BUILD NOW — stub, one passing test
    └── test_chart.py             # BUILD NOW — stub, one passing test
```

---

### 3c. config.yaml

```yaml
profiles:
  paper_default:
    traded_instrument: ES                # ES | NQ | YM — single selection (CLI --market overrides)
    context_instruments: [NQ, YM]        # read-only, used for SMT and correlation
    sessions: [LONDON, NY_AM, NY_PM]
    mode: paper
    bias_timeframes: [240, 60, 15]                    # bias chain — all must agree
    fvg_detection_timeframes: [240, 60, 15, 5, 3, 1]  # FVGs detected on all six
    execution_timeframe: 1                              # 1m entry chart
    smt_check_timeframes: [5, 1]                       # SMT divergence checked here
    signal_cutoff_minutes_before_kz_close: 15

    # Per-instrument trade parameters
    # Validation phase: flat 1:1 R:R across all instruments.
    # Once entries are proven, widen targets, add contracts, or pyramid.
    instrument_params:
      ES:
        contracts: 1
        stop_ticks: 20
        target_ticks: 20
        min_target_ticks: 20
        min_fvg_size_ticks: 4
      NQ:
        contracts: 1
        stop_ticks: 20
        target_ticks: 20
        min_target_ticks: 20
        min_fvg_size_ticks: 4
      YM:
        contracts: 1
        stop_ticks: 20
        target_ticks: 20
        min_target_ticks: 20
        min_fvg_size_ticks: 4

  conservative:
    traded_instrument: ES
    context_instruments: [NQ, YM]
    sessions: [NY_AM]
    mode: paper
    bias_timeframes: [60, 15]
    fvg_detection_timeframes: [60, 15, 5, 3, 1]
    execution_timeframe: 1
    smt_check_timeframes: [5, 1]
    signal_cutoff_minutes_before_kz_close: 15
    instrument_params:
      ES:
        contracts: 1
        stop_ticks: 15
        target_ticks: 15
        min_target_ticks: 15
        min_fvg_size_ticks: 4
      NQ:
        contracts: 1
        stop_ticks: 15
        target_ticks: 15
        min_target_ticks: 15
        min_fvg_size_ticks: 4
      YM:
        contracts: 1
        stop_ticks: 15
        target_ticks: 15
        min_target_ticks: 15
        min_fvg_size_ticks: 4

  aggressive:
    traded_instrument: ES
    context_instruments: [NQ, YM]
    sessions: [LONDON, NY_AM, NY_PM]
    mode: paper
    bias_timeframes: [240, 60, 15]
    fvg_detection_timeframes: [240, 60, 15, 5, 3, 1]
    execution_timeframe: 1
    smt_check_timeframes: [5, 1]
    signal_cutoff_minutes_before_kz_close: 15
    instrument_params:
      ES:
        contracts: 2
        stop_ticks: 25
        target_ticks: 25
        min_target_ticks: 25
        min_fvg_size_ticks: 4
      NQ:
        contracts: 2
        stop_ticks: 25
        target_ticks: 25
        min_target_ticks: 25
        min_fvg_size_ticks: 4
      YM:
        contracts: 2
        stop_ticks: 25
        target_ticks: 25
        min_target_ticks: 25
        min_fvg_size_ticks: 4

tick_values:
  ES:
    ticks_per_handle: 4
    tick_size: 0.25
    tick_value_usd: 12.50
    min_tick: 0.25
  NQ:
    ticks_per_handle: 4
    tick_size: 0.25
    tick_value_usd: 5.00
    min_tick: 0.25
  YM:
    ticks_per_handle: 1
    tick_size: 1.0
    tick_value_usd: 5.00
    min_tick: 1.0

sessions:
  LONDON:
    start: '03:00'
    end: '04:00'
    timezone: 'America/New_York'
  NY_AM:
    start: '10:00'
    end: '11:00'
    timezone: 'America/New_York'
  NY_PM:
    start: '14:00'
    end: '15:00'
    timezone: 'America/New_York'

ibkr:
  paper:
    host: '127.0.0.1'
    port: 7497
    client_id: 1
  live:
    host: '127.0.0.1'
    port: 7496
    client_id: 1
  connection_timeout: 30
  reconnect_attempts: 3
  reconnect_delay: 5

risk:
  max_daily_loss_usd: 500
  max_drawdown_usd: 300
  max_consecutive_losses: 3
  cool_off_minutes: 30
  news_window_minutes: 10
  max_open_positions: 1

database:
  path: 'data/apex.db'

logging:
  level: 'INFO'
  log_file: 'logs/apex.log'
  max_bytes: 10485760     # 10 MB
  backup_count: 5

telegram:
  enabled: false
  token: ''
  chat_id: ''

anthropic:
  model: 'claude-haiku-4-5-20251001'
  max_tokens_sentiment: 300
  max_tokens_validation: 200
  temperature: 0
  validation_timeout_seconds: 2.0

dashboard:
  enabled: true
  host: '127.0.0.1'
  port: 8050
  refresh_interval_ms: 1000
```

---

### 3d. core/signal.py — SignalCandidate Dataclass

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class SignalCandidate:
    # Core identification
    signal_id:                    str
    created_at:                   datetime    # UTC
    traded_instrument:            str          # ES | NQ | YM
    direction:                    str          # bullish | bearish
    model_name:                   str

    # Bias chain — three timeframes only
    bias_timeframes:              list         # e.g. [240, 60, 15]
    bias_per_timeframe:           dict         # e.g. {240: 'bullish', 60: 'bullish', 15: 'bullish'}
    bias_alignment:               bool         # True only if ALL agree
    bias_alignment_checked_at:    datetime    # UTC

    # FVG context
    fvg_timeframe:                int          # which TF the entry FVG came from (typically 1, 3, or 5)
    fvg_high:                     float        = 0.0
    fvg_low:                      float        = 0.0
    fvg_midpoint:                 float        = 0.0
    fvg_size_ticks:               int          = 0
    fvg_first_touch:              bool         = False

    # Key ICT levels at time of signal
    prev_day_high:                float        = 0.0
    prev_day_low:                 float        = 0.0
    daily_high:                   float        = 0.0
    daily_low:                    float        = 0.0
    midnight_open:                float        = 0.0
    ny_open:                      float        = 0.0
    weekly_open:                  float        = 0.0

    # Liquidity sweep details
    liquidity_level_swept:        float        = 0.0
    sweep_direction:              str          = ''     # 'BSL' | 'SSL'
    sweep_time:                   Optional[datetime] = None  # UTC

    # MSS
    mss_confirmed:                bool         = False
    mss_bar_index:                int          = -1

    # ICT confirmations
    liquidity_swept:              bool         = False
    fvg_identified:               bool         = False

    # Entry parameters (from instrument_params for traded_instrument)
    entry_price:                  float        = 0.0
    stop_loss_price:              float        = 0.0
    take_profit_price:            float        = 0.0
    stop_ticks:                   int          = 0
    target_ticks:                 int          = 0
    contracts:                    int          = 1

    # Session context
    session:                      str          = ''     # LONDON | NY_AM | NY_PM
    kill_zone_active:             bool         = False

    # SMT context (sister instruments, set by smt_agent at Step 3.5)
    sister_1_symbol:              str          = ''
    sister_1_bias:                str          = ''     # bullish | bearish | neutral
    sister_1_smt_divergence:      bool         = False
    sister_2_symbol:              str          = ''
    sister_2_bias:                str          = ''
    sister_2_smt_divergence:      bool         = False

    # AI gate result (set by validation_gate at Step 7)
    ai_gate_displacement_score:   Optional[int]   = None
    ai_gate_sweep_score:          Optional[int]   = None
    ai_gate_environment_score:    Optional[int]   = None
    ai_gate_average:              Optional[float] = None
    ai_gate_result:               str          = ''     # APPROVE | REJECT | TIMEOUT | ERROR
    ai_gate_reason:               str          = ''
    ai_gate_latency_ms:           Optional[int]   = None

    # Outcome
    discard_reason:               str          = ''     # populated if rejected at any step
    executed:                     bool         = False
    order_id:                     Optional[str]   = None
```

---

### 3e. core/database.py — Schema (async, aiosqlite)

```sql
-- TABLE: signal_candidates
-- Every setup evaluated, regardless of outcome.
CREATE TABLE IF NOT EXISTS signal_candidates (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id                   TEXT UNIQUE NOT NULL,
    created_at                  TEXT NOT NULL,         -- UTC ISO 8601
    traded_instrument           TEXT NOT NULL,         -- ES | NQ | YM
    direction                   TEXT NOT NULL,         -- bullish | bearish
    model_name                  TEXT NOT NULL,
    -- Bias chain
    bias_timeframes_json        TEXT NOT NULL,         -- JSON list, e.g. "[240,60,15]"
    bias_per_timeframe_json     TEXT NOT NULL,         -- JSON dict
    bias_alignment              INTEGER NOT NULL,      -- 0 | 1
    bias_alignment_checked_at   TEXT NOT NULL,
    -- FVG
    fvg_timeframe               INTEGER,
    fvg_high                    REAL,
    fvg_low                     REAL,
    fvg_midpoint                REAL,
    fvg_size_ticks              INTEGER,
    fvg_first_touch             INTEGER,
    -- Key ICT levels
    prev_day_high               REAL,
    prev_day_low                REAL,
    daily_high                  REAL,
    daily_low                   REAL,
    midnight_open               REAL,
    ny_open                     REAL,
    weekly_open                 REAL,
    -- Liquidity / MSS
    liquidity_level_swept       REAL,
    sweep_direction             TEXT,
    sweep_time                  TEXT,
    mss_confirmed               INTEGER,
    mss_bar_index               INTEGER,
    liquidity_swept             INTEGER,
    fvg_identified              INTEGER,
    -- Entry
    entry_price                 REAL,
    stop_loss_price             REAL,
    take_profit_price           REAL,
    stop_ticks                  INTEGER,
    target_ticks                INTEGER,
    contracts                   INTEGER,
    -- Session
    session                     TEXT,
    kill_zone_active            INTEGER,
    -- SMT context
    sister_1_symbol             TEXT,
    sister_1_bias               TEXT,
    sister_1_smt_divergence     INTEGER,
    sister_2_symbol             TEXT,
    sister_2_bias               TEXT,
    sister_2_smt_divergence     INTEGER,
    -- AI gate
    ai_gate_displacement_score  INTEGER,
    ai_gate_sweep_score         INTEGER,
    ai_gate_environment_score   INTEGER,
    ai_gate_average             REAL,
    ai_gate_result              TEXT,
    ai_gate_reason              TEXT,
    ai_gate_latency_ms          INTEGER,
    -- Outcome
    discard_reason              TEXT,
    executed                    INTEGER DEFAULT 0,
    order_id                    TEXT
);

-- TABLE: trades
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
    outcome           TEXT,                              -- WIN | LOSS | BREAKEVEN | EXIT_MANUAL
    entry_time        TEXT,                              -- UTC ISO 8601
    exit_time         TEXT,                              -- UTC ISO 8601
    duration_seconds  INTEGER,
    FOREIGN KEY (signal_id) REFERENCES signal_candidates(signal_id)
);

-- TABLE: system_events
CREATE TABLE IF NOT EXISTS system_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time  TEXT NOT NULL,                           -- UTC ISO 8601
    event_type  TEXT NOT NULL,                           -- STARTUP | SHUTDOWN | KILL_SWITCH |
                                                          -- IBKR_CONNECT | IBKR_DISCONNECT |
                                                          -- AI_GATE_TIMEOUT | AI_GATE_ERROR | ERROR
    detail      TEXT
);

-- TABLE: news_events
CREATE TABLE IF NOT EXISTS news_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_at      TEXT NOT NULL,
    headline        TEXT,
    source          TEXT,
    sentiment_score REAL,
    impact_rating   TEXT
);

-- TABLE: performance_daily
CREATE TABLE IF NOT EXISTS performance_daily (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date        TEXT NOT NULL,                     -- YYYY-MM-DD (NY date)
    traded_instrument TEXT NOT NULL,
    total_trades      INTEGER DEFAULT 0,
    wins              INTEGER DEFAULT 0,
    losses            INTEGER DEFAULT 0,
    pnl_usd           REAL DEFAULT 0.0,
    win_rate          REAL,
    avg_r             REAL,
    UNIQUE(trade_date, traded_instrument)
);

-- TABLE: fvg_registry
-- Tracks every FVG detected across all timeframes and all 3 instruments.
CREATE TABLE IF NOT EXISTS fvg_registry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     TEXT NOT NULL,
    instrument      TEXT NOT NULL,                       -- ES | NQ | YM
    is_traded       INTEGER NOT NULL,                    -- 1 if this is the traded_instrument, 0 if context
    timeframe       INTEGER NOT NULL,                    -- 240 | 60 | 15 | 5 | 3 | 1
    direction       TEXT NOT NULL,                       -- bullish | bearish
    high            REAL NOT NULL,
    low             REAL NOT NULL,
    midpoint        REAL NOT NULL,
    size_ticks      INTEGER,
    fvg_type        TEXT DEFAULT 'FVG',                  -- FVG | IFVG
    status          TEXT DEFAULT 'open',                 -- open | filled | invalidated
    filled_at       TEXT,
    used_for_signal INTEGER DEFAULT 0
);

-- TABLE: key_levels
-- ICT key reference levels updated each session, per instrument.
CREATE TABLE IF NOT EXISTS key_levels (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at      TEXT NOT NULL,
    instrument       TEXT NOT NULL,                      -- ES | NQ | YM
    level_date       TEXT NOT NULL,                      -- YYYY-MM-DD (NY date)
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

-- TABLE: smt_events
-- SMT divergence detections across instrument pairs.
CREATE TABLE IF NOT EXISTS smt_events (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at         TEXT NOT NULL,
    traded_instrument   TEXT NOT NULL,
    sister_instrument   TEXT NOT NULL,
    timeframe           INTEGER NOT NULL,
    divergence_type     TEXT NOT NULL,                   -- BULLISH_SMT | BEARISH_SMT
    traded_swing_price  REAL,
    sister_swing_price  REAL,
    detail              TEXT
);
```

`DatabaseManager` class requirements:
- async `init()` method that creates all 8 tables
- async `log_event(event_type, detail)` for system_events
- async insert / query helpers (full CRUD lands in later phases)
- Uses aiosqlite throughout
- Path from config: `database.path`

---

### 3f. core/ibkr_client.py

Build `IBKRClient` wrapping `ib_insync.IB()`.

- Methods: `async connect()`, `async disconnect()`, `is_connected()`, `async test_connection()`
- Read all params from config (`ibkr.paper.*` or `ibkr.live.*` based on profile mode)
- Log connection events to system_events table via DatabaseManager
- **CRITICAL:** Explicitly guard live port 7496 — `connect()` must raise `IBKRConnectionError` if `config mode != 'live'` and target port is 7496
- Raise `IBKRConnectionError` on any connection failure with clear message

---

### 3g. core/logger.py

Configure Python `logging` with:
- File handler: `logs/apex.log` from config
- Rotating: `RotatingFileHandler` with `max_bytes` and `backup_count` from config
- Console handler: stdout, same level
- Format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Timezone: timestamps in UTC (use `logging.Formatter` with `converter = time.gmtime`)
- Expose `get_logger(name: str)` factory

---

### 3h. main.py — CLI Entry Point

argparse with:
- `--profile` (default: `paper_default`) — config profile to use
- `--market` (choices: ES, NQ, YM) — overrides `traded_instrument` from profile
- `--dry-run` — skip IBKR connection
- `--interactive` — prompt for each parameter

Startup flow:
1. Parse CLI args
2. Configure logger from config
3. Load `config.yaml`, merge profile, apply `--market` override
4. Validate `traded_instrument` is in {ES, NQ, YM}
5. Validate `traded_instrument` is NOT in `context_instruments` (sanity)
6. If `--interactive`: prompt for each parameter
7. Print config summary — must show:
   - Active profile
   - **Traded instrument** (large label)
   - Context instruments
   - bias_timeframes
   - fvg_detection_timeframes
   - smt_check_timeframes
   - instrument_params for the traded instrument only
   - Mode (paper/live)
8. Initialize `DatabaseManager` — create all 8 tables
9. Initialize `KillSwitch` from config
10. Test IBKR connection unless `--dry-run`
11. Log STARTUP event to system_events with detail JSON: `{profile, traded_instrument, mode}`
12. Print `APEX SYSTEM READY — TRADING {traded_instrument}`
13. Ctrl+C: log SHUTDOWN, close DB, disconnect IBKR, exit cleanly

---

### 3i. agents/risk_manager.py — KillSwitch Skeleton

```python
class KillSwitch:
    def __init__(self, config: dict):
        risk = config['risk']
        self.max_daily_loss_usd      = risk['max_daily_loss_usd']
        self.max_drawdown_usd        = risk['max_drawdown_usd']
        self.max_consecutive_losses  = risk['max_consecutive_losses']
        self.cool_off_minutes        = risk['cool_off_minutes']
        self.news_window_minutes     = risk['news_window_minutes']
        self.max_open_positions      = risk['max_open_positions']
        self.triggered               = False
        self.trigger_reason          = None

    def check(self, daily_pnl: float, drawdown: float,
              open_positions: int, consecutive_losses: int) -> bool:
        # Stub — full logic Phase 6
        return False

    def trigger(self, reason: str):
        self.triggered = True
        self.trigger_reason = reason

    def reset(self):
        self.triggered = False
        self.trigger_reason = None
```

---

### 3j. prompts/validation_prompt.txt

```
You are evaluating an ICT futures trade setup that has already passed all
mechanical filters (bias chain alignment, kill zone, sweep detected, MSS,
FVG identification, tick filters). Your job is to score SETUP QUALITY only.

TRADED INSTRUMENT: {traded_instrument}
DIRECTION: {direction}
SETUP MODEL: {model_name}

LAST 20 1-MINUTE BARS (OHLCV):
{bars_1m}

LAST 10 5-MINUTE BARS (OHLCV):
{bars_5m}

SETUP CONTEXT:
  FVG range: {fvg_low} to {fvg_high} (size: {fvg_size_ticks} ticks)
  Entry (FVG midpoint): {entry_price}
  Stop: {stop_loss_price} | Target: {take_profit_price}
  Liquidity swept: {liquidity_level_swept} ({sweep_direction}) at {sweep_time}
  MSS displacement bar index: {mss_bar_index}

SISTER INSTRUMENT CONTEXT (read-only):
  {sister_1_symbol}: bias {sister_1_bias}, SMT divergence vs traded: {sister_1_smt_divergence}
  {sister_2_symbol}: bias {sister_2_bias}, SMT divergence vs traded: {sister_2_smt_divergence}

Score each dimension 1-5:

1. DISPLACEMENT QUALITY: Is the MSS bar a clean strong-body candle, or
   wicky/weak? Strong displacement = 4-5. Wicky/marginal = 1-2.

2. SWEEP DECISIVENESS: Did price take liquidity and reverse cleanly within
   1-3 bars, or hover/drift around the level? Decisive = 4-5. Drifting = 1-2.

3. ENVIRONMENT: Is recent price action directional and clean, or choppy?
   Factor in sister instrument SMT — divergence against trade direction
   downgrades this score. Clean directional = 4-5. Chop or SMT conflict = 1-2.

Compute average. APPROVE only if average >= 3.5 AND no dimension scores 1.

Respond ONLY with JSON, no preamble:
{
  "scores": {"displacement": N, "sweep": N, "environment": N},
  "average": N.NN,
  "result": "APPROVE" or "REJECT",
  "reason": "one sentence explaining the lowest-scoring dimension"
}
```

---

### 3k. .env.template

```
# Anthropic API — required for Claude quality gate (Phase 5) and sentiment (Phase 3)
ANTHROPIC_API_KEY=

# Telegram Bot — required for alerts (Phase 8). Set telegram.enabled: true in config.yaml
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# IBKR — optional. Account ID is informational only; connection uses host/port from config.
IBKR_ACCOUNT_ID=
```

---

### 3l. .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
.pytest_cache/
.venv/
venv/

# Environment
.env

# Data and logs
data/*.db
data/*.db-journal
data/*.db-wal
data/*.db-shm
logs/*.log
logs/*.log.*

# IDE
.vscode/
.idea/
*.swp
.DS_Store
```

---

### 3m. requirements.txt

```
ib_insync>=0.9.86
aiosqlite>=0.19.0
PyYAML>=6.0
python-dotenv>=1.0.0
anthropic>=0.39.0
aiohttp>=3.9.0
dash>=2.16.0
plotly>=5.20.0
pytz>=2024.1
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

---

### 3n. Test Stubs — All Six Must Have One Passing Test

- `test_database.py` — all 8 tables create cleanly: signal_candidates, trades, system_events, news_events, performance_daily, fvg_registry, key_levels, smt_events. Verify signal_candidates has all expected columns including SMT and AI gate fields.
- `test_ibkr_connection.py` — IBKRClient instantiates, dry-run skips connection, live port 7496 guard raises when `mode != 'live'`.
- `test_kill_switch.py` — KillSwitch instantiates with config, `check()` returns False with all-zero inputs, `trigger()` sets flag and reason, `reset()` clears.
- `test_signal.py` — SignalCandidate instantiates with all required fields, `bias_timeframes=[240, 60, 15]` stored correctly, SMT context fields default empty, AI gate fields default None.
- `test_smt.py` — `agents/smt_agent.py` is importable. Stub class instantiates without error.
- `test_chart.py` — dashboard/ folder exists, all 5 stub files importable without error.

---

## 4. Phase 1 Audit Checklist

### config.yaml
- [ ] `traded_instrument` field present in all profiles, valid (ES | NQ | YM)
- [ ] `context_instruments` field present in all profiles
- [ ] `traded_instrument` is NOT in `context_instruments`
- [ ] `bias_timeframes` is `[240, 60, 15]` in `paper_default` and `aggressive`
- [ ] `bias_timeframes` is `[60, 15]` in `conservative`
- [ ] `fvg_detection_timeframes` is `[240, 60, 15, 5, 3, 1]` in `paper_default` and `aggressive`
- [ ] `smt_check_timeframes` is `[5, 1]` in all profiles
- [ ] `execution_timeframe` is 1 in all profiles
- [ ] `signal_cutoff_minutes_before_kz_close: 15` in all profiles
- [ ] `instrument_params` block present in all profiles with ES, NQ, YM entries
- [ ] All instruments in `paper_default` have flat 1:1 R:R (stop=target=20)
- [ ] Tick values correct: ES $12.50, NQ $5.00, YM $5.00
- [ ] No CL entry in tick_values
- [ ] `risk.max_consecutive_losses: 3`
- [ ] `risk.cool_off_minutes: 30`
- [ ] `risk.news_window_minutes: 10`
- [ ] `anthropic.model: 'claude-haiku-4-5-20251001'`
- [ ] `anthropic.temperature: 0`
- [ ] `anthropic.validation_timeout_seconds: 2.0`
- [ ] `dashboard` section present with host, port, refresh_interval_ms
- [ ] `logging` section present with level, log_file, max_bytes, backup_count

### core/signal.py
- [ ] All bias chain fields: bias_timeframes, bias_per_timeframe, bias_alignment, bias_alignment_checked_at
- [ ] All key level fields: prev_day_high, prev_day_low, daily_high, daily_low, midnight_open, ny_open, weekly_open
- [ ] All sweep/MSS fields: liquidity_level_swept, sweep_direction, sweep_time, mss_confirmed, mss_bar_index
- [ ] All FVG fields: fvg_timeframe, fvg_high, fvg_low, fvg_midpoint, fvg_size_ticks, fvg_first_touch
- [ ] All SMT context fields for both sisters
- [ ] All AI gate fields with default None where applicable
- [ ] `traded_instrument` field (not `market`)
- [ ] `test_signal.py` passes with `bias_timeframes=[240, 60, 15]`

### core/database.py
- [ ] All 8 tables created on init: signal_candidates, trades, system_events, news_events, performance_daily, fvg_registry, key_levels, smt_events
- [ ] `signal_candidates` has all SMT context columns
- [ ] `signal_candidates` has all AI gate columns
- [ ] `signal_candidates` has `traded_instrument` (not `market`)
- [ ] `fvg_registry` has `instrument` and `is_traded` columns
- [ ] `key_levels` has `instrument` column
- [ ] `smt_events` table exists with correct schema
- [ ] All timestamps documented as UTC ISO 8601
- [ ] `test_database.py` verifies all 8 tables exist

### core/logger.py
- [ ] RotatingFileHandler configured with config values
- [ ] Console handler configured
- [ ] Timestamps in UTC
- [ ] `get_logger(name)` factory exposed

### core/ibkr_client.py
- [ ] Live port 7496 guard explicit — raises `IBKRConnectionError` when `mode != 'live'`
- [ ] async `connect()`, `disconnect()`, `test_connection()` methods
- [ ] Connection events logged to system_events

### main.py CLI
- [ ] `--market` flag with choices [ES, NQ, YM]
- [ ] `--market` overrides profile's `traded_instrument`
- [ ] `--dry-run` skips IBKR connection
- [ ] `--interactive` prompts for parameters
- [ ] Validates `traded_instrument` not in `context_instruments`
- [ ] Config summary on startup shows traded_instrument prominently
- [ ] Config summary shows correct bias_timeframes [240, 60, 15]
- [ ] STARTUP event written with profile, traded_instrument, mode in detail
- [ ] SHUTDOWN event written on Ctrl+C
- [ ] Prints `APEX SYSTEM READY — TRADING {traded_instrument}`

### prompts/validation_prompt.txt
- [ ] Quality scoring prompt (judgment), not rule rechecking
- [ ] References `traded_instrument` not `market`
- [ ] Three quality dimensions: displacement, sweep, environment
- [ ] Includes `bars_1m` and `bars_5m` placeholders for actual price data
- [ ] Includes both sister instruments with SMT divergence flags
- [ ] APPROVE rule: average >= 3.5 AND no dimension scores 1
- [ ] JSON-only response instruction with explicit format

### Folder Structure
- [ ] `dashboard/` folder exists with all 5 stub files
- [ ] `chart_agent.py` stub exists in `agents/`
- [ ] `smt_agent.py` stub exists in `agents/`
- [ ] `core/logger.py` exists and is functional
- [ ] `logs/` folder exists with `.gitkeep`
- [ ] `.gitignore` excludes data/*.db, .env, logs/*.log, __pycache__
- [ ] `.env.template` includes all four keys (ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IBKR_ACCOUNT_ID)
- [ ] No `models/cl_liquidity.py` file
- [ ] No reference to CL anywhere except acknowledgment that it was removed
- [ ] All other stubs raise `NotImplementedError` or pass through cleanly

### Tests
- [ ] All 6 test files have at least one passing test
- [ ] `pytest` exits zero with all tests passing

---

## 5. Full Build Sequence

| Phase | Scope |
|---|---|
| 1 | Foundation — this spec |
| 2 | Market data agent — bar streaming traded + 2 context instruments, all 6 timeframes |
| 3 | Session clock + news scraper + cutoff window |
| 4 | Model 1 Silver Bullet + SMT detection |
| 5 | AI quality gate — Claude Haiku 4.5, quality scoring |
| 6 | Risk manager — all hard rules |
| 7 | Execution engine — IBKR bracket orders, traded instrument only |
| 8 | Audit agent — SQLite + Telegram |
| 9 | ICT Chart Dashboard — Plotly Dash, primary + context panels |
| 10 | Models 2-4 — IFVG+SMT, PO3, News Catalyst |
| 11 | Live transition |
