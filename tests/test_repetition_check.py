"""연속 씬(±2) 같은 카메라·연출 검사."""
import json
import subprocess
import sys
from pathlib import Path

from auto_agent.tools.repetition_check import (camera_signature, find_repetitions, load_plan,
                                               motion_signature)

ROOT = Path(__file__).resolve().parent.parent


def test_camera_signatures():
    assert camera_signature({"type": "slow_zoom_in", "amount": 6}) == "slow_zoom_in"
    assert camera_signature({"type": "none"}) is None
    assert camera_signature("높은 곳에서 내려다본 하이앵글 와이드 구도") is None   # 구도 설명은 무빙 아님
    keys = [{"t": 0, "rect": [0, 0, 1600, 900]}, {"t": 2, "rect": [400, 200, 800, 450]}]
    assert camera_signature(keys) == "zoom_in"
    pan = [{"t": 0, "rect": [0, 0, 800, 450]}, {"t": 2, "rect": [200, 0, 800, 450]}]
    assert camera_signature(pan) == "pan_right"
    still = [{"t": 0, "rect": [0, 0, 800, 450]}, {"t": 2, "rect": [0, 0, 800, 450]}]
    assert camera_signature(still) is None


def test_motion_signature_ignores_breathing():
    layers = [{"layer": "a", "moves": [{"type": "bob"}]}, {"layer": "b", "moves": [{"type": "pop"}, {"type": "slide_in"}]}]
    assert motion_signature(layers) == "pop+slide_in"
    assert motion_signature([{"layer": "a", "moves": [{"type": "bob"}]}]) is None


def test_find_repetitions_within_two_scenes_only():
    plan = [{"scene": 1, "camera": "zoom_in", "motion": "pop"},
            {"scene": 2, "camera": None, "motion": None},          # 고정 — 비교 안 함
            {"scene": 3, "camera": "zoom_in", "motion": "slide_in"},
            {"scene": 4, "camera": None, "motion": None},
            {"scene": 5, "camera": None, "motion": None},
            {"scene": 6, "camera": "zoom_in", "motion": "slide_in"}]
    reps = find_repetitions(plan, 2)
    assert {(r["a"], r["b"], r["field"]) for r in reps} == {(1, 3, "camera")}
    reps3 = find_repetitions(plan, 3)
    assert (3, 6, "camera") in {(r["a"], r["b"], r["field"]) for r in reps3}
    assert (3, 6, "motion") in {(r["a"], r["b"], r["field"]) for r in reps3}


def test_load_plan_from_motion_files_and_cli(tmp_path):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "a1"}, {"sceneNumber": 2, "sceneId": "b2"},
        {"sceneNumber": 3, "sceneId": "c3", "camera": "pan_left"}]}), encoding="utf-8")
    for sid in ("a1", "b2"):
        (tmp_path / f"motion_{sid}.json").write_text(json.dumps(
            {"camera": {"type": "pan_left", "amount": 60}, "layers": [{"layer": "x", "moves": [{"type": "pop"}]}]}),
            encoding="utf-8")
    plan = load_plan(tmp_path)
    assert [p["camera"] for p in plan] == ["pan_left", "pan_left", "pan_left"]
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_repetition.py"), str(tmp_path),
                        "--json", str(tmp_path / "rep.json")], capture_output=True, text=True)
    assert r.returncode == 1
    rep = json.loads((tmp_path / "rep.json").read_text(encoding="utf-8"))
    assert {(x["a"], x["b"]) for x in rep["repetitions"] if x["field"] == "camera"} == {(1, 2), (1, 3), (2, 3)}
