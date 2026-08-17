# 레이어 패널 + 벡터라이징 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 씬별 레이어를 포토샵식 목록으로 보며 눈을 켜고 끄고 프로젝트에서 빼고, 선택한 레이어를 Recraft로 벡터화해 AE에서 확대해도 깨지지 않게 내보낸다.

**Architecture:** 레이어의 표시/제거 상태는 기존 사이드카 `layers/{sid}__elements.json`에 `hidden`·`removed` 불리언 필드로만 기록하고 파일은 옮기지 않는다. 매니페스트가 `removed`를 거르고 `{stem}.svg`가 있으면 그것을 내보내며, jsx가 벡터 레이어에 연속 래스터화를 켠다. 벡터화는 새 모듈 `backend/vectorize.py`가 Recraft API를 stdlib `urllib`로 호출한다.

**Tech Stack:** Python 3.11 stdlib 전용(백엔드), pytest, CEP 패널 순수 ES5, ExtendScript(.jsx), Recraft vectorize API.

## Global Constraints

- 백엔드는 Python 3.11 **stdlib만** 쓴다. 새 서드파티 의존성을 넣지 않는다(PIL은 이미 선택적 의존이며 기존 용법만 유지).
- 패널 JS는 **순수 ES5**다. `let`·`const`·화살표 함수·템플릿 리터럴·`class`를 쓰지 않는다. `var`와 `function`만 쓴다.
- API 키 값을 로그·예외 메시지·응답에 **절대** 넣지 않는다. 일부라도 출력하지 않는다.
- 한국어 문자열에 **일본어 가나와 한자를 쓰지 않는다.** 순수 한글과 영어만 쓴다.
- 이미지 생성은 codex `$imagegen` 전용이라는 프로젝트 규칙이 있다. 레이어 분리(fal)에 이어 **벡터화(Recraft)도 이미지 생성이 아닌 변환**이므로 이 규칙에 저촉되지 않는다. 새 이미지를 만드는 코드를 추가하지 않는다.
- 사이드카 파일명은 `{sid}__elements.json`(상수 `imagegen.ELEMENTS_SIDECAR`)이다. 새 파일을 만들지 않는다.
- `hidden`은 패널 미리보기 전용이며 **AE 내보내기에 영향을 주지 않는다.** `removed`만 내보내기에서 빠진다.
- 배경 레이어(`imagegen.is_background_layer`)는 제거할 수 없다.
- 벡터화는 **버튼을 누를 때만** 실행한다. 레이어 분리 직후 자동 실행하지 않는다.
- 테스트에서 Recraft·fal API를 실제로 호출하지 않는다. 반드시 가짜로 대체한다.

## 파일 구조

| 파일 | 책임 | 상태 |
|---|---|---|
| `backend/imagegen.py` | 사이드카 플래그 읽기·쓰기(`set_layer_state`), 기존 `delete_layer` 제거 | 수정 |
| `backend/scenes.py` | 패널에 레이어 메타(플래그·SVG 유무·이름·z)를 실어 보냄 | 수정 |
| `backend/vectorize.py` | Recraft 호출 1건 = PNG 바이트 → SVG 바이트 | **신규** |
| `backend/router.py` | `/api/layers/state`(신규), `/api/layers/vectorize`(신규), `/api/layers/delete`(제거) | 수정 |
| `backend/manifest.py` | `removed` 필터, SVG 우선 경로, `vector` 플래그 | 수정 |
| `cep/com.autokairos.pd/jsx/build_scene.jsx` | 벡터 레이어에 연속 래스터화 켜기 | 수정 |
| `cep/com.autokairos.pd/js/storyboard.js` | 레이어 목록 UI, 합성 미리보기 | 수정 |
| `cep/com.autokairos.pd/index.html` | 목록·미리보기 CSS | 수정 |

`backend/vectorize.py`만 신규다. 나머지는 기존 파일의 좁은 수정이다. `vectorize.py`는 `fal_api.py`와 같은 위치·같은 방식(stdlib urllib, `env.get_key`)을 따른다.

---

### Task 1: 사이드카 플래그 — `set_layer_state`

**Files:**
- Modify: `backend/imagegen.py` (`delete_layer` 435-460 제거, `set_layer_state` 추가, `regenerate_layer` 462-477 필터 추가)
- Test: `tests/test_layer_state.py` (신규)

**Interfaces:**
- Consumes: `imagegen.load_element_specs(out_base, sid) -> list`, `imagegen.write_element_specs(out_base, sid, specs)`, `imagegen.is_background_layer(layer) -> bool`, `imagegen._stem_of(layer) -> str` (모두 `backend/imagegen.py`에 이미 있다)
- Produces: `imagegen.set_layer_state(proj_dir, sid, layer, *, hidden=None, removed=None, subdir="layers") -> dict` — 성공 시 `{"ok": True, "layer": str, "hidden": bool, "removed": bool}`, 실패 시 `{"error": str}`

**배경:** `layers/{sid}__elements.json`은 요소 레이어의 명세 리스트다. 각 항목은 `layer`(파일 stem)·`index`·`name`·`name_en`·`location`·`kind`·`intent`·`bbox`·`z`를 갖는다. 배경 레이어(`{sid}__bg`)는 이 리스트에 들어 있지 않다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_layer_state.py`를 만든다.

```python
import json
from pathlib import Path

from backend import imagegen

SID = "abc123"


def _proj(tmp_path: Path, specs, extra_files=()):
    """layers/ 에 사이드카와 PNG를 갖춘 임시 프로젝트."""
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    for s in specs:
        (lay / (s["layer"] + ".png")).write_bytes(b"png")
    for name in extra_files:
        (lay / name).write_bytes(b"png")
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    return tmp_path


def _sidecar(tmp_path: Path):
    return json.loads((tmp_path / "layers" / f"{SID}__elements.json").read_text(encoding="utf-8"))


def _spec(i, name):
    return {"layer": f"{SID}__{i}_{name}", "index": i, "name": name,
            "name_en": name, "location": "", "kind": "object", "intent": ""}


def test_hidden_written_to_sidecar(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__0_car", hidden=True)
    assert res["ok"] is True
    assert res["hidden"] is True
    assert res["removed"] is False
    assert _sidecar(proj)[0]["hidden"] is True


def test_removed_written_and_restored(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=True)
    assert _sidecar(proj)[0]["removed"] is True
    res = imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=False)
    assert res["removed"] is False
    assert _sidecar(proj)[0]["removed"] is False


def test_file_is_not_moved(tmp_path):
    """제거는 플래그일 뿐 — 파일은 그 자리에 있어야 복구가 즉시 된다."""
    proj = _proj(tmp_path, [_spec(0, "car")])
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=True)
    assert (proj / "layers" / f"{SID}__0_car.png").is_file()
    assert not (proj / "layers" / "_prev").exists()


def test_hidden_and_removed_are_independent(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", hidden=True)
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=True)
    entry = _sidecar(proj)[0]
    assert entry["hidden"] is True and entry["removed"] is True
    # removed만 되돌려도 hidden은 그대로 남는다
    imagegen.set_layer_state(proj, SID, f"{SID}__0_car", removed=False)
    entry = _sidecar(proj)[0]
    assert entry["hidden"] is True and entry["removed"] is False


def test_background_cannot_be_removed(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__bg.png"])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__bg", removed=True)
    assert "error" in res
    assert "ok" not in res


def test_background_can_be_hidden(tmp_path):
    """배경도 미리보기에서는 끌 수 있다 — 사이드카에 항목이 새로 생긴다."""
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__bg.png"])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__bg", hidden=True)
    assert res["ok"] is True
    entry = next(s for s in _sidecar(proj) if s["layer"] == f"{SID}__bg")
    assert entry["hidden"] is True


def test_unknown_layer_rejected(tmp_path):
    proj = _proj(tmp_path, [_spec(0, "car")])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__9_ghost", removed=True)
    assert "error" in res


def test_legacy_layer_without_sidecar_entry(tmp_path):
    """사이드카에 없지만 PNG는 있는 레거시 레이어 — 항목이 새로 생기고 기존 항목은 그대로."""
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__1_tree.png"])
    res = imagegen.set_layer_state(proj, SID, f"{SID}__1_tree", removed=True)
    assert res["ok"] is True
    side = _sidecar(proj)
    assert len(side) == 2
    assert next(s for s in side if s["layer"] == f"{SID}__0_car").get("removed") is None
    assert next(s for s in side if s["layer"] == f"{SID}__1_tree")["removed"] is True


def test_path_forms_accepted(tmp_path):
    """'layers/x.png' 같은 경로 형태도 stem으로 정규화된다."""
    proj = _proj(tmp_path, [_spec(0, "car")])
    res = imagegen.set_layer_state(proj, SID, f"layers/{SID}__0_car.png", hidden=True)
    assert res["ok"] is True
    assert _sidecar(proj)[0]["hidden"] is True


