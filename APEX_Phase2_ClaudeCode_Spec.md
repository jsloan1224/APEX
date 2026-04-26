# APEX — Phase 2 Claude Code Build Spec
**Market Data Agent: IBKR Bar Streaming · Bar Buffer · Contract Resolution · Historical Persistence**
**Version 1.0 | April 2026**

---

## How to Use This Document

Paste the build instructions from Section 3 as your first message to Claude Code. Claude Code must build exactly what is specified. No additional features. No assumptions. After Claude Code completes Phase 2, return this document to Claude (design) for audit.

---

## 1. Phase 2 Scope

Phase 2 builds the market data agent only. No signal detection. No session clock enforcement. No news scraper. No AI gate. No order execution.

1. `config.yaml` — add `bar_buffer_size` to the `market_data` block
2. `core/bar_buffer.py` — new module: thread-safe in-memory ring buffer, one per (instrument, timeframe)
3. `core/database.py` — add `historical_bars` table (9th table)
4. `agents/market_data_agent.py` — implement: IBKR connection, contract resolution, bar streaming for 3 instruments × 6 timeframes, bar normalization, buffer writes, historical persistence, gap detection, reconnect logic
5. `tests/test_market_data.py` — replace stub with real tests
6. `tests/test_bar_buffer.py` — new test file

Phase 2 does **not** implement:
- Session clock window gating (Phase 3)
- Kill zone cutoff enforcement (Phase 3)
- News impact filtering (Phase 3)
- Any signal or setup detection (Phase 4)

---

## 2. What Changed Since Phase 1

| Component | Change |
|---|---|
| `config.yaml` | New `market_data` block: `bar_buffer_size`, `bar_timestamp_convention`, `persist_historical_bars` |
| `core/bar_buffer.py` | New module — did not exist in Phase 1 |
| `core/database.py` | New `historical_bars` table added to `_create_tables()` |
| `agents/market_data_agent.py` | Implemented — was a stub in Phase 1 |
| `tests/test_market_data.py` | Real tests — was a stub in Phase 1 |
| `tests/test_bar_buffer.py` | New test file |

Nothing else changes. All Phase 1 modules remain untouched unless specified below.

---

## 3. Phase 2 Build Instructions — Paste to Claude Code

### 3a. Preamble

```
APEX TRADING SYSTEM — PHASE 2 BUILD INSTRUCTIONS v1.0

You are building Phase 2 of APEX: the market data agent.
Read APEX_Phase2_ClaudeCode_Spec.md in full before writing a single line of code.
Build exactly what is specified. No additional features. No assumptions.
Do not modify any Phase 1 module unless this spec explicitly tells you to.

KEY ARCHITECTURAL FACTS CARRIED FROM PHASE 1:
- APEX trades ONE instrument per run (traded_instrument). The other two are context only.
- bias_timeframes: [240, 60, 15]. 5m and 3m are FVG-detection-only.
- fvg_detection_timeframes: [240, 60, 15, 5, 3, 1] — all six timeframes stream bars.
- All timestamps stored as UTC ISO 8601 in SQLite.
- Async throughout — aiosqlite + ib_insync.
- Live port 7496 is guarded in IBKRClient — do not change that logic.

NEW IN PHASE 2:
- Bar timestamps are converted to BAR CLOSE TIME internally (IBKR returns open time — add bar duration to get close time).
- Bar buffer is memory-only ring buffer, configurable size (default 500 bars per timeframe per instrument).
- Historical bars (completed sessions) are persisted to SQLite for all 18 streams.
- Contract resolution is dynamic via reqContractDetails() at session start — not hardcoded symbols.
```

---

### 3b. config.yaml — Add market_data block

Add the following block to `config.yaml` at the top level (after the `dashboard` block):

```yaml
market_data:
  bar_buffer_size: 500              # bars retained per (instrument, timeframe) in memory — increase if indicators need more lookback
  bar_timestamp_convention: close   # 'close' = IBKR open-time + bar duration. Do not change.
  persist_historical_bars: true     # write completed-session bars to historical_bars table
```

