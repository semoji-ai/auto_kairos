"""AE handoff preparation preserves source scenes and existing edits."""
import importlib.util
import json
from pathlib import Path


_PATH = Path(__file__).resolve().parents[1] / "scripts/prepare_ae_project.py"
_SPEC = importlib.util.spec_from_file_location("prepare_ae_project", _PATH)
prepare_ae_project = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(prepare_ae_project)


def _project(tmp_path, *, technique="wipe-reveal-bubble"):
    project = tmp_path / "episode"
    project.mkdir()
    image = project / "images/search/scene_001.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    (project / "scene_specs.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "original-id", "narration": "첫 문장",
         "motion": "fade_rise", "techniques": [technique], "motionNote": "말풍선이 열린다"},
        {"sceneNumber": 2, "sceneId": "second-id", "narration": "둘째 문장",
         "imageAsset": {"source": "none"}},
    ]}, ensure_ascii=False))
    (project / "images/image_assets.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "images": [
            {"file": "search/scene_001.png", "selected": True},
        ]},
    ]}))
    return project


def test_preparation_is_read_only_until_write_and_preserves_scene_intent(tmp_path):
    project = _project(tmp_path)
    result = prepare_ae_project.prepare(project)
    assert result["ok"] and result["status"] == "ready_to_create"
    assert not (project / "scenes.json").exists()

    created = prepare_ae_project.prepare(project, write=True)
    assert created["status"] == "created"
    scenes = json.loads((project / "scenes.json").read_text())["scenes"]
    assert [s["sceneNumber"] for s in scenes] == [1, 2]
    assert scenes[0]["sceneId"] == "original-id"
    assert scenes[0]["narration"] == "첫 문장"
    assert scenes[0]["imageRef"] == "images/search/scene_001.png"
    assert scenes[0]["techniques"] == ["wipe-reveal-bubble"]
    assert scenes[0]["motionNote"] == "말풍선이 열린다"
    assert scenes[1]["imageRef"] == ""
    assert len(list(project.rglob("*.png"))) == 1

    before = (project / "scenes.json").read_bytes()
    assert prepare_ae_project.prepare(project, write=True)["status"] == "existing"
    assert (project / "scenes.json").read_bytes() == before


def test_missing_selected_image_blocks_creation(tmp_path):
    project = _project(tmp_path)
    (project / "images/search/scene_001.png").unlink()
    result = prepare_ae_project.prepare(project, write=True)
    assert not result["ok"]
    assert any("선택 이미지 없음" in message for message in result["errors"])
    assert not (project / "scenes.json").exists()


def test_unported_reference_technique_is_manual_and_unknown_id_blocks(tmp_path):
    project = _project(tmp_path, technique="chat-parody")
    result = prepare_ae_project.prepare(project)
    assert result["ok"]
    assert any("AE 수동 연출 대상" in message for message in result["warnings"])

    specs_path = project / "scene_specs.json"
    specs = json.loads(specs_path.read_text())
    specs["scenes"][0]["techniques"] = ["not-a-dogam-technique"]
    specs_path.write_text(json.dumps(specs))
    result = prepare_ae_project.prepare(project, write=True)
    assert not result["ok"]
    assert any("도감에 없는 기법" in message for message in result["errors"])
    assert not (project / "scenes.json").exists()


def test_existing_ae_scene_order_is_never_rewritten(tmp_path):
    project = _project(tmp_path)
    path = project / "scenes.json"
    path.write_text(json.dumps({"scenes": [{"sceneNumber": 2}, {"sceneNumber": 1}]}))
    before = path.read_bytes()
    result = prepare_ae_project.prepare(project, write=True)
    assert not result["ok"]
    assert any("번호·순서" in message for message in result["errors"])
    assert path.read_bytes() == before


def test_existing_ae_edits_are_reported_without_replacement(tmp_path):
    project = _project(tmp_path)
    prepare_ae_project.prepare(project, write=True)
    path = project / "scenes.json"
    data = json.loads(path.read_text())
    data["scenes"][0]["narration"] = "AE에서 고친 원고"
    data["scenes"][0]["imageRef"] = "images/search/scene_001.png"
    path.write_text(json.dumps(data))
    before = path.read_bytes()

    result = prepare_ae_project.prepare(project, write=True)
    assert result["ok"] and result["status"] == "existing"
    assert any("AE 원고" in message for message in result["warnings"])
    assert path.read_bytes() == before