def test_regenerate_skips_removed_elements(tmp_path, monkeypatch):
    """재분리는 제거된 요소를 다시 만들지 않는다 — 배경에 녹아든다."""
    proj = _proj(tmp_path, [_spec(0, "car"), _spec(1, "tree")])
    imagegen.set_layer_state(proj, SID, f"{SID}__1_tree", removed=True)
    seen = {}

    def fake_split(proj_dir, scene_image, sid, elements, **kw):
        seen["names"] = [e["name_en"] for e in elements]
        return {"layers": [], "unexpected": [], "missing": []}

    monkeypatch.setattr(imagegen, "split_scene_to_elements", fake_split)
    imagegen.regenerate_layer(proj, "scene.png", SID, f"{SID}__0_car")
    assert seen["names"] == ["car"]


def test_regenerate_skips_specs_without_name_en(tmp_path, monkeypatch):
    """name_en이 빈 항목(배경 hidden 기록 등)은 요소 예산을 잡아먹지 않는다."""
    proj = _proj(tmp_path, [_spec(0, "car")], extra_files=[f"{SID}__bg.png"])
    imagegen.set_layer_state(proj, SID, f"{SID}__bg", hidden=True)
    seen = {}

    def fake_split(proj_dir, scene_image, sid, elements, **kw):
        seen["names"] = [e["name_en"] for e in elements]
        return {"layers": [], "unexpected": [], "missing": []}

    monkeypatch.setattr(imagegen, "split_scene_to_elements", fake_split)
    imagegen.regenerate_layer(proj, "scene.png", SID, f"{SID}__0_car")
    assert seen["names"] == ["car"]
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_layer_state.py -v`
Expected: FAIL — `AttributeError: module 'backend.imagegen' has no attribute 'set_layer_state'`

- [ ] **Step 3: `set_layer_state`를 구현한다**

`backend/imagegen.py`의 `delete_layer` 함수(435-460줄) **전체를 아래로 교체한다.** `delete_layer`는 더 이상 쓰이지 않는다(Task 2에서 호출부도 없앤다).

```python
def set_layer_state(proj_dir: Path, sid: str, layer: str, *, hidden=None, removed=None,
                    subdir: str = "layers") -> dict:
    """레이어의 hidden/removed 플래그를 사이드카에 기록한다. 파일은 옮기지 않는다.

    hidden은 패널 미리보기 전용이고 removed만 매니페스트에서 빠진다.
    파일을 그대로 두므로 복구가 플래그를 끄는 것으로 끝난다.
    반환 {ok, layer, hidden, removed} 또는 {error}."""
    out_base = Path(proj_dir) / subdir
    stem = _stem_of(layer)
    if removed and is_background_layer(stem):
        return {"error": "배경 레이어는 제거할 수 없습니다 — 합성의 바탕입니다"}
    if not (out_base / f"{stem}.png").is_file():
        return {"error": f"레이어 없음: {stem}"}
    specs = load_element_specs(out_base, sid)
    target = None
    for s in specs:
        if s.get("layer") == stem:
            target = s
            break
    if target is None:              # 배경 또는 사이드카에 없는 레거시 레이어
        target = {"layer": stem}
        specs.append(target)
    if hidden is not None:
        target["hidden"] = bool(hidden)
    if removed is not None:
        target["removed"] = bool(removed)
    write_element_specs(out_base, sid, specs)
    return {"ok": True, "layer": stem,
            "hidden": bool(target.get("hidden")), "removed": bool(target.get("removed"))}
```

- [ ] **Step 4: `regenerate_layer`에 필터를 넣는다**

`backend/imagegen.py`의 `regenerate_layer` 안에서 `elements`를 만드는 리스트 컴프리헨션을 아래로 바꾼다. 제거된 요소와 `name_en`이 빈 항목(배경의 hidden 기록 등)을 걸러 요소 예산(`MAX_ELEMENTS`)을 낭비하지 않게 한다.

기존:
```python
    elements = [{"name": s.get("name", ""), "name_en": s.get("name_en", ""),
                 "location": s.get("location", ""), "kind": s.get("kind", "object"),
                 "reason": "", "intent": s.get("intent", "")} for s in specs]
```

교체:
```python
    # 제거된 요소는 다시 만들지 않는다 — 새 배경판에 그대로 녹아든다.
    # name_en이 없는 항목(배경의 hidden 기록 등)은 분리 대상이 아니다.
    live = [s for s in specs if not s.get("removed") and (s.get("name_en") or "").strip()]
    if not live:
        return {"error": f"분리할 요소가 없습니다 — 모두 제거되었습니다: {sid}"}
    elements = [{"name": s.get("name", ""), "name_en": s.get("name_en", ""),
                 "location": s.get("location", ""), "kind": s.get("kind", "object"),
                 "reason": "", "intent": s.get("intent", "")} for s in live]
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/test_layer_state.py -v`
Expected: PASS (11건)

- [ ] **Step 6: 기존 테스트가 깨지지 않는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: `delete_layer`를 참조하는 기존 테스트가 있으면 실패한다. 있으면 그 테스트를 삭제한다 — 기능 자체가 없어졌으므로 옮겨 적지 않는다. 그 외 실패는 없어야 한다.

- [ ] **Step 7: 커밋한다**

```bash
git add backend/imagegen.py tests/test_layer_state.py
git commit -m "feat(layers): 사이드카 hidden/removed 플래그 — 파일 이동 없는 제거·복구"
```

---

### Task 2: 상태 엔드포인트 + 배경 재생성 삭제 경로 제거

**Files:**
- Modify: `backend/router.py` (`/api/layers/delete` 분기 제거 — 559-615줄의 delete 부분, `/api/layers/state` 추가)
- Modify: `backend/scenes.py:101` 부근 (`_layer_meta` 추가)
- Test: `tests/test_layer_state_api.py` (신규)

**Interfaces:**
- Consumes: `imagegen.set_layer_state(proj_dir, sid, layer, *, hidden=None, removed=None) -> dict` (Task 1), `imagegen.load_element_specs(out_base, sid) -> list`, `router.handle_request(method, path, query, body, ctx) -> (int, dict)`
- Produces:
  - `POST /api/layers/state` — 본문 `{"project_id": str, "sceneNumber": int, "layer": str, "hidden": bool?, "removed": bool?}` → 200 `{"ok": True, "layer": str, "hidden": bool, "removed": bool}` 또는 422 `{"error": str}`
  - `scenes.load_scenes()`의 각 씬에 `_layer_meta`: `{stem: {"name": str, "kind": str, "z": int|None, "hidden": bool, "removed": bool, "svg": bool}}`

**배경:** `router.py`의 모든 라우트는 `_dispatch(method, path, query, body, ctx)` 안의 `if method == ... and p == ...:` 블록이다. `p`는 `path.rstrip("/") or "/"`로 정규화돼 있다. `ctx`는 `{"root": projects_root, "jobs": JobRegistry()}`다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_layer_state_api.py`를 만든다.

```python
import json
from pathlib import Path

from backend import jobs as jobs_mod
from backend import router

SID = "abc123"


def _ctx(root):
    return {"root": root, "jobs": jobs_mod.JobRegistry()}


def _project(tmp_path: Path):
    """씬 1개 + 레이어 2장 + 사이드카를 갖춘 프로젝트."""
    proj = tmp_path / "p1"
    (proj / "layers").mkdir(parents=True)
    (proj / "storyboard").mkdir()
    (proj / "storyboard" / f"sb_{SID}.png").write_bytes(b"png")
    for stem in (f"{SID}__0_car", f"{SID}__bg"):
        (proj / "layers" / (stem + ".png")).write_bytes(b"png")
    specs = [{"layer": f"{SID}__0_car", "index": 0, "name": "차", "name_en": "car",
              "location": "", "kind": "object", "intent": "", "z": 1}]
    (proj / "layers" / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": "n",
         "imageRef": f"storyboard/sb_{SID}.png"}]}, ensure_ascii=False), encoding="utf-8")
    return proj


def test_state_sets_removed(tmp_path):
    proj = _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 1, "layer": f"{SID}__0_car", "removed": True},
        _ctx(tmp_path))
    assert status == 200
    assert res["ok"] is True and res["removed"] is True
    side = json.loads((proj / "layers" / f"{SID}__elements.json").read_text(encoding="utf-8"))
    assert side[0]["removed"] is True


def test_state_rejects_background_removal(tmp_path):
    _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 1, "layer": f"{SID}__bg", "removed": True},
        _ctx(tmp_path))
    assert status == 422
    assert "error" in res


def test_state_unknown_scene(tmp_path):
    _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 99, "layer": f"{SID}__0_car", "hidden": True},
        _ctx(tmp_path))
    assert status == 404


def test_state_requires_layer(tmp_path):
    _project(tmp_path)
    status, res = router.handle_request(
        "POST", "/api/layers/state", {},
        {"project_id": "p1", "sceneNumber": 1, "hidden": True}, _ctx(tmp_path))
    assert status == 400


def test_delete_endpoint_is_gone(tmp_path):
    """배경 재생성 삭제 경로는 제거됐다 — z0 배경판이 이미 완전하다."""
    _project(tmp_path)
    status, _ = router.handle_request(
        "POST", "/api/layers/delete", {},
        {"project_id": "p1", "sceneNumber": 1, "layer": f"{SID}__0_car"}, _ctx(tmp_path))
    assert status == 404


def test_scene_layer_meta(tmp_path):
    from backend import scenes
    proj = _project(tmp_path)
    (proj / "layers" / f"{SID}__0_car.svg").write_text("<svg/>", encoding="utf-8")
    router.handle_request("POST", "/api/layers/state", {},
                          {"project_id": "p1", "sceneNumber": 1,
                           "layer": f"{SID}__0_car", "hidden": True}, _ctx(tmp_path))
    data = scenes.load_scenes(proj)
    meta = data["scenes"][0]["_layer_meta"]
    assert meta[f"{SID}__0_car"]["hidden"] is True
    assert meta[f"{SID}__0_car"]["removed"] is False
    assert meta[f"{SID}__0_car"]["svg"] is True
    assert meta[f"{SID}__0_car"]["name"] == "차"
    assert meta[f"{SID}__bg"]["svg"] is False
    assert meta[f"{SID}__bg"]["removed"] is False
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_layer_state_api.py -v`
Expected: FAIL — `/api/layers/state`가 404를 돌려주고, `_layer_meta` 키가 없다.