`bar_buffer_size` must be read by `MarketDataAgent` and `BarBuffer` — never hardcode 500 anywhere in the code.

---

### 3c. core/bar_buffer.py — New Module

Implement a thread-safe in-memory ring buffer.

```python
"""
core/bar_buffer.py

In-memory ring buffer for IBKR bar data.
One buffer instance per (instrument, timeframe) combination.
Max size is configurable via bar_buffer_size in config.yaml.
All timestamps stored as UTC ISO 8601 strings (bar close time).
Thread-safe: uses threading.Lock for all read/write operations.
"""
```

**Class: `BarBuffer`**

```python
class BarBuffer:
    def __init__(self, instrument: str, timeframe: int, max_size: int):
        ...
```

- `instrument`: str — e.g., "ES"
- `timeframe`: int — bar duration in minutes, e.g., 240, 60, 15, 5, 3, 1
- `max_size`: int — maximum bars to retain (from config `bar_buffer_size`)
- Internal storage: `collections.deque(maxlen=max_size)`
- All operations protected by `threading.Lock`

**Methods:**

`push(bar: dict) -> None`
- Appends bar to the right of the deque. Oldest bar is automatically evicted when `maxlen` is reached.
- Bar dict schema (all fields required):
  ```python
  {
      "instrument": str,       # "ES", "NQ", "YM"
      "timeframe": int,        # bar duration in minutes
      "timestamp": str,        # UTC ISO 8601, bar CLOSE time
      "open": float,
      "high": float,
      "low": float,
      "close": float,
      "volume": int
  }
  ```
- Raises `ValueError` if any required field is missing.

`get_bars(n: int = None) -> list[dict]`
- Returns list of bars, oldest first (chronological order).
- If `n` is specified, returns the last `n` bars. If buffer has fewer than `n` bars, returns all.
- Returns a copy — callers cannot mutate internal state.

`latest() -> dict | None`
- Returns the most recent bar, or None if buffer is empty.

`size() -> int`
- Returns current number of bars in buffer.

`clear() -> None`
- Empties the buffer.

**Module-level: `BufferManager`**

```python
class BufferManager:
    def __init__(self, instruments: list[str], timeframes: list[int], max_size: int):
        ...
```

- Creates one `BarBuffer` per (instrument, timeframe) pair on init.
- `instruments`: all three (traded + context)
- `timeframes`: `fvg_detection_timeframes` (all six — this is the superset)

`get(instrument: str, timeframe: int) -> BarBuffer`
- Returns the BarBuffer for the given pair. Raises `KeyError` if not found.

`push(instrument: str, timeframe: int, bar: dict) -> None`
- Delegates to the appropriate BarBuffer.

---

### 3d. core/database.py — Add historical_bars Table

Add a 9th table to the existing `_create_tables()` method. Do not modify any other table definition.

```sql
CREATE TABLE IF NOT EXISTS historical_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT NOT NULL,
    timeframe INTEGER NOT NULL,
    timestamp TEXT NOT NULL,        -- UTC ISO 8601, bar close time
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    session_date TEXT NOT NULL,     -- YYYY-MM-DD in America/New_York (the trading day this bar belongs to)
    created_at TEXT NOT NULL        -- UTC ISO 8601, when this record was written
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_bars_unique
    ON historical_bars (instrument, timeframe, timestamp);

CREATE INDEX IF NOT EXISTS idx_historical_bars_lookup
    ON historical_bars (instrument, timeframe, session_date);
```

Add a method to `DatabaseManager`:

```python
async def insert_historical_bars(self, bars: list[dict]) -> int:
    """
    Bulk insert bars into historical_bars.
    Uses INSERT OR IGNORE to handle duplicates gracefully.
    Returns count of rows actually inserted.
    bars: list of dicts matching the historical_bars schema (minus id, created_at — those are auto-set).
    """
```

