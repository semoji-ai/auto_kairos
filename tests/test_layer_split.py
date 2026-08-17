"""layerize 기반 분리 — 저장 규칙·사이드카·예산·예상 외 레이어."""
import json
from pathlib import Path

from backend import imagegen

FIXTURE = Path(__file__).resolve().parents[1] / "docs" / "notes" / "seedream-layerize-trial-response.json"

ELEMENTS = [
    {"name": "차량", "name_en": "white electric car", "location": "중앙",
     "kind": "object", "reason": "r", "intent": "i"},
    {"name": "남자", "name_en": "man on the right", "location": "우측",
     "kind": "character", "reason": "r", "intent": "i"},
]


def _fake_layerize(seen):
    """픽스처의 z/name/bbox를 그대로 흉내낸다(데이터는 짧은 더미 PNG 바이트)."""
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def _call(image_path, names, **kw):
        seen["names"] = list(names)
        out = []
        for L in sorted(payload["layers"], key=lambda x: x["z_index"]):
            bb = (L.get("bounding_box") or {}).get("absolute")
            out.append({"name": L.get("name"), "z": L["z_index"],
                        "bbox": list(bb) if bb else None,
                        "data": b"\x89PNG" + str(L["z_index"]).encode()})
        return out
    return _call


def _run(tmp_path, monkeypatch, elements=None):
    seen = {}
    monkeypatch.setattr(imagegen.fal_api, "layerize", _fake_layerize(seen))
    scene = tmp_path / "scene.png"
    scene.write_bytes(b"\x89PNG")
    res = imagegen.split_scene_to_elements(tmp_path, str(scene), "ab",
                                           elements if elements is not None else ELEMENTS)
    return res, seen, tmp_path / "layers"


def test_prompt_names_come_from_name_en_only(tmp_path, monkeypatch):
    _res, seen, _d = _run(tmp_path, monkeypatch)
    assert seen["names"] == ["white electric car", "man on the right"]
    assert not any("background" in n.lower() for n in seen["names"])


def test_plate_saved_as_background_file(tmp_path, monkeypatch):
    """z0(이름·bbox 없음)이 기존 배경 파일명으로 저장돼야 매니페스트·삭제가 그대로 동작한다."""
    _res, _seen, d = _run(tmp_path, monkeypatch)
    assert (d / "ab__bg.png").is_file()


def test_named_layers_use_existing_filename_rule(tmp_path, monkeypatch):
    res, _seen, d = _run(tmp_path, monkeypatch)
    names = sorted(p.name for p in d.glob("ab__*.png"))
    assert "ab__0_white_electric_car.png" in names
    assert any(n.startswith("ab__1_man_on_the_right") and n.endswith("_char.png") for n in names)
    assert all(L["status"] == "completed" for L in res["layers"])


def test_sidecar_keeps_bbox_and_z(tmp_path, monkeypatch):
    _res, _seen, d = _run(tmp_path, monkeypatch)
    specs = imagegen.load_element_specs(d, "ab")
    car = [s for s in specs if s["name_en"] == "white electric car"][0]
    assert car["bbox"] == [344, 500, 1254, 912]      # 실측 bbox
    assert car["z"] == 3
    assert car["intent"] == "i" and car["kind"] == "object"


def test_unexpected_layers_are_reported_not_dropped(tmp_path, monkeypatch):
    """요청하지 않은 이름이 오면(모델이 임의로 쪼갬) 버리지 않고 알린다."""
    res, _seen, _d = _run(tmp_path, monkeypatch)
    assert "background" in res["unexpected"]         # 픽스처의 z1은 요청 목록에 없다
    assert "EV charger" in res["unexpected"]


def test_budget_caps_names_sent(tmp_path, monkeypatch):
    twelve = [{"name": f"요소{i}", "name_en": f"thing {i}", "location": "",
            "kind": "object", "reason": "r", "intent": "i"} for i in range(12)]
    _res, seen, _d = _run(tmp_path, monkeypatch, elements=twelve)
    assert len(seen["names"]) == imagegen.MAX_ELEMENTS == 10


def test_missing_requested_elements_are_reported(tmp_path, monkeypatch):
    """요청했는데 안 온 요소가 무신호로 사라지면 사용자는 이유를 알 수 없다."""
    def _only_plate(image_path, names, **kw):
        return [{"name": None, "z": 0, "bbox": None, "data": b"\x89PNG"}]
    monkeypatch.setattr(imagegen.fal_api, "layerize", _only_plate)
    scene = tmp_path / "scene.png"; scene.write_bytes(b"\x89PNG")
    res = imagegen.split_scene_to_elements(tmp_path, str(scene), "ab", ELEMENTS)
    assert sorted(res["missing"]) == ["man on the right", "white electric car"]


def test_name_matching_is_case_insensitive(tmp_path, monkeypatch):
    def _caps(image_path, names, **kw):
        return [{"name": None, "z": 0, "bbox": None, "data": b"\x89PNG"},
                {"name": "White Electric Car", "z": 3, "bbox": [1, 2, 3, 4], "data": b"\x89PNG"}]
    monkeypatch.setattr(imagegen.fal_api, "layerize", _caps)
    scene = tmp_path / "scene.png"; scene.write_bytes(b"\x89PNG")
    res = imagegen.split_scene_to_elements(tmp_path, str(scene), "ab", ELEMENTS)
    assert res["unexpected"] == []
    assert "white electric car" not in res["missing"]
    assert (tmp_path / "layers" / "ab__0_white_electric_car.png").is_file()


def test_duplicate_returned_name_goes_to_unexpected(tmp_path, monkeypatch):
    """같은 이름이 두 번 오면 두 번째는 별개 요소가 아니다 — 덮어쓰지 않는다."""
    def _dup(image_path, names, **kw):
        return [{"name": None, "z": 0, "bbox": None, "data": b"\x89PNG"},
                {"name": "white electric car", "z": 3, "bbox": [1, 2, 3, 4], "data": b"\x89PNG1"},
                {"name": "white electric car", "z": 4, "bbox": [5, 6, 7, 8], "data": b"\x89PNG2"}]
    monkeypatch.setattr(imagegen.fal_api, "layerize", _dup)
    scene = tmp_path / "scene.png"; scene.write_bytes(b"\x89PNG")
    res = imagegen.split_scene_to_elements(tmp_path, str(scene), "ab", ELEMENTS)
    assert res["unexpected"].count("white electric car") == 1
    specs = imagegen.load_element_specs(tmp_path / "layers", "ab")
    cars = [s for s in specs if s["name_en"] == "white electric car"]
    assert len(cars) == 1 and cars[0]["bbox"] == [1, 2, 3, 4]   # 첫 번째가 남는다


def test_previous_layers_archived(tmp_path, monkeypatch):
    d = tmp_path / "layers"
    d.mkdir()
    (d / "ab__0_old.png").write_bytes(b"\x89PNG")
    _res, _seen, _d = _run(tmp_path, monkeypatch)
    assert not (d / "ab__0_old.png").exists()
    assert (d / "_prev" / "ab__0_old.png").is_file()
