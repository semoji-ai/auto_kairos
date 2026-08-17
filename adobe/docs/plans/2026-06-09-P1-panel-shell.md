# P1 — 패널 셸(목록↔상세 + 탭 + 하단 채팅 + 반응형) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) 또는 superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** AE 패널을 "프로젝트 목록 뷰 ↔ 프로젝트 상세 뷰(기획/스토리보드 탭 + 하단 채팅 자리)"의 반응형 셸로 재구성한다. 기존 기능은 상세 뷰 탭으로 이전해 그대로 동작.

**Architecture:** 단일 `index.html`에 `#view-list` / `#view-detail` 두 섹션. 상세 뷰는 헤더(제목+나가기) + 태스크바(자리) + 탭바(기획/스토리보드) + 탭 콘텐츠 + 하단 채팅(자리). 뷰/탭 전환은 신규 `js/nav.js`(show/hide). 백엔드 변경 없음(기존 `/api/projects` 사용). 정적이라 빌드 불필요.

**Tech Stack:** CEP(HTML/CSS/vanilla JS), pytest(정적 구조 검증), node(JS 문법 검증).

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트에서.

**규칙:** 한쪽만 수정 금지 아님(패널은 단일 소스). 기존 버튼 ID 유지(main.js 바인딩 보존). P1은 셸만 — 챗/태스크/갤러리/파일뷰어 내용은 후속 Phase.

---

## File Structure

- **Modify** `cep/com.autokairos.pd/index.html` — `<style>`에 레이아웃/반응형 추가, `<body>`를 목록/상세 2뷰 + 탭 + 채팅 자리로 재구성. 기존 컨트롤을 탭 컨테이너로 이동.
- **Create** `cep/com.autokairos.pd/js/nav.js` — `enterProject/exitProject/switchTab` + 바인딩.
- **Modify** `cep/com.autokairos.pd/js/main.js` — `loadProjects` 카드 클릭 → `enterProject` 호출. (스크립트 로드는 index.html에서 main.js → nav.js 순.)
- **Create** `tests/test_panel_structure.py` — 패널 정적 구조 검증(필수 ID·뷰·탭·채팅·반응형 존재).

---

## Task 1: 패널 구조 검증 테스트 (실패부터)

**Files:** Create `tests/test_panel_structure.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
from pathlib import Path

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
HTML = PANEL / "index.html"
NAV = PANEL / "js" / "nav.js"
MAIN = PANEL / "js" / "main.js"


def test_index_has_two_views():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="view-list"' in html
    assert 'id="view-detail"' in html
    # 상세 뷰는 초기 숨김
    assert 'id="view-detail" hidden' in html or 'id="view-detail"  hidden' in html


def test_index_has_detail_header_and_back():
    html = HTML.read_text(encoding="utf-8")
    assert 'id="detailTitle"' in html
    assert 'id="btnBackToList"' in html


def test_index_has_tabs():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="btnTabPlanning"', 'id="btnTabStoryboard"',
               'id="tab-planning"', 'id="tab-storyboard"']:
        assert el in html, el


def test_index_has_chat_dock():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="chat-dock"', 'id="chatInput"', 'id="btnChatSend"']:
        assert el in html, el


def test_index_has_taskbar():
    assert 'id="task-bar"' in HTML.read_text(encoding="utf-8")


def test_index_has_responsive_media_query():
    assert "@media" in HTML.read_text(encoding="utf-8")


def test_existing_controls_present_in_detail():
    # 기존 버튼 ID 보존(바인딩 깨짐 방지)
    html = HTML.read_text(encoding="utf-8")
    for bid in ['id="btnManuscript"', 'id="btnDecompose"', 'id="btnGenCharacter"',
                'id="btnRefList"', 'id="btnGenStoryboard"', 'id="btnGenLayers"',
                'id="btnBuild"', 'id="btnCreate"', 'id="btnProjects"']:
        assert bid in html, bid


def test_nav_defines_functions():
    nav = NAV.read_text(encoding="utf-8")
    for fn in ["function enterProject", "function exitProject", "function switchTab"]:
        assert fn in nav, fn


def test_main_calls_enterProject():
    assert "enterProject(" in MAIN.read_text(encoding="utf-8")
```

