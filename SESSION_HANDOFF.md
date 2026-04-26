# SESSION_HANDOFF.md
**Bootstrap document for new chat sessions on the APEX project.**
**Last updated: April 26, 2026 | Phase 1 complete, awaiting Phase 2 spec authoring**

---

## Purpose

If you are Claude in a fresh conversation, the user has just brought you onto the APEX project. **Read this file first**, then read the supporting docs in this order:

1. `CLAUDE.md` — non-negotiable rules of engagement
2. `PROJECT_STATE.md` — what's built, what's stubbed, what's next
3. `BACKLOG.md` — open issues and deferred decisions
4. `APEX_System_Whiteboard.md` — full system design (source of truth)
5. `APEX_Phase1_ClaudeCode_Spec.md` — Phase 1 build instructions (already executed)

After reading those, you have full context. Do not ask the user to re-explain the project. The user expects continuity.

---

## One-Paragraph Project Summary

APEX is a fully autonomous ICT (Inner Circle Trader) futures trading system written in Python. It trades **one selectable instrument per run** — ES, NQ, or YM — on Interactive Brokers. The other two indices stream read-only as context for SMT divergence and correlation. Deterministic ICT setup detection (bias chain, liquidity sweep, MSS, FVG identification) runs in Python; a Claude Haiku 4.5 quality gate scores three judgment dimensions (displacement quality, sweep decisiveness, environment) on 1–5 before any trade executes. SQLite logs everything, Plotly Dash provides a real-time dashboard, paper trading via IBKR port 7497 with live trading guarded behind explicit flags. Build is split into 11 sequential phases; **Phase 1 (Foundation) is complete and audited**. Next step is authoring `APEX_Phase2_ClaudeCode_Spec.md` for the market data agent.

---

## Where We Are Right Now

| Item | State |
|---|---|
| Spec version | v1.3 (committed) |
| Current phase | Phase 1 — Foundation: **COMPLETE** |
| Next phase | Phase 2 — Market Data Agent: **NOT STARTED** |
| Next required action | Resolve B-001, B-004, B-005 with user, then author `APEX_Phase2_ClaudeCode_Spec.md` |
| Tests passing | 25 / 25 |
| Smoke test status | Not yet run by user (recommended before Phase 2) |

### Blockers Before Phase 2 Spec Authoring

These three open decisions in `BACKLOG.md` must be resolved with the user before the Phase 2 spec can be written. Do not start drafting the spec until all three are answered.

- **B-001** — Bar buffer persistence: memory-only ring buffer, persistent table, or hybrid?
- **B-004** — IBKR contract resolution: static config symbol vs dynamic `reqContractDetails` at session start
- **B-005** — Bar timestamp convention: open time (IBKR default) vs close time (ICT convention)

---

## What Has Been Decided and Locked

These decisions are non-negotiable. Do not propose alternatives in a new session unless the user explicitly reopens the question.

1. **Single-instrument trading.** One `traded_instrument` per run (ES | NQ | YM). Two `context_instruments` for SMT and correlation, never receive orders. Selection via `--market` CLI flag or config.
2. **Bias chain is `[240, 60, 15]`.** Three timeframes, all must agree. 5m and 3m are FVG-detection-only.
3. **R:R is 1:1 for validation phase.** This is intentional, not an oversight. Will widen to 2:1 / 3:1 / pyramiding only after entries are proven.
4. **AI gate is quality scoring, not rule rechecking.** Three dimensions on 1–5 scale. Hard 2s timeout. Claude Haiku 4.5.
5. **SMT divergence is context, not hard reject.** Flows into the AI gate's environment score.
6. **CL is removed.** Index futures only.
7. **UTC in DB, America/New_York at agent and display layers.**
8. **Async throughout** (aiosqlite + ib_insync).
9. **Live port 7496 is guarded** in `IBKRClient.connect()`.

Full list in `CLAUDE.md`.

---

## What Has Been Removed or Forbidden

Don't accidentally re-introduce these. They were considered and rejected.

