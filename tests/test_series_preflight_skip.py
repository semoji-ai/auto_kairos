"""시리즈 모드 브리프 상속 + 브리프 주입 제외 검증.

docs/token-waste-audit.md 2번/4번 항목.
"""
import json
from pathlib import Path

import pytest

from auto_agent.orchestrator import runner as runner_mod
from auto_agent.orchestrator.runner import PipelineRunner


@pytest.fixture
def fake_runner(tmp_path):
    """DB/프로젝트 없이 판별 메서드만 검사하기 위한 최소 인스턴스."""
    r = PipelineRunner.__new__(PipelineRunner)
    r.project_dir = tmp_path
    return r


def test_no_brief_files_is_not_series(fake_runner):
    assert fake_runner._has_series_brief() is False


def test_plain_brief_is_not_series(fake_runner, tmp_path):
    """단독 프로젝트 브리프(_series 없음)는 상속 대상이 아니다."""
    (tmp_path / "editorial_brief.json").write_text(
        json.dumps({"core_question": "q"}, ensure_ascii=False), encoding="utf-8"
    )
    assert fake_runner._has_series_brief() is False


def test_series_brief_detected(fake_runner, tmp_path):
    (tmp_path / "episode_brief.json").write_text(
        json.dumps(
            {"core_question": "q", "_series": {"series_id": "lg", "episode_number": 3}},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    assert fake_runner._has_series_brief() is True


def test_corrupt_brief_does_not_raise(fake_runner, tmp_path):
    """깨진 JSON이 있어도 예외 없이 False."""
    (tmp_path / "editorial_brief.json").write_text("{not json", encoding="utf-8")
    assert fake_runner._has_series_brief() is False


def test_skip_list_covers_preflight_agents():
    """브리프 주입 제외 목록에 preflight 계열이 포함됐는지 (소스 기준)."""
    src = Path(runner_mod.__file__).read_text(encoding="utf-8")
    marker = "_skip_brief_agents = {"
    block = src[src.index(marker) : src.index("}", src.index(marker))]
    for agent in ("config-inspector", "brief-interviewer-auto",
                  "data-mapper", "fact-verifier", "assembly-director"):
        assert agent in block, f"{agent} 누락"


def test_series_inherit_steps_declared():
    """step_0b/step_0d가 시리즈 상속 스킵 대상으로 선언됐는지."""
    src = Path(runner_mod.__file__).read_text(encoding="utf-8")
    marker = "_series_inherit_steps = {"
    block = src[src.index(marker) : src.index("}", src.index(marker))]
    assert "step_0b" in block and "step_0d" in block
