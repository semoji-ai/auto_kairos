from auto_agent.orchestrator.runner import is_legacy_gated


def test_legacy_only_step_gated_when_flag_off():
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=False) is True


def test_legacy_only_step_runs_when_flag_on():
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=True) is False


def test_non_legacy_step_never_gated():
    step = {"id": "step_2", "name": "chapters"}
    assert is_legacy_gated(step, enable_legacy=False) is False
    assert is_legacy_gated(step, enable_legacy=True) is False
