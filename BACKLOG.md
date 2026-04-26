# BACKLOG.md
**Open issues, deferred decisions, known limitations, technical debt.**
**Last updated: April 26, 2026**

This is the running list of things that are known but not blocking. New items added at the top of each section. When an item is resolved, move it to "Resolved" at the bottom of the file.

---

## Open Decisions (need user input before relevant phase)

> **Phase 2 spec authoring is blocked on B-001, B-004, and B-005.** These three need user resolution before the Phase 2 spec can be drafted.

### B-001 — Bar buffer persistence strategy (Phase 2) — **BLOCKER**
**Question:** Should the in-memory bar buffer also persist to SQLite, or stay memory-only?
**Tradeoff:**
- Memory-only: simpler, faster, but lose all bars on restart — must re-request historical bars on every startup
- Persistent: durability, easier post-mortem analysis, but writes-per-second scale up significantly (3 instruments × 6 timeframes = potentially 18 writes per minute on 1m bars alone)
**Recommendation:** memory-only for the live ring buffer (last N bars per timeframe, where N is enough for indicator computation), with a separate `historical_bars` table that captures only completed-session data for backtest / replay. Decide before Phase 2 spec is authored.

### B-002 — Phase 2 spec authoring approach
**Question:** Author Phase 2 spec from scratch, or fork it from the Phase 1 spec template?
**Recommendation:** Fork the structure (preamble, build instructions, audit checklist) but write fresh content. Phase 2 is fundamentally different in nature — it's a runtime data pipeline, not a static foundation. Trying to mirror Phase 1's section breakdown one-to-one will be awkward.

### B-003 — Smoke test before Phase 2
**Question:** Run `python main.py --dry-run` once on the user's Windows box before starting Phase 2?
**Recommendation:** Yes. Tests verify the parts; a smoke test verifies they wire together. 30 seconds of effort, catches integration issues that pytest can't.

### B-004 — IBKR contract resolution — **BLOCKER**
**Question:** How do we resolve "ES" to a specific futures contract? IBKR requires a Contract object with symbol, secType, exchange, currency, and either expiry or continuous-front specification.
**Note:** Front-month rolls every quarter (Mar/Jun/Sep/Dec). System needs to either:
- Track current front-month symbol manually in config (e.g., `ES_CURRENT_CONTRACT: ESM6`)
- Use `reqContractDetails()` to discover front-month dynamically each session
- Use IBKR's continuous futures symbol if available
**Recommendation:** Dynamic resolution at session start via `reqContractDetails`. Cache for the session. Specify in Phase 2 spec.

### B-005 — Bar timestamp convention from IBKR — **BLOCKER**
**Question:** IBKR returns bars where timestamp = bar OPEN time. ICT methodology typically references bar CLOSE. Pick one and document it.
**Recommendation:** Convert to bar-close timestamps internally. Document in `core/database.py` schema comments. Most ICT software uses close timestamps and the user is likely operating mentally in that frame.

### B-006 — Validation prompt instrument-specific tuning
**Question:** Does the AI gate prompt need to know it's evaluating an index futures contract vs general "trade setup"?
**Note:** Currently the prompt is instrument-agnostic. ES, NQ, and YM behave differently — NQ is more volatile, YM is slower. The prompt may produce better judgment if it knows which instrument it's evaluating beyond just the symbol string.
**Recommendation:** Defer to Phase 5. Run with current prompt for first 30 trades, log scores, see if scores differ meaningfully across instruments. Tune only if data shows it matters.

---

## Deferred / Phase-Specific Items

### B-101 — Multi-instance support (deferred to "post-Phase 11")
Running APEX for ES + NQ simultaneously requires two independent processes with two IBKR client IDs and two database paths. The current design supports only one instance per IBKR account. Not blocking; trivial to address with a `--instance-id` flag and per-instance config. Add when actually needed.

### B-102 — Backtesting framework (no plan yet)
APEX as designed is a live/paper system. No backtesting harness. ICT setup detection on historical bars is non-trivial because some setups (sweep, MSS) reference state that's not in the bar itself but in the recent bar sequence. Worth designing a replay harness in Phase 10+ once Models 2-4 are in. Not blocking Phase 1-9.

### B-103 — Migration strategy for DB schema changes
Spec says "If schema needs to change, the table is dropped and recreated for now." This is fine while no real data exists. Once paper trading produces meaningful logs, drop-recreate destroys history. Not urgent — address before live transition (Phase 11).

### B-104 — Telegram bot setup
`telegram.enabled: false` by default. User has not yet generated a bot token or chat ID. Not blocking until Phase 8.

### B-105 — Anthropic API key not yet set
`.env` does not exist; user has not yet placed their Anthropic API key. Not blocking until Phase 5.

---

## Known Limitations

### B-201 — Paper account fills are optimistic
IBKR paper account simulates fills with idealized assumptions — no slippage, instant fills at limit prices, etc. Phase 7 paper trading will show better results than live trading produces. Phase 11 (live transition) must monitor for slippage degradation. Documented in `CLAUDE.md`.