- `created_at` is set server-side as `datetime.utcnow().isoformat() + 'Z'` inside this method — callers do not supply it.
- Batch in a single `executemany` call for performance.
- Log at DEBUG level: `"Inserted {n} historical bars"`.

---

### 3e. agents/market_data_agent.py — Full Implementation

```python
"""
agents/market_data_agent.py

Market Data Agent — Phase 2.
Responsibilities:
- Resolve IBKR Contract objects dynamically via reqContractDetails() at session start.
- Request real-time bar streams for 3 instruments × 6 timeframes = 18 streams.
- Normalize each bar: convert timestamp to bar-close UTC, validate fields.
- Push normalized bars to BarBuffer (in-memory).
- Persist completed-session bars to historical_bars table.
- Detect and log bar gaps without filling them.
- Handle reconnection per ibkr.reconnect_attempts config.
"""
```

**Class: `MarketDataAgent`**

```python
class MarketDataAgent:
    def __init__(self, config: dict, ibkr_client: IBKRClient, db: DatabaseManager, buffer_manager: BufferManager):
        ...
```

**Contract Resolution — `_resolve_contracts() -> dict[str, Contract]`**

- Called once at agent startup (before streaming begins).
- For each instrument in `[traded_instrument] + context_instruments`:
  - Build a `Contract` object: `symbol=instrument, secType='FUT', exchange='CME', currency='USD'`
    - NQ and ES use CME. YM uses CBOT. Use the correct exchange per instrument:
      - ES → exchange='CME'
      - NQ → exchange='CME'
      - YM → exchange='CBOT'
  - Call `reqContractDetails()` to get available contracts.
  - Select the front-month contract: the contract with the nearest expiry that is >= today's date.
  - Cache the resolved `Contract` in a dict keyed by instrument symbol string.
  - Log at INFO: `"Resolved {instrument}: {localSymbol} expiry {lastTradeDateOrContractMonth}"`
- If resolution fails for any instrument, raise `MarketDataError` with the instrument name.
- Re-resolve at the start of each new trading session (handles quarterly rolls).

**Bar Streaming — `start_streaming() -> None`**

- Uses `ib_insync` `reqRealTimeBars()` with `barSize=5` (5-second bars from IBKR). This is the only native real-time bar type IBKR supports via `reqRealTimeBars`.

  **Wait — important architectural note:** `reqRealTimeBars` only supports 5-second bars. For 1m, 3m, 5m, 15m, 60m, 240m bars, use `reqHistoricalData` with `keepUpToDate=True` and the appropriate `barSizeSetting` string. This is the correct IBKR approach for multi-timeframe streaming.

  Use `reqHistoricalData` with `keepUpToDate=True` for all 6 timeframes. IBKR `barSizeSetting` strings:
  - 1m → `"1 min"`
  - 3m → `"3 mins"`
  - 5m → `"5 mins"`
  - 15m → `"15 mins"`
  - 60m → `"1 hour"`
  - 240m → `"4 hours"`

  `durationStr` for initial history: `"2 D"` (2 days of history loads into the buffer on startup).

- Subscribe once per (instrument, timeframe) pair = 18 subscriptions total.
- Register a bar update callback per subscription via `ib_insync` event pattern (`bars.updateEvent`).

**Bar Normalization — `_normalize_bar(raw_bar, instrument: str, timeframe: int) -> dict`**

- Convert `raw_bar.date` (IBKR open time, can be `datetime` or `str`) to bar-close UTC:
  - Parse to `datetime` if string.
  - Add `timedelta(minutes=timeframe)` to get close time.
  - Convert to UTC if not already.
  - Format as ISO 8601 string: `"2026-04-26T14:01:00Z"`
- Return dict matching BarBuffer bar schema.
- Raise `ValueError` on malformed bar (log at WARNING, do not crash the stream).

