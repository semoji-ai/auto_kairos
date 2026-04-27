# kairos-pd Plan 1: 코어 엔진 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/Volumes/kairos/CC_projects/kairos-pd/` 에 프로젝트를 생성하고, SQLite 기반 태스크 DB + DAG 엔진 + 실패 게이트 + 기본 CLI를 구현한다.

**Architecture:** `core/task_db.py`가 SQLite CRUD를 담당하고, `core/engine.py`가 DAG를 순회하며 태스크를 실행 순서대로 스케줄링한다. `core/gate.py`는 실패 시 retry/skip/abort를 처리하고, `cli.py`는 Click 기반으로 사용자 진입점을 제공한다. 태스크 실제 실행은 이번 플랜에서 stub으로 처리하고 Plan 3에서 에이전트와 연결한다.

**Tech Stack:** Python 3.11+, SQLite (stdlib), Click, pytest

---

## 파일 구조

```
/Volumes/kairos/CC_projects/kairos-pd/
├── core/
│   ├── __init__.py
│   ├── task_db.py        # SQLite CRUD — projects/tasks 테이블
│   ├── engine.py         # DAG 순회 + 태스크 스케줄링
│   ├── gate.py           # 실패 게이트 (retry/skip/abort)
│   └── task_runner.py    # 태스크 실행 (이번 플랜에서 stub)
├── tasks/
│   └── pipeline.json     # 태스크 DAG 선언
├── tests/
│   ├── __init__.py
│   ├── test_task_db.py
│   ├── test_engine.py
│   └── test_gate.py
├── cli.py                # Click CLI
├── pyproject.toml
└── projects.db           # 런타임 생성
```

---

## Task 1: 프로젝트 스캐폴드

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/pyproject.toml`
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/__init__.py`
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tasks/__init__.py` (빈 파일)
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tests/__init__.py`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Volumes/kairos/CC_projects/kairos-pd/{core,tasks,tests}
touch /Volumes/kairos/CC_projects/kairos-pd/core/__init__.py
touch /Volumes/kairos/CC_projects/kairos-pd/tests/__init__.py
```

- [ ] **Step 2: pyproject.toml 작성**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "kairos-pd"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
]

[project.scripts]
kairos-pd = "cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: 의존성 설치**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
pip install -e ".[dev]" 2>/dev/null || pip install click pytest
```

- [ ] **Step 4: 설치 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -c "import click; print('click OK')"
```

Expected: `click OK`

- [ ] **Step 5: git 초기화 및 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git init
echo "projects.db\n__pycache__/\n*.pyc\n.env\noutput/" > .gitignore
git add .
git commit -m "chore: init kairos-pd project scaffold"
```

---

## Task 2: task_db.py — SQLite CRUD

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/task_db.py`
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tests/test_task_db.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/kairos/CC_projects/kairos-pd/tests/test_task_db.py`:

```python
import pytest
import tempfile
import os
from core.task_db import TaskDB

@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    d = TaskDB(db_path)
    d.init()
    return d

def test_create_project(db):
    db.create_project("proj-001", "테스트_프로젝트", {"channel": "이로미즘"})
    p = db.get_project("proj-001")
    assert p["project_id"] == "proj-001"
    assert p["slug"] == "테스트_프로젝트"
    assert p["status"] == "pending"

def test_create_and_get_tasks(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["preflight", "research.skeleton", "research.ingest"])
    tasks = db.get_tasks("proj-001")
    assert len(tasks) == 3
    assert tasks[0]["task_id"] == "preflight"
    assert tasks[0]["status"] == "pending"

def test_update_task_status(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["preflight"])
    db.update_task_status("proj-001", "preflight", "completed")
    tasks = db.get_tasks("proj-001")
    assert tasks[0]["status"] == "completed"

def test_update_task_status_with_error(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["research.skeleton"])
    db.update_task_status("proj-001", "research.skeleton", "failed", error="API 오류")
    tasks = db.get_tasks("proj-001")
    assert tasks[0]["status"] == "failed"
    assert tasks[0]["error"] == "API 오류"

def test_list_projects(db):
    db.create_project("proj-001", "slug1", {})
    db.create_project("proj-002", "slug2", {})
    projects = db.list_projects()
    assert len(projects) == 2
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_task_db.py -v 2>&1 | head -20
```

