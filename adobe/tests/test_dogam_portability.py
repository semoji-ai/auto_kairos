"""Bundled dogam must remain usable when the sibling semoji-motion repo is absent."""
import json
import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_dogam.py"
_SPEC = importlib.util.spec_from_file_location("sync_dogam", _PATH)
sync_dogam = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sync_dogam)


def test_bundled_catalog_covers_ae_registry():
    bundled = sync_dogam.BUNDLED
    catalog = json.loads((bundled / "dogam/techniques.json").read_text(encoding="utf-8"))
    registry = json.loads(sync_dogam.REGISTRY.read_text(encoding="utf-8"))

    assert len(catalog) == registry["total_catalog"] == 343
    assert registry["count"] == len(registry["techniques"]) == 12
    ids = {item["id"] for item in catalog}
    for item in registry["techniques"]:
        assert item["id"] in ids
        assert (sync_dogam.EXT / item["file"]).is_file()
        for extension in ("jpg", "mp4"):
            assert (bundled / "dogam/previews" / f"{item['preview']}.{extension}").is_file()

    assert (bundled / "ae/assets/map_bg.png").is_file()
    assert (bundled / "video/public/img/s06_kid.png").is_file()


def test_bundled_sync_fills_panel_assets(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_dogam, "ASSETS", tmp_path / "assets")
    stats = sync_dogam.sync_assets(sync_dogam.BUNDLED, "copy")
    assert stats["previews_jpg"] == 12
    assert stats["previews_mp4"] == 12
    assert (sync_dogam.ASSETS / "map/map_bg.png").is_file()
    assert (sync_dogam.ASSETS / "catalog/techniques.json").is_file()
