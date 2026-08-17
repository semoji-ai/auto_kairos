# P3 — 스토리보드 프로덕션 시트 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 스토리보드 탭에 씬당 1행 프로덕션 시트를 구현한다 — 씬# · 미디어(씬 이미지) · 나레이션 인라인 편집 · 캐릭터 · 레이어 썸네일, 그리고 행별 씬 이미지 생성/재생성.

**Architecture:** 백엔드 `scenes.py`가 `scenes.json`을 읽어 각 씬에 미디어/레이어 경로(존재하는 것만, 최신 버전)를 부여하고 나레이션 수정을 저장. 라우터 `GET /api/scenes`, `POST /api/scenes/narration`, `POST /api/scenes/image`(단일 씬, 기존 imagegen 재사용). 패널 `storyboard.js`가 시트를 렌더. 씬 구조 편집(split/merge/add/delete)은 P5, 갤러리 패널은 P4 — 비범위.

**Tech Stack:** stdlib Python, pytest, vanilla JS(CEP), node 문법 체크.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**확정 사실(코드 기준):**
- scenes.json: `{version, project_id, topic, total_scenes, scenes:[{sceneNumber, section, title, narration, characters, visual_summary, image_prompt, duration_estimate_sec}]}`.
- 씬 이미지: `storyboard/sb_{n}.png`(재생성은 `imagegen.generate_one`이 `sb_{n}_v2.png` 등 버전 생성 — 무삭제).
- 레이어: `layers/bg_{n}.png`, `layers/char_{n}.png`.
- 단일 씬 이미지 생성은 `imagegen.generate_one(proj_dir, f"sb_{n}.png", image_prompt, subdir="storyboard", character_ref=...)` 재사용.

---

## File Structure

