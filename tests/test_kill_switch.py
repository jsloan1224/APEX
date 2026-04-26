import pytest

from agents.risk_manager import KillSwitch


def make_config() -> dict:
    return {
        'risk': {
            'max_daily_loss_usd': 500,
            'max_drawdown_usd': 300,
            'max_consecutive_losses': 3,
            'cool_off_minutes': 30,
            'news_window_minutes': 10,
            'max_open_positions': 1,
        }
    }


def test_kill_switch_instantiates():
    ks = KillSwitch(make_config())
    assert ks.max_daily_loss_usd == 500
    assert ks.max_drawdown_usd == 300
    assert ks.max_consecutive_losses == 3
    assert ks.cool_off_minutes == 30
    assert ks.news_window_minutes == 10
    assert ks.max_open_positions == 1
    assert ks.triggered is False
    assert ks.trigger_reason is None


def test_check_returns_false_with_zero_inputs():
    ks = KillSwitch(make_config())
    result = ks.check(daily_pnl=0.0, drawdown=0.0, open_positions=0, consecutive_losses=0)
    assert result is False


def test_trigger_sets_flag_and_reason():
    ks = KillSwitch(make_config())
    ks.trigger('max daily loss hit')
    assert ks.triggered is True
    assert ks.trigger_reason == 'max daily loss hit'


def test_reset_clears_flag_and_reason():
    ks = KillSwitch(make_config())
    ks.trigger('test')
    ks.reset()
    assert ks.triggered is False
    assert ks.trigger_reason is None
