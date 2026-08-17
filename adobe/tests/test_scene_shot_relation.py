import json
from pathlib import Path
from backend import scene_analysis


def _setup(tmp_path, manuscript="씬1.\n<!--SCENE-->\n씬2."):
    (tmp_path / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def test_shot_relation_location_props_passthrough(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(scene_analysis, "_direct_scenes", lambda proj, segs, **k: [
        {"visual_summary": "v1", "shot_relation": "cut", "location": "연구실", "props": ["접착제"]},
        {"visual_summary": "v2", "shot_relation": "continue", "location": "연구실", "props": []}])
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["shot_relation"] == "cut" and s[0]["location"] == "연구실" and s[0]["props"] == ["접착제"]
    assert s[1]["shot_relation"] == "continue"


def test_shot_relation_defaults_cut_and_validates(tmp_path, monkeypatch):
    _setup(tmp_path, "한 씬뿐.")
    monkeypatch.setattr(scene_analysis, "_direct_scenes", lambda proj, segs, **k: [
        {"visual_summary": "v", "shot_relation": "zoom"}])
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["shot_relation"] == "cut"


def test_scene_specs_schema_has_shot_relation():
    sp = json.loads(Path("backend/schemas/scene_specs.schema.json").read_text(encoding="utf-8"))
    props = sp["properties"]["scenes"]["items"]["properties"]
    assert props["shot_relation"]["enum"] == ["cut", "continue"]
    assert props["location"]["type"] == "string" and props["props"]["type"] == "array"


def test_scene_analyze_skill_instructs_shot_relation():
    t = Path("skills/scene-analyze/SKILL.md").read_text(encoding="utf-8")
    assert "shot_relation" in t and "continue" in t and "location" in t and "props" in t
