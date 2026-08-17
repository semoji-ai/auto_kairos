# SB1 — 스토리보드 탭 2-pane 레이아웃 + 컬럼 리사이즈 + 도구상자 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 스토리보드 탭을 좌(프로덕션 시트)/우(도구상자+세로 갤러리) 2-pane로 재구성한다. 시트 컬럼을 드래그로 너비 조절 가능하게 하고(이미지 컬럼 기본 2배), 나레이션 저장 버튼을 소형화하며, 흩어진 버튼을 우측 도구상자로 모은다(배치·고급은 접이식).

**Architecture:** 순수 패널 변경(백엔드 무관). index.html 스토리보드 탭을 `#sb-2pane`(`#sb-left`+`#sb-right`)로 재배치 — **모든 기존 버튼/박스 ID 보존**(main.js/gallery.js/storyboard.js 바인딩 무손상). 컬럼 너비는 `#sheet`의 CSS 변수 `--cols`로 제어, 헤더 핸들 드래그로 갱신(storyboard.js). 갤러리 썸네일은 세로 배열(클래스 기반).

**Tech Stack:** CEP HTML/CSS/vanilla JS, pytest(구조 검증), node 문법.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트.

**보존 필수 ID(바인딩됨):** btnDecompose, btnLoadSheet, btnGenCharacter, btnRefreshCharacters, btnGalSearch, btnGalRefresh, galSearch, galEngine, btnRefList, btnGenImages, btnImportImages, btnRefreshGallery, btnGenStoryboard, btnRefreshStoryboard, btnImportStoryboard, btnGenLayers, btnRefreshLayers, btnImportLayers, btnBuild + 박스 scenes/characters/gallery/storyboard/layers/aeresult/gallery-panel/sheet.

---

## File Structure

- **Modify** `cep/com.autokairos.pd/index.html` — 스토리보드 탭 2-pane 재배치 + CSS(2-pane/그리드 --cols/세로 갤러리/소형 버튼/도구상자).
- **Modify** `cep/com.autokairos.pd/js/storyboard.js` — 헤더에 리사이즈 핸들 + `--cols` 적용 + 컬럼 드래그 리사이즈 + 저장 버튼 라벨 소형(💾).
- **Modify** `cep/com.autokairos.pd/js/gallery.js` — 소스 썸네일 세로(클래스 `gal-thumb`).
- **Modify** `tests/test_panel_structure.py` — 2-pane/도구상자 ID 검증.

---

## Task 1: index.html — 스토리보드 탭 2-pane 재배치

**Files:** Modify `cep/com.autokairos.pd/index.html`

먼저 `<div id="tab-storyboard" hidden> … </div>` 전체를 Read 한다.

- [ ] **Step 1: 스토리보드 탭 블록 전체 교체** — 현재 `<div id="tab-storyboard" hidden>`부터 그 닫는 `</div>`까지를 아래로 교체(모든 ID 보존, 위치만 재배치):

```html
      <div id="tab-storyboard" hidden>
        <div id="sb-2pane">
          <!-- 좌: 프로덕션 시트 -->
          <div id="sb-left">
            <div class="label">프로덕션 시트
              <button id="btnLoadSheet" class="mini">시트 불러오기</button>
            </div>
            <div id="sheet">—</div>
          </div>

          <!-- 우: 도구상자 + 세로 갤러리 -->
          <div id="sb-right">
            <div id="sb-toolbar">
              <button id="btnOpenGenModal" title="이미지 생성(SB2)">+ 이미지 생성</button>
              <button id="btnDecompose" class="alt">씬 분해</button>
              <button id="btnRefreshCharacters" class="alt">캐릭터</button>
              <button id="btnGalRefresh" class="alt">소스</button>
            </div>
            <div class="sb-search">
              <input id="galSearch" type="text" placeholder="이미지 검색">
              <select id="galEngine">
                <option value="serper">구글</option>
                <option value="pixabay">pixabay</option>
              </select>
              <button id="btnGalSearch" class="mini">검색</button>
            </div>
            <div class="box" id="gallery-panel" style="min-height:60px">—</div>

            <!-- 기준 캐릭터(임시 — SB2에서 모달로 통합) -->
            <details class="sb-acc">
              <summary>기준 캐릭터</summary>
              <input id="charName" type="text" placeholder="이름 (예: 지오)">
              <input id="charLooks" type="text" placeholder="헤어·의상">
              <button id="btnGenCharacter" class="mini">캐릭터 생성</button>
              <div class="box" id="characters">—</div>
            </details>

            <!-- 배치·고급(레거시 — 접이식, 바인딩 보존) -->
            <details class="sb-acc">
              <summary>배치 · 고급</summary>
              <div class="label">씬 분해 결과</div>
              <div class="box" id="scenes">—</div>
              <div class="label">레퍼런스 이미지</div>
              <button id="btnRefList" class="mini">레퍼런스 목록</button>
              <button id="btnGenImages" class="mini alt">이미지 생성</button>
              <div class="box" id="gallery">—</div>
              <button id="btnImportImages" class="mini alt">레퍼런스 → AE</button>
              <button id="btnRefreshGallery" class="mini">갤러리 새로고침</button>
              <div class="label">씬 이미지(배치)</div>
              <button id="btnGenStoryboard" class="mini">씬 이미지 생성</button>
              <div class="box" id="storyboard">—</div>
              <button id="btnRefreshStoryboard" class="mini">새로고침</button>
              <button id="btnImportStoryboard" class="mini alt">→ AE</button>
              <div class="label">씬 레이어(배치)</div>
              <button id="btnGenLayers" class="mini">레이어 생성</button>
              <div class="box" id="layers">—</div>
              <button id="btnRefreshLayers" class="mini">레이어 새로고침</button>
              <button id="btnImportLayers" class="mini alt">레이어 → AE</button>
              <div class="label">AE 컴프</div>
              <button id="btnBuild" class="mini alt">manifest → AE 컴프</button>
              <div class="box" id="aeresult">—</div>
            </details>
          </div>
        </div>
      </div>
```

