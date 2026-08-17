import json
from pathlib import Path

import pytest

from backend import jobs as jobs_mod
from backend import router

SID = "abc123"


def _ctx(root):
    return {"root": root, "jobs": jobs_mod.JobRegistry()}


def _project(tmp_path: Path):
    """씬 1개 + 레이어 2장 + 사이드카를 갖춘 프로젝트."""
    proj = tmp_path / "p1"
    (proj / "layers").mkdir(parents=True)
    (proj / "storyboard").mkdir()
    (proj / "storyboard" / f"sb_{SID}.png").write_bytes(b"png")
    for stem in (f"{SID}__0_car", f"{SID}__bg"):
        (proj / "layers" / (stem + ".png")).write_bytes(b"png")
    specs = [{"layer": f"{SID}__0_car", "index": 0, "name": "차", "name_en": "car",
              "location": "", "kind": "object", "intent": "", "z": 1}]
    (proj / "layers" / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": "n",
         "imageRef": f"storyboard/sb_{SID}.png"}]}, ensure_ascii=False), encoding="utf-8")
    return proj


def test_state_sets_removed(tmp_path):
    proj = _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 1, "layer": f"{SID}__0_car", "removed": True},
        _ctx(tmp_path))
    assert status == 200
    assert res["ok"] is True and res["removed"] is True
    side = json.loads((proj / "layers" / f"{SID}__elements.json").read_text(encoding="utf-8"))
    assert side[0]["removed"] is True


def test_state_rejects_background_removal(tmp_path):
    _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 1, "layer": f"{SID}__bg", "removed": True},
        _ctx(tmp_path))
    assert status == 422
    assert "error" in res


def test_state_unknown_scene(tmp_path):
    _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 99, "layer": f"{SID}__0_car", "hidden": True},
        _ctx(tmp_path))
    assert status == 404


def test_state_requires_layer(tmp_path):
    _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 1, "hidden": True}, _ctx(tmp_path))
    assert status == 400


def test_delete_endpoint_is_gone(tmp_path):
    """배경 재생성 삭제 경로는 제거됐다 — z0 배경판이 이미 완전하다."""
    _project(tmp_path)
    status, _ = router.handle_request(
        "POST", "/api/layers/delete", {},
        {"project_id": "p1", "sceneNumber": 1, "layer": f"{SID}__0_car"}, _ctx(tmp_path))
    assert status == 404


def test_scene_layer_meta(tmp_path):
    from backend import scenes
    proj = _project(tmp_path)
    (proj / "layers" / f"{SID}__0_car.svg").write_text("<svg/>", encoding="utf-8")
    router.handle_request("POST", "/api/layers/state", {},
                          {"project_id": "p1", "sceneNumber": 1,
                           "layer": f"{SID}__0_car", "hidden": True}, _ctx(tmp_path))
    data = scenes.load_scenes(proj)
    meta = data["scenes"][0]["_layer_meta"]
    assert meta[f"{SID}__0_car"]["hidden"] is True
    assert meta[f"{SID}__0_car"]["removed"] is False
    assert meta[f"{SID}__0_car"]["svg"] is True
    assert meta[f"{SID}__0_car"]["name"] == "차"
    assert meta[f"{SID}__bg"]["svg"] is False
    assert meta[f"{SID}__bg"]["removed"] is False


def test_layer_meta_box_percent(tmp_path):
    """bbox가 배경판 크기 기준 백분율로 변환된다 — 패널 합성 미리보기용."""
    from PIL import Image
    from backend import scenes
    proj = _project(tmp_path)
    Image.new("RGBA", (1000, 500)).save(proj / "layers" / f"{SID}__bg.png")
    Image.new("RGBA", (200, 100)).save(proj / "layers" / f"{SID}__0_car.png")
    specs = [{"layer": f"{SID}__0_car", "index": 0, "name": "차", "name_en": "car",
              "location": "", "kind": "object", "intent": "", "z": 1,
              "bbox": [100, 50, 300, 150]}]
    (proj / "layers" / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    meta = scenes.load_scenes(proj)["scenes"][0]["_layer_meta"]
    box = meta[f"{SID}__0_car"]["box"]
    assert box["left"] == pytest.approx(10.0)
    assert box["top"] == pytest.approx(10.0)
    assert box["width"] == pytest.approx(20.0)
    assert meta[f"{SID}__bg"]["box"] is None


def test_layer_meta_box_none_without_bbox(tmp_path):
    from backend import scenes
    proj = _project(tmp_path)
    meta = scenes.load_scenes(proj)["scenes"][0]["_layer_meta"]
    assert meta[f"{SID}__0_car"]["box"] is None
