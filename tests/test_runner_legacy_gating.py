import sys
from pathlib import Path

from auto_agent.orchestrator.runner import (
    PipelineRunner,
    is_legacy_gated,
    build_adapter_cmd,
    result_bucket,
)


class _StubRunner:
    """_has_v4_artifacts는 project_dir만 본다 — 전체 러너를 세우지 않는다."""

    def __init__(self, project_dir: Path):
        self.project_dir = project_dir

    has_v4_artifacts = PipelineRunner._has_v4_artifacts


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


def test_build_adapter_cmd_empty_style_falls_back():
    cmd = build_adapter_cmd("/proj/x", "styles/", None)
    assert cmd[cmd.index("--style-id") + 1] == "quirky_cartoon"


# ── legacy 게이팅 ───────────────────────────────────────────────
# v5 기준(docs/v5-plan.md): v3 네이티브가 줄기다. v4-bridge는 PD가 v4 산출물을
# 실제로 만들어 둔 프로젝트에서만 켜지는 갈래다.

def test_legacy_only_runs_when_no_v4_artifacts():
    """v4 산출물이 없으면 네이티브 v3 stage 1/2가 기본 경로다."""
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=False, v4_artifacts=False) is False


def test_legacy_only_gated_in_v4_bridge_project():
    """v4 산출물이 있으면 네이티브 스텝이 그것을 덮어쓰지 않도록 막는다."""
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=False, v4_artifacts=True) is True


def test_enable_legacy_overrides_v4_project():
    """ENABLE_LEGACY_V3=1은 v4 프로젝트에서도 네이티브 경로를 강제 복구한다."""
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=True, v4_artifacts=True) is False


def test_v4_artifacts_defaults_to_absent():
    """인자를 생략하면 v4 산출물 없음 — 네이티브 경로."""
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=False) is False


def test_non_legacy_step_never_gated():
    step = {"id": "step_2", "name": "chapters"}
    for legacy in (True, False):
        for v4 in (True, False):
            assert is_legacy_gated(step, enable_legacy=legacy, v4_artifacts=v4) is False


# ── 결과 버킷 분류 ──────────────────────────────────────────────
# skipped는 completed도 failed도 아닌 3번째 상태다. 순차 경로가 skipped를
# completed_steps로, 병렬 경로가 failed_steps로 넣던 불일치를 한곳으로 모은다.

def test_completed_goes_to_completed_steps():
    assert result_bucket("completed") == "completed_steps"


def test_skipped_goes_to_skipped_steps():
    assert result_bucket("skipped") == "skipped_steps"


def test_failed_goes_to_failed_steps():
    assert result_bucket("failed") == "failed_steps"


def test_unknown_status_treated_as_failure():
    """모르는 상태를 성공으로 세지 않는다."""
    assert result_bucket("") == "failed_steps"
    assert result_bucket("weird") == "failed_steps"


# ── v4 산출물 탐지 ──────────────────────────────────────────────

def test_no_v4_artifacts_in_empty_project(tmp_path):
    assert _StubRunner(tmp_path).has_v4_artifacts() is False


def test_marked_manuscript_counts_as_v4_artifact(tmp_path):
    """어댑터 실행 전 — PD가 마커 원고를 놓아 둔 상태."""
    (tmp_path / "final_manuscript_marked.md").write_text("# Ch 1.\n", encoding="utf-8")
    assert _StubRunner(tmp_path).has_v4_artifacts() is True


def test_sentinel_counts_as_v4_artifact(tmp_path):
    """어댑터 실행 후 — 마커 원고가 정리돼도 sentinel로 판별한다."""
    (tmp_path / ".v4_bridge_origin").write_text("", encoding="utf-8")
    assert _StubRunner(tmp_path).has_v4_artifacts() is True


def test_v3_native_manuscript_is_not_a_v4_artifact(tmp_path):
    """네이티브 경로 산출물(final_manuscript.md)은 게이팅 근거가 아니다."""
    (tmp_path / "final_manuscript.md").write_text("본문", encoding="utf-8")
    assert _StubRunner(tmp_path).has_v4_artifacts() is False
