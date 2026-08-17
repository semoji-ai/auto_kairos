import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scene_specs_schema_has_asset_source():
    s = json.loads((ROOT / "backend/schemas/scene_specs.schema.json").read_text(encoding="utf-8"))
    props = s["properties"]["scenes"]["items"]["properties"]
    assert props["asset_source"]["enum"] == ["generate", "search"]
    assert props["search_query"]["type"] == "string"


def test_scene_analyze_skill_instructs_asset_source():
    t = (ROOT / "skills/scene-analyze/SKILL.md").read_text(encoding="utf-8")
    assert "asset_source" in t and "search_query" in t
    assert "search" in t and "generate" in t
    assert "실사" in t