Expected: FAIL with "ModuleNotFoundError: No module named 'core.task_db'"

- [ ] **Step 3: task_db.py 구현**

`/Volumes/kairos/CC_projects/kairos-pd/core/task_db.py`:

```python
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone


class TaskDB:
    def __init__(self, db_path: str = "projects.db"):
        self.db_path = db_path

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS projects (
                    id         INTEGER PRIMARY KEY,
                    project_id TEXT UNIQUE NOT NULL,
                    slug       TEXT NOT NULL,
                    status     TEXT NOT NULL DEFAULT 'pending',
                    config     TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id          INTEGER PRIMARY KEY,
                    project_id  TEXT NOT NULL,
                    task_id     TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'pending',
                    attempt     INTEGER DEFAULT 1,
                    error       TEXT,
                    started_at  TEXT,
                    finished_at TEXT
                );
            """)

    def create_project(self, project_id: str, slug: str, config: dict):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO projects (project_id, slug, status, config, created_at) VALUES (?, ?, 'pending', ?, ?)",
                (project_id, slug, json.dumps(config, ensure_ascii=False), now)
            )

    def get_project(self, project_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            if not row:
                return None
            d = dict(row)
            if d.get("config"):
                d["config"] = json.loads(d["config"])
            return d

    def list_projects(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def update_project_status(self, project_id: str, status: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE projects SET status = ? WHERE project_id = ?",
                (status, project_id)
            )

    def create_tasks(self, project_id: str, task_ids: list[str]):
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO tasks (project_id, task_id, status) VALUES (?, ?, 'pending')",
                [(project_id, tid) for tid in task_ids]
            )

    def get_tasks(self, project_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY id",
                (project_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_task(self, project_id: str, task_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? AND task_id = ?",
                (project_id, task_id)
            ).fetchone()
            return dict(row) if row else None

    def update_task_status(self, project_id: str, task_id: str, status: str, error: str = None):
        now = datetime.now(timezone.utc).isoformat()
        started_at = now if status == "running" else None
        finished_at = now if status in ("completed", "failed", "skipped") else None
        with self._conn() as conn:
            conn.execute(
                """UPDATE tasks SET status = ?, error = ?,
                   started_at = COALESCE(started_at, ?),
                   finished_at = ?
                   WHERE project_id = ? AND task_id = ?""",
                (status, error, started_at, finished_at, project_id, task_id)
            )

    def increment_attempt(self, project_id: str, task_id: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE tasks SET attempt = attempt + 1, status = 'pending', error = NULL, started_at = NULL, finished_at = NULL WHERE project_id = ? AND task_id = ?",
                (project_id, task_id)
            )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_task_db.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/task_db.py tests/test_task_db.py
git commit -m "feat: add TaskDB SQLite CRUD"
```

---