- [ ] **Step 3: `_layer_meta`를 씬에 싣는다**

`backend/scenes.py`의 `load_scenes` 안, `s["_layers"] = ...` 줄 바로 다음에 넣는다.

```python
        s["_layer_meta"] = _layer_meta(lay_dir, sid) if sid and lay_dir.is_dir() else {}
```

같은 파일 아래쪽(모듈 함수 영역)에 헬퍼를 추가한다.

```python
def _layer_meta(lay_dir, sid: str) -> dict:
    """{stem: {name, kind, z, hidden, removed, svg}} — 패널 레이어 목록용.

    사이드카에 없는 레이어(배경·레거시)도 파일 기준으로 항목을 만든다.
    svg는 같은 이름의 .svg 파일 존재 여부다."""
    from backend import imagegen
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(lay_dir, sid)}
    out = {}
    for p in sorted(lay_dir.glob(f"*{sid}*.png")):
        stem = p.stem
        sp = specs.get(stem) or {}
        is_bg = imagegen.is_background_layer(stem)
        out[stem] = {
            "name": sp.get("name") or ("배경" if is_bg else stem),
            "kind": "bg" if is_bg else (sp.get("kind") or "object"),
            "z": sp.get("z"),
            "hidden": bool(sp.get("hidden")),
            "removed": bool(sp.get("removed")),
            "svg": (lay_dir / (stem + ".svg")).is_file(),
        }
    return out
```

- [ ] **Step 4: 라우터에서 삭제 경로를 제거하고 상태 경로를 추가한다**

`backend/router.py`에서 `if method == "POST" and p in ("/api/layers/delete", "/api/layers/regenerate"):` 블록을 찾는다. 조건을 `regenerate` 하나만으로 좁히고, 그 블록 안의 `# 삭제 — 파일 이동은 즉시...` 이후 코드(`imagegen.delete_layer` 호출부터 `return 200, {"ok": True, "removed": ...}`까지)를 **전부 지운다.** `regenerate` 분기는 그대로 둔다.

조건 줄을 이렇게 바꾼다.

```python
    if method == "POST" and p == "/api/layers/regenerate":
```

그리고 블록 안의 `if p == "/api/layers/regenerate":` 중첩 조건을 없애 본문을 한 단계 끌어올린다(들여쓰기만 바뀌고 로직은 그대로다).

그 블록 바로 다음에 새 라우트를 추가한다.

```python
    if method == "POST" and p == "/api/layers/state":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = next((s for s in data["scenes"] if s.get("sceneNumber") == b.get("sceneNumber")), None)
        if not sc:
            return 404, {"error": "씬 없음"}
        layer = (b.get("layer") or "").strip()
        if not layer:
            return 400, {"error": "layer 필요"}
        res = imagegen.set_layer_state(
            proj_dir, sc.get("sceneId"), layer,
            hidden=b.get("hidden"), removed=b.get("removed"))
        if res.get("error"):
            return 422, res
        return 200, res
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/test_layer_state_api.py -v`
Expected: PASS (6건)

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `python -m pytest tests/ -q`
Expected: 실패 없음. `/api/layers/delete`를 호출하는 기존 테스트가 있으면 삭제한다.

- [ ] **Step 7: 커밋한다**

```bash
git add backend/router.py backend/scenes.py tests/test_layer_state_api.py
git commit -m "feat(layers): /api/layers/state 추가, 배경 재생성 삭제 경로 제거"
```

---

### Task 3: 매니페스트 SVG 우선 + 제거 필터 + jsx 연속 래스터화

**Files:**
- Modify: `backend/manifest.py:35-83` (`_scene_layers`)
- Modify: `cep/com.autokairos.pd/jsx/build_scene.jsx` (`addLayerObj`)
- Test: `tests/test_manifest_layers_svg.py` (신규)

**Interfaces:**
- Consumes: `imagegen.load_element_specs(out_base, sid) -> list` — 항목에 `hidden`·`removed`가 있을 수 있다(Task 1)
- Produces: `_scene_layers`가 만드는 엔트리에 `vector: True`가 붙을 수 있다. `path`가 `.svg`를 가리킬 수 있다.

**배경:** `_scene_layers(proj_dir, layer_rels, sid, comp_width)`는 `layer_rels`(`layers/*{sid}*.png` 상대경로 목록)를 받아 `[{name, path, kind, position?, scale?, foot?}]`를 만든다. 배경(`__bg`)을 맨 앞에 두고 요소는 `z`로 정렬한다.

**중요:** Recraft SVG는 `width`/`height` 속성이 원본 PNG 크기와 정확히 같다(실측 확인). 따라서 `position`·`scale`·`foot` 계산은 **PNG 기준 그대로 두고** `path`만 SVG로 바꾼다. `_img_size`는 PIL이라 SVG를 못 읽으므로 크기 계산에는 반드시 PNG를 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_manifest_layers_svg.py`를 만든다.

```python
import json
from pathlib import Path

from backend import manifest

SID = "abc123"


def _layers(tmp_path: Path, specs, files):
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    for name in files:
        (lay / name).write_bytes(b"x")
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    return [f"layers/{n}" for n in files if n.endswith(".png")]


def _spec(i, name, **kw):
    d = {"layer": f"{SID}__{i}_{name}", "index": i, "name": name, "name_en": name,
         "location": "", "kind": "object", "intent": "", "z": i + 1}
    d.update(kw)
    return d


def test_removed_layer_is_excluded(tmp_path):
    rels = _layers(tmp_path, [_spec(0, "car"), _spec(1, "tree", removed=True)],
                   [f"{SID}__bg.png", f"{SID}__0_car.png", f"{SID}__1_tree.png"])
    out = manifest._scene_layers(tmp_path, rels, SID)
    names = [e["name"] for e in out]
    assert f"{SID}__1_tree" not in names
    assert f"{SID}__0_car" in names


def test_hidden_layer_is_included(tmp_path):
    """hidden은 패널 미리보기 전용 — AE에는 그대로 들어간다."""
    rels = _layers(tmp_path, [_spec(0, "car", hidden=True)],
                   [f"{SID}__bg.png", f"{SID}__0_car.png"])
    out = manifest._scene_layers(tmp_path, rels, SID)
    assert f"{SID}__0_car" in [e["name"] for e in out]


def test_svg_preferred_when_present(tmp_path):
    rels = _layers(tmp_path, [_spec(0, "car")],
                   [f"{SID}__bg.png", f"{SID}__0_car.png", f"{SID}__0_car.svg"])
    out = manifest._scene_layers(tmp_path, rels, SID)
    car = next(e for e in out if e["name"] == f"{SID}__0_car")
    assert car["path"].endswith(".svg")
    assert car["vector"] is True


def test_png_used_when_no_svg(tmp_path):
    rels = _layers(tmp_path, [_spec(0, "car")], [f"{SID}__bg.png", f"{SID}__0_car.png"])
    out = manifest._scene_layers(tmp_path, rels, SID)
    car = next(e for e in out if e["name"] == f"{SID}__0_car")
    assert car["path"].endswith(".png")
    assert "vector" not in car


def test_background_svg_also_preferred(tmp_path):
    rels = _layers(tmp_path, [_spec(0, "car")],
                   [f"{SID}__bg.png", f"{SID}__bg.svg", f"{SID}__0_car.png"])
    out = manifest._scene_layers(tmp_path, rels, SID)
    bg = out[0]
    assert bg["kind"] == "bg"
    assert bg["path"].endswith(".svg")
    assert bg["vector"] is True


def test_removed_background_still_included(tmp_path):
    """배경에 removed가 잘못 기록돼도 배경은 빠지지 않는다 — 빠지면 합성이 무너진다."""
    rels = _layers(tmp_path, [_spec(0, "car"),
                              {"layer": f"{SID}__bg", "removed": True}],
                   [f"{SID}__bg.png", f"{SID}__0_car.png"])
    out = manifest._scene_layers(tmp_path, rels, SID)
    assert out[0]["kind"] == "bg"
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_manifest_layers_svg.py -v`
Expected: FAIL — 제거 필터와 SVG 선택이 없어 `test_removed_layer_is_excluded`·`test_svg_preferred_when_present` 등이 깨진다.

- [ ] **Step 3: `_scene_layers`를 고친다**

`backend/manifest.py`의 `_scene_layers` 안에서 `bg`/`el`을 나누는 두 줄 바로 다음에 제거 필터를 넣는다.

기존:
```python
    bg = [r for r in layer_rels if "__bg" in Path(r).name]
    el = [r for r in layer_rels if "__bg" not in Path(r).name]
