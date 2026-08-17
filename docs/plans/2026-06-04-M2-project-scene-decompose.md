# M2 — 프로젝트 & 씬 분해 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 실제 프로젝트를 패널에서 불러오고, PD Chat에서 codex로 원고를 씬으로 분해(scenes.json)해 씬 목록을 표시한다.

**Architecture:** stdlib HTTP 백엔드를 작은 모듈(projects/jobs/codex_runner/라우팅)로 분리. 순수 로직은 TDD, codex exec는 subprocess 래퍼(세션 resume + --json 스트리밍 + --output-schema). scene-decompose는 codex 프롬프트(SKILL.md)+JSON Schema로 자체 구현. v4는 참고만.

**Tech Stack:** Python 3.12(표준 라이브러리만), pytest, codex CLI(exec), CEP 패널(HTML/JS).

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python` (pytest 보유). 백엔드 자체는 stdlib라 임의 python3로 기동.

근거 계약: `docs/design/M2_reference_and_contract.md`

---

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/projects.py` | 프로젝트 스캔/로드 (순수 로직) |
| `backend/jobs.py` | job 레지스트리 (생성/로그/상태, 스레드세이프) |
| `backend/codex_runner.py` | codex exec 커맨드 빌드(순수) + 스킬 실행(subprocess) |
| `backend/router.py` | `handle_request()` 순수 라우팅 (소켓 없이 테스트 가능) |
| `backend/app.py` | HTTP 서버 부트스트랩(기존, 라우터 연결로 교체) |
| `skills/scene-decompose/SKILL.md` | codex 스킬 프롬프트 |
| `skills/scene-decompose/scenes.schema.json` | scenes.json JSON Schema (--output-schema) |
| `cep/com.autokairos.pd/index.html` | 탭 UI(연결/프로젝트/채팅) |
| `cep/com.autokairos.pd/js/main.js` | 프로젝트 목록·PD Chat·씬 목록 |
| `tests/test_projects.py` `tests/test_jobs.py` `tests/test_codex_runner.py` `tests/test_router.py` `tests/test_scenes_schema.py` | 단위 테스트 |
| `projects/demo01/final_manuscript.md` | 테스트용 샘플 프로젝트 |

---

## Task 1: 프로젝트 스토어 (projects.py)

**Files:**
- Create: `backend/projects.py`
- Test: `tests/test_projects.py`
- Fixture: `projects/demo01/final_manuscript.md`, `projects/demo01/plan.md`

- [ ] **Step 1: 샘플 프로젝트 픽스처 생성**

`projects/demo01/plan.md`:
```markdown
# 트럼프의 세 번의 파산과 두 번의 백악관

톤: 다큐멘터리
```

`projects/demo01/final_manuscript.md`:
```markdown
카지노가 세 번 무너졌고, 대선에서 한 번 졌습니다. 그런데 백악관에 두 번 들어갔습니다.
실패가 끝이 아니었던 이유를 따라가 봅니다.
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/test_projects.py`:
```python
from pathlib import Path
from backend import projects

ROOT = Path(__file__).resolve().parents[1] / "projects"


def test_scan_finds_demo_project():
    rows = projects.scan_projects(ROOT)
    ids = [r["project_id"] for r in rows]
    assert "demo01" in ids


def test_scan_row_shape():
    row = next(r for r in projects.scan_projects(ROOT) if r["project_id"] == "demo01")
    assert row["title"] == "트럼프의 세 번의 파산과 두 번의 백악관"
    assert row["status"] == "manuscript"          # 원고 있고 scenes 없음
    assert set(["project_id", "title", "status", "updated_at", "artifacts"]) <= set(row)
    assert row["artifacts"]["final_manuscript.md"] is True
    assert row["artifacts"]["scenes.json"] is False


def test_load_project_next_actions():
    info = projects.load_project(ROOT, "demo01")
    assert info["project_id"] == "demo01"
    assert "scene-decompose" in info["next_actions"]
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_projects.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.projects`