- [ ] **Step 2: CSS 추가** — `<style>`의 스토리보드 시트 CSS 블록(`.sheet-row button { … }` 다음)에 추가:

```css
    /* 스토리보드 2-pane */
    #sb-2pane { display:flex; gap:12px; align-items:flex-start; }
    #sb-left { flex:1; min-width:0; }
    #sb-right { width:300px; flex:0 0 300px; }
    #sb-toolbar { display:flex; flex-wrap:wrap; gap:4px; }
    #sb-toolbar button { width:auto; flex:0 0 auto; margin:0; padding:6px 8px; font-size:12px; }
    .sb-search { display:flex; gap:4px; margin:6px 0; }
    .sb-search input { flex:1; min-width:0; box-sizing:border-box; padding:6px; background:#1b1d21; color:#e6e6e6; border:1px solid #33363c; border-radius:5px; }
    .sb-search select { padding:5px; background:#1b1d21; color:#e6e6e6; border:1px solid #33363c; border-radius:5px; }
    button.mini { width:auto; margin:2px 0; padding:5px 9px; font-size:12px; }
    .sb-acc { margin-top:8px; border-top:1px solid #2c2f36; }
    .sb-acc > summary { cursor:pointer; color:#9aa0a6; font-size:12px; padding:6px 0; }
    .sb-acc input { width:100%; box-sizing:border-box; padding:6px; margin:3px 0; background:#1b1d21; color:#e6e6e6; border:1px solid #33363c; border-radius:5px; }
    /* 세로 갤러리 썸네일 */
    #gallery-panel .gal-thumb { display:block; width:100%; height:auto; margin:5px 0; border-radius:4px; }
    /* 좁은 창: 세로 스택 */
    @media (max-width: 720px) {
      #sb-2pane { flex-direction:column; }
      #sb-right { width:auto; flex:none; }
    }
```

- [ ] **Step 3: 시트 그리드를 --cols 변수로** — `.sheet-head, .sheet-row { display:grid; grid-template-columns: 30px 110px minmax(150px,1fr) 120px 60px; … }` 의 `grid-template-columns` 줄을 아래로 교체(이미지 기본 2배=220px, 변수화):

```css
    .sheet-head, .sheet-row { display:grid;
      grid-template-columns: var(--cols, 30px 220px minmax(150px,1fr) 120px 60px);
      gap:8px; align-items:start; min-width:520px; }
```

- [ ] **Step 4: 구조 테스트 추가** — `tests/test_panel_structure.py` 끝에:

```python
def test_storyboard_2pane():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="sb-2pane"', 'id="sb-left"', 'id="sb-right"', 'id="sb-toolbar"', 'id="btnOpenGenModal"']:
        assert el in html, el


def test_storyboard_preserves_legacy_ids():
    html = HTML.read_text(encoding="utf-8")
    for bid in ['id="btnDecompose"', 'id="btnRefList"', 'id="btnGenStoryboard"',
                'id="btnGenLayers"', 'id="btnBuild"', 'id="btnGenCharacter"',
                'id="btnRefreshCharacters"', 'id="btnGalRefresh"', 'id="btnGalSearch"',
                'id="sheet"', 'id="gallery-panel"', 'id="scenes"', 'id="aeresult"']:
        assert bid in html, bid
```