```

교체:
```python
    bg = [r for r in layer_rels if "__bg" in Path(r).name]
    el = [r for r in layer_rels if "__bg" not in Path(r).name]
    # 프로젝트에서 제거한 요소는 내보내지 않는다. hidden은 패널 미리보기 전용이라 무시한다.
    # 배경은 제거 대상이 아니므로 el만 거른다.
    el = [r for r in el if not (specs.get(Path(r).stem) or {}).get("removed")]
```

그리고 엔트리를 만드는 부분에서 `path`를 정할 때 SVG를 우선한다.

기존:
```python
        stem = Path(r).stem
        entry = {"name": stem, "path": _abs(proj_dir, r),
                 "kind": "bg" if "__bg" in Path(r).name else "element"}
```

교체:
```python
        stem = Path(r).stem
        # 벡터화한 레이어는 SVG로 내보낸다 — AE에서 연속 래스터화를 켜면 확대해도 깨지지 않는다.
        # 크기 계산(position/scale)은 PNG 기준을 그대로 쓴다. Recraft SVG의 width/height가
        # 원본 PNG와 같고, PIL은 SVG를 읽지 못한다.
        svg_rel = str(Path(r).with_suffix(".svg"))
        has_svg = (proj_dir / svg_rel).is_file()
        entry = {"name": stem, "path": _abs(proj_dir, svg_rel if has_svg else r),
                 "kind": "bg" if "__bg" in Path(r).name else "element"}
        if has_svg:
            entry["vector"] = True
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/test_manifest_layers_svg.py -v`
Expected: PASS (6건)

- [ ] **Step 5: jsx에서 연속 래스터화를 켠다**

`cep/com.autokairos.pd/jsx/build_scene.jsx`의 `addLayerObj` 함수에서 `var il = comp.layers.add(foot);` 바로 다음 줄에 넣는다.

```javascript
        // SVG는 기본값으로 100% 크기에서 한 번만 래스터화된다 — 확대하면 PNG처럼 깨진다.
        // 연속 래스터화를 켜야 배율마다 벡터에서 다시 그린다. 이것이 벡터화의 목적 그 자체다.
        // 부작용: 이 스위치를 켠 레이어는 블렌딩 모드와 일부 이펙트가 무시된다(AE 제약).
        if (layer.vector) { try { il.collapseTransformation = true; } catch (eCR) { } }
```

- [ ] **Step 6: 전체 테스트를 돌린다**

Run: `python -m pytest tests/ -q`
Expected: 실패 없음.

- [ ] **Step 7: 커밋한다**

```bash
git add backend/manifest.py cep/com.autokairos.pd/jsx/build_scene.jsx tests/test_manifest_layers_svg.py
git commit -m "feat(export): 제거 레이어 제외 + SVG 우선 내보내기 + AE 연속 래스터화"
```

---

### Task 4: Recraft 벡터화 — `backend/vectorize.py`와 엔드포인트

**Files:**
- Create: `backend/vectorize.py`
- Modify: `backend/router.py` (`/api/layers/vectorize` 추가, 상단 import에 `vectorize` 추가)
- Test: `tests/test_vectorize.py` (신규)

**Interfaces:**
- Consumes: `env.get_key(name) -> str` (`backend/env.py:32`), `ctx["jobs"]` (`JobRegistry`), `backend.jobs.run_async(jobs, jid, fn)`
- Produces:
  - `vectorize.VectorizeError` (Exception)
  - `vectorize.api_key() -> str`
  - `vectorize.vectorize_png(png_path, *, timeout=300) -> bytes` — SVG 바이트
  - `vectorize.vectorize_layers(proj_dir, sid, stems, *, subdir="layers", force=False, on_event=None) -> dict` — `{"ok": [stem...], "skipped": [stem...], "failed": [{"layer": stem, "error": str}...]}`
  - `POST /api/layers/vectorize` — 본문 `{"project_id": str, "sceneNumber": int, "layers": [stem...]}` → 200 `{"job_id": str, "status": "running"}`

**API 계약(실측 확인):**
```
POST https://external.api.recraft.ai/v1/images/vectorize
Authorization: Bearer <RECRAFT_API_KEY>
multipart/form-data: file=<이미지>, response_format=url
응답: {"image": {"url": ...}} 또는 {"url": ...}
```
**결과 URL 다운로드에는 브라우저 User-Agent가 반드시 필요하다.** 없으면 HTTP 403이 난다. 처음부터 붙인다 — 403을 보고 재시도하는 구조로 만들지 않는다.

비용은 이미지당 1크레딧, 소요는 장당 약 10초다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_vectorize.py`를 만든다.

```python
import json
from pathlib import Path

import pytest

from backend import vectorize

SID = "abc123"
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>'


def _proj(tmp_path: Path, stems, specs=None):
    lay = tmp_path / "layers"
    lay.mkdir(parents=True)
    for stem in stems:
        (lay / (stem + ".png")).write_bytes(b"png")
    (lay / f"{SID}__elements.json").write_text(
        json.dumps(specs or [], ensure_ascii=False), encoding="utf-8")
    return tmp_path


def test_all_layers_vectorized(tmp_path, monkeypatch):
    proj = _proj(tmp_path, [f"{SID}__bg", f"{SID}__0_car"])
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__bg", f"{SID}__0_car"])
    assert sorted(res["ok"]) == sorted([f"{SID}__bg", f"{SID}__0_car"])
    assert res["failed"] == []
    assert (proj / "layers" / f"{SID}__0_car.svg").read_bytes() == SVG


def test_partial_failure_keeps_going(tmp_path, monkeypatch):
    """3장 중 2번째가 실패해도 1·3번은 저장된다."""
    stems = [f"{SID}__0_a", f"{SID}__1_b", f"{SID}__2_c"]
    proj = _proj(tmp_path, stems)

    def flaky(path, **kw):
        if Path(path).stem == f"{SID}__1_b":
            raise vectorize.VectorizeError("서버 오류")
        return SVG

    monkeypatch.setattr(vectorize, "vectorize_png", flaky)
    res = vectorize.vectorize_layers(proj, SID, stems)
    assert sorted(res["ok"]) == [f"{SID}__0_a", f"{SID}__2_c"]
    assert len(res["failed"]) == 1
    assert res["failed"][0]["layer"] == f"{SID}__1_b"
    assert (proj / "layers" / f"{SID}__0_a.svg").is_file()
    assert (proj / "layers" / f"{SID}__2_c.svg").is_file()
    assert not (proj / "layers" / f"{SID}__1_b.svg").exists()


def test_existing_svg_is_skipped(tmp_path, monkeypatch):
    """이미 SVG가 있으면 API를 호출하지 않는다 — 크레딧을 또 쓰지 않는다."""
    proj = _proj(tmp_path, [f"{SID}__0_car"])
    (proj / "layers" / f"{SID}__0_car.svg").write_bytes(b"old")
    calls = []
    monkeypatch.setattr(vectorize, "vectorize_png",
                        lambda p, **kw: calls.append(p) or SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__0_car"])
    assert res["skipped"] == [f"{SID}__0_car"]
    assert res["ok"] == []
    assert calls == []
    assert (proj / "layers" / f"{SID}__0_car.svg").read_bytes() == b"old"


def test_force_overwrites_existing_svg(tmp_path, monkeypatch):
    """개별 재벡터화는 force로 기존 SVG를 덮어쓴다."""
    proj = _proj(tmp_path, [f"{SID}__0_car"])
    (proj / "layers" / f"{SID}__0_car.svg").write_bytes(b"old")
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__0_car"], force=True)
    assert res["ok"] == [f"{SID}__0_car"]
    assert (proj / "layers" / f"{SID}__0_car.svg").read_bytes() == SVG


def test_removed_layer_is_not_vectorized(tmp_path, monkeypatch):
    specs = [{"layer": f"{SID}__0_car", "name": "차", "name_en": "car", "removed": True}]
    proj = _proj(tmp_path, [f"{SID}__0_car"], specs)
    calls = []
    monkeypatch.setattr(vectorize, "vectorize_png",
                        lambda p, **kw: calls.append(p) or SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__0_car"])
    assert calls == []
    assert res["ok"] == []
    assert res["skipped"] == [f"{SID}__0_car"]


def test_missing_png_is_failure(tmp_path, monkeypatch):
    proj = _proj(tmp_path, [])
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    res = vectorize.vectorize_layers(proj, SID, [f"{SID}__9_ghost"])
    assert len(res["failed"]) == 1
    assert res["failed"][0]["layer"] == f"{SID}__9_ghost"


def test_events_reported(tmp_path, monkeypatch):
    stems = [f"{SID}__0_a", f"{SID}__1_b"]
    proj = _proj(tmp_path, stems)
    monkeypatch.setattr(vectorize, "vectorize_png", lambda p, **kw: SVG)
    seen = []
    vectorize.vectorize_layers(proj, SID, stems, on_event=lambda e: seen.append(e))
    assert len(seen) == 2
    assert seen[0]["layer"] == f"{SID}__0_a"
    assert seen[0]["status"] == "completed"


def test_no_key_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(vectorize, "api_key", lambda: "")
    with pytest.raises(vectorize.VectorizeError):
        vectorize.vectorize_png(tmp_path / "x.png")


def test_multipart_body_has_file_and_format():
    body, ctype = vectorize._multipart({"response_format": "url"}, "file", b"PNGDATA", "a.png")
    assert ctype.startswith("multipart/form-data; boundary=")
    assert b'name="response_format"' in body
    assert b"url" in body
    assert b'name="file"; filename="a.png"' in body
    assert b"PNGDATA" in body
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_vectorize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.vectorize'`

