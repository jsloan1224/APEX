# APEX — Autonomous Predictive Execution System
## System Whiteboard
**Version 1.3 | Single-Instrument Trading + Quality-Gate AI | April 2026**

---

## 1. System Overview

APEX is a fully autonomous futures trading system built on ICT (Inner Circle Trader) methodology. It trades **one selectable instrument per run** — ES, NQ, or YM — via Interactive Brokers. The other two indices stream as read-only context for SMT divergence and correlation. Every signal passes through an AI quality gate (Claude API) that judges setup quality on dimensions deterministic rules cannot evaluate. A real-time ICT chart dashboard provides full visual monitoring.

| Attribute | Value |
|---|---|
| Broker | Interactive Brokers (IBKR) via ib_insync |
| Data Feed | IBKR market data (paper account — CME futures) |
| Tradeable Instruments | ES, NQ, or YM — one selected per run |
| Context Instruments | The other two indices — read-only, used for SMT and correlation |
| Methodology | ICT — Inner Circle Trader |
| Language | Python 3.11+ |
| Chart Dashboard | Browser-based real-time ICT chart (Plotly Dash) |
| Database | SQLite via aiosqlite |
| Alerts | Telegram |
| AI Quality Gate | Claude Haiku 4.5 — quality scoring, not rule rechecking |
| Starting Mode | Paper trading (port 7497) |
| Config | config.yaml — CLI-driven, no code changes needed |
| Initial R:R | 1:1 (validation phase) — configurable per instrument |

---

## 2. Six-Layer Architecture

| Layer | Name | Responsibility |
|---|---|---|
| 1 | Agent Layer | Market data (traded + context), session clock, news |
| 2 | Signal Engine | Four ICT trade models detect and score setups |
| 3 | AI Quality Gate | Claude API judges setup quality — not rule rechecking |
| 4 | Risk Manager | Hard rules — non-negotiable, kill switch, per-instrument sizing |
| 5 | Execution Engine | IBKR bracket orders on traded instrument only |
| 6 | Audit & Feedback | SQLite logging, Telegram alerts, chart dashboard |

---

## 3. Instrument Selection

### Single-Instrument Trading Rule

APEX trades **one and only one instrument per run.** Selected via:

1. CLI flag: `python main.py --market ES`
2. Or config: `traded_instrument: ES` in the active profile

Valid values: `ES`, `NQ`, `YM`. The remaining two are streamed as **context instruments** — used for SMT divergence and correlation reads, never receive orders.

### Why Single-Instrument

ES, NQ, and YM are heavily correlated intraday (~0.85+). Trading multiple correlated instruments concurrently is not diversification — it is concentration with the appearance of breadth. Single-instrument trading also simplifies risk math, eliminates "which signal fires first" race conditions, and makes performance attribution clean.

### Context Instrument Use

| Use | Description |
|---|---|
| SMT Divergence | If traded = ES long but NQ fails to make a higher high on same timeframe → bearish divergence. Flagged as quality warning. |
| Correlation Read | If both context instruments show clearly opposite bias on the bias chain, environment is choppy/uncertain. Flagged as quality warning. |
| Dashboard Display | Context instruments shown as smaller side panels with bias labels and SMT alerts highlighted |

SMT divergence and correlation conflict are **context warnings**, not hard rejects. They feed into the Claude quality gate's environment score.

---

## 4. Timeframe Roles — Corrected v1.3

The previous version conflated "FVG detection timeframe" with "bias timeframe." They are separate roles.

| Timeframe | Role |
|---|---|
| 4H (240) | **Bias** — macro trend, premium/discount zones, major swing structure |
| 1H (60) | **Bias** — intermediate structure, order blocks, swing highs/lows |
| 15m | **Bias** — entry bias, immediate directional context |
| 5m | **FVG detection only** — gap identification for 1m entry context |
| 3m | **FVG detection only** — fine-structure gap identification |
| 1m | **Execution** — FVG first-touch entry |

### Bias Chain Rules

- All three bias timeframes [240, 60, 15] must return BULLISH or BEARISH in the same direction
- If ANY bias timeframe returns NEUTRAL or conflicts → discard setup (`MTF_BIAS_CONFLICT`)
- Bias check is Step 0 — no further signal logic runs if alignment fails

### FVG Detection Rules

- FVGs detected and tracked on all six timeframes [240, 60, 15, 5, 3, 1]
- Higher-timeframe FVGs (4H, 1H, 15m) plotted on dashboard as context — price tends to react at these levels
- Mid-timeframe FVGs (5m, 3m) and execution-timeframe FVGs (1m) are entry candidates
- All FVGs logged to `fvg_registry` table with status (open / filled / invalidated)

