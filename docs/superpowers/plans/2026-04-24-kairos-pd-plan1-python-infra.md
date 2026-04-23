# kairos-pd Plan 1: Python 인프라 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/Volumes/kairos/CC_projects/kairos-pd/` 에 프로젝트를 생성하고, SQLite 태스크 DB + CLI 진입점 + 플러그인 매니저를 구현한다.

**Architecture:** Python은 세 가지만 담당한다 — SQLite CRUD(`task_db.py`), Click CLI 진입점(`cli.py`), 플러그인 동기화(`plugin_manager.py`). DAG 순회·태스크 실행·실패 게이트는 Plan 2에서 Claude Orchestrator Agent가 담당하므로 `engine.py`, `gate.py`, `runner.py`는 이 플랜에 없다.

**Tech Stack:** Python 3.11+, SQLite (stdlib), Click 8.x, pytest

---

## 파일 맵

### Create
- `/Volumes/kairos/CC_projects/kairos-pd/pyproject.toml`
- `/Volumes/kairos/CC_projects/kairos-pd/core/__init__.py`
- `/Volumes/kairos/CC_projects/kairos-pd/core/task_db.py` — SQLite CRUD
- `/Volumes/kairos/CC_projects/kairos-pd/core/plugin_manager.py` — 플러그인 update/status
- `/Volumes/kairos/CC_projects/kairos-pd/cli.py` — Click CLI
- `/Volumes/kairos/CC_projects/kairos-pd/tests/__init__.py`
- `/Volumes/kairos/CC_projects/kairos-pd/tests/test_task_db.py`
- `/Volumes/kairos/CC_projects/kairos-pd/tests/test_plugin_manager.py`
- `/Volumes/kairos/CC_projects/kairos-pd/plugins/.gitkeep`
- `/Volumes/kairos/CC_projects/kairos-pd/styles/.gitkeep`
- `/Volumes/kairos/CC_projects/kairos-pd/skills/.gitkeep`
- `/Volumes/kairos/CC_projects/kairos-pd/tasks/.gitkeep`

---

## Task 1: 프로젝트 스캐폴드

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/pyproject.toml`
- Create: 디렉토리 구조 전체

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Volumes/kairos/CC_projects/kairos-pd/{core,tests,plugins,styles,skills,tasks,output}
touch /Volumes/kairos/CC_projects/kairos-pd/core/__init__.py
touch /Volumes/kairos/CC_projects/kairos-pd/tests/__init__.py
touch /Volumes/kairos/CC_projects/kairos-pd/plugins/.gitkeep
touch /Volumes/kairos/CC_projects/kairos-pd/styles/.gitkeep
touch /Volumes/kairos/CC_projects/kairos-pd/skills/.gitkeep
touch /Volumes/kairos/CC_projects/kairos-pd/tasks/.gitkeep
```

- [ ] **Step 2: pyproject.toml 작성**

`/Volumes/kairos/CC_projects/kairos-pd/pyproject.toml`:

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

[project.optional-dependencies]
dev = ["pytest>=7"]

[project.scripts]
kairos-pd = "cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: 의존성 설치**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
pip install click pytest
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
printf "projects.db\n__pycache__/\n*.pyc\n.env\noutput/\n" > .gitignore
git add .
git commit -m "chore: init kairos-pd scaffold"
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
from core.task_db import TaskDB


@pytest.fixture
def db(tmp_path):
    d = TaskDB(str(tmp_path / "test.db"))
    d.init()
    return d


def test_create_and_get_project(db):
    db.create_project("proj-001", "포켓몬_30주년", {"channel": "이로미즘"})
    p = db.get_project("proj-001")
    assert p["project_id"] == "proj-001"
    assert p["slug"] == "포켓몬_30주년"
    assert p["status"] == "pending"
    assert p["config"]["channel"] == "이로미즘"


def test_create_and_get_tasks(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["preflight", "research.skeleton", "research.strategy"])
    tasks = db.get_tasks("proj-001")
    assert len(tasks) == 3
    assert tasks[0]["task_id"] == "preflight"
    assert tasks[0]["status"] == "pending"