## Task 3: pipeline.json — 태스크 DAG 선언

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tasks/pipeline.json`

- [ ] **Step 1: pipeline.json 작성**

`/Volumes/kairos/CC_projects/kairos-pd/tasks/pipeline.json`:

```json
{
  "version": "1.0",
  "description": "kairos-pd 태스크 DAG — v3 파이프라인 태스크화",
  "tasks": [
    {
      "id": "preflight",
      "name": "환경 검증",
      "type": "module",
      "module": "preflight",
      "depends_on": []
    },
    {
      "id": "research.skeleton",
      "name": "골격 리서치",
      "type": "module",
      "module": "skeleton_from_vault",
      "depends_on": ["preflight"],
      "inputs": ["editorial_brief.json"],
      "outputs": ["skeleton.json"]
    },
    {
      "id": "research.strategy",
      "name": "리서치 전략",
      "type": "agent",
      "agent": "research-strategist",
      "depends_on": ["research.skeleton"],
      "inputs": ["editorial_brief.json", "skeleton.json"],
      "outputs": ["outline.json", "research_queries.json"]
    },
    {
      "id": "research.ingest",
      "name": "소스 수집",
      "type": "module",
      "module": "source_ingest",
      "depends_on": ["research.strategy"],
      "inputs": ["research_queries.json"],
      "outputs": ["research/"]
    },
    {
      "id": "research.projection",
      "name": "챕터 프로젝션",
      "type": "module",
      "module": "chapter_projection",
      "depends_on": ["research.strategy"],
      "inputs": ["outline.json"],
      "outputs": ["chapter_facts/"]
    },
    {
      "id": "manuscript.draft",
      "name": "초고 작성",
      "type": "agent",
      "agent": "draft-writer",
      "depends_on": ["research.ingest", "research.projection"],
      "inputs": ["outline.json", "chapter_facts/"],
      "outputs": ["draft.md"]
    },
    {
      "id": "manuscript.target",
      "name": "타겟 리서치",
      "type": "agent",
      "agent": "targeted-researcher",
      "depends_on": ["manuscript.draft"],
      "inputs": ["draft.md"],
      "outputs": ["targeted_claims.json"]
    },
    {
      "id": "manuscript.write",
      "name": "최종 원고",
      "type": "agent",
      "agent": "script-director",
      "mode": "manuscript",
      "depends_on": ["manuscript.target"],
      "inputs": ["draft.md", "targeted_claims.json"],
      "outputs": ["final_manuscript.md"]
    },
    {
      "id": "scene.chapters",
      "name": "씬 분할 + 연출",
      "type": "agent",
      "agent": "script-director",
      "mode": "chapters",
      "depends_on": ["manuscript.write"],
      "inputs": ["final_manuscript.md", "outline.json"],
      "outputs": ["scene_specs.json"],
      "parallel": true
    },
    {
      "id": "scene.data",
      "name": "데이터 매핑",
      "type": "agent",
      "agent": "data-mapper",
      "depends_on": ["scene.chapters"],
      "inputs": ["scene_specs.json"],
      "outputs": ["scene_specs.json"]
    },
    {
      "id": "scene.review",
      "name": "래칫 리뷰",
      "type": "agent",
      "agent": "script-reviewer",
      "depends_on": ["scene.data"],
      "inputs": ["scene_specs.json"],
      "outputs": ["review_feedback.json"]
    },
    {
      "id": "assembly",
      "name": "에셋 조립 + 렌더링",
      "type": "agent",
      "agent": "assembly-director",
      "depends_on": ["scene.review"],
      "inputs": ["scene_specs.json"],
      "outputs": ["*.mp4"]
    },
    {
      "id": "release",
      "name": "릴리즈 패키지",
      "type": "agent",
      "agent": "release-manager",
      "depends_on": ["assembly"],
      "inputs": ["scene_specs.json"],
      "outputs": ["upload_info.json"]
    }
  ]
}
```

- [ ] **Step 2: JSON 유효성 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -c "import json; d=json.load(open('tasks/pipeline.json')); print(f'태스크 {len(d[\"tasks\"])}개 OK')"
```

Expected: `태스크 13개 OK`

- [ ] **Step 3: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add tasks/pipeline.json
git commit -m "feat: add pipeline.json task DAG"
```

---

## Task 4: engine.py — DAG 엔진

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/engine.py`
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tests/test_engine.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/kairos/CC_projects/kairos-pd/tests/test_engine.py`:

```python
import pytest
from core.engine import DAGEngine

SIMPLE_DAG = [
    {"id": "a", "depends_on": []},
    {"id": "b", "depends_on": ["a"]},
    {"id": "c", "depends_on": ["a"]},
    {"id": "d", "depends_on": ["b", "c"]},
]

def test_ready_tasks_initial():
    engine = DAGEngine(SIMPLE_DAG)
    statuses = {"a": "pending", "b": "pending", "c": "pending", "d": "pending"}
    ready = engine.get_ready_tasks(statuses)
    assert ready == ["a"]

def test_ready_tasks_after_a_completed():
    engine = DAGEngine(SIMPLE_DAG)
    statuses = {"a": "completed", "b": "pending", "c": "pending", "d": "pending"}
    ready = engine.get_ready_tasks(statuses)
    assert set(ready) == {"b", "c"}

