"""Storyboard imports reuse image bytes and use per-scene selection flags."""
import asyncio
from io import BytesIO
import json

from auto_agent.tools.image_assets import (
    add_version,
    clear_selection,
    get_scene_versions,
    select_version,
    store_unique_image,
)


def test_same_image_is_stored_once_and_selected_per_scene(tmp_path):
    images_dir = tmp_path / "images"
    first, created = store_unique_image(images_dir, "search/scene_001_search_01.png", b"image-a")
    assert created is True
    second, created = store_unique_image(images_dir, "search/scene_002_search_01.png", b"image-a")
    assert (second, created) == (first, False)

    add_version(images_dir, 1, first, "search")
    add_version(images_dir, 2, second, "search")
    assert get_scene_versions(images_dir, 1)["selected"] == first
    assert get_scene_versions(images_dir, 2)["selected"] == first
    assert len(list(images_dir.rglob("*.png"))) == 1

    other, _ = store_unique_image(images_dir, "search/scene_001_search_02.png", b"image-b")
    add_version(images_dir, 1, other, "search")
    assert select_version(images_dir, 1, first)
    data = json.loads((images_dir / "image_assets.json").read_text())
    scene = next(s for s in data["scenes"] if s["sceneNumber"] == 1)
    assert scene["selected"] == first
    assert [v["selected"] for v in scene["images"]] == [True, False]

    clear_selection(images_dir, 1)
    assert get_scene_versions(images_dir, 1)["selected"] is None
    assert get_scene_versions(images_dir, 2)["selected"] == first
    assert len(list(images_dir.rglob("*.png"))) == 2


def test_store_unique_image_keeps_different_contents_when_names_collide(tmp_path):
    images_dir = tmp_path / "images"
    first, _ = store_unique_image(images_dir, "search/scene_001.png", b"first")
    second, created = store_unique_image(images_dir, "search/scene_001.png", b"second")
    assert created is True
    assert first != second
    assert (images_dir / first).read_bytes() == b"first"
    assert (images_dir / second).read_bytes() == b"second"


def test_gallery_uses_boolean_selected_instead_of_stale_legacy_field(tmp_path, monkeypatch):
    import app

    images_dir = tmp_path / "images"
    first, _ = store_unique_image(images_dir, "search/scene_001_a.png", b"first")
    second, _ = store_unique_image(images_dir, "search/scene_001_b.png", b"second")
    add_version(images_dir, 1, first, "search")
    add_version(images_dir, 1, second, "search")
    data_path = images_dir / "image_assets.json"
    data = json.loads(data_path.read_text())
    data["scenes"][0]["selected"] = first  # legacy field is stale
    data_path.write_text(json.dumps(data))

    monkeypatch.setattr(app, "get_pm", lambda: object())
    monkeypatch.setattr(
        app, "resolve_project_ref",
        lambda _pm, _ref: ({"slug": "test", "output_dir": str(tmp_path)}, False),
    )
    response = asyncio.run(app.images_all(None, "test"))
    images = json.loads(response.body)["images"]
    assert {v["file"] for v in images if v["selected"]} == {second}


def test_scene_spec_points_to_selected_file_without_copy(tmp_path):
    import app

    images_dir = tmp_path / "images"
    selected, _ = store_unique_image(images_dir, "search/scene_001_search_01.png", b"image")
    add_version(images_dir, 1, selected, "search")
    specs_path = tmp_path / "scene_specs.json"
    specs_path.write_text(json.dumps({"scenes": [{"sceneNumber": 1, "imageAsset": {}}]}))

    app._update_scene_specs_src(str(tmp_path), "test", 1)

    scene = json.loads(specs_path.read_text())["scenes"][0]
    expected = f"/output/{tmp_path.name}/images/{selected}"
    assert scene["imageAsset"]["src"] == expected
    assert scene["imagePath"] == expected
    assert len(list(images_dir.rglob("*.png"))) == 1


def test_editor_reupload_reuses_file_and_selection(tmp_path, monkeypatch):
    from fastapi import UploadFile
    from auto_agent.dashboard import scene_editor

    (tmp_path / "scene_specs.json").write_text(
        json.dumps({"scenes": [{"sceneNumber": 1, "imageAsset": {}}]})
    )
    monkeypatch.setattr(
        scene_editor, "resolve_project_ref",
        lambda _pm, _ref: ({"output_dir": str(tmp_path), "uuid": "test"}, False),
    )
    monkeypatch.setattr(scene_editor, "_rebuild_manifest_sync", lambda _project: None)

    async def upload():
        return await scene_editor.upload_scene_image(
            "test", 1, None,
            UploadFile(file=BytesIO(b"same-image"), filename="source.png"),
        )

    first = asyncio.run(upload())
    second = asyncio.run(upload())
    assert first["image_url"] == second["image_url"]
    assert len(list((tmp_path / "images").rglob("*.png"))) == 1
    assert get_scene_versions(tmp_path / "images", 1)["selected"] == "search/scene_001_search_01.png"