```yaml
# config.yaml — applies to all profiles
bias_timeframes: [240, 60, 15]                    # bias chain — all must agree
fvg_detection_timeframes: [240, 60, 15, 5, 3, 1]  # FVGs tracked on all six
execution_timeframe: 1                              # 1m entry chart
smt_check_timeframes: [5, 1]                       # SMT divergence checked here
```

---

## 5. ICT Chart Dashboard

A browser-based real-time dashboard runs locally alongside APEX. Monitoring tool only — no trading from the chart. Built with Plotly Dash, updated via dcc.Interval polling. Runs at `localhost:8050`.

### Primary Chart — Traded Instrument

The traded instrument (ES, NQ, or YM) is the dashboard centerpiece — full multi-panel ICT view.

| Element | Detail |
|---|---|
| Candlestick charts | All timeframes visible: 4H, 1H, 15m, 5m, 3m, 1m |
| Swing highs / lows | Marked on every active timeframe |
| BOS / CHOCH | Break of structure and change of character labeled with arrows |
| Premium / Discount zones | Equilibrium line drawn — price position shown above/below |
| Equal highs / Equal lows | Highlighted as liquidity targets |

### Context Panels — Sister Instruments

The two non-traded instruments displayed as smaller side panels:

| Element | Detail |
|---|---|
| Bias label | Per-timeframe bullish/bearish/neutral indicator |
| SMT divergence alert | Highlighted when divergence vs traded instrument detected |
| Correlation indicator | Green when aligned with traded direction, red when opposing |

### Liquidity Layer (Traded Instrument)

| Element | Detail |
|---|---|
| Buy side liquidity (BSL) | Previous day high, previous week high, equal highs — dotted lines |
| Sell side liquidity (SSL) | Previous day low, previous week low, equal lows — dotted lines |
| Liquidity swept | Level marked with X when price takes it out |
| Daily high / Daily low | Current day high and low updated in real time |
| Previous day high / low | Static reference lines for the session |

### Fair Value Gaps (Traded Instrument)

| Element | Detail |
|---|---|
| FVGs plotted on all timeframes | 4H, 1H, 15m, 5m, 3m, 1m — color coded by timeframe |
| Unfilled FVGs | Shaded boxes until price closes through them |
| Filled FVGs | Box outline remains, fill removed — historical reference |
| Inverse FVGs (IFVGs) | Marked separately in distinct color |
| FVG midpoint line | Dotted line at midpoint — entry target for Silver Bullet |
| FVG size label | Tick count shown on each box |

### Key Levels

| Level | Description |
|---|---|
| Midnight open | ICT key reference — horizontal line from 00:00 EST |
| New York open | 09:30 EST horizontal line |
| Previous day close | Carried forward as reference |
| Current day open | Updated at session start |
| Weekly open | Monday open reference |
| Session kill zones | London, NY AM, NY PM — shaded background on chart |

### Signal Overlay

| Element | Detail |
|---|---|
| MSS arrow | Plotted on displacement candle when market structure shifts |
| FVG entry box | Active setup FVG highlighted in bright color |
| Entry line | Horizontal line at FVG midpoint entry price |
| Stop loss line | Horizontal line at SL level — red |
| Take profit line | Horizontal line at TP level — green |
| Bias labels | Per-timeframe bullish/bearish label shown on each chart |
| MTF alignment indicator | All-green badge when bias chain agrees |
| SMT divergence flag | Warning indicator when sister instrument diverges |

### Status Panel

| Element | Detail |
|---|---|
| System status | READY / RUNNING / KILL SWITCH TRIGGERED — color coded |
| Active profile | Current config profile name |
| Traded instrument | ES / NQ / YM — large display |
| Kill switch status | Green = armed and watching / Red = triggered |
| Open position | Direction, entry price, current P&L |
| Daily P&L | Running total in USD |
| Win / Loss count | Session totals |
| Active kill zone | Which session window is currently open |

### Signal Log

Live scrolling log of every setup evaluated. Columns: timestamp, instrument, direction, MTF alignment, SMT context, Claude quality scores, gate result, discard reason or execution confirmation.

### Dashboard Tech Stack

| Component | Technology |
|---|---|
| Framework | Plotly Dash (Python) |
| Charts | Plotly financial charts — candlesticks, annotations, shapes |
| Real-time updates | dcc.Interval polling APEX state every 1s |
| Layout | Multi-panel: traded instrument primary, context sisters secondary, status right, signal log bottom |
| Hosting | Local only — localhost:8050 |