- [ ] **Step 5: 부분 확인 + 커밋** — `... -m pytest tests/test_panel_structure.py -q` → 새 2개 PASS, 기존 PASS.

```bash
git add cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 스토리보드 탭 2-pane(좌 시트/우 도구상자+세로 갤러리) 재배치, 레거시 ID 보존"
```

---

## Task 2: storyboard.js — 컬럼 리사이즈 + 저장 버튼 소형화

**Files:** Modify `cep/com.autokairos.pd/js/storyboard.js`

먼저 `loadSheet`(헤더 생성)와 `renderRow`(sv-nar 버튼)를 Read 한다.

- [ ] **Step 1: 컬럼 너비 상태 + 적용 + 리사이즈 핸들** — `storyboard.js` 상단(`function loadSheet` 위)에 추가:

```javascript
/* 컬럼 너비(px) — 인덱스 2(스크립트)는 flex(1fr). 드래그로 갱신. */
var COLW = [30, 220, null, 120, 60];

function _colsCss() {
  return COLW.map(function (w, i) { return i === 2 ? "minmax(150px,1fr)" : w + "px"; }).join(" ");
}

function _applyCols() {
  var el = $("sheet");
  if (el) el.style.setProperty("--cols", _colsCss());
}

function _bindColResize() {
  var handles = $("sheet").querySelectorAll(".col-resize");
  for (var i = 0; i < handles.length; i++) {
    handles[i].addEventListener("mousedown", function (e) {
      e.preventDefault();
      var idx = parseInt(this.getAttribute("data-col"), 10);
      var startX = e.clientX, startW = COLW[idx] || 100;
      function move(ev) {
        COLW[idx] = Math.max(30, startW + (ev.clientX - startX));
        _applyCols();
      }
      function up() {
        document.removeEventListener("mousemove", move);
        document.removeEventListener("mouseup", up);
      }
      document.addEventListener("mousemove", move);
      document.addEventListener("mouseup", up);
    });
  }
}
```

- [ ] **Step 2: 헤더에 리사이즈 핸들 + 적용** — `loadSheet`의 헤더 줄을 교체. 현재:

```javascript
      var head = '<div class="sheet-head"><div>#</div><div>이미지</div><div>스크립트</div><div>에셋</div><div>TTS</div></div>';
      $("sheet").innerHTML = head + list.map(function (s) { return renderRow(s, dir); }).join("");
      bindRows();
```

을:

```javascript
      var head = '<div class="sheet-head">'
        + '<div>#</div>'
        + '<div>이미지<span class="col-resize" data-col="1"></span></div>'
        + '<div>스크립트</div>'
        + '<div>에셋<span class="col-resize" data-col="3"></span></div>'
        + '<div>TTS<span class="col-resize" data-col="4"></span></div>'
        + '</div>';
      $("sheet").innerHTML = head + list.map(function (s) { return renderRow(s, dir); }).join("");
      _applyCols();
      _bindColResize();
      bindRows();
```

- [ ] **Step 3: 저장 버튼 소형화** — `renderRow`의 나레이션 저장 버튼을 아이콘 소형으로. 현재:

```javascript
    + '    <button class="sv-nar" data-scene="' + n + '">나레이션 저장</button>'
```

을:

```javascript
    + '    <button class="sv-nar mini" data-scene="' + n + '" title="나레이션 저장">💾</button>'
```

- [ ] **Step 4: col-resize 핸들 CSS** — `index.html` `<style>`의 시트 CSS에 추가:

```css
    .sheet-head > div { position:relative; }
    .col-resize { position:absolute; right:-4px; top:0; width:8px; height:100%;
      cursor:col-resize; }
    .col-resize:hover { background:#3a6df0; opacity:0.4; }
```

(주: 이 CSS 추가는 index.html 수정이므로 Task 2에 포함해 함께 커밋.)

- [ ] **Step 5: JS 문법 + 구조** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/storyboard.js','utf8'))" && echo OK`. `... -m pytest tests/test_panel_structure.py -q` PASS(dropOnScene/loadSheet 존재 유지).

- [ ] **Step 6: 커밋**

```bash
git add cep/com.autokairos.pd/js/storyboard.js cep/com.autokairos.pd/index.html
git commit -m "feat(panel): 시트 컬럼 드래그 리사이즈(--cols)+이미지 기본 2배, 나레이션 저장 버튼 소형화"
```