- [ ] **Step 3: `backend/vectorize.py`를 만든다**

```python
"""Recraft vectorize API 호출 — 레이어 PNG를 SVG로.

목적은 AE에서 확대해도 깨지지 않는 레이어다. SVG를 얹은 뒤 연속 래스터화를 켜야
효과가 나며 그 처리는 build_scene.jsx가 한다.

새 의존성 없이 stdlib urllib만 쓴다(fal_api.py와 같은 방식).
"""
from __future__ import annotations

import json
import mimetypes
import urllib.request
import uuid
from pathlib import Path

from backend import env

ENDPOINT = "https://external.api.recraft.ai/v1/images/vectorize"
KEY_NAME = "RECRAFT_API_KEY"
# 결과 URL은 브라우저 User-Agent를 요구한다 — 없으면 HTTP 403이 난다(실측).
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")


class VectorizeError(Exception):
    """벡터화 실패 — 키 없음·비200·응답 이상·내려받기 실패."""


def api_key() -> str:
    return env.get_key(KEY_NAME)


def _multipart(fields: dict, file_field: str, data: bytes, filename: str) -> tuple:
    """stdlib만으로 multipart/form-data 조립 — (body, content_type)."""
    boundary = "----ak" + uuid.uuid4().hex
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts = []
    for k, v in fields.items():
        parts.append(
            ('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
             % (boundary, k, v)).encode("utf-8"))
    parts.append(
        ('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
         'Content-Type: %s\r\n\r\n' % (boundary, file_field, filename, mime)).encode("utf-8"))
    parts.append(data)
    parts.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    return b"".join(parts), "multipart/form-data; boundary=" + boundary


def vectorize_png(png_path, *, timeout: int = 300) -> bytes:
    """PNG 1장을 SVG 바이트로. 실패 시 VectorizeError.

    키 값은 어떤 메시지에도 넣지 않는다."""
    key = api_key()
    if not key:
        raise VectorizeError(f"{KEY_NAME} 없음 — .env 또는 환경변수에 넣어 주세요")
    src = Path(png_path)
    if not src.is_file():
        raise VectorizeError(f"이미지 없음: {src.name}")
    body, ctype = _multipart({"response_format": "url"}, "file", src.read_bytes(), src.name)
    req = urllib.request.Request(
        ENDPOINT, data=body, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except VectorizeError:
        raise
    except Exception as e:
        raise VectorizeError(f"벡터화 호출 실패: {str(e)[:200]}") from e
    url = ((data.get("image") or {}).get("url") or data.get("url") or "").strip()
    if not url:
        raise VectorizeError(f"응답에 SVG URL 없음: {str(data)[:200]}")
    dl = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA,
                                              "Accept": "image/svg+xml,*/*"})
    try:
        with urllib.request.urlopen(dl, timeout=timeout) as resp:
            return resp.read()
    except Exception as e:
        raise VectorizeError(f"SVG 내려받기 실패: {str(e)[:200]}") from e


def vectorize_layers(proj_dir, sid: str, stems: list, *, subdir: str = "layers",
                     force: bool = False, on_event=None) -> dict:
    """여러 레이어를 차례로 벡터화한다. 한 장이 실패해도 나머지를 계속 처리한다.

    이미 .svg가 있거나 제거된 레이어는 건너뛴다(force면 기존 SVG를 덮어쓴다).
    반환 {"ok": [stem...], "skipped": [stem...], "failed": [{"layer", "error"}...]}."""
    from backend import imagegen
    out_base = Path(proj_dir) / subdir
    specs = {s.get("layer"): s for s in imagegen.load_element_specs(out_base, sid)}
    ok, skipped, failed = [], [], []
    for raw in stems or []:
        stem = Path(str(raw)).stem
        svg_path = out_base / (stem + ".svg")
        if (specs.get(stem) or {}).get("removed"):
            skipped.append(stem)
            continue
        if svg_path.is_file() and not force:
            skipped.append(stem)
            continue
        try:
            data = vectorize_png(out_base / (stem + ".png"))
            svg_path.write_bytes(data)
        except (VectorizeError, OSError) as e:
            failed.append({"layer": stem, "error": str(e)[:200]})
            if on_event:
                on_event({"layer": stem, "status": "failed", "error": str(e)[:200]})
            continue
        ok.append(stem)
        if on_event:
            on_event({"layer": stem, "status": "completed"})
    return {"ok": ok, "skipped": skipped, "failed": failed}
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/test_vectorize.py -v`
Expected: PASS (9건)

- [ ] **Step 5: 엔드포인트를 추가한다**

`backend/router.py` 상단 import 줄(10-12줄 부근, `from backend import ...`)에 `vectorize`를 더한다.

Task 2에서 추가한 `/api/layers/state` 블록 다음에 넣는다.

```python
    if method == "POST" and p == "/api/layers/vectorize":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        data = scenes.load_scenes(proj_dir)
        sc = next((s for s in data["scenes"] if s.get("sceneNumber") == b.get("sceneNumber")), None)
        if not sc:
            return 404, {"error": "씬 없음"}
        stems = [s for s in (b.get("layers") or []) if s]
        if not stems:
            return 400, {"error": "layers 필요"}
        if not vectorize.api_key():
            # 키가 없으면 잡을 시작하지 않는다 — 크레딧도 시간도 쓰지 않는다.
            return 422, {"error": "RECRAFT_API_KEY 없음 — .env 또는 환경변수에 넣어 주세요"}
        sid = sc.get("sceneId")
        force = bool(b.get("force"))
        jobs = ctx["jobs"]
        jid = jobs.create("layer-vectorize", pid)
        def _do_vec(proj_dir=proj_dir, sid=sid, stems=stems, force=force, jid=jid):
            res = vectorize.vectorize_layers(
                proj_dir, sid, stems, force=force,
                on_event=lambda e: jobs.append_log(
                    jid, f"{e['layer']}: {e['status']}" + (f" — {e.get('error','')}"
                                                          if e["status"] == "failed" else "")))
            jobs.set_status(jid, "running", artifact_paths=[str(proj_dir / "layers")])
            vault.log_work(proj_dir, "vectorize",
                           f"씬{sc.get('sceneNumber')} 벡터화 {len(res['ok'])}장"
                           f"(건너뜀 {len(res['skipped'])}, 실패 {len(res['failed'])})")
            return res
        run_async(jobs, jid, _do_vec)
        return 200, {"job_id": jid, "status": "running"}
```

- [ ] **Step 6: 엔드포인트 테스트를 추가한다**

`tests/test_vectorize.py` 끝에 붙인다.

```python
def test_endpoint_requires_key(tmp_path, monkeypatch):
    from backend import jobs as jobs_mod
    from backend import router
    proj = tmp_path / "p1"
    (proj / "layers").mkdir(parents=True)
    (proj / "layers" / f"{SID}__0_car.png").write_bytes(b"png")
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": "n"}]},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(vectorize, "api_key", lambda: "")
    status, res = router.handle_request(
        "POST", "/api/layers/vectorize", {},
        {"project_id": "p1", "sceneNumber": 1, "layers": [f"{SID}__0_car"]},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 422
    assert "RECRAFT_API_KEY" in res["error"]


def test_endpoint_requires_layers(tmp_path, monkeypatch):
    from backend import jobs as jobs_mod
    from backend import router
    proj = tmp_path / "p1"
    (proj / "layers").mkdir(parents=True)
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": "n"}]},
        ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(vectorize, "api_key", lambda: "k")
    status, res = router.handle_request(
        "POST", "/api/layers/vectorize", {},
        {"project_id": "p1", "sceneNumber": 1, "layers": []},
        {"root": tmp_path, "jobs": jobs_mod.JobRegistry()})
    assert status == 400
```

- [ ] **Step 7: 테스트를 돌린다**

Run: `python -m pytest tests/test_vectorize.py -v && python -m pytest tests/ -q`
Expected: 모두 PASS.

- [ ] **Step 8: 커밋한다**

```bash
git add backend/vectorize.py backend/router.py tests/test_vectorize.py
git commit -m "feat(vectorize): Recraft 벡터화 모듈 + /api/layers/vectorize (부분 실패 허용)"
```

---

### Task 5: 패널 레이어 목록 UI

