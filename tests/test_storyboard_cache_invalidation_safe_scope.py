from pathlib import Path

ROOT = Path("/Users/jleavens_macmini/Projects/auto_kairos_v3")


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_storyboard_exposes_manifest_cache_invalidation_hook():
    content = _read("auto_agent/dashboard/templates/partials/_storyboard.html")
    assert "window.clearManifestCache = function(sceneNum, opts)" in content
    assert "window._detailSceneNum = sceneNum;" in content
    assert "window._detailSceneNum = null;" in content


def test_storyboard_cache_invalidation_refreshes_mounted_scene_and_detail_view():
    content = _read("auto_agent/dashboard/templates/partials/_storyboard.html")
    assert "mount.dataset.refresh = '1';" in content
    assert "if (window._detailSceneNum === sceneNum && overlay && overlay.classList.contains('open'))" in content
    assert "window.openSceneDetail(slug, sceneNum);" in content


def test_studio_subtitle_save_triggers_storyboard_cache_invalidation():
    content = _read("auto_agent/dashboard/templates/partials/_studio.html")
    assert "window.clearManifestCache(sceneNum, { refreshDetail: true });" in content
    assert "window.dispatchEvent(new CustomEvent('storyboard:invalidate'" in content
