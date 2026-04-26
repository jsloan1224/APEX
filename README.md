# APEX — Autonomous Predictive Execution System

Fully autonomous ICT futures trading system. Trades **one instrument per run** (ES, NQ, or YM) on Interactive Brokers using Inner Circle Trader methodology, with deterministic rules in Python and a Claude AI quality gate for setup judgment.

**Status:** Phase 1 (Foundation) complete. Phase 2 (Market Data Agent) not yet started.

---

## What APEX Does

1. Streams bar data from IBKR for one **traded instrument** plus two **context instruments** (read-only — used for SMT divergence and correlation, never receive orders).
2. Runs an MTF bias chain on `[4H, 1H, 15m]` — all three must agree for any signal to proceed.
3. Detects FVGs (Fair Value Gaps) on all six timeframes `[4H, 1H, 15m, 5m, 3m, 1m]`. Entries trigger on 1m FVG first-touch.
4. Confirms ICT setup conditions: liquidity sweep, MSS (market structure shift), FVG identification, kill-zone window.
5. Computes SMT divergence vs sister instruments — passed to AI gate as quality context.
6. Submits the candidate to a Claude Haiku 4.5 quality gate that scores three dimensions (displacement quality, sweep decisiveness, environment) on 1–5. APPROVE only if average ≥ 3.5 with no dimension scoring 1.
7. Applies hard risk rules (daily loss cap, drawdown, cool-off, max consecutive losses, news window).
8. Routes IBKR bracket orders on the traded instrument only.
9. Logs every signal, gate score, and trade outcome to SQLite for post-trade analysis.
10. Displays a real-time ICT chart dashboard at `localhost:8050`.

Mode starts as **paper**. Live trading is guarded behind an explicit `mode: live` config flag plus port 7496 check.

---

## Documents in This Repo

| File | Purpose |
|---|---|
| `APEX_System_Whiteboard.md` | Full system design — architecture, models, signal flow, schema |
| `APEX_Phase1_ClaudeCode_Spec.md` | Phase 1 build instructions for Claude Code (foundation only) |
| `CLAUDE.md` | Project rules of engagement — read by every Claude session |
| `PROJECT_STATE.md` | Current build state — what's done, what's stubbed, what's next |
| `BACKLOG.md` | Open issues, deferred decisions, known limitations |
| `SESSION_HANDOFF.md` | Bootstrap doc for new chat sessions |
| `BOOTSTRAP_TEMPLATE.md` | What to paste into your claude.ai project bootstrap field |
| `README.md` | This file |

If you're starting a new chat session, point Claude at `SESSION_HANDOFF.md` first.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Smoke test (no IBKR connection needed)
python main.py --dry-run --profile paper_default

# Switch instruments via CLI
python main.py --dry-run --market NQ
python main.py --dry-run --market YM

# Run tests
pytest -v
```

---

## Tech Stack

- Python 3.11+, asyncio throughout
- IBKR via `ib_insync` (paper port 7497, live port 7496)
- SQLite via `aiosqlite`
- Anthropic Claude API — Haiku 4.5 for the quality gate
- Plotly Dash for the dashboard (Phase 9)
- pytest + pytest-asyncio for tests
- Implementation done with Claude Code

---

## Build Phases

| Phase | Scope | Status |
|---|---|---|
| 1 | Foundation: scaffold, config, DB, IBKR, kill switch, logger, CLI, tests | ✅ Complete |
| 2 | Market data agent — bar streaming, 3 instruments × 6 timeframes | ⏸ Not started |
| 3 | Session clock + news scraper + cutoff window | ⏸ |
| 4 | Model 1 Silver Bullet + SMT detection | ⏸ |
| 5 | AI quality gate — Claude Haiku 4.5 | ⏸ |
| 6 | Risk manager full logic | ⏸ |
| 7 | Execution engine — IBKR bracket orders | ⏸ |
| 8 | Audit agent — Telegram alerts | ⏸ |
| 9 | ICT chart dashboard — Plotly Dash | ⏸ |
| 10 | Models 2–4: IFVG+SMT, Power of Three, News Catalyst | ⏸ |
| 11 | Live transition | ⏸ |

See `PROJECT_STATE.md` for current detail.
