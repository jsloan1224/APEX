# APEX — Phase 3 Claude Code Build Spec
**Session Clock Agent · News Scraper Agent · Kill Zone Cutoff Enforcement**
**Version 1.0 | April 2026**

---

## How to Use This Document

Paste the build instructions from Section 3 as your first message to Claude Code. Claude Code must build exactly what is specified. No additional features. No assumptions. After Claude Code completes Phase 3, return this document to Claude (design) for audit.

---

## 1. Phase 3 Scope

Phase 3 builds two agents: the session clock agent and the news scraper agent. It also enforces cutoff windows that gate signal candidates from downstream phases.

1. `agents/session_clock_agent.py` — implement: session window open/close logic, kill zone cutoff enforcement, US market holiday calendar
2. `agents/news_scraper_agent.py` — implement: ForexFactory economic calendar scrape, red-impact USD event parsing, `news_events` table writes, news blackout window query
3. `config.yaml` — add `news_scraper` block
4. `core/database.py` — `news_events` table already exists (Phase 1); confirm schema is correct; add `upsert_news_event()` helper
5. `tests/test_session_clock.py` — replace stub with real tests
6. `tests/test_news_scraper.py` — replace stub with real tests

Phase 3 does **not** implement:
- Any signal or setup detection (Phase 4)
- FVG, OB, MSS, or sweep logic (Phase 4)
- SMT divergence (Phase 4)
- AI quality gate (Phase 5)
- KillSwitch.check() full logic (Phase 6)
- Any order execution (Phase 7)

---

## 2. What Changes in Phase 3

| Component | Change |
|---|---|
| `agents/session_clock_agent.py` | Implemented — was a stub in Phase 2 |
| `agents/news_scraper_agent.py` | Implemented — was a stub in Phase 2 |
| `config.yaml` | New `news_scraper` block added |
| `core/database.py` | `upsert_news_event()` helper added |
| `tests/test_session_clock.py` | Real tests — was a stub in Phase 2 |
| `tests/test_news_scraper.py` | Real tests — was a stub in Phase 2 |

Nothing else changes. All Phase 1 and Phase 2 modules remain untouched unless specified below.

---

## 3. Phase 3 Build Instructions — Paste to Claude Code

### 3a. Preamble

```
APEX TRADING SYSTEM — PHASE 3 BUILD INSTRUCTIONS v1.0

You are building Phase 3 of APEX: the session clock agent and news scraper agent.
Read APEX_Phase3_ClaudeCode_Spec.md in full before writing a single line of code.
Build exactly what is specified. No additional features. No assumptions.
Do not modify any Phase 1 or Phase 2 module unless this spec explicitly tells you to.

KEY ARCHITECTURAL FACTS CARRIED FROM PRIOR PHASES:
- APEX trades ONE instrument per run (traded_instrument). The other two are context only.
- bias_timeframes: [240, 60, 15]. 5m and 3m are FVG-detection-only.
- All timestamps stored as UTC ISO 8601 in SQLite.
- Session windows and kill zone math use America/New_York timezone — convert at the agent layer.
- Dashboard display uses America/New_York — convert at the presentation layer.
- Never store local time. Always UTC in DB.
- Async throughout — aiosqlite + ib_insync.

NEW IN PHASE 3:
- SessionClockAgent determines whether APEX is inside a valid trading window.
- NewsScraperAgent fetches ForexFactory, parses red-impact USD events, writes to news_events table.
- Both agents expose a simple boolean query interface used by the signal pipeline in Phase 4+.
- Session clock enforces signal_cutoff_minutes_before_kz_close from config.
- News blackout window is news_window_minutes from config (default 10) around each red event.
- US market holiday calendar is built-in; APEX does not trade on CME Globex holidays.
```

---

### 3b. Folder Structure — Phase 3 Changes

Files marked `# BUILD NOW` require full implementation this phase.
Files marked `# stub — Phase N` are untouched placeholder files from prior phases.