def test_update_task_status_completed(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["preflight"])
    db.update_task_status("proj-001", "preflight", "completed")
    t = db.get_task("proj-001", "preflight")
    assert t["status"] == "completed"
    assert t["finished_at"] is not None


def test_update_task_status_failed_with_error(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["research.skeleton"])
    db.update_task_status("proj-001", "research.skeleton", "failed", error="API 오류")
    t = db.get_task("proj-001", "research.skeleton")
    assert t["status"] == "failed"
    assert t["error"] == "API 오류"


def test_increment_attempt_resets_to_pending(db):
    db.create_project("proj-001", "slug", {})
    db.create_tasks("proj-001", ["research.ingest"])
    db.update_task_status("proj-001", "research.ingest", "failed", error="timeout")
    db.increment_attempt("proj-001", "research.ingest")
    t = db.get_task("proj-001", "research.ingest")
    assert t["status"] == "pending"
    assert t["attempt"] == 2
    assert t["error"] is None


def test_list_projects(db):
    db.create_project("proj-001", "slug1", {})
    db.create_project("proj-002", "slug2", {})
    projects = db.list_projects()
    assert len(projects) == 2


def test_update_project_status(db):
    db.create_project("proj-001", "slug", {})
    db.update_project_status("proj-001", "running")
    p = db.get_project("proj-001")
    assert p["status"] == "running"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_task_db.py -v 2>&1 | head -15
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.task_db'`

- [ ] **Step 3: task_db.py 구현**

`/Volumes/kairos/CC_projects/kairos-pd/core/task_db.py`:

```python
import sqlite3
import json
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

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def create_project(self, project_id: str, slug: str, config: dict):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO projects (project_id, slug, status, config, created_at) VALUES (?, ?, 'pending', ?, ?)",
                (project_id, slug, json.dumps(config, ensure_ascii=False), self._now()),
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
            result = []
            for r in rows:
                d = dict(r)
                if d.get("config"):
                    d["config"] = json.loads(d["config"])
                result.append(d)
            return result

    def update_project_status(self, project_id: str, status: str):
        with self._conn() as conn:
            conn.execute(
                "UPDATE projects SET status = ? WHERE project_id = ?",
                (status, project_id),
            )

    def create_tasks(self, project_id: str, task_ids: list[str]):
        with self._conn() as conn:
            conn.executemany(
                "INSERT INTO tasks (project_id, task_id, status) VALUES (?, ?, 'pending')",
                [(project_id, tid) for tid in task_ids],
            )

    def get_tasks(self, project_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? ORDER BY id",
                (project_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_task(self, project_id: str, task_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE project_id = ? AND task_id = ?",
                (project_id, task_id),
            ).fetchone()
            return dict(row) if row else None

    def update_task_status(self, project_id: str, task_id: str, status: str, error: str = None):
        now = self._now()
        started_at = now if status == "running" else None
        finished_at = now if status in ("completed", "failed", "skipped") else None
        with self._conn() as conn:
            conn.execute(
                """UPDATE tasks SET status = ?, error = ?,
                   started_at = COALESCE(started_at, ?),
                   finished_at = ?
                   WHERE project_id = ? AND task_id = ?""",
                (status, error, started_at, finished_at, project_id, task_id),
            )

    def increment_attempt(self, project_id: str, task_id: str):
        with self._conn() as conn:
            conn.execute(
                """UPDATE tasks
                   SET attempt = attempt + 1, status = 'pending', error = NULL,
                       started_at = NULL, finished_at = NULL
                   WHERE project_id = ? AND task_id = ?""",
                (project_id, task_id),
            )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_task_db.py -v
```

Expected: 7 passed

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/task_db.py tests/test_task_db.py
git commit -m "feat: add TaskDB SQLite CRUD"
```

---

## Task 3: plugin_manager.py — 플러그인 동기화

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/core/plugin_manager.py`
- Create: `/Volumes/kairos/CC_projects/kairos-pd/tests/test_plugin_manager.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/kairos/CC_projects/kairos-pd/tests/test_plugin_manager.py`:

```python
import json
import pytest
from pathlib import Path
from core.plugin_manager import PluginManager


@pytest.fixture
def tmp_plugin_root(tmp_path):
    return tmp_path / "plugins"


@pytest.fixture
def source_skill(tmp_path):
    src = tmp_path / "source" / "fontagent" / "SKILL.md"
    src.parent.mkdir(parents=True)
    src.write_text("# FontAgent SKILL\nv1 content", encoding="utf-8")
    return src


def test_install_creates_plugin_dir(tmp_plugin_root, source_skill):
    pm = PluginManager(tmp_plugin_root)
    pm.install("fontagent", source_skill)

    skill_path = tmp_plugin_root / "fontagent" / "SKILL.md"
    version_path = tmp_plugin_root / "fontagent" / "version.json"

    assert skill_path.exists()
    assert skill_path.read_text(encoding="utf-8") == "# FontAgent SKILL\nv1 content"
    assert version_path.exists()

    version = json.loads(version_path.read_text(encoding="utf-8"))
    assert version["plugin"] == "fontagent"
    assert version["source_path"] == str(source_skill)
    assert "synced_at" in version


def test_update_copies_latest_content(tmp_plugin_root, source_skill):
    pm = PluginManager(tmp_plugin_root)
    pm.install("fontagent", source_skill)

    source_skill.write_text("# FontAgent SKILL\nv2 content", encoding="utf-8")
    pm.update("fontagent")

    skill_path = tmp_plugin_root / "fontagent" / "SKILL.md"
    assert skill_path.read_text(encoding="utf-8") == "# FontAgent SKILL\nv2 content"


def test_list_returns_installed_plugins(tmp_plugin_root, source_skill):
    pm = PluginManager(tmp_plugin_root)
    pm.install("fontagent", source_skill)

    plugins = pm.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["plugin"] == "fontagent"


def test_status_detects_drift(tmp_plugin_root, source_skill):
    pm = PluginManager(tmp_plugin_root)
    pm.install("fontagent", source_skill)

    source_skill.write_text("# FontAgent SKILL\nv2 content", encoding="utf-8")
    statuses = pm.status()

    assert statuses[0]["plugin"] == "fontagent"
    assert statuses[0]["drift"] is True


def test_status_no_drift_when_synced(tmp_plugin_root, source_skill):
    pm = PluginManager(tmp_plugin_root)
    pm.install("fontagent", source_skill)

    statuses = pm.status()
    assert statuses[0]["drift"] is False


def test_update_unknown_plugin_raises(tmp_plugin_root):
    pm = PluginManager(tmp_plugin_root)
    with pytest.raises(FileNotFoundError):
        pm.update("nonexistent")
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_plugin_manager.py -v 2>&1 | head -15
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.plugin_manager'`

- [ ] **Step 3: plugin_manager.py 구현**

`/Volumes/kairos/CC_projects/kairos-pd/core/plugin_manager.py`:

```python
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


class PluginManager:
    def __init__(self, plugins_root: Path):
        self.root = Path(plugins_root)

    def _version_path(self, name: str) -> Path:
        return self.root / name / "version.json"

    def _skill_path(self, name: str) -> Path:
        return self.root / name / "SKILL.md"

    def install(self, name: str, source_skill_path: Path):
        dest_dir = self.root / name
        dest_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_skill_path, dest_dir / "SKILL.md")

        version = {
            "plugin": name,
            "source_path": str(source_skill_path),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
        self._version_path(name).write_text(
            json.dumps(version, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def update(self, name: str):
        version_path = self._version_path(name)
        if not version_path.exists():
            raise FileNotFoundError(f"플러그인 '{name}'이 설치되어 있지 않습니다.")

        version = json.loads(version_path.read_text(encoding="utf-8"))
        source = Path(version["source_path"])
        shutil.copy2(source, self._skill_path(name))

        version["synced_at"] = datetime.now(timezone.utc).isoformat()
        version_path.write_text(
            json.dumps(version, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_plugins(self) -> list[dict]:
        if not self.root.exists():
            return []
        result = []
        for version_path in sorted(self.root.glob("*/version.json")):
            result.append(json.loads(version_path.read_text(encoding="utf-8")))
        return result

    def status(self) -> list[dict]:
        plugins = self.list_plugins()
        result = []
        for p in plugins:
            source = Path(p["source_path"])
            installed = self._skill_path(p["plugin"])
            drift = source.exists() and installed.read_text(encoding="utf-8") != source.read_text(encoding="utf-8")
            result.append({**p, "drift": drift})
        return result
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/test_plugin_manager.py -v
```

Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add core/plugin_manager.py tests/test_plugin_manager.py
git commit -m "feat: add PluginManager for versioned skill sync"
```

---

## Task 4: cli.py — Click CLI

**Files:**
- Create: `/Volumes/kairos/CC_projects/kairos-pd/cli.py`

CLI는 진입점만 담당한다. `run` 명령은 Plan 2에서 Orchestrator Agent를 Claude CLI로 실행하는 로직으로 채워진다 — 이 플랜에서는 DB 초기화 + 안내 메시지만 출력하는 뼈대로 구현한다.

- [ ] **Step 1: cli.py 작성**

`/Volumes/kairos/CC_projects/kairos-pd/cli.py`:

```python
import uuid
import json
import click
from pathlib import Path
from core.task_db import TaskDB
from core.plugin_manager import PluginManager

