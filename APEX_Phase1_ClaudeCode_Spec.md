# APEX — Phase 1 Claude Code Build Spec
**Foundation: Scaffold · Config · Database · IBKR · Kill Switch · CLI**
**Version 1.2 | 3m/5m Timeframes + Chart Phase | April 2026**

---

## How to Use This Document

Paste the build instructions from Section 3 as your first message to Claude Code. Claude Code must build exactly what is specified. No additional features. No assumptions. After Claude Code completes Phase 1, return this document to Claude (design) for audit.

---

## 1. Phase 1 Scope

Phase 1 builds the foundation only. No trading logic. No signal detection. No chart. No order execution.

1. Project scaffold — exact folder structure
2. config.yaml — full parameter structure with 3m/5m/MTF bias chain
3. SQLite database — all tables including fvg_registry and key_levels
4. IBKR paper trading connection via ib_insync
5. Kill switch skeleton — KillSwitch class, limits from config
6. Telegram bot skeleton
7. CLI entry point (main.py) with argparse
8. .env template — never hardcode credentials
9. requirements.txt
10. pytest skeleton — five test files, one passing test each

---

## 2. What Changed — v1.2

| Component | Change |
|---|---|
| config.yaml | bias_timeframes now [240, 60, 15, 5, 3] — 3m and 5m added to all profiles |
| core/database.py | Two new tables: fvg_registry (all FVGs across all TFs) and key_levels (daily H/L, midnight open, NY open) |
| prompts/validation_prompt.txt | Key levels section added: prev day H/L, daily H/L, midnight open, NY open, liquidity sweep detail |
| Build sequence | Phase 9 is now ICT Chart Dashboard. Models 2-5 moved to Phase 10. Live transition is Phase 11. |
| Folder structure | New dashboard/ folder added for Phase 9 (stub only in Phase 1) |
| requirements.txt | dash and plotly added for chart phase (installed in Phase 1, used in Phase 9) |

---

## 3. Phase 1 Build Instructions — Paste to Claude Code

### 3a. Preamble

```
APEX TRADING SYSTEM — PHASE 1 BUILD INSTRUCTIONS v1.2

You are building Phase 1 of APEX, a fully autonomous futures trading system.
Build exactly what is specified. No additional features. No assumptions.
Follow the folder structure precisely.
This is foundation only. No trading logic. No chart. No signal detection.
```

---

### 3b. Exact Folder Structure

```
apex/
├── main.py
├── config.yaml
├── .env.template
├── requirements.txt
├── README.md
│
├── agents/
│   ├── __init__.py
│   ├── market_data_agent.py      # stub — Phase 2
│   ├── session_clock_agent.py    # stub — Phase 2
│   ├── news_scraper_agent.py     # stub — Phase 3
│   ├── sentiment_agent.py        # stub — Phase 3
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
│   ├── cl_liquidity.py           # stub — Phase 10
│   └── news_catalyst.py          # stub — Phase 10
│
├── core/
│   ├── __init__.py
│   ├── signal.py                 # BUILD NOW — SignalCandidate dataclass
│   ├── indicators.py             # stub — Phase 2
│   ├── ibkr_client.py            # BUILD NOW
│   ├── claude_client.py          # stub — Phase 5
│   └── database.py               # BUILD NOW
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
│   └── validation_prompt.txt     # BUILD NOW
│
├── data/
│   └── .gitkeep
│
└── tests/
    ├── __init__.py
    ├── test_database.py          # BUILD NOW
    ├── test_ibkr_connection.py   # BUILD NOW
    ├── test_kill_switch.py       # BUILD NOW
    ├── test_signal.py            # BUILD NOW
    └── test_chart.py             # BUILD NOW — stub, one passing test
```

---

### 3c. config.yaml

