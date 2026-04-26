# APEX — Autonomous Predictive Execution System
## System Whiteboard
**Version 1.2 | ICT Chart View + 3m/5m Timeframes | April 2026**

---

## 1. System Overview

APEX is a fully autonomous futures trading system built on ICT (Inner Circle Trader) methodology. It trades ES, NQ, and YM futures via Interactive Brokers. Every signal passes through an AI validation gate (Claude API) before execution. A real-time ICT chart dashboard provides full visual monitoring of price structure, liquidity levels, FVGs across all timeframes, and system status.

| Attribute | Value |
|---|---|
| Broker | Interactive Brokers (IBKR) via ib_insync |
| Data Feed | IBKR market data (paper account — CME futures) |
| Markets | ES, NQ, YM |
| Methodology | ICT — Inner Circle Trader |
| Language | Python |
| Chart Dashboard | Browser-based real-time ICT chart (Plotly Dash) |
| Database | SQLite |
| Alerts | Telegram |
| AI Validation | Claude API — hard gate, not advisory |
| Starting Mode | Paper trading (port 7497) |
| Config | config.yaml — CLI-driven, no code changes needed |

---

## 2. Six-Layer Architecture

| Layer | Name | Responsibility |
|---|---|---|
| 1 | Agent Layer | Market data, news, sentiment, session clock |
| 2 | Signal Engine | Five ICT trade models detect and score setups |
| 3 | AI Validation Gate | Claude API validates every signal — hard gate |
| 4 | Risk Manager | Hard kill switch rules — non-negotiable |
| 5 | Execution Engine | IBKR bracket orders with SL and TP |
| 6 | Audit & Feedback | SQLite logging, Telegram alerts, chart dashboard |

---

## 3. Multi-Timeframe Bias Chain

APEX evaluates directional bias top-down across a configurable chain of timeframes before any signal is eligible. All timeframes must agree on direction. A single conflict invalidates the setup. The 3m and 5m timeframes are included for granular FVG detection between the 1m execution chart and the 15m bias chart.

| Timeframe | Role |
|---|---|
| 4H (240 min) | Macro trend — premium/discount zones, major swing structure |
| 1H (60 min) | Intermediate structure — order blocks, swing highs/lows |
| 15m | Entry bias — immediate directional context |
| 5m | Granular FVG detection — bridge between 15m and 1m |
| 3m | Granular FVG detection — fine structure confirmation |
| 1m (execution) | Entry timing — FVG first-touch entry |

**Rules:**
- All timeframes in `bias_timeframes[]` must return BULLISH or BEARISH in the same direction
- If ANY timeframe returns NEUTRAL or conflicts → discard setup (`MTF_BIAS_CONFLICT`)
- Bias check is Step 0 — no further signal logic runs if alignment fails
- FVGs are tracked and plotted on ALL timeframes including 3m and 5m

```yaml
# config.yaml
profiles:
  paper_default:
    bias_timeframes: [240, 60, 15, 5, 3]   # 4H -> 1H -> 15m -> 5m -> 3m
    execution_timeframe: 1                   # 1m entry chart

  conservative:
    bias_timeframes: [60, 15, 5]
    execution_timeframe: 1

  aggressive:
    bias_timeframes: [240, 60, 15, 5, 3]
    execution_timeframe: 1
```

---

## 4. ICT Chart Dashboard

A browser-based real-time dashboard runs locally alongside APEX. Monitoring tool only — no trading from the chart. Built with Plotly Dash, updated via websocket as APEX processes each bar. Runs at `localhost:8050`.

### Chart Panel — Price Structure

| Element | Detail |
|---|---|
| Candlestick charts | All bias timeframes visible: 4H, 1H, 15m, 5m, 3m, 1m |
| Swing highs / lows | Marked on every active timeframe |
| BOS / CHOCH | Break of structure and change of character labeled with arrows |
| Premium / Discount zones | Equilibrium line drawn — price position shown above/below |
| Equal highs / Equal lows | Highlighted as liquidity targets |

### Chart Panel — Liquidity

| Element | Detail |
|---|---|
| Buy side liquidity (BSL) | Previous day high, previous week high, equal highs — dotted lines |
| Sell side liquidity (SSL) | Previous day low, previous week low, equal lows — dotted lines |
| Liquidity swept | Level marked with X when price takes it out |
| Daily high / Daily low | Current day high and low updated in real time |
| Previous day high / low | Static reference lines for the session |