- [ ] **Step 4: 구현**

`backend/projects.py`:
```python
"""프로젝트 스토어 — projects/{id}/ 스캔/로드 (순수 로직)."""
from __future__ import annotations

import os
from pathlib import Path

ARTIFACT_FILES = ["plan.md", "final_manuscript.md", "scenes.json", "pd_notebook.md"]


def projects_root() -> Path:
    env = os.environ.get("AK_PROJECTS_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "projects"


def _title(proj_dir: Path) -> str:
    plan = proj_dir / "plan.md"
    if plan.exists():
        for line in plan.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    return proj_dir.name


def _artifacts(proj_dir: Path) -> dict:
    return {f: (proj_dir / f).exists() for f in ARTIFACT_FILES}


def _status(arts: dict) -> str:
    if arts["scenes.json"]:
        return "decomposed"
    if arts["final_manuscript.md"]:
        return "manuscript"
    return "empty"


def _updated_at(proj_dir: Path) -> float:
    mtimes = [p.stat().st_mtime for p in proj_dir.glob("*") if p.is_file()]
    return max(mtimes) if mtimes else proj_dir.stat().st_mtime


def scan_projects(root: Path) -> list[dict]:
    if not root.exists():
        return []
    rows = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        arts = _artifacts(d)
        if not (arts["final_manuscript.md"] or arts["plan.md"]):
            continue
        rows.append({
            "project_id": d.name,
            "title": _title(d),
            "status": _status(arts),
            "updated_at": _updated_at(d),
            "artifacts": arts,
        })
    return rows


def load_project(root: Path, project_id: str) -> dict:
    d = root / project_id
    if not d.is_dir():
        raise FileNotFoundError(f"project not found: {project_id}")
    arts = _artifacts(d)
    next_actions = []
    if arts["final_manuscript.md"] and not arts["scenes.json"]:
        next_actions.append("scene-decompose")
    return {
        "project_id": project_id,
        "title": _title(d),
        "status": _status(arts),
        "artifacts": arts,
        "next_actions": next_actions,
    }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_projects.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 커밋**

```bash
git add backend/projects.py tests/test_projects.py projects/demo01
git commit -m "feat(backend): 프로젝트 스토어 scan/load + demo 픽스처"
```

---

## Task 2: Job 레지스트리 (jobs.py)

**Files:**
- Create: `backend/jobs.py`
- Test: `tests/test_jobs.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_jobs.py`:
```python
from backend.jobs import JobRegistry


def test_create_and_get():
    reg = JobRegistry()
    jid = reg.create("scene-decompose", "demo01")
    assert jid.startswith("job_")
    j = reg.get(jid)
    assert j["status"] == "running"
    assert j["skill_name"] == "scene-decompose"
    assert j["project_id"] == "demo01"
    assert j["logs"] == []


def test_append_log_and_complete():
    reg = JobRegistry()
    jid = reg.create("scene-decompose", "demo01")
    reg.append_log(jid, "line1")
    reg.append_log(jid, "line2")
    reg.set_status(jid, "completed", artifact_paths=["projects/demo01/scenes.json"])
    j = reg.get(jid)
    assert j["logs"] == ["line1", "line2"]
    assert j["status"] == "completed"
    assert j["artifact_paths"] == ["projects/demo01/scenes.json"]


def test_get_unknown_returns_none():
    assert JobRegistry().get("job_999") is None
```

- [ ] **Step 2: 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_jobs.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.jobs`

- [ ] **Step 3: 구현**