- **Create** `backend/scenes.py` — `load_scenes`(미디어/레이어 경로 enrich), `update_narration`.
- **Modify** `backend/router.py` — `GET /api/scenes`, `POST /api/scenes/narration`, `POST /api/scenes/image`.
- **Test** `tests/test_scenes.py`(신규), `tests/test_router.py`.
- **Create** `cep/com.autokairos.pd/js/storyboard.js` — 시트 렌더 + 나레이션 저장 + 행별 이미지 생성.
- **Modify** `cep/com.autokairos.pd/index.html` — 스토리보드 탭에 시트 영역(#sheet, #btnLoadSheet) 추가, storyboard.js 스크립트.
- **Modify** `cep/com.autokairos.pd/js/nav.js` — 스토리보드 탭 전환 시 시트 로드.
- **Modify** `tests/test_panel_structure.py` — 시트 ID 검증.

---

## Task 1: scenes.load_scenes (미디어/레이어 enrich)

**Files:** Create `backend/scenes.py`; Test `tests/test_scenes.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_scenes.py`:

```python
import json
from pathlib import Path
from backend import scenes


def _proj(tmp_path, scene_list):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(
        json.dumps({"project_id": "p", "scenes": scene_list}, ensure_ascii=False),
        encoding="utf-8")
    return d


def test_load_scenes_enriches_media_and_layers(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "title": "A", "narration": "가",
                          "image_prompt": "장면1"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_1.png").write_bytes(b"\x89PNG")
    (d / "layers").mkdir()
    (d / "layers" / "bg_1.png").write_bytes(b"\x89PNG")
    (d / "layers" / "char_1.png").write_bytes(b"\x89PNG")
    data = scenes.load_scenes(d)
    s = data["scenes"][0]
    assert s["_image"] == "storyboard/sb_1.png"
    assert s["_layers"] == ["layers/bg_1.png", "layers/char_1.png"]
    assert data["dir"] == str(d)


def test_load_scenes_picks_latest_image_version(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 2, "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    (sb / "sb_2.png").write_bytes(b"\x89PNG")
    (sb / "sb_2_v2.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "storyboard/sb_2_v2.png"   # 최신 버전


def test_load_scenes_no_media(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"}])
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] is None and s["_layers"] == []


def test_load_scenes_missing_file(tmp_path):
    assert scenes.load_scenes(tmp_path / "nope") == {"scenes": [], "dir": ""}
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_scenes.py -q` → FAIL(모듈 없음).

- [ ] **Step 3: 구현** — `backend/scenes.py`:

```python
"""scenes.json 조회/수정 — 미디어·레이어 경로 enrich, 나레이션 편집(무삭제)."""
from __future__ import annotations

import json
from pathlib import Path


def _path(proj_dir: Path) -> Path:
    return proj_dir / "scenes.json"


def _latest_image(sb_dir: Path, n) -> str | None:
    """storyboard/sb_{n}.png 및 버전(sb_{n}_v2.png …) 중 최신(이름 정렬 마지막)."""
    if not sb_dir.is_dir():
        return None
    cands = sorted(p.name for p in sb_dir.glob(f"sb_{n}.png"))
    cands += sorted(p.name for p in sb_dir.glob(f"sb_{n}_v*.png"))
    return f"storyboard/{cands[-1]}" if cands else None


def load_scenes(proj_dir: Path) -> dict:
    """scenes.json 로드 + 각 씬에 _image(최신 씬 이미지)·_layers 부여. dir=프로젝트 절대경로."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"scenes": [], "dir": ""}
    data = json.loads(fp.read_text(encoding="utf-8"))
    sb_dir, lay_dir = proj_dir / "storyboard", proj_dir / "layers"
    for s in data.get("scenes", []):
        n = s.get("sceneNumber")
        s["_image"] = _latest_image(sb_dir, n)
        s["_layers"] = [f"layers/{nm}" for nm in (f"bg_{n}.png", f"char_{n}.png")
                        if (lay_dir / nm).exists()]
    data["dir"] = str(proj_dir)
    return data


def update_narration(proj_dir: Path, scene_number: int, narration: str) -> dict:
    """씬 나레이션 수정 + narration_dirty=True 저장. {ok, sceneNumber} 또는 {error}."""
    fp = _path(proj_dir)
    if not fp.is_file():
        return {"error": "scenes.json 없음"}
    data = json.loads(fp.read_text(encoding="utf-8"))
    for s in data.get("scenes", []):
        if s.get("sceneNumber") == scene_number:
            s["narration"] = narration
            s["narration_dirty"] = True
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            return {"ok": True, "sceneNumber": scene_number}
    return {"error": f"scene {scene_number} 없음"}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_scenes.py -q` → PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/scenes.py tests/test_scenes.py
git commit -m "feat(backend): scenes.load_scenes(미디어·레이어 enrich)+update_narration(narration_dirty)"
```

---

## Task 2: scenes.update_narration 엣지 테스트

**Files:** Test `tests/test_scenes.py`

- [ ] **Step 1: 실패 테스트 추가**

```python
def test_update_narration_sets_dirty(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "narration": "옛", "image_prompt": "x"}])
    res = scenes.update_narration(d, 1, "새 나레이션")
    assert res == {"ok": True, "sceneNumber": 1}
    saved = json.loads((d / "scenes.json").read_text(encoding="utf-8"))
    assert saved["scenes"][0]["narration"] == "새 나레이션"
    assert saved["scenes"][0]["narration_dirty"] is True


