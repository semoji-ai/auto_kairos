# P10 — 하드닝 B: _esc 적용 + 행 단위 재렌더 + jsx JSON.parse + 경로 하드코딩 제거 Implementation Plan

**Goal:** 감사 3순위 — ① main.js 동적 HTML에 `_esc` 적용(따옴표 깨짐 방지), ② 시트 **행 단위 재렌더**(`refreshRow`) — 전체 loadSheet로 인한 포커스 손실/스크롤 점프 해소, ③ jsx `eval` → **json2 폴리필 + JSON.parse**, ④ main.js **경로 하드코딩 제거**(`/health`에 root 포함).

**테스트:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`. JS: node 문법.

**현재 사실(확인됨):**
- `_esc`는 storyboard.js 정의(전역) — main.js에서도 런타임 호출 가능(로드: main→…→storyboard, 호출은 DOMContentLoaded 이후라 안전).
- main.js 비이스케이프 삽입: `loadProjects`(p.title/p.status → proj-item + data-label), `showCharacters`(nm → data-name/title), `showGallery`(n → title), `showStoryboard`/`showLayers`(n → title), `renderScenes`(s.title/s.narration).
- `renderScenes`의 scenes.json **절대경로 하드코딩**: `/Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/projects/{pid}/scenes.json` (evalScript로 AE에서 읽음 — 사실 백엔드 `/api/scenes`로 대체 가능). `MANIFEST` 상수도 잔존(미사용에 가까움 — buildComp는 API 사용).
- `/health` 응답: `{backend_status, codex_status, version}` — root 없음. app.py의 `CTX["root"]`가 프로젝트 루트.
- jsx: `eval("(" + raw + ")")`. ExtendScript에 native JSON 없음. `readLocal`(main.js)로 jsx 파일 문자열 로드 후 evalScript(jsx+call) — **json2.jsx를 앞에 이어붙이면 됨**.
- 시트 갱신 호출부: `genTts`·`splitLayers` 폴링 완료(loadSheet), `dropOnScene`/`unlinkScene`/`genSceneImage` 완료(loadSheet). sceneOp(구조 변경)는 전체 재렌더가 맞음(행 수 변동) — 유지.

---

## Task 1: /health에 root + main.js 경로 하드코딩 제거

**Files:** Modify `backend/router.py`, `cep/com.autokairos.pd/js/main.js`; Test `tests/test_router.py`, `tests/test_panel_structure.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`의 `test_health`에 `assert "root" in body` 추가(또는 새 테스트):

```python
def test_health_includes_root(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/health", {}, None, ctx)
    assert code == 200 and body["root"] == str(tmp_path)
```

- [ ] **Step 2: 구현** — router `/health` 응답에 `"root": str(root)` 추가. main.js:
  - 전역 `var PROJECTS_ROOT = "";` 추가, `checkBackend` 성공 시 `PROJECTS_ROOT = j.root || "";`.
  - `renderScenes`: 하드코딩 경로 → 백엔드 API로 교체(AE 파일 읽기 불필요):

```javascript
function renderScenes() {
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (doc) {
      $("scenes").innerHTML = (doc.scenes || []).map(function (s) {
        return "<div>#" + s.sceneNumber + " <b>" + _esc(s.title || "") + "</b> — " +
          _esc((s.narration || "").slice(0, 40)) + "...</div>";
      }).join("") || "(씬 없음)";
    })
    .catch(function (e) { $("scenes").textContent = "오류: " + e; });
}
```

  - `MANIFEST` 상수 제거(참조 없으면).
- [ ] **Step 3: 구조 테스트** — `test_panel_structure.py`:

```python
def test_no_hardcoded_machine_paths_in_panel():
    main = MAIN.read_text(encoding="utf-8")
    assert "/Users/jleavens_macmini" not in main
```

- [ ] **Step 4: 통과 + 커밋** — `git commit -m "fix(panel): 경로 하드코딩 제거 — /health root + renderScenes API화"`

---

## Task 2: main.js `_esc` 적용

**Files:** Modify `cep/com.autokairos.pd/js/main.js`; Test `tests/test_panel_structure.py`

- [ ] **Step 1: 적용 지점** — `loadProjects`(title/status/data-label), `showCharacters`(nm), `showGallery`/`showStoryboard`/`showLayers`(파일명 title). 모두 `_esc(...)` 감싸기. 단 `data-pid`/`data-name`은 클릭 시 속성으로 되읽으므로, **이스케이프된 값이 그대로 사용돼도 안전한지** 확인: pid는 uuid8(안전), 캐릭터 nm은 사용자 입력 → `data-name`에 `_esc(nm)` 넣으면 SELECTED_CHARACTER가 이스케이프 문자열이 됨 → **속성엔 encodeURIComponent, 읽을 때 decodeURIComponent** 사용(텍스트 표시만 _esc).
- [ ] **Step 2: 구조 테스트**:

```python
def test_main_js_escapes_dynamic_html():
    main = MAIN.read_text(encoding="utf-8")
    assert "_esc(p.title" in main            # 프로젝트 제목 이스케이프
    assert "_esc(" in main.split("function showCharacters")[1].split("function ")[1]
```

- [ ] **Step 3: node 문법 + 통과 + 커밋** — `git commit -m "fix(panel): main.js 동적 HTML _esc 적용(따옴표/태그 깨짐 방지)"`

---

## Task 3: 행 단위 재렌더 refreshRow

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`; Test `tests/test_panel_structure.py`

