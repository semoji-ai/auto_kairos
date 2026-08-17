# P2 — 기획 탭 결과물 파일 뷰어 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 상세 뷰 "기획" 탭을, 프로젝트 산출물(기획서/리서치/원고)을 **파일 단위로 목록·열람**하는 뷰어로 구현한다.

**Architecture:** 백엔드 `projects.list_files()`가 프로젝트 최상위 문서 파일(.md/.json/.txt)을 카테고리(기획/리서치/원고/기타)로 그룹핑 → `/api/projects/files`. 파일 본문은 기존 `/api/projects/file?name=`(트래버설 방지) 재사용. 패널 `planning.js`가 그룹 목록 렌더 + 클릭 시 본문 뷰어 표시. 기존 임시 "원고 보기" 버튼은 일반 파일 뷰어로 대체.

**Tech Stack:** stdlib Python(백엔드), pytest, vanilla JS(CEP), node 문법 체크.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` — repo 루트에서.

**스코프:** 최상위 문서 파일만(서브디렉토리 리서치는 후속). 스토리보드/에셋/시스템 파일 제외. 읽기 전용(편집은 비서 P7).

---

## File Structure

- **Modify** `backend/projects.py` — `list_files(proj_dir)` 추가(그룹핑 + 제외 목록).
- **Modify** `backend/router.py` — `GET /api/projects/files` 추가.
- **Test** `tests/test_projects.py`, `tests/test_router.py` — list_files/엔드포인트.
- **Create** `cep/com.autokairos.pd/js/planning.js` — 파일 목록 렌더 + 뷰어 + 탭 진입 시 로드.
- **Modify** `cep/com.autokairos.pd/index.html` — 기획 탭 마크업(파일 목록 #planFiles + 뷰어 #planViewer), `btnManuscript`/`#manuscript` 제거, `planning.js` 스크립트 추가.
- **Modify** `cep/com.autokairos.pd/js/main.js` — `showManuscript` 바인딩/함수 제거.
- **Modify** `cep/com.autokairos.pd/js/nav.js` — `enterProject` 시 `loadPlanningFiles()` 호출(파일 목록 로드).
- **Modify** `tests/test_panel_structure.py` — 기획 탭 뷰어 ID 검증(btnManuscript 의존 제거).

---

## Task 1: projects.list_files (백엔드 그룹핑)

**Files:** Modify `backend/projects.py`; Test `tests/test_projects.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_projects.py`에 추가:

```python
def test_list_files_groups(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "plan.md").write_text("기획", encoding="utf-8")
    (d / "research_report.json").write_text("{}", encoding="utf-8")
    (d / "draft.md").write_text("초고", encoding="utf-8")
    (d / "final_manuscript.md").write_text("원고", encoding="utf-8")
    (d / "scenes.json").write_text("{}", encoding="utf-8")          # 제외(스토리보드)
    (d / "notes.txt").write_text("메모", encoding="utf-8")           # 기타
    groups = projects.list_files(d)
    by = {g["label"]: g["files"] for g in groups}
    assert by["기획"] == ["plan.md"]
    assert by["리서치"] == ["research_report.json"]
    assert sorted(by["원고"]) == ["draft.md", "final_manuscript.md"]
    assert "scenes.json" not in by.get("기타", [])
    assert by["기타"] == ["notes.txt"]
    # 빈 그룹은 결과에 없음
    assert all(g["files"] for g in groups)


def test_list_files_missing_dir(tmp_path):
    assert projects.list_files(tmp_path / "nope") == []
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_projects.py -q` → FAIL (list_files 없음).

- [ ] **Step 3: 구현** — `backend/projects.py` 상단 `ARTIFACT_FILES = [...]` 아래에 추가:

```python
_VIEW_EXT = {".md", ".json", ".txt"}
_EXCLUDE_FILES = {
    "scenes.json", "layers.json", "references.json", "image_assets.json",
    ".imagegen_last.txt",
}
_FILE_GROUPS = [
    ("기획", ("plan", "strategy", "brief")),
    ("리서치", ("research", "facts", "claims", "deep", "targeted", "skeleton", "outline")),
    ("원고", ("draft", "manuscript", "final_manuscript", "questions", "script")),
]


def list_files(proj_dir: Path) -> list[dict]:
    """프로젝트 최상위 문서 파일(.md/.json/.txt)을 카테고리로 그룹핑.
    스토리보드/에셋/시스템 파일은 제외. 빈 그룹은 결과에서 생략."""
    if not proj_dir.is_dir():
        return []
    names = sorted(
        f.name for f in proj_dir.iterdir()
        if f.is_file() and f.suffix.lower() in _VIEW_EXT and f.name not in _EXCLUDE_FILES
    )
    buckets: dict[str, list[str]] = {label: [] for label, _ in _FILE_GROUPS}
    buckets["기타"] = []
    for n in names:
        low = n.lower()
        for label, keys in _FILE_GROUPS:
            if any(k in low for k in keys):
                buckets[label].append(n)
                break
        else:
            buckets["기타"].append(n)
    order = [label for label, _ in _FILE_GROUPS] + ["기타"]
    return [{"label": label, "files": buckets[label]} for label in order if buckets[label]]
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_projects.py -q` → PASS.

- [ ] **Step 5: 커밋**

```bash
git add backend/projects.py tests/test_projects.py
git commit -m "feat(backend): projects.list_files — 산출물 파일 카테고리 그룹핑(기획/리서치/원고/기타)"
```

---

## Task 2: GET /api/projects/files (라우터)

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:

```python
def test_projects_files_list(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "plan.md").write_text("기획", encoding="utf-8")
    (proj / "final_manuscript.md").write_text("원고", encoding="utf-8")
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects/files",
                                {"project_id": "p"}, None, ctx)
    assert code == 200
    labels = [g["label"] for g in body["groups"]]
    assert "기획" in labels and "원고" in labels


def test_projects_files_missing_project(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("GET", "/api/projects/files",
                                {"project_id": "nope"}, None, ctx)
    assert code == 200
    assert body["groups"] == []
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -q` → 새 2개 FAIL.

- [ ] **Step 3: 구현** — `backend/router.py`의 `if method == "GET" and p == "/api/projects/file":` 블록 **앞**에 추가:

```python
    if method == "GET" and p == "/api/projects/files":
        pid = query.get("project_id", "")
        return 200, {"groups": projects.list_files(root / pid)}
```

(주: `/api/projects/files`가 `/api/projects/file`보다 먼저 매칭되도록 앞에 둔다 — 정확 일치라 순서 무관하지만 가독성상 인접 배치.)

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, git status 클린.

- [ ] **Step 5: 커밋**

```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): GET /api/projects/files — 산출물 파일 그룹 목록"
```

---

## Task 3: 패널 — 기획 탭 파일 뷰어 마크업

**Files:** Modify `cep/com.autokairos.pd/index.html`; Modify `tests/test_panel_structure.py`

먼저 `index.html`의 `<div id="tab-planning"> ... </div>` 블록을 Read 한다.

- [ ] **Step 1: 기획 탭 마크업 교체** — 현재 기획 탭 블록:

```html
      <div id="tab-planning">
        <div class="label">원고</div>
        <button id="btnManuscript">원고 보기</button>
        <div class="box" id="manuscript">—</div>
        <div class="label" style="color:#666">(P2: 기획/리서치/원고 파일 뷰어)</div>
      </div>
```

을 아래로 교체:

```html
      <div id="tab-planning">
        <div class="label">결과물 (기획·리서치·원고)</div>
        <button id="btnReloadFiles">파일 새로고침</button>
        <div class="box" id="planFiles" style="min-height:40px">—</div>
        <div class="label">미리보기</div>
        <div class="box" id="planViewer" style="max-height:50vh;overflow:auto">파일을 선택하세요.</div>
      </div>
```