`backend/jobs.py`:
```python
"""인메모리 job 레지스트리 (스레드세이프)."""
from __future__ import annotations

import itertools
import threading


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._counter = itertools.count(1)

    def create(self, skill_name: str, project_id: str) -> str:
        with self._lock:
            jid = f"job_{next(self._counter)}"
            self._jobs[jid] = {
                "job_id": jid,
                "skill_name": skill_name,
                "project_id": project_id,
                "status": "running",
                "logs": [],
                "artifact_paths": [],
                "error": None,
            }
            return jid

    def append_log(self, job_id: str, line: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["logs"].append(line)

    def set_status(self, job_id: str, status: str,
                   artifact_paths: list[str] | None = None,
                   error: str | None = None) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if not j:
                return
            j["status"] = status
            if artifact_paths is not None:
                j["artifact_paths"] = artifact_paths
            if error is not None:
                j["error"] = error

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            j = self._jobs.get(job_id)
            return dict(j) if j else None
```

- [ ] **Step 4: 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_jobs.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/jobs.py tests/test_jobs.py
git commit -m "feat(backend): 스레드세이프 job 레지스트리"
```

---

## Task 3: Codex Runner — 커맨드 빌더 (codex_runner.py)

**Files:**
- Create: `backend/codex_runner.py`
- Test: `tests/test_codex_runner.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_codex_runner.py`:
```python
import sys
from backend.codex_runner import build_codex_cmd


def test_build_basic_with_schema_and_output():
    cmd = build_codex_cmd("PROMPT", output_schema="/p/s.json", output_last="/p/out.json")
    assert cmd[0:2] == ["codex", "exec"]
    assert "--skip-git-repo-check" in cmd
    assert "--json" in cmd
    assert cmd[cmd.index("--output-schema") + 1] == "/p/s.json"
    assert cmd[cmd.index("-o") + 1] == "/p/out.json"
    assert cmd[-1] == "PROMPT"


def test_build_resume_session():
    cmd = build_codex_cmd("FOLLOWUP", session_id="abc-123")
    assert cmd[1] == "exec"
    assert "resume" in cmd
    assert "abc-123" in cmd
    assert cmd[-1] == "FOLLOWUP"


def test_no_json_when_disabled():
    cmd = build_codex_cmd("P", json_events=False)
    assert "--json" not in cmd
```

- [ ] **Step 2: 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_codex_runner.py -v`
Expected: FAIL — `ImportError: build_codex_cmd`

- [ ] **Step 3: 구현 (빌더 + 실행 래퍼)**

`backend/codex_runner.py`:
```python
"""codex exec 래퍼 — 커맨드 빌드(순수) + 스킬 실행(subprocess, 스트리밍)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def build_codex_cmd(
    prompt: str,
    *,
    session_id: str | None = None,
    output_schema: str | None = None,
    output_last: str | None = None,
    json_events: bool = True,
    skip_git: bool = True,
) -> list[str]:
    """codex exec 커맨드 리스트. session_id 있으면 resume."""
    cmd = ["codex", "exec"]
    if session_id:
        cmd += ["resume", session_id]
    if skip_git:
        cmd += ["--skip-git-repo-check"]
    if json_events:
        cmd += ["--json"]
    if output_schema:
        cmd += ["--output-schema", output_schema]
    if output_last:
        cmd += ["-o", output_last]
    cmd += [prompt]
    return cmd


def _extract_session_id(json_line: str) -> str | None:
    try:
        evt = json.loads(json_line)
    except ValueError:
        return None
    for key in ("session_id", "sessionId", "conversation_id"):
        if isinstance(evt, dict) and evt.get(key):
            return str(evt[key])
    return None


def run_skill(
    prompt: str,
    cwd: Path,
    *,
    session_id: str | None = None,
    output_schema: str | None = None,
    output_last: str | None = None,
    on_line=None,
) -> dict:
    """codex exec 실행. 각 stdout 라인을 on_line(line)으로 흘림.
    반환: {returncode, session_id, output_last}."""
    cmd = build_codex_cmd(
        prompt, session_id=session_id,
        output_schema=output_schema, output_last=output_last,
    )
    proc = subprocess.Popen(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", bufsize=1,
    )
    found_session = session_id
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if on_line:
            on_line(line)
        if found_session is None:
            sid = _extract_session_id(line)
            if sid:
                found_session = sid
    proc.wait()
    return {
        "returncode": proc.returncode,
        "session_id": found_session,
        "output_last": output_last,
    }
```

