# SB2 — 이미지 생성 모달(캐릭터/배경/소품/씬) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 우측 도구상자 `[+ 이미지 생성]` 버튼으로 카테고리식 이미지 생성 모달을 연다 — 캐릭터/배경/소품/씬. 카테고리별 폼으로 기존(캐릭터·씬) + 신규(배경·소품) 생성 엔드포인트에 연결.

**Architecture:** 백엔드: 배경/소품용 `POST /api/assets/generate`(images/에 생성→갤러리 소스로 노출), `/api/scenes/image`에 prompt 오버라이드 옵션. 캐릭터=기존 `/api/characters/generate`, 씬=기존 `/api/scenes/image`. 검증된 규칙(scene-image/character-sheet) 그대로 — 배경/소품은 무캐릭터 분기(generate_one character_ref=None → 베이스만, 인물 금지). 패널: 모달 마크업 + `genmodal.js`(카테고리 분기·제출 라우팅·완료 후 갱신).

**Tech Stack:** stdlib Python(uuid), pytest, vanilla JS(CEP), node 문법.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**현재 사실:** `imagegen.generate_one(proj_dir, rel_out, prompt, *, subdir=, character_ref=None, on_line=)` — character_ref 없으면 무캐릭터 분기(베이스 첨부, 인물 금지). `/api/characters/generate {project_id,name,looks}`. `/api/scenes/image {project_id,sceneNumber,character}` 생성→imageRef 링크. btnOpenGenModal 존재(미배선).

---

## File Structure

- **Modify** `backend/router.py` — `POST /api/assets/generate`(배경/소품) + `/api/scenes/image`에 prompt 옵션.
- **Test** `tests/test_router.py`.
- **Modify** `cep/com.autokairos.pd/index.html` — 모달 마크업 + CSS + genmodal.js 로드.
- **Create** `cep/com.autokairos.pd/js/genmodal.js` — 모달 로직.
- **Modify** `tests/test_panel_structure.py` — 모달 ID 검증.

---

## Task 1: /api/assets/generate + /api/scenes/image prompt 옵션

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

먼저 `router.py` 상단 import와 `/api/scenes/image` 블록을 Read 한다.

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:

```python
def test_assets_generate_background(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen.update(rel_out=rel_out, subdir=subdir, prompt=image_prompt, character_ref=character_ref)
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "background", "prompt": "작업실 배경"}, ctx)
    assert code == 200 and body["result"]["status"] == "completed"
    assert seen["rel_out"].startswith("background_") and seen["subdir"] == "images"
    assert seen["character_ref"] is None        # 무캐릭터 분기


def test_assets_generate_requires_prompt(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "prop", "prompt": ""}, ctx)
    assert code == 400


def test_assets_generate_bad_category(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/assets/generate", {},
                                {"project_id": "p", "category": "scene", "prompt": "x"}, ctx)
    assert code == 400        # background/prop만 허용(scene/character는 전용 엔드포인트)


def test_scenes_image_prompt_override(tmp_path, monkeypatch):
    import backend.router as r
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "scenes.json").write_text(
        '{"scenes":[{"sceneNumber":1,"sceneId":"sx","image_prompt":"기본"}]}', encoding="utf-8")
    seen = {}

    def fake_one(proj_dir, rel_out, image_prompt, *, subdir="images", character_ref=None, **kw):
        seen["prompt"] = image_prompt
        out = proj_dir / subdir / rel_out
        out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(b"\x89PNG")
        return {"status": "completed", "path": str(out)}

    monkeypatch.setattr(r.imagegen, "generate_one", fake_one)
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/scenes/image", {},
                                {"project_id": "p", "sceneNumber": 1, "prompt": "오버라이드 프롬프트"}, ctx)
    assert code == 200 and seen["prompt"] == "오버라이드 프롬프트"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -q` → 새 4개 FAIL.

- [ ] **Step 3: 구현** —

(a) `router.py` 상단 import에 `uuid` 추가: `import shutil` 옆/아래에 `import uuid`.

(b) `/api/scenes/image` 블록에서 이미지 프롬프트를 오버라이드 가능하게. 현재 generate_one 호출의 prompt 인자

```python
            scene.get("image_prompt", "") or scene.get("visual_summary", ""),
```

를

```python
            (b.get("prompt") or "").strip() or scene.get("image_prompt", "") or scene.get("visual_summary", ""),
```

로 교체.

(c) `/api/scenes/image` 블록 다음에 assets 엔드포인트 추가:

```python
    if method == "POST" and p == "/api/assets/generate":
        b = body or {}
        proj_dir = root / b.get("project_id", "")
        if not proj_dir.is_dir():
            return 404, {"error": "프로젝트 없음"}
        cat = (b.get("category") or "").strip()
        prompt = (b.get("prompt") or "").strip()
        if cat not in ("background", "prop"):
            return 400, {"error": "category는 background 또는 prop"}
        if not prompt:
            return 400, {"error": "prompt 필요"}
        jobs = ctx["jobs"]
        jid = jobs.create("asset", b.get("project_id", ""))
        name = f"{cat}_{uuid.uuid4().hex[:6]}.png"
        res = imagegen.generate_one(
            proj_dir, name, prompt, subdir="images",
            on_line=lambda ln: jobs.append_log(jid, ln))
        jobs.set_status(jid, "completed" if res.get("status") == "completed" else "failed",
                        artifact_paths=[str(proj_dir / "images")])
        return 200, {"job_id": jid, "result": res}
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/assets/generate(배경·소품→images, 무캐릭터 분기) + /api/scenes/image prompt 오버라이드"
```

---

## Task 2: 패널 — 이미지 생성 모달 마크업 + CSS

**Files:** Modify `cep/com.autokairos.pd/index.html`; Modify `tests/test_panel_structure.py`

먼저 `index.html`의 `</body>` 직전과 `<style>` 끝을 Read 한다.

- [ ] **Step 1: 모달 마크업 삽입** — `<div id="view-detail">` 닫힘 다음(즉 `</div>`로 view-detail 끝난 직후, `<script>` 태그들 앞)에 추가:

```html
  <!-- 이미지 생성 모달 -->
  <div id="genModal" hidden>
    <div class="gen-box">
      <div class="gen-head">이미지 생성 <button id="genClose" class="mini">✕</button></div>
      <div class="label">카테고리</div>
      <select id="genCategory">
        <option value="character">캐릭터</option>
        <option value="background">배경</option>
        <option value="prop">소품</option>
        <option value="scene">씬</option>
      </select>

      <div id="genFieldName" class="gen-field">
        <div class="label">이름</div>
        <input id="genName" type="text" placeholder="예: 지오 / 작업실 배경 / 렌치">
      </div>

      <div id="genFieldScene" class="gen-field" hidden>
        <div class="label">씬 선택</div>
        <select id="genScene"></select>
        <div class="label">기준 캐릭터(선택)</div>
        <select id="genSceneChar"><option value="">(없음)</option></select>
      </div>

      <div class="label" id="genPromptLabel">설명 / 프롬프트</div>
      <textarea id="genPrompt" rows="3" placeholder="헤어·의상(캐릭터) / 장면 설명(배경·소품) / 씬은 비우면 원고 기반"></textarea>

      <div class="gen-actions">
        <button id="genSubmit">생성</button>
        <button id="genCancel" class="alt">취소</button>
      </div>
      <div class="box" id="genStatus" style="min-height:16px">—</div>
    </div>
  </div>
```

- [ ] **Step 2: 모달 CSS** — `<style>` 끝(`@media (min-width: 760px)` 블록 다음, `</style>` 앞)에 추가:

```css
    /* 이미지 생성 모달 */
    #genModal { position:fixed; inset:0; background:rgba(0,0,0,0.6); z-index:100;
      display:flex; align-items:center; justify-content:center; }
    #genModal[hidden] { display:none; }
    #genModal .gen-box { width:min(420px,92vw); max-height:88vh; overflow-y:auto;
      background:#23262b; border:1px solid #33363c; border-radius:10px; padding:16px; }
    #genModal .gen-head { display:flex; justify-content:space-between; align-items:center;
      font-size:14px; font-weight:600; margin-bottom:8px; }
    #genModal select, #genModal input, #genModal textarea { width:100%; box-sizing:border-box;
      padding:7px; margin:3px 0; background:#1b1d21; color:#e6e6e6; border:1px solid #33363c; border-radius:5px; }
    #genModal .gen-actions { display:flex; gap:8px; margin-top:10px; }
    #genModal .gen-actions button { flex:1; }
```

- [ ] **Step 3: genmodal.js 스크립트 추가** — `<script src="js/gallery.js"></script>` 다음에:

```html
  <script src="js/genmodal.js"></script>
```

- [ ] **Step 4: 구조 테스트** — `tests/test_panel_structure.py` 끝에:

```python
def test_genmodal_present():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="genModal"', 'id="genCategory"', 'id="genPrompt"', 'id="genSubmit"',
               'id="genScene"', 'src="js/genmodal.js"']:
        assert el in html, el
```

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 이미지 생성 모달 마크업(카테고리 캐릭터/배경/소품/씬)+CSS"
```

---

## Task 3: genmodal.js — 카테고리 분기 + 제출 라우팅

**Files:** Create `cep/com.autokairos.pd/js/genmodal.js`

- [ ] **Step 1: genmodal.js 작성**

```javascript
/* 이미지 생성 모달 — 카테고리별 폼 + 엔드포인트 라우팅. 전역 $/BACKEND/SELECTED_PROJECT.
   완료 후 loadGallery/loadSheet 갱신(있으면). */

function openGenModal() {
  if (!SELECTED_PROJECT) { alert("프로젝트를 먼저 선택하세요."); return; }
  $("genStatus").textContent = "—";
  $("genModal").hidden = false;
  _genOnCategory();
}

function closeGenModal() { $("genModal").hidden = true; }