```yaml
profiles:
  paper_default:
    contracts: 1
    stop_ticks: 20
    target_ticks: 21
    min_target_ticks: 21
    markets: [ES, NQ, YM]
    sessions: [LONDON, NY_AM, NY_PM]
    mode: paper
    bias_timeframes: [240, 60, 15, 5, 3]   # 4H -> 1H -> 15m -> 5m -> 3m
    execution_timeframe: 1                   # 1m entry chart

  conservative:
    contracts: 1
    stop_ticks: 15
    target_ticks: 20
    min_target_ticks: 20
    markets: [ES]
    sessions: [NY_AM]
    mode: paper
    bias_timeframes: [60, 15, 5]
    execution_timeframe: 1

  aggressive:
    contracts: 2
    stop_ticks: 25
    target_ticks: 40
    min_target_ticks: 30
    markets: [ES, NQ, YM]
    sessions: [LONDON, NY_AM, NY_PM]
    mode: paper
    bias_timeframes: [240, 60, 15, 5, 3]
    execution_timeframe: 1

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
  CL:
    ticks_per_handle: 10
    tick_size: 0.01
    tick_value_usd: 10.00
    min_tick: 0.01

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
  cool_off_minutes: 15
  news_window_minutes: 2
  max_open_positions: 1

database:
  path: 'data/apex.db'

telegram:
  enabled: false
  token: ''
  chat_id: ''

anthropic:
  model: 'claude-sonnet-4-5-20251001'
  max_tokens_sentiment: 300
  max_tokens_validation: 500
  temperature: 0

dashboard:
  enabled: true
  host: '127.0.0.1'
  port: 8050
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
    created_at:                   datetime
    market:                       str          # ES | NQ | YM | CL
    direction:                    str          # bullish | bearish
    model_name:                   str

    # MTF bias chain — all timeframes including 3m and 5m
    bias_timeframes:              list         # e.g. [240, 60, 15, 5, 3]
    bias_per_timeframe:           dict         # e.g. {240: 'bullish', 60: 'bullish', ...}
    bias_alignment:               bool         # True only if ALL agree
    bias_alignment_checked_at:    datetime

    # Key ICT levels at time of signal
    prev_day_high:                float        = 0.0
    prev_day_low:                 float        = 0.0
    daily_high:                   float        = 0.0
    daily_low:                    float        = 0.0
    midnight_open:                float        = 0.0
    ny_open:                      float        = 0.0
    liquidity_level_swept:        float        = 0.0
    sweep_direction:              str          = ''   # BSL | SSL

    # Entry parameters
    entry_price:                  float        = 0.0
    stop_loss_price:              float        = 0.0
    take_profit_price:            float        = 0.0
    stop_ticks:                   int          = 20
    target_ticks:                 int          = 21
    fvg_size_ticks:               int          = 0
    fvg_timeframe:                int          = 1    # which TF the entry FVG is on

    # Session context
    session:                      str          = ''
    kill_zone_active:             bool         = False

    # ICT confirmations
    liquidity_swept:              bool         = False
    mss_confirmed:                bool         = False
    fvg_identified:               bool         = False
    fvg_first_touch:              bool         = False

    # Validation state
    ai_validation_result:         str          = 'PENDING'  # APPROVE | REJECT | PENDING
    ai_validation_reason:         str          = ''
    risk_check_passed:            bool         = False
    executed:                     bool         = False
    discard_reason:               Optional[str]= None       # MTF_BIAS_CONFLICT | TICK_FILTER | ...
```

---

### 3e. core/database.py — Full Schema

Build DatabaseManager with async (aiosqlite) and sync init. Create all seven tables on startup.

