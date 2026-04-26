# CLAUDE.md
**Project: APEX — Autonomous Predictive Execution System**
**Last updated: April 26, 2026 | Spec version: v1.3 | Phase 1 complete**

---

## Purpose of This File

This file is read by Claude Code at the start of every session and by Claude (design/audit) when reviewing builds. It defines the rules of engagement for working on APEX so the system stays consistent across sessions, machines, and weeks of work.

If anything in this file conflicts with the spec documents (`APEX_System_Whiteboard.md` or `APEX_Phase1_ClaudeCode_Spec.md`), the spec documents win. This file is meta-rules, not implementation rules.

## Companion Docs — Read These Too

| File | When to read |
|---|---|
| `SESSION_HANDOFF.md` | First, in any new chat session |
| `PROJECT_STATE.md` | After this file — tells you what's built and what's next |
| `BACKLOG.md` | Open issues, deferred decisions, known limitations |
| `APEX_System_Whiteboard.md` | Source of truth for system design |
| `APEX_Phase1_ClaudeCode_Spec.md` | Source of truth for Phase 1 (already built) |

---

## What APEX Is — One-Paragraph Briefing

APEX is a fully autonomous futures trading system that trades **one instrument per run** (ES, NQ, or YM) on Interactive Brokers using ICT (Inner Circle Trader) methodology. The other two indices stream as read-only context for SMT divergence and correlation. The architecture is six layers: agents → signal engine (4 ICT models) → AI quality gate (Claude Haiku 4.5) → risk manager → execution → audit. Every signal candidate is logged to SQLite with full reasoning trace including AI gate scores. A Plotly Dash dashboard at `localhost:8050` provides real-time visual monitoring. **Mode starts as paper. Live is guarded behind an explicit config flag.**

---

## Build Phases — Don't Skip Ahead

APEX is built in 11 sequential phases. **No phase begins until the previous phase passes design audit by Claude (design).** Claude Code does not preemptively implement future phases.

| Phase | Scope |
|---|---|
| 1 | Foundation — scaffold, config, DB, IBKR, kill switch, logger, CLI, tests |
| 2 | Market data agent — bar streaming traded + 2 context instruments, all 6 timeframes |
| 3 | Session clock + news scraper + cutoff window |
| 4 | Model 1 Silver Bullet + SMT detection |
| 5 | AI quality gate — Claude Haiku 4.5, quality scoring |
| 6 | Risk manager — all hard rules |
| 7 | Execution engine — IBKR bracket orders, traded instrument only |
| 8 | Audit agent — SQLite + Telegram |
| 9 | ICT Chart Dashboard — Plotly Dash |
| 10 | Models 2-4 — IFVG+SMT, Power of Three, News Catalyst |
| 11 | Live transition |

Spec for the current phase is the source of truth. The phase spec's Section 3b folder structure annotates each file as either `# BUILD NOW` (real implementation required this phase) or `# stub — Phase N` (placeholder; full implementation deferred to Phase N). Files marked `# stub — Phase N` must contain only a docstring and a class skeleton (`pass` body or `__init__` accepting config) until that phase begins. See "Stubs" under File Conventions for the exact pattern.

---

## Architectural Rules — Non-Negotiable

These are decisions already made. Do not propose alternatives. Do not refactor toward different choices.

### Single-Instrument Trading
- One instrument traded per run: **ES, NQ, or YM**. Selected via `--market` CLI flag or `traded_instrument` config field.
- The other two are **streamed read-only as context** — never receive orders.
- Field name is `traded_instrument` (string), never `market` or `markets`.

### Timeframes — Three Distinct Roles
| Timeframe | Role |
|---|---|
| 4H, 1H, 15m | **Bias** (`bias_timeframes: [240, 60, 15]`) |
| 5m, 3m | **FVG detection only** (NOT bias) |
| 1m | **Execution** |

All six are in `fvg_detection_timeframes`. Do not put 5m or 3m in `bias_timeframes`. This was a v1.2 mistake corrected in v1.3.

### R:R Is Currently 1:1 — Intentional
- `stop_ticks = target_ticks = 20` for all instruments in `paper_default`.
- This is **validation phase**: prove entries are real signals before optimizing for profit.
- Do not "fix" this. Do not propose 2:1 or 3:1 defaults. The structure supports per-instrument override; widening happens later when the user decides.

