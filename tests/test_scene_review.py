import json
import pytest
from backend import scene_analysis, llm


def _setup(tmp_path, scenes, manuscript=None, duration="1분"):
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
    (tmp_path / "plan.md").write_text(f"# t\n채널: semoji\n분량: {duration}\n", encoding="utf-8")
    man = manuscript if manuscript is not None else " ".join(s.get("narration", "") for s in scenes)
    (tmp_path / "final_manuscript.md").write_text(man, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def _good_scenes():
    return [{"sceneNumber": 1, "narration": "첫 씬 내용.", "visual_summary": "v1",
             "layout": "cinematic", "shot_relation": "cut", "characters": [], "location": ""},
            {"sceneNumber": 2, "narration": "둘째 씬 내용.", "visual_summary": "v2",
             "layout": "headline_only", "shot_relation": "cut", "characters": [], "location": ""}]


def test_review_merges_llm_flags(tmp_path, monkeypatch):
    _setup(tmp_path, _good_scenes())
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm",
                        lambda pd, scenes, **k: {"scenes": [{"sceneNumber": 1, "layout_fit": "ok"}],
                                                 "flags": ["씬2: headline 적절"], "overall": "양호"})
    r = scene_analysis.review_scenes(tmp_path)
    assert r["flags"] == 1
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    assert rep["overall"] == "양호" and rep["flags"] == ["씬2: headline 적절"]
    assert rep["deterministic"]["scenes"] == 2


def test_det_detects_first_scene_continue_and_bad_visual(tmp_path, monkeypatch):
    bad = _good_scenes()
    bad[0]["shot_relation"] = "continue"
    bad[1]["visual_summary"] = ""
    _setup(tmp_path, bad)
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm", lambda *a, **k: {"scenes": [], "flags": []})
    r = scene_analysis.review_scenes(tmp_path)
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    issues = " ".join(rep["deterministic"]["issues"])
    assert "첫 씬" in issues and "visual_summary" in issues
    assert r["det_issues"] >= 2


def test_det_detects_per_minute_too_many(tmp_path, monkeypatch):
    many = [{"sceneNumber": i + 1, "narration": f"씬{i}.", "visual_summary": "v",
             "layout": "cinematic", "shot_relation": "cut"} for i in range(20)]
    _setup(tmp_path, many, duration="1분")
    monkeypatch.setattr(scene_analysis, "_review_scenes_llm", lambda *a, **k: {"scenes": [], "flags": []})
    scene_analysis.review_scenes(tmp_path)
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    assert any("분당 씬 수" in x for x in rep["deterministic"]["issues"])


def test_review_llm_failure_fallback(tmp_path, monkeypatch):
    _setup(tmp_path, _good_scenes())
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = scene_analysis.review_scenes(tmp_path)
    assert r["flags"] == 0
    rep = json.loads((tmp_path / "scene_review.json").read_text(encoding="utf-8"))
    assert rep["scenes"] == [] and rep["deterministic"]["scenes"] == 2


def test_review_no_scenes_errors(tmp_path):
    (tmp_path / "final_manuscript.md").write_text("x", encoding="utf-8")
    r = scene_analysis.review_scenes(tmp_path)
    assert r.get("error")
