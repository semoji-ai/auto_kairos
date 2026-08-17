import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_entities_schema_valid():
    schema = json.loads((_ROOT / "backend/schemas/entities.schema.json").read_text(encoding="utf-8"))
    items = schema["properties"]["entities"]["items"]
    assert items["properties"]["type"]["enum"] == ["character", "location", "prop"]
    assert items["required"] == ["id", "type", "name"]


def test_entity_registry_skill_exists():
    md = (_ROOT / "skills/entity-registry/SKILL.md").read_text(encoding="utf-8")
    assert "entity-registry" in md


from backend import entities


def test_norm_collapses_whitespace():
    assert entities._norm("  할머니   캐릭터 ") == "할머니 캐릭터"
    assert entities._norm(None) == ""


def test_gather_occurrences_orders_and_filters():
    scenes = [
        {"sceneNumber": 1, "characters": ["할머니", ""], "location": "거실", "props": ["포스트잇"]},
        {"sceneNumber": 2, "characters": [], "location": "", "props": []},
    ]
    occ = entities._gather_occurrences(scenes)
    assert occ == [
        {"type": "character", "raw": "할머니", "scene": 1},
        {"type": "location", "raw": "거실", "scene": 1},
        {"type": "prop", "raw": "포스트잇", "scene": 1},
    ]


def test_fallback_entities_dedupes_by_norm():
    occ = [
        {"type": "character", "raw": "할머니", "scene": 1},
        {"type": "character", "raw": "할머니", "scene": 2},
        {"type": "location", "raw": "거실", "scene": 1},
    ]
    ents = entities._fallback_entities(occ)
    assert len(ents) == 2
    grandma = next(e for e in ents if e["type"] == "character")
    assert grandma["id"] == "character-1"
    assert grandma["scenes"] == [1, 2]
    assert grandma["first_scene"] == 1
    assert grandma["aliases"] == ["할머니"]


def test_backlink_scenes_maps_ids_via_aliases():
    scenes = [
        {"sceneNumber": 1, "characters": ["할머니"], "location": "거실", "props": []},
        {"sceneNumber": 2, "characters": ["할머니 캐릭터"], "location": "", "props": []},
    ]
    ents = [
        {"id": "char-grandma", "type": "character", "name": "할머니",
         "aliases": ["할머니", "할머니 캐릭터"]},
        {"id": "loc-living", "type": "location", "name": "거실", "aliases": ["거실"]},
    ]
    updated = entities._backlink_scenes(scenes, ents)
    assert updated == 2
    assert scenes[0]["character_ids"] == ["char-grandma"]
    assert scenes[0]["location_id"] == "loc-living"
    assert scenes[0]["prop_ids"] == []
    assert scenes[1]["character_ids"] == ["char-grandma"]
    assert scenes[1]["location_id"] == ""


def test_backlink_unmatched_logs_and_skips():
    scenes = [{"sceneNumber": 1, "characters": ["미지의인물"], "location": "", "props": []}]
    events = []
    updated = entities._backlink_scenes(scenes, [], on_event=events.append)
    assert updated == 0
    assert scenes[0]["character_ids"] == []
    assert any("미매칭" in e for e in events)


import json as _json
from backend import llm


def _write_scenes(tmp_path, scenes):
    (tmp_path / "scenes.json").write_text(
        _json.dumps({"scenes": scenes}, ensure_ascii=False), encoding="utf-8")


def _patch_llm(monkeypatch, ents):
    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(_json.dumps({"entities": ents}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)


def test_build_registry_consolidates_and_backlinks(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [
        {"sceneNumber": 1, "characters": ["할머니"], "location": "거실", "props": []},
        {"sceneNumber": 2, "characters": ["할머니 캐릭터"], "location": "거실", "props": []},
    ])
    _patch_llm(monkeypatch, [
        {"id": "char-grandma", "type": "character", "name": "할머니",
         "aliases": ["할머니", "할머니 캐릭터"], "visual": {}, "first_scene": 1, "scenes": [1, 2]},
        {"id": "loc-living", "type": "location", "name": "거실",
         "aliases": ["거실"], "visual": {}, "first_scene": 1, "scenes": [1, 2]},
    ])
    r = entities.build_entity_registry(tmp_path)
    assert r["entities"] == 2 and r["scenes_updated"] == 2
    reg = _json.loads((tmp_path / "entities.json").read_text(encoding="utf-8"))
    assert len(reg["entities"]) == 2
    scenes = _json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert scenes[0]["character_ids"] == ["char-grandma"]
    assert scenes[1]["character_ids"] == ["char-grandma"]   # 표기 변형 → 같은 id
    assert scenes[0]["location_id"] == "loc-living"


def test_build_registry_fallback_on_llm_failure(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [
        {"sceneNumber": 1, "characters": ["소년"], "location": "", "props": ["연필"]},
    ])
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    r = entities.build_entity_registry(tmp_path)
    assert r["entities"] == 2   # 소년 + 연필
    scenes = _json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert scenes[0]["character_ids"] == ["character-1"]
    assert scenes[0]["prop_ids"] == ["prop-1"]


def test_build_registry_no_occurrences(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [{"sceneNumber": 1, "characters": [], "location": "", "props": []}])
    called = []
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: called.append(1) or {"returncode": 0})
    r = entities.build_entity_registry(tmp_path)
    assert r == {"entities": 0, "scenes_updated": 0}
    assert not called   # LLM 미호출


def test_build_registry_no_scenes_errors(tmp_path):
    r = entities.build_entity_registry(tmp_path)
    assert r.get("error")


def test_build_registry_preserves_existing_fields(tmp_path, monkeypatch):
    _write_scenes(tmp_path, [
        {"sceneNumber": 1, "narration": "옛날 옛적", "layout": "cinematic",
         "characters": ["소년"], "location": "숲", "props": []},
    ])
    _patch_llm(monkeypatch, [
        {"id": "char-boy", "type": "character", "name": "소년", "aliases": ["소년"]},
        {"id": "loc-forest", "type": "location", "name": "숲", "aliases": ["숲"]},
    ])
    entities.build_entity_registry(tmp_path)
    s = _json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert s["narration"] == "옛날 옛적" and s["layout"] == "cinematic"
    assert s["characters"] == ["소년"]   # 원본 free-text 보존
    assert s["character_ids"] == ["char-boy"]