def test_ready_tasks_skipped_counts_as_satisfied():
    engine = DAGEngine(SIMPLE_DAG)
    statuses = {"a": "skipped", "b": "pending", "c": "pending", "d": "pending"}
    ready = engine.get_ready_tasks(statuses)
    assert set(ready) == {"b", "c"}

def test_ready_tasks_blocked_by_failed():
    engine = DAGEngine(SIMPLE_DAG)
    statuses = {"a": "failed", "b": "pending", "c": "pending", "d": "pending"}
    ready = engine.get_ready_tasks(statuses)
    assert ready == []

def test_all_completed():
    engine = DAGEngine(SIMPLE_DAG)
    statuses = {"a": "completed", "b": "completed", "c": "completed", "d": "completed"}
    assert engine.is_complete(statuses) is True

def test_not_complete_with_pending():
    engine = DAGEngine(SIMPLE_DAG)
    statuses = {"a": "completed", "b": "pending", "c": "pending", "d": "pending"}
    assert engine.is_complete(statuses) is False

def test_get_task():
    engine = DAGEngine(SIMPLE_DAG)
    task = engine.get_task("b")
    assert task["id"] == "b"
    assert task["depends_on"] == ["a"]
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_engine.py -v 2>&1 | head -10
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: engine.py 구현**

`/Volumes/kairos/CC_projects/kairos-pd/core/engine.py`:

```python
from __future__ import annotations


SATISFIED = {"completed", "skipped"}


class DAGEngine:
    def __init__(self, tasks: list[dict]):
        self._tasks = {t["id"]: t for t in tasks}

    def get_task(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    def get_ready_tasks(self, statuses: dict[str, str]) -> list[str]:
        """depends_on이 모두 satisfied인 pending 태스크 목록 반환."""
        ready = []
        for task_id, task in self._tasks.items():
            if statuses.get(task_id) != "pending":
                continue
            deps = task.get("depends_on", [])
            if all(statuses.get(dep) in SATISFIED for dep in deps):
                ready.append(task_id)
        return ready

    def is_complete(self, statuses: dict[str, str]) -> bool:
        """모든 태스크가 completed 또는 skipped이면 True."""
        return all(
            statuses.get(tid) in SATISFIED
            for tid in self._tasks
        )

    def is_blocked(self, statuses: dict[str, str]) -> bool:
        """pending 태스크가 있지만 ready가 없으면 blocked."""
        has_pending = any(s == "pending" for s in statuses.values())
        if not has_pending:
            return False
        return len(self.get_ready_tasks(statuses)) == 0

    @classmethod
    def from_pipeline_json(cls, pipeline: dict) -> "DAGEngine":
        return cls(pipeline["tasks"])
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_engine.py -v
```

Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/engine.py tests/test_engine.py
git commit -m "feat: add DAGEngine for task scheduling"
```

---

## Task 5: gate.py — 실패 게이트

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/gate.py`
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tests/test_gate.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/kairos/CC_projects/kairos-pd/tests/test_gate.py`:

```python
import pytest
from unittest.mock import patch
from core.gate import FailureGate, GateDecision

def test_retry_decision():
    gate = FailureGate(interactive=False)
    with patch("builtins.input", return_value="r"):
        decision = gate.ask("research.ingest", "API 오류")
    assert decision == GateDecision.RETRY

def test_skip_decision():
    gate = FailureGate(interactive=False)
    with patch("builtins.input", return_value="s"):
        decision = gate.ask("research.ingest", "API 오류")
    assert decision == GateDecision.SKIP

def test_abort_decision():
    gate = FailureGate(interactive=False)
    with patch("builtins.input", return_value="a"):
        decision = gate.ask("research.ingest", "API 오류")
    assert decision == GateDecision.ABORT

def test_invalid_then_valid_input():
    gate = FailureGate(interactive=False)
    with patch("builtins.input", side_effect=["x", "y", "s"]):
        decision = gate.ask("research.ingest", "오류")
    assert decision == GateDecision.SKIP

def test_non_interactive_defaults_to_abort():
    gate = FailureGate(interactive=False, default=GateDecision.ABORT)
    with patch("builtins.input", side_effect=EOFError):
        decision = gate.ask("research.ingest", "오류")
    assert decision == GateDecision.ABORT
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_gate.py -v 2>&1 | head -10
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: gate.py 구현**