- [ ] **Step 1: 구현** — storyboard.js에 추가:

```javascript
/* 단일 씬 행만 갱신 — 전체 loadSheet의 포커스 손실/스크롤 점프 방지.
   행 수가 변하는 구조 편집(add/del/split/merge)은 loadSheet 사용. */
function refreshRow(n) {
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var s = (j.scenes || []).filter(function (x) { return x.sceneNumber === parseInt(n, 10); })[0];
      var old = $("sheet").querySelector('.sheet-row[data-scene="' + n + '"]');
      if (!s || !old) { loadSheet(); return; }            // 못 찾으면 전체 갱신 폴백
      NAR_ORIG[s.sceneNumber] = s.narration || "";
      var tmp = document.createElement("div");
      tmp.innerHTML = renderRow(s, j.dir || "");
      var fresh = tmp.firstChild;
      old.parentNode.replaceChild(fresh, old);
      bindRows();                                          // 재바인딩(전 행 — 단순·안전)
      var ta = fresh.querySelector("textarea.nar");
      if (ta) _autosize(ta);
    })
    .catch(function () { loadSheet(); });
}
```

- [ ] **Step 2: 호출부 전환** — 단일 씬 작업 완료 시 `loadSheet()` → `refreshRow(n)`: `genTts` 완료, `genSceneImage` 완료, `dropOnScene` 완료, `unlinkScene` 완료, `splitLayers` 폴링 완료. (sceneOp·decompose는 loadSheet 유지.)
- [ ] **Step 3: 구조 테스트**:

```python
def test_refresh_row_single_scene():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function refreshRow" in js
    # 단일 씬 작업(genTts)은 refreshRow 사용
    assert "refreshRow" in js.split("function genTts")[1].split("function ")[1]
```

- [ ] **Step 4: node 문법 + 통과 + 커밋** — `git commit -m "feat(panel): refreshRow 행 단위 재렌더 — 포커스/스크롤 보존"`

---

## Task 4: jsx JSON.parse(json2 폴리필)

**Files:** Create `cep/com.autokairos.pd/jsx/json2.jsx`; Modify `jsx/build_scene.jsx`, `js/main.js`; Test `tests/test_panel_structure.py`

- [ ] **Step 1: json2.jsx** — Douglas Crockford json2 공개 도메인 구현의 **JSON.parse 부분만** 포함한 경량판(전역 JSON 객체 보장: `if (typeof JSON !== "object") { JSON = {}; }` + parse 구현 — eval 기반 검증 파서(json2 표준: 문자 검증 후 eval)이면 충분. ExtendScript 호환 ES3 문법만).
- [ ] **Step 2: build_scene.jsx** — `var m = eval("(" + raw + ")");` →

```javascript
        var m = (typeof JSON === "object" && JSON.parse) ? JSON.parse(raw) : eval("(" + raw + ")");
```

- [ ] **Step 3: main.js** — `buildComp`/`_assemble`의 jsx 로드를 json2 선행 결합으로:

```javascript
      var jsx;
      try { jsx = readLocal("./jsx/json2.jsx") + "\n" + readLocal("./jsx/build_scene.jsx"); }
      catch (e) { setS("jsx 로드 실패: " + e); return; }
```

- [ ] **Step 4: 구조 테스트**:

```python
def test_jsx_uses_json_parse():
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "JSON.parse" in jsx
    assert (PANEL / "jsx" / "json2.jsx").exists()
    main = MAIN.read_text(encoding="utf-8")
    assert "json2.jsx" in main
```

- [ ] **Step 5: 통과 + 커밋** — `git commit -m "fix(jsx): json2 폴리필 + JSON.parse — 나레이션 특수문자로 eval 깨짐 방지"`

---

## Task 5: 통합 검증

- [ ] 전체 테스트 멱등 2회 + git 클린 + JS 7파일 node 문법(jsx는 문자열 검사만).
- [ ] 백엔드 재시작(8765) + `/health`에 root 포함 확인.

---

## Self-Review

- **이스케이프 전략**: 표시 텍스트=_esc, 되읽는 속성(data-name)=encodeURIComponent 왕복 — 이스케이프 문자열 오염 방지.
- **refreshRow 폴백**: 행/씬 못 찾으면 loadSheet — 구조 변경 직후 안전.
- **bindRows 전체 재바인딩**: 중복 리스너 우려 — 기존 노드 교체(replaceChild)라 옛 행 리스너는 GC, 새 행만 바인딩 필요하지만 bindRows는 전 행 대상 → 기존 행에 리스너 중복 추가됨. **수정**: bindRows 호출 대신 새 행만 바인딩하는 `_bindRow(fresh)` 헬퍼로 분리하거나, bindRows를 멱등(기존 리스너 중복 무해 — 같은 함수 재등록은 중복 실행됨!)으로 두지 말 것. → 구현 시 `bindRows()`를 행 스코프 파라미터를 받게 리팩터(`bindRows(scope)` — scope 기본 $("sheet"), refreshRow는 fresh만 전달). 계획 코드의 `bindRows()`를 `bindRows(fresh)`로 작성할 것.
- **json2**: 표준 검증 후 eval 방식 — 외부 의존 없음, ES3 호환.
- **한계(정직)**: refreshRow도 fetch 전체 scenes — 단일 씬 API는 과설계라 보류. 중복 리스너는 scope 바인딩으로 회피.
