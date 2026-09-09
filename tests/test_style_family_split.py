"""문체 스킬 3분할(narrative / voice / direction) + 윤문 전담 스텝 검증.

배경: 예전에는 활성 writing-style 스킬을 모든 에이전트에 자동 주입하고,
`<project_config>`로 "문체 필수 적용" 지시를 무조건 넣었다. 그 탓에 초고 작가가
규칙서 없이 문체 규격만 요구받았고, 형식을 맞추느라 내용이 밀렸다.

이제 구성(narrative)은 초고부터, 문체(voice)는 윤문 단계부터, 연출(direction)은
씬분할부터 적용한다.
"""
import json
from pathlib import Path

import pytest

from auto_agent.orchestrator.runner import PipelineRunner

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "auto_agent" / "data" / "pipeline.json"
AGENTS = ROOT / "auto_agent" / "data" / "agents.json"
SHARED = ROOT / "auto_agent" / "data" / "skills" / "shared"

FAMILIES = ("narrative", "voice", "direction")
STYLES = ("semoji", "iromism")


class _Stub:
    """_resolve_style_skills / _step_applies_voice는 config만 본다."""

    _STYLE_FAMILIES = PipelineRunner._STYLE_FAMILIES
    _STYLE_VARIANTS = PipelineRunner._STYLE_VARIANTS
    _resolve_style_skills = PipelineRunner._resolve_style_skills
    _step_applies_voice = PipelineRunner._step_applies_voice

    def __init__(self, writing_style=""):
        self.state = type("S", (), {"config": {"writing_style": writing_style}})()


def _steps():
    p = json.loads(PIPELINE.read_text(encoding="utf-8"))
    out, order = {}, []
    for ph in p["phases"]:
        for s in ph.get("steps", []):
            out[s["id"]] = s
            order.append(s["id"])
    return out, order


def _style_families(step):
    return {s.split("/")[-1] for s in step.get("skills", []) if s.startswith("style/")}


# ── 스킬 파일 ───────────────────────────────────────────────────

@pytest.mark.parametrize("family", FAMILIES)
@pytest.mark.parametrize("style", STYLES)
def test_split_skill_files_exist(family, style):
    assert (SHARED / f"{family}-{style}.md").is_file()


@pytest.mark.parametrize("style", STYLES)
def test_voice_carries_the_frequency_rules_not_narrative(style):
    """빈도 규격은 문체 쪽에만 있어야 한다 — 초고 작가가 떠안으면 안 된다."""
    voice = (SHARED / f"voice-{style}.md").read_text(encoding="utf-8")
    narrative = (SHARED / f"narrative-{style}.md").read_text(encoding="utf-8")
    marker = "그런데" if style == "semoji" else "자문자답"
    assert marker in voice, f"voice-{style}에 시그니처 규격 누락"
    assert "회" in voice
    # 구성 파일이 문체 규격을 다시 요구하면 분리가 무의미해진다
    assert "번역체" not in narrative, f"narrative-{style}에 문체 규칙 잔존"


@pytest.mark.parametrize("style", STYLES)
def test_voice_forbids_inventing_facts_to_meet_quota(style):
    """리듬을 채우려고 사실을 지어내지 말라는 금지가 문체 스킬에 있어야 한다."""
    voice = (SHARED / f"voice-{style}.md").read_text(encoding="utf-8")
    assert "사실을 바꾸지 않습니다" in voice


# ── 해석 로직 ───────────────────────────────────────────────────

def test_style_family_resolves_to_active_writing_style():
    r = _Stub("semoji")
    assert r._resolve_style_skills(["style/narrative"]) == ["narrative-semoji"]
    assert r._resolve_style_skills(["style/voice"]) == ["voice-semoji"]


def test_other_style_variant_is_dropped():
    """이로미즘 프로젝트에 세모지 문체가 섞이지 않는다."""
    r = _Stub("iromism")
    assert r._resolve_style_skills(["voice-semoji", "style/voice"]) == ["voice-iromism"]


def test_no_writing_style_drops_style_families():
    r = _Stub("")
    assert r._resolve_style_skills(["style/voice", "shared/writing-style"]) == ["shared/writing-style"]


def test_non_style_skills_pass_through_in_order():
    r = _Stub("semoji")
    got = r._resolve_style_skills(["style/narrative", "shared/motion-presets"])
    assert got == ["narrative-semoji", "shared/motion-presets"]


def test_voice_directive_only_when_step_takes_voice():
    r = _Stub("semoji")
    assert r._step_applies_voice({"skills": ["style/narrative"]}) is False
    assert r._step_applies_voice({"skills": ["style/narrative", "style/voice"]}) is True
    assert r._step_applies_voice({"skills": []}) is False


# ── 단계별 배정 ─────────────────────────────────────────────────

def test_draft_gets_narrative_but_not_voice():
    """이번 변경의 핵심 — 초고는 구성만 받는다."""
    steps, _ = _steps()
    fam = _style_families(steps["step_2_draft"])
    assert "narrative" in fam
    assert "voice" not in fam, "초고가 아직 문체를 떠안고 있다"


def test_manuscript_gets_narrative_but_not_voice():
    steps, _ = _steps()
    fam = _style_families(steps["step_2_manuscript"])
    assert "narrative" in fam
    assert "voice" not in fam


def test_polish_step_is_wired_with_voice():
    steps, _ = _steps()
    assert "step_2_polish" in steps, "윤문 스텝 미배선"
    s = steps["step_2_polish"]
    assert s["agent"] == "script-polisher"
    assert _style_families(s) == {"narrative", "voice"}


def test_polish_runs_between_manuscript_and_gate():
    _, order = _steps()
    assert order.index("step_2_manuscript") < order.index("step_2_polish")
    assert order.index("step_2_polish") < order.index("step_2_manuscript_review")
    assert order.index("step_2_polish") < order.index("step_2")


def test_scene_split_gets_direction_not_voice():
    """씬분할은 나레이션을 재작성하지 않으므로 문체가 필요 없다."""
    steps, _ = _steps()
    fam = _style_families(steps["step_2"])
    assert "direction" in fam
    assert "voice" not in fam


def test_scene_gate_sees_all_three_families():
    """script-reviewer는 문체와 연출을 모두 채점한다."""
    steps, _ = _steps()
    assert _style_families(steps["step_2_review"]) == {"narrative", "voice", "direction"}


def test_polisher_agent_registered_with_write_access():
    a = json.loads(AGENTS.read_text(encoding="utf-8"))["agents"]
    assert "script-polisher" in a
    assert a["script-polisher"]["skill_file"] == "agents/script-polisher/SKILL.md"
    assert "Write" in a["script-polisher"]["allowed_tools"]


def test_polisher_skill_forbids_touching_figures():
    sk = (ROOT / "auto_agent" / "data" / "skills" / "agents" / "script-polisher" / "SKILL.md")
    text = sk.read_text(encoding="utf-8")
    assert "내용 불변" in text
    assert "fact_fix_log.json" in text, "정정 우선순위 규칙 누락"


def test_polish_pairs_with_native_manuscript_path():
    """v4-bridge 원작은 PD가 이미 윤문했으므로 함께 꺼진다."""
    steps, _ = _steps()
    assert steps["step_2_polish"].get("legacy_only") is True
    assert steps["step_2_manuscript"].get("legacy_only") is True