- [ ] **Step 2: 구조 테스트 갱신** — `tests/test_panel_structure.py`의 `test_existing_controls_present_in_detail`에서 `'id="btnManuscript"'` 항목을 제거하고, 새 테스트 추가:

기존 리스트에서 `'id="btnManuscript"'` 줄 삭제. 파일 끝에 추가:

```python
def test_planning_tab_has_file_viewer():
    html = HTML.read_text(encoding="utf-8")
    for el in ['id="btnReloadFiles"', 'id="planFiles"', 'id="planViewer"']:
        assert el in html, el
    # 임시 원고보기 버튼/박스는 제거됨
    assert 'id="btnManuscript"' not in html
    assert 'id="manuscript"' not in html


def test_index_loads_planning_js():
    assert 'src="js/planning.js"' in HTML.read_text(encoding="utf-8")
```

- [ ] **Step 3: planning.js 스크립트 태그 추가** — `index.html`의 `<script src="js/nav.js"></script>` 줄 **뒤**에 추가:

```html
  <script src="js/planning.js"></script>
```

- [ ] **Step 4: 부분 확인** — `... -m pytest tests/test_panel_structure.py -q` → `test_planning_tab_has_file_viewer` PASS, `test_index_loads_planning_js`는 planning.js 미생성이라도 마크업만 보므로 PASS. (main.js의 showManuscript 미정리로 다른 테스트는 영향 없음.)

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/index.html tests/test_panel_structure.py
git commit -m "feat(panel): 기획 탭을 파일 뷰어 마크업(목록+미리보기)으로 교체, 임시 원고보기 제거"
```

---

## Task 4: planning.js — 파일 목록·뷰어 로직

**Files:** Create `cep/com.autokairos.pd/js/planning.js`

- [ ] **Step 1: planning.js 작성**

```javascript
/* 기획 탭 — 산출물 파일 목록(그룹) + 미리보기. BACKEND/$/SELECTED_PROJECT는 main.js 전역. */

function loadPlanningFiles() {
  if (!SELECTED_PROJECT) { $("planFiles").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("planFiles").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/projects/files?project_id=" + encodeURIComponent(SELECTED_PROJECT))
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var groups = j.groups || [];
      if (!groups.length) { $("planFiles").textContent = "(문서 없음)"; return; }
      $("planFiles").innerHTML = groups.map(function (g) {
        var items = g.files.map(function (n) {
          return '<a href="#" data-file="' + n + '" style="display:inline-block;margin:2px 8px 2px 0;color:#7ab0ff;">' + n + '</a>';
        }).join("");
        return '<div style="margin:4px 0"><span style="color:#9aa0a6">' + g.label + '</span><br>' + items + '</div>';
      }).join("");
      var links = $("planFiles").querySelectorAll("a[data-file]");
      for (var i = 0; i < links.length; i++) {
        links[i].addEventListener("click", function (e) {
          e.preventDefault();
          viewPlanningFile(this.getAttribute("data-file"));
        });
      }
    })
    .catch(function (e) { $("planFiles").textContent = "오류: " + e; });
}

function viewPlanningFile(name) {
  $("planViewer").textContent = "불러오는 중... (" + name + ")";
  fetch(BACKEND + "/api/projects/file?project_id=" + encodeURIComponent(SELECTED_PROJECT) +
        "&name=" + encodeURIComponent(name))
    .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
    .then(function (res) {
      $("planViewer").textContent =
        (res.ok && res.j.content != null) ? res.j.content : ("(열 수 없음) " + JSON.stringify(res.j));
    })
    .catch(function (e) { $("planViewer").textContent = "오류: " + e; });
}

document.addEventListener("DOMContentLoaded", function () {
  $("btnReloadFiles").addEventListener("click", loadPlanningFiles);
});
```

- [ ] **Step 2: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/planning.js','utf8'))" && echo OK` → `OK`

