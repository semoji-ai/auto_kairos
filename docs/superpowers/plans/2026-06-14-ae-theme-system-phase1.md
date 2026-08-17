# AE 통합 테마 시스템 Phase 1 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 차트·지도 디자인을 통합 테마 카탈로그에서 골라 프로젝트 전역(+씬별 예외)으로 적용하는 시스템을 만든다.

**Architecture:** `data/artstyle/themes/<id>.json` 카탈로그 + 단일 해석 지점 `backend/themes.py:resolve_theme(씬 override → 프로젝트 theme → ae_tokens 기본)`. chartgen·manifest·mapgen이 전부 이 해석을 경유한다. 카탈로그가 없으면 기존 `ae_tokens` 동작을 그대로 유지(하위호환).

**Tech Stack:** Python(stdlib http.server 백엔드), CEP 패널 JS(ES5), chartagent CLI, pytest.

> 리서치 수집(참고 이미지 → codex 비전 → 신규 테마)은 **후속 계획**으로 분리. 이 Phase 1은 시드 테마 3종만으로 동작하는 완결된 시스템이다.

---

## 파일 구조

- Create: `backend/themes.py` — 카탈로그 로드 + `resolve_theme` 단일 해석 지점
- Create: `data/artstyle/themes/semoji.json`, `modern_clean.json`, `dark_broadcast.json` — 시드 테마
- Create: `scripts/seed_themes.py` — 시드 생성(멱등, 재현용)
- Modify: `backend/scenes.py` — `set_project_theme`/`set_scene_theme`, `load_scenes`가 resolve된 테마 노출
- Modify: `backend/chartgen.py` — `gen_chart_spec`이 `resolve_theme(...).chart` 사용
- Modify: `backend/manifest.py` — 색은 resolve된 테마에서, 사이드카 해석 유지
- Modify: `backend/router.py` — `/api/themes`, `/api/themes/set-project`, `/api/themes/set-scene`
- Modify: `cep/com.autokairos.pd/js/mapgen.js` — 씬/프로젝트 테마의 map 섹션 우선 사용
- Modify: `cep/com.autokairos.pd/js/storyboard.js` — 테마 드롭다운 + 🎨 씬 테마 버튼
- Modify: `cep/com.autokairos.pd/index.html` — 테마 셀렉터 + 버튼
- Test: `tests/test_themes.py`, `tests/test_router.py`, `tests/test_panel_structure.py`(추가)

---

## Task 1: 테마 카탈로그 로드 + resolve_theme

**Files:**
- Create: `backend/themes.py`
- Test: `tests/test_themes.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_themes.py`:
```python
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
    # 씬1: override=dark_broadcast 우선
    assert themes.resolve_theme(pd, s1)["chart"]["theme_set"] == "broadcast_signal"
    # 씬2: 프로젝트 theme=semoji
    assert themes.resolve_theme(pd, s2)["chart"]["theme_set"] == "gallery_infographic"
    # 씬 미지정: 프로젝트 theme
    assert themes.resolve_theme(pd, None)["chart"]["theme_set"] == "gallery_infographic"


def test_resolve_falls_back_to_ae_tokens(tmp_path, monkeypatch):
    """카탈로그/theme 필드 없으면 ae_tokens 기본값으로."""
    td = tmp_path / "empty_themes"; td.mkdir()
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    pd = tmp_path / "proj2"; pd.mkdir()
    (pd / "scenes.json").write_text(json.dumps({"scenes": [{"sceneNumber": 1, "sceneId": "a"}]}), encoding="utf-8")
    r = themes.resolve_theme(pd, None)
    assert "chart" in r and "map" in r and "colors" in r   # ae_tokens 기반 기본 테마
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_themes.py -v`
Expected: FAIL (`ModuleNotFoundError: backend.themes` 또는 `AttributeError`)

- [ ] **Step 3: 최소 구현 작성**