**Files:**
- Modify: `cep/com.autokairos.pd/js/storyboard.js` (`renderRow` 220-290, `bindRows` 378-393, `deleteLayer` 834-867 제거, `toggleLayerOverlay` 402-419 제거)
- Modify: `cep/com.autokairos.pd/index.html` (레이어 CSS 55·92-107줄 부근)

**Interfaces:**
- Consumes: 씬 객체의 `s._layers`(`["layers/x.png", ...]`)와 `s._layer_meta`(`{stem: {name, kind, z, hidden, removed, svg}}`, Task 2), `POST /api/layers/state`(Task 2), `POST /api/layers/vectorize`(Task 4), 기존 헬퍼 `_esc(s)`, `_rowStatus(n, msg)`, `refreshRow(n)`, `_awaitJob(jobId, onDone, onLog, intervalMs)`, `BACKEND`, `SELECTED_PROJECT`
- Produces: 전역 `LYR_OPEN = {}`(씬별 목록 펼침 상태), `LYR_SEL = {}`(씬별 벡터화 선택), 함수 `renderLayerList(s, dir)`, `setLayerState(n, stem, patch)`, `vectorizeLayers(n, stems, force)`

**제약:** 순수 ES5다. `let`·`const`·화살표 함수·템플릿 리터럴을 쓰지 않는다. 기존 코드와 같이 `var`와 문자열 `+` 연결만 쓴다.

- [ ] **Step 1: CSS를 넣는다**

`cep/com.autokairos.pd/index.html`의 기존 `.lyr-item` 관련 규칙(100-107줄)을 아래로 교체한다. `.lyr-overlay`·`.lyr.sel` 규칙(93-98줄)은 `toggleLayerOverlay`와 함께 없어지므로 지운다.

```css
    /* 레이어 목록 — 포토샵식 세로 리스트. 기본은 접힘(썸네일 띠). */
    .lyr-head { display:flex; align-items:center; gap:6px; margin-top:4px; font-size:11px; color:#aaa; }
    .lyr-head .lyr-toggle { width:auto; margin:0; padding:1px 5px; font-size:11px; }
    .lyr-head .lyr-vec-all, .lyr-head .lyr-vec-sel { width:auto; margin:0; padding:1px 6px; font-size:11px; }
    .lyr-list { margin-top:3px; border:1px solid #333; border-radius:4px; }
    .lyr-row { display:flex; align-items:center; gap:5px; padding:2px 4px; border-bottom:1px solid #2a2a2a; }
    .lyr-row:last-child { border-bottom:none; }
    .lyr-row img.lyr { width:28px; height:auto; margin:0; border-radius:2px; background:#222; }
    .lyr-row .lyr-name { flex:1; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .lyr-row .lyr-kind { font-size:10px; color:#888; }
    .lyr-row .lyr-eye, .lyr-row .lyr-rm, .lyr-row .lyr-restore, .lyr-row .lyr-revec {
      width:auto; margin:0; padding:0 4px; font-size:11px; line-height:1.3; background:#333; }
    .lyr-row .lyr-rm:hover { background:#a33; }
    .lyr-row.off img.lyr, .lyr-row.off .lyr-name { opacity:0.35; }
    .lyr-row.gone { opacity:0.4; }
    .lyr-row.busy { opacity:0.4; pointer-events:none; }
    .lyr-badge { font-size:9px; padding:0 3px; border-radius:2px; background:#2d5a2d; color:#cfc; }
    .lyr-badge.fail { background:#5a2d2d; color:#fcc; }
    .lyr-sep { padding:2px 5px; font-size:10px; color:#777; background:#242424; }
```

기존 `.sheet-row .col-img .lyr { width:32px; ... }`(55줄)는 접힌 상태의 썸네일 띠가 계속 쓰므로 그대로 둔다.

- [ ] **Step 2: 목록 렌더 함수를 추가한다**

`cep/com.autokairos.pd/js/storyboard.js`에서 `renderRow` 함수 **앞에** 넣는다.

```javascript
/* ===== 레이어 목록 — 포토샵식. 기본은 접힘(썸네일 띠), 펴면 세로 목록. ===== */
var LYR_OPEN = {};      // {sceneNumber: true} — 재렌더에도 펼침 유지
var LYR_SEL = {};       // {sceneNumber: {stem: true}} — 벡터화 선택(눈과 무관)

function _lyrStem(rel) {
  return rel.split("/").pop().replace(/\.(png|svg)$/i, "");
}

/* 접힌 상태 — 지금까지 쓰던 가로 썸네일 띠(클릭하면 펴진다). */
function _lyrStrip(s, dir) {
  var meta = s._layer_meta || {};
  var html = "";
  for (var i = 0; i < (s._layers || []).length; i++) {
    var stem = _lyrStem(s._layers[i]);
    var m = meta[stem] || {};
    if (m.removed) continue;
    html += '<img class="lyr" src="file://' + dir + '/' + s._layers[i] + '"'
          + ' title="' + _esc(m.name || stem) + '"'
          + (m.hidden ? ' style="opacity:0.35"' : '') + '>';
  }
  return html;
}

/* 펼친 상태 — 세로 목록. z 오름차순, 배경이 맨 위(AE 최하단). */
function renderLayerList(s, dir) {
  var n = s.sceneNumber;
  var meta = s._layer_meta || {};
  var rels = (s._layers || []).slice();
  rels.sort(function (a, b) {
    var ma = meta[_lyrStem(a)] || {}, mb = meta[_lyrStem(b)] || {};
    if ((ma.kind === "bg") !== (mb.kind === "bg")) return ma.kind === "bg" ? -1 : 1;
    var za = (ma.z == null) ? 9999 : ma.z, zb = (mb.z == null) ? 9999 : mb.z;
    if (za !== zb) return za - zb;
    return a < b ? -1 : 1;
  });
  var sel = LYR_SEL[n] || {};
  var live = "", gone = "";
  for (var i = 0; i < rels.length; i++) {
    var stem = _lyrStem(rels[i]);
    var m = meta[stem] || {};
    var isBg = m.kind === "bg";
    var kindLabel = isBg ? "배경" : (m.kind === "character" ? "인물" : "사물");
    var thumb = '<img class="lyr" src="file://' + dir + '/' + rels[i] + '">';
    var nameCell = '<span class="lyr-name" title="' + _esc(stem) + '">'
                 + _esc(m.name || stem) + '</span>'
                 + '<span class="lyr-kind">' + kindLabel + '</span>'
                 + (m.svg ? '<span class="lyr-badge">SVG</span>' : '');
    if (m.removed) {
      gone += '<div class="lyr-row gone" data-scene="' + n + '" data-layer="' + _esc(stem) + '">'
            +   thumb + nameCell
            +   '<button class="lyr-restore" title="이 레이어를 프로젝트에 되돌립니다">↩ 복구</button>'
            + '</div>';
      continue;
    }
    live += '<div class="lyr-row' + (m.hidden ? ' off' : '') + '"'
          +   ' data-scene="' + n + '" data-layer="' + _esc(stem) + '">'
          +   '<input type="checkbox" class="lyr-pick"' + (sel[stem] ? ' checked' : '')
          +     ' title="벡터화 대상 선택">'
          +   '<button class="lyr-eye" title="패널 미리보기에서만 끕니다 — 내보내기에는 그대로 들어갑니다">'
          +     (m.hidden ? '🚫' : '👁') + '</button>'
          +   thumb + nameCell
          +   (m.svg ? '<button class="lyr-revec" title="이 레이어를 다시 벡터화합니다(1크레딧)">↻SVG</button>'
                     : '<button class="lyr-revec" title="이 레이어를 벡터화합니다(1크레딧)">SVG</button>')
          +   (isBg ? '' : '<button class="lyr-rm" title="프로젝트에서 뺍니다 — 파일은 남고 되돌릴 수 있습니다">🗑</button>')
          + '</div>';
  }
  return '<div class="lyr-list">' + live
       + (gone ? '<div class="lyr-sep">제거됨</div>' + gone : '')
       + '</div>';
}

function _lyrHead(s) {
  var n = s.sceneNumber;
  var open = !!LYR_OPEN[n];
  var count = 0, meta = s._layer_meta || {};
  for (var i = 0; i < (s._layers || []).length; i++) {
    if (!(meta[_lyrStem(s._layers[i])] || {}).removed) count++;
  }
  return '<div class="lyr-head">'
       + '<button class="lyr-toggle" data-scene="' + n + '">' + (open ? '▾' : '▸') + '</button>'
       + '<span>레이어 ' + count + '</span>'
       + (open ? '<button class="lyr-vec-all" data-scene="' + n + '"'
                 + ' title="SVG가 없는 레이어를 모두 벡터화합니다(레이어당 1크레딧)">전체 벡터화</button>'
               + '<button class="lyr-vec-sel" data-scene="' + n + '"'
                 + ' title="체크한 레이어만 벡터화합니다">선택 벡터화</button>'
             : '')
       + '</div>';
}
```

- [ ] **Step 3: `renderRow`가 목록을 쓰게 한다**

`renderRow` 안의 `var layers = (s._layers || []).map(...).join("");` 블록 **전체**를 지우고 아래로 바꾼다.

