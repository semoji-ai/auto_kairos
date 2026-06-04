import sys

from auto_agent.orchestrator.runner import is_legacy_gated, build_adapter_cmd


def test_build_adapter_cmd_basic():
    cmd = build_adapter_cmd("/proj/abc_slug", "quirky_cartoon", None)
    assert cmd == [
        sys.executable, "-m", "auto_agent.modules.v4_bridge.adapter",
        "--project", "/proj/abc_slug", "--style-id", "quirky_cartoon",
    ]


def test_build_adapter_cmd_strips_json_and_path():
    cmd = build_adapter_cmd("/proj/x", "styles/semoji.json", "dark")
    assert "--style-id" in cmd
    assert cmd[cmd.index("--style-id") + 1] == "semoji"
    assert cmd[-2:] == ["--theme", "dark"]


def test_build_adapter_cmd_ignores_invalid_theme():
    cmd = build_adapter_cmd("/proj/x", "lego", "weird")
    assert "--theme" not in cmd


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


def test_build_adapter_cmd_empty_style_falls_back():
    cmd = build_adapter_cmd("/proj/x", "styles/", None)
    assert cmd[cmd.index("--style-id") + 1] == "quirky_cartoon"