---

## 6. Agent Layer

| Agent | Phase | Responsibility |
|---|---|---|
| market_data_agent | 2 | IBKR bar streaming — traded + 2 context instruments, all bias + FVG timeframes |
| session_clock_agent | 2 | Kill zone window management |
| news_scraper_agent | 3 | RSS + web crawling pre-trade filter |
| sentiment_agent | 3 | Claude API sentiment scoring |
| smt_agent | 4 | SMT divergence detection across context instruments |
| validation_gate | 5 | Claude API quality gate — judgment, not rule checking |
| risk_manager | 6 | All hard risk rules + kill switch |
| execution_agent | 7 | IBKR bracket order routing — traded instrument only |
| audit_agent | 8 | SQLite writes + Telegram alerts |
| chart_agent | 9 | Real-time ICT chart dashboard — Plotly Dash |

---

## 7. Four ICT Trade Models

| Model | Name | Summary |
|---|---|---|
| Model 1 (Primary) | ICT Silver Bullet FVG | Kill zone FVG entry on MSS + displacement. Full bias chain + SMT context. |
| Model 2 | IFVG + SMT Divergence | Inverse FVG entry confirmed by SMT divergence between traded and sister instrument. |
| Model 3 | Power of Three (PO3) | Accumulation → Manipulation → Distribution on session open. |
| Model 4 | News Catalyst + OB | High-impact news event + order block retest entry. |

> **Note:** v1.2 included a Model 4 "CL Liquidity Sweep" for crude oil. Removed in v1.3 — APEX trades index futures only.

### Model 1 — Silver Bullet Kill Zones

| Session | EST Window |
|---|---|
| London Kill Zone | 03:00 – 04:00 |
| New York AM | 10:00 – 11:00 |
| New York PM | 14:00 – 15:00 |

### Signal Cutoff

No new entries in the final 15 minutes of any kill zone (`signal_cutoff_minutes_before_kz_close: 15`). Setups generated late in a kill zone do not have time to develop before the window closes.

---

## 8. Signal Flow — Bar Close to Executed Order

| Step | Name | Action |
|---|---|---|
| 0 | Bias Chain Check | Fetch last closed bar for [240, 60, 15] on traded instrument. All three must agree or `MTF_BIAS_CONFLICT`. |
| 1 | Session Check | Confirm current time is within active kill zone and not in cutoff window. |
| 2 | Liquidity Sweep | Confirm recent sweep of buy-side or sell-side liquidity on traded instrument. |
| 3 | MSS | Market Structure Shift on displacement candle confirms direction. |
| 3.5 | SMT Context Read | Compute SMT divergence vs both sister instruments on `smt_check_timeframes`. Result attached to candidate (not gate). |
| 4 | FVG Identification | Identify valid FVG on 1m execution chart (or 3m/5m if model specifies). |
| 5 | Filters | FVG size ≥ `min_fvg_size_ticks`, target distance ≥ `min_target_ticks`. |
| 6 | Signal Candidate | Populate SignalCandidate with all fields including bar windows for AI gate. |
| 7 | AI Quality Gate | Submit to Claude Haiku 4.5 — quality scoring. APPROVE or REJECT with reason. |
| 8 | Risk Check | Apply hard risk rules (kill switch, daily loss, drawdown, cool-off, news window). |
| 9 | Order Execution | IBKR bracket on traded instrument: entry at FVG midpoint, SL/TP per `instrument_params`. |
| 10 | Chart Update | Push signal and order levels to dashboard. |
| 11 | Audit Log | Write to SQLite. Push Telegram alert. |

---

## 9. Risk Engine — Hard Rules

> Non-negotiable. No override. No exception.

| Rule | Condition |
|---|---|
| Daily Loss Cap | Stop all trading if daily P&L loss exceeds `max_daily_loss_usd` |
| Max Drawdown | Kill switch triggers if drawdown exceeds `max_drawdown_usd` |
| Max Consecutive Losses | Stop trading for the day after `max_consecutive_losses` losing trades |
| Cool-Off Period | No new trades for `cool_off_minutes` after a loss |
| News Window | No trades within `news_window_minutes` of high-impact news |
| Max Open Positions | 1 — single instrument, single position |
| Min FVG Size | FVG must be ≥ `min_fvg_size_ticks`. Hard discard if not. |
| Min Target Distance | Target distance must be ≥ `min_target_ticks`. Hard discard if not. |
| Bias Chain Alignment | All three bias timeframes [240, 60, 15] must agree. Hard discard if not. |
| Kill Zone Only | Signals only valid during active kill zone, before cutoff window |
| AI Quality Gate | Claude Haiku 4.5 must return APPROVE. REJECT or timeout blocks execution. |
| Paper Mode Guard | Live order routing blocked unless `mode == 'live'` in config |