```sql
-- TABLE: signal_candidates
CREATE TABLE IF NOT EXISTS signal_candidates (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id                   TEXT UNIQUE NOT NULL,
    created_at                  TEXT NOT NULL,
    market                      TEXT NOT NULL,
    direction                   TEXT NOT NULL,
    model_name                  TEXT NOT NULL,
    bias_timeframes             TEXT,
    bias_per_timeframe          TEXT,
    bias_alignment              INTEGER,
    bias_alignment_checked_at   TEXT,
    prev_day_high               REAL,
    prev_day_low                REAL,
    daily_high                  REAL,
    daily_low                   REAL,
    midnight_open               REAL,
    ny_open                     REAL,
    liquidity_level_swept       REAL,
    sweep_direction             TEXT,
    entry_price                 REAL,
    stop_loss_price             REAL,
    take_profit_price           REAL,
    stop_ticks                  INTEGER,
    target_ticks                INTEGER,
    fvg_size_ticks              INTEGER,
    fvg_timeframe               INTEGER,
    session                     TEXT,
    kill_zone_active            INTEGER,
    liquidity_swept             INTEGER DEFAULT 0,
    mss_confirmed               INTEGER DEFAULT 0,
    fvg_identified              INTEGER DEFAULT 0,
    fvg_first_touch             INTEGER DEFAULT 0,
    ai_validation_result        TEXT DEFAULT 'PENDING',
    ai_validation_reason        TEXT,
    risk_check_passed           INTEGER DEFAULT 0,
    executed                    INTEGER DEFAULT 0,
    discard_reason              TEXT
);

-- TABLE: trades
CREATE TABLE IF NOT EXISTS trades (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id         TEXT NOT NULL,
    market            TEXT NOT NULL,
    direction         TEXT NOT NULL,
    entry_price       REAL,
    exit_price        REAL,
    stop_loss_price   REAL,
    take_profit_price REAL,
    contracts         INTEGER,
    pnl_usd           REAL,
    outcome           TEXT,
    entry_time        TEXT,
    exit_time         TEXT,
    duration_seconds  INTEGER
);

-- TABLE: system_events
CREATE TABLE IF NOT EXISTS system_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time  TEXT NOT NULL,
    event_type  TEXT NOT NULL,
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
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date   TEXT UNIQUE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    wins         INTEGER DEFAULT 0,
    losses       INTEGER DEFAULT 0,
    pnl_usd      REAL DEFAULT 0.0,
    win_rate     REAL,
    avg_r        REAL
);

-- TABLE: fvg_registry (NEW v1.2)
-- Tracks every FVG detected across all timeframes
CREATE TABLE IF NOT EXISTS fvg_registry (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     TEXT NOT NULL,
    market          TEXT NOT NULL,
    timeframe       INTEGER NOT NULL,   -- 240|60|15|5|3|1
    direction       TEXT NOT NULL,      -- bullish | bearish
    high            REAL NOT NULL,      -- top of FVG
    low             REAL NOT NULL,      -- bottom of FVG
    midpoint        REAL NOT NULL,      -- entry target
    size_ticks      INTEGER,
    fvg_type        TEXT DEFAULT 'FVG', -- FVG | IFVG
    status          TEXT DEFAULT 'open', -- open | filled | invalidated
    filled_at       TEXT,
    used_for_signal INTEGER DEFAULT 0   -- 1 if this FVG triggered a signal
);

-- TABLE: key_levels (NEW v1.2)
-- ICT key reference levels updated each session
CREATE TABLE IF NOT EXISTS key_levels (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    recorded_at      TEXT NOT NULL,
    market           TEXT NOT NULL,
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
```

---

### 3f. core/ibkr_client.py

Build IBKRClient wrapping ib_insync IB().

- Methods: `connect()`, `disconnect()`, `is_connected()`, `test_connection()`
- Read all params from config. Default paper port 7497
- Log connection events to system_events table
- **CRITICAL:** Explicitly guard live port 7496 — cannot connect unless `config mode == 'live'`
- Raise `IBKRConnectionError` on failure with clear message

---

### 3g. main.py — CLI Entry Point

argparse with: `--profile` (default: paper_default), `--dry-run`, `--interactive`

1. Parse CLI args
2. Load config.yaml, merge profile, apply CLI overrides
3. If --interactive: prompt for each parameter
4. Print config summary — must include bias_timeframes [240, 60, 15, 5, 3]
5. Initialize DatabaseManager — create all 7 tables
6. Initialize KillSwitch from config
7. Test IBKR connection unless --dry-run
8. Log STARTUP event to system_events
9. Print `APEX SYSTEM READY`
10. Ctrl+C: log SHUTDOWN, exit cleanly

---

### 3h. agents/risk_manager.py — KillSwitch Skeleton

```python
class KillSwitch:
    def __init__(self, config: dict):
        self.max_daily_loss_usd  = config['risk']['max_daily_loss_usd']
        self.max_drawdown_usd    = config['risk']['max_drawdown_usd']
        self.cool_off_minutes    = config['risk']['cool_off_minutes']
        self.news_window_minutes = config['risk']['news_window_minutes']
        self.max_open_positions  = config['risk']['max_open_positions']
        self.triggered           = False
        self.trigger_reason      = None

    def check(self, daily_pnl: float, drawdown: float,
              open_positions: int) -> bool:
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

### 3i. prompts/validation_prompt.txt

```
TRADE SETUP VALIDATION REQUEST

Market: {market} | Direction: {direction} | Model: {model_name}
Session: {session} | Kill Zone Active: {kill_zone_active}

MTF BIAS CHAIN:
  Timeframes: [240, 60, 15, 5, 3]
  Bias per timeframe: {bias_per_timeframe}
  All aligned: {bias_alignment}
  RULE: If bias_alignment is False -> REJECT

KEY ICT LEVELS:
  Previous day high: {prev_day_high}
  Previous day low:  {prev_day_low}
  Daily high:        {daily_high}
  Daily low:         {daily_low}
  Midnight open:     {midnight_open}
  NY open (9:30):    {ny_open}
  Liquidity swept:   {liquidity_level_swept} ({sweep_direction})