DB_PATH = "projects.db"
PLUGINS_ROOT = Path("plugins")
PIPELINE_PATH = Path("tasks/pipeline.json")


def get_db() -> TaskDB:
    db = TaskDB(DB_PATH)
    db.init()
    return db


@click.group()
def main():
    """kairos-pd — 에이전트 주도 콘텐츠 제작 파이프라인"""
    pass


# ── 프로젝트 ──────────────────────────────────────────────

@main.command()
@click.argument("topic", required=False, default="")
def new(topic):
    """기획 인터뷰 시작 → 프로젝트 생성 (Plan 2에서 Orchestrator 연결)"""
    db = get_db()
    project_id = str(uuid.uuid4())
    slug = topic.replace(" ", "_") if topic else "untitled"
    config = {"topic_hint": topic, "channel": "", "duration_minutes": 10}
    db.create_project(project_id, slug, config)

    if PIPELINE_PATH.exists():
        pipeline = json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
        task_ids = [t["id"] for t in pipeline["tasks"]]
        db.create_tasks(project_id, task_ids)

    click.echo(f"\n프로젝트 생성됨:")
    click.echo(f"  ID  : {project_id}")
    click.echo(f"  Slug: {slug}")
    click.echo(f"\n실행: kairos-pd run --project {project_id}")


@main.command()
@click.option("--project", required=True, help="project_id")
@click.option("--from", "from_task", default=None, help="특정 태스크부터 실행")
@click.option("--only", default=None, help="단일 태스크만 실행")
def run(project, from_task, only):
    """프로젝트 실행 (Plan 2에서 Orchestrator Agent 연결)"""
    db = get_db()
    p = db.get_project(project)
    if not p:
        click.echo(f"프로젝트 '{project}'를 찾을 수 없습니다.", err=True)
        raise SystemExit(1)
    click.echo(f"[kairos-pd] '{p['slug']}' 실행 준비 완료")
    click.echo("Orchestrator Agent 연결은 Plan 2에서 구현됩니다.")


@main.command()
@click.option("--project", default=None, help="특정 프로젝트 상태")
def status(project):
    """프로젝트 / 태스크 상태 확인"""
    db = get_db()
    if project:
        p = db.get_project(project)
        if not p:
            click.echo(f"프로젝트 '{project}'를 찾을 수 없습니다.", err=True)
            raise SystemExit(1)
        click.echo(f"\n{p['slug']} ({p['project_id']})")
        click.echo(f"상태: {p['status']}")
        click.echo("\n태스크:")
        icons = {"completed": "✓", "failed": "✗", "running": "→", "skipped": "○", "pending": "·"}
        for t in db.get_tasks(project):
            icon = icons.get(t["status"], "?")
            err = f" — {t['error']}" if t.get("error") else ""
            click.echo(f"  {icon} {t['task_id']}{err}")
    else:
        projects = db.list_projects()
        if not projects:
            click.echo("프로젝트 없음")
            return
        for p in projects:
            click.echo(f"  [{p['status']:10}] {p['slug']:30} {p['project_id'][:8]}...")


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