### Chart Panel — Fair Value Gaps

| Element | Detail |
|---|---|
| FVGs plotted on all timeframes | 4H, 1H, 15m, 5m, 3m, 1m — each color coded by timeframe |
| Unfilled FVGs | Remain visible as shaded boxes until price closes through them |
| Filled FVGs | Box outline remains, fill removed — historical reference |
| Inverse FVGs (IFVGs) | Marked separately in distinct color |
| FVG midpoint line | Dotted line at midpoint — APEX entry target for Silver Bullet |
| FVG size label | Tick count shown on each box |

### Chart Panel — Key Levels

| Level | Description |
|---|---|
| Midnight open | ICT key reference — horizontal line from 00:00 EST |
| New York open | 9:30 EST horizontal line |
| Previous day close | Carried forward as reference |
| Current day open | Updated at session start |
| Weekly open | Monday open reference |
| Session kill zones | London, NY AM, NY PM — shaded background on chart |

### Chart Panel — Signal Overlay

| Element | Detail |
|---|---|
| MSS arrow | Plotted on displacement candle when market structure shifts |
| FVG entry box | Active setup FVG highlighted in bright color |
| Entry line | Horizontal line at FVG midpoint entry price |
| Stop loss line | Horizontal line at SL level — red |
| Take profit line | Horizontal line at TP level — green |
| Bias labels | Per-timeframe bullish/bearish label shown on each chart |
| MTF alignment indicator | All-green badge when all timeframes agree |

### Status Panel (Right Side)

| Element | Detail |
|---|---|
| System status | READY / RUNNING / KILL SWITCH TRIGGERED — color coded |
| Active profile | Current config profile name |
| Kill switch status | Green = armed and watching / Red = triggered |
| Open position | Market, direction, entry price, current P&L |
| Daily P&L | Running total in USD |
| Win / Loss count | Session totals |
| Active kill zone | Which session window is currently open |

### Signal Log (Bottom Panel)

Live scrolling log of every setup evaluated. Columns: timestamp, market, direction, MTF alignment result, Claude API result, discard reason or execution confirmation.

### Dashboard Tech Stack

| Component | Technology |
|---|---|
| Framework | Plotly Dash (Python) |
| Charts | Plotly financial charts — candlesticks, annotations, shapes |
| Real-time updates | Dash websocket or dcc.Interval pushing from APEX |
| Layout | Multi-panel: charts left, status right, signal log bottom |
| Hosting | Local only — localhost:8050 |

---

## 5. Agent Layer

| Agent | Phase | Responsibility |
|---|---|---|
| market_data_agent | 2 | IBKR bar streaming — all bias_timeframes + execution_timeframe |
| session_clock_agent | 2 | Kill zone window management |
| news_scraper_agent | 3 | RSS + web crawling pre-trade filter |
| sentiment_agent | 3 | Claude API sentiment scoring |
| validation_gate | 5 | Claude API signal validation — hard gate |
| risk_manager | 6 | All hard risk rules + kill switch |
| execution_agent | 7 | IBKR bracket order routing |
| audit_agent | 8 | SQLite writes + Telegram alerts |
| chart_agent | 9 | Real-time ICT chart dashboard — Plotly Dash |

---

## 6. Five ICT Trade Models

| Model | Name | Summary |
|---|---|---|
| Model 1 (Primary) | ICT Silver Bullet FVG | Kill zone FVG entry on MSS + displacement. Full MTF bias chain. |
| Model 2 | IFVG + SMT Divergence | Inverse FVG with SMT divergence between correlated pairs. |
| Model 3 | Power of Three (PO3) | Accumulation → Manipulation → Distribution on session open. |
| Model 4 | CL Liquidity Sweep | Crude Oil stop hunt + reversal from key liquidity level. |
| Model 5 | News Catalyst + OB | High-impact news event + order block retest entry. |

### Model 1 — Silver Bullet Kill Zones

| Session | EST Window |
|---|---|
| London Kill Zone | 03:00 – 04:00 |
| New York AM | 10:00 – 11:00 |
| New York PM | 14:00 – 15:00 |

---

## 7. Signal Flow — Bar Close to Executed Order

