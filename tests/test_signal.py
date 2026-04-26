from datetime import datetime, timezone
import pytest

from core.signal import SignalCandidate


def make_signal(**overrides) -> SignalCandidate:
    now = datetime.now(timezone.utc)
    defaults = dict(
        signal_id='SIG-001',
        created_at=now,
        traded_instrument='ES',
        direction='bullish',
        model_name='silver_bullet',
        bias_timeframes=[240, 60, 15],
        bias_per_timeframe={240: 'bullish', 60: 'bullish', 15: 'bullish'},
        bias_alignment=True,
        bias_alignment_checked_at=now,
        fvg_timeframe=1,
    )
    defaults.update(overrides)
    return SignalCandidate(**defaults)


def test_signal_instantiates_with_required_fields():
    sig = make_signal()
    assert sig.signal_id == 'SIG-001'
    assert sig.traded_instrument == 'ES'
    assert sig.direction == 'bullish'


def test_bias_timeframes_stored_correctly():
    sig = make_signal()
    assert sig.bias_timeframes == [240, 60, 15]
    assert sig.bias_per_timeframe == {240: 'bullish', 60: 'bullish', 15: 'bullish'}
    assert sig.bias_alignment is True


def test_smt_context_fields_default_empty():
    sig = make_signal()
    assert sig.sister_1_symbol == ''
    assert sig.sister_1_bias == ''
    assert sig.sister_1_smt_divergence is False
    assert sig.sister_2_symbol == ''
    assert sig.sister_2_bias == ''
    assert sig.sister_2_smt_divergence is False


def test_ai_gate_fields_default_none():
    sig = make_signal()
    assert sig.ai_gate_displacement_score is None
    assert sig.ai_gate_sweep_score is None
    assert sig.ai_gate_environment_score is None
    assert sig.ai_gate_average is None
    assert sig.ai_gate_latency_ms is None
    assert sig.ai_gate_result == ''
    assert sig.ai_gate_reason == ''


def test_traded_instrument_field_not_market():
    sig = make_signal(traded_instrument='NQ')
    assert hasattr(sig, 'traded_instrument')
    assert not hasattr(sig, 'market')
    assert sig.traded_instrument == 'NQ'