def test_update_narration_unknown_scene(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"}])
    assert "error" in scenes.update_narration(d, 99, "x")
```

- [ ] **Step 2: 통과 확인** — `... -m pytest tests/test_scenes.py -q` → PASS(이미 구현됨).

- [ ] **Step 3: 커밋**

```bash
git add tests/test_scenes.py
git commit -m "test(backend): update_narration dirty/미존재 씬 케이스"
```

---

## Task 3: 라우터 — /api/scenes (GET) + narration + image (POST)

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:

```python
def test_scenes_get(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"project_id":"p","scenes":[{"sceneNumber":1,"title":"A","narration":"가","image_prompt":"장면1"}]}',
        encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/scenes", {"project_id": "p"}, None, ctx)
    assert code == 200
    assert body["scenes"][0]["sceneNumber"] == 1
    assert body["dir"] == str(proj)


def test_scenes_update_narration(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"narration":"옛","image_prompt":"x"}]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/narration", {},
                                {"project_id": "p", "sceneNumber": 1, "narration": "새"}, ctx)
    assert code == 200 and body["ok"] is True
    import json as _j
    assert _j.loads((proj / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]["narration"] == "새"


def test_scenes_image_single(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":3,"image_prompt":"전기차 공장"}]}', encoding="utf-8")
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen.update(rel_out=rel_out, subdir=subdir, prompt=image_prompt, character_ref=character_ref)
        return {"status": "completed", "path": str(proj_dir / subdir / rel_out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 3, "character": "지오"}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"
    assert seen["rel_out"] == "sb_3.png" and seen["subdir"] == "storyboard"
    assert seen["prompt"] == "전기차 공장"
    # 캐릭터 시트가 없으면 character_ref=None (파일 미존재)
    assert seen["character_ref"] is None


def test_scenes_image_unknown_scene(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text('{"scenes":[]}', encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 9}, ctx)
    assert code == 404
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -q` → 새 4개 FAIL.

- [ ] **Step 3: 구현** — `backend/router.py` 상단 import에 `scenes` 추가:

`from backend import projects, skills_cfg, sessions, pipeline, imagegen` 를
`from backend import projects, skills_cfg, sessions, pipeline, imagegen, scenes` 로 변경.

그리고 `/api/characters/list` 블록 다음(또는 `/api/storyboard/generate` 앞)에 추가:

```python
    if method == "GET" and p == "/api/scenes":
        pid = query.get("project_id", "")
        return 200, scenes.load_scenes(root / pid)

    if method == "POST" and p == "/api/scenes/narration":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        sn = b.get("sceneNumber")
        res = scenes.update_narration(proj_dir, sn, b.get("narration", ""))
        return (200, res) if res.get("ok") else (404, res)

    if method == "POST" and p == "/api/scenes/image":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        sn = b.get("sceneNumber")
        data = scenes.load_scenes(proj_dir)
        scene = next((s for s in data["scenes"] if s.get("sceneNumber") == sn), None)
        if not scene:
            return 404, {"error": f"scene {sn} 없음"}
        char = (b.get("character") or "").strip()
        character_ref = None
        if char:
            cref = proj_dir / "characters" / f"char_{char}.png"
            if cref.exists():
                character_ref = str(cref)
        jobs = ctx["jobs"]
        jid = jobs.create("scene-image", pid)
        res = imagegen.generate_one(
            proj_dir, f"sb_{sn}.png", scene.get("image_prompt", "") or scene.get("visual_summary", ""),
            subdir="storyboard", character_ref=character_ref,
            on_line=lambda ln: jobs.append_log(jid, ln))
        ok = res.get("status") == "completed"
        jobs.set_status(jid, "completed" if ok else "failed",
                        artifact_paths=[str(proj_dir / "storyboard")])
        return 200, {"job_id": jid, "result": res}
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/scenes GET + narration·image(단일 씬, character_ref) POST"
```

---

## Task 4: 패널 — 스토리보드 탭에 시트 영역

**Files:** Modify `cep/com.autokairos.pd/index.html`; Modify `tests/test_panel_structure.py`

먼저 `index.html`의 `<div id="tab-storyboard" ...>` 블록을 Read 한다.

- [ ] **Step 1: 씬 분해 박스(`#scenes`) 다음에 시트 영역 삽입** — `<div class="box" id="scenes">—</div>` 줄 바로 뒤에 추가:

```html
        <div class="label">프로덕션 시트</div>
        <button id="btnLoadSheet">시트 불러오기</button>
        <div id="sheet">—</div>
```

- [ ] **Step 2: storyboard.js 스크립트 태그 추가** — `<script src="js/planning.js"></script>` 줄 뒤에 추가:

```html
  <script src="js/storyboard.js"></script>
```

- [ ] **Step 3: 구조 테스트 추가** — `tests/test_panel_structure.py` 끝에:

```python
def test_storyboard_tab_has_sheet():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="sheet"' in html and 'id="btnLoadSheet"' in html
    assert 'src="js/storyboard.js"' in html


def test_storyboard_js_defines_loadSheet():
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "function loadSheet" in js
```

- [ ] **Step 4: 부분 확인** — `... -m pytest tests/test_panel_structure.py -q` → `test_storyboard_tab_has_sheet` PASS, `test_storyboard_js_defines_loadSheet`는 파일 미생성이라 FAIL(다음 태스크에서 통과).

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 스토리보드 탭에 프로덕션 시트 영역(#sheet)+storyboard.js 로드"
```

---

## Task 5: storyboard.js — 시트 렌더 + 나레이션 저장 + 행별 이미지 생성

**Files:** Create `cep/com.autokairos.pd/js/storyboard.js`

- [ ] **Step 1: storyboard.js 작성**

```javascript
/* 스토리보드 프로덕션 시트 — 씬당 1행. BACKEND/$/SELECTED_PROJECT/SELECTED_CHARACTER는 main.js 전역. */

function _esc(s) {
  return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function loadSheet() {
  if (!SELECTED_PROJECT) { $("sheet").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("sheet").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var dir = j.dir || "", list = j.scenes || [];
      if (!list.length) { $("sheet").textContent = "(씬 없음 — 씬 분해 먼저)"; return; }
      $("sheet").innerHTML = list.map(function (s) { return renderRow(s, dir); }).join("");
      bindRows();
    })
    .catch(function (e) { $("sheet").textContent = "오류: " + e; });
}

function renderRow(s, dir) {
  var n = s.sceneNumber;
  var media = s._image
    ? '<img src="file://' + dir + '/' + s._image + '" style="width:100%;border-radius:4px;">'
    : '<div style="color:#666;font-size:11px">(이미지 없음)</div>';
  var layers = (s._layers || []).map(function (lp) {
    return '<img src="file://' + dir + '/' + lp + '" style="width:38px;height:auto;margin:2px;border-radius:3px;" title="' + _esc(lp) + '">';
  }).join("");
  var chars = (s.characters || []).join(", ");
  return ''
    + '<div class="box" style="display:block" data-scene="' + n + '">'
    + '  <div style="color:#9aa0a6;font-size:11px">#' + n + " · " + _esc(s.title || "") + (chars ? " · 👤 " + _esc(chars) : "") + '</div>'
    + '  <div style="margin:4px 0">' + media + '</div>'
    + (layers ? '<div style="margin:2px 0">' + layers + '</div>' : '')
    + '  <textarea class="nar" data-scene="' + n + '" rows="2" style="width:100%;box-sizing:border-box;background:#23262b;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;padding:6px;">' + _esc(s.narration || "") + '</textarea>'
    + '  <div style="display:flex;gap:6px">'
    + '    <button class="sv-nar" data-scene="' + n + '" style="margin:4px 0">나레이션 저장</button>'
    + '    <button class="gen-img alt" data-scene="' + n + '" style="margin:4px 0">씬 이미지 생성</button>'
    + '  </div>'
    + '  <div class="row-status" data-scene="' + n + '" style="font-size:11px;color:#9aa0a6"></div>'
    + '</div>';
}

function bindRows() {
  var save = $("sheet").querySelectorAll("button.sv-nar");
  for (var i = 0; i < save.length; i++) {
    save[i].addEventListener("click", function () { saveNarration(this.getAttribute("data-scene")); });
  }
  var gen = $("sheet").querySelectorAll("button.gen-img");
  for (var k = 0; k < gen.length; k++) {
    gen[k].addEventListener("click", function () { genSceneImage(this.getAttribute("data-scene")); });
  }
}

function _rowStatus(n, msg) {
  var el = $("sheet").querySelector('.row-status[data-scene="' + n + '"]');
  if (el) el.textContent = msg;
}

function saveNarration(n) {
  var ta = $("sheet").querySelector('textarea.nar[data-scene="' + n + '"]');
  if (!ta) return;
  _rowStatus(n, "저장 중...");
  fetch(BACKEND + "/api/scenes/narration", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10), narration: ta.value }),
  }).then(function (r) { return r.json(); })
    .then(function (j) { _rowStatus(n, j.ok ? "저장됨 ✓" : ("실패: " + JSON.stringify(j))); })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}

