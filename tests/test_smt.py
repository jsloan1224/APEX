import pytest

from agents.smt_agent import SMTAgent


def test_smt_agent_importable():
    assert SMTAgent is not None


def test_smt_agent_instantiates_without_error():
    agent = SMTAgent()
    assert agent is not None


def test_smt_agent_instantiates_with_config():
    agent = SMTAgent(config={'smt_check_timeframes': [5, 1]})
    assert agent.config == {'smt_check_timeframes': [5, 1]}
