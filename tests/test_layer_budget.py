import json

from backend import imagegen


def _els(n):
    return [{"name": f"el{i}", "location": "loc", "kind": "object", "reason": "r"} for i in range(n)]


def test_budget_keeps_first_ten_in_priority_order():
    """분석 프롬프트가 최상위(앞)부터 주므로 절단은 뒤쪽(배경에 가까운 것)부터다."""
    res = imagegen.apply_element_budget(_els(12))
    assert [e["name"] for e in res["elements"]] == [f"el{i}" for i in range(10)]
    assert [e["name"] for e in res["dropped"]] == ["el10", "el11"]
    assert imagegen.MAX_ELEMENTS == 10
    assert imagegen.MIN_ELEMENTS == 2


def test_budget_passes_through_when_under_limit():
    res = imagegen.apply_element_budget(_els(3))
    assert len(res["elements"]) == 3 and res["dropped"] == []


def test_budget_handles_empty():
    res = imagegen.apply_element_budget([])
    assert res["elements"] == [] and res["dropped"] == []


def test_analyze_applies_budget(tmp_path, monkeypatch):
    """씬당 최대 11레이어 = 요소 10 + 배경 1."""
    out_json = tmp_path / ".layer_analysis.json"

    def _fake_run(prompt, proj_dir, **kw):
        out_json.write_text(json.dumps({"elements": _els(12)}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(imagegen.llm, "run_orchestrator", _fake_run)
    res = imagegen.analyze_scene_layers(tmp_path, str(tmp_path / "scene.png"))
    assert len(res["elements"]) == 10
    assert len(res["dropped"]) == 2