```javascript
  var hasLayers = (s._layers || []).length > 0;
  var layerBlock = hasLayers
    ? (_lyrHead(s) + (LYR_OPEN[n] ? renderLayerList(s, dir)
                                  : '<div class="lyr-strip">' + _lyrStrip(s, dir) + '</div>'))
    : "";
```

그리고 `col-img` 안에서 썸네일 띠를 넣던 줄

```javascript
    +      (layers ? '<div class="lyr-strip">' + layers + '</div>' : '')
```

을 아래로 바꾼다.

```javascript
    +      layerBlock
```

- [ ] **Step 4: 삭제·오버레이 코드를 없앤다**

- `toggleLayerOverlay` 함수(402-419줄) 전체를 지운다. 합성 미리보기(Task 6)가 그 역할을 대신한다.
- `deleteLayer` 함수(841-867줄) 전체를 지운다. 배경 재생성 경로는 백엔드에서 사라졌다.
- `bindRows` 안의 `button.lyr-del` 바인딩 루프와 `img.lyr` 클릭(`toggleLayerOverlay`) 바인딩 루프를 지운다.
- `_layerBusy(n, stem, on)`은 `.lyr-item` 대신 `.lyr-row`를 찾도록 고친다.

```javascript
function _layerBusy(n, stem, on) {
  var it = $("sheet").querySelector('.lyr-row[data-scene="' + n + '"][data-layer="' + stem + '"]');
  if (it) it.classList.toggle("busy", !!on);
}
```

`regenLayer`(869-891줄)는 그대로 둔다. `.lyr-regen` 버튼은 목록에서 없어졌으므로, `renderLayerList`의 배경 행(`isBg`)에 재분리 버튼을 하나 남긴다 — `nameCell` 뒤에 붙인다.

```javascript
          +   (isBg ? '<button class="lyr-regen" title="씬을 다시 분리합니다 — 레이어 전체가 새로 만들어집니다">↻</button>' : '')
```

`bindRows`의 `button.lyr-regen` 바인딩 루프는 `.lyr-item` 대신 `.lyr-row`를 찾도록 고친다.

```javascript
  var regs = scope.querySelectorAll("button.lyr-regen");
  for (var rgn = 0; rgn < regs.length; rgn++) {
    regs[rgn].addEventListener("click", function (ev) {
      ev.stopPropagation();
      var it = this.closest(".lyr-row");
      regenLayer(it.getAttribute("data-scene"), it.getAttribute("data-layer"));
    });
  }
```

- [ ] **Step 5: 상태 변경·벡터화 함수를 추가한다**

`regenLayer` 함수 다음에 넣는다.

```javascript
/* 눈 토글 / 제거 / 복구 — 사이드카 플래그만 바꾼다. 파일은 그대로 남는다. */
function setLayerState(n, stem, patch) {
  var b = { project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10), layer: stem };
  if (patch.hidden != null) b.hidden = patch.hidden;
  if (patch.removed != null) b.removed = patch.removed;
  _layerBusy(n, stem, true);
  return fetch(BACKEND + "/api/layers/state", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(b),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      _layerBusy(n, stem, false);
      if (!j.ok) { _rowStatus(n, "실패: " + (j.error || JSON.stringify(j))); return; }
      refreshRow(n);
    })
    .catch(function (e) { _layerBusy(n, stem, false); _rowStatus(n, "오류: " + e); });
}

/* 벡터화 — 레이어당 1크레딧. 한 장이 실패해도 나머지는 계속된다. */
function vectorizeLayers(n, stems, force) {
  if (!stems.length) { _rowStatus(n, "벡터화할 레이어를 고르세요"); return; }
  if (!confirm("레이어 " + stems.length + "장을 벡터화합니다.\n\n"
             + "레이어당 1크레딧이 들고 장당 10초쯤 걸립니다.")) return;
  _rowStatus(n, "벡터화 중... (Recraft)");
  return fetch(BACKEND + "/api/layers/vectorize", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10),
                           layers: stems, force: !!force }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "running" || !j.job_id) {
        _rowStatus(n, "실패: " + (j.error || JSON.stringify(j))); return;
      }
      _awaitJob(j.job_id, function (job) {
        if (job.status !== "completed") {
          _rowStatus(n, "벡터화 실패: " + (job.error || "")); return;
        }
        var res = job.result || {};
        var okn = (res.ok || []).length, sk = (res.skipped || []).length,
            fl = (res.failed || []).length;
        _rowStatus(n, "벡터화 완료 " + okn + "장"
                    + (sk ? " (건너뜀 " + sk + ")" : "")
                    + (fl ? " — 실패 " + fl + ": "
                          + res.failed.map(function (f) { return f.layer; }).join(", ") : ""));
        refreshRow(n);
      }, function (logs) {
        if (logs.length) _rowStatus(n, "벡터화 중... " + logs[logs.length - 1]);
      }, 1500);
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}

/* 벡터화 대상 — 전체 버튼은 SVG가 없는 살아 있는 레이어만 넘긴다(있는 것은 백엔드가 건너뛴다). */
function _lyrStemsOf(n, onlySelected) {
  var rows = $("sheet").querySelectorAll('.lyr-row[data-scene="' + n + '"]');
  var out = [];
  for (var i = 0; i < rows.length; i++) {
    if (rows[i].classList.contains("gone")) continue;
    if (onlySelected) {
      var cb = rows[i].querySelector("input.lyr-pick");
      if (!cb || !cb.checked) continue;
    }
    out.push(rows[i].getAttribute("data-layer"));
  }
  return out;
}
```

- [ ] **Step 6: 바인딩을 추가한다**

`bindRows` 안(기존 `lyr-regen` 루프 근처)에 넣는다.

```javascript
  var tgs = scope.querySelectorAll("button.lyr-toggle");
  for (var tg = 0; tg < tgs.length; tg++) {
    tgs[tg].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      LYR_OPEN[n] = !LYR_OPEN[n];
      refreshRow(n);
    });
  }
  var eyes = scope.querySelectorAll("button.lyr-eye");
  for (var ey = 0; ey < eyes.length; ey++) {
    eyes[ey].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      setLayerState(row.getAttribute("data-scene"), row.getAttribute("data-layer"),
                    { hidden: !row.classList.contains("off") });
    });
  }
  var rms = scope.querySelectorAll("button.lyr-rm");
  for (var rm = 0; rm < rms.length; rm++) {
    rms[rm].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      setLayerState(row.getAttribute("data-scene"), row.getAttribute("data-layer"),
                    { removed: true });
    });
  }
  var rsts = scope.querySelectorAll("button.lyr-restore");
  for (var rst = 0; rst < rsts.length; rst++) {
    rsts[rst].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      setLayerState(row.getAttribute("data-scene"), row.getAttribute("data-layer"),
                    { removed: false });
    });
  }
  var picks = scope.querySelectorAll("input.lyr-pick");
  for (var pk = 0; pk < picks.length; pk++) {
    picks[pk].addEventListener("change", function () {
      var row = this.closest(".lyr-row");
      var n = row.getAttribute("data-scene"), stem = row.getAttribute("data-layer");
      if (!LYR_SEL[n]) LYR_SEL[n] = {};
      if (this.checked) LYR_SEL[n][stem] = true; else delete LYR_SEL[n][stem];
    });
  }
  var vall = scope.querySelectorAll("button.lyr-vec-all");
  for (var va = 0; va < vall.length; va++) {
    vall[va].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      vectorizeLayers(n, _lyrStemsOf(n, false), false);
    });
  }
  var vsel = scope.querySelectorAll("button.lyr-vec-sel");
  for (var vs = 0; vs < vsel.length; vs++) {
    vsel[vs].addEventListener("click", function () {
      var n = this.getAttribute("data-scene");
      vectorizeLayers(n, _lyrStemsOf(n, true), false);
    });
  }
  var revs = scope.querySelectorAll("button.lyr-revec");
  for (var rv = 0; rv < revs.length; rv++) {
    revs[rv].addEventListener("click", function () {
      var row = this.closest(".lyr-row");
      var n = row.getAttribute("data-scene");
      // 이미 SVG가 있는 레이어를 다시 벡터화할 때만 force가 필요하다.
      var has = !!row.querySelector(".lyr-badge");
      vectorizeLayers(n, [row.getAttribute("data-layer")], has);
    });
  }
```

- [ ] **Step 7: 문법을 확인한다**

Run: `node --check cep/com.autokairos.pd/js/storyboard.js`
Expected: 출력 없음(문법 오류 없음)

ES5 위반이 없는지 확인한다.

Run: `grep -nE "=>|\blet\b|\bconst\b|\`" cep/com.autokairos.pd/js/storyboard.js`
Expected: 출력 없음

- [ ] **Step 8: 남은 참조가 없는지 확인한다**

Run: `grep -n "lyr-del\|toggleLayerOverlay\|lyr-overlay\|deleteLayer\|api/layers/delete" cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html backend/router.py`
Expected: 출력 없음

- [ ] **Step 9: 커밋한다**

```bash
git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html
git commit -m "feat(panel): 포토샵식 레이어 목록 — 눈 토글·제거·복구·벡터화 버튼"
```

---

### Task 6: 합성 미리보기

