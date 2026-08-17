import json
from pathlib import Path
from backend import scene_analysis, search, scenes as scenes_mod


def _setup(tmp_path, manuscript="씬1.\n<!--SCENE-->\n씬2."):
    (tmp_path / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"x"}', encoding="utf-8")


def _patch_directions(monkeypatch, dirs):
    monkeypatch.setattr(scene_analysis, "_direct_scenes", lambda proj, segs, **k: dirs)


def _patch_search(monkeypatch, *, images=None, fail=False):
    def fake_search(q, engine="serper", count=12):
        if fail:
            return {"error": "no key", "images": []}
        return {"images": images if images is not None else [{"url": "http://x/p.jpg", "title": "t"}]}
    def fake_save(proj_dir, url, name, subdir="images/search"):
        d = Path(proj_dir) / subdir
        d.mkdir(parents=True, exist_ok=True)
        f = d / name
        f.write_bytes(b"img")
        return {"status": "completed", "path": str(f), "rel": f"{subdir}/{name}"}
    monkeypatch.setattr(search, "search_images", fake_search)
    monkeypatch.setattr(search, "save_image", fake_save)


def test_search_scene_gets_imageref(tmp_path, monkeypatch):
    _setup(tmp_path)
    _patch_directions(monkeypatch, [
        {"visual_summary": "특허", "asset_source": "search", "search_query": "US 3691140 patent"},
        {"visual_summary": "감정", "asset_source": "generate"}])
    _patch_search(monkeypatch)
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["searched"] == 1 and r["count"] == 2
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["asset_source"] == "search" and s[0]["imageRef"].endswith(".jpg")
    assert s[1]["asset_source"] == "generate" and s[1]["imageRef"] == ""


def test_search_failure_falls_back(tmp_path, monkeypatch):
    _setup(tmp_path)
    _patch_directions(monkeypatch, [{"visual_summary": "특허", "asset_source": "search", "search_query": "q"}])
    _patch_search(monkeypatch, fail=True)
    r = scene_analysis.analyze_scenes(tmp_path)
    assert r["searched"] == 0
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["imageRef"] == ""


def test_enrich_false_skips_search(tmp_path, monkeypatch):
    _setup(tmp_path)
    _patch_directions(monkeypatch, [{"visual_summary": "특허", "asset_source": "search", "search_query": "q"}])
    called = {"n": 0}
    monkeypatch.setattr(search, "search_images", lambda *a, **k: called.__setitem__("n", called["n"] + 1) or {"images": []})
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    assert r["searched"] == 0 and called["n"] == 0


def test_asset_source_defaults_generate(tmp_path, monkeypatch):
    _setup(tmp_path, "한 씬뿐.")
    _patch_directions(monkeypatch, [{"visual_summary": "v"}])
    r = scene_analysis.analyze_scenes(tmp_path, enrich=False)
    s = json.loads((tmp_path / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert s[0]["asset_source"] == "generate"