- [ ] **Step 3: 커밋**

```bash
git add cep/com.autokairos.pd/js/planning.js
git commit -m "feat(panel): planning.js — 산출물 파일 그룹 목록 + 클릭 미리보기"
```

---

## Task 5: main.js/nav.js 정리 — showManuscript 제거, 진입 시 파일 로드

**Files:** Modify `cep/com.autokairos.pd/js/main.js`, `cep/com.autokairos.pd/js/nav.js`

먼저 `main.js`에서 `showManuscript` 함수와 그 바인딩(`$("btnManuscript").addEventListener("click", showManuscript);`)을 Read 로 확인한다.

- [ ] **Step 1: main.js에서 showManuscript 바인딩 제거** — DOMContentLoaded 안의 아래 줄 삭제:

```javascript
  $("btnManuscript").addEventListener("click", showManuscript);
```

- [ ] **Step 2: main.js에서 showManuscript 함수 제거** — `function showManuscript() { ... }` 블록 전체 삭제(더 이상 호출 없음 — 파일 뷰어가 대체).

- [ ] **Step 3: nav.js — enterProject 시 파일 목록 로드** — `enterProject` 안 `switchTab("planning");` 다음 줄에 추가:

```javascript
  if (typeof loadPlanningFiles === "function") loadPlanningFiles();
```

(planning.js 로드 순서 보장 위해 `typeof` 가드 — index.html은 main→nav→planning 순이나 enterProject는 클릭 시 호출되므로 안전. 가드는 방어적.)

- [ ] **Step 4: JS 문법 + 전체 테스트** —

```bash
for f in main nav planning; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo JS_OK
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/ -q
```
Expected: `JS_OK` + 전체 PASS. (`test_main_calls_enterProject`는 여전히 enterProject 호출 존재 → PASS. showManuscript 제거로 깨지는 테스트 없음 — manuscript 의존 테스트는 Task 3에서 제거됨.)

- [ ] **Step 5: 커밋**

```bash
git add cep/com.autokairos.pd/js/main.js cep/com.autokairos.pd/js/nav.js
git commit -m "refactor(panel): showManuscript 제거(파일 뷰어로 대체) + 프로젝트 입장 시 파일 목록 로드"
```

---

## Task 6: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` (2회) → PASS, git status 클린.
- [ ] **Step 2: 전체 JS 문법** — `for f in main nav planning; do node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/'+'$f'+'.js','utf8'))"; done && echo ALL_OK` → `ALL_OK`
- [ ] **Step 3: (사용자) AE 검증** — 프로젝트 입장 → 기획 탭 → 파일 목록(기획/리서치/원고 그룹) 표시 → 파일 클릭 → 미리보기에 본문 → [파일 새로고침] 동작.

---

## Self-Review

- **스펙 커버리지(§3.1 기획 탭 = 결과물 파일 단위 열람)**: list_files(T1)+/api/projects/files(T2)+기획 탭 마크업(T3)+planning.js(T4)+진입 로드(T5)로 충족. md 렌더링은 텍스트 미리보기로 단순화(YAGNI; 스펙 "md 렌더링/텍스트" 허용 범위). 서브디렉토리 리서치 파일은 비범위(스펙 P2 최상위 한정).
- **Placeholder 없음**: 모든 코드 단계 완전 코드. 카테고리 키워드/제외 목록 명시.
- **타입/ID 일관성**: `list_files`→`[{label, files}]`, 엔드포인트 `{groups:[...]}`, planning.js가 `groups`/`g.files`/`data-file` 사용 — 일치. 제거 대상 ID(btnManuscript/manuscript)는 T3 마크업·T5 main.js·T3 테스트에서 일괄 제거(잔존 참조 없음). enterProject(T5)·loadPlanningFiles(T4) 시그니처 일치.
- **회귀 방지**: `/api/projects/file`(기존, 트래버설 방지) 재사용 — 변경 없음. 기존 `test_projects_file_*` 영향 없음.