---

## Task 3: gallery.js — 소스 썸네일 세로 배열

**Files:** Modify `cep/com.autokairos.pd/js/gallery.js`

먼저 `loadGallery`의 이미지 렌더(인라인 width:72px) 부분을 Read 한다.

- [ ] **Step 1: 소스 썸네일을 클래스 기반 세로로** — `loadGallery`의 이미지 항목 렌더에서 인라인 `style="width:72px;…"`를 `class="gal-thumb"`로 교체. 현재(이미지 분기):

```javascript
          return '<img src="file://' + it.dir + '/' + it.rel + '" draggable="true"'
            + ' ondragstart="event.dataTransfer.setData(\'text/plain\', this.getAttribute(\'data-rel\'))"'
            + ' data-rel="' + _gesc(it.rel) + '" title="' + _gesc(it.rel) + ' — 시트 행으로 드래그"'
            + ' style="width:72px;height:auto;margin:3px;border-radius:4px;cursor:grab;">';
```

을:

```javascript
          return '<img src="file://' + it.dir + '/' + it.rel + '" draggable="true"'
            + ' ondragstart="event.dataTransfer.setData(\'text/plain\', this.getAttribute(\'data-rel\'))"'
            + ' data-rel="' + _gesc(it.rel) + '" title="' + _gesc(it.rel) + ' — 시트 행으로 드래그"'
            + ' class="gal-thumb" style="cursor:grab;">';
```

- [ ] **Step 2: 검색 결과 썸네일도 세로(클릭 저장 유지)** — `searchGallery`의 결과 이미지 렌더에서 인라인 width를 `class="gal-thumb"`로 교체. 현재:

```javascript
        return '<img src="' + _gesc(im.thumb) + '" data-url="' + _gesc(im.url) + '" data-idx="' + idx
          + '" title="클릭하면 소스로 저장: ' + _gesc(im.title) + '"'
          + ' style="width:72px;height:auto;margin:3px;border-radius:4px;cursor:pointer;">';
```

을:

```javascript
        return '<img src="' + _gesc(im.thumb) + '" data-url="' + _gesc(im.url) + '" data-idx="' + idx
          + '" title="클릭하면 소스로 저장: ' + _gesc(im.title) + '"'
          + ' class="gal-thumb" style="cursor:pointer;">';
```

- [ ] **Step 3: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/gallery.js','utf8'))" && echo OK`

- [ ] **Step 4: 커밋**

```bash
git add cep/com.autokairos.pd/js/gallery.js
git commit -m "feat(panel): 갤러리 소스/검색 썸네일을 세로 배열(gal-thumb 클래스)"
```

---

## Task 4: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, 클린.
- [ ] **Step 2: 전체 JS 문법** — `for f in main nav planning storyboard gallery; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK`
- [ ] **Step 3: (사용자) AE 검증** — 스토리보드 탭 → 좌측 시트/우측 도구상자+세로 갤러리 2-pane → [시트 불러오기] → 헤더 컬럼 경계 드래그로 너비 조절(이미지 기본 2배) → 나레이션 저장 💾 소형 → 우측 [소스]·검색·[캐릭터] 동작 → "배치·고급" 접이식 안에 레거시 버튼.

---

## Self-Review

- **요청 커버리지**: (1)이미지 2배+리사이즈→Task1 CSS(--cols 220px)+Task2 핸들. (2)저장 버튼 소형→Task2 💾. (3)2-pane 우측 세로 갤러리→Task1+Task3. (5)도구상자 버튼 통합→Task1 #sb-toolbar(+이미지 생성/씬분해/캐릭터/소스), 레거시는 접이식. (4)이미지 생성 모달=SB2, (6)호버 레이어=SB3 — SB1 비범위([+이미지 생성] 버튼은 자리만, SB2가 배선).
- **바인딩 무손상**: 모든 기존 ID를 새 위치에 보존(main.js/gallery.js의 addEventListener 대상 전부 존재). btnOpenGenModal만 신규(SB1에선 미배선 — 클릭 무동작, SB2에서 모달 연결).
- **Placeholder 없음**: 전 코드 완전. 컬럼 리사이즈는 mousedown/move/up 표준.
- **타입/일관성**: `--cols` 변수는 index.html CSS 기본값과 storyboard.js `_colsCss` 동일 형식(5컬럼, idx2=1fr). gal-thumb 클래스는 index.html CSS와 gallery.js 양쪽 일치.
- **로드 순서 무변경**: main→nav→planning→storyboard→gallery. _applyCols/_bindColResize는 loadSheet 내에서 호출.
