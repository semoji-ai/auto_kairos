import json
from pathlib import Path
from backend import scene_analysis, llm


def _setup(tmp_path, manuscript):
    (tmp_path / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")


def _patch_direct(monkeypatch, scenes):
    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({"scenes": scenes}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)


def test_analyze_scenes_builds_scenes_json(tmp_path, monkeypatch):
    _setup(tmp_path, "첫 씬.\n<!--SCENE-->\n둘째 씬.")
    _patch_direct(monkeypatch, [
        {"visual_summary": "공장 외경", "image_prompt": "1933 공장", "characters": []},
        {"visual_summary": "창업자 클로즈업", "image_prompt": "유일한 박사", "characters": ["유일한"]}])
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["count"] == 2
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    s = data["scenes"]
    assert s[0]["narration"] == "첫 씬." and s[0]["visual_summary"] == "공장 외경"
    assert s[1]["narration"] == "둘째 씬." and s[1]["sceneNumber"] == 2
    assert all(sc.get("sceneId") for sc in s)
    assert s[1]["characters"] == ["유일한"]


def test_analyze_scenes_marker_chars_win(tmp_path, monkeypatch):
    _setup(tmp_path, "씬.\n<!--CHARS: 소년-->\n본문.")
    _patch_direct(monkeypatch, [{"visual_summary": "v", "image_prompt": "p", "characters": ["딴사람"]}])
    scene_analysis.analyze_scenes(tmp_path)
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    assert data["scenes"][0]["characters"] == ["소년"]


def test_analyze_scenes_direction_count_mismatch(tmp_path, monkeypatch):
    _setup(tmp_path, "씬1.\n<!--SCENE-->\n씬2.\n<!--SCENE-->\n씬3.")
    _patch_direct(monkeypatch, [{"visual_summary": "v1", "image_prompt": "p1"}])
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["count"] == 3
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    assert data["scenes"][0]["visual_summary"] == "v1"
    assert data["scenes"][2]["narration"] == "씬3."


def test_analyze_scenes_llm_failure_fallback(tmp_path, monkeypatch):
    _setup(tmp_path, "씬1.\n<!--SCENE-->\n씬2.")
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["count"] == 2
    data = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))
    assert data["scenes"][0]["narration"] == "씬1."


def test_analyze_scenes_no_manuscript_errors(tmp_path):
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r.get("error")