@main.command()
@click.option("--project", required=True)
@click.option("--task", required=True)
def retry(project, task):
    """실패한 태스크 재시도"""
    db = get_db()
    db.increment_attempt(project, task)
    click.echo(f"재시도 준비: {task}")
    click.echo(f"실행: kairos-pd run --project {project} --only {task}")


@main.command()
@click.option("--project", required=True)
@click.option("--task", required=True)
def skip(project, task):
    """태스크 스킵"""
    db = get_db()
    db.update_task_status(project, task, "skipped")
    click.echo(f"스킵됨: {task}")


# ── 플러그인 ──────────────────────────────────────────────

@main.group()
def plugin():
    """플러그인 관리"""
    pass


@plugin.command("list")
def plugin_list():
    """설치된 플러그인 목록"""
    pm = PluginManager(PLUGINS_ROOT)
    plugins = pm.list_plugins()
    if not plugins:
        click.echo("설치된 플러그인 없음")
        return
    for p in plugins:
        click.echo(f"  {p['plugin']:20} 동기화: {p['synced_at'][:10]}")


@plugin.command("status")
def plugin_status():
    """원본과 diff 비교"""
    pm = PluginManager(PLUGINS_ROOT)
    statuses = pm.status()
    if not statuses:
        click.echo("설치된 플러그인 없음")
        return
    for s in statuses:
        drift = "⚠ 변경 있음" if s["drift"] else "✓ 최신"
        click.echo(f"  {s['plugin']:20} {drift}")


@plugin.command("update")
@click.argument("name", required=False)
@click.option("--all", "update_all", is_flag=True)
def plugin_update(name, update_all):
    """플러그인 업데이트 (원본에서 최신 SKILL.md 복사)"""
    pm = PluginManager(PLUGINS_ROOT)
    if update_all:
        plugins = pm.list_plugins()
        for p in plugins:
            pm.update(p["plugin"])
            click.echo(f"  업데이트됨: {p['plugin']}")
    elif name:
        pm.update(name)
        click.echo(f"  업데이트됨: {name}")
    else:
        click.echo("플러그인 이름 또는 --all 옵션을 지정하세요.", err=True)


# ── 스타일 ──────────────────────────────────────────────

@main.group()
def style():
    """채널 스타일 관리"""
    pass


@style.command("list")
def style_list():
    """등록된 채널 스타일 목록"""
    styles_root = Path("styles")
    if not styles_root.exists():
        click.echo("등록된 스타일 없음")
        return
    for bundle in sorted(styles_root.glob("*/style_bundle.json")):
        import json as _json
        data = _json.loads(bundle.read_text(encoding="utf-8"))
        click.echo(f"  {data.get('channel', bundle.parent.name):20} v{data.get('version', '?')}")


@style.command("show")
@click.argument("channel")
def style_show(channel):
    """스타일 번들 출력"""
    import json as _json
    bundle_path = Path("styles") / channel / "style_bundle.json"
    if not bundle_path.exists():
        click.echo(f"스타일 '{channel}'을 찾을 수 없습니다.", err=True)
        raise SystemExit(1)
    click.echo(bundle_path.read_text(encoding="utf-8"))


@style.command("new")
@click.argument("channel")
def style_new(channel):
    """채널 스타일 신규 생성 (Plan 3에서 인터뷰 플로우 연결)"""
    click.echo(f"스타일 생성: {channel}")
    click.echo("인터뷰 플로우는 Plan 3에서 구현됩니다.")


@style.command("set")
@click.argument("channel")
@click.argument("field")
@click.argument("value")
def style_set(channel, field, value):
    """스타일 단일 필드 수정 (예: voice.id EXAVITQu4vr4xnSDxMaL)"""
    import json as _json
    bundle_path = Path("styles") / channel / "style_bundle.json"
    if not bundle_path.exists():
        click.echo(f"스타일 '{channel}'을 찾을 수 없습니다.", err=True)
        raise SystemExit(1)
    data = _json.loads(bundle_path.read_text(encoding="utf-8"))
    keys = field.split(".")
    target = data
    for k in keys[:-1]:
        target = target.setdefault(k, {})
    target[keys[-1]] = value
    bundle_path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    click.echo(f"  {channel}.{field} = {value}")


