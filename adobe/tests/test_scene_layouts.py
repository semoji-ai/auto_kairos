"""레이아웃 단일 출처 — 목록·별칭·필드 정규화."""
from backend import scene_layouts as SL


def test_resolve_native_layouts_unchanged():
    for name in ("cinematic", "headline_only", "items_list",
                 "metric_spotlight", "bar", "quote", "map"):
        assert SL.resolve_layout(name) == name


def test_resolve_v3_aliases():
    """v3 라우터가 쓰던 매핑을 그대로 가져온다 — 같은 그림을 그리는 이름들."""
    assert SL.resolve_layout("slide_list") == "items_list"
    assert SL.resolve_layout("slide_statistic") == "metric_spotlight"
    assert SL.resolve_layout("slide_highlight") == "headline_only"
    assert SL.resolve_layout("title_card") == "headline_only"
    assert SL.resolve_layout("bar_chart") == "bar"
    assert SL.resolve_layout("graph") == "bar"
    assert SL.resolve_layout("dramatic_number") == "metric_spotlight"
    assert SL.resolve_layout("narrative_build") == "items_list"
    assert SL.resolve_layout("reveal_sequence") == "items_list"


def test_resolve_compare_aliases_to_generic():
    """spec이 요구하는 비교형 별칭 — compare 고유 렌더러가 없으니 generic으로(내용을 안 버린다)."""
    for name in ("split_contrast", "diagram", "slide_compare"):
        assert SL.resolve_layout(name) == SL.GENERIC
        assert name in SL.KNOWN


def test_normalize_takes_unit_from_chart():
    """레거시 스키마는 unit을 chart 안에 둔다 — 놓치면 막대 값의 단위가 사라진다."""
    out = SL.normalize_fields({"chart": {"labels": ["가"], "values": [40], "unit": "%"}})
    assert out["unit"] == "%"
    # 최상위 unit이 있으면 그것이 우선
    out2 = SL.normalize_fields({"unit": "명", "chart": {"labels": ["가"], "values": [1], "unit": "%"}})
    assert out2["unit"] == "명"


def test_unknown_layout_falls_back_to_generic_never_cinematic():
    """모르는 이름이라고 내용을 버리면 안 된다 — 범용 렌더러가 받는다."""
    for name in ("tech_tree", "slide_qna", "timeline", "table",
                 "완전히_모르는_이름", "", None, 123):
        got = SL.resolve_layout(name)
        assert got != "cinematic", name
        assert got in SL.NATIVE or got == SL.GENERIC, (name, got)
    assert SL.resolve_layout("tech_tree") == SL.GENERIC


def test_known_includes_native_and_aliases_and_generic():
    for name in ("bar", "cinematic", "slide_ranking", "generic"):
        assert name in SL.KNOWN, name


def test_normalize_maps_legacy_aliases():
    out = SL.normalize_fields({
        "headline": "제목", "sub": "부제",
        "chart": {"labels": ["가", "나"], "values": [3, 5]}})
    assert out["title"] == "제목"
    assert out["descriptions"] == ["부제"]
    assert out["items"] == ["가", "나"]
    assert out["values"] == [3, 5]


def test_normalize_maps_metric_and_quote():
    m = SL.normalize_fields({"value": "26", "label": "년", "unit": "년"})
    assert m["values"] == ["26"] and m["items"] == ["년"] and m["unit"] == "년"
    q = SL.normalize_fields({"quote_text": "말했다", "quote_who": "머스크"})
    assert q["items"] == ["말했다"] and q["source"] == "머스크"


def test_normalize_prefers_canonical_over_alias():
    """정규 필드가 이미 있으면 별칭이 덮어쓰지 않는다."""
    out = SL.normalize_fields({"headline": "제목",
                               "items": ["A"], "chart": {"labels": ["B"], "values": [1]}})
    assert out["title"] == "제목"
    assert out["items"] == ["A"]
    assert out["values"] == [1]          # items는 정규 우선, values는 chart에서만 온다


def test_normalize_passes_through_v3_fields():
    out = SL.normalize_fields({
        "headline": "t", "items": ["a"], "values": [1], "descriptions": ["d"],
        "unit": "%", "source": "출처",
        "left": {"title": "L", "items": ["x"]}, "right": {"title": "R", "items": ["y"]},
        "relations": ["a>b"], "profileName": "이름", "profileSubtitle": "직함"})
    for k in ("title", "items", "values", "descriptions", "unit", "source",
              "left", "right", "relations", "profileName", "profileSubtitle"):
        assert k in out, k


def test_normalize_omits_empty():
    """빈 값은 싣지 않는다 — 매니페스트가 커지고 jsx가 빈 텍스트를 그린다."""
    out = SL.normalize_fields({"headline": "", "items": [], "unit": None, "source": "출처"})
    assert out == {"source": "출처"}
    assert SL.normalize_fields({}) == {}


def test_normalize_keeps_zero_values():
    """0은 유효한 수치다 — 파이썬 truthiness로 거르면 조용히 사라진다."""
    out = SL.normalize_fields({"value": 0, "label": "년", "unit": "년"})
    assert out["values"] == [0]
    assert out["items"] == ["년"]
    # 빈 문자열은 여전히 값 없음으로 취급
    assert "values" not in SL.normalize_fields({"value": ""})


def test_layout_list_has_single_source():
    """목록이 세 곳에 흩어져 어긋나 있었다 — bar가 검증 목록에서 빠져 정상 씬이 지적됐다."""
    import json
    from pathlib import Path
    from backend import scene_analysis
    assert scene_analysis._LAYOUTS is SL.KNOWN

    schema = json.loads((Path(__file__).resolve().parents[1] / "skills" / "scene-decompose"
                         / "scenes.schema.json").read_text(encoding="utf-8"))
    enum = schema["properties"]["scenes"]["items"]["properties"]["layout"]["enum"]
    named = {e for e in enum if e is not None}
    assert named == set(SL.KNOWN), sorted(named ^ set(SL.KNOWN))
    assert "bar" in named                      # 예전에 빠져 있던 값
    assert None in enum                        # 레이아웃 미지정 허용은 유지


def test_bar_scene_is_not_flagged_nonstandard(tmp_path):
    """bar가 검증 목록에서 빠져 정상 씬이 '비표준값'으로 지적되던 문제."""
    from backend import scene_analysis
    res = scene_analysis._scene_det_checks(tmp_path, [
        {"sceneNumber": 1, "visual_summary": "요약", "layout": "bar"},
        {"sceneNumber": 2, "visual_summary": "요약", "layout": "slide_ranking"},
    ])
    assert not [i for i in res["issues"] if "layout" in i], res["issues"]