ENTRY PARAMETERS:
  Entry: {entry_price} | SL: {stop_loss_price} | TP: {take_profit_price}
  Stop ticks: {stop_ticks} | Target ticks: {target_ticks}
  FVG timeframe: {fvg_timeframe}m | FVG size: {fvg_size_ticks} ticks
  RULE: If fvg_size_ticks < {min_target_ticks} -> REJECT

ICT CONFIRMATIONS:
  Liquidity swept:  {liquidity_swept}
  MSS confirmed:    {mss_confirmed}
  FVG identified:   {fvg_identified}
  First touch only: {fvg_first_touch}
  RULE: All four must be True to APPROVE

Respond ONLY with JSON. No preamble. No explanation outside the JSON.
{"result": "APPROVE" or "REJECT", "reason": "one sentence"}
```

---

### 3j. requirements.txt

```
ib_insync>=0.9.86
aiosqlite>=0.19.0
PyYAML>=6.0
python-dotenv>=1.0.0
anthropic>=0.25.0
aiohttp>=3.9.0
dash>=2.16.0
plotly>=5.20.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

---

### 3k. Test Stubs — All Five Must Have One Passing Test

- `test_database.py` — tables create cleanly, verify fvg_registry and key_levels exist, signal_candidates has all columns
- `test_ibkr_connection.py` — IBKRClient instantiates, dry-run skips connection, live port guard works
- `test_kill_switch.py` — KillSwitch instantiates with config, check() returns False, trigger() sets flag
- `test_signal.py` — SignalCandidate instantiates with all fields, bias_timeframes=[240,60,15,5,3] stored correctly
- `test_chart.py` — dashboard/ folder exists, all stub files importable without error

---

## 4. Phase 1 Audit Checklist

### config.yaml
- [ ] bias_timeframes is [240, 60, 15, 5, 3] in paper_default and aggressive profiles
- [ ] bias_timeframes is [60, 15, 5] in conservative profile
- [ ] execution_timeframe: 1 in all profiles
- [ ] dashboard section present with host and port
- [ ] All tick values correct: ES $12.50, NQ $5.00, YM $5.00

### core/signal.py
- [ ] All four MTF fields present: bias_timeframes, bias_per_timeframe, bias_alignment, bias_alignment_checked_at
- [ ] All key level fields present: prev_day_high, prev_day_low, daily_high, daily_low, midnight_open, ny_open, liquidity_level_swept, sweep_direction
- [ ] fvg_timeframe field present
- [ ] test_signal.py passes with bias_timeframes=[240,60,15,5,3]

### core/database.py
- [ ] All 7 tables created on init: signal_candidates, trades, system_events, news_events, performance_daily, fvg_registry, key_levels
- [ ] fvg_registry has timeframe column supporting values: 240, 60, 15, 5, 3, 1
- [ ] key_levels has midnight_open and ny_open columns
- [ ] test_database.py verifies all 7 tables exist

### IBKR / Kill Switch / CLI
- [ ] Live port guard explicit in ibkr_client.py
- [ ] --dry-run skips connection
- [ ] Config summary on startup shows bias_timeframes correctly
- [ ] STARTUP and SHUTDOWN events written to system_events
- [ ] All 5 tests pass

### prompts/validation_prompt.txt
- [ ] MTF BIAS CHAIN section present with [240, 60, 15, 5, 3] listed
- [ ] KEY ICT LEVELS section present with all 7 level fields
- [ ] fvg_timeframe field present in ENTRY PARAMETERS
- [ ] JSON-only response instruction present

### Folder Structure
- [ ] dashboard/ folder exists with all 5 stub files
- [ ] chart_agent.py stub exists in agents/
- [ ] All other stubs raise NotImplementedError or pass

---

## 5. Full Build Sequence

| Phase | Scope |
|---|---|
| 1 | Foundation — this spec |
| 2 | Market data agent — bar streaming all 6 timeframes [240,60,15,5,3,1] |
| 3 | Session clock + news scraper |
| 4 | Model 1 Silver Bullet — full ICT + MTF bias chain |
| 5 | AI validation gate — Claude API |
| 6 | Risk manager — all hard rules |
| 7 | Execution engine — IBKR bracket orders |
| 8 | Audit agent — SQLite + Telegram |
| 9 | ICT Chart Dashboard — Plotly Dash (full ICT view) |
| 10 | Models 2-5 — remaining ICT models |
| 11 | Live transition |