| Step | Name | Action |
|---|---|---|
| 0 | MTF Bias Check | Fetch last closed bar for each timeframe [240,60,15,5,3]. All must agree or MTF_BIAS_CONFLICT. |
| 1 | Session Check | Confirm current time is within active kill zone. |
| 2 | Liquidity Sweep | Confirm recent sweep of buy-side or sell-side liquidity. |
| 3 | MSS | Market Structure Shift on displacement candle confirms direction. |
| 4 | FVG Identification | Identify valid FVG on 1m execution chart. |
| 5 | Tick Filter | Measure FVG — minimum 21-tick potential required. Discard if below. |
| 6 | Signal Candidate | Populate SignalCandidate dataclass with all fields. |
| 7 | AI Validation Gate | Submit to Claude API. Await APPROVE/REJECT. |
| 8 | Risk Check | Apply hard kill switch rules. Reject if any rule trips. |
| 9 | Order Execution | IBKR bracket: entry at FVG midpoint, SL 20 ticks, TP 21 ticks. |
| 10 | Chart Update | Push signal and order levels to ICT chart dashboard. |
| 11 | Audit Log | Write to SQLite. Push Telegram alert. |

---

## 8. Risk Engine — Hard Rules

> These rules are non-negotiable. No override. No exception.

| Rule | Condition |
|---|---|
| Daily Loss Cap | Stop all trading if daily P&L loss exceeds max_daily_loss_usd |
| Max Drawdown | Kill switch triggers if drawdown exceeds max_drawdown_usd |
| Cool-Off Period | No new trades for cool_off_minutes after a loss |
| News Window | No trades within news_window_minutes of high-impact news |
| Max Open Positions | Never exceed max_open_positions (default: 1) |
| Minimum Tick Potential | FVG must offer >= min_target_ticks. Hard discard if not. |
| MTF Bias Alignment | All bias_timeframes [240,60,15,5,3] must agree. Hard discard if not. |
| AI Gate | Claude API must return APPROVE. Any other result blocks execution. |
| Kill Zone Only | Signals only valid during active session kill zone windows |
| Paper Mode Guard | Live order routing blocked unless mode = live in config |

---

## 9. Claude AI Validation Gate

Hard gate — not advisory. Every signal must receive APPROVE before execution. Full ICT context and MTF bias chain sent with every request.

```
TRADE SETUP VALIDATION REQUEST

Market: {market} | Direction: {direction} | Model: {model_name}
Session: {session} | Kill Zone Active: {kill_zone_active}

MTF BIAS CHAIN:
  Timeframes: [240, 60, 15, 5, 3]
  Bias: {bias_per_timeframe}
  All aligned: {bias_alignment}
  RULE: If bias_alignment is False -> REJECT

KEY LEVELS:
  Previous day high: {prev_day_high} | Previous day low: {prev_day_low}
  Daily high: {daily_high} | Daily low: {daily_low}
  Midnight open: {midnight_open} | NY open: {ny_open}
  Liquidity swept: {liquidity_level} ({sweep_direction})

ENTRY PARAMETERS:
  Entry: {entry_price} | SL: {stop_loss_price} | TP: {take_profit_price}
  Stop ticks: {stop_ticks} | Target ticks: {target_ticks}
  FVG size ticks: {fvg_size_ticks} (min required: {min_target_ticks})
  RULE: If fvg_size_ticks < min_target_ticks -> REJECT

ICT CONFIRMATIONS:
  Liquidity swept: {liquidity_swept}
  MSS confirmed: {mss_confirmed}
  FVG identified: {fvg_identified}
  First touch: {fvg_first_touch}
  RULE: All four must be True to APPROVE

Respond ONLY with JSON: {"result": "APPROVE"|"REJECT", "reason": "one sentence"}
```

---

## 10. SQLite Database Schema

```sql
signal_candidates  -- every setup evaluated, MTF bias chain, ICT confirmations, outcome
trades             -- executed trades, entry/exit, P&L, duration
system_events      -- startup, shutdown, kill switch triggers, errors
news_events        -- scraped headlines, sentiment scores, impact ratings
performance_daily  -- daily P&L, win rate, avg R-multiple
key_levels         -- daily H/L, prev day H/L, midnight open, NY open (updated each session)
fvg_registry       -- all active FVGs across all timeframes, status (open/filled/invalidated)
```

