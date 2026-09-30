from pathlib import Path
import json

from PIL import Image
from fastapi.testclient import TestClient

from auto_agent.dashboard.image_preview import selected_image_preview


def test_selected_image_preview_is_small_cached_and_tracks_source_changes(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    source = images / "scene_001.png"
    Image.new("RGB", (2400, 1350), "red").save(source)
    cache = tmp_path / "thumbnails"

    first = selected_image_preview(images, "scene_001.png", cache, 1)
    assert first.is_file()
    assert first.suffix == ".webp"
    assert first.stat().st_size < source.stat().st_size
    with Image.open(first) as preview:
        assert preview.size == (960, 540)
    assert selected_image_preview(images, "scene_001.png", cache, 1) == first
    assert source.is_file()

    Image.new("RGB", (2400, 1350), "blue").save(source)
    second = selected_image_preview(images, "scene_001.png", cache, 1)
    assert second != first
    assert first.is_file()  # 과거 버전을 삭제하지 않는다


def test_selected_image_preview_rejects_escape(tmp_path):
    images = tmp_path / "images"
    images.mkdir()
    (tmp_path / "outside.png").write_bytes(b"x")
    try:
        selected_image_preview(images, "../outside.png", tmp_path / "thumbnails", 1)
    except ValueError:
        pass
    else:
        raise AssertionError("project image directory escape must fail")


def test_preview_route_only_serves_versions_registered_for_scene(tmp_path, monkeypatch):
    import app
    from auto_agent.dashboard import scene_editor
    from auto_agent.db import project_manager

    output = tmp_path / "demo"
    images = output / "images"
    images.mkdir(parents=True)
    Image.new("RGB", (2000, 1000), "green").save(images / "selected.png")
    Image.new("RGB", (2000, 1000), "red").save(images / "other.png")
    (images / "image_assets.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "images": [{"file": "selected.png", "selected": True}]},
        {"sceneNumber": 2, "images": [{"file": "other.png", "selected": True}]},
    ]}), encoding="utf-8")
    monkeypatch.setattr(project_manager, "ProjectManager", lambda: object())
    monkeypatch.setattr(scene_editor, "resolve_project_ref",
                        lambda pm, ref: ({"output_dir": str(output), "uuid": "abc12345"}, False))
    client = TestClient(app.app)
    selected = client.get("/api/p/demo/images/preview/1")
    assert selected.status_code == 200
    assert selected.headers["content-type"] == "image/webp"
    assert client.get("/api/p/demo/images/preview/1?file=other.png").status_code == 404
    assert client.get("/api/p/demo/images/preview/1?file=../outside.png").status_code == 404