@style.command("edit")
@click.argument("channel")
@click.option("--writing", is_flag=True, help="writing_style.md 편집")
def style_edit(channel, writing):
    """스타일 파일 에디터로 열기"""
    import os
    styles_root = Path("styles") / channel
    if not styles_root.exists():
        click.echo(f"스타일 '{channel}'을 찾을 수 없습니다.", err=True)
        raise SystemExit(1)
    target = styles_root / ("writing_style.md" if writing else "style_bundle.json")
    editor = os.environ.get("EDITOR", "vi")
    os.execlp(editor, editor, str(target))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: CLI 기본 동작 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python cli.py --help
```

Expected:
```
Usage: cli.py [OPTIONS] COMMAND [ARGS]...
  kairos-pd — 에이전트 주도 콘텐츠 제작 파이프라인
Commands:
  new     기획 인터뷰 시작
  run     프로젝트 실행
  status  프로젝트 / 태스크 상태 확인
  list    프로젝트 목록
  retry   실패한 태스크 재시도
  skip    태스크 스킵
  plugin  플러그인 관리
  style   채널 스타일 관리
```

- [ ] **Step 3: new + status 엔드투엔드 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python cli.py new "포켓몬 30주년"
# 출력된 project_id 복사
python cli.py status
python cli.py list
```

Expected: 프로젝트 생성 확인, `[pending]` 상태로 목록 표시

- [ ] **Step 4: 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add cli.py
git commit -m "feat: add Click CLI skeleton (new/run/status/list/retry/skip/plugin/style)"
```

---

## Task 5: pip install 및 최종 확인

**Files:**
- Modify: `/Volumes/kairos/CC_projects/kairos-pd/pyproject.toml` (scripts 섹션 확인)

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/ -v
```

Expected: 13 passed (task_db: 7, plugin_manager: 6)

- [ ] **Step 2: pip install 확인**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
pip install -e .
kairos-pd --help
```

Expected: CLI 도움말 표시

- [ ] **Step 3: plugin install 수동 확인**

v3의 style-manager SKILL.md를 fontagent 대신 임시 플러그인으로 설치해 PluginManager 동작 검증:

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python - <<'EOF'
from pathlib import Path
from core.plugin_manager import PluginManager

source = Path("/Users/jleavens_macmini/LocalProjects/auto_kairos_v3/auto_agent/data/skills/agents/style-manager/SKILL.md")
pm = PluginManager(Path("plugins"))
pm.install("style-manager", source)
print(pm.list_plugins())
print(pm.status())
EOF
```

Expected: `[{'plugin': 'style-manager', ...}]`, drift=False

- [ ] **Step 4: 최종 커밋**

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
git add .
git commit -m "feat: kairos-pd Plan 1 완료 — Python 인프라 (task_db + plugin_manager + cli)"
```

---

## Verification

```bash
cd /Volumes/kairos/CC_projects/kairos-pd
python -m pytest tests/ -v
# Expected: 13 passed

kairos-pd --help
kairos-pd new "테스트 영상"
kairos-pd list
kairos-pd plugin list
kairos-pd style list
```

## Self-Review

### Spec Coverage

| 스펙 요구사항 | 구현 태스크 |
|-------------|-----------|
| SQLite task_db (projects + tasks) | Task 2 |
| 태스크 상태 머신 (pending→running→completed\|failed\|skipped) | Task 2 |
| CLI: new/run/status/list/retry/skip | Task 4 |
| CLI: plugin list/status/update | Task 4 |
| CLI: style list/show/new/set/edit | Task 4 |
| PluginManager install/update/status/drift 감지 | Task 3 |
| run 명령 뼈대 (Plan 2 연결 예정) | Task 4 |
| style new 뼈대 (Plan 3 연결 예정) | Task 4 |

### 플레이스홀더 없음 ✅
### 타입 일관성 ✅ — TaskDB, PluginManager 메서드 시그니처가 cli.py 호출과 일치