```
agents/
├── session_clock_agent.py        # BUILD NOW
├── news_scraper_agent.py         # BUILD NOW
├── market_data_agent.py          # Phase 2 — DO NOT MODIFY
├── risk_manager.py               # stub — Phase 6
├── smt_agent.py                  # stub — Phase 4
├── validation_gate.py            # stub — Phase 5
├── execution_agent.py            # stub — Phase 7
├── audit_agent.py                # stub — Phase 8
└── chart_agent.py                # stub — Phase 9

core/
├── database.py                   # BUILD NOW — add upsert_news_event() only
├── bar_buffer.py                 # Phase 2 — DO NOT MODIFY
├── signal.py                     # Phase 1 — DO NOT MODIFY
├── ibkr_client.py                # Phase 1 — DO NOT MODIFY
├── logger.py                     # Phase 1 — DO NOT MODIFY
├── claude_client.py              # stub — Phase 5
└── indicators.py                 # stub — Phase 4

tests/
├── test_session_clock.py         # BUILD NOW — replace stub
├── test_news_scraper.py          # BUILD NOW — replace stub
├── test_database.py              # Phase 1 — DO NOT MODIFY
├── test_bar_buffer.py            # Phase 2 — DO NOT MODIFY
├── test_market_data.py           # Phase 2 — DO NOT MODIFY
├── test_ibkr_client.py           # Phase 1 — DO NOT MODIFY
├── test_kill_switch.py           # Phase 1 — DO NOT MODIFY
└── test_signal.py                # Phase 1 — DO NOT MODIFY
```

---

### 3c. config.yaml — Add news_scraper block

Add the following block to `config.yaml` at the top level (after the `market_data` block):

```yaml
news_scraper:
  source: 'forexfactory'
  currency_filter: ['USD']
  impact_filter: ['High']                # ForexFactory "red" events only
  fetch_interval_minutes: 60             # how often to refresh the calendar
  news_window_minutes: 10               # blackout window before AND after each event
  request_timeout_seconds: 15
  user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
```

`news_window_minutes` must be read from config — never hardcoded. The blackout applies `news_window_minutes` before the event AND `news_window_minutes` after the scheduled event time.

---

### 3d. agents/session_clock_agent.py — Full Implementation

```python
"""
agents/session_clock_agent.py

Session clock agent. Determines whether APEX is inside a valid trading window.
Enforces kill zone cutoff. Checks US CME Globex holiday calendar.
"""
```

**Class: `SessionClockAgent`**

Constructor: `__init__(self, config: dict)`

Reads from `config`:
- `config['sessions']` — the sessions block defining LONDON, NY_AM, NY_PM windows
- `config['paper_default']['signal_cutoff_minutes_before_kz_close']` — cutoff window (use whichever profile is active; accept the full config and let the active profile be passed separately OR accept profile config directly — see note below)
- Timezone is always `America/New_York` for session window math

**Note on config access:** Accept `config` as the full loaded YAML dict. The active profile name is passed as a second constructor argument `profile: str = 'paper_default'`. Use `config[profile]['signal_cutoff_minutes_before_kz_close']` and `config[profile]['sessions']` to get the right profile values. Sessions block is top-level: `config['sessions']`.

**Methods required:**

```python
def is_session_open(self, dt: datetime | None = None) -> bool:
    """
    Return True if dt (default: now in America/New_York) falls within any
    active session window AND the signal cutoff has not been reached.

    Signal cutoff: returns False if fewer than signal_cutoff_minutes_before_kz_close
    minutes remain in the current session window.
    """

def current_session(self, dt: datetime | None = None) -> str | None:
    """
    Return the name of the active session ('LONDON', 'NY_AM', 'NY_PM')
    or None if outside all session windows.
    Does NOT apply cutoff logic — returns session name purely based on clock.
    """

def minutes_until_next_session(self, dt: datetime | None = None) -> float | None:
    """
    Return minutes until the next session opens.
    Returns None if no future session exists today (after NY_PM close).
    Looks ahead to next calendar day if needed, skipping holidays.
    """

def is_holiday(self, dt: datetime | None = None) -> bool:
    """
    Return True if dt's date (America/New_York) is a US CME Globex holiday.
    APEX does not trade on these days.
    """
```