`backend/themes.py`:
```python
"""통합 테마 카탈로그 + 단일 해석 지점.

카탈로그: data/artstyle/themes/<id>.json (차트+지도+공유색 통합).
해석 우선순위: 씬.themeOverride → 프로젝트 scenes.json.theme → ae_tokens 기본값.
chartgen·manifest·mapgen이 전부 resolve_theme를 경유한다(단일 지점).
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA = Path(__file__).resolve().parents[1] / "data" / "artstyle"


def _catalog_dir() -> Path:
    return _DATA / "themes"


def _ae_tokens() -> dict:
    fp = _DATA / "ae_tokens.json"
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _default_theme() -> dict:
    """ae_tokens.json을 테마 형식으로 래핑한 기본 테마(하위호환)."""
    ae = _ae_tokens()
    ca = ae.get("chartagent") or {}
    mp = ae.get("map") or {}
    return {
        "id": "default", "label": "기본(ae_tokens)",
        "colors": ae.get("colors") or {},
        "chart": {"theme_set": ca.get("theme_set") or "dashboard_analytical",
                  "theme_overrides": ca.get("theme_overrides") or {}},
        "map": {"tile": "bright", "overrides": [],
                "rasterFilter": "", "defaultTheme": mp.get("defaultTheme") or "warm_earth"},
    }


def list_themes() -> list[dict]:
    """카탈로그의 모든 테마 dict(파일명 정렬). 디렉토리 없으면 빈 리스트."""
    cd = _catalog_dir()
    if not cd.is_dir():
        return []
    out = []
    for p in sorted(cd.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    return out


def load_theme(theme_id: str) -> dict | None:
    if not theme_id:
        return None
    p = _catalog_dir() / f"{theme_id}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _project_theme_id(proj_dir: Path) -> str | None:
    fp = proj_dir / "scenes.json"
    if not fp.is_file():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8")).get("theme")
    except json.JSONDecodeError:
        return None


def resolve_theme(proj_dir: Path, scene: dict | None = None) -> dict:
    """우선순위 병합 → {id, label, colors, chart, map}.
    씬.themeOverride → 프로젝트.theme → ae_tokens 기본."""
    tid = None
    if scene and scene.get("themeOverride"):
        tid = scene["themeOverride"]
    if not tid:
        tid = _project_theme_id(proj_dir)
    return (tid and load_theme(tid)) or _default_theme()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_themes.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add backend/themes.py tests/test_themes.py
git commit -m "feat(themes): 통합 테마 카탈로그 로드 + resolve_theme 단일 해석 지점

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: 시드 테마 3종 생성

**Files:**
- Create: `scripts/seed_themes.py`
- Create: `data/artstyle/themes/{semoji,modern_clean,dark_broadcast}.json` (스크립트가 생성)
- Test: `tests/test_themes.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_themes.py` 끝에 추가:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_themes.py::test_seed_creates_three_themes -v`
Expected: FAIL (`ModuleNotFoundError: scripts.seed_themes`)

- [ ] **Step 3: 최소 구현 작성**

`scripts/seed_themes.py`:
```python
"""시드 테마 3종 생성 — chartagent theme_set + 지도 테마(v3 이식)를 통합 테마로 매핑.
멱등(이미 있으면 덮어씀). 사용: python -m scripts.seed_themes"""
from __future__ import annotations

import json
from pathlib import Path

# 지도 레이어 오버라이드 — cep/js/mapgen.js의 MAP_THEMES와 동일 값(단일 소스 시드)
_WARM_EARTH = [
    {"match": "background", "paint": {"background-color": "#F0E8DE"}},
    {"match": "water", "paint": {"fill-color": "#C8BAA0"}},
    {"match": "boundary*", "paint": {"line-color": "#8A6E48", "line-width": 1.6, "line-opacity": 0.9}},
    {"match": "road*", "paint": {"line-color": "#C8B498", "line-opacity": 0.7}},
]
_CLEAN_WHITE = [
    {"match": "background", "paint": {"background-color": "#FFFFFF"}},
    {"match": "water", "paint": {"fill-color": "#D6E6F5"}},
    {"match": "boundary*", "paint": {"line-color": "#A0AAB8", "line-width": 1.2, "line-opacity": 0.8}},
    {"match": "road*", "paint": {"line-color": "#D8DCE4", "line-opacity": 0.7}},
]
_MATTE_SLATE = [
    {"match": "background", "paint": {"background-color": "#1A1C22"}},
    {"match": "water", "paint": {"fill-color": "#0E1018"}},
    {"match": "boundary*", "paint": {"line-color": "#6A6E7C", "line-width": 1.4, "line-opacity": 0.8}},
    {"match": "road*", "paint": {"line-color": "#383C48", "line-opacity": 0.6}},
]

_THEMES = [
    {"id": "semoji", "label": "세모지", "source": "내장 시드",
     "colors": {"accentRgb": [74, 144, 217], "textRgb": [232, 234, 237],
                "mutedRgb": [154, 160, 166], "bgRgb": [35, 38, 43]},
     "chart": {"theme_set": "gallery_infographic", "theme_overrides": {"pattern_mode": "outline_plus_hatch"}},
     "map": {"tile": "bright", "overrides": _WARM_EARTH, "rasterFilter": "sepia(0.32) saturate(0.85) brightness(1.03)"}},
    {"id": "modern_clean", "label": "모던클린", "source": "내장 시드",
     "colors": {"accentRgb": [74, 144, 217], "textRgb": [33, 37, 41],
                "mutedRgb": [134, 142, 150], "bgRgb": [248, 249, 250]},
     "chart": {"theme_set": "neutral_white", "theme_overrides": {}},
     "map": {"tile": "bright", "overrides": _CLEAN_WHITE, "rasterFilter": ""}},
    {"id": "dark_broadcast", "label": "다크방송", "source": "내장 시드",
     "colors": {"accentRgb": [255, 80, 80], "textRgb": [240, 240, 240],
                "mutedRgb": [150, 150, 150], "bgRgb": [18, 18, 20]},
     "chart": {"theme_set": "broadcast_signal", "theme_overrides": {}},
     "map": {"tile": "dark", "overrides": _MATTE_SLATE, "rasterFilter": ""}},
]


def seed(catalog_dir: Path) -> None:
    catalog_dir.mkdir(parents=True, exist_ok=True)
    for t in _THEMES:
        (catalog_dir / f"{t['id']}.json").write_text(
            json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "themes"
    seed(target)
    print(f"시드 완료: {target}")
```

