# M-PM — 프로젝트 관리(생성/불러오기) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 패널에서 프로젝트를 새로 만들고(제목/스타일/분량 → plan.md) 불러와, 현재 프로젝트 + 상태/아티팩트를 명확히 관리한다.

**Architecture:** 백엔드 `projects.create_project` + `/api/projects/create`. 패널에 "새 프로젝트" 폼 + "현재 프로젝트" 표시 + load 상세. 기존 액션 버튼은 SELECTED_PROJECT에 그대로 적용.

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` **repo 루트에서**.

---

## Task 1: projects.create_project + status "planned"

**Files:** Modify `backend/projects.py`; Test `tests/test_projects.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_projects.py`에 추가:
```python
def test_create_project(tmp_path):
    info = projects.create_project(tmp_path, "테슬라 역사", channel="semoji", duration="1분")
    pid = info["project_id"]
    assert (tmp_path / pid / "plan.md").exists()
    plan = (tmp_path / pid / "plan.md").read_text(encoding="utf-8")
    assert "테슬라 역사" in plan and "semoji" in plan and "1분" in plan
    # 생성 직후 status = planned
    row = next(r for r in projects.scan_projects(tmp_path) if r["project_id"] == pid)
    assert row["status"] == "planned"


def test_status_planned_when_plan_only(tmp_path):
    d = tmp_path / "x"; d.mkdir()
    (d / "plan.md").write_text("# T", encoding="utf-8")
    row = next(r for r in projects.scan_projects(tmp_path) if r["project_id"] == "x")
    assert row["status"] == "planned"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_projects.py -v` → FAIL

- [ ] **Step 3: 구현** — `backend/projects.py`:
(a) 상단 `import uuid` 추가.
(b) `_status`에 planned 추가:
```python
def _status(arts: dict) -> str:
    if arts.get("scenes.json"):
        return "decomposed"
    if arts.get("final_manuscript.md"):
        return "manuscript"
    if arts.get("plan.md"):
        return "planned"
    return "empty"
```
(c) 함수 추가:
```python
def create_project(root: Path, title: str, *, channel: str = "semoji",
                   duration: str = "1분", tone: str = "흥미로운 다큐") -> dict:
    """projects/{id}/plan.md 생성. id=uuid8."""
    root.mkdir(parents=True, exist_ok=True)
    pid = uuid.uuid4().hex[:8]
    d = root / pid
    d.mkdir(parents=True, exist_ok=False)
    (d / "plan.md").write_text(
        f"# {title}\n\n채널: {channel}\n분량: {duration}\n톤: {tone}\n", encoding="utf-8")
    return {"project_id": pid, "title": title, "status": "planned"}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_projects.py -v` → PASS. 전체도 확인.

- [ ] **Step 5: 커밋**
```bash
git add backend/projects.py tests/test_projects.py
git commit -m "feat(backend): projects.create_project + status planned(plan.md만 있을 때)"
```

---

## Task 2: /api/projects/create (router.py)

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_router.py`에 추가:
```python
def test_projects_create(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/create", {},
                                {"title": "새 영상", "channel": "semoji", "duration": "1분"}, ctx)
    assert code == 200
    pid = body["project_id"]
    assert (tmp_path / pid / "plan.md").exists()


def test_projects_create_requires_title(tmp_path):
    ctx = {"root": tmp_path, "jobs": JobRegistry()}
    code, body = handle_request("POST", "/api/projects/create", {}, {"title": ""}, ctx)
    assert code == 400
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_router.py -v` → 새 2개 FAIL

- [ ] **Step 3: router.py 확장** — `/api/projects/load` 블록 다음에:
```python
    if method == "POST" and p == "/api/projects/create":
        b = body or {}
        title = (b.get("title") or "").strip()
        if not title:
            return 400, {"error": "title 필요"}
        info = projects.create_project(
            root, title,
            channel=b.get("channel", "semoji"),
            duration=b.get("duration", "1분"))
        return 200, info
```

- [ ] **Step 4: 통과 (멱등 2회)** — `... -m pytest tests/ -q` 2회 → PASS, git status 클린.

- [ ] **Step 5: 커밋**
```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): POST /api/projects/create"
```

---

## Task 3: 패널 — 새 프로젝트 폼 + 현재 프로젝트 표시 + load 상세

**Files:** Modify `cep/com.autokairos.pd/{index.html,js/main.js}`

먼저 두 파일 Read (loadProjects/SELECTED_PROJECT/$/BACKEND + DOMContentLoaded).

- [ ] **Step 1: index.html** — "프로젝트" 라벨 블록 **위**(h1 다음, 백엔드 블록 다음)에 삽입:
```html
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
```

- [ ] **Step 2: main.js** — 함수 추가(DOMContentLoaded 위):
```js
function createProject() {
  var title = ($("newTitle").value || "").trim();
  if (!title) { $("current").textContent = "제목을 입력하세요."; return; }
  fetch(BACKEND + "/api/projects/create", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title, channel: $("newStyle").value, duration: $("newDuration").value }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (!j.project_id) { $("current").textContent = "생성 실패: " + JSON.stringify(j); return; }
      SELECTED_PROJECT = j.project_id;
      $("current").textContent = "현재 프로젝트: " + j.title + " (" + j.project_id + ") [planned]";
      $("newTitle").value = "";
      loadProjects();
    })
    .catch(function (e) { $("current").textContent = "오류: " + e; });
}
```
그리고 `loadProjects`의 프로젝트 링크 클릭 핸들러 안(SELECTED_PROJECT 설정하는 곳)에 현재표시 갱신 1줄 추가 — 클릭 콜백에서:
```js
          SELECTED_PROJECT = this.getAttribute("data-pid");
          $("current").textContent = "현재 프로젝트: " + this.textContent;   // ← 추가
```
(this.textContent에 "pid · title [status]"가 들어있음)

- [ ] **Step 3: DOMContentLoaded 바인딩 추가**
```js
  $("btnCreate").addEventListener("click", createProject);
```

- [ ] **Step 4: JS 문법** — `node -e "new Function(require('fs').readFileSync('cep/com.autokairos.pd/js/main.js','utf8'))" && echo OK`

- [ ] **Step 5: 커밋**
```bash
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/main.js
git commit -m "feat(panel): 새 프로젝트 만들기 폼 + 현재 프로젝트 표시"
```

---

## Task 4: 통합 검증

- [ ] **Step 1: 전체 테스트 멱등 2회** — `... -m pytest tests/ -q` → PASS, 클린.
- [ ] **Step 2: import** — `... -c "from backend import projects, router; print('ok')"`
- [ ] **Step 3: (사용자) AE 검증** — 패널 재로드 → 제목 입력 → 「프로젝트 만들기」 → 목록에 뜨고 현재 프로젝트 표시 → 그 프로젝트로 씬분해 등 진행.

---

## Self-Review
- create_project(T1)/api(T2)/패널 폼·현재표시(T3). status planned 추가(plan-only). 기존 list/load/액션 무손상.
- Placeholder 없음. 타입 일관(create_project/{project_id,title,status}).
- 미반영: 5문 기획 인터뷰(richer brief)는 후속. 지금은 제목/스타일/분량 plan.md.