**Holiday calendar:** Hard-code the CME Globex holiday list for 2025 and 2026. Include:
- New Year's Day
- Martin Luther King Jr. Day
- Presidents' Day
- Good Friday
- Memorial Day
- Juneteenth
- Independence Day
- Labor Day
- Thanksgiving Day
- Christmas Day

If a holiday falls on Saturday, observe Friday. If Sunday, observe Monday. Use Python's `datetime` module to compute observed dates — do not hardcode specific calendar dates beyond the rule set above, so the calendar auto-computes correctly for any year.

**Timezone handling:** All internal math uses `pytz.timezone('America/New_York')`. Session start/end strings from config are parsed as NY time. The `dt` parameter to all methods, if provided, must be a timezone-aware datetime. If `dt` is None, use `datetime.now(pytz.timezone('America/New_York'))`.

**Logging:** Log session open and close events at INFO level using `get_logger(__name__)`. Do not log on every `is_session_open()` call — only on state transitions (closed → open, open → closed).

---

### 3e. agents/news_scraper_agent.py — Full Implementation

```python
"""
agents/news_scraper_agent.py

News scraper agent. Fetches ForexFactory economic calendar.
Parses red-impact USD events. Writes to news_events table.
Provides blackout window query interface for signal pipeline.
"""
```

**Class: `NewsScraperAgent`**

Constructor: `__init__(self, config: dict, db: DatabaseManager)`

Reads from `config['news_scraper']`.

**ForexFactory calendar fetching:**

ForexFactory publishes a JSON calendar endpoint used by their own web app:
```
https://nfs.faireconomy.media/ff_calendar_thisweek.json
```
and for next week:
```
https://nfs.faireconomy.media/ff_calendar_nextweek.json
```

Use `httpx` (async) to fetch both URLs. Do not scrape HTML — use the JSON feed. Add `httpx` to `requirements.txt`.

Each event in the JSON has this shape (approximate — handle defensively):
```json
{
  "title": "Core CPI m/m",
  "country": "USD",
  "date": "2026-04-29T08:30:00-04:00",
  "impact": "High",
  "forecast": "0.3%",
  "previous": "0.4%"
}
```

Filter criteria (both must match):
- `country == 'USD'` (from `config['news_scraper']['currency_filter']`)
- `impact == 'High'` (from `config['news_scraper']['impact_filter']`)

**Methods required:**

```python
async def fetch_and_store(self) -> int:
    """
    Fetch this week's and next week's ForexFactory calendars.
    Filter to red USD events.
    Upsert into news_events table via db.upsert_news_event().
    Return count of events upserted.
    Log fetch result at INFO level (count + any errors).
    """

async def is_news_blackout(self, dt: datetime | None = None) -> bool:
    """
    Return True if dt (default: now UTC) is within news_window_minutes
    before OR after any high-impact USD event stored in news_events.
    Query the DB — do not hold events in memory.
    dt must be UTC-aware for DB comparison.
    """

async def start_refresh_loop(self) -> None:
    """
    Run fetch_and_store() on startup, then repeat every
    config['news_scraper']['fetch_interval_minutes'] minutes.
    Designed to run as an asyncio background task.
    Log each refresh cycle at DEBUG level.
    On fetch failure: log ERROR, do not crash, retry next cycle.
    """
```

**Error handling:** If the ForexFactory feed is unreachable or returns non-200, log at ERROR level and return an empty result (do not raise). The system must still run without news data — it will simply not apply a blackout. Log a WARNING once if operating without news data so the user is aware.

**User agent:** Use `config['news_scraper']['user_agent']` as the `User-Agent` header on all requests.

**Timeout:** Use `config['news_scraper']['request_timeout_seconds']` as the httpx timeout.

---

### 3f. core/database.py — Add upsert_news_event()

Do not change any existing method or table definition. Add one method only:

```python
async def upsert_news_event(self, event: dict) -> None:
    """
    Insert or replace a news event in the news_events table.
    event dict keys: title, currency, impact, event_time (UTC ISO 8601 string),
    forecast (str or None), previous (str or None), source (str).
    Uses INSERT OR REPLACE.
    """
```

The existing `news_events` table schema (from Phase 1) is:
```sql
CREATE TABLE IF NOT EXISTS news_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_time TEXT NOT NULL,
    currency TEXT NOT NULL,
    impact TEXT NOT NULL,
    title TEXT NOT NULL,
    forecast TEXT,
    previous TEXT,
    source TEXT,
    created_at TEXT NOT NULL
)
```

`INSERT OR REPLACE` requires a UNIQUE constraint to be useful. Add a unique index on `(event_time, title, currency)` in `_create_tables()` — add this index definition alongside the existing table definition. This ensures re-fetching the same event doesn't create duplicates.

**Migration note:** The `historical_bars` table already has a unique index added in Phase 2 using `CREATE UNIQUE INDEX IF NOT EXISTS`. Use the same pattern.

---

### 3g. requirements.txt — Add httpx

Add `httpx>=0.27.0` to `requirements.txt`. This is the only new dependency in Phase 3.

---

### 3h. tests/test_session_clock.py — Required Tests

Minimum passing tests (write more if useful):

1. **`test_is_session_open_inside_window`** — construct a datetime inside NY_AM (e.g., 10:30 AM ET on a non-holiday weekday), assert `is_session_open()` returns True.

2. **`test_is_session_open_outside_window`** — construct a datetime outside all windows (e.g., 08:00 AM ET), assert returns False.

3. **`test_cutoff_enforcement`** — construct a datetime inside NY_AM but within `signal_cutoff_minutes_before_kz_close` minutes of close (e.g., 10:50 AM with 15-minute cutoff), assert `is_session_open()` returns False.

4. **`test_current_session_returns_correct_name`** — datetime inside LONDON window returns `'LONDON'`; datetime outside all windows returns `None`.

5. **`test_is_holiday_new_years`** — assert `is_holiday()` returns True for January 1 of any year.

6. **`test_is_holiday_observed`** — assert `is_holiday()` handles a holiday that falls on Sunday (observed Monday).

7. **`test_no_trading_on_holiday`** — construct a datetime inside NY_AM window on a known holiday, assert `is_session_open()` returns False.

8. **`test_minutes_until_next_session`** — construct a datetime between LONDON close and NY_AM open, assert returned value is a positive float less than 1440 (minutes in a day).

All tests must pass without a live IBKR connection and without network calls.

---

### 3i. tests/test_news_scraper.py — Required Tests

Minimum passing tests (write more if useful):

All ForexFactory HTTP calls must be mocked — tests must not make real network calls.

1. **`test_fetch_and_store_filters_correctly`** — mock the FF JSON feed to return a mix of USD/High, EUR/High, and USD/Medium events; assert only the USD/High events are upserted.

2. **`test_fetch_and_store_returns_count`** — assert `fetch_and_store()` returns the correct count of upserted events.

3. **`test_is_news_blackout_true`** — insert a news event into the test DB at a known UTC time; construct `dt` within the blackout window; assert `is_news_blackout()` returns True.

4. **`test_is_news_blackout_false`** — same event; construct `dt` well outside the blackout window; assert returns False.

5. **`test_is_news_blackout_boundary`** — assert returns True when `dt` is exactly `news_window_minutes` before the event (boundary is inclusive).

6. **`test_fetch_failure_does_not_raise`** — mock the HTTP call to raise a `httpx.RequestError`; assert `fetch_and_store()` does not raise, returns 0.

7. **`test_upsert_deduplication`** — call `fetch_and_store()` twice with the same mocked data; assert the `news_events` table has no duplicate rows (unique constraint working).

All tests must pass without network calls. Use `pytest-mock` or `unittest.mock.patch` for HTTP mocking. Add `pytest-mock` to `requirements.txt` if not already present.