### B-202 — News scraper sources unspecified
Phase 3 includes a news scraper but the spec doesn't list specific RSS/web sources. Common choices: Reuters, Bloomberg, ForexFactory, Investing.com economic calendar. User should choose 2–3 sources before Phase 3 begins.

### B-203 — IBKR market data subscription requirements
ES/NQ/YM real-time bars require a CME market data subscription on the IBKR account. Paper accounts get delayed data by default. User needs to confirm subscription status before Phase 2 testing — delayed data will work for development but won't give true bar-close behavior.

### B-204 — Single-broker lock-in
Current design assumes IBKR. Switching to Tradovate, Rithmic, or others requires a new client wrapper module. Architecture supports this (broker is isolated to `core/ibkr_client.py` and `agents/execution_agent.py`) but adds work. Not a real limitation since IBKR is the chosen broker.

### B-205 — Holiday calendar not implemented
US market holidays (no trading) are not currently in the session clock. CME Globex still streams during some holidays but trade volume is meaningless. Phase 3 should include a holiday calendar check.

---

## Technical Debt

### B-301 — Stub style inconsistency
Some agent stubs use docstring + class with `pass` body; others use docstring + class with `__init__(config)`. Both valid but inconsistent. Cosmetic; not worth fixing now. Address whenever the relevant agent gets implemented.

### B-302 — `conftest.py` is essentially empty
Currently just registers an asyncio marker that pytest-asyncio already provides. Could be removed without effect, but harmless. Leave for now — when fixtures are added later (mock IBKR, mock DB, etc.) it'll be the right home for them.

### B-303 — No CI pipeline
Tests run locally only. No GitHub Actions workflow. Trivial to add (`pytest` on push). Not blocking.

### B-304 — `pytest.ini` testpaths only includes `tests/`
If integration tests or property-based tests get added in non-`tests/` directories later, `pytest.ini` needs updating. Note for the future.

---

## Open Questions Without Strong Recommendations

### B-401 — How does APEX handle trades that span session boundaries?
Example: A NY_PM signal fires at 14:55. Position holds past 15:00 when the kill zone closes. What happens?
- Option A: Position runs until SL/TP hits, regardless of session — `kill_zone` is for *entry*, not *holding*
- Option B: Force-close at session end
- Option C: Force-close at end of regular trading hours (16:00 ET for index futures)
**Phase 7 must decide.** Industry default is Option A. Recommend Option A unless user has a reason otherwise.

### B-402 — Should APEX restart automatically after a kill switch trigger the next trading day?
A kill switch trigger ends trading for the current session. Next session: does APEX resume automatically, or does it require a manual reset?
**Recommendation:** Manual reset required. Kill switch trips usually mean something is wrong (drawdown, repeated losses); humans should decide when to resume. Address in Phase 6.

### B-403 — What happens if the AI gate is offline (Anthropic API down) for an extended period?
Current design: timeout = REJECT, log it, no trades. This means an extended outage = no trading. Acceptable for safety, but the user should be aware.
**Mitigation option:** A "degraded mode" config flag that lets APEX trade without the gate during outages, using stricter risk limits. Not recommended for default behavior. Consider only if API reliability proves to be a real problem.

---

## Resolved (kept for history)

### R-001 — v1.2 → v1.3 spec corrections
**Resolved 2026-04-26.** v1.2 of the spec had several issues identified during review:
- 5m/3m incorrectly listed in `bias_timeframes` — moved to FVG-detection-only
- Default R:R of 20/21 ticks was negative-expectancy after fees — changed to flat 1:1 (intentional validation-phase choice)
- AI gate prompt was rule rechecking, not judgment — redesigned around quality scoring
- CL Liquidity Sweep Model 4 was inconsistent with single-instrument design — removed
- Section 3d was truncated in the Phase 1 spec file — restored with full SignalCandidate dataclass
- Stale model string `claude-sonnet-4-5-20251001` — updated to `claude-haiku-4-5-20251001`
- `.env.template` and `.gitignore` were missing — added
- `core/logger.py` was missing — added with rotating file handler and UTC timestamps
- Timezone policy was unspecified — documented (UTC in storage, NY for sessions/display)
All resolved in v1.3 commit `2864cbc`.

### R-002 — Single-instrument trading model
**Resolved 2026-04-26.** Earlier spec versions had `markets: [ES, NQ, YM]` allowing multi-instrument concurrent trading. User clarified intent: trade one instrument per run, use the others as context. Implemented as `traded_instrument` (string) + `context_instruments` (list) in config, with `--market` CLI override. Sister instruments stream read-only for SMT divergence and correlation context.

### R-003 — Phase 1 Build
**Resolved 2026-04-26.** Claude Code completed Phase 1 foundation. 25 tests passing. Audited against Section 4 checklist and verified by Claude (design). Commit on `main`.