**Files:**
- Modify: `cep/com.autokairos.pd/js/storyboard.js` (`_previewHTML` 및 `renderRow`의 `img-wrap`)
- Modify: `cep/com.autokairos.pd/index.html` (합성 CSS)

**Interfaces:**
- Consumes: `s._layers`, `s._layer_meta`(각 항목의 `hidden`·`removed`), 요소 위치는 사이드카 `bbox` — 패널에는 아직 없으므로 Task 2의 `_layer_meta`에 `bbox`를 더한다
- Produces: 함수 `renderComposite(s, dir)` — 레이어가 2장 이상이면 합성 HTML, 아니면 빈 문자열

**배경:** 지금 씬 셀에는 `_previewHTML(s, dir)`가 만든 스토리보드 이미지가 뜬다. 눈을 꺼도 그림이 그대로면 토글이 무의미하다.

`bbox`는 배경판 픽셀 좌표 `[l, t, r, b]`다. 배경판 폭·높이를 기준으로 백분율로 환산해 CSS 절대배치한다. 배경판 실제 크기는 브라우저가 이미지를 읽어야 알 수 있으므로 `bbox` 대신 **배경판 자체를 `width:100%`로 깔고, 요소는 배경판 크기를 모르는 채로도 배치할 수 있게 백분율을 백엔드가 계산해 준다.**

- [ ] **Step 1: `_layer_meta`에 백분율 배치를 더한다**

`backend/scenes.py`의 `_layer_meta` 헬퍼를 고친다. 배경판 PNG 크기를 읽어 각 요소의 `bbox`를 백분율로 바꾼다.

`_layer_meta` 함수 본문에서 `specs = ...` 다음에 배경 크기를 구한다.

```python
    plate = None
    for p in lay_dir.glob(f"*{sid}*bg*.png"):
        try:
            from PIL import Image
            with Image.open(p) as im:
                plate = (im.width, im.height)
        except Exception:
            plate = None
        break
```

그리고 `out[stem] = {...}` 딕셔너리에 `box` 키를 더한다.

```python
            "box": _box_pct(sp.get("bbox"), plate) if not is_bg else None,
```

같은 파일에 헬퍼를 추가한다.

```python
def _box_pct(bbox, plate):
    """bbox(배경판 픽셀) → {left, top, width} 백분율. 패널 합성 미리보기용.
    bbox나 배경판 크기가 없으면 None — 패널이 풀프레임으로 겹친다."""
    if not bbox or len(bbox) != 4 or not plate or not plate[0] or not plate[1]:
        return None
    try:
        l, t, r, b = [float(v) for v in bbox]
    except (TypeError, ValueError):
        return None
    if r - l <= 0 or b - t <= 0:
        return None
    pw, ph = plate
    return {"left": l / pw * 100, "top": t / ph * 100, "width": (r - l) / pw * 100}
```

- [ ] **Step 2: `_layer_meta` 테스트를 보강한다**

`tests/test_layer_state_api.py`의 `test_scene_layer_meta` 다음에 붙인다.

```python
def test_layer_meta_box_percent(tmp_path):
    """bbox가 배경판 크기 기준 백분율로 변환된다 — 패널 합성 미리보기용."""
    from PIL import Image
    from backend import scenes
    proj = _project(tmp_path)
    Image.new("RGBA", (1000, 500)).save(proj / "layers" / f"{SID}__bg.png")
    Image.new("RGBA", (200, 100)).save(proj / "layers" / f"{SID}__0_car.png")
    specs = [{"layer": f"{SID}__0_car", "index": 0, "name": "차", "name_en": "car",
              "location": "", "kind": "object", "intent": "", "z": 1,
              "bbox": [100, 50, 300, 150]}]
    (proj / "layers" / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    meta = scenes.load_scenes(proj)["scenes"][0]["_layer_meta"]
    box = meta[f"{SID}__0_car"]["box"]
    assert box["left"] == pytest.approx(10.0)
    assert box["top"] == pytest.approx(10.0)
    assert box["width"] == pytest.approx(20.0)
    assert meta[f"{SID}__bg"]["box"] is None


def test_layer_meta_box_none_without_bbox(tmp_path):
    from backend import scenes
    proj = _project(tmp_path)
    meta = scenes.load_scenes(proj)["scenes"][0]["_layer_meta"]
    assert meta[f"{SID}__0_car"]["box"] is None
```

파일 맨 위에 `import pytest`를 더한다.

- [ ] **Step 3: 테스트를 돌린다**

Run: `python -m pytest tests/test_layer_state_api.py -v`
Expected: PASS (8건)

- [ ] **Step 4: 합성 CSS를 넣는다**

`cep/com.autokairos.pd/index.html`의 `.col-img .img-wrap { position:relative; }` 다음에 넣는다.

```css
    .col-img .comp { position:relative; width:100%; line-height:0; }
    .col-img .comp img.comp-bg { width:100%; height:auto; display:block; }
    .col-img .comp img.comp-el { position:absolute; }
    .col-img .comp img.comp-el.full { top:0; left:0; width:100%; }
```

- [ ] **Step 5: 합성 렌더 함수를 추가한다**

`storyboard.js`의 `renderLayerList` 다음에 넣는다.

```javascript
/* 레이어 합성 미리보기 — 배경판을 깔고 요소를 bbox 백분율로 얹는다.
   눈을 끈 레이어는 그리지 않는다. 백엔드 호출 없이 이미 받은 PNG만 쓴다. */
function renderComposite(s, dir) {
  var meta = s._layer_meta || {};
  var rels = (s._layers || []).slice();
  if (rels.length < 2) return "";                 // 배경 + 요소가 있어야 합성이다
  rels.sort(function (a, b) {
    var ma = meta[_lyrStem(a)] || {}, mb = meta[_lyrStem(b)] || {};
    if ((ma.kind === "bg") !== (mb.kind === "bg")) return ma.kind === "bg" ? -1 : 1;
    var za = (ma.z == null) ? 9999 : ma.z, zb = (mb.z == null) ? 9999 : mb.z;
    return za - zb;
  });
  var bgRel = null, html = "";
  for (var i = 0; i < rels.length; i++) {
    var stem = _lyrStem(rels[i]);
    var m = meta[stem] || {};
    if (m.removed || m.hidden) continue;
    var src = 'file://' + dir + '/' + rels[i];
    if (m.kind === "bg" && !bgRel) {
      bgRel = src;
      continue;
    }
    if (m.box) {
      html += '<img class="comp-el" src="' + src + '"'
            + ' style="left:' + m.box.left + '%;top:' + m.box.top + '%;width:'
            + m.box.width + '%">';
    } else {
      html += '<img class="comp-el full" src="' + src + '">';   // bbox 없는 레거시 풀프레임
    }
  }
  if (!bgRel) {
    // 배경을 껐거나 없다 — 씬 이미지를 바탕으로 쓴다(요소 위치 기준이 같다)
    if (!s._image) return "";
    bgRel = 'file://' + dir + '/' + s._image;
  }
  return '<div class="comp"><img class="comp-bg" src="' + bgRel + '">' + html + '</div>';
}
```

- [ ] **Step 6: `renderRow`가 합성을 쓰게 한다**

`renderRow` 안의 `var media = _previewHTML(s, dir);` 를 아래로 바꾼다.

```javascript
  // 레이어가 있으면 합성 미리보기(눈 토글이 즉시 보인다), 없으면 기존 컴프 미리보기.
  var comp = renderComposite(s, dir);
  var media = comp || _previewHTML(s, dir);
```

- [ ] **Step 7: 문법과 ES5를 확인한다**

Run: `node --check cep/com.autokairos.pd/js/storyboard.js && grep -nE "=>|\blet\b|\bconst\b|\`" cep/com.autokairos.pd/js/storyboard.js`
Expected: 둘 다 출력 없음

- [ ] **Step 8: 전체 테스트를 돌린다**

Run: `python -m pytest tests/ -q`
Expected: 실패 없음

- [ ] **Step 9: 커밋한다**

```bash
git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html backend/scenes.py tests/test_layer_state_api.py
git commit -m "feat(panel): 레이어 합성 미리보기 — 눈 토글이 그림에 바로 보이게"
```

---

## 사람이 확인해야 하는 것

자동 검증이 되지 않는다. 구현이 끝난 뒤 테스터 PC에서 봐야 한다.

1. **AE의 SVG 임포트.** 이 맥에는 After Effects가 설치돼 있지 않다. 벡터 레이어를 얹은 컴프에서 그러데이션이 제대로 렌더되는지, 200%로 키웠을 때 실제로 안 깨지는지 확인해야 한다.
2. **합성 미리보기의 시각적 정확성.** `bbox` 백분율 배치가 원본 씬과 일치하는지.
3. **`RECRAFT_API_KEY` 배치.** `env.get_key`는 `AUTO_KAIROS_ENV` 환경변수가 가리키는 파일, 없으면 `LocalProjects/auto_kairos_v3/.env`를 읽는다. 현재 Recraft 키는 `kairos-ai/.env`에만 있어 **그대로는 잡히지 않는다.** `auto_kairos_v3/.env`에 `RECRAFT_API_KEY`를 추가하거나 환경변수로 넣어야 한다.