### Risk Manager Per-Instrument

Each instrument has its own trade parameters (`instrument_params.<symbol>`):
- `contracts` — position size
- `stop_ticks` — stop loss distance
- `target_ticks` — take profit distance
- `min_target_ticks` — minimum acceptable target distance (R:R floor)
- `min_fvg_size_ticks` — minimum FVG gap size for entry

This structure supports flat sizing today and per-instrument scaling / pyramiding later without code changes.

---

## 10. Claude AI Quality Gate

The gate's job is **judgment, not rule checking.** All deterministic rules are enforced in `risk_manager.py` before the candidate reaches the gate. Only candidates that have already passed every mechanical filter are sent to Claude.

The gate scores three quality dimensions and returns APPROVE / REJECT.

### Gate Configuration

| Setting | Value |
|---|---|
| Model | `claude-haiku-4-5-20251001` |
| Temperature | 0 |
| Max output tokens | 200 |
| Hard timeout | 2.0 seconds |
| On timeout | REJECT, log `AI_GATE_TIMEOUT` |
| On API error | REJECT, log `AI_GATE_ERROR` |

### Quality Scoring Prompt

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
  Liquidity swept: {liquidity_level} ({sweep_direction}) at {sweep_time}
  MSS displacement bar index: {mss_bar_index}

SISTER INSTRUMENT CONTEXT (read-only):
  {sister_1}: bias {sister_1_bias}, SMT divergence vs traded: {smt_1}
  {sister_2}: bias {sister_2_bias}, SMT divergence vs traded: {smt_2}

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

### Why This Gate Earns Its Cost

- The bar windows give Claude actual price action to evaluate, not just numeric labels
- Quality dimensions are judgment-based — they cannot be cleanly written as if/else rules
- SMT context flows in here as a quality factor, not a hard reject — preserving optionality
- Gate output (scores + reason) is logged for post-trade review of which dimensions correlate with profitable trades

---

## 11. SQLite Database Schema

```sql
signal_candidates  -- every setup evaluated, bias chain, ICT confirmations,
                   -- SMT context, AI gate scores, outcome
trades             -- executed trades, entry/exit, P&L, duration
system_events      -- startup, shutdown, kill switch triggers, errors,
                   -- AI gate timeouts/errors
news_events        -- scraped headlines, sentiment scores, impact ratings
performance_daily  -- daily P&L, win rate, avg R-multiple, by instrument
key_levels         -- daily H/L, prev day H/L, midnight open, NY open,
                   -- per instrument
fvg_registry       -- all active FVGs across all timeframes and instruments,
                   -- status (open/filled/invalidated), is_traded flag
smt_events         -- SMT divergence detections across instrument pairs
```

> All timestamps stored as UTC ISO 8601. Conversion to America/New_York is done at the agent layer for session-window math and at the dashboard layer for display.

---

## 12. Project Folder Structure

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
│   ├── market_data_agent.py    # bar streaming — traded + context instruments
│   ├── session_clock_agent.py  # kill zone management + cutoff window
│   ├── news_scraper_agent.py
│   ├── sentiment_agent.py
│   ├── smt_agent.py            # SMT divergence detection
│   ├── validation_gate.py      # Claude quality gate
│   ├── risk_manager.py         # kill switch + all hard rules
│   ├── execution_agent.py      # IBKR bracket orders
│   ├── audit_agent.py          # SQLite + Telegram
│   └── chart_agent.py          # ICT chart dashboard — Plotly Dash
│
├── models/
│   ├── base_model.py           # bias chain check in base class
│   ├── silver_bullet.py        # Model 1
│   ├── ifvg_smt.py             # Model 2
│   ├── power_of_three.py       # Model 3
│   └── news_catalyst.py        # Model 4
│
├── core/
│   ├── signal.py               # SignalCandidate dataclass
│   ├── indicators.py           # FVG, OB, MSS, sweep, bias detection
│   ├── ibkr_client.py          # IBKR connection wrapper
│   ├── claude_client.py        # Anthropic API wrapper
│   ├── database.py             # SQLite manager (aiosqlite, async)
│   └── logger.py               # File + console logging configuration
│
├── dashboard/
│   ├── app.py                  # Dash app entry point
│   ├── layout.py               # Panel layout — primary + context sisters
│   ├── charts.py               # Candlestick + ICT overlays
│   ├── overlays.py             # FVG boxes, liquidity lines, levels
│   └── callbacks.py            # Real-time update handlers
│
├── prompts/
│   ├── sentiment_prompt.txt
│   └── validation_prompt.txt   # Quality scoring (judgment, not rules)
│
├── data/
│   └── apex.db
│
├── logs/
│   └── apex.log
│
└── tests/
    ├── test_database.py
    ├── test_ibkr_connection.py
    ├── test_kill_switch.py
    ├── test_signal.py
    ├── test_smt.py
    └── test_chart.py