---

### 3j. Communication and Commit Protocol

When Phase 3 is complete, Claude Code must report:

1. **Files created or modified** — flat list with line counts
2. **pytest output** — full output, not a summary
3. **Deviations** — anything that differs from this spec with the reason
4. **Open questions** — any ambiguity resolved with a judgment call

After all tests pass, commit with message `Phase 3: session clock + news scraper agents` and push to `origin/build`. Do not push to `main`.

---

## 4. Audit Checklist — Claude (Design) Runs This After Claude Code Completes

Pull from `origin/build` and verify each item against actual file contents. Do not trust the build session's self-report.

### 4a. config.yaml
- [ ] `news_scraper` block present with all six keys: `source`, `currency_filter`, `impact_filter`, `fetch_interval_minutes`, `news_window_minutes`, `request_timeout_seconds`, `user_agent`
- [ ] No other config changes made

### 4b. agents/session_clock_agent.py
- [ ] `is_session_open()` implemented with cutoff logic
- [ ] `current_session()` implemented without cutoff logic
- [ ] `minutes_until_next_session()` implemented
- [ ] `is_holiday()` implemented with computed (not hardcoded date) holiday calendar covering 2025–2026
- [ ] Holiday observed-date rules implemented (Sat→Fri, Sun→Mon)
- [ ] `is_session_open()` returns False on holidays
- [ ] All timezone math uses `pytz.timezone('America/New_York')`
- [ ] `get_logger(__name__)` used; no `print()` calls
- [ ] No hardcoded config values — all read from `config`

### 4c. agents/news_scraper_agent.py
- [ ] `fetch_and_store()` fetches both thisweek and nextweek FF JSON URLs
- [ ] Filters to `currency == 'USD'` and `impact == 'High'` only
- [ ] Calls `db.upsert_news_event()` for each qualifying event
- [ ] Returns correct upsert count
- [ ] `is_news_blackout()` queries DB (not in-memory list)
- [ ] Blackout window is symmetric: `news_window_minutes` before AND after event
- [ ] `start_refresh_loop()` implemented as async loop
- [ ] Fetch failure logs ERROR and does not raise
- [ ] `httpx` used for async HTTP (not `requests`, not `aiohttp`)
- [ ] `get_logger(__name__)` used; no `print()` calls

### 4d. core/database.py
- [ ] `upsert_news_event()` method added
- [ ] Uses `INSERT OR REPLACE`
- [ ] Unique index on `(event_time, title, currency)` added to `_create_tables()`
- [ ] No other changes to existing methods or table definitions

### 4e. requirements.txt
- [ ] `httpx>=0.27.0` present
- [ ] `pytest-mock` present (if used in tests)
- [ ] No other new dependencies added

### 4f. Tests
- [ ] `test_session_clock.py` — all 8 required tests present and passing
- [ ] `test_news_scraper.py` — all 7 required tests present and passing
- [ ] No tests make real network calls
- [ ] Total passing test count ≥ 56 (41 prior + 15 new minimum)
- [ ] `pytest -v` output shows no warnings about unclosed event loops or deprecated async patterns

### 4g. Stubs Untouched
- [ ] `agents/risk_manager.py` — unchanged from Phase 2
- [ ] `agents/smt_agent.py` — unchanged from Phase 2
- [ ] `agents/validation_gate.py` — unchanged from Phase 2
- [ ] `agents/execution_agent.py` — unchanged from Phase 2
- [ ] `agents/audit_agent.py` — unchanged from Phase 2
- [ ] `agents/chart_agent.py` — unchanged from Phase 2
- [ ] `core/claude_client.py` — unchanged from Phase 2
- [ ] `core/indicators.py` — unchanged from Phase 2

### 4h. Commit
- [ ] Commit message is `Phase 3: session clock + news scraper agents`
- [ ] Push is to `origin/build`, not `origin/main`

**Verdict: PASS / FAIL**

If FAIL — list items to fix and return to Claude Code. Do not modify code directly.
