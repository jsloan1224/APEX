"""
core/bar_buffer.py

In-memory ring buffer for IBKR bar data.
One buffer instance per (instrument, timeframe) combination.
Max size is configurable via bar_buffer_size in config.yaml.
All timestamps stored as UTC ISO 8601 strings (bar close time).
Thread-safe: uses threading.Lock for all read/write operations.
"""
import collections
import threading

from core.logger import get_logger

logger = get_logger('apex.core.bar_buffer')

REQUIRED_BAR_FIELDS = frozenset({
    'instrument', 'timeframe', 'timestamp', 'open', 'high', 'low', 'close', 'volume'
})


class BarBuffer:
    def __init__(self, instrument: str, timeframe: int, max_size: int):
        self.instrument = instrument
        self.timeframe = timeframe
        self.max_size = max_size
        self._deque: collections.deque = collections.deque(maxlen=max_size)
        self._lock = threading.Lock()

    def push(self, bar: dict) -> None:
        missing = REQUIRED_BAR_FIELDS - set(bar.keys())
        if missing:
            raise ValueError(f'Bar missing required fields: {missing}')
        with self._lock:
            self._deque.append(bar)

    def replace_last(self, bar: dict) -> None:
        missing = REQUIRED_BAR_FIELDS - set(bar.keys())
        if missing:
            raise ValueError(f'Bar missing required fields: {missing}')
        with self._lock:
            if self._deque:
                self._deque[-1] = bar

    def get_bars(self, n: int = None) -> list:
        with self._lock:
            bars = list(self._deque)
        if n is not None:
            bars = bars[-n:]
        return bars

    def latest(self) -> dict | None:
        with self._lock:
            if not self._deque:
                return None
            return dict(self._deque[-1])

    def size(self) -> int:
        with self._lock:
            return len(self._deque)

    def clear(self) -> None:
        with self._lock:
            self._deque.clear()


class BufferManager:
    def __init__(self, instruments: list, timeframes: list, max_size: int):
        self._buffers: dict = {}
        for instrument in instruments:
            for timeframe in timeframes:
                self._buffers[(instrument, timeframe)] = BarBuffer(instrument, timeframe, max_size)
        logger.debug(
            'BufferManager initialized: %d buffers (%d instruments × %d timeframes)',
            len(self._buffers), len(instruments), len(timeframes),
        )

    def get(self, instrument: str, timeframe: int) -> BarBuffer:
        key = (instrument, timeframe)
        if key not in self._buffers:
            raise KeyError(f'No buffer for ({instrument}, {timeframe}m)')
        return self._buffers[key]

    def push(self, instrument: str, timeframe: int, bar: dict) -> None:
        self.get(instrument, timeframe).push(bar)
