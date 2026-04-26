# PROJECT_STATE.md
**Current build state for APEX. Updated when phase status changes.**
**Last updated: April 26, 2026 | Spec version: v1.3 | Phase 2 complete**

---

## Current Phase

**Phase 1 — Foundation: COMPLETE and AUDITED.**
**Phase 2 — Market Data Agent: COMPLETE and AUDITED.**
**Phase 3 — Session Clock + News Scraper: SPEC WRITTEN. Ready for Claude Code.**

---

## What's Built and Working

### Configuration (`config.yaml`)
- Three profiles: `paper_default`, `conservative`, `aggressive`
- All profiles use single-instrument trading model
- `bias_timeframes: [240, 60, 15]` (3 timeframes only — 5m/3m are NOT bias)
- `fvg_detection_timeframes: [240, 60, 15, 5, 3, 1]` (all six)
- `smt_check_timeframes: [5, 1]`
- Per-instrument trade params with flat 1:1 R:R (stop=target=20 ticks) for validation phase
- Tick values: ES $12.50, NQ $5.00, YM $5.00. No CL.
- Risk block: max_daily_loss $500, max_drawdown $300, max_consecutive_losses 3, cool_off 30min, news_window 10min
- Anthropic model: `claude-haiku-4-5-20251001`, temperature 0, validation_timeout 2s
- Sessions in America/New_York: LONDON 03:00-04:00, NY_AM 10:00-11:00, NY_PM 14:00-15:00

### Core Modules — Implemented
- `core/database.py` — Async aiosqlite manager. All 8 tables created on init: `signal_candidates`, `trades`, `system_events`, `news_events`, `performance_daily`, `fvg_registry`, `key_levels`, `smt_events`. UTC ISO 8601 timestamps. `log_event()` and `get_columns()` helpers.
- `core/signal.py` — `SignalCandidate` dataclass with all fields including bias chain (3 timeframes), FVG context, key ICT levels, sweep/MSS, entry params, session context, SMT context for both sisters, AI gate scores.
- `core/ibkr_client.py` — `IBKRClient` wrapper with async connect/disconnect/test_connection. Live port 7496 guard raises `IBKRConnectionError` when `mode != 'live'`. Dry-run support.
- `core/logger.py` — `configure_logging()` and `get_logger()`. RotatingFileHandler + console handler, UTC timestamps via `formatter.converter = time.gmtime`.

### Phase 2 Modules — Implemented
- `core/bar_buffer.py` — `BarBuffer` (thread-safe deque ring buffer, configurable size) and `BufferManager` (18 buffers: 3 instruments × 6 timeframes). All read/write ops under `threading.Lock`. Push validates required fields.
- `agents/market_data_agent.py` — Full implementation: dynamic contract resolution via `reqContractDetails()`, `reqHistoricalData` with `keepUpToDate=True` for all 6 timeframes × 3 instruments = 18 streams, bar normalization to close-time UTC, buffer writes, historical persistence via `asyncio.get_running_loop().create_task()`, gap detection + logging, reconnect logic with kill switch trigger on exhaustion.
- `core/database.py` — `historical_bars` table added (9th table). Unique index on `(instrument, timeframe, timestamp)`. Lookup index on `(instrument, timeframe, session_date)`. `insert_historical_bars()` bulk method with `INSERT OR IGNORE`.
- `config.yaml` — `market_data` block added: `bar_buffer_size: 500`, `bar_timestamp_convention: close`, `persist_historical_bars: true`.

### Agents — Built or Stubbed
- `agents/risk_manager.py` — `KillSwitch` class with config-driven limits, `check()` returning False (stub), `trigger()`, `reset()`. Full logic Phase 6.
- `agents/market_data_agent.py` — **BUILT** (Phase 2). See above.
- All other agents are stubs (Phase 3+): `session_clock_agent`, `news_scraper_agent`, `sentiment_agent`, `smt_agent`, `validation_gate`, `execution_agent`, `audit_agent`, `chart_agent`.

### Models — All Stubbed
`models/base_model.py`, `silver_bullet.py`, `ifvg_smt.py`, `power_of_three.py`, `news_catalyst.py` — all stubs. Built in Phases 4 and 10.

### Dashboard — All Stubbed
`dashboard/{app,layout,charts,overlays,callbacks}.py` — all stubs. Built in Phase 9.

### Prompts
- `prompts/validation_prompt.txt` — Claude AI quality gate prompt. Quality scoring (judgment), three dimensions (displacement, sweep, environment), bar windows for 1m and 5m, sister SMT context, JSON-only response. APPROVE rule: avg ≥ 3.5 AND no dimension = 1.
- `prompts/sentiment_prompt.txt` — empty stub for Phase 3.

### Main Entry Point
- `main.py` — argparse with `--profile`, `--market`, `--dry-run`, `--interactive`. Validates `traded_instrument` in {ES,NQ,YM} and not in `context_instruments`. Prints config summary with traded instrument prominent. Initializes DatabaseManager, KillSwitch, IBKRClient. Logs STARTUP and SHUTDOWN events. Prints `APEX SYSTEM READY — TRADING {ti}`.