`/Volumes/kairos/CC_projects/kairos-pd/core/gate.py`:

```python
from enum import Enum


class GateDecision(Enum):
    RETRY = "retry"
    SKIP = "skip"
    ABORT = "abort"


class FailureGate:
    def __init__(self, interactive: bool = True, default: GateDecision = GateDecision.ABORT):
        self.interactive = interactive
        self.default = default

    def ask(self, task_id: str, error: str) -> GateDecision:
        print(f"\n{'='*50}")
        print(f"[FAILED] task: {task_id}")
        print(f"Error: {error}")
        print(f"{'='*50}")

        mapping = {"r": GateDecision.RETRY, "s": GateDecision.SKIP, "a": GateDecision.ABORT}

        while True:
            try:
                choice = input("> (r)etry  (s)kip  (a)bort ? ").strip().lower()
                if choice in mapping:
                    return mapping[choice]
                print("r, s, a 중 하나를 입력하세요.")
            except (EOFError, KeyboardInterrupt):
                print(f"\n입력 불가 — 기본값 {self.default.value} 적용")
                return self.default
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_gate.py -v
```

Expected: 5 passed

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/gate.py tests/test_gate.py
git commit -m "feat: add FailureGate for retry/skip/abort"
```

---

## Task 6: task_runner.py — 실행 stub

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/task_runner.py`

- [ ] **Step 1: task_runner.py stub 작성**

`/Volumes/kairos/CC_projects/kairos-pd/core/task_runner.py`:

```python
"""
태스크 실행 담당. Plan 3에서 실제 에이전트/모듈과 연결.
현재는 stub — 태스크를 즉시 completed로 처리.
"""
from __future__ import annotations
from pathlib import Path


class TaskRunner:
    def __init__(self, project_dir: Path, config: dict):
        self.project_dir = project_dir
        self.config = config

    def run(self, task: dict) -> tuple[bool, str | None]:
        """
        태스크를 실행한다.
        반환: (success: bool, error: str | None)
        """
        task_id = task["id"]
        print(f"  [RUN] {task_id} ... (stub — Plan 3에서 실제 연결)")
        # Plan 3에서 type에 따라 module/agent 실행으로 교체
        return True, None
```

- [ ] **Step 2: import 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -c "from core.task_runner import TaskRunner; print('TaskRunner OK')"
```

Expected: `TaskRunner OK`

- [ ] **Step 3: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/task_runner.py
git commit -m "feat: add TaskRunner stub (Plan 3에서 에이전트 연결)"
```

---

## Task 7: 통합 실행 루프 (engine + db + gate + runner)

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/runner.py`

- [ ] **Step 1: runner.py 작성**

`/Volumes/kairos/CC_projects/kairos-pd/core/runner.py`:

```python
"""
프로젝트 실행 루프 — DAG 엔진 + DB + 게이트 + 태스크 러너 통합.
"""
from __future__ import annotations
import json
from pathlib import Path
from core.task_db import TaskDB
from core.engine import DAGEngine
from core.gate import FailureGate, GateDecision
from core.task_runner import TaskRunner


def load_pipeline(pipeline_path: Path) -> dict:
    return json.loads(pipeline_path.read_text(encoding="utf-8"))


