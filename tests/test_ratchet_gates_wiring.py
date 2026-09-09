"""원고 게이트 / 씬 게이트 배선 검증.

CLAUDE.md가 오랫동안 "래칫 리뷰 루프"를 있다고 적어 왔지만 pipeline.json에는
리뷰어 스텝이 step_0d(기획안) 하나뿐이었다. 문서와 배선이 다시 갈라지지 않도록
여기서 못박는다.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "auto_agent" / "data" / "pipeline.json"
AGENTS = ROOT / "auto_agent" / "data" / "agents.json"
SKILLS = ROOT / "auto_agent" / "data" / "skills"


def _steps():
    p = json.loads(PIPELINE.read_text(encoding="utf-8"))
    out = {}
    order = []
    for ph in p["phases"]:
        for s in ph.get("steps", []):
            out[s["id"]] = s
            order.append(s["id"])
    return out, order


def _agents():
    return json.loads(AGENTS.read_text(encoding="utf-8"))["agents"]


# ── 에이전트 등록 ───────────────────────────────────────────────

def test_manuscript_reviewer_is_registered():
    a = _agents()
    assert "manuscript-reviewer" in a
    assert a["manuscript-reviewer"]["skill_file"] == "agents/manuscript-reviewer/SKILL.md"


def test_manuscript_reviewer_skill_file_exists():
    a = _agents()["manuscript-reviewer"]
    assert (SKILLS / a["skill_file"]).is_file()


def test_manuscript_reviewer_can_edit():
    """자체 래칫 루프에서 원고를 직접 고쳐 써야 하므로 쓰기 권한이 필요하다."""
    tools = _agents()["manuscript-reviewer"]["allowed_tools"]
    assert "Write" in tools and "Read" in tools


def test_script_reviewer_still_registered():
    assert "script-reviewer" in _agents()


# ── 배선 ────────────────────────────────────────────────────────

def test_both_gates_are_wired():
    steps, _ = _steps()
    assert "step_2_manuscript_review" in steps, "원고 게이트 미배선"
    assert "step_2_review" in steps, "씬 게이트 미배선"


def test_gates_use_the_right_agents():
    steps, _ = _steps()
    assert steps["step_2_manuscript_review"]["agent"] == "manuscript-reviewer"
    assert steps["step_2_review"]["agent"] == "script-reviewer"


def test_manuscript_gate_runs_before_scene_split():
    """원고를 고칠 수 있는 마지막 지점 — step_2가 narration을 substring으로 가져간다."""
    _, order = _steps()
    assert order.index("step_2_manuscript") < order.index("step_2_manuscript_review")
    assert order.index("step_2_manuscript_review") < order.index("step_2_plan")
    assert order.index("step_2_manuscript_review") < order.index("step_2")


def test_scene_gate_runs_after_scene_split_and_before_factcheck():
    _, order = _steps()
    assert order.index("step_2") < order.index("step_2_review")
    assert order.index("step_2_review") < order.index("step_2b")


# ── 게이트 성질 ─────────────────────────────────────────────────

def test_gates_are_non_blocking():
    """점수 미달로 파이프라인 전체를 세우지 않는다 — step_0d와 같은 취급."""
    steps, _ = _steps()
    for sid in ("step_2_manuscript_review", "step_2_review"):
        assert steps[sid]["blocking"] is False, f"{sid}가 blocking"


def test_gates_skip_resume():
    """래칫은 출력 파일이 있어도 다시 돌아야 한다."""
    steps, _ = _steps()
    for sid in ("step_2_manuscript_review", "step_2_review"):
        assert steps[sid]["skip_resume"] is True, f"{sid} skip_resume 누락"


def test_manuscript_gate_pairs_with_native_manuscript_step():
    """v4-bridge 원작 프로젝트는 PD가 이미 개정했으므로 원고 게이트를 건너뛴다.

    step_2_manuscript과 같은 legacy_only를 달아 둘이 함께 켜지고 함께 꺼지게 한다.
    """
    steps, _ = _steps()
    assert steps["step_2_manuscript"].get("legacy_only") is True
    assert steps["step_2_manuscript_review"].get("legacy_only") is True


def test_scene_gate_runs_on_both_paths():
    """씬분할은 v4 경로에서도 돌므로 씬 게이트도 게이팅되면 안 된다."""
    steps, _ = _steps()
    assert not steps["step_2"].get("legacy_only")
    assert not steps["step_2_review"].get("legacy_only")


def test_gate_outputs_do_not_collide():
    steps, _ = _steps()
    a = set(steps["step_2_manuscript_review"]["output"])
    b = set(steps["step_2_review"]["output"])
    assert not (a & b), f"산출물 충돌: {a & b}"