### AI Gate Is Quality Scoring, Not Rule Rechecking
- Deterministic rules (bias chain, sweep, MSS, FVG, tick filters, risk caps) are enforced in `risk_manager.py` and the model classes.
- The Claude gate scores **three quality dimensions** on 1–5: displacement quality, sweep decisiveness, environment.
- The gate prompt must contain bar windows (last 20 1m bars, last 10 5m bars), not just numeric labels.
- Do not write a gate prompt that re-checks rules. That gate adds nothing and will be removed.

### SMT Divergence Is Context, Not Hard Reject
- Computed at signal flow Step 3.5 (`smt_agent`).
- Result attached to the SignalCandidate and passed to the AI gate as a quality factor.
- Never used as a deterministic REJECT.

### Async Throughout
- `aiosqlite` for DB, `ib_insync` for broker — both event-loop-based.
- Do not mix sync and async DB calls. Pick async, stay async.

### Timezone Policy
- All storage and computation: **UTC ISO 8601** in SQLite.
- Session windows and kill zones: **America/New_York** — converted at the agent layer for time-window math.
- Dashboard display: **America/New_York** — converted at the presentation layer.
- Never store local time.

### Live Trading Is Guarded
- Live port is 7496. Paper port is 7497.
- `IBKRClient.connect()` must raise `IBKRConnectionError` if `mode != 'live'` and target port is 7496.
- Do not weaken this guard.

---

## Removed / Forbidden Concepts

These were in earlier spec versions and are **gone**. Do not re-introduce them.

- **CL (Crude Oil)** — not a tradeable instrument. Removed from `tick_values`. No `models/cl_liquidity.py` file. No "Model 4 CL Liquidity Sweep."
- **Multi-instrument concurrent trading** — `markets: [ES, NQ, YM]` as a list of traded instruments is wrong. The only valid shape is one `traded_instrument` plus `context_instruments`.
- **3m or 5m in bias chain** — they were never bias timeframes. They are FVG-detection-only.
- **Sonnet 4.5 (`claude-sonnet-4-5-20251001`)** — old model string. Use `claude-haiku-4-5-20251001` for the gate.
- **Cross-project memory bleed** — APEX is a trading system, full stop. If Claude memory surfaces context from any other project the user has worked on (book drafts, research notes, anything else), ignore it. Never weave unrelated content into APEX docs, code, or comments.

---

## File Conventions

### Folder Structure
The folder structure in Section 3b of the Phase 1 spec is exact. Do not add files outside it. Do not rename folders. Stubs for future phases must exist as empty-ish files matching the structure.

### Stubs
A stub file looks like this:

```python
"""
agents/smt_agent.py — SMT divergence detection.
Stub — implemented in Phase 4.
"""

class SMTAgent:
    """SMT divergence detector. Phase 4."""
    pass
```

Not `raise NotImplementedError` at module top level (breaks imports). Not empty file (linters complain). A docstring + minimal class.

### Imports
- Absolute imports from project root (`from core.signal import SignalCandidate`)
- No relative imports (`from .signal import ...`)

### Logging
- Every module that does anything gets a logger: `logger = get_logger(__name__)` at top of file.
- Never use `print()` for runtime output. `print()` is acceptable only in `main.py` for the startup banner.

### Config Access
- All config is loaded once in `main.py` and passed down. Never re-read `config.yaml` from inside agents or core modules.
- Config keys are accessed by dictionary lookup — no global state.

### Environment Variables
- All secrets live in `.env`, loaded via `python-dotenv`. Never hardcoded.
- All env var names are documented in `.env.template`.
- Code reads them via `os.getenv('VAR_NAME')` with explicit error if required and missing.

### Database
- All schema lives in `core/database.py` as `CREATE TABLE IF NOT EXISTS` statements run on init.
- Migrations are not in scope through Phase 10. If schema needs to change before then, the table is dropped and recreated. **This is a known limitation — see `BACKLOG.md` B-103.** A real migration story must be in place before Phase 11 (live transition), since drop-recreate destroys live trade history.
- Every timestamp column stores UTC ISO 8601 strings, not Unix epochs.

---

## Testing Conventions

### pytest
- Async tests use `pytest-asyncio` with `@pytest.mark.asyncio` decorator.
- Tests must not require a live IBKR connection (use `--dry-run` mode or mock).
- Tests must not require an Anthropic API key (mock the Claude client).
- Every Phase requires its associated test file to have at least one passing test before audit.

