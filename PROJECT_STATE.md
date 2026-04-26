# PROJECT_STATE.md
**Current build state for APEX. Updated when phase status changes.**
**Last updated: April 26, 2026 | Spec version: v1.3 | Phase 1 complete**

---

## Current Phase

**Phase 1 — Foundation: COMPLETE and AUDITED.**
**Phase 2 — Market Data Agent: NOT STARTED. Awaiting user go-ahead.**

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

### Agents — Built or Stubbed
- `agents/risk_manager.py` — `KillSwitch` class with config-driven limits, `check()` returning False (stub), `trigger()`, `reset()`. Full logic Phase 6.
- All other agents are stubs (Phase 2+): `market_data_agent`, `session_clock_agent`, `news_scraper_agent`, `sentiment_agent`, `smt_agent`, `validation_gate`, `execution_agent`, `audit_agent`, `chart_agent`.

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
- 25 tests across 6 files, all passing in 0.67s
- Tests verify: all 8 tables created, signal columns including SMT/AI gate fields, IBKR live port guard, dry-run mode, kill switch state machine, signal dataclass fields, dashboard imports, SMT agent imports

### Project Hygiene
- `.env.template` with ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IBKR_ACCOUNT_ID
- `.gitignore` excluding `.env`, `data/*.db*`, `logs/*.log*`, `__pycache__/`, IDE files
- `requirements.txt` with ib_insync, aiosqlite, PyYAML, anthropic, dash, plotly, pytest, pytest-asyncio, etc.
- `CLAUDE.md` defining project rules of engagement
- Git history: clean commits, descriptive messages

---

## What's Verified Working

Verified by running pytest:
- DB schema creates cleanly (all 8 tables)
- SignalCandidate dataclass instantiates with v1.3 field set
- IBKR live-port guard raises in not-live mode
- Dry-run skips IBKR connection
- KillSwitch state machine works
- All stubs are importable

**Not yet smoke-tested by user:** `python main.py --dry-run` — actually running the CLI end-to-end on a real machine. Recommended before Phase 2 starts.

---

## What's Deliberately Not Built Yet

These are correctly stubbed per the phased build discipline. Do not implement until their phase begins.

| Component | Phase |
|---|---|
| IBKR bar streaming | 2 |
| Session clock window logic | 2 |
| Kill zone cutoff enforcement | 3 |
| News scraping + impact filter | 3 |
| FVG / OB / MSS / sweep / bias detection algorithms | 4 |
| SMT divergence detection | 4 |
| Silver Bullet model logic | 4 |
| Claude API call + quality gate | 5 |
| KillSwitch.check() full logic | 6 |
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

## Phase 2 Preview — What Comes Next

Phase 2 builds the **market data agent**. Scope:

- IBKR connection acquires three Contract objects (traded instrument + 2 context instruments) — front-month continuous futures
- `reqRealTimeBars()` or `reqHistoricalData()` with `keepUpToDate=True` for each of 6 timeframes per instrument = 18 streams
- Bar normalization: every bar timestamped UTC, written to in-memory bar buffer
- Bar buffer persistence to SQLite (or in-memory only — Phase 2 design decision)
- Gap handling: detect missing bars, log warning, do not silently fill
- Session boundary handling: Globex hours (Sunday 18:00 ET to Friday 17:00 ET, with daily 17:00-18:00 break)
- Reconnect resilience: if TWS drops, retry per `ibkr.reconnect_attempts`, log every reconnection event

**Phase 2 must be specified in detail before Claude Code starts.** The current spec only outlines the agent at high level. A `APEX_Phase2_ClaudeCode_Spec.md` file should be authored before Phase 2 begins, mirroring the structure and rigor of the Phase 1 spec.

---

## How to Resume Work

1. Read `SESSION_HANDOFF.md` first.
2. Read `CLAUDE.md` for the rules of engagement.
3. Read this file (`PROJECT_STATE.md`) for current state.
4. Read `BACKLOG.md` for known issues and deferred items.
5. The two spec docs (`APEX_System_Whiteboard.md`, `APEX_Phase1_ClaudeCode_Spec.md`) are source of truth for what's already designed.
6. To start Phase 2, the next step is authoring `APEX_Phase2_ClaudeCode_Spec.md` — not pasting to Claude Code yet.
