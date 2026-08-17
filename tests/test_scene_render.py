import json
from pathlib import Path
from backend import scene_render


def _mksheet(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG\r\n")


def test_resolve_scene_refs_existing_only(tmp_path):
    _mksheet(tmp_path, "references/characters/char-1.png")
    ents = {
        "char-1": {"id": "char-1", "type": "character", "name": "하루", "sheet": "references/characters/char-1.png"},
        "char-2": {"id": "char-2", "type": "character", "name": "미아", "sheet": "references/characters/char-2.png"},
    }
    scene = {"sceneNumber": 1, "character_ids": ["char-1", "char-2"], "location_id": "", "prop_ids": []}
    refs = scene_render.resolve_scene_refs(scene, ents, tmp_path)
    assert len(refs["character_sheets"]) == 1   # char-2 시트 파일 없음 → 제외
    assert refs["character_sheets"][0]["name"] == "하루"
    assert refs["location_sheet"] == {}
    assert refs["prop_sheets"] == []


def test_resolve_scene_refs_location_and_props(tmp_path):
    _mksheet(tmp_path, "references/locations/loc-1.png")
    _mksheet(tmp_path, "references/props/prop-1.png")
    ents = {
        "loc-1": {"id": "loc-1", "type": "location", "name": "거실", "sheet": "references/locations/loc-1.png"},
        "prop-1": {"id": "prop-1", "type": "prop", "name": "포스트잇", "sheet": "references/props/prop-1.png"},
    }
    scene = {"sceneNumber": 1, "character_ids": [], "location_id": "loc-1", "prop_ids": ["prop-1"]}
    refs = scene_render.resolve_scene_refs(scene, ents, tmp_path)
    assert refs["location_sheet"]["name"] == "거실"
    assert refs["prop_sheets"][0]["name"] == "포스트잇"


def test_build_scene_prompt_includes_scene_and_descriptors():
    p = scene_render.build_scene_prompt(
        {"image_prompt": "공원 산책"},
        ["1번 캐릭터 시트 '하루'", "인물 없음"],
        "STYLE", "scenes/scene_1.png")
    assert "공원 산책" in p
    assert "하루" in p
    assert "scenes/scene_1.png" in p
    assert "STYLE" in p


from backend import imagegen


def _setup(tmp_path, scene_list, entities, sheets=()):
    (tmp_path / "scenes.json").write_text(
        json.dumps({"scenes": scene_list}, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "entities.json").write_text(
        json.dumps({"entities": entities}, ensure_ascii=False), encoding="utf-8")
    for rel in sheets:
        _mksheet(tmp_path, rel)


def _fake_codex(monkeypatch, fail_scenes=()):
    calls = []

    def fake(proj_dir, out, prompt, *, images=None, retries=2, on_line=None, post=None):
        calls.append({"out": str(out), "prompt": prompt, "images": list(images or [])})
        if any(f"scene_{n}.png" == Path(out).name for n in fail_scenes):
            return {"status": "failed", "error": "no_file"}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_bytes(b"\x89PNG\r\n")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(imagegen, "_run_codex_image", fake)
    return calls


def test_render_scenes_attaches_sheets_and_links(tmp_path, monkeypatch):
    _setup(tmp_path,
        [{"sceneNumber": 1, "shot_relation": "cut", "character_ids": ["char-1"],
          "location_id": "loc-1", "prop_ids": [], "image_prompt": "등장"}],
        [{"id": "char-1", "type": "character", "name": "하루", "sheet": "references/characters/char-1.png"},
         {"id": "loc-1", "type": "location", "name": "거실", "sheet": "references/locations/loc-1.png"}],
        sheets=["references/characters/char-1.png", "references/locations/loc-1.png"])
    calls = _fake_codex(monkeypatch)
    r = scene_render.render_scenes(tmp_path)
    assert r["rendered"] == 1 and r["total"] == 1 and r["skipped"] == []
    imgs = calls[0]["images"]
    assert any("char-1.png" in i for i in imgs)
    assert any("loc-1.png" in i for i in imgs)
    doc = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert doc[0]["imageRef"] == "scenes/scene_1.png"
    assert (tmp_path / "scenes/scene_1.png").exists()


def test_render_continue_attaches_prev_scene(tmp_path, monkeypatch):
    _setup(tmp_path,
        [{"sceneNumber": 1, "shot_relation": "cut", "character_ids": ["char-1"]},
         {"sceneNumber": 2, "shot_relation": "continue", "character_ids": ["char-1"]}],
        [{"id": "char-1", "type": "character", "name": "하루", "sheet": "references/characters/char-1.png"}],
        sheets=["references/characters/char-1.png"])
    calls = _fake_codex(monkeypatch)
    scene_render.render_scenes(tmp_path)
    c1 = [c for c in calls if Path(c["out"]).name == "scene_1.png"][0]
    c2 = [c for c in calls if Path(c["out"]).name == "scene_2.png"][0]
    assert any(Path(i).name == "scene_1.png" for i in c2["images"])   # 씬2가 씬1 첨부
    assert ("직전" in c2["prompt"]) or ("연속" in c2["prompt"])
    assert not any(Path(i).name.startswith("scene_") for i in c1["images"])   # 씬1은 prev 없음


def test_render_skip_on_failure(tmp_path, monkeypatch):
    _setup(tmp_path,
        [{"sceneNumber": 1, "character_ids": []}, {"sceneNumber": 2, "character_ids": []}],
        [])
    _fake_codex(monkeypatch, fail_scenes=(1,))
    r = scene_render.render_scenes(tmp_path)
    assert r["rendered"] == 1
    assert any(s["scene"] == 1 for s in r["skipped"])


def test_render_no_entities_errors(tmp_path):
    (tmp_path / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    assert scene_render.render_scenes(tmp_path).get("error")


def test_render_no_scenes_errors(tmp_path):
    assert scene_render.render_scenes(tmp_path).get("error")
