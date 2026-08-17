# v3 지도 씬 임포트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v3에서 임포트한 지도 씬이 실제 좌표를 갖게 한다 — 지금은 `layout: "map"` 만 얻고 좌표가 없어 패널이 기본값(서울)을 렌더한다.

**Architecture:** `backend/v3_import.py` 의 `_map_scene` 이 v3 `mapScene` 을 패널이 읽는 `map_center`·`map_zoom`·`map_markers`·`map_route` 로 번역한다. v3는 좌표를 `[경도, 위도]` 로, 어도비는 `[위도, 경도]` 로 쓰므로 모든 좌표를 뒤집는다. 대응이 없는 v3 정보는 `map_v3` 에 원본째 보관한다.

**Tech Stack:** Python 3.11 stdlib, pytest.

## Global Constraints

- **좌표 순서를 뒤집는다.** v3 `[경도, 위도]` → 어도비 `[위도, 경도]`. 안 뒤집으면 예외 없이 엉뚱한 곳이 렌더된다.
- **첫 키프레임을 쓴다** — 마커가 모두 화면에 들어오고, 어도비가 지도 씬에 `slow_zoom_in` 을 자동으로 걸어 v3의 밀어들어가는 연출이 재현된다.
- **잘못된 값을 만들어내지 않는다.** 값이 이상하면 그 필드를 아예 쓰지 않는다 — 없으면 패널이 기본값으로 가고 사람이 알아채지만, 잘못된 좌표는 정상으로 보인다.
- 씬의 `title`(시트에 보이는 씬 이름)은 건드리지 않는다. v3 지도 제목은 `headline` 으로 간다.
- 마커 하나가 깨져도 그 마커만 건너뛴다 — 씬 전체를 버리지 않는다.
- `mapStyle` 을 테마로 번역하지 않는다(타일은 프로젝트/씬 테마가 정한다).
- 한국어 주석에 일본어 가나와 한자를 쓰지 않는다.
- 새 의존성을 추가하지 않는다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/v3_import.py` | `_map_scene` 의 `mapScene` 분기를 번역으로 교체 + 좌표 헬퍼 |
| `tests/test_v3_import.py` | 번역·폴백 테스트(기존 파일에 추가) |

---

### Task 1: mapScene을 패널 좌표계로 번역

**Files:**
- Modify: `backend/v3_import.py` — `_map_scene` 의 `if s.get("mapScene"):` 분기
- Test: `tests/test_v3_import.py` (기존 파일에 추가)

**Interfaces:**
- Produces:
  - `_lonlat_to_latlon(coord) -> list | None` — `[경도, 위도]` 를 `[위도, 경도]` 로. 길이 2의 숫자쌍이 아니면 `None`
  - `_map_fields(map_scene: dict) -> dict` — 패널 필드 dict(값이 유효한 것만)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_v3_import.py` 끝에 이어붙인다(파일 상단에 `from backend import v3_import` 가 이미 있다):

