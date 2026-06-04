import json
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1] / "auto_agent" / "data" / "pipeline.json"

LEGACY_STEPS = {
    "step_1a", "step_1_strategy", "step_1_fresh", "step_1_vault_lookup",
    "step_1d_wiki_compile", "step_1b", "step_1c",
    "step_2_draft", "step_2_target", "step_2_target_register",
    "step_2_target_deepen", "step_2_manuscript",
}


def _all_steps():
    p = json.loads(PIPELINE.read_text(encoding="utf-8"))
    out = {}
    for ph in p["phases"]:
        for s in ph.get("steps", []):
            out[s["id"]] = s
    return out


def test_v4bridge_step_exists_and_is_module():
    steps = _all_steps()
    assert "step_1_v4bridge" in steps
    s = steps["step_1_v4bridge"]
    assert s["type"] == "module"
    assert s["module"] == "v4_bridge_adapter"
    assert not s.get("legacy_only")  # 표준 스텝은 게이팅 안 됨


def test_v4bridge_is_first_in_stage_1():
    p = json.loads(PIPELINE.read_text(encoding="utf-8"))
    stage1 = next(ph for ph in p["phases"] if ph["id"] == "stage_1")
    assert stage1["steps"][0]["id"] == "step_1_v4bridge"


def test_native_stage12_steps_are_legacy_only():
    steps = _all_steps()
    for sid in LEGACY_STEPS:
        assert steps.get(sid, {}).get("legacy_only") is True, f"{sid} legacy_only 누락"


def test_chapters_step_not_legacy():
    steps = _all_steps()
    assert not steps["step_2"].get("legacy_only")  # 씬분할은 v4-bridge 경로에서도 실행