- [ ] **Step 4: 테스트 통과 + 실제 시드 실행**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_themes.py::test_seed_creates_three_themes -v`
Expected: PASS

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m scripts.seed_themes`
Expected: `시드 완료: .../data/artstyle/themes`

- [ ] **Step 5: 커밋**

```bash
git add scripts/seed_themes.py data/artstyle/themes/ tests/test_themes.py
git commit -m "feat(themes): 시드 테마 3종(세모지/모던클린/다크방송) 생성 스크립트

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: 테마 설정 함수 (scenes.py)

**Files:**
- Modify: `backend/scenes.py`
- Test: `tests/test_scenes.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_scenes.py` 끝에 추가:
```python
def test_set_project_and_scene_theme(tmp_path):
    """프로젝트 전역 theme + 씬별 themeOverride 설정/해제."""
    import json
    from backend import scenes
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "a"}]}), encoding="utf-8")
    scenes.set_project_theme(tmp_path, "semoji")
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert d["theme"] == "semoji"
    scenes.set_scene_theme(tmp_path, 1, "dark_broadcast")
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert d["scenes"][0]["themeOverride"] == "dark_broadcast"
    scenes.set_scene_theme(tmp_path, 1, None)   # 해제
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert "themeOverride" not in d["scenes"][0]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scenes.py::test_set_project_and_scene_theme -v`
Expected: FAIL (`AttributeError: set_project_theme`)

- [ ] **Step 3: 최소 구현 작성**

`backend/scenes.py`의 `merge_scenes` 함수 뒤(파일 끝)에 추가:
```python
def set_project_theme(proj_dir: Path, theme_id: str) -> dict:
    """scenes.json 최상위 theme 설정. {ok} 또는 {error}."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        data["theme"] = theme_id
        fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "theme": theme_id}


def set_scene_theme(proj_dir: Path, scene_number: int, theme_id: str | None) -> dict:
    """씬 themeOverride 설정(None이면 해제). {ok} 또는 {error}."""
    with _LOCK:
        fp = _path(proj_dir)
        if not fp.is_file():
            return {"error": "scenes.json 없음"}
        data = json.loads(fp.read_text(encoding="utf-8"))
        for s in data.get("scenes", []):
            if s.get("sceneNumber") == scene_number:
                if theme_id:
                    s["themeOverride"] = theme_id
                else:
                    s.pop("themeOverride", None)
                fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                return {"ok": True, "sceneNumber": scene_number, "themeOverride": theme_id}
        return {"error": f"scene {scene_number} 없음"}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scenes.py::test_set_project_and_scene_theme -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/scenes.py tests/test_scenes.py
git commit -m "feat(themes): 프로젝트/씬 테마 설정 함수(set_project_theme/set_scene_theme)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: load_scenes가 resolve된 테마 노출

**Files:**
- Modify: `backend/scenes.py`
- Test: `tests/test_scenes.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_scenes.py` 끝에 추가:
```python
def test_load_scenes_exposes_resolved_theme(tmp_path, monkeypatch):
    """load_scenes — 프로젝트 _theme(전역) + 각 씬 _theme(override 반영)."""
    import json
    from backend import scenes, themes
    td = tmp_path / "cat"; td.mkdir()
    (td / "semoji.json").write_text(json.dumps({"id": "semoji", "label": "세모지",
        "colors": {"accentRgb": [1, 2, 3]}, "chart": {"theme_set": "gallery_infographic"},
        "map": {"tile": "bright", "overrides": []}}), encoding="utf-8")
    (td / "dark_broadcast.json").write_text(json.dumps({"id": "dark_broadcast", "label": "다크방송",
        "colors": {"accentRgb": [9, 9, 9]}, "chart": {"theme_set": "broadcast_signal"},
        "map": {"tile": "dark", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    (tmp_path / "scenes.json").write_text(json.dumps({"theme": "semoji", "scenes": [
        {"sceneNumber": 1, "sceneId": "a"},
        {"sceneNumber": 2, "sceneId": "b", "themeOverride": "dark_broadcast"}]}), encoding="utf-8")
    data = scenes.load_scenes(tmp_path)
    assert data["_theme"]["id"] == "semoji"               # 프로젝트 전역
    assert data["scenes"][0]["_theme"]["id"] == "semoji"  # override 없음 → 전역
    assert data["scenes"][1]["_theme"]["id"] == "dark_broadcast"  # override
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scenes.py::test_load_scenes_exposes_resolved_theme -v`
Expected: FAIL (`KeyError: '_theme'`)

- [ ] **Step 3: 최소 구현 작성**

`backend/scenes.py` 상단 import에 추가(파일 맨 위 import 블록):
```python
from backend import themes
```

`backend/scenes.py`의 `load_scenes` 함수에서 `data["dir"] = str(proj_dir)` 줄 **바로 앞**에 추가:
```python
        s["_theme"] = themes.resolve_theme(proj_dir, s)   # 씬별 resolve(override 반영)
```
(이 줄은 `for s in data.get("scenes", []):` 루프 **안**, 기존 `s["_status"] = {...}` 블록 뒤에 위치)

그리고 `data["dir"] = str(proj_dir)` 줄 앞(루프 밖)에 추가:
```python
    data["_theme"] = themes.resolve_theme(proj_dir, None)  # 프로젝트 전역 테마
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scenes.py -v`
Expected: PASS (기존 + 신규)

- [ ] **Step 5: 커밋**

```bash
git add backend/scenes.py tests/test_scenes.py
git commit -m "feat(themes): load_scenes가 프로젝트/씬 resolve된 테마(_theme) 노출

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: 라우터 테마 엔드포인트

**Files:**
- Modify: `backend/router.py`
- Test: `tests/test_router.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_router.py` 끝에 추가:
```python
def test_themes_endpoints(tmp_path, monkeypatch):
    """GET /api/themes 목록 + set-project/set-scene."""
    import json
    from backend import router, themes
    td = tmp_path / "cat"; td.mkdir()
    (td / "semoji.json").write_text(json.dumps({"id": "semoji", "label": "세모지",
        "colors": {}, "chart": {"theme_set": "gallery_infographic"}, "map": {"tile": "bright", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    # 목록
    st, res = router.handle_request("GET", "/api/themes", {}, None, {"root": tmp_path})
    assert st == 200 and any(t["id"] == "semoji" for t in res["themes"])
    # 프로젝트 적용
    d = tmp_path / "p1"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": [{"sceneNumber": 1, "sceneId": "a"}]}), encoding="utf-8")
    st, res = router.handle_request("POST", "/api/themes/set-project", {},
        {"project_id": "p1", "theme_id": "semoji"}, {"root": tmp_path})
    assert st == 200 and res["theme"] == "semoji"
    # 씬 적용
    st, res = router.handle_request("POST", "/api/themes/set-scene", {},
        {"project_id": "p1", "sceneNumber": 1, "theme_id": "semoji"}, {"root": tmp_path})
    assert st == 200 and res["themeOverride"] == "semoji"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_router.py::test_themes_endpoints -v`
Expected: FAIL (404 — 라우트 없음)

- [ ] **Step 3: 최소 구현 작성**

`backend/router.py` 상단 import 줄에 `themes` 추가(기존 `from backend import ... chartgen` 줄 끝):
```python
from backend import projects, skills_cfg, sessions, pipeline, imagegen, scenes, search, media, tts, manifest, assistant, llm, motion, v3_import, edits, vault, subtitles, chartgen, themes
```

`backend/router.py`의 `if method == "GET" and p == "/api/tokens":` 블록 **바로 앞**에 추가:
```python
    if method == "GET" and p == "/api/themes":
        return 200, {"themes": themes.list_themes()}

    if method == "POST" and p == "/api/themes/set-project":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.set_project_theme(proj_dir, b.get("theme_id", ""))
        if res.get("ok"):
            vault.log_work(proj_dir, "set_theme", {"theme": b.get("theme_id")})
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p == "/api/themes/set-scene":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        res = scenes.set_scene_theme(proj_dir, b.get("sceneNumber"), b.get("theme_id"))
        return (200, res) if res.get("ok") else (404, res)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_router.py::test_themes_endpoints -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(themes): /api/themes 목록 + set-project/set-scene 라우트

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: chartgen이 resolve_theme 경유

**Files:**
- Modify: `backend/chartgen.py`
- Test: `tests/test_chartgen.py` (생성)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_chartgen.py`:
```python
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
    assert captured["task"]["theme_set"] == "broadcast_signal"   # 테마에서 옴
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_chartgen.py -v`
Expected: FAIL (`gen_chart_spec()` 인자 불일치 — 현재 `ae_tokens` 인자 필요)

- [ ] **Step 3: 최소 구현 작성**

`backend/chartgen.py` 상단 import에 추가:
```python
from backend import themes
```

`backend/chartgen.py`의 `gen_chart_spec` 시그니처와 theme 결정부를 교체.
기존:
```python
def gen_chart_spec(proj_dir: Path, scene: dict, ae_tokens: dict) -> dict:
    """..."""
    sid = scene.get("sceneId")
    if not sid:
        return {"error": "sceneId 없음"}
    cfg = ae_tokens.get("chartagent") or {}
    theme_set = cfg.get("theme_set") or "dashboard_analytical"
    theme_overrides = cfg.get("theme_overrides")
```
교체:
```python
def gen_chart_spec(proj_dir: Path, scene: dict) -> dict:
    """씬 1개에 대해 chartagent 명세서 생성 → AE 토큰 추출 → chart_{sid}.spec.json 저장.
    테마는 resolve_theme(씬 override → 프로젝트 → 기본)에서 결정. 반환 {ok, tokens} 또는 {error}."""
    sid = scene.get("sceneId")
    if not sid:
        return {"error": "sceneId 없음"}
    cfg = (themes.resolve_theme(proj_dir, scene).get("chart")) or {}
    theme_set = cfg.get("theme_set") or "dashboard_analytical"
    theme_overrides = cfg.get("theme_overrides")
```

- [ ] **Step 4: 라우터 호출부 수정**

`backend/router.py`의 `/api/scenes/chart-spec` 블록에서 `ae_tokens` 로드/전달 제거.
기존:
```python
        tp = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "ae_tokens.json"
        ae_tokens = json.loads(tp.read_text(encoding="utf-8")) if tp.is_file() else {}
        try:
            res = chartgen.gen_chart_spec(proj_dir, scene, ae_tokens)
```
교체:
```python
        try:
            res = chartgen.gen_chart_spec(proj_dir, scene)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_chartgen.py tests/test_router.py -v`
Expected: PASS (기존 chart-spec 라우트 테스트도 통과 — `fake_gen`이 인자 1개 받도록 이미 `(proj_dir, scene, ae_tokens)`였다면 그 테스트의 `fake_gen` 시그니처를 `def fake_gen(proj_dir, scene):`로 수정)

- [ ] **Step 6: 커밋**

```bash
git add backend/chartgen.py backend/router.py tests/test_chartgen.py tests/test_router.py
git commit -m "feat(themes): chartgen이 resolve_theme 경유 — 차트 theme_set을 테마에서 결정

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: manifest가 resolve된 테마 색 주입

**Files:**
- Modify: `backend/manifest.py`
- Test: `tests/test_manifest.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_manifest.py` 끝에 추가:
```python
def test_manifest_injects_theme_colors(tmp_path, monkeypatch):
    """manifest — resolve된 테마 색을 themeColors로 주입(jsx가 ae_tokens 위에 오버라이드)."""
    from backend import themes
    td = tmp_path / "cat"; td.mkdir()
    (td / "dark_broadcast.json").write_text(json.dumps({"id": "dark_broadcast", "label": "다크방송",
        "colors": {"accentRgb": [255, 80, 80]}, "chart": {"theme_set": "broadcast_signal"},
        "map": {"tile": "dark", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "headline_only",
                          "headline": "x", "narration": "n"}])
    data = json.loads((d / "scenes.json").read_text()); data["theme"] = "dark_broadcast"
    (d / "scenes.json").write_text(json.dumps(data), encoding="utf-8")
    manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text())
    assert mf["themeColors"]["accentRgb"] == [255, 80, 80]
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manifest.py::test_manifest_injects_theme_colors -v`
Expected: FAIL (`KeyError: 'themeColors'`)

- [ ] **Step 3: 최소 구현 작성**

`backend/manifest.py` 상단 import에 추가:
```python
from backend import themes
```

`backend/manifest.py`의 `tokens_path = ...` 블록(파일 끝 `mf` 구성부) 바로 뒤에 추가:
```python
    proj_theme = themes.resolve_theme(proj_dir, None)
    if proj_theme.get("colors"):
        mf["themeColors"] = proj_theme["colors"]   # jsx가 ae_tokens.colors 위에 오버라이드
```

- [ ] **Step 4: jsx가 themeColors 오버라이드 적용**

`cep/com.autokairos.pd/jsx/build_scene.jsx`의 ae_tokens 로드 블록(`if (tj.type) TK.type = tj.type;` 뒤, `} catch (eTk) { }` 앞)에 추가:
```javascript
                    // 프로젝트 테마 색 오버라이드(manifest.themeColors)
                    if (m.themeColors) {
                        for (var ck in m.themeColors) { TK.colors[ck] = m.themeColors[ck]; }
                    }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manifest.py -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add backend/manifest.py cep/com.autokairos.pd/jsx/build_scene.jsx tests/test_manifest.py
git commit -m "feat(themes): manifest가 테마 색(themeColors) 주입 + jsx 오버라이드

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: mapgen이 프로젝트/씬 테마의 map 섹션 사용

**Files:**
- Modify: `cep/com.autokairos.pd/js/mapgen.js`
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_panel_structure.py` 끝에 추가:
```python
def test_mapgen_uses_scene_theme():
    """지도 — 씬/프로젝트 resolve된 테마(_theme.map)를 우선 사용(하드코딩 MAP_THEMES는 폴백)."""
    mg = (PANEL / "js" / "mapgen.js").read_text(encoding="utf-8")
    assert "_theme" in mg                     # 씬/프로젝트 테마 사용
    assert "overrides" in mg and "rasterFilter" in mg
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py::test_mapgen_uses_scene_theme -v`
Expected: FAIL (`_theme` 미사용)

- [ ] **Step 3: 최소 구현 작성**

`cep/com.autokairos.pd/js/mapgen.js`의 `_mapTheme` 함수를 교체.
기존:
```javascript
function _mapTheme() {                                      // ae_tokens.map.defaultTheme(세모지=warm_earth)
  var name = (typeof TOKENS === "object" && TOKENS && TOKENS.map && TOKENS.map.defaultTheme) || "warm_earth";
  return MAP_THEMES[name] || MAP_THEMES.warm_earth;
}
```
교체:
```javascript
// 씬에 resolve된 테마(_theme.map)가 있으면 그걸 우선 사용, 없으면 기존 MAP_THEMES(폴백).
function _mapTheme(scene) {
  var tm = scene && scene._theme && scene._theme.map;
  if (tm && tm.overrides) {
    return {
      url: tm.tile === "dark" ? MAP_DARK_URL : MAP_BRIGHT_URL,
      overrides: tm.overrides,
      rasterFilter: tm.rasterFilter || "",
    };
  }
  var name = (typeof TOKENS === "object" && TOKENS && TOKENS.map && TOKENS.map.defaultTheme) || "warm_earth";
  return MAP_THEMES[name] || MAP_THEMES.warm_earth;
}
```

- [ ] **Step 4: 호출부에 scene 전달**

`cep/com.autokairos.pd/js/mapgen.js`의 `renderMapScene(s)` 안 `var theme = _mapTheme();` 두 곳(벡터 경로 + 라스터 폴백)을 `var theme = _mapTheme(s);`로 변경.

라스터 폴백 `renderMapRaster(s)`의 테마 결정부:
```javascript
    var name = (typeof TOKENS === "object" && TOKENS && TOKENS.map && TOKENS.map.defaultTheme) || "warm_earth";
    var th = RASTER_THEMES[name] || RASTER_THEMES.warm_earth;
```
교체:
```javascript
    var tm = s && s._theme && s._theme.map;
    var th;
    if (tm && tm.overrides) {
      th = { url: tm.tile === "dark" ? "https://basemaps.cartocdn.com/dark_all/" : "https://basemaps.cartocdn.com/light_all/",
             filter: tm.rasterFilter || "", dark: tm.tile === "dark" };
    } else {
      var name = (typeof TOKENS === "object" && TOKENS && TOKENS.map && TOKENS.map.defaultTheme) || "warm_earth";
      th = RASTER_THEMES[name] || RASTER_THEMES.warm_earth;
    }
```

- [ ] **Step 5: 테스트 통과 + 구문 점검**

Run: `node --check cep/com.autokairos.pd/js/mapgen.js`
Expected: (출력 없음 = 통과)

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py::test_mapgen_uses_scene_theme -v`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add cep/com.autokairos.pd/js/mapgen.js tests/test_panel_structure.py
git commit -m "feat(themes): mapgen이 씬/프로젝트 테마의 map 섹션 우선 사용(MAP_THEMES 폴백)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: 패널 UI — 테마 드롭다운 + 🎨 씬 테마

**Files:**
- Modify: `cep/com.autokairos.pd/index.html`
- Modify: `cep/com.autokairos.pd/js/storyboard.js`
- Test: `tests/test_panel_structure.py` (추가)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_panel_structure.py` 끝에 추가:
```python
def test_theme_selector_ui():
    """테마 UI — 프로젝트 드롭다운 + 씬 테마 버튼 + 로드 함수."""
    html = HTML.read_text(encoding="utf-8")
    assert 'id="projectTheme"' in html        # 프로젝트 테마 드롭다운
    assert 'id="sa-theme"' in html            # 씬 테마 버튼
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function loadThemes" in js and "/api/themes" in js
    assert "/api/themes/set-project" in js and "/api/themes/set-scene" in js
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py::test_theme_selector_ui -v`
Expected: FAIL

- [ ] **Step 3: HTML 추가**

`cep/com.autokairos.pd/index.html`의 도구상자 `<button id="sa-chart" ...>📊 차트</button>` 줄 **뒤**에 추가:
```html
              <button id="sa-theme" title="체크한 씬에 테마 오버라이드 지정/해제">🎨 씬 테마</button>
```

같은 파일 `<div id="sheet-actionbar" ...>` 여는 태그 **앞**(도구상자 위)에 프로젝트 테마 셀렉터 추가:
```html
            <div style="display:flex;align-items:center;gap:6px;padding:4px 0;font-size:12px;color:#9aa0a6">
              <span>프로젝트 테마:</span>
              <select id="projectTheme" style="background:#23262b;color:#e6e6e6;border:1px solid #33363c;border-radius:4px;padding:3px 6px"></select>
            </div>
```

- [ ] **Step 4: storyboard.js 함수 + 바인딩 추가**

`cep/com.autokairos.pd/js/storyboard.js`의 `bindSheetToolbar` 함수 안, `on("sa-add", ...)` **앞**에 추가:
```javascript
  on("sa-theme", function () {
    var ns = _needChecked(1, "씬 테마"); if (!ns) return;
    var tid = window.prompt("이 씬에 적용할 테마 id(비우면 해제):", "");
    _runSeq(ns, function (n) {
      return fetch(BACKEND + "/api/themes/set-scene", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: n, theme_id: tid || null }),
      }).then(function (r) { return r.json(); }).then(function () { refreshRow(n); });
    });
  });
```

같은 파일 끝(파일 최하단)에 추가:
```javascript
// 프로젝트 테마 드롭다운 — 카탈로그 로드 + 현재 프로젝트 테마 선택 + 변경 시 저장
function loadThemes() {
  var sel = $("projectTheme");
  if (!sel || !SELECTED_PROJECT) return;
  fetch(BACKEND + "/api/themes").then(function (r) { return r.json(); }).then(function (j) {
    var themes = j.themes || [];
    fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
      .then(function (r) { return r.json(); }).then(function (sd) {
        var cur = (sd._theme && sd._theme.id) || "";
        sel.innerHTML = themes.map(function (t) {
          return '<option value="' + t.id + '"' + (t.id === cur ? " selected" : "") + ">" + _esc(t.label || t.id) + "</option>";
        }).join("");
      });
  });
  sel.onchange = function () {
    fetch(BACKEND + "/api/themes/set-project", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project_id: SELECTED_PROJECT, theme_id: sel.value }),
    }).then(function () { loadSheet(); });   // 미리보기 갱신
  };
}
```

`cep/com.autokairos.pd/js/storyboard.js`의 `loadSheet` 함수 안, 시트 렌더가 끝나는 `.then` 블록에서 `bindRows();` 호출 **뒤**에 추가:
```javascript
      loadThemes();
```

- [ ] **Step 5: 테스트 통과 + 구문 점검**

Run: `node --check cep/com.autokairos.pd/js/storyboard.js`
Expected: (출력 없음)

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py::test_theme_selector_ui -v`
Expected: PASS

- [ ] **Step 6: 전체 테스트 + 커밋**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 전체 PASS

```bash
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/storyboard.js tests/test_panel_structure.py
git commit -m "feat(themes): 패널 테마 UI — 프로젝트 드롭다운 + 씬 테마 오버라이드 버튼

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: 미리보기가 테마 색 반영 + 백엔드 재시작 검증

**Files:**
- Modify: `cep/com.autokairos.pd/js/storyboard.js`
- Test: 수동(E2E)

- [ ] **Step 1: 미리보기 색이 테마 따르도록 수정**

`cep/com.autokairos.pd/js/storyboard.js`의 `_previewHTML` 함수 시작부:
```javascript
function _previewHTML(s, dir) {
  var T = TOKENS || {}, c = T.colors || {}, t = T.type || {};
```
교체:
```javascript
function _previewHTML(s, dir) {
  var T = TOKENS || {}, t = T.type || {};
  var c = (s._theme && s._theme.colors) || T.colors || {};   // 씬 resolve된 테마 색 우선
```

- [ ] **Step 2: 구문 점검 + 전체 테스트**

Run: `node --check cep/com.autokairos.pd/js/storyboard.js`
Expected: (출력 없음)

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 전체 PASS

- [ ] **Step 3: 백엔드 재시작 (새 라우트/모듈 반영)**

Run:
```bash
pkill -f "backend.app"; sleep 1; (cd /Users/jleavens_macmini/LocalProjects/auto_kairos_adobe && nohup python3 -m backend.app > /tmp/ak_backend.log 2>&1 &); sleep 2
curl -s http://localhost:8765/api/themes | head -c 200
```
Expected: `{"themes": [...세모지/모던클린/다크방송...]}`

- [ ] **Step 4: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js
git commit -m "feat(themes): 시트 미리보기가 씬 테마 색 반영

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

- [ ] **Step 5: 수동 E2E 안내(사용자)**

패널 재오픈 → 수면 프로젝트 → 프로젝트 테마 드롭다운에서 "다크방송" 선택 →
시트 미리보기 색이 바뀌고, 씬6(차트) 📊 차트 재생성 시 broadcast_signal 패턴 적용 확인.
씬7(지도) 🗺 지도 재렌더 시 matte_slate(다크) 지도 확인.

---

## 자기 검토 결과 (Self-Review)

- **스펙 커버리지**: §3 카탈로그(Task 1·2), §4 적용 해석(Task 1·3·4), §5 UI(Task 9·10), §6 시드(Task 2), §7 테스트/마이그레이션(전 Task의 하위호환 테스트 + Task 6·7·8의 resolve 경유). §6 "리서치 신규 추가"는 의도적으로 **후속 계획**으로 분리(문서 상단 명시).
- **플레이스홀더**: 없음 — 모든 코드 단계에 실제 코드 포함.
- **타입 일관성**: `resolve_theme(proj_dir, scene)` 반환 `{id,label,colors,chart,map}`을 Task 6(chart)·7(colors)·8(map)이 일관 사용. `set_project_theme`/`set_scene_theme` 시그니처가 Task 3 정의 → Task 5 라우트에서 동일 사용. `_theme` 키가 Task 4에서 노출 → Task 8·10에서 소비.
- **미해결**: Task 6 Step 5의 기존 `test_chart_spec_endpoint`의 `fake_gen` 시그니처를 `(proj_dir, scene)`로 맞춰야 함(해당 단계에 명시).
