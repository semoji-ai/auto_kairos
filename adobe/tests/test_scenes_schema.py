import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "skills/scene-decompose/scenes.schema.json"


def test_schema_is_strict_and_requires_scenes():
    s = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert s["type"] == "object"
    assert s["additionalProperties"] is False
    assert "scenes" in s["properties"]
    item = s["properties"]["scenes"]["items"]
    assert item["additionalProperties"] is False
    assert "narration" in item["required"]
    # strict 모드: 모든 속성이 required 에 있어야 함
    assert set(item["required"]) == set(item["properties"].keys())
    assert set(s["required"]) == set(s["properties"].keys())


def test_sample_doc_has_all_required_fields():
    s = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = {
        "version": "adobe-0.1", "project_id": "demo01", "topic": "t",
        "total_scenes": 1,
        "scenes": [{
            "sceneNumber": 1, "section": None, "title": "도입",
            "narration": "카지노가 세 번 무너졌습니다.", "characters": [],
            "visual_summary": "카지노 외관", "image_prompt": "무너진 카지노",
            "duration_estimate_sec": 3.0,
            "layout": "cinematic", "headline": None, "sub": None, "items": None,
            "value": None, "label": None, "chart": None,
            "quote_text": None, "quote_who": None,
            "map_center": None, "map_zoom": None, "map_markers": None, "map_route": None,
        }],
    }
    for k in s["required"]:
        assert k in doc
    for k in s["properties"]["scenes"]["items"]["required"]:
        assert k in doc["scenes"][0]
