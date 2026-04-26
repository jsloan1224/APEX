import threading

import pytest

from core.bar_buffer import BarBuffer, BufferManager

INSTRUMENTS = ['ES', 'NQ', 'YM']
TIMEFRAMES = [240, 60, 15, 5, 3, 1]


def make_bar(instrument='ES', timeframe=1, timestamp='2026-04-26T10:00:00Z',
             open_=4500.0, high=4510.0, low=4490.0, close=4505.0, volume=1000):
    return {
        'instrument': instrument,
        'timeframe': timeframe,
        'timestamp': timestamp,
        'open': open_,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    }


def test_push_single_bar_latest_and_size():
    buf = BarBuffer('ES', 1, 100)
    bar = make_bar()
    buf.push(bar)
    assert buf.size() == 1
    assert buf.latest() == bar


def test_push_overflow_evicts_oldest():
    max_size = 10
    buf = BarBuffer('ES', 1, max_size)
    for i in range(max_size + 10):
        buf.push(make_bar(timestamp=f'2026-04-26T{i // 60:02d}:{i % 60:02d}:00Z'))
    assert buf.size() == max_size


def test_get_bars_returns_last_n_in_order():
    buf = BarBuffer('ES', 1, 100)
    for i in range(10):
        buf.push(make_bar(timestamp=f'2026-04-26T10:{i:02d}:00Z', close=float(4500 + i)))
    result = buf.get_bars(n=5)
    assert len(result) == 5
    # chronological order: oldest first
    closes = [b['close'] for b in result]
    assert closes == sorted(closes)
    assert closes == [4505.0, 4506.0, 4507.0, 4508.0, 4509.0]


def test_push_missing_field_raises_value_error():
    buf = BarBuffer('ES', 1, 100)
    bad_bar = {'instrument': 'ES', 'timeframe': 1, 'timestamp': '2026-04-26T10:00:00Z'}
    with pytest.raises(ValueError):
        buf.push(bad_bar)


def test_clear_empties_buffer():
    buf = BarBuffer('ES', 1, 100)
    buf.push(make_bar())
    buf.push(make_bar())
    buf.clear()
    assert buf.size() == 0
    assert buf.latest() is None


def test_buffer_manager_creates_correct_number_of_buffers():
    bm = BufferManager(instruments=INSTRUMENTS, timeframes=TIMEFRAMES, max_size=500)
    expected = len(INSTRUMENTS) * len(TIMEFRAMES)
    count = 0
    for inst in INSTRUMENTS:
        for tf in TIMEFRAMES:
            bm.get(inst, tf)  # raises if missing
            count += 1
    assert count == expected  # 3 × 6 = 18


def test_buffer_manager_get_unknown_pair_raises_key_error():
    bm = BufferManager(instruments=['ES'], timeframes=[1], max_size=100)
    with pytest.raises(KeyError):
        bm.get('CL', 1)
    with pytest.raises(KeyError):
        bm.get('ES', 999)


def test_bar_buffer_thread_safety():
    buf = BarBuffer('ES', 1, 500)
    errors = []

    def push_bars():
        for i in range(100):
            try:
                buf.push(make_bar(timestamp='2026-04-26T10:00:00Z'))
            except Exception as exc:
                errors.append(exc)

    threads = [threading.Thread(target=push_bars) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f'Thread errors: {errors}'
    assert buf.size() == 500  # 1000 pushes, maxlen=500