### Testing Infrastructure
- `pytest.ini` with `asyncio_mode = auto`
- `conftest.py` registers asyncio marker
- 41 tests across 8 files, all passing
- Tests verify: all 9 tables created, bar buffer eviction and thread safety, bar normalization (open→close time), gap detection, historical bar insert/dedup, IBKR live port guard, dry-run mode, kill switch state machine, signal dataclass fields, dashboard imports, SMT agent imports

### Project Hygiene
- `.env.template` with ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IBKR_ACCOUNT_ID
- `.gitignore` excluding `.env`, `data/*.db*`, `logs/*.log*`, `__pycache__/`, IDE files
- `requirements.txt` with ib_insync, aiosqlite, PyYAML, anthropic, dash, plotly, pytest, pytest-asyncio, etc.
- `CLAUDE.md` defining project rules of engagement
- Git history: clean commits, descriptive messages

---

## What's Verified Working

Verified by running pytest (41/41):
- DB schema creates cleanly (all 9 tables including historical_bars)
- BarBuffer ring buffer eviction, thread safety, field validation
- Bar normalization: IBKR open time → close time UTC ISO 8601
- Gap detection logs correctly, does not fill gaps
- Historical bar bulk insert with duplicate suppression
- SignalCandidate dataclass instantiates with v1.3 field set
- IBKR live-port guard raises in not-live mode
- Dry-run skips IBKR and MarketDataAgent
- KillSwitch state machine works
- All stubs are importable

**Smoke tested by user:** `python main.py` ran successfully on Windows box (paper mode, expected IBKR connection error since TWS not running).

---

## What's Deliberately Not Built Yet

These are correctly stubbed per the phased build discipline. Do not implement until their phase begins.

| Component | Phase |
|---|---|
| Session clock window logic | 3 |
| Kill zone cutoff enforcement | 3 |
| News scraping + impact filter | 3 |
| FVG / OB / MSS / sweep / bias detection algorithms | 4 |
| SMT divergence detection | 4 |
| Silver Bullet model logic | 4 |
| Claude API call + quality gate | 5 |
| KillSwitch.check() full logic + shared instance wiring | 6 |
| IBKR bracket order placement | 7 |
| Telegram alerts | 8 |
| Plotly Dash chart UI | 9 |
| Models 2, 3, 4 | 10 |
| Live trading mode validation | 11 |

---

## Important Architectural Decisions Already Made

These are **non-negotiable**. See `CLAUDE.md` for the full list. Highlights:

1. **Single-instrument trading.** One `traded_instrument` per run. Two `context_instruments` for SMT and correlation. Field name is always `traded_instrument`, never `market` or `markets`.
2. **Three-timeframe bias chain.** `[240, 60, 15]`. 5m and 3m are FVG-detection-only.
3. **R:R is intentionally 1:1 for validation phase.** Will widen to 2:1 / 3:1 / pyramiding only after entry quality is proven over a meaningful sample.
4. **AI gate is quality scoring, not rule rechecking.** Three dimensions (displacement, sweep, environment) on 1–5 scale. Hard 2s timeout. REJECT-on-timeout.
5. **SMT divergence is a context warning, not a hard reject.** Flows into the AI gate's environment score.
6. **CL (Crude Oil) is removed.** Index futures only.
7. **UTC in DB. America/New_York at agent and display layers.**
8. **Async throughout** — aiosqlite + ib_insync.
9. **Live port 7496 guarded** — `IBKRClient.connect()` raises if `mode != 'live'`.

---

## Phase 3 Preview — What Comes Next

Phase 3 builds the **session clock agent** and **news scraper agent**. Scope:

- Session clock: window open/close logic for LONDON, NY_AM, NY_PM in America/New_York. Kill zone cutoff enforcement (`signal_cutoff_minutes_before_kz_close`). US market holiday calendar.
- News scraper: fetch economic calendar from 2–3 sources (user to decide sources — see B-202). Parse high-impact events. `news_window_minutes` blackout enforcement. Write to `news_events` table.

**Phase 3 must be specified in detail before Claude Code starts.** Author `APEX_Phase3_ClaudeCode_Spec.md` following the same structure as Phase 1 and Phase 2 specs.

### Open Decision Before Phase 3 Spec
- **B-202** — News scraper sources: user must choose 2–3 sources (Reuters, Bloomberg, ForexFactory, Investing.com economic calendar). Decide before Phase 3 spec is authored.

---

## How to Resume Work

1. Read `SESSION_HANDOFF.md` first.
2. Read `CLAUDE.md` for the rules of engagement.
3. Read this file (`PROJECT_STATE.md`) for current state.
4. Read `BACKLOG.md` for known issues and deferred items.
5. The two spec docs (`APEX_System_Whiteboard.md`, `APEX_Phase1_ClaudeCode_Spec.md`) are source of truth for what's already designed.
6. To start Phase 2, the next step is authoring `APEX_Phase2_ClaudeCode_Spec.md` — not pasting to Claude Code yet.
