import json
from pathlib import Path

from backend import chartgen, themes


def test_gen_chart_spec_uses_resolved_theme(tmp_path, monkeypatch):
    """gen_chart_spec — ae_tokens 대신 resolve된 테마의 chart 섹션 사용."""
    td = tmp_path / "cat"; td.mkdir()
    (td / "dark_broadcast.json").write_text(json.dumps({"id": "dark_broadcast", "label": "다크방송",
        "colors": {}, "chart": {"theme_set": "broadcast_signal", "theme_overrides": {}},
        "map": {"tile": "dark", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    pd = tmp_path / "p"; pd.mkdir()
    (pd / "scenes.json").write_text(json.dumps({"theme": "dark_broadcast", "scenes": []}), encoding="utf-8")
    scene = {"sceneNumber": 1, "sceneId": "cs", "layout": "bar", "headline": "t",
             "chart": {"labels": ["a", "b"], "values": [1, 2], "unit": "분"}}
    captured = {}
    def fake_run(task_path, out_dir):
        captured["task"] = json.loads(Path(task_path).read_text(encoding="utf-8"))
        spec = out_dir / "chart_spec.json"
        spec.write_text(json.dumps({"style_spec": {"theme_set": "broadcast_signal",
            "motif_tokens": {"pattern_kind_default": "diagonal_hatch"}, "layout_tokens": {}}}), encoding="utf-8")
        return spec
    monkeypatch.setattr(chartgen, "_run_cli", fake_run)
    res = chartgen.gen_chart_spec(pd, scene)
    assert res["ok"]
    assert captured["task"]["theme_set"] == "broadcast_signal"


def test_theme_pattern_kind_override(tmp_path, monkeypatch):
    """테마의 patternKind가 chartagent 결과(crosshatch)를 오버라이드(한 방향 강제)."""
    td = tmp_path / "cat"; td.mkdir()
    (td / "semoji.json").write_text(json.dumps({"id": "semoji", "label": "세모지",
        "colors": {}, "chart": {"theme_set": "gallery_infographic", "patternKind": "diagonal_hatch"},
        "map": {"tile": "bright", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    pd = tmp_path / "p"; pd.mkdir()
    (pd / "scenes.json").write_text(json.dumps({"theme": "semoji", "scenes": []}), encoding="utf-8")
    scene = {"sceneNumber": 1, "sceneId": "cs", "layout": "bar", "headline": "t",
             "chart": {"labels": ["a", "b"], "values": [1, 2]}}
    def fake_run(task_path, out_dir):
        spec = out_dir / "chart_spec.json"
        spec.write_text(json.dumps({"style_spec": {"theme_set": "gallery_infographic",
            "motif_tokens": {"pattern_kind_default": "crosshatch_light"}, "layout_tokens": {}}}), encoding="utf-8")
        return spec
    monkeypatch.setattr(chartgen, "_run_cli", fake_run)
    res = chartgen.gen_chart_spec(pd, scene)
    assert res["tokens"]["patternKind"] == "diagonal_hatch"   # 테마 오버라이드 적용