function _genOnCategory() {
  var cat = $("genCategory").value;
  $("genFieldName").hidden = (cat === "scene");
  $("genFieldScene").hidden = (cat !== "scene");
  $("genPromptLabel").textContent =
    cat === "character" ? "헤어·의상" :
    cat === "scene" ? "프롬프트(비우면 원고 기반)" : "장면 설명 / 프롬프트";
  if (cat === "scene") _genLoadScenes();
}

function _genLoadScenes() {
  fetch(BACKEND + "/api/scenes?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var opts = (j.scenes || []).map(function (s) {
        return '<option value="' + s.sceneNumber + '">#' + s.sceneNumber + " " + (s.title || "") + '</option>';
      }).join("");
      $("genScene").innerHTML = opts || '<option value="">(씬 없음)</option>';
    });
  // 기준 캐릭터 옵션
  fetch(BACKEND + "/api/characters/list?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var opts = '<option value="">(없음)</option>' + (j.images || []).map(function (n) {
        var nm = n.replace(/^char_/, "").replace(/\.png$/, "");
        return '<option value="' + nm + '">' + nm + '</option>';
      }).join("");
      $("genSceneChar").innerHTML = opts;
    });
}

function submitGen() {
  var cat = $("genCategory").value;
  var prompt = ($("genPrompt").value || "").trim();
  var name = ($("genName").value || "").trim();
  $("genStatus").textContent = "생성 중... (codex, 수십 초)";
  var url, payload;
  if (cat === "character") {
    if (!name || !prompt) { $("genStatus").textContent = "이름과 헤어·의상을 입력하세요."; return; }
    url = "/api/characters/generate"; payload = { project_id: SELECTED_PROJECT, name: name, looks: prompt };
  } else if (cat === "scene") {
    url = "/api/scenes/image";
    payload = { project_id: SELECTED_PROJECT, sceneNumber: parseInt($("genScene").value, 10),
                character: $("genSceneChar").value || "", prompt: prompt };
  } else { // background / prop
    if (!prompt) { $("genStatus").textContent = "장면 설명을 입력하세요."; return; }
    url = "/api/assets/generate"; payload = { project_id: SELECTED_PROJECT, category: cat, name: name, prompt: prompt };
  }
  fetch(BACKEND + url, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      var res = j.result || j.character || j;
      var ok = res && (res.status === "completed" || res.ok || j.character);
      $("genStatus").textContent = ok ? "생성 완료 ✓" : ("실패: " + JSON.stringify(j));
      if (ok) {
        if (typeof loadGallery === "function") loadGallery();
        if (typeof loadSheet === "function") loadSheet();
      }
    })
    .catch(function (e) { $("genStatus").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  $("btnOpenGenModal").addEventListener("click", openGenModal);
  $("genClose").addEventListener("click", closeGenModal);
  $("genCancel").addEventListener("click", closeGenModal);
  $("genCategory").addEventListener("change", _genOnCategory);
  $("genSubmit").addEventListener("click", submitGen);
});
```

- [ ] **Step 2: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/genmodal.js','utf8'))" && echo OK`

- [ ] **Step 3: 커밋**

```bash
git add cep/com.autokairos.pd/js/genmodal.js
git commit -m "feat(panel): genmodal.js — 카테고리(캐릭터/배경/소품/씬) 생성 모달 + 엔드포인트 라우팅"
```

---

## Task 4: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — `for f in main nav planning storyboard gallery genmodal; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK`
- [ ] **Step 3: (사용자) AE 검증** — 도구상자 [+ 이미지 생성] → 모달 → 카테고리 전환 시 폼 변화(캐릭터=이름+헤어의상 / 배경·소품=설명 / 씬=씬·캐릭터 선택+프롬프트) → 생성 → 완료 후 갤러리/시트 갱신. (백엔드 재시작 필요 — assets 엔드포인트 신규.)

---

## Self-Review

- **스펙 커버리지(§B 이미지 생성 모달 4 카테고리 — kairos_ai식)**: 모달 마크업(T2)+분기 로직(T3)+배경·소품 엔드포인트·씬 prompt(T1). 캐릭터→/characters/generate, 씬→/scenes/image(prompt·character), 배경·소품→/assets/generate. 검증된 규칙(generate_one 무캐릭터 분기=베이스 첨부·인물 금지) 그대로.
- **무삭제 준수**: assets는 images/에 고유 이름(uuid) 생성(generate_one versioned). 삭제 없음.
- **Placeholder 없음**: 전 코드 완전. btnOpenGenModal(SB1 미배선)을 여기서 배선.
- **타입/일관성**: assets→{result:{status}}, scenes/image→{result:{status}}, characters→{character:{status}}. submitGen이 status/ok/character 모두 처리. /api/scenes/image prompt 오버라이드는 기존 character/sceneNumber와 병존.
- **로드 순서**: main→nav→planning→storyboard→gallery→genmodal. 모달은 전역 함수 호출(loadGallery/loadSheet typeof 가드).
- **스코프**: SB3(호버 레이어 LLM 분석)는 비범위.