```

---

## 13. Build Sequence

Phases are sequential. No phase begins until the previous phase passes design audit.

| Phase | Scope | Audit Criteria |
|---|---|---|
| 1 | Foundation — scaffold, config, DB, IBKR, kill switch, CLI, logger | Config loads, IBKR connects paper, DB initializes all 8 tables, instrument selection works, all tests pass |
| 2 | Market data agent — bar streaming traded + context instruments, all timeframes | Bars received for 3 instruments × 6 timeframes, timestamps UTC, no gaps |
| 3 | Session clock + news scraper | Correct EST window activation for all three sessions, cutoff window enforced, news pre-trade filter functional |
| 4 | Model 1 Silver Bullet + SMT detection | Bias chain check runs first, SMT divergence computed and logged, all ICT conditions validated |
| 5 | AI quality gate — Claude Haiku 4.5 | Bar windows sent to Claude, quality scores parsed, timeout fallback works, all gate events logged |
| 6 | Risk manager — all hard rules enforced | Daily loss cap, drawdown, cool-off, news window, max consecutive losses all trigger |
| 7 | Execution engine — IBKR bracket orders | Brackets placed on traded instrument with per-instrument SL/TP, fills logged |
| 8 | Audit agent — SQLite + Telegram | All events written, Telegram alerts delivered, AI gate scores logged |
| 9 | ICT Chart Dashboard — Plotly Dash | Primary instrument full chart, context sisters as side panels, SMT alerts visible, signal overlay live |
| 10 | Models 2-4 — remaining ICT models | Each model passes its own spec audit |
| 11 | Live transition | Paper to live reviewed and approved, monitored first week |

---

## 14. Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Async | asyncio throughout — aiosqlite + ib_insync are event-loop-based |
| Broker / Data | Interactive Brokers — ib_insync (paper account) |
| AI Quality Gate | Anthropic Claude API — Haiku 4.5 |
| Database | SQLite via aiosqlite |
| Chart Dashboard | Plotly Dash — localhost:8050 |
| Alerts | Telegram Bot API |
| Configuration | config.yaml — PyYAML |
| Logging | Python logging — file + console, rotating |
| Testing | pytest + pytest-asyncio |
| Implementation Agent | Claude Code |
| Paper Trading Port | 7497 (IBKR TWS) |
| Live Trading Port | 7496 (IBKR TWS — guarded) |

---

## 15. Operational Notes

### Validation Phase R:R

Initial R:R is **1:1** (stop_ticks = target_ticks = 20 across all instruments). This is intentional — the goal of the first 50–100 trades is to validate that entries are real signals, not to maximize per-trade profit. Tight symmetric R:R is a more honest test of entry quality than wider asymmetric R:R, which lets bad entries hide behind occasional large winners.

Once the system has produced a meaningful sample with stable win rate, the upgrade path is:
1. Widen targets — 1:2 or 1:3 R:R on proven setups
2. Pyramid — add contracts on confirmation, scale out at multiple targets
3. Per-instrument tuning — different R:R per market based on observed behavior

All of this is enabled by the `instrument_params` config structure. No code changes required.

### Timezone Policy

- All internal storage and computation: **UTC** (ISO 8601 in SQLite)
- Session windows and kill zones: **America/New_York** (converted at agent layer)
- Dashboard display: **America/New_York** (converted at presentation layer)
- IBKR bar timestamps: arrive as UTC, stored as UTC

### IBKR Disconnect Handling

If TWS drops mid-trade, `ib_insync` raises a connection event. APEX behavior:
1. Log `IBKR_DISCONNECT` to system_events with current open position state
2. Trip kill switch — no new orders until reconnect confirmed
3. Telegram alert sent
4. Reconnect attempts per `ibkr.reconnect_attempts` and `ibkr.reconnect_delay`
5. Open positions remain at IBKR — APEX does not attempt emergency close (TWS bracket is the safety net)

This is acknowledged in the spec; full implementation lands in Phase 7.