- [ ] **Step 2: 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py -q`
Expected: FAIL (nav.js 없음 → FileNotFoundError, 그리고 id 미존재 assert 실패).

- [ ] **Step 3: 커밋(테스트만)**

```bash
git add tests/test_panel_structure.py
git commit -m "test(panel): P1 셸 구조 검증 테스트(실패 상태)"
```

---

## Task 2: index.html 재구성 (목록/상세 + 탭 + 채팅 + 반응형)

**Files:** Modify `cep/com.autokairos.pd/index.html`

먼저 현재 `index.html` 전체를 Read 한다(기존 컨트롤 마크업 보존하며 컨테이너로 옮기기 위함).

- [ ] **Step 1: `<style>` 블록 교체 — 레이아웃/반응형 추가**

기존 `<style>...</style>` 전체를 아래로 교체:

```html
  <style>
    body { font-family: -apple-system, sans-serif; background:#23262b; color:#e6e6e6;
           margin:0; padding:0; font-size:13px; }
    h1 { font-size:15px; margin:0 0 12px; }
    button { width:100%; padding:10px; margin:6px 0; border:0; border-radius:6px;
             background:#3a6df0; color:#fff; font-size:13px; cursor:pointer; }
    button.alt { background:#444; }
    button.tab { background:#2c2f36; color:#c5c8cc; border-radius:0; margin:0; }
    button.tab.active { background:#3a6df0; color:#fff; }
    .box { background:#1b1d21; border:1px solid #33363c; border-radius:6px;
           padding:10px; margin:8px 0; white-space:pre-wrap; word-break:break-all;
           min-height:18px; font-family: ui-monospace, monospace; font-size:12px; }
    .label { color:#9aa0a6; margin-top:10px; }
    [hidden] { display:none !important; }

    /* 셸 레이아웃 */
    #view-list { padding:16px; }
    #view-detail { display:flex; flex-direction:column; height:100vh; }
    #detail-header { display:flex; align-items:center; gap:8px; padding:10px 14px;
                     background:#1b1d21; border-bottom:1px solid #33363c; }
    #detailTitle { flex:1; font-size:14px; font-weight:600; }
    #btnBackToList { width:auto; padding:6px 12px; margin:0; background:#444; }
    #task-bar { padding:8px 14px; font-size:11px; color:#9aa0a6;
                border-bottom:1px solid #2c2f36; }
    #tabs { display:flex; border-bottom:1px solid #33363c; }
    #tabs .tab { flex:1; }
    #tab-content { flex:1; overflow-y:auto; padding:14px; }
    #chat-dock { border-top:1px solid #33363c; background:#1b1d21; padding:10px 14px; }
    #chat-dock .row { display:flex; gap:6px; }
    #chatInput { flex:1; box-sizing:border-box; padding:8px; background:#23262b;
                 color:#e6e6e6; border:1px solid #33363c; border-radius:5px; }
    #btnChatSend { width:auto; padding:8px 14px; margin:0; }

    /* 반응형: 넓은 창이면 탭 콘텐츠 2열 여지 + 본문 최대폭 */
    @media (min-width: 760px) {
      #tab-content { max-width:1200px; margin:0 auto; width:100%; }
      #view-list { max-width:520px; margin:0 auto; }
    }
  </style>
```

- [ ] **Step 2: `<body>` 재구성**

현재 `<body> ... </body>` 전체를 아래로 교체. (기존 컨트롤 마크업은 그대로 옮김 — ID 불변)

```html
<body>
  <!-- ===== 목록 뷰 ===== -->
  <div id="view-list">
    <h1>auto_kairos PD</h1>

    <div class="label">1) 백엔드 연결</div>
    <button id="btnHealth">백엔드 확인</button>
    <div class="box" id="health">—</div>

    <div class="label">새 프로젝트</div>
    <input id="newTitle" type="text" placeholder="영상 제목/주제" style="width:100%;box-sizing:border-box;padding:7px;margin:3px 0;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
    <select id="newStyle" style="width:49%;padding:6px;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
      <option value="semoji">semoji</option>
      <option value="iromism">iromism</option>
    </select>
    <select id="newDuration" style="width:49%;padding:6px;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
      <option value="1분">1분</option><option value="3분">3분</option><option value="5분">5분</option>
    </select>
    <button id="btnCreate">프로젝트 만들기</button>
    <div class="box" id="current">현재 프로젝트: (없음)</div>

    <div class="label">프로젝트</div>
    <button id="btnProjects">프로젝트 목록 새로고침</button>
    <div class="box" id="projects">—</div>
  </div>

  <!-- ===== 상세 뷰 ===== -->
  <div id="view-detail" hidden>
    <div id="detail-header">
      <span id="detailTitle">프로젝트</span>
      <button id="btnBackToList">← 목록</button>
    </div>
    <div id="task-bar">태스크: (P5에서 활성)</div>
    <div id="tabs">
      <button id="btnTabPlanning" class="tab active">기획</button>
      <button id="btnTabStoryboard" class="tab">스토리보드</button>
    </div>
    <div id="tab-content">
      <!-- 기획 탭 -->
      <div id="tab-planning">
        <div class="label">원고</div>
        <button id="btnManuscript">원고 보기</button>
        <div class="box" id="manuscript">—</div>
        <div class="label" style="color:#666">(P2: 기획/리서치/원고 파일 뷰어)</div>
      </div>

      <!-- 스토리보드 탭 -->
      <div id="tab-storyboard" hidden>
        <div class="label">씬 분해 (PD)</div>
        <button id="btnDecompose">선택 프로젝트 씬 분해</button>
        <div class="box" id="scenes">—</div>

        <div class="label">기준 캐릭터 (베이스 리스타일)</div>
        <input id="charName" type="text" placeholder="캐릭터 이름 (예: 지오)" style="width:100%;box-sizing:border-box;padding:7px;margin:3px 0;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
        <input id="charLooks" type="text" placeholder="헤어·의상" style="width:100%;box-sizing:border-box;padding:7px;margin:3px 0;background:#1b1d21;color:#e6e6e6;border:1px solid #33363c;border-radius:5px;">
        <button id="btnGenCharacter">캐릭터 생성</button>
        <div class="box" id="characters">—</div>
        <button id="btnRefreshCharacters">캐릭터 새로고침</button>

        <div class="label">레퍼런스 이미지</div>
        <button id="btnRefList">레퍼런스 목록 생성</button>
        <button id="btnGenImages" class="alt">이미지 생성</button>
        <div class="box" id="gallery">—</div>
        <button id="btnImportImages" class="alt">레퍼런스 → AE 가져오기</button>
        <button id="btnRefreshGallery">갤러리 새로고침</button>

        <div class="label">스토리보드(씬 이미지)</div>
        <button id="btnGenStoryboard">씬 이미지 생성</button>
        <div class="box" id="storyboard">—</div>
        <button id="btnRefreshStoryboard">새로고침</button>
        <button id="btnImportStoryboard" class="alt">→ AE 가져오기</button>

        <div class="label">씬 레이어</div>
        <button id="btnGenLayers">레이어 생성</button>
        <div class="box" id="layers">—</div>
        <button id="btnRefreshLayers">레이어 새로고침</button>
        <button id="btnImportLayers" class="alt">레이어 → AE 가져오기</button>

        <div class="label">AE 컴프</div>
        <button id="btnBuild" class="alt">샘플 manifest → AE 컴프 생성</button>
      </div>
    </div>

    <!-- 하단 채팅(자리, P7 활성) -->
    <div id="chat-dock">
      <div class="label" style="margin:0 0 4px">💬 제작 비서 (P7에서 활성)</div>
      <div class="row">
        <input id="chatInput" type="text" placeholder="메시지… (아직 비활성)" disabled>
        <button id="btnChatSend" disabled>전송</button>
      </div>
    </div>
  </div>

  <script src="js/main.js"></script>
  <script src="js/nav.js"></script>
</body>
```

> 주의: 기존 `<script>` 태그가 `</body>` 앞에 이미 있었다면 위 교체에 포함되므로 중복 추가 금지. 교체 후 `main.js` → `nav.js` 순 1회만 존재해야 함.

- [ ] **Step 3: 구조 테스트 통과 확인(부분)**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py -q`
Expected: nav 관련 2개(`test_nav_defines_functions`, `test_main_calls_enterProject`)만 FAIL, 나머지 PASS.

- [ ] **Step 4: 커밋**

```bash
git add cep/com.autokairos.pd/index.html
git commit -m "feat(panel): index.html을 목록/상세 2뷰 + 탭(기획/스토리보드) + 하단 채팅 자리 + 반응형으로 재구성"
```

---

## Task 3: nav.js — 뷰/탭 전환

**Files:** Create `cep/com.autokairos.pd/js/nav.js`

- [ ] **Step 1: nav.js 작성**

```javascript
/* 뷰/탭 전환 — 목록 뷰 ↔ 상세 뷰, 기획/스토리보드 탭.
   SELECTED_PROJECT는 main.js의 전역(var)을 공유한다. main.js → nav.js 순 로드. */

function _$(id) { return document.getElementById(id); }

function showListView() {
  _$("view-detail").hidden = true;
  _$("view-list").hidden = false;
}

function enterProject(pid, label) {
  SELECTED_PROJECT = pid;            // main.js 전역
  _$("detailTitle").textContent = label || pid;
  _$("view-list").hidden = true;
  _$("view-detail").hidden = false;
  switchTab("planning");
}

function exitProject() {
  showListView();
}

function switchTab(name) {
  var planning = name === "planning";
  _$("tab-planning").hidden = !planning;
  _$("tab-storyboard").hidden = planning;
  _$("btnTabPlanning").classList.toggle("active", planning);
  _$("btnTabStoryboard").classList.toggle("active", !planning);
}

document.addEventListener("DOMContentLoaded", function () {
  _$("btnBackToList").addEventListener("click", exitProject);
  _$("btnTabPlanning").addEventListener("click", function () { switchTab("planning"); });
  _$("btnTabStoryboard").addEventListener("click", function () { switchTab("storyboard"); });
});
```

- [ ] **Step 2: JS 문법 검증**

Run: `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/nav.js','utf8'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add cep/com.autokairos.pd/js/nav.js
git commit -m "feat(panel): nav.js — 목록/상세 뷰 전환 + 기획/스토리보드 탭 전환"
```

---

## Task 4: main.js — 카드 클릭 시 프로젝트 입장

**Files:** Modify `cep/com.autokairos.pd/js/main.js`

먼저 `main.js`의 `loadProjects` 함수를 Read 한다(현재 `#projects`에 링크를 렌더하고 클릭 시 `SELECTED_PROJECT` 설정 + `$("current")` 갱신).

- [ ] **Step 1: loadProjects 클릭 핸들러를 enterProject 호출로 교체**

`loadProjects` 안에서 프로젝트 링크 클릭 콜백(현재 `SELECTED_PROJECT = this.getAttribute("data-pid"); $("current").textContent = ...` 부분)을 아래로 교체:

```javascript
        links[i].addEventListener("click", function (e) {
          e.preventDefault();
          var pid = this.getAttribute("data-pid");
          $("current").textContent = "현재 프로젝트: " + this.textContent;
          enterProject(pid, this.textContent);   // nav.js — 상세 뷰로 입장
        });
```

(주: `enterProject`가 `SELECTED_PROJECT`를 설정하므로 콜백에서 별도 설정 불필요. `links`/`i` 변수명은 기존 코드 그대로 유지.)

- [ ] **Step 2: createProject 성공 후에도 입장(선택 — 기존 동작 보존 + 입장)**

`createProject`의 성공 콜백에서 `SELECTED_PROJECT = j.project_id;` 다음 줄에 추가:

```javascript
      enterProject(j.project_id, j.title + " (" + j.project_id + ") [planned]");
```

- [ ] **Step 3: 전체 패널 JS 문법 검증**

Run: `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/main.js','utf8'))" && echo OK`
Expected: `OK`

- [ ] **Step 4: 구조 테스트 전체 통과**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_panel_structure.py -q`
Expected: PASS (9 tests)

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/js/main.js
git commit -m "feat(panel): 프로젝트 카드/생성 시 상세 뷰로 입장(enterProject)"
```

---

## Task 5: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/ -q` (2회)
Expected: 모두 PASS, git status 클린.

- [ ] **Step 2: 전체 JS 문법**

Run: `for f in main nav; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/$f.js','utf8'))"; done && echo ALL_OK`
Expected: `ALL_OK`

- [ ] **Step 3: (사용자) AE 검증** — 패널 재로드 → 목록 뷰 표시 → 프로젝트 카드 클릭 → 상세 뷰(헤더+나가기+탭+하단 채팅 자리) → [기획]/[스토리보드] 탭 전환 → [← 목록]으로 복귀. 기존 버튼(씬분해·캐릭터·이미지 등) 스토리보드 탭에서 동작.

---

## Self-Review

- **스펙 커버리지(§2 네비게이션, §3 탭 골격, §3.3 하단 채팅 자리, §10 반응형)**: Task 2(뷰/탭/채팅/반응형 마크업+CSS) + Task 3(전환) + Task 4(입장)로 충족. 기획 파일뷰어(§3.1)·시트(§3.2)·갤러리(§3.2)·비서 실동작(§4)·검색/TTS/AE(§6~8)는 P2~P7 — P1 비범위(스펙 §11과 일치).
- **Placeholder**: 채팅/태스크/파일뷰어는 "자리(P_ 활성)"로 명시 — 미구현 기능을 가짜로 두지 않고 비활성 표시. 코드 단계는 전부 완전 코드.
- **타입/ID 일관성**: 테스트가 검증하는 ID(view-list/view-detail/detailTitle/btnBackToList/btnTab*/tab-*/chat-dock/chatInput/btnChatSend/task-bar)와 Task 2 마크업, Task 3 nav.js 참조 ID 일치 확인. `enterProject(pid,label)` 시그니처 — nav.js 정의와 main.js 호출 일치.
- **로드 순서**: index.html에서 `main.js`(SELECTED_PROJECT var 정의) → `nav.js` 순. enterProject는 클릭 시 호출되므로 두 스크립트 파싱 후 → 안전.
