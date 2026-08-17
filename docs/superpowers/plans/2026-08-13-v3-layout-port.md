# v3 레이아웃 이식 0단계 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v3의 레이아웃 21종이 어도비에서 전부 화면에 나오게 한다 — 공통 데이터 계약, 별칭표, 범용 렌더러, 그리고 v3 임포트 배선까지.

**Architecture:** `backend/scene_layouts.py` 가 레이아웃 목록·별칭·필드 정규화의 단일 출처가 된다. 매니페스트는 정규화된 데이터만 jsx에 넘기고, jsx는 `layouts.jsx` 의 등록표에서 렌더러를 찾되 없으면 범용 렌더러로 그린다. 그래서 모르는 레이아웃 이름이 와도 내용이 사라지지 않는다.

**Tech Stack:** Python 3.11 stdlib, ExtendScript(ES3 수준), pytest.

## Global Constraints

- **어떤 레이아웃 이름도 `cinematic` 으로 떨어뜨리지 않는다.** 고유 렌더러 → 별칭 → 범용 렌더러 3단으로 반드시 그린다.
- **씬의 `title` 은 건드리지 않는다.** 어도비 씬의 `title` 은 시트에 보이는 씬 이름이다. v3 `visualization.title`(뷰 제목)은 어도비의 기존 필드 `headline` 에 넣는다. 정규화된 매니페스트 키는 `title` 이며, 이는 매니페스트에만 존재한다(매니페스트 씬에는 `title` 키가 없으므로 충돌하지 않는다).
- jsx 헬퍼(`addTextL` `addRectL` `addBarShape` `addBgSolid`)는 `akBuildScene` 안의 클로저다. 분리한 렌더러에는 `ctx` 객체로 넘긴다.
- ExtendScript는 ES3 수준이다: `var` 만, 화살표 함수·템플릿 리터럴·`const`/`let`·`Array.prototype.map` 금지. 기존 `build_scene.jsx` 스타일을 따른다.
- 한국어 주석·문구에 일본어 가나와 한자를 쓰지 않는다.
- 새 의존성을 추가하지 않는다.
- 이 계획의 범위는 0단계까지다. 목록형·구조형·차트형 고유 렌더러(1~3단계)는 만들지 않는다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/scene_layouts.py` (신규) | 레이아웃 목록·별칭표·`resolve_layout`·`normalize_fields`. 다른 모듈은 이 목록을 참조만 한다 |
| `backend/scene_analysis.py` | `_LAYOUTS` 를 `scene_layouts` 참조로 교체(현재 `bar` 누락 버그 동시 해소) |
| `skills/scene-decompose/scenes.schema.json` | enum 확장 |
| `backend/manifest.py` | 정규화된 데이터 필드를 매니페스트에 실음 |
| `backend/v3_import.py` | v3 `visualization` → 씬 레이아웃·데이터 이관 |
| `cep/…/jsx/layouts.jsx` (신규) | 렌더러 등록표 + 범용 렌더러 + 기존 5종 이관 |
| `cep/…/jsx/build_scene.jsx` | `renderLayout` 을 ctx 조립 + 등록표 조회로 축소 |
| `cep/…/js/main.js` | jsx 이어붙이기에 `layouts.jsx` 추가 |
| `tests/test_scene_layouts.py` (신규) | 목록·별칭·정규화 |

---

### Task 1: 레이아웃 단일 출처 모듈

**Files:**
- Create: `backend/scene_layouts.py`
- Test: `tests/test_scene_layouts.py`

**Interfaces:**
- Produces:
  - `NATIVE: tuple` — 어도비가 고유 렌더러를 가진 이름들
  - `ALIASES: dict` — v3 이름 → 그릴 렌더러 이름
  - `GENERIC: str` = `"generic"`
  - `KNOWN: frozenset` — 스키마 enum·검증이 쓰는 허용 목록
  - `resolve_layout(name) -> str`
  - `normalize_fields(scene: dict) -> dict`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_scene_layouts.py`:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_scene_layouts.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.scene_layouts'`

- [ ] **Step 3: 구현**

`backend/scene_layouts.py`:

```python
"""레이아웃 이름·별칭·데이터 필드의 단일 출처.

v3는 Remotion 컴포넌트 21종으로 그렸고 어도비는 AE 네이티브 렌더러 몇 종만 갖는다.
모르는 이름이 와도 내용을 버리지 않는 것이 이 모듈의 목적이다 —
고유 렌더러 → 별칭 → 범용 렌더러 3단으로 반드시 그린다.
"""
from __future__ import annotations

GENERIC = "generic"

# 어도비가 고유 렌더러를 가진 레이아웃
NATIVE = ("cinematic", "headline_only", "items_list", "metric_spotlight",
          "bar", "quote", "map")

# v3 이름 → 같은 그림을 그리는 어도비 렌더러.
# v3 VisualizationRenderer의 폴백 매핑을 그대로 가져왔다.
ALIASES = {
    # 목록형
    "slide_list": "items_list",
    "slide_numbered": "items_list",
    "narrative_build": "items_list",
    "word_cascade": "items_list",
    "icon_grid": "items_list",
    "reveal_sequence": "items_list",
    # 수치 강조
    "slide_statistic": "metric_spotlight",
    "impact_count": "metric_spotlight",
    "dramatic_number": "metric_spotlight",
    "counter_wall": "metric_spotlight",
    "icon_stat": "metric_spotlight",
    "slide_bignum": "metric_spotlight",
    # 한 문장 선언
    "slide_highlight": "headline_only",
    "spotlight_reveal": "headline_only",
    "title_card": "headline_only",
    # 차트
    "bar_chart": "bar",
    "graph": "bar",
}

# 스키마 enum·검증이 허용하는 이름 전체
KNOWN = frozenset(NATIVE) | frozenset(ALIASES) | {GENERIC}


def resolve_layout(name) -> str:
    """레이아웃 이름 → 실제로 그릴 렌더러 이름.

    고유 렌더러가 있으면 그것, 없으면 별칭, 그래도 없으면 범용.
    빈 값은 cinematic(이미지 씬)이지만, **모르는 이름은 절대 cinematic으로 보내지 않는다** —
    그러면 title·items·values가 화면에서 통째로 사라진다."""
    if not isinstance(name, str) or not name.strip():
        return "cinematic"
    key = name.strip()
    if key in NATIVE:
        return key
    return ALIASES.get(key, GENERIC)


def _first_nonempty(*vals):
    for v in vals:
        if v is None:
            continue
        if isinstance(v, (str, list, tuple, dict)) and len(v) == 0:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def normalize_fields(scene: dict) -> dict:
    """씬의 레이아웃 데이터를 v3 공통 계약으로 정규화한다(값이 있는 것만).

    어도비 기존 어휘(headline/sub/chart/value+label/quote_*)를 정규 이름으로 옮겨,
    jsx 렌더러가 한 가지 형태만 알면 되게 한다. 정규 필드가 이미 있으면 그것을 쓴다.
    씬의 title(씬 이름)은 읽지 않는다 — 뷰 제목은 headline이다."""
    s = scene or {}
    chart = s.get("chart") if isinstance(s.get("chart"), dict) else {}
    out = {
        # 씬의 title은 시트에 보이는 씬 이름이므로 읽지 않는다. 뷰 제목은 headline이다.
        "title": _first_nonempty(s.get("headline")),
        "items": _first_nonempty(s.get("items"), chart.get("labels"),
                                 [s.get("quote_text")] if s.get("quote_text") else None,
                                 [s.get("label")] if s.get("label") else None),
        "values": _first_nonempty(s.get("values"), chart.get("values"),
                                  [s.get("value")] if s.get("value") else None),
        "descriptions": _first_nonempty(s.get("descriptions"),
                                        [s.get("sub")] if s.get("sub") else None),
        "unit": _first_nonempty(s.get("unit")),
        "source": _first_nonempty(s.get("source"), s.get("quote_who")),
        "left": _first_nonempty(s.get("left")),
        "right": _first_nonempty(s.get("right")),
        "relations": _first_nonempty(s.get("relations")),
        "profileName": _first_nonempty(s.get("profileName")),
        "profileSubtitle": _first_nonempty(s.get("profileSubtitle")),
    }
    return {k: v for k, v in out.items() if v is not None}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_scene_layouts.py -q`
