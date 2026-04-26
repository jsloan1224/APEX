# BACKLOG.md
**Open issues, deferred decisions, known limitations, technical debt.**
**Last updated: April 26, 2026 | Phase 2 complete | Phase 3 spec written**

This is the running list of things that are known but not blocking. New items added at the top of each section. When an item is resolved, move it to "Resolved" at the bottom of the file.

---

## Open Decisions (need user input before relevant phase)

### B-006 — Validation prompt instrument-specific tuning
**Question:** Does the AI gate prompt need to know it's evaluating an index futures contract vs general "trade setup"?
**Note:** Currently the prompt is instrument-agnostic. ES, NQ, and YM behave differently — NQ is more volatile, YM is slower. The prompt may produce better judgment if it knows which instrument it's evaluating beyond just the symbol string.
**Recommendation:** Defer to Phase 5. Run with current prompt for first 30 trades, log scores, see if scores differ meaningfully across instruments. Tune only if data shows it matters.

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

### B-203 — IBKR market data subscription requirements
ES/NQ/YM real-time bars require a CME market data subscription on the IBKR account. Paper accounts get delayed data by default. User needs to confirm subscription status before Phase 2 testing — delayed data will work for development but won't give true bar-close behavior.

### B-204 — Single-broker lock-in
Current design assumes IBKR. Switching to Tradovate, Rithmic, or others requires a new client wrapper module. Architecture supports this (broker is isolated to `core/ibkr_client.py` and `agents/execution_agent.py`) but adds work. Not a real limitation since IBKR is the chosen broker.

### B-306 — `reqHistoricalData` blocks event loop during startup (Phase 3)
`_start_subscriptions()` in `MarketDataAgent` calls `reqHistoricalData` (synchronous ib_insync call) inside an `async def` without `run_in_executor`. With 18 streams and a 2-day history load each, this blocks the asyncio event loop 18 times during startup. No crash in paper mode but will freeze the loop. Address when the full async event loop architecture is wired in Phase 3.

### B-307 — `_setup_disconnect_handler` uses bare `asyncio.create_task()` (Phase 3)
The disconnect callback in `MarketDataAgent._setup_disconnect_handler()` calls `asyncio.create_task(self._reconnect())` — the bare form, not `asyncio.get_running_loop().create_task()`. Inconsistent with the rest of the codebase and will raise `RuntimeError` if triggered outside a running loop. Fix when reconnect logic is exercised in Phase 3 integration testing.

### B-308 — `cursor.rowcount` unreliable after `executemany` with INSERT OR IGNORE
`DatabaseManager.insert_historical_bars()` uses `cursor.rowcount` to return the inserted count. On some aiosqlite/SQLite versions, `rowcount` after `executemany` returns `-1` or total attempted rows, not actual inserted rows. The value is only used in debug logging so no logic is affected, but the log will show wrong counts. Fix by replacing with `SELECT changes()` after the insert.

### B-305 — KillSwitch shared instance not wired into MarketDataAgent
Phase 2 `MarketDataAgent` instantiates its own `KillSwitch(config)` internally because the constructor signature in the spec didn't include a KillSwitch parameter. This means the MarketDataAgent's kill switch is a separate instance from the one in `main.py`. Phase 6 must wire a single shared KillSwitch instance through the full system — passed into MarketDataAgent, ExecutionAgent, and any other agent that needs to trigger it.

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

### R-004 — Phase 2 blockers resolved (B-001, B-004, B-005)
**Resolved 2026-04-26.** User decisions:
- B-001: Memory-only ring buffer (`collections.deque`) for live pipeline + separate `historical_bars` SQLite table for completed-session data. All 18 streams persisted.
- B-004: Dynamic contract resolution via `reqContractDetails()` at session start. Front-month = nearest expiry >= today. Cached for session lifetime.
- B-005: Bar close time convention. IBKR open time + `timedelta(minutes=timeframe)` internally. UTC ISO 8601 output.
- B-002 (spec approach): Written fresh, mirroring Phase 1 structure.
- B-003 (smoke test): Confirmed passing by user — `python main.py` ran successfully on Windows box.

### R-007 — B-205 Holiday calendar
**Resolved 2026-04-26.** Holiday calendar (CME Globex observed holidays, Sat→Fri/Sun→Mon rules) addressed in Phase 3 spec. SessionClockAgent will implement computed holiday detection for 2025–2026.

### R-006 — B-202 News scraper sources
**Resolved 2026-04-26.** User chose ForexFactory as the sole news source. Red-impact (High) USD events only. No secondary source needed. Spec written accordingly in APEX_Phase3_ClaudeCode_Spec.md using the ForexFactory JSON feed (nfs.faireconomy.media).

### R-005 — Phase 2 Build
**Resolved 2026-04-26.** Claude Code completed Phase 2 market data agent. 41 tests passing (25 Phase 1 + 8 bar buffer + 8 market data). Four implementation deviations — all audited and accepted:
1. Gap check runs before push (spec contradiction resolved in favor of correct behavior).
2. KillSwitch instantiated internally in MarketDataAgent — tracked as B-305 for Phase 6.
3. `test_database.py` updated for 9-table schema — correct and necessary.
4. `asyncio.get_running_loop().create_task()` pattern used — superior to bare `asyncio.create_task()` for callback context.
Committed to `build` branch.
**Resolved 2026-04-26.** Claude Code completed Phase 1 foundation. 25 tests passing. Audited against Section 4 checklist and verified by Claude (design). Commit on `main`.