> Two tables added in v1.2: `fvg_registry` tracks every FVG detected across all timeframes [240, 60, 15, 5, 3, 1]. `key_levels` updated at session start and in real time as new highs/lows form.

---

## 11. Project Folder Structure

```
apex/
├── main.py
├── config.yaml
├── .env.template
├── requirements.txt
├── README.md
│
├── agents/
│   ├── market_data_agent.py   # bar streaming — all configured timeframes
│   ├── session_clock_agent.py # kill zone management
│   ├── news_scraper_agent.py
│   ├── sentiment_agent.py
│   ├── validation_gate.py     # Claude API hard gate
│   ├── risk_manager.py        # kill switch + all hard rules
│   ├── execution_agent.py     # IBKR bracket orders
│   ├── audit_agent.py         # SQLite + Telegram
│   └── chart_agent.py         # ICT chart dashboard — Plotly Dash
│
├── models/
│   ├── base_model.py          # MTF bias check in base class
│   ├── silver_bullet.py       # Model 1
│   ├── ifvg_smt.py            # Model 2
│   ├── power_of_three.py      # Model 3
│   ├── cl_liquidity.py        # Model 4
│   └── news_catalyst.py       # Model 5
│
├── core/
│   ├── signal.py              # SignalCandidate dataclass
│   ├── indicators.py          # FVG, OB, MSS, sweep, bias detection
│   ├── ibkr_client.py         # IBKR connection wrapper
│   ├── claude_client.py       # Anthropic API wrapper
│   └── database.py            # SQLite manager
│
├── dashboard/
│   ├── app.py                 # Dash app entry point
│   ├── layout.py              # Panel layout definition
│   ├── charts.py              # Candlestick + ICT overlays
│   ├── overlays.py            # FVG boxes, liquidity lines, levels
│   └── callbacks.py           # Real-time update handlers
│
├── prompts/
│   ├── sentiment_prompt.txt
│   └── validation_prompt.txt  # Full ICT context + MTF chain
│
├── data/
│   └── apex.db
│
└── tests/
    ├── test_database.py
    ├── test_ibkr_connection.py
    ├── test_kill_switch.py
    ├── test_signal.py
    └── test_chart.py
```

---

## 12. Build Sequence

Phases are sequential. No phase begins until the previous phase passes Claude audit. Claude Code implements. Claude (design) audits after each phase.

| Phase | Scope | Audit Criteria |
|---|---|---|
| 1 | Foundation — scaffold, config, DB, IBKR, kill switch, CLI | Config loads, IBKR connects paper, DB initializes, all MTF fields present |
| 2 | Market data agent — bar streaming all timeframes [240,60,15,5,3,1] | Bars received for all 6 timeframes, timestamps correct, no gaps |
| 3 | Session clock — kill zone detection | Correct EST window activation for all three sessions |
| 4 | Model 1 Silver Bullet — full ICT logic with MTF bias chain | MTF check runs first, all ICT conditions validated, tick filter applied |
| 5 | AI validation gate — Claude API | Every signal sent to gate, APPROVE/REJECT parsed correctly |
| 6 | Risk manager — all hard rules enforced | Daily loss cap, drawdown, cool-off, news window all trigger |
| 7 | Execution engine — IBKR bracket orders | Brackets placed with correct SL/TP ticks, fills logged |
| 8 | Audit agent — SQLite + Telegram | All events written, Telegram alerts delivered |
| 9 | ICT Chart Dashboard — Plotly Dash | All chart elements render: FVGs on all TFs, liquidity, levels, signal overlay |
| 10 | Models 2-5 — remaining ICT models | Each model passes its own spec audit |
| 11 | Live transition | Paper to live reviewed and approved, monitored first week |

---

## 13. Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Broker / Data | Interactive Brokers — ib_insync (paper account) |
| AI Validation | Anthropic Claude API |
| Database | SQLite via aiosqlite |
| Chart Dashboard | Plotly Dash — localhost:8050 |
| Alerts | Telegram Bot API |
| Configuration | config.yaml — PyYAML |
| Testing | pytest + pytest-asyncio |
| Implementation Agent | Claude Code |
| Paper Trading Port | 7497 (IBKR TWS) |
| Live Trading Port | 7496 (IBKR TWS — guarded) |