### Test Naming
`tests/test_<module>.py` — one file per module under test. `test_kill_switch.py` tests `agents/risk_manager.py::KillSwitch`, etc.

---

## Communication Protocol — How Claude Code Reports Back

When Claude Code finishes a phase, the report must include:

1. **Files created** — flat list, with line counts
2. **pytest output** — full output, not just "all passed"
3. **Deviations** — anything that differs from the spec, with the reason
4. **Open questions** — anything ambiguous in the spec that was resolved with a judgment call

Do not summarize as "Phase N complete" without these four sections.

After confirming all tests pass, Claude Code must commit and push to `origin/build` before reporting completion. Do not ask for permission — push is part of done. Never push to `main`.

---

## Communication Protocol — How Claude (Design/Audit) Should Respond

When the user brings Claude Code's output back for audit:

1. Run the audit checklist from the relevant phase spec section
2. Identify any deviations or shortcuts
3. Flag any "stub" implementations that should have been full
4. Confirm test coverage matches the phase requirements
5. Give a clear pass/fail verdict, not a soft "looks good"

If the build fails audit, give a single concise list of what to fix. Do not rewrite the code.

### What an Audit Actually Consists Of

- **Read every checklist item** in the phase spec's audit section against the actual file contents in the cloned repo. Not the handoff doc's claim that something passed — the file itself.
- **Run `pytest -v` in a fresh clone** and verify the count and pass/fail match the spec's requirements. Do not trust reported test output from the build session.
- **Spot-check stubs** — confirm files marked "stub — Phase N" in Section 3b of the spec contain only docstring + class skeleton, not partial Phase N+ logic.
- **Audits are end-of-session activity.** New chat sessions do not start with a code audit. Sessions start by reading the handoff docs and giving the user a status report (per `BOOTSTRAP_TEMPLATE.md`). Audits run at the end of a build phase, when the user brings Claude Code's output back.
- **The auditor does not modify code.** If audit fails, write the fix list and stop. Implementation goes back to Claude Code.

Every phase spec must include its own audit checklist as a numbered section (Section 4 in Phase 1). New phase specs that omit this fail review and must be rewritten before Claude Code is engaged.

---

## Style Preferences (from project owner)

- **Direct answers, no validation language.** Skip "Great question!" Skip "I understand your concern." Just answer.
- **Push back when wrong.** If a request would break the architecture or weaken the system, say so plainly with reasons. The owner pushes back on weak arguments and expects the same in return.
- **Concise prose, no filler.** Bullet points and tables when they help. Paragraphs when they help. No bullet-points-for-the-sake-of-bullets.
- **Show the math.** When a tradeoff involves numbers (R:R, latency, cost), show the actual numbers, not "this could be expensive."
- **No false certainty.** When uncertain, say so. When something needs verification (model strings, library APIs, market behavior), search or check rather than guessing.

---

## Honest Trade-Off Reminders

These are real, not hidden. If they become problems, surface them; don't gloss.

- The AI quality gate is the differentiator that justifies Python over NinjaTrader. If after Phase 5–6 the gate's scores don't correlate with trade outcomes, the gate isn't earning its cost — surface this with data, don't quietly defend it.
- 1:1 R:R needs a real win rate to break even after commissions. Validation phase tolerates this; production phase doesn't. Don't let the validation R:R become permanent without a deliberate decision.
- Single-instrument-per-run means you can only run one APEX instance per IBKR account at a time. Running two for ES + NQ simultaneously requires two IBKR client IDs and two database paths — possible but not Phase 1 work.
- IBKR paper account fills are optimistic compared to live. Don't conclude "live works" from paper results alone. Phase 11 monitoring is real, not ceremonial.

---

## Repo URL and Branch Strategy

`https://github.com/jsloan1224/APEX`

**Two branches:**
| Branch | Purpose |
|---|---|
| `main` | Stable. Contains completed, audited phases only. |
| `build` | Working branch. All Claude Code development happens here. |

**Rules:**
- Claude Code always works on `build`. Never push directly to `main`.
- After a phase passes audit, the user merges `build` → `main` via pull request.
- Force-push only with explicit user instruction.

---

## When in Doubt

Stop and ask. The user prefers a clarifying question over a wrong implementation. Phase 1 build for example: if the spec says "stub" but Claude Code thinks it should be implemented, ask first. If the spec is silent on a small choice (e.g., logger format string), pick reasonable defaults and note the choice in the deviation list.