- [ ] **Step 4: 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_codex_runner.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/codex_runner.py tests/test_codex_runner.py
git commit -m "feat(backend): codex exec 래퍼 — 커맨드 빌더 + 스트리밍 실행"
```

---

## Task 4: scene-decompose 스킬 (프롬프트 + 스키마)

**Files:**
- Create: `skills/scene-decompose/SKILL.md`
- Create: `skills/scene-decompose/scenes.schema.json`
- Test: `tests/test_scenes_schema.py`

- [ ] **Step 1: JSON Schema 작성**

`skills/scene-decompose/scenes.schema.json`:
```json
{
  "type": "object",
  "required": ["version", "project_id", "total_scenes", "scenes"],
  "properties": {
    "version": { "type": "string" },
    "project_id": { "type": "string" },
    "topic": { "type": "string" },
    "total_scenes": { "type": "integer" },
    "scenes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["sceneNumber", "title", "narration"],
        "properties": {
          "sceneNumber": { "type": "integer" },
          "section": { "type": ["string", "null"] },
          "title": { "type": "string" },
          "narration": { "type": "string" },
          "characters": { "type": "array", "items": { "type": "string" } },
          "visual_summary": { "type": "string" },
          "image_prompt": { "type": "string" },
          "duration_estimate_sec": { "type": "number" }
        }
      }
    }
  }
}
```

- [ ] **Step 2: SKILL.md 작성**

`skills/scene-decompose/SKILL.md`:
```markdown
---
name: scene-decompose
description: final_manuscript.md를 의미·길이·인물 기준으로 씬으로 분해해 scenes.json 생성. narration은 원문 substring 불변.
---

# scene-decompose

원고를 씬 단위로 분해한다. narration은 원고에서 **그대로** 가져온다(재작성·요약 금지).

## Reads
- `final_manuscript.md` (필수)
- `plan.md` (선택 — 제목/톤/섹션)

## Writes
- `scenes.json` (스키마: `scenes.schema.json`)

## 그룹핑 기준 (우선순위)
1. 섹션/문단 경계
2. 의미 전환(도입/전개/전환/마무리)
3. 길이 예산: 씬당 한국어 약 100~250자(상한 ~40초 분량)
4. 핵심 인물(주어) 변화 시 씬 경계

## 씬 필드
- title: 2~6글자 핵심 키워드
- narration: 해당 씬 원고 텍스트(원문 substring, 공백 1칸 join)
- characters: 등장 인물(없으면 빈 배열)
- visual_summary: 한 줄 화면 설명
- image_prompt: 생성/검색용 시각 단서(한국어, 아트스타일 키워드 제외)
- duration_estimate_sec: 한국어 글자수 ÷ 6 추정

## 출력
- `scenes.json` 만 출력. JSON 외 텍스트 금지(--output-schema 강제).

## 금지
- narration 변경(요약/오탈자 수정 포함)
- 연출/레이아웃/이미지 생성 결정(후속 단계)

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 3: 스키마 검증 테스트**

`tests/test_scenes_schema.py`:
```python
import json
from pathlib import Path

SCHEMA = Path(__file__).resolve().parents[1] / "skills/scene-decompose/scenes.schema.json"


def test_schema_is_valid_json_and_requires_scenes():
    s = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert s["type"] == "object"
    assert "scenes" in s["properties"]
    assert "narration" in s["properties"]["scenes"]["items"]["required"]


def test_sample_doc_validates():
    s = json.loads(SCHEMA.read_text(encoding="utf-8"))
    doc = {
        "version": "adobe-0.1", "project_id": "demo01", "topic": "t",
        "total_scenes": 1,
        "scenes": [{"sceneNumber": 1, "title": "도입",
                    "narration": "카지노가 세 번 무너졌습니다."}],
    }
    # 최소 검증: required 키 존재
    for k in s["required"]:
        assert k in doc
    sc = doc["scenes"][0]
    for k in s["properties"]["scenes"]["items"]["required"]:
        assert k in sc
```