function genSceneImage(n) {
  _rowStatus(n, "씬 이미지 생성 중... (codex, 수십 초)" + (SELECTED_CHARACTER ? " [" + SELECTED_CHARACTER + "]" : ""));
  fetch(BACKEND + "/api/scenes/image", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, sceneNumber: parseInt(n, 10),
                           character: SELECTED_CHARACTER || "" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      _rowStatus(n, (j.result && j.result.status === "completed") ? "생성 완료 ✓" : ("실패: " + JSON.stringify(j)));
      if (j.result && j.result.status === "completed") loadSheet();   // 썸네일 갱신
    })
    .catch(function (e) { _rowStatus(n, "오류: " + e); });
}
```

- [ ] **Step 2: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/storyboard.js','utf8'))" && echo OK` → `OK`

- [ ] **Step 3: 구조 테스트 통과** — `... -m pytest tests/test_panel_structure.py -q` → `test_storyboard_js_defines_loadSheet` PASS.

- [ ] **Step 4: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js
git commit -m "feat(panel): storyboard.js — 프로덕션 시트(미디어·레이어 썸네일·나레이션 편집·행별 씬 이미지 생성)"
```

---

## Task 6: nav.js — 스토리보드 탭 진입 시 시트 로드

**Files:** Modify `cep/com.autokairos.pd/js/nav.js`

- [ ] **Step 1: switchTab에 시트 로드 훅 추가** — `switchTab` 함수에서 버튼 active 토글 다음에 추가:

```javascript
  if (!planning && typeof loadSheet === "function") loadSheet();