```python
# --- 지도 씬 임포트 ---
# 실제 v3 데이터(이란 공습 씬)의 값으로 고정한다.
MAP_SCENE = {
    "mapType": "location_reveal",
    "mapStyle": "dark_cyber",
    "title": "동시 타격",
    "source": "최소 9개 도시",
    "camera": {
        "easing": "easeOut",
        "keyframes": [
            {"frame": 0, "center": [53, 30], "zoom": 3.5, "bearing": 0, "pitch": 0},
            {"frame": 45, "center": [53, 32], "zoom": 5.0, "bearing": 0, "pitch": 0},
        ],
    },
    "markers": [
        {"coordinates": [51.39, 35.69], "label": "테헤란", "style": "pulse", "appearAtFrame": 15},
        {"coordinates": [51.68, 32.65], "label": "이스파한", "style": "pulse", "appearAtFrame": 25},
    ],
}


def test_lonlat_swapped_to_latlon():
    """v3는 [경도, 위도], 어도비는 [위도, 경도] — 안 뒤집으면 조용히 엉뚱한 곳이 렌더된다."""
    assert v3_import._lonlat_to_latlon([51.39, 35.69]) == [35.69, 51.39]
    assert v3_import._lonlat_to_latlon([53, 30]) == [30, 53]
    for bad in ([1], [1, 2, 3], ["a", 2], None, "51,35", [None, 1], {}):
        assert v3_import._lonlat_to_latlon(bad) is None, bad


def test_map_center_and_zoom_come_from_first_keyframe():
    """첫 키프레임이 가장 넓어 마커가 다 들어온다. 어도비가 slow_zoom_in을 걸어 밀어들어감이 재현된다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": MAP_SCENE})
    assert out["map_center"] == [30, 53]        # [53, 30] 뒤집힘
    assert out["map_zoom"] == 3.5               # 둘째 키프레임의 5.0이 아니다


def test_markers_translated_with_labels():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": MAP_SCENE})
    assert out["map_markers"] == [
        {"coord": [35.69, 51.39], "name": "테헤란"},
        {"coord": [32.65, 51.68], "name": "이스파한"},
    ]


def test_map_title_and_source_go_to_layout_fields():
    """씬의 title(시트에 보이는 이름)은 건드리지 않는다."""
    out = v3_import._map_scene({"sceneNumber": 1, "title": "씬 이름", "mapScene": MAP_SCENE})
    assert out["headline"] == "동시 타격"
    assert out["source"] == "최소 9개 도시"
    assert out["title"] == "씬 이름"
    assert out["layout"] == "map"


def test_original_mapscene_preserved_for_later():
    """대응 없는 정보(mapStyle·mapType·bearing·appearAtFrame 등)를 다시 임포트하지 않아도 되게."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": MAP_SCENE})
    assert out["map_v3"] == MAP_SCENE
    assert "mapScene" not in out                # 옛 키 이름은 쓰지 않는다


def test_missing_camera_leaves_center_absent():
    """좌표를 만들어내는 것보다 없는 편이 낫다 — 없으면 패널 기본값으로 가고 사람이 알아챈다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"markers": []}})
    assert out["layout"] == "map"
    assert "map_center" not in out and "map_zoom" not in out


def test_bad_center_or_zoom_are_skipped_individually():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "camera": {"keyframes": [{"center": ["a", "b"], "zoom": "가까이"}]}}})
    assert "map_center" not in out and "map_zoom" not in out
    ok_zoom = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "camera": {"keyframes": [{"center": [1], "zoom": 4}]}}})
    assert "map_center" not in ok_zoom and ok_zoom["map_zoom"] == 4


def test_broken_marker_skipped_not_whole_scene():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"markers": [
        {"coordinates": [51.39, 35.69], "label": "테헤란"},
        {"coordinates": "이상함", "label": "깨짐"},
        {"coordinates": [51.68, 32.65], "label": "이스파한"},
    ]}})
    assert [m["name"] for m in out["map_markers"]] == ["테헤란", "이스파한"]


def test_route_translated_when_present():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "route": [[53, 30], [51.39, 35.69], ["나쁨", 1]]}})
    assert out["map_route"] == [[30, 53], [35.69, 51.39]]


def test_non_map_scene_gets_no_map_fields():
    out = v3_import._map_scene({"sceneNumber": 1, "narration": "말",
                                "visualization": {"creative": {"layout": "headline_only"}}})
    assert not [k for k in out if k.startswith("map_")]
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python3 -m pytest tests/test_v3_import.py -q`
Expected: FAIL — `AttributeError: module 'backend.v3_import' has no attribute '_lonlat_to_latlon'`

- [ ] **Step 3: 구현**

`backend/v3_import.py` 의 `_map_scene` 위에 두 헬퍼를 추가한다:

```python
def _num(v):
    """숫자면 그대로, 아니면 None. bool은 숫자로 치지 않는다."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v


def _lonlat_to_latlon(coord):
    """v3 [경도, 위도] → 어도비 [위도, 경도]. 길이 2의 숫자쌍이 아니면 None.

    패널(mapgen.js)은 map_center/map_markers를 [위도, 경도]로 읽고 MapLibre에 넘길 때
    다시 뒤집는다. 여기서 안 뒤집으면 예외 없이 엉뚱한 좌표가 렌더된다."""
    if not isinstance(coord, (list, tuple)) or len(coord) != 2:
        return None
    lon, lat = _num(coord[0]), _num(coord[1])
    if lon is None or lat is None:
        return None
    return [lat, lon]


def _map_fields(map_scene: dict) -> dict:
    """v3 mapScene → 패널이 읽는 지도 필드(유효한 것만).

    카메라는 첫 키프레임을 쓴다 — 가장 넓어 마커가 다 들어오고,
    어도비가 지도 씬에 slow_zoom_in을 자동으로 걸어 v3의 밀어들어감이 재현된다."""
    m = map_scene or {}
    out: dict = {"layout": "map", "map_v3": m}
    kfs = ((m.get("camera") or {}).get("keyframes")) or []
    first = kfs[0] if kfs and isinstance(kfs[0], dict) else {}
    center = _lonlat_to_latlon(first.get("center"))
    if center:
        out["map_center"] = center
    zoom = _num(first.get("zoom"))
    if zoom is not None:
        out["map_zoom"] = zoom
    markers = []
    for mk in (m.get("markers") or []):
        if not isinstance(mk, dict):
            continue
        coord = _lonlat_to_latlon(mk.get("coordinates"))
        if coord:                                   # 깨진 마커는 그것만 건너뛴다
            markers.append({"coord": coord, "name": mk.get("label", "") or ""})
    if markers:
        out["map_markers"] = markers
    route = []
    for pt in (m.get("route") or []):
        p = _lonlat_to_latlon(pt)
        if p:
            route.append(p)
    if route:
        out["map_route"] = route
    if m.get("title"):
        out["headline"] = m["title"]                # 씬의 title(씬 이름)과 충돌하지 않게
    if m.get("source"):
        out["source"] = m["source"]
    return out
```

`_map_scene` 안의 `mapScene` 분기를 교체한다. 현재는 이렇게 되어 있다:

```python
    if s.get("mapScene"):
        out["layout"] = "map"
        out["mapScene"] = s["mapScene"]
    elif layout:
        out["layout"] = layout
```

아래로 바꾼다:

```python
    if s.get("mapScene"):
        out.update(_map_fields(s["mapScene"]))
    elif layout:
        out["layout"] = layout
```

`_map_fields` 가 `headline`·`source` 를 넣은 뒤에 아래의 `if viz:` 블록이 같은 키를 덮어쓸 수 있다. 지도 씬은 `visualization` 이 없거나 비어 있는 것이 정상이지만, 둘 다 있는 씬에서는 **지도 쪽 값이 이기도록** `if viz:` 블록의 `headline`·`source` 대입을 `out.setdefault(...)` 로 바꾼다:

```python
        if viz.get("title"):
            out.setdefault("headline", viz["title"])
        elif cre.get("headline"):
            out.setdefault("headline", cre["headline"])
```

그리고 같은 블록의 반복문에서 `source` 만 `setdefault` 로 바꾼다:

```python
        for key in ("items", "values", "descriptions", "unit",
                    "left", "right", "relations", "profileName", "profileSubtitle"):
            val = viz.get(key)
            if val:
                out[key] = val
        if viz.get("source"):
            out.setdefault("source", viz["source"])
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python3 -m pytest tests/test_v3_import.py tests/test_scene_layouts.py -q`
Expected: PASS — 신규 10개 + 기존 v3 임포트·레이아웃 테스트

- [ ] **Step 5: 전체 회귀**

Run:
```bash
python3 -m pytest tests/ -q \
  --ignore=tests/test_research_web_smoke.py \
  --ignore=tests/test_research_web_agent.py \
  --ignore=tests/test_research_news.py \
  --ignore=tests/test_research_lanes_basic.py
```
Expected: PASS — 직전 기준선은 674 passed. 기존 테스트가 `out["mapScene"]` 을 기대하고 있으면 `map_v3` 로 고친다(키 이름 변경은 의도된 것이다).

- [ ] **Step 6: 커밋**

```bash
git add backend/v3_import.py tests/test_v3_import.py
git commit -m "feat(v3): 지도 씬 좌표 이관 — 경도·위도 순서 뒤집기 + 마커·경로 번역"
```

---

## 사람이 직접 확인해야 하는 것

**지도가 실제로 그 위치에 렌더되는지는 자동 검증할 수 없다.** MapLibre 타일을 받아야 하는 일이다.

1. v3 프로젝트를 임포트한 뒤 지도 씬을 체크하고 패널의 🗺 버튼을 눌러, 서울이 아니라 의도한 지역이 나오는지 본다.
2. 마커가 지명에 맞는 자리에 찍히는지 — 좌표를 반대로 넣으면 지도는 정상으로 보이지만 마커가 엉뚱한 곳에 모인다.
3. 첫 키프레임 기준 줌이 너무 넓거나 좁지 않은지. 좁으면 마커 일부가 화면 밖으로 나간다.