- [ ] **Step 4: 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_scenes_schema.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 커밋**

```bash
git add skills/scene-decompose tests/test_scenes_schema.py
git commit -m "feat(skill): scene-decompose 프롬프트 + scenes JSON Schema"
```

---

## Task 5: HTTP 라우팅 (router.py + app.py 교체)

**Files:**
- Create: `backend/router.py`
- Modify: `backend/app.py` (라우터 연결)
- Test: `tests/test_router.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_router.py`:
```python
import json
from pathlib import Path
from backend.router import handle_request
from backend.jobs import JobRegistry

ROOT = Path(__file__).resolve().parents[1] / "projects"


def _ctx():
    return {"root": ROOT, "jobs": JobRegistry()}


def test_health():
    code, body = handle_request("GET", "/health", {}, None, _ctx())
    assert code == 200
    assert body["backend_status"] == "connected"


def test_projects_list():
    code, body = handle_request("GET", "/api/projects", {}, None, _ctx())
    assert code == 200
    assert any(p["project_id"] == "demo01" for p in body["projects"])


def test_project_load():
    code, body = handle_request("POST", "/api/projects/load", {},
                                {"project_id": "demo01"}, _ctx())
    assert code == 200
    assert body["project_id"] == "demo01"


def test_unknown_404():
    code, body = handle_request("GET", "/nope", {}, None, _ctx())
    assert code == 404
```

- [ ] **Step 2: 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_router.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.router`

- [ ] **Step 3: router.py 구현**

`backend/router.py`:
```python
"""순수 라우팅 — (method, path, query, body, ctx) -> (status, dict). 소켓 의존 없음."""
from __future__ import annotations

import shutil
from pathlib import Path

from backend import projects

VERSION = "0.2.0-m2"


def _codex_status() -> str:
    if shutil.which("codex") is None:
        return "not_installed"
    return "ready" if (Path.home() / ".codex" / "auth.json").exists() else "not_authenticated"


def handle_request(method: str, path: str, query: dict, body: dict | None, ctx: dict):
    root: Path = ctx["root"]
    p = path.rstrip("/") or "/"

    if method == "GET" and p == "/health":
        return 200, {"backend_status": "connected", "codex_status": _codex_status(),
                     "version": VERSION}

    if method == "GET" and p == "/api/projects":
        return 200, {"projects": projects.scan_projects(root)}

    if method == "POST" and p == "/api/projects/load":
        pid = (body or {}).get("project_id", "")
        try:
            return 200, projects.load_project(root, pid)
        except FileNotFoundError as e:
            return 404, {"error": str(e)}

    return 404, {"error": "not found", "path": path}