```

(스토리보드 탭으로 전환할 때만 시트 로드. typeof 가드 — storyboard.js 미로드 방어.)

- [ ] **Step 2: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/nav.js','utf8'))" && echo OK` → `OK`

- [ ] **Step 3: 커밋**

```bash
git add cep/com.autokairos.pd/js/nav.js
git commit -m "feat(panel): 스토리보드 탭 전환 시 시트 자동 로드"
```

---

## Task 7: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — `for f in main nav planning storyboard; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK` → `ALL_OK`
- [ ] **Step 3: (사용자) AE 검증** — 프로젝트 입장 → 스토리보드 탭 → 시트 자동 로드(씬 행: 이미지 썸네일·레이어 썸네일·나레이션) → 나레이션 수정 후 [나레이션 저장] → [씬 이미지 생성](기준 캐릭터 선택 시 일관) → 썸네일 갱신.

---

## Self-Review

- **스펙 커버리지(§3.2 시트: 씬 행·미디어·나레이션 인라인 편집·씬 이미지 생성/재생성·레이어 썸네일)**: load_scenes(T1)+narration/image 엔드포인트(T3)+시트 렌더(T5)+탭 진입 로드(T6)로 충족. split/merge/add/delete(P5)·갤러리 패널(P4)·검색/TTS(P4/P6)는 비범위(스펙 P3 한정).
- **이미지 삭제 금지 준수**: 재생성은 `generate_one`의 버전 생성(무삭제), 시트는 최신 버전 표시(`_latest_image`).
- **Placeholder 없음**: 전 코드 완전. `_esc`로 나레이션/레이어 라벨 HTML 이스케이프(나레이션은 사용자 입력이라 필수).
- **타입/ID 일관성**: `load_scenes`→`{scenes:[{...,_image,_layers}], dir}`, `/api/scenes` 동일, storyboard.js가 `j.scenes`/`s._image`/`s._layers`/`j.dir` 사용 — 일치. `update_narration`→`{ok,sceneNumber}|{error}`, narration 엔드포인트가 ok면 200·아니면 404. `/api/scenes/image`가 `imagegen.generate_one(... subdir="storyboard", character_ref=...)` 호출 — 기존 시그니처(P-char 단계)와 일치. 기존 배치 `/api/storyboard/generate`·버튼은 무변경(공존).
- **로드 순서**: main→nav→planning→storyboard. loadSheet는 탭 전환/버튼 클릭 시 호출 → 안전.