Expected: PASS (9 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/scene_layouts.py tests/test_scene_layouts.py
git commit -m "feat(layouts): 레이아웃 단일 출처 — 별칭표·범용 폴백·필드 정규화"
```

---

### Task 2: 레이아웃 목록을 세 곳에서 하나로

**Files:**
- Modify: `backend/scene_analysis.py:16` (`_LAYOUTS`)
- Modify: `skills/scene-decompose/scenes.schema.json` (layout enum)
- Test: `tests/test_scene_layouts.py` (추가)

**Interfaces:**
- Consumes: `scene_layouts.KNOWN`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_scene_layouts.py` 에 이어붙인다:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_scene_layouts.py -q`
Expected: FAIL — `AssertionError` (`_LAYOUTS` 가 별개 집합)

`_scene_det_checks(proj_dir: Path, scenes: list) -> dict` 가 `_LAYOUTS` 를 쓰는 함수이며, 반환 dict의 `issues` 키에 문제 문자열 목록이 들어 있다. 이 함수는 `from backend import brief as brief_mod` 를 지역 import 하므로 `proj_dir` 로 `tmp_path` 를 넘겨도 동작한다.

- [ ] **Step 3: 구현**

`backend/scene_analysis.py` 의 `_LAYOUTS` 정의 줄을 교체한다:

```python
from backend import scene_layouts as _scene_layouts

_LAYOUTS = _scene_layouts.KNOWN     # 목록은 scene_layouts가 단일 출처
```

기존 `_LAYOUTS = {"headline_only", ...}` 줄은 지운다. import는 파일 상단의 다른 `from backend import ...` 옆에 둔다.

`skills/scene-decompose/scenes.schema.json` 의 layout enum을 아래로 교체한다(알파벳 순, `null` 유지):

```json
            "enum": [
              "bar",
              "bar_chart",
              "cinematic",
              "counter_wall",
              "dramatic_number",
              "generic",
              "graph",
              "headline_only",
              "icon_grid",
              "icon_stat",
              "impact_count",
              "items_list",
              "map",
              "metric_spotlight",
              "narrative_build",
              "quote",
              "reveal_sequence",
              "slide_bignum",
              "slide_highlight",
              "slide_list",
              "slide_numbered",
              "slide_statistic",
              "spotlight_reveal",
              "title_card",
              "word_cascade",
              null
            ]
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_scene_layouts.py tests/test_scene_analyze.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/scene_analysis.py skills/scene-decompose/scenes.schema.json tests/test_scene_layouts.py
git commit -m "fix(layouts): 레이아웃 목록 단일 출처화 — bar가 비표준으로 지적되던 문제 해소"
```

---

### Task 3: 매니페스트가 정규화된 데이터를 싣는다

**Files:**
- Modify: `backend/manifest.py` (`data_fields` 조립부, 약 153-170행)
- Test: `tests/test_manifest.py` (추가)

**Interfaces:**
- Consumes: `scene_layouts.normalize_fields`, `scene_layouts.resolve_layout`
- Produces: 매니페스트 씬에 `layout`(해석된 렌더러 이름) + 정규화된 데이터 키

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_manifest.py` 에 이어붙인다:

```python
def test_manifest_normalizes_layout_data(tmp_path):
    """jsx는 정규 이름만 알면 되게 — 별칭은 백엔드에서 정리해 넘긴다."""
    import json as _j
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "headline_only",
                          "headline": "제목", "sub": "부제"}])
    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    sc = mf["scenes"][0]
    assert sc["title"] == "제목"
    assert sc["descriptions"] == ["부제"]
    assert sc["layout"] == "headline_only"


def test_manifest_resolves_unknown_layout_to_generic(tmp_path):
    """모르는 v3 이름이 와도 cinematic으로 떨어뜨리지 않는다."""
    import json as _j
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "slide_qna",
                          "headline": "질문", "items": ["가", "나"]}])
    sc = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "generic"
    assert sc["title"] == "질문" and sc["items"] == ["가", "나"]


def test_manifest_aliases_v3_layout(tmp_path):
    import json as _j
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "slide_list",
                          "headline": "제목", "items": ["가"]}])
    sc = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "items_list"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_manifest.py -q`
Expected: FAIL — `KeyError: 'title'`

- [ ] **Step 3: 구현**

`backend/manifest.py` 상단 import에 추가한다:

```python
from backend import scene_layouts
```

`layout = s.get("layout") or "cinematic"` 이 있는 줄 바로 아래에 해석을 넣는다:

```python
        layout = scene_layouts.resolve_layout(layout)   # 별칭·미지원 이름 → 그릴 수 있는 이름
```

그리고 기존 `data_fields` 조립 블록을 교체한다:

```python
        # 레이아웃 데이터 — v3 공통 계약으로 정규화해서 넘긴다(jsx는 정규 이름만 안다)
        data_fields = scene_layouts.normalize_fields(s)
```

기존의 `data_fields = {k: s[k] for k in ("headline", "sub", ...) if s.get(k) is not None}` 줄은 지운다. `**data_fields` 를 쓰는 부분은 그대로 둔다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_manifest.py tests/test_scene_layouts.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/manifest.py tests/test_manifest.py
git commit -m "feat(layouts): 매니페스트가 레이아웃 해석 + 정규화된 데이터를 싣는다"
```

---

### Task 4: v3 임포트가 레이아웃과 데이터를 옮긴다

**Files:**
- Modify: `backend/v3_import.py` (`_map_scene`, 약 25-42행)
- Test: `tests/test_v3_import.py` (기존 파일에 추가)

**Interfaces:**
- Produces: 씬에 `layout` + `headline`·`items`·`values`·`descriptions`·`unit`·`source`·`left`·`right`·`relations`·`profileName`·`profileSubtitle`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_v3_import.py` 는 이미 존재한다. 아래 테스트들을 그 파일 끝에 이어붙인다(파일 상단의 기존 import는 그대로 두고, 필요하면 `from backend import v3_import` 가 이미 있는지 확인한다):

```python
def test_map_scene_ports_layout_from_creative():
    """v3 신형: creative.layout에 레이아웃 이름이 있다."""
    out = v3_import._map_scene({
        "sceneNumber": 1, "narration": "말",
        "visualization": {"title": "제목", "items": ["가", "나"], "values": [1, 2],
                          "creative": {"concept": "개념", "layout": "headline_only",
                                       "headline": "헤드라인"}}})
    assert out["layout"] == "headline_only"
    assert out["headline"] == "제목"
    assert out["items"] == ["가", "나"] and out["values"] == [1, 2]


def test_map_scene_prefers_viztype_over_creative_layout():
    """v3 구형 매니페스트는 vizType을 갖는다 — 있으면 그것이 우선."""
    out = v3_import._map_scene({
        "sceneNumber": 1,
        "visualization": {"vizType": "slide_ranking", "title": "t",
                          "creative": {"layout": "headline_only"}}})
    assert out["layout"] == "slide_ranking"


def test_map_scene_ports_all_v3_data_fields():
    out = v3_import._map_scene({
        "sceneNumber": 1,
        "visualization": {"title": "t", "items": ["a"], "values": [1],
                          "descriptions": ["d"], "unit": "%", "source": "출처",
                          "left": {"title": "L"}, "right": {"title": "R"},
                          "relations": ["a>b"], "profileName": "이름",
                          "profileSubtitle": "직함", "vizType": "compare"}})
    for k in ("descriptions", "unit", "source", "left", "right",
              "relations", "profileName", "profileSubtitle"):
        assert k in out, k


def test_map_scene_map_scene_becomes_map_layout():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"center": [1, 2]}})
    assert out["layout"] == "map"


def test_map_scene_without_visualization_is_unchanged():
    """레이아웃 정보가 없으면 layout 키를 만들지 않는다(이미지 씬)."""
    out = v3_import._map_scene({"sceneNumber": 1, "narration": "말", "title": "제목"})
    assert "layout" not in out
    assert out["narration"] == "말"
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_v3_import.py -q`
Expected: FAIL — `KeyError: 'layout'`

- [ ] **Step 3: 구현**

`backend/v3_import.py` 의 `_map_scene` 에서 `return out` 직전에 아래를 넣는다:

```python
    # 레이아웃 이관 — v3의 visualization이 곧 레이아웃 정보다.
    # 어도비가 모르는 이름이어도 그대로 싣는다(별칭표·범용 렌더러가 받는다).
    viz = s.get("visualization") or {}
    cre = viz.get("creative") or {}
    layout = (viz.get("vizType") or cre.get("layout") or "").strip()
    if s.get("mapScene"):
        out["layout"] = "map"
        out["mapScene"] = s["mapScene"]
    elif layout:
        out["layout"] = layout
    if viz:
        if viz.get("title"):
            out["headline"] = viz["title"]          # 씬의 title(씬 이름)과 충돌하지 않게 headline으로
        elif cre.get("headline"):
            out["headline"] = cre["headline"]
        for key in ("items", "values", "descriptions", "unit", "source",
                    "left", "right", "relations", "profileName", "profileSubtitle"):
            val = viz.get(key)
            if val:
                out[key] = val
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_v3_import.py tests/test_scene_layouts.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/v3_import.py tests/test_v3_import.py
git commit -m "feat(v3): 임포트가 레이아웃·레이아웃 데이터를 옮긴다 — 전부 cinematic이 되던 문제 해소"
```

---

### Task 5: jsx 렌더러 등록표 + 범용 렌더러

**Files:**
- Create: `cep/com.autokairos.pd/jsx/layouts.jsx`
- Modify: `cep/com.autokairos.pd/jsx/build_scene.jsx` (`renderLayout`, 약 295-384행)
- Modify: `cep/com.autokairos.pd/js/main.js:221`
- Test: `tests/test_panel_structure.py` (추가)

**Interfaces:**
- Consumes: 매니페스트 씬의 `layout`(해석된 이름) + 정규화된 데이터 키
- Produces:
  - `AK_LAYOUTS` — 이름 → 렌더러 함수 등록표(`layouts.jsx` 전역)
  - `akLayout_generic(comp, s, ctx)`
  - `akRenderLayout(comp, s, ctx)` — 등록표 조회 + 폴백

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_panel_structure.py` 에 이어붙인다:

```python
def test_layouts_jsx_registry_and_generic():
    """모르는 레이아웃도 그려야 한다 — 등록표 + 범용 렌더러."""
    jsx = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    assert "AK_LAYOUTS" in jsx
    assert "function akLayout_generic" in jsx
    assert "function akRenderLayout" in jsx
    for name in ("headline_only", "items_list", "metric_spotlight", "quote"):
        assert "akLayout_" + name in jsx, name
    # ES3 수준 — 화살표 함수·템플릿 리터럴 금지
    assert "=>" not in jsx and "`" not in jsx
    assert "const " not in jsx and "let " not in jsx


def test_build_scene_delegates_to_layouts():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "akRenderLayout(" in jsx
    main = MAIN.read_text(encoding="utf-8")
    assert "layouts.jsx" in main            # 이어붙이기에 포함


def test_generic_renderer_uses_common_contract():
    """범용 렌더러는 v3 공통 계약 필드로 그린다."""
    jsx = (PANEL / "jsx" / "layouts.jsx").read_text(encoding="utf-8")
    for field in ("s.title", "s.items", "s.values", "s.descriptions", "s.source"):
        assert field in jsx, field
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_panel_structure.py -q`
Expected: FAIL — `FileNotFoundError: .../jsx/layouts.jsx`

- [ ] **Step 3: 구현**

`cep/com.autokairos.pd/jsx/layouts.jsx` 를 새로 만든다. 기존 `renderLayout` 의 5종 본문을 그대로 옮기되, 클로저였던 헬퍼는 `ctx` 에서 꺼내 쓴다:

```javascript
// auto_kairos — 씬 레이아웃 렌더러. build_scene.jsx가 ctx를 만들어 호출한다.
// 헬퍼(addTextL/addRectL/addBarShape)는 akBuildScene 안의 클로저라 ctx로 받는다.
// 모르는 레이아웃 이름은 akLayout_generic이 받는다 — 내용을 버리지 않기 위해서다.

function akLayout_headline_only(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    ctx.addRectL(comp, "accent", W / 2 - 60 * S, H * 0.30, 120 * S, 10 * S, c.accentRgb);
    ctx.addTextL(comp, s.title || "", { x: W / 2, y: H * 0.47, size: t.headline * S, rgb: c.textRgb,
                                        font: ctx.fonts.headline, box: [W * 0.84, H * 0.34], leading: 1.25,
                                        anim: s.textAnim || { type: "reveal", t0: 0.2, dur: 0.8 } });
    var sub = (s.descriptions && s.descriptions.length) ? s.descriptions[0] : "";
    if (sub) {
        ctx.addTextL(comp, sub, { x: W / 2, y: H * 0.67, size: t.sub * S, rgb: c.mutedRgb,
                                  font: ctx.fonts.body, box: [W * 0.7, H * 0.12], leading: 1.3,
                                  anim: { type: "slide", dir: "up", t0: 0.5, dur: 0.6 } });
    }
}

function akLayout_items_list(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    ctx.addTextL(comp, s.title || "", { x: W / 2, y: H * 0.16, size: t.sub * 1.5 * S, rgb: c.textRgb,
                                        font: ctx.fonts.headline, anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
    ctx.addRectL(comp, "rule", W * 0.16, H * 0.235, W * 0.68, 3 * S, c.accentRgb);
    var items = s.items || [];
    var y0 = H * 0.33, gap = Math.min(130 * S, (H * 0.58) / Math.max(1, items.length));
    for (var ii = 0; ii < items.length; ii++) {
        var by = y0 + ii * gap;
        ctx.addRectL(comp, "bullet" + ii, W * 0.16, by - 21 * S, 12 * S, 42 * S, c.accentRgb);
        var boxW = W * 0.62;
        ctx.addTextL(comp, items[ii], { x: W * 0.2 + boxW / 2, y: by, size: t.item * S, rgb: c.textRgb,
                                        font: ctx.fonts.body, just: ParagraphJustification.LEFT_JUSTIFY,
                                        box: [boxW, gap * 0.9], leading: 1.2,
                                        anim: { type: "slide", dir: "left", t0: 0.3 + ii * 0.12, dur: 0.5 } });
    }
}

function akLayout_metric_spotlight(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var val = (s.values && s.values.length) ? String(s.values[0]) : "";
    var lab = (s.items && s.items.length) ? s.items[0] : "";
    if (s.unit) { val = val + s.unit; }
    ctx.addTextL(comp, val, { x: W / 2, y: H * 0.42, size: t.metric * S, rgb: c.accentRgb,
                              font: ctx.fonts.number, leading: 1.0,
                              anim: { type: "reveal", t0: 0.2, dur: 0.7 } });
    ctx.addRectL(comp, "underline", W / 2 - 110 * S, H * 0.585, 220 * S, 5 * S, c.accentRgb);
    ctx.addTextL(comp, lab, { x: W / 2, y: H * 0.66, size: t.metricLabel * S, rgb: c.textRgb,
                              font: ctx.fonts.body, box: [W * 0.7, H * 0.12], leading: 1.3 });
}

function akLayout_quote(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    var text = (s.items && s.items.length) ? s.items[0] : "";
    ctx.addTextL(comp, text, { x: W / 2, y: H * 0.45, size: t.sub * 1.2 * S, rgb: c.textRgb,
                               font: ctx.fonts.quote, box: [W * 0.74, H * 0.4], leading: 1.4,
                               anim: { type: "reveal", t0: 0.2, dur: 0.8 } });
    if (s.source) {
        ctx.addTextL(comp, "— " + s.source, { x: W / 2, y: H * 0.72, size: t.sub * 0.8 * S,
                                              rgb: c.mutedRgb, font: ctx.fonts.body });
    }
}

function akLayout_bar(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    ctx.addTextL(comp, s.title || "", { x: W / 2, y: H * 0.13, size: t.sub * 1.4 * S, rgb: c.textRgb,
                                        font: ctx.fonts.headline, anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
    ctx.addRectL(comp, "axis", W * 0.13, H * 0.76, W * 0.74, 2 * S, c.mutedRgb);
    var vals = s.values || [], labs = s.items || [];
    var n = Math.max(1, vals.length), maxV = 0;
    for (var vi = 0; vi < vals.length; vi++) { if (vals[vi] > maxV) { maxV = vals[vi]; } }
    var gw = (W * 0.70) / n;
    for (var bi = 0; bi < vals.length; bi++) {
        var bh = maxV ? (vals[bi] / maxV) * (H * 0.42) : 0;
        var bx = W * 0.15 + gw * bi + gw * 0.225;
        var bw = gw * 0.55;
        ctx.addBarShape(comp, "bar" + bi, bw, bh, c.accentRgb, s.chartSpec || {}, S)
           .property("Position").setValue([bx + bw / 2, H * 0.76 - bh / 2]);
        if (labs[bi]) {
            ctx.addTextL(comp, labs[bi], { x: bx + bw / 2, y: H * 0.80, size: t.item * 0.8 * S,
                                           rgb: c.mutedRgb, font: ctx.fonts.body });
        }
    }
}

// 모르는 레이아웃 — 공통 계약(title/items/values/descriptions/source)만으로 그린다.
// 고유한 생김새는 아니지만 내용이 화면에서 사라지지 않는다.
function akLayout_generic(comp, s, ctx) {
    var W = ctx.W, H = ctx.H, S = ctx.S, c = ctx.colors, t = ctx.type;
    if (s.title) {
        ctx.addTextL(comp, s.title, { x: W / 2, y: H * 0.15, size: t.sub * 1.5 * S, rgb: c.textRgb,
                                      font: ctx.fonts.headline, box: [W * 0.84, H * 0.14], leading: 1.2,
                                      anim: { type: "reveal", t0: 0.15, dur: 0.6 } });
        ctx.addRectL(comp, "rule", W * 0.16, H * 0.225, W * 0.68, 3 * S, c.accentRgb);
    }
    var items = s.items || [], vals = s.values || [], descs = s.descriptions || [];
    var y0 = H * 0.32, gap = Math.min(150 * S, (H * 0.50) / Math.max(1, items.length));
    for (var i = 0; i < items.length; i++) {
        var by = y0 + i * gap;
        ctx.addRectL(comp, "gbullet" + i, W * 0.16, by - 18 * S, 10 * S, 36 * S, c.accentRgb);
        ctx.addTextL(comp, items[i], { x: W * 0.20 + (W * 0.48) / 2, y: by, size: t.item * S, rgb: c.textRgb,
                                       font: ctx.fonts.body, just: ParagraphJustification.LEFT_JUSTIFY,
                                       box: [W * 0.48, gap * 0.55], leading: 1.2,
                                       anim: { type: "slide", dir: "left", t0: 0.3 + i * 0.1, dur: 0.5 } });
        if (i < vals.length && vals[i] !== null && vals[i] !== undefined) {
            var vtext = String(vals[i]) + (s.unit ? s.unit : "");
            ctx.addTextL(comp, vtext, { x: W * 0.80, y: by, size: t.item * 1.1 * S, rgb: c.accentRgb,
                                        font: ctx.fonts.number, just: ParagraphJustification.RIGHT_JUSTIFY,
                                        box: [W * 0.16, gap * 0.55] });
        }
        if (i < descs.length && descs[i]) {
            ctx.addTextL(comp, descs[i], { x: W * 0.20 + (W * 0.48) / 2, y: by + gap * 0.34,
                                           size: t.item * 0.62 * S, rgb: c.mutedRgb, font: ctx.fonts.body,
                                           just: ParagraphJustification.LEFT_JUSTIFY,
                                           box: [W * 0.48, gap * 0.3], leading: 1.15 });
        }
    }
    if (s.source) {
        ctx.addTextL(comp, s.source, { x: W / 2, y: H * 0.93, size: t.item * 0.6 * S,
                                       rgb: c.mutedRgb, font: ctx.fonts.body });
    }
}

var AK_LAYOUTS = {
    "headline_only": akLayout_headline_only,
    "items_list": akLayout_items_list,
    "metric_spotlight": akLayout_metric_spotlight,
    "quote": akLayout_quote,
    "bar": akLayout_bar,
    "generic": akLayout_generic
};

// 등록표 조회 + 폴백. 백엔드가 이미 별칭을 해석해 보내므로 여기서는 이름 그대로 찾는다.
function akRenderLayout(comp, s, ctx) {
    var fn = AK_LAYOUTS[s.layout];
    if (!fn) { fn = akLayout_generic; }
    fn(comp, s, ctx);
}
```

`cep/com.autokairos.pd/jsx/build_scene.jsx` 의 `renderLayout` 함수 전체(배경 솔리드 이후의 `if (s.layout === ...)` 사슬 포함)를 아래로 교체한다:

```javascript
    function renderLayout(comp, s, W, H) {
        var c = TK.colors, t = TK.type;
        var S = W / 1920;                                  // 해상도 배율(1080p=1)
        addBgSolid(comp, W, H, c.bgRgb);
        // 렌더러는 layouts.jsx에 있다. 헬퍼가 이 함수의 클로저라 ctx로 넘긴다.
        akRenderLayout(comp, s, {
            W: W, H: H, S: S, colors: c, type: t, fonts: TK.fonts,
            addTextL: addTextL, addRectL: addRectL, addBarShape: addBarShape
        });
    }
```

`cep/com.autokairos.pd/js/main.js` 의 221행 부근 조립 jsx 로드를 교체한다:

```javascript
      try { jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/layouts.jsx")
                  + "\n" + readLocal("./jsx/build_scene.jsx"); }
```

- [ ] **Step 4: 테스트·문법 확인**

Run:
```bash
python3 -m pytest tests/test_panel_structure.py -q
cp cep/com.autokairos.pd/jsx/layouts.jsx /tmp/ak_layouts_check.js && node --check /tmp/ak_layouts_check.js
cp cep/com.autokairos.pd/jsx/build_scene.jsx /tmp/ak_build_check.js && node --check /tmp/ak_build_check.js
node --check cep/com.autokairos.pd/js/main.js
```
Expected: PASS + 문법 오류 없음. `node --check` 는 ExtendScript를 실행하지 못하지만 괄호·문법 오류는 잡는다.

- [ ] **Step 5: 전체 회귀**

Run:
```bash
python3 -m pytest tests/ -q \
  --ignore=tests/test_research_web_smoke.py \
  --ignore=tests/test_research_web_agent.py \
  --ignore=tests/test_research_news.py \
  --ignore=tests/test_research_lanes_basic.py
```
Expected: PASS — 직전 기준선은 668 passed. 실패가 나면 그 테스트가 옛 필드 이름(`headline`·`sub`·`chart`)을 매니페스트 출력에서 기대하고 있는지 확인하고, 정규 이름(`title`·`descriptions`·`items`/`values`)으로 고친다.

- [ ] **Step 6: 커밋**

```bash
git add cep/com.autokairos.pd/jsx/layouts.jsx cep/com.autokairos.pd/jsx/build_scene.jsx cep/com.autokairos.pd/js/main.js tests/test_panel_structure.py
git commit -m "feat(layouts): jsx 렌더러 등록표 + 범용 렌더러 — 모르는 레이아웃도 내용을 그린다"
```

---

## 사람이 직접 확인해야 하는 것

테스트는 배선까지만 보장한다. **AE에서 실제로 어떻게 보이는지는 자동 검증이 안 된다.**

1. v3 프로젝트를 임포트해 레이아웃 씬이 `cinematic` 이 아닌지 확인한다.
2. 별칭 씬(`slide_list` 등)이 기존 렌더러로 제대로 그려지는지 AE에서 본다.
3. 범용 렌더러 씬(`slide_qna`·`timeline` 등)이 읽을 만한지 본다 — 항목이 넘치거나 겹치면 `gap` 계산을 조정해야 한다.
4. `bar` 씬이 예전과 똑같이 나오는지(회귀 확인) — 차트 렌더러를 `layouts.jsx` 로 옮기면서 `addBarShape` 호출 방식이 바뀌었다.