- CL (Crude Oil) and Model 4 "CL Liquidity Sweep" — removed in v1.3
- Multi-instrument concurrent trading (`markets: [ES, NQ, YM]` as a list of traded markets)
- 3m or 5m in `bias_timeframes`
- Sonnet 4.5 model string (`claude-sonnet-4-5-20251001`) — replaced with Haiku 4.5
- Hard-gate SMT divergence (it's context, not a deterministic block)
- Wider default R:R (1:1 is intentional for validation phase)

---

## Style Expectations from the User

The user is a working trader and project owner. Read the user preferences carefully:

- **Direct answers, no validation language.** Skip "Great question!" Skip "I understand." Just answer.
- **Push back when wrong.** If a request would break the architecture or weaken the system, say so plainly with reasons. The user pushes back on weak arguments and expects the same in return.
- **Concise prose, no filler.** Tables and bullets when they help. Paragraphs when they help.
- **Show the math.** Tradeoffs that involve numbers (R:R, latency, cost) get actual numbers, not "this could be expensive."
- **No false certainty.** When uncertain, say so. When something needs verification (model strings, library APIs, market behavior), search or check rather than guessing.

---

## How Phases Work

APEX is built in 11 sequential phases. **Phase N+1 does not begin until Phase N passes design audit.** The pattern is:

1. **Author phase spec.** Claude (design) writes a detailed `APEX_PhaseN_ClaudeCode_Spec.md` with build instructions and an audit checklist.
2. **Push to repo.** Spec is committed to GitHub.
3. **Hand to Claude Code.** User pastes the build message into a Claude Code session in the local repo. Claude Code clones the spec, builds, runs tests, commits, and pushes.
4. **Audit.** User brings the result back to a Claude (design) session. Claude pulls from repo, runs the audit checklist, and gives a pass/fail verdict.
5. **Resolve any issues.** If audit fails, fixes go back to Claude Code. If audit passes, move to Phase N+1.

Phase 1 went through this loop successfully. Phase 2 is next.

---

## How to Pick Up Phase 2

When the user says "let's start Phase 2" or similar:

1. Confirm the user has run a smoke test of Phase 1 (`python main.py --dry-run`) on their machine, OR explicitly skipped it.
2. Read `BACKLOG.md` items B-001 through B-005 — these are open Phase 2 design questions that need user input.
3. Resolve those questions with the user. Specifically:
   - B-001: Bar buffer persistence strategy (memory-only vs persistent, or hybrid)
   - B-004: IBKR contract resolution approach (static config vs dynamic per-session)
   - B-005: Bar timestamp convention (open vs close)
4. Once resolved, **author `APEX_Phase2_ClaudeCode_Spec.md`**. Mirror the structure of the Phase 1 spec: scope, what changed since previous version, build instructions section, audit checklist. Push to repo.
5. Hand off to Claude Code with a paste-ready message pointing to the new spec file.

Do not let the user paste a Phase 2 build message until the spec is written and committed. Phase 1 worked because the spec was rigorous; Phase 2 needs the same discipline.

---

## Repo Layout (top level)

```
APEX/
├── README.md                          # Project overview
├── CLAUDE.md                          # Rules of engagement
├── PROJECT_STATE.md                   # Current state
├── BACKLOG.md                         # Open issues
├── SESSION_HANDOFF.md                 # This file
├── APEX_System_Whiteboard.md          # Full design (source of truth)
├── APEX_Phase1_ClaudeCode_Spec.md     # Phase 1 build instructions
│
├── config.yaml                        # All profiles, instruments, risk
├── main.py                            # CLI entry point
├── requirements.txt
├── pytest.ini
├── conftest.py
├── .env.template
├── .gitignore
│
├── agents/                            # Phase 2-9 agent stubs + risk_manager (stub for kill switch)
├── core/                              # database, signal, ibkr_client, logger (built); claude_client, indicators (stubs)
├── models/                            # All Phase 4/10 stubs
├── dashboard/                         # All Phase 9 stubs
├── prompts/                           # validation_prompt.txt (built), sentiment_prompt.txt (stub)
├── tests/                             # 25 passing tests
├── data/                              # apex.db lives here
└── logs/                              # apex.log lives here
```

---

## Known State of the User's Local Environment

- User runs Claude Code locally on Windows
- Repo: `https://github.com/jsloan1224/APEX`
- Branch strategy: `build` is the working branch — all Claude Code pushes go to `build`. Merges to `main` happen after each phase passes audit.
- User uses fine-grained PATs from the `jsloan1224` GitHub account for pushes (regenerated per session)
- Anthropic API key not yet placed in `.env`
- IBKR TWS not yet confirmed running on user's machine
- No smoke test of `main.py` has been run yet

---

## Anti-Patterns to Avoid in a New Session

- **Don't propose architectural changes to settled decisions.** If the user reopens a question, fine. Otherwise, work within the locked decisions.
- **Don't skip the audit step.** Every Claude Code build gets audited against the phase checklist before declaring done.
- **Don't silently widen scope.** Phase 2 builds only the market data agent. Don't bleed into session clock or news scraper.
- **Don't write speculative code in design discussions.** Design first, hand to Claude Code for implementation.
- **Don't lose the user's preferences across sessions.** This file exists so style and rules carry forward.

---

## If Anything Conflicts

`APEX_System_Whiteboard.md` and `APEX_Phase1_ClaudeCode_Spec.md` are the source of truth for what's already designed. `CLAUDE.md` is the source of truth for project rules. This file (`SESSION_HANDOFF.md`) is meta — if it conflicts with the others, the others win.

If you find conflicts in the docs themselves, raise them with the user. Do not silently pick one version.
