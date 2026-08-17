import json
from pathlib import Path

from backend import themes


def _catalog(tmp_path):
    """임시 카탈로그 디렉토리 + 테마 2종."""
    td = tmp_path / "themes"
    td.mkdir()
    (td / "semoji.json").write_text(json.dumps({
        "id": "semoji", "label": "세모지",
        "colors": {"accentRgb": [74, 144, 217]},
        "chart": {"theme_set": "gallery_infographic", "theme_overrides": {"pattern_mode": "outline_plus_hatch"}},
        "map": {"tile": "bright", "overrides": [], "rasterFilter": "sepia(0.3)"},
    }), encoding="utf-8")
    (td / "dark_broadcast.json").write_text(json.dumps({
        "id": "dark_broadcast", "label": "다크방송",
        "colors": {"accentRgb": [255, 80, 80]},
        "chart": {"theme_set": "broadcast_signal", "theme_overrides": {}},
        "map": {"tile": "dark", "overrides": [], "rasterFilter": ""},
    }), encoding="utf-8")
    return td


def test_list_themes(tmp_path, monkeypatch):
    td = _catalog(tmp_path)
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    ids = {t["id"] for t in themes.list_themes()}
    assert ids == {"semoji", "dark_broadcast"}


def test_load_theme(tmp_path, monkeypatch):
    td = _catalog(tmp_path)
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    t = themes.load_theme("semoji")
    assert t["chart"]["theme_set"] == "gallery_infographic"
    assert themes.load_theme("없음") is None


def test_resolve_priority_scene_over_project(tmp_path, monkeypatch):
    td = _catalog(tmp_path)
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    pd = tmp_path / "proj"; pd.mkdir()
    (pd / "scenes.json").write_text(json.dumps({"theme": "semoji", "scenes": [
        {"sceneNumber": 1, "sceneId": "a", "themeOverride": "dark_broadcast"},
        {"sceneNumber": 2, "sceneId": "b"},
    ]}), encoding="utf-8")
    data = json.loads((pd / "scenes.json").read_text())
    s1, s2 = data["scenes"]
    assert themes.resolve_theme(pd, s1)["chart"]["theme_set"] == "broadcast_signal"
    assert themes.resolve_theme(pd, s2)["chart"]["theme_set"] == "gallery_infographic"
    assert themes.resolve_theme(pd, None)["chart"]["theme_set"] == "gallery_infographic"


def test_seed_creates_three_themes(tmp_path, monkeypatch):
    """seed_themes가 시드 3종을 멱등 생성."""
    import scripts.seed_themes as seed
    td = tmp_path / "themes"
    seed.seed(td)
    ids = {p.stem for p in td.glob("*.json")}
    assert ids == {"semoji", "modern_clean", "dark_broadcast"}
    semoji = json.loads((td / "semoji.json").read_text(encoding="utf-8"))
    assert semoji["chart"]["theme_set"] == "gallery_infographic"
    assert semoji["map"]["tile"] == "bright"
    # 멱등 — 다시 실행해도 3종 유지
    seed.seed(td)
    assert len({p.stem for p in td.glob("*.json")}) == 3


def test_resolve_falls_back_to_ae_tokens(tmp_path, monkeypatch):
    """카탈로그/theme 필드 없으면 ae_tokens 기본값으로."""
    td = tmp_path / "empty_themes"; td.mkdir()
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    pd = tmp_path / "proj2"; pd.mkdir()
    (pd / "scenes.json").write_text(json.dumps({"scenes": [{"sceneNumber": 1, "sceneId": "a"}]}), encoding="utf-8")
    r = themes.resolve_theme(pd, None)
    assert "chart" in r and "map" in r and "colors" in r