class ProjectRunner:
    def __init__(self, db: TaskDB, pipeline_path: Path, interactive: bool = True):
        self.db = db
        self.pipeline = load_pipeline(pipeline_path)
        self.dag = DAGEngine.from_pipeline_json(self.pipeline)
        self.gate = FailureGate(interactive=interactive)

    def run(self, project_id: str, only: str = None, from_task: str = None):
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 {project_id} 없음")

        project_dir = Path(f"output/{project_id}_{project['slug']}")
        project_dir.mkdir(parents=True, exist_ok=True)
        runner = TaskRunner(project_dir, project.get("config") or {})

        self.db.update_project_status(project_id, "running")
        print(f"\n[kairos-pd] 프로젝트 시작: {project['slug']} ({project_id})")

        while True:
            statuses = {t["task_id"]: t["status"] for t in self.db.get_tasks(project_id)}

            if self.dag.is_complete(statuses):
                self.db.update_project_status(project_id, "completed")
                print("\n[kairos-pd] 완료!")
                break

            if self.dag.is_blocked(statuses):
                self.db.update_project_status(project_id, "failed")
                print("\n[kairos-pd] 모든 태스크가 블록됨 — 중단")
                break

            ready = self.dag.get_ready_tasks(statuses)

            # --only 옵션: 해당 태스크만 실행
            if only:
                ready = [t for t in ready if t == only]
                if not ready:
                    print(f"[kairos-pd] {only} 태스크는 아직 실행 불가 (의존성 미충족)")
                    break

            # --from 옵션: 해당 태스크 이전은 completed로 처리
            if from_task:
                task_ids = [t["id"] for t in self.pipeline["tasks"]]
                from_idx = task_ids.index(from_task) if from_task in task_ids else 0
                for tid in task_ids[:from_idx]:
                    if statuses.get(tid) == "pending":
                        self.db.update_task_status(project_id, tid, "skipped")
                from_task = None
                continue

            for task_id in ready:
                task = self.dag.get_task(task_id)
                self.db.update_task_status(project_id, task_id, "running")
                print(f"\n  → {task_id}: {task.get('name', '')}")

                success, error = runner.run(task)

                if success:
                    self.db.update_task_status(project_id, task_id, "completed")
                    print(f"  ✓ {task_id}")
                else:
                    self.db.update_task_status(project_id, task_id, "failed", error=error)
                    decision = self.gate.ask(task_id, error or "알 수 없는 오류")

                    if decision == GateDecision.RETRY:
                        self.db.increment_attempt(project_id, task_id)
                    elif decision == GateDecision.SKIP:
                        self.db.update_task_status(project_id, task_id, "skipped")
                    else:  # ABORT
                        self.db.update_project_status(project_id, "aborted")
                        print("\n[kairos-pd] 중단됨")
                        return
```

- [ ] **Step 2: import 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -c "from core.runner import ProjectRunner; print('ProjectRunner OK')"
```

Expected: `ProjectRunner OK`

- [ ] **Step 3: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/runner.py
git commit -m "feat: add ProjectRunner integration loop"
```

---

## Task 8: cli.py — Click CLI

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/cli.py`

- [ ] **Step 1: cli.py 작성**

`/Volumes/kairos/CC_projects/kairos-pd/cli.py`:

```python
import click
import uuid
import json
from pathlib import Path
from core.task_db import TaskDB
from core.runner import ProjectRunner

DB_PATH = "projects.db"
PIPELINE_PATH = Path("tasks/pipeline.json")


def get_db() -> TaskDB:
    db = TaskDB(DB_PATH)
    db.init()
    return db


@click.group()
def main():
    """kairos-pd — 태스크 기반 영상 제작 파이프라인"""
    pass


@main.command()
@click.argument("topic", required=False, default="")
def new(topic):
    """기획 인터뷰 시작 (Plan 2에서 인터뷰 플로우 추가)"""
    db = get_db()
    project_id = str(uuid.uuid4())
    slug = topic.replace(" ", "_") if topic else "untitled"

    # Plan 2에서 인터뷰 플로우로 교체
    config = {"topic_hint": topic, "channel": "", "duration_minutes": 10}

    db.create_project(project_id, slug, config)
    pipeline = json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
    task_ids = [t["id"] for t in pipeline["tasks"]]
    db.create_tasks(project_id, task_ids)

    click.echo(f"\n프로젝트 생성됨:")
    click.echo(f"  ID:   {project_id}")
    click.echo(f"  Slug: {slug}")
    click.echo(f"\n실행하려면:")
    click.echo(f"  kairos-pd run --project {project_id}")


@main.command()
@click.option("--project", required=True, help="project_id")
@click.option("--only", default=None, help="단일 태스크만 실행")
@click.option("--from", "from_task", default=None, help="특정 태스크부터 실행")
def run(project, only, from_task):
    """프로젝트 실행"""
    db = get_db()
    runner = ProjectRunner(db, PIPELINE_PATH, interactive=True)
    runner.run(project, only=only, from_task=from_task)


@main.command()
@click.option("--project", required=True, help="project_id")
@click.option("--task", required=True, help="재실행할 task_id")
def retry(project, task):
    """실패한 태스크 재시도"""
    db = get_db()
    db.increment_attempt(project, task)
    click.echo(f"재시도 준비: {task}")
    runner = ProjectRunner(db, PIPELINE_PATH, interactive=True)
    runner.run(project, only=task)


@main.command()
@click.option("--project", required=True, help="project_id")
@click.option("--task", required=True, help="스킵할 task_id")
def skip(project, task):
    """태스크 스킵"""
    db = get_db()
    db.update_task_status(project, task, "skipped")
    click.echo(f"스킵됨: {task}")


@main.command()
@click.option("--project", default=None, help="특정 프로젝트 상태")
def status(project):
    """프로젝트 상태 확인"""
    db = get_db()
    if project:
        p = db.get_project(project)
        if not p:
            click.echo(f"프로젝트 {project} 없음")
            return
        click.echo(f"\n{p['slug']} ({p['project_id']})")
        click.echo(f"상태: {p['status']}")
        click.echo("\n태스크:")
        for t in db.get_tasks(project):
            icon = {"completed": "✓", "failed": "✗", "running": "→", "skipped": "○", "pending": "·"}.get(t["status"], "?")
            err = f" — {t['error']}" if t.get("error") else ""
            click.echo(f"  {icon} {t['task_id']}{err}")
    else:
        projects = db.list_projects()
        if not projects:
            click.echo("프로젝트 없음")
            return
        for p in projects:
            click.echo(f"  [{p['status']}] {p['slug']} ({p['project_id'][:8]}...)")


@main.command("list")
def list_projects():
    """프로젝트 목록"""
    db = get_db()
    projects = db.list_projects()
    if not projects:
        click.echo("프로젝트 없음")
        return
    for p in projects:
        click.echo(f"  [{p['status']:10}] {p['slug']:30} {p['project_id'][:8]}...")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: CLI 동작 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python cli.py --help
```

Expected:
```
Usage: cli.py [OPTIONS] COMMAND [ARGS]...
  kairos-pd — 태스크 기반 영상 제작 파이프라인
Commands:
  new     기획 인터뷰 시작
  run     프로젝트 실행
  retry   실패한 태스크 재시도
  skip    태스크 스킵
  status  프로젝트 상태 확인
  list    프로젝트 목록
```

- [ ] **Step 3: 엔드투엔드 동작 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python cli.py new "테스트 영상"
# 출력된 project_id 복사
python cli.py run --project <복사한_project_id>
python cli.py status --project <복사한_project_id>
```

Expected: 13개 태스크 모두 ✓ completed (stub이므로 즉시 완료)

- [ ] **Step 4: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add cli.py
git commit -m "feat: add Click CLI (new/run/retry/skip/status/list)"
```

---

## Task 9: 전체 테스트 실행 및 최종 커밋

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/ -v
```

Expected: 17 passed (task_db: 5, engine: 7, gate: 5)

- [ ] **Step 2: pip install 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
pip install -e .
kairos-pd --help
```

Expected: CLI 도움말 표시

- [ ] **Step 3: 최종 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add .
git commit -m "feat: kairos-pd Plan 1 완료 — 코어 엔진 + CLI"
```

---

## Self-Review

### Spec Coverage

| 스펙 요구사항 | 구현 태스크 |
|-------------|-----------|
| project_id(uuid) + slug 조합 | Task 2, 8 |
| DAG 기반 실행 + 독립 재실행 | Task 4, 7 |
| SQLite 상태 저장 | Task 2 |
| 실패 게이트 (retry/skip/abort) | Task 5, 7 |
| skipped = 의존성 충족 | Task 4 |
| 태스크 DAG 선언 (pipeline.json) | Task 3 |
| CLI (new/run/retry/skip/status/list) | Task 8 |
| --only / --from 옵션 | Task 7, 8 |
| 터미널 실패 알림 | Task 5 |

### Placeholder 없음 ✅
### Type Consistency ✅ — TaskDB, DAGEngine, FailureGate, ProjectRunner, TaskRunner 모두 일관된 인터페이스