```

- [ ] **Step 4: 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_router.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: app.py를 라우터 연결로 교체**

`backend/app.py` 전체를 다음으로 교체:
```python
"""auto_kairos Adobe PD Assistant — HTTP 서버 (M2).
순수 라우팅은 backend.router.handle_request 가 담당. 이 파일은 소켓/JSON 입출력만."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from backend import projects
from backend.jobs import JobRegistry
from backend.router import handle_request

PORT = int(os.environ.get("AK_BACKEND_PORT", "8765"))
CTX = {"root": projects.projects_root(), "jobs": JobRegistry()}


class Handler(BaseHTTPRequestHandler):
    def _read_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return None

    def _route(self, method: str) -> None:
        u = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(u.query).items()}
        body = self._read_body() if method == "POST" else None
        code, payload = handle_request(method, u.path, query, body, CTX)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):   self._route("GET")    # noqa: E704,N802
    def do_POST(self):  self._route("POST")   # noqa: E704,N802

    def do_OPTIONS(self):  # noqa: N802 (CORS preflight)
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[auto_kairos backend M2] http://127.0.0.1:{PORT}  root={CTX['root']}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: 백엔드 기동 스모크**

Run (백그라운드 아님, 5초 후 Ctrl-C):
`/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m backend.app &` 후
`curl -s http://127.0.0.1:8765/api/projects`
Expected: demo01 포함 JSON. 확인 후 `kill %1`.
(backend 패키지 인식 위해 repo 루트에 빈 `backend/__init__.py` 필요 — 없으면 생성)

- [ ] **Step 7: 커밋**

```bash
git add backend/router.py backend/app.py backend/__init__.py tests/test_router.py
git commit -m "feat(backend): 순수 라우터 + HTTP 서버 (projects/health API)"
```

---

## Task 6: skills/run + jobs API + scene-decompose 라이브 연결

**Files:**
- Modify: `backend/router.py` (`/api/skills/run`, `/api/jobs/{id}`)
- Test: `tests/test_router.py` (라우트 추가 — 스킬 실행은 모킹)

- [ ] **Step 1: 실패 테스트 추가 (codex 실행은 주입으로 모킹)**

`tests/test_router.py`에 추가:
```python
def test_skills_run_returns_job_id(monkeypatch):
    import backend.router as r
    # 실제 codex 대신 가짜 러너 주입
    def fake_run(prompt, cwd, **kw):
        out = kw.get("output_last")
        if out:
            from pathlib import Path as _P
            _P(out).write_text('{"version":"adobe-0.1","project_id":"demo01","total_scenes":0,"scenes":[]}', encoding="utf-8")
        return {"returncode": 0, "session_id": "sess-1", "output_last": out}
    monkeypatch.setattr(r, "run_skill", fake_run)
    ctx = _ctx()
    code, body = handle_request("POST", "/api/skills/run", {},
                                {"project_id": "demo01", "skill_name": "scene-decompose"}, ctx)
    assert code == 200
    jid = body["job_id"]
    # 동기 실행 가정 — 완료 상태
    code2, jbody = handle_request("GET", f"/api/jobs/{jid}", {}, None, ctx)
    assert code2 == 200
    assert jbody["status"] == "completed"
    assert any("scenes.json" in a for a in jbody["artifact_paths"])
```

- [ ] **Step 2: 실패 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_router.py -v`
Expected: FAIL (skills/run 404 또는 run_skill 미정의)

- [ ] **Step 3: router.py 확장**

`backend/router.py` 상단 import에 추가:
```python
from backend.codex_runner import run_skill
```
import 블록 아래 상수 추가:
```python
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
```
`handle_request`의 마지막 `return 404` 직전에 추가:
```python
    if method == "POST" and p == "/api/skills/run":
        b = body or {}
        pid, skill = b.get("project_id", ""), b.get("skill_name", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        jobs = ctx["jobs"]
        jid = jobs.create(skill, pid)
        skill_md = (SKILLS_DIR / skill / "SKILL.md")
        schema = (SKILLS_DIR / skill / "scenes.schema.json")
        out = proj_dir / "scenes.json"
        manuscript = (proj_dir / "final_manuscript.md")
        prompt = (
            skill_md.read_text(encoding="utf-8") if skill_md.exists() else f"skill: {skill}"
        ) + "\n\n## 입력 원고\n" + (
            manuscript.read_text(encoding="utf-8") if manuscript.exists() else ""
        ) + f"\n\nproject_id={pid}. scenes.json 형식으로만 출력."
        result = run_skill(
            prompt, proj_dir,
            output_schema=str(schema) if schema.exists() else None,
            output_last=str(out),
            on_line=lambda ln: jobs.append_log(jid, ln),
        )
        if result["returncode"] == 0 and out.exists():
            jobs.set_status(jid, "completed", artifact_paths=[str(out)])
        else:
            jobs.set_status(jid, "failed", error=f"rc={result['returncode']}")
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"]}

    if method == "GET" and p.startswith("/api/jobs/"):
        jid = p.rsplit("/", 1)[-1]
        j = ctx["jobs"].get(jid)
        if not j:
            return 404, {"error": f"job not found: {jid}"}
        return 200, j
```

> 주: M2는 **동기 실행**(요청 내에서 codex 완료까지 대기)으로 단순화. 스트리밍/비동기는 M2 패널에서 폴링으로 보완, 완전 비동기는 후속.

- [ ] **Step 4: 통과 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_router.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: 라이브 스모크 (codex 실제 호출 — 1회, 크레딧 소비)**

```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m backend.app &
sleep 1
curl -s -X POST http://127.0.0.1:8765/api/skills/run \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"demo01","skill_name":"scene-decompose"}'
sleep 30
cat projects/demo01/scenes.json
kill %1
```
Expected: scenes.json 생성, 씬 배열에 narration이 원고 substring으로 존재.

- [ ] **Step 6: 커밋**

```bash
git add backend/router.py tests/test_router.py projects/demo01/scenes.json
git commit -m "feat(backend): /api/skills/run + /api/jobs — scene-decompose 라이브 연결"
```

---

## Task 7: 패널 — 프로젝트 탭 + PD Chat + 씬 목록

**Files:**
- Modify: `cep/com.autokairos.pd/index.html`
- Modify: `cep/com.autokairos.pd/js/main.js`

- [ ] **Step 1: index.html에 프로젝트/씬 영역 추가**

`cep/com.autokairos.pd/index.html`의 `<body>` 안, 기존 "2) AE 컴프 생성" 블록 **위**에 삽입:
```html
  <div class="label">프로젝트</div>
  <button id="btnProjects">프로젝트 목록 새로고침</button>
  <div class="box" id="projects">—</div>

  <div class="label">씬 분해 (PD)</div>
  <button id="btnDecompose">선택 프로젝트 씬 분해</button>
  <div class="box" id="scenes">—</div>
```

- [ ] **Step 2: main.js에 로직 추가**

`cep/com.autokairos.pd/js/main.js`의 `document.addEventListener("DOMContentLoaded", ...)` **위**에 추가:
```js
var SELECTED_PROJECT = null;

function loadProjects() {
  $("projects").textContent = "불러오는 중...";
  fetch(BACKEND + "/api/projects").then(function (r) { return r.json(); })
    .then(function (j) {
      var rows = j.projects || [];
      if (!rows.length) { $("projects").textContent = "(프로젝트 없음)"; return; }
      $("projects").innerHTML = rows.map(function (p) {
        return '<div><a href="#" data-pid="' + p.project_id + '">'
          + p.project_id + " · " + p.title + " [" + p.status + "]</a></div>";
      }).join("");
      var links = $("projects").querySelectorAll("a[data-pid]");
      for (var i = 0; i < links.length; i++) {
        links[i].addEventListener("click", function (e) {
          e.preventDefault();
          SELECTED_PROJECT = this.getAttribute("data-pid");
          $("projects").querySelectorAll("a").forEach &&
            $("projects").querySelectorAll("a").forEach(function (a) { a.style.fontWeight = "normal"; });
          this.style.fontWeight = "bold";
        });
      }
    })
    .catch(function (e) { $("projects").textContent = "실패: " + e; });
}

function decompose() {
  if (!SELECTED_PROJECT) { $("scenes").textContent = "프로젝트를 먼저 선택하세요."; return; }
  $("scenes").textContent = "씬 분해 중... (codex)";
  fetch(BACKEND + "/api/skills/run", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: SELECTED_PROJECT, skill_name: "scene-decompose" }),
  }).then(function (r) { return r.json(); })
    .then(function (j) {
      if (j.status !== "completed") { $("scenes").textContent = "실패: " + JSON.stringify(j); return; }
      return fetch(BACKEND + "/api/jobs/" + j.job_id).then(function (r) { return r.json(); });
    })
    .then(function () { return renderScenes(); })
    .catch(function (e) { $("scenes").textContent = "오류: " + e; });
}

function renderScenes() {
  // 백엔드가 파일을 만들었으므로 load로 상태만 갱신 + scenes 파일 직접 읽기 대신 요약
  evalScript('(function(){var f=new File(' +
    JSON.stringify("/Users/jleavens_macmini/LocalProjects/auto_kairos_adobe/projects/" + SELECTED_PROJECT + "/scenes.json") +
    ');if(!f.exists)return "no scenes";f.open("r");var c=f.read();f.close();return c;})()')
    .then(function (txt) {
      try {
        var doc = JSON.parse(txt);
        $("scenes").innerHTML = (doc.scenes || []).map(function (s) {
          return "<div>#" + s.sceneNumber + " <b>" + s.title + "</b> — " +
            (s.narration || "").slice(0, 40) + "...</div>";
        }).join("") || "(씬 없음)";
      } catch (e) { $("scenes").textContent = txt; }
    });
}
```
그리고 `DOMContentLoaded` 핸들러 안에 이벤트 바인딩 추가:
```js
  $("btnProjects").addEventListener("click", loadProjects);
  $("btnDecompose").addEventListener("click", decompose);
```

> 주: scenes.json 읽기를 ExtendScript File로 우회(패널 file:// fetch 제약 회피). 경로는 PoC와 동일 하드코딩(M3에서 백엔드 `/api/scenes` 엔드포인트로 정리).

- [ ] **Step 3: 검증 (AE 패널)**

RUNBOOK 절차로 AE 패널 열고:
1. 「프로젝트 목록 새로고침」 → demo01 표시
2. demo01 클릭(굵게) → 「선택 프로젝트 씬 분해」 → 잠시 후 씬 목록(#1 제목 narration) 표시
Expected: 씬 목록이 패널에 렌더됨.

- [ ] **Step 4: 커밋**

```bash
git add cep/com.autokairos.pd/index.html cep/com.autokairos.pd/js/main.js
git commit -m "feat(panel): 프로젝트 목록 + 씬 분해 실행 + 씬 목록 표시"
```

---

## Task 8: M2 통합 검증

**Files:** (검증만)

- [ ] **Step 1: 전체 단위 테스트**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/ -v`
Expected: 전부 PASS (projects/jobs/codex_runner/router/scenes_schema)

- [ ] **Step 2: 백엔드 import 정상**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -c "from backend import app, router, projects, jobs, codex_runner; print('ok')"`
Expected: `ok`

- [ ] **Step 3: M2 exit 기준 (수동, AE)**

demo01 선택 → 씬 분해 → scenes.json 생성 + 패널 씬 목록 표시. 후속(M3에서 다회차 확장) 준비 확인.

- [ ] **Step 4: 최종 커밋(있으면) + 푸시**

```bash
git push
```

---

## Self-Review (작성자 체크)

- **계약 커버리지**: projects 스토어(T1) / jobs(T2) / codex_runner 세션·스트림(T3) / scene-decompose 스킬+스키마(T4) / API 라우팅(T5) / skills.run+jobs+라이브(T6) / 패널(T7). 계약 §2.2~2.8 매핑됨.
- **Placeholder**: 없음 — 모든 코드 스텝에 실제 코드.
- **타입 일관성**: `scan_projects/load_project`, `JobRegistry.create/get/append_log/set_status`, `build_codex_cmd/run_skill`, `handle_request(method,path,query,body,ctx)` — Task 간 시그니처 일치.
- **미반영(의도)**: 완전 비동기/스트리밍 폴링은 M2 동기 단순화로 대체(주석 명시), units 중간층·이미지·승인은 M3+.
