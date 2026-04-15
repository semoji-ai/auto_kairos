# tests/test_runner_until.py
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def _make_steps():
    return [
        {"id": "step_1a", "phase": "stage_1"},
        {"id": "step_2_draft", "phase": "stage_2"},
        {"id": "step_2b", "phase": "stage_2"},
        {"id": "step_3b", "phase": "stage_3"},
    ]

def test_stop_after_step_excludes_later_steps():
    """stop_after_step='step_2b'이면 step_3b는 실행되지 않아야 한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after="step_2b")
    ids = [s["id"] for s in result]
    assert "step_3b" not in ids
    assert "step_2b" in ids

def test_stop_after_step_includes_target():
    """stop_after_step 대상 step 자체는 포함되어야 한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after="step_2_draft")
    ids = [s["id"] for s in result]
    assert "step_2_draft" in ids
    assert "step_2b" not in ids

def test_stop_after_none_returns_all():
    """stop_after=None이면 전체 steps를 그대로 반환한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after=None)
    assert len(result) == len(steps)

def test_stop_after_unknown_raises():
    """존재하지 않는 step_id를 지정하면 ValueError를 발생시킨다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    with pytest.raises(ValueError, match="stop_after"):
        _filter_steps_until(steps, stop_after="step_999")

def test_stop_after_last_step_returns_all():
    """stop_after가 마지막 step이면 전체를 반환해야 한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after="step_3b")
    assert len(result) == len(steps)