**Bar Callback — `_on_bar_update(bars, has_new_bar: bool, instrument: str, timeframe: int)`**

- Called by ib_insync on each bar update.
- If `has_new_bar` is False: bar is an update to the current (incomplete) bar — update buffer's last entry in place. Do not push as a new bar.
- If `has_new_bar` is True: previous bar is now complete. Push it to the buffer.
- After pushing, call `_check_gap(instrument, timeframe, new_bar)`.
- If `persist_historical_bars` is True and bar is complete: call `_persist_bar(bar)`.

**Gap Detection — `_check_gap(instrument: str, timeframe: int, new_bar: dict) -> None`**

- Get `latest()` from the buffer (before the new bar is pushed — so this is the previous bar).
- If buffer is empty: no gap check possible, return.
- Calculate expected next bar open time: `previous_bar.close_time + timedelta(minutes=timeframe)`.
- If `new_bar.timestamp` != expected: log at WARNING:
  ```
  GAP DETECTED: {instrument} {timeframe}m — expected {expected}, got {actual}, gap={gap_minutes}m
  ```
- Log to `system_events` table via `db.log_event()`: type=`"bar_gap"`, detail=gap info as JSON.
- Do **not** fill the gap. Do not synthesize missing bars.

**Historical Persistence — `_persist_bar(bar: dict) -> None`**

- Compute `session_date`: the America/New_York date for the bar's close timestamp.
- Call `db.insert_historical_bars([bar_with_session_date])`.
- Fire-and-forget async call — do not await inline in the callback. Use `asyncio.create_task()`.

**Reconnection — `_reconnect() -> None`**

- If IBKR connection drops (detect via `ib_insync` disconnect event):
  - Log at ERROR: `"IBKR disconnected — attempting reconnect {attempt}/{max_attempts}"`
  - Retry `ibkr.reconnect_attempts` times with `ibkr.reconnect_delay` seconds between attempts.
  - On successful reconnect: re-resolve contracts, re-subscribe all 18 streams.
  - Log at INFO: `"IBKR reconnected — {18} streams re-subscribed"`
  - On all retries exhausted: log at CRITICAL, trigger kill switch via `KillSwitch.trigger()`, raise `MarketDataError`.
  - Log each reconnect attempt to `system_events` table.

**Public Methods:**

```python
async def start(self) -> None:
    """Resolve contracts, start streaming, begin event loop."""

async def stop(self) -> None:
    """Cancel all bar subscriptions, flush any pending persists, log SHUTDOWN."""

def get_buffer(self, instrument: str, timeframe: int) -> BarBuffer:
    """Convenience accessor — delegates to BufferManager.get()."""
```

**Error class:**

```python
class MarketDataError(Exception):
    pass
```

Define in `agents/market_data_agent.py`.

---

### 3f. main.py — Wire MarketDataAgent

Modify `main.py` to instantiate `MarketDataAgent` after `IBKRClient` connects. In dry-run mode, skip `MarketDataAgent.start()` (same pattern as IBKRClient skip). Add a `--dry-run` guard:

```python
if not args.dry_run:
    buffer_manager = BufferManager(
        instruments=[config['traded_instrument']] + config['context_instruments'],
        timeframes=config['fvg_detection_timeframes'],
        max_size=config['market_data']['bar_buffer_size']
    )
    mda = MarketDataAgent(config, ibkr_client, db, buffer_manager)
    await mda.start()
```

Do not add `MarketDataAgent` to dry-run path.

---

### 3g. tests/test_bar_buffer.py — New Test File

Write tests covering:

1. `BarBuffer` — push single bar, `latest()` returns it, `size()` == 1
2. `BarBuffer` — push `max_size + 10` bars, `size()` == `max_size` (eviction works)
3. `BarBuffer` — `get_bars(n=5)` on a buffer with 10 bars returns 5 bars in chronological order
4. `BarBuffer` — `push()` raises `ValueError` if a required field is missing
5. `BarBuffer` — `clear()` empties buffer, `size()` == 0, `latest()` == None
6. `BufferManager` — init creates correct number of buffers (3 instruments × 6 timeframes = 18)
7. `BufferManager` — `get()` raises `KeyError` for unknown (instrument, timeframe) pair
8. `BarBuffer` — thread safety: push 1000 bars from 10 concurrent threads, final `size()` == `max_size`, no exceptions

---

### 3h. tests/test_market_data.py — Replace Stub

Write tests covering:

1. `_normalize_bar()` — IBKR open-time datetime input produces correct close-time UTC ISO string for a 15m bar
2. `_normalize_bar()` — same for a 240m bar
3. `_normalize_bar()` — raises `ValueError` on None bar date
4. `_check_gap()` — no gap logged when bars are consecutive (no WARNING emitted)
5. `_check_gap()` — gap logged correctly when a bar is missing (WARNING emitted with correct gap minutes)
6. `historical_bars` table — `insert_historical_bars()` inserts a batch and returns correct count
7. `historical_bars` table — duplicate insert (same instrument/timeframe/timestamp) is silently ignored (INSERT OR IGNORE)
8. `DatabaseManager` — `_create_tables()` now creates 9 tables (was 8 in Phase 1)

Use `pytest-asyncio` for async tests. Mock IBKR calls — do not require a live TWS connection for tests.

---

### 3i. Logging Requirements

All new log messages must follow Phase 1 conventions: UTC timestamps, `apex.agents.market_data` logger name for the agent, `apex.core.bar_buffer` for the buffer module.

Key log events (in addition to gap detection above):
- Agent start: `INFO "MarketDataAgent starting — {n_instruments} instruments, {n_timeframes} timeframes, {n_streams} streams"`
- Each contract resolved: `INFO "Resolved {instrument}: {localSymbol} expiry {expiry}"`
- Each stream subscribed: `DEBUG "Subscribed {instrument} {timeframe}m"`
- Each completed bar received: `DEBUG "Bar: {instrument} {timeframe}m {timestamp} O={open} H={high} L={low} C={close} V={volume}"`
- Reconnect attempts: `ERROR "IBKR disconnected — attempting reconnect {attempt}/{max}"`
- Reconnect success: `INFO "IBKR reconnected — {n} streams re-subscribed"`

Do not log every partial bar update at DEBUG — only completed bars. Partial bar updates would flood the log at 18 streams.

---

## 4. Audit Checklist

After Claude Code completes Phase 2, return this spec to Claude (design). Claude (design) will pull from GitHub and verify each item below.

### 4a. Config
- [ ] `market_data` block present in `config.yaml` with `bar_buffer_size: 500`, `bar_timestamp_convention: close`, `persist_historical_bars: true`
- [ ] `bar_buffer_size` is read from config in both `BarBuffer` and `BufferManager` — value 500 does not appear hardcoded anywhere in source

### 4b. BarBuffer
- [ ] `core/bar_buffer.py` exists
- [ ] `BarBuffer` uses `collections.deque(maxlen=max_size)`
- [ ] `BarBuffer` uses `threading.Lock` on all read/write operations
- [ ] `push()` validates all required fields, raises `ValueError` on missing field
- [ ] `get_bars()` returns a copy, not a reference to internal deque
- [ ] `BufferManager` creates exactly `len(instruments) × len(timeframes)` buffers
- [ ] `BufferManager.get()` raises `KeyError` on unknown pair

### 4c. Database
- [ ] `historical_bars` table created in `_create_tables()` — 9th table
- [ ] Unique index on `(instrument, timeframe, timestamp)`
- [ ] Lookup index on `(instrument, timeframe, session_date)`
- [ ] `insert_historical_bars()` method exists, uses `INSERT OR IGNORE`, uses `executemany`
- [ ] `created_at` is set inside the method, not passed by callers

