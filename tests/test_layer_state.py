import json
from pathlib import Path

from backend import imagegen

SID = "abc123"


def _proj(tmp_path: Path, specs, extra_files=()):
    """layers/ 에 사이드카와 PNG를 갖춘 임시 프로젝트."""
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    for s in specs:
        (lay / (s["layer"] + ".png")).write_bytes(b"png")
    for name in extra_files:
        (lay / name).write_bytes(b"png")
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _sidecar(tmp_path: Path):
    return json.loads((tmp_path / "layers" / f"{SID}__elements.json").read_text(encoding="utf-8"))


def _spec(i, name):
    return {"layer": f"{SID}__{i}_{name}", "index": i, "name": name,
            "name_en": name, "location": "", "kind": "object", "intent": ""}


def test_hidden_written_to_sidecar(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__0_car", hidden=True)
    assert res["ok"] is True
    assert res["hidden"] is True
    assert res["removed"] is False
    assert _sidecar(proj)[0]["hidden"] is True


def test_removed_written_and_restored(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=True)
    assert _sidecar(proj)[0]["removed"] is True
    res = imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=False)
    assert res["removed"] is False
    assert _sidecar(proj)[0]["removed"] is False


def test_file_is_not_moved(tmp_path):
    """제거는 플래그일 뿐 — 파일은 그 자리에 있어야 복구가 즉시 된다."""
    proj = _proj(tmp_path, [_spec(0, "car")])
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=True)
    assert (proj / "layers" / f"{SID}__0_car.png").is_file()
    assert not (proj / "layers" / "_prev").exists()


def test_hidden_and_removed_are_independent(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", hidden=True)
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=True)
    entry = _sidecar(proj)[0]
    assert entry["hidden"] is True and entry["removed"] is True
    # removed만 되돌려도 hidden은 그대로 남는다
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=False)
    entry = _sidecar(proj)[0]
    assert entry["hidden"] is True and entry["removed"] is False


def test_background_cannot_be_removed(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__bg.png"])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__bg", removed=True)
    assert "error" in res
    assert "ok" not in res


def test_background_can_be_hidden(tmp_path):
    """배경도 미리보기에서는 끌 수 있다 — 사이드카에 항목이 새로 생긴다."""
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__bg.png"])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__bg", hidden=True)
    assert res["ok"] is True
    entry = next(s for s in _sidecar(proj) if s["layer"] == f"{SID}__bg")
    assert entry["hidden"] is True


def test_unknown_layer_rejected(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__9_ghost", removed=True)
    assert "error" in res


def test_legacy_layer_without_sidecar_entry(tmp_path):
    """사이드카에 없지만 PNG는 있는 레거시 레이어 — 항목이 새로 생기고 기존 항목은 그대로."""
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__1_tree.png"])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__1_tree", removed=True)
    assert res["ok"] is True
    side = _sidecar(proj)
    assert len(side) == 2
    assert next(s for s in side if s["layer"] == f"{SID}__0_car").get("removed") is None
    assert next(s for s in side if s["layer"] == f"{SID}__1_tree")["removed"] is True


def test_path_forms_accepted(tmp_path):
    """'layers/x.png' 같은 경로 형태도 stem으로 정규화된다."""
    proj = _proj(tmp_path, [_spec(0, "car")])
    res = imagegen.set_layer_state(proj, SID, f"layers/{SID}__0_car.png", hidden=True)
    assert res["ok"] is True
    assert _sidecar(proj)[0]["hidden"] is True


def test_regenerate_skips_removed_elements(tmp_path, monkeypatch):
    """재분리는 제거된 요소를 다시 만들지 않는다 — 배경에 녹아든다."""
    proj = _proj(tmp_path, [_spec(0, "car"), _spec(1, "tree")])
    imagegen.set_layer_state(proj, SID, f"{SID}__1_tree", removed=True)
    seen = {}

    def fake_split(proj_dir, scene_image, sid, elements, **kw):
        seen["names"] = [e["name_en"] for e in elements]
        return {"layers": [], "unexpected": [], "missing": []}

    monkeypatch.setattr(imagegen, "split_scene_to_elements", fake_split)
    imagegen.regenerate_layer(proj, "scene.png", SID, f"{SID}__0_car")
    assert seen["names"] == ["car"]


def test_regenerate_skips_specs_without_name_en(tmp_path, monkeypatch):
    """name_en이 빈 항목(배경 hidden 기록 등)은 요소 예산을 잡아먹지 않는다."""
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__bg.png"])
    imagegen.set_layer_state(proj, SID, f"{SID}__bg", hidden=True)
    seen = {}

    def fake_split(proj_dir, scene_image, sid, elements, **kw):
        seen["names"] = [e["name_en"] for e in elements]
        return {"layers": [], "unexpected": [], "missing": []}

    monkeypatch.setattr(imagegen, "split_scene_to_elements", fake_split)
    imagegen.regenerate_layer(proj, "scene.png", SID, f"{SID}__0_car")
    assert seen["names"] == ["car"]