### 4d. MarketDataAgent
- [ ] `agents/market_data_agent.py` is fully implemented (not a stub)
- [ ] Contract resolution uses `reqContractDetails()` — no hardcoded expiry strings
- [ ] YM uses exchange `'CBOT'`, ES and NQ use `'CME'`
- [ ] Front-month selection: nearest expiry >= today
- [ ] Bar streaming uses `reqHistoricalData` with `keepUpToDate=True` for all 6 timeframes
- [ ] Correct IBKR `barSizeSetting` strings used for all 6 timeframes
- [ ] `_normalize_bar()` adds `timedelta(minutes=timeframe)` to IBKR open time to get close time
- [ ] `_normalize_bar()` outputs UTC ISO 8601 timestamp string ending in `Z`
- [ ] `has_new_bar=False` path updates current bar in place, does not push new bar
- [ ] `has_new_bar=True` path pushes completed bar to buffer
- [ ] Gap detection logs WARNING and logs to `system_events` — does not fill gaps
- [ ] `_persist_bar()` uses `asyncio.create_task()` — does not block callback
- [ ] `session_date` is America/New_York date of bar close time
- [ ] Reconnect retries `ibkr.reconnect_attempts` times with `ibkr.reconnect_delay` delay
- [ ] Reconnect exhaustion triggers kill switch and raises `MarketDataError`
- [ ] `MarketDataError` class defined in the agent module
- [ ] `start()` and `stop()` are async
- [ ] Dry-run guard in `main.py` — `MarketDataAgent` not instantiated in dry-run mode

### 4e. Tests
- [ ] `tests/test_bar_buffer.py` exists with 8 tests as specified
- [ ] `tests/test_market_data.py` has 8 real tests (not the Phase 1 stub)
- [ ] Thread safety test in `test_bar_buffer.py` runs 10 threads
- [ ] All tests pass: `pytest` green
- [ ] Total test count is >= 33 (25 Phase 1 + 8 buffer + 8 market data — some may overlap with prior stubs)

### 4f. No Phase Creep
- [ ] No session window logic implemented (Phase 3)
- [ ] No kill zone cutoff enforcement (Phase 3)
- [ ] No news filtering (Phase 3)
- [ ] No signal or setup detection (Phase 4)
- [ ] No modifications to Phase 1 modules beyond what this spec explicitly requires (`database.py` table addition, `main.py` wiring)

### 4g. Code Quality
- [ ] No hardcoded credentials, symbols, or magic numbers
- [ ] Logger names follow `apex.agents.market_data` and `apex.core.bar_buffer` convention
- [ ] All new async functions are properly awaited
- [ ] `asyncio.create_task()` used for fire-and-forget persist calls (not `await` inline in callback)
- [ ] Git commit is clean with a descriptive message referencing Phase 2

---

## 5. Decisions Made in This Phase (for future reference)

| Decision | Choice | Rationale |
|---|---|---|
| Bar buffer storage | Memory-only ring buffer (`collections.deque`) | Keeps live pipeline fast; no SQLite write latency on every bar |
| Historical persistence | Separate `historical_bars` table, all 18 streams | Cheap storage, full post-mortem data for all instruments/timeframes |
| Bar timestamp convention | Bar close time | Consistent with ICT methodology; IBKR open time + bar duration |
| Contract resolution | Dynamic `reqContractDetails()` at session start | Handles quarterly rolls automatically; cached for session lifetime |
| Bar streaming method | `reqHistoricalData` with `keepUpToDate=True` | Only correct IBKR method for multi-timeframe streaming beyond 5-second bars |
| Buffer size | 500 bars per (instrument, timeframe), config-driven | Sufficient for all planned indicator lookback; user-adjustable via `bar_buffer_size` |
| Gap handling | Log + system_events, no fill | Silent gap fills corrupt ICT setups that depend on bar sequence integrity |
| Reconnect on failure | Retry N times, then kill switch | Safety over availability — a bad data feed is worse than no trading |
