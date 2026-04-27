# kairos-pd Plan 2: Orchestrator + 기획 인터뷰 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `kairos-pd run` 이 Claude Orchestrator Agent를 장수 세션으로 실행해 파이프라인을 태스크별로 순회하고, `/kairos-pd` 슬래시 스킬로 기획 인터뷰를 수행한다.

**Architecture:** Python CLI는 프롬프트를 구성해 `claude` CLI를 subprocess로 실행하고 stdout/stderr를 터미널에 직접 노출한다. Orchestrator는 Bash 도구로 `kairos-pd` CLI를 호출해 DB를 읽고 쓰며, 각 태스크를 `claude` 서브프로세스로 스폰한다. 기획 인터뷰는 Claude Code 슬래시 스킬로 현재 세션에서 대화형으로 수행되고 결과를 `editorial_brief.json`으로 저장한다.

**Tech Stack:** Python 3.11+, Click, subprocess.Popen (스트리밍), Claude CLI (`~/.local/bin/claude`), Markdown SKILL.md

---

## 파일 맵

### Create
- `/Volumes/jleavens/Projects/kairos-pd/skills/agents/orchestrator/SKILL.md` — Orchestrator 지침
- `/Volumes/jleavens/Projects/kairos-pd/skills/agents/interviewer/SKILL.md` — 기획 인터뷰 에이전트
- `/Volumes/jleavens/Projects/kairos-pd/.claude/skills/kairos-pd.md` — CC 슬래시 스킬
- `/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_orchestrator.py` — run/new 커맨드 테스트
- `/Volumes/jleavens/Projects/kairos-pd/core/claude_runner.py` — Claude CLI 실행 헬퍼

### Modify
- `/Volumes/jleavens/Projects/kairos-pd/cli.py` — `run`, `new`, `update-task`, `project-info` 커맨드 업데이트

---

## Task 1: Orchestrator용 DB 도구 CLI 추가

Orchestrator가 Bash 도구로 호출할 두 커맨드를 추가한다.

**Files:**
- Modify: `/Volumes/jleavens/Projects/kairos-pd/cli.py`
- Test: `/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_orchestrator.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_orchestrator.py`:

```python
from __future__ import annotations
import json
import pytest
from click.testing import CliRunner
from cli import main
from core.task_db import TaskDB


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_with_project(tmp_path, monkeypatch):
    """프로젝트 + 태스크가 있는 임시 DB."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("cli.DB_PATH", db_path)
    db = TaskDB(db_path)
    db.init()
    db.create_project("proj-001", "테스트_영상", {"channel": "이로미즘"})
    db.create_tasks("proj-001", ["preflight", "research.skeleton", "assembly"])
    return db


def test_status_json_output(runner, db_with_project):
    result = runner.invoke(main, ["status", "--project", "proj-001", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["project_id"] == "proj-001"
    assert len(data["tasks"]) == 3
    assert data["tasks"][0]["task_id"] == "preflight"
    assert data["tasks"][0]["status"] == "pending"


def test_update_task_command(runner, db_with_project):
    result = runner.invoke(main, [
        "update-task", "--project", "proj-001",
        "--task", "preflight", "--status", "completed"
    ])
    assert result.exit_code == 0
    db = db_with_project
    t = db.get_task("proj-001", "preflight")
    assert t["status"] == "completed"


def test_update_task_with_error(runner, db_with_project):
    result = runner.invoke(main, [
        "update-task", "--project", "proj-001",
        "--task", "preflight", "--status", "failed",
        "--error", "API 오류"
    ])
    assert result.exit_code == 0
    t = db_with_project.get_task("proj-001", "preflight")
    assert t["status"] == "failed"
    assert t["error"] == "API 오류"


def test_project_info_json(runner, db_with_project):
    result = runner.invoke(main, ["project-info", "--project", "proj-001"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["project_id"] == "proj-001"
    assert data["slug"] == "테스트_영상"
    assert data["config"]["channel"] == "이로미즘"


def test_status_json_unknown_project(runner, db_with_project):
    result = runner.invoke(main, ["status", "--project", "nope", "--json"])
    assert result.exit_code == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_orchestrator.py -v 2>&1 | head -20
```

Expected: FAIL — `--json` 옵션 없음, `update-task`/`project-info` 커맨드 없음

- [ ] **Step 3: cli.py 업데이트**

`cli.py`의 `status` 커맨드에 `--json` 옵션 추가:

```python
@main.command()
@click.option("--project", default=None, help="특정 프로젝트 상태")
@click.option("--json", "as_json", is_flag=True, help="JSON 출력 (Orchestrator용)")
def status(project, as_json):
    """프로젝트 / 태스크 상태 확인"""
    db = get_db()
    if project:
        p = db.get_project(project)
        if not p:
            click.echo(f"프로젝트 '{project}'를 찾을 수 없습니다.", err=True)
            raise SystemExit(1)
        if as_json:
            import json as _json
            click.echo(_json.dumps({
                "project_id": p["project_id"],
                "slug": p["slug"],
                "status": p["status"],
                "config": p.get("config", {}),
                "tasks": db.get_tasks(project),
            }, ensure_ascii=False))
            return
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
```

`update-task` 커맨드 추가 (skip 커맨드 아래):

```python
@main.command("update-task")
@click.option("--project", required=True)
@click.option("--task", required=True)
@click.option("--status", "task_status", required=True,
              type=click.Choice(["pending", "running", "completed", "failed", "skipped"]))
@click.option("--error", "error_msg", default=None)
def update_task(project, task, task_status, error_msg):
    """태스크 상태 업데이트 (Orchestrator용)"""
    db = get_db()
    db.update_task_status(project, task, task_status, error=error_msg)
    click.echo(f"updated: {task} → {task_status}")
```

`project-info` 커맨드 추가:

```python
@main.command("project-info")
@click.option("--project", required=True)
def project_info(project):
    """프로젝트 설정 JSON 출력 (Orchestrator용)"""
    import json as _json
    db = get_db()
    p = db.get_project(project)
    if not p:
        click.echo(f"프로젝트 '{project}'를 찾을 수 없습니다.", err=True)
        raise SystemExit(1)
    click.echo(_json.dumps(p, ensure_ascii=False))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_orchestrator.py -v
```

Expected: 5 passed

- [ ] **Step 5: 전체 테스트 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
```

Expected: 18 passed

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add cli.py tests/test_cli_orchestrator.py
git commit -m "feat: add status --json, update-task, project-info for Orchestrator"
```

---

## Task 2: claude_runner.py — Claude CLI 실행 헬퍼

**Files:**
- Create: `/Volumes/jleavens/Projects/kairos-pd/core/claude_runner.py`
- Test: `/Volumes/jleavens/Projects/kairos-pd/tests/test_claude_runner.py`

- [ ] **Step 1: 테스트 작성**

`/Volumes/jleavens/Projects/kairos-pd/tests/test_claude_runner.py`:

```python
from __future__ import annotations
import subprocess
import pytest
from unittest.mock import patch, MagicMock
from core.claude_runner import build_claude_cmd, ClaudeRunner


def test_build_claude_cmd_defaults():
    cmd = build_claude_cmd(max_turns=50, tools=["Bash"])
    assert "claude" in cmd[0]
    assert "--max-turns" in cmd
    assert "50" in cmd
    assert "--allowedTools" in cmd
    assert "Bash" in cmd
    assert "--dangerously-skip-permissions" in cmd


def test_build_claude_cmd_model():
    cmd = build_claude_cmd(max_turns=10, tools=["Bash"], model="claude-haiku-4-5-20251001")
    assert "--model" in cmd
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "claude-haiku-4-5-20251001"


def test_claude_runner_run_calls_popen(tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.wait.return_value = 0

    with patch("core.claude_runner.subprocess.Popen", return_value=mock_proc) as mock_popen:
        runner = ClaudeRunner(claude_bin="/usr/local/bin/claude")
        rc = runner.run(prompt="테스트 프롬프트", max_turns=10, tools=["Bash"])

    assert mock_popen.called
    call_kwargs = mock_popen.call_args
    cmd = call_kwargs[0][0]
    assert "/usr/local/bin/claude" in cmd
    assert rc == 0


def test_claude_runner_returns_nonzero_on_failure(tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.wait.return_value = 1

    with patch("core.claude_runner.subprocess.Popen", return_value=mock_proc):
        runner = ClaudeRunner(claude_bin="/usr/local/bin/claude")
        rc = runner.run(prompt="fail", max_turns=5, tools=["Bash"])

    assert rc == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_claude_runner.py -v 2>&1 | head -15
```

Expected: FAIL with `ModuleNotFoundError: No module named 'core.claude_runner'`

- [ ] **Step 3: claude_runner.py 구현**

`/Volumes/jleavens/Projects/kairos-pd/core/claude_runner.py`:

```python
from __future__ import annotations
import os
import subprocess
from pathlib import Path


_DEFAULT_CLAUDE_BIN = str(Path.home() / ".local" / "bin" / "claude")


def build_claude_cmd(
    max_turns: int,
    tools: list[str],
    model: str = "claude-sonnet-4-6",
    claude_bin: str = _DEFAULT_CLAUDE_BIN,
) -> list[str]:
    cmd = [claude_bin, "--dangerously-skip-permissions",
           "--model", model, "--max-turns", str(max_turns)]
    for tool in tools:
        cmd += ["--allowedTools", tool]
    return cmd


class ClaudeRunner:
    def __init__(self, claude_bin: str = _DEFAULT_CLAUDE_BIN):
        self.claude_bin = claude_bin

    def run(
        self,
        prompt: str,
        max_turns: int,
        tools: list[str],
        model: str = "claude-sonnet-4-6",
        env_extra: dict | None = None,
        cwd: str | None = None,
    ) -> int:
        """프롬프트를 stdin으로 전달해 claude CLI를 실행한다. 출력은 터미널에 직접 표시."""
        cmd = build_claude_cmd(max_turns=max_turns, tools=tools,
                               model=model, claude_bin=self.claude_bin)
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)  # 중첩 세션 방지
        if env_extra:
            env.update(env_extra)

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=None,   # 터미널 직접 출력
            stderr=None,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=cwd,
        )
        proc.stdin.write(prompt)
        proc.stdin.close()
        proc.wait()
        return proc.returncode
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_claude_runner.py -v
```

Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add core/claude_runner.py tests/test_claude_runner.py
git commit -m "feat: add ClaudeRunner helper for subprocess claude CLI"
```

---

## Task 3: Orchestrator SKILL.md

**Files:**
- Create: `/Volumes/jleavens/Projects/kairos-pd/skills/agents/orchestrator/SKILL.md`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Volumes/jleavens/Projects/kairos-pd/skills/agents/orchestrator
```

- [ ] **Step 2: SKILL.md 작성**

`/Volumes/jleavens/Projects/kairos-pd/skills/agents/orchestrator/SKILL.md`:

```markdown
# Orchestrator Agent

당신은 kairos-pd Orchestrator입니다.
주어진 PROJECT_ID의 파이프라인을 DAG 순서에 따라 태스크별로 실행하고,
각 태스크 결과를 DB에 기록하며, 실패 시 사용자에게 처리 방법을 묻습니다.

## 환경

- PROJECT_ID: $PROJECT_ID
- 파이프라인 정의: $PIPELINE_PATH
- kairos-pd CLI: kairos-pd (PATH에 등록됨)
- Claude CLI: $CLAUDE_BIN

## 도구

Bash 도구만 사용합니다.

## 실행 루프

다음을 모든 태스크가 완료되거나 중단될 때까지 반복합니다.

### 1. 현재 상태 조회

```bash
kairos-pd status --project $PROJECT_ID --json
```

응답 JSON에서 tasks 배열을 읽어 각 태스크의 status를 파악합니다.

### 2. 실행 가능한 태스크 판단 (DAG)

pipeline.json을 읽어 `depends_on`이 모두 `completed` 또는 `skipped`인 `pending` 태스크를 찾습니다.

```bash
cat $PIPELINE_PATH
```

- `completed` 또는 `skipped` 태스크만 의존성 충족으로 인정합니다.
- 실행 가능한 태스크가 없고 pending도 없으면 → 파이프라인 완료.
- 실행 가능한 태스크가 없는데 pending이 있으면 → 블로킹 상태, 중단.

### 3. 태스크 실행

실행 가능한 태스크 하나를 선택해 실행합니다.

#### 태스크 시작 등록

```bash
kairos-pd update-task --project $PROJECT_ID --task <task_id> --status running
```

#### 태스크 유형별 실행

**type: "agent"** — SKILL.md를 읽어 서브에이전트로 실행:

```bash
SKILL=$(cat <skill_path>)
PROMPT="${SKILL}

## 현재 태스크
project_id: $PROJECT_ID
task_id: <task_id>
output_dir: $OUTPUT_DIR
"
echo "$PROMPT" | $CLAUDE_BIN --dangerously-skip-permissions \
  --model claude-sonnet-4-6 --max-turns 60 \
  --allowedTools Bash --allowedTools Read --allowedTools Write --allowedTools Edit
```

**type: "plugin"** — plugins/ 디렉토리에서 SKILL.md를 읽어 실행:

```bash
PLUGIN_SKILL=$(cat plugins/<plugin_name>/SKILL.md)
# agent와 동일하게 실행
```

#### 결과 등록

- 서브에이전트 exit code 0 → completed
- exit code 非0 → failed

```bash
# 성공
kairos-pd update-task --project $PROJECT_ID --task <task_id> --status completed

# 실패
kairos-pd update-task --project $PROJECT_ID --task <task_id> --status failed \
  --error "exit code <n>"
```

### 4. 실패 게이트

태스크가 failed이면 사용자에게 묻습니다:

```
[FAILED] task: <task_id>
오류: <error>

어떻게 할까요?
  r) 재시도 (attempt 증가)
  s) 건너뛰기 (skipped 처리, 다운스트림 계속)
  a) 전체 중단
```

- r → `kairos-pd retry --project $PROJECT_ID --task <task_id>` 후 루프 계속
- s → `kairos-pd skip --project $PROJECT_ID --task <task_id>` 후 루프 계속
- a → 루프 종료

### 5. 완료 판정

모든 태스크가 `completed` 또는 `skipped`이면:

```
✅ 파이프라인 완료: $PROJECT_ID
```

를 출력하고 종료합니다.

## 규칙

- 한 번에 하나의 태스크만 실행합니다 (병렬 실행은 현재 지원하지 않음).
- `--only`나 `--from` 옵션이 전달된 경우 해당 태스크만 또는 해당 태스크부터 실행합니다.
- 서브에이전트 실행 전 반드시 `update-task --status running`을 먼저 호출합니다.
- 환경변수 `CLAUDECODE`는 서브에이전트 호출 시 제거합니다 (중첩 세션 방지).
```

- [ ] **Step 3: 파일 존재 확인**

```bash
cat /Volumes/jleavens/Projects/kairos-pd/skills/agents/orchestrator/SKILL.md | head -5
```

Expected: `# Orchestrator Agent` 출력

- [ ] **Step 4: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add skills/agents/orchestrator/SKILL.md
git commit -m "feat: add Orchestrator SKILL.md"
```

---

## Task 4: `run` 커맨드 → Claude CLI 연결

**Files:**
- Modify: `/Volumes/jleavens/Projects/kairos-pd/cli.py`
- Test: `/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_orchestrator.py`

- [ ] **Step 1: 테스트 추가**

`tests/test_cli_orchestrator.py` 하단에 추가:

```python
def test_run_invokes_claude_runner(runner, db_with_project):
    """run 커맨드가 ClaudeRunner.run을 호출하는지 검증."""
    with patch("cli.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        mock_instance.run.return_value = 0
        MockRunner.return_value = mock_instance

        result = runner.invoke(main, ["run", "--project", "proj-001"])

    assert result.exit_code == 0
    assert mock_instance.run.called
    call_kwargs = mock_instance.run.call_args[1]
    assert "PROJECT_ID=proj-001" in call_kwargs.get("env_extra", {}).get("PROJECT_ID", "") \
        or call_kwargs.get("env_extra", {}).get("PROJECT_ID") == "proj-001"


def test_run_fails_for_unknown_project(runner, db_with_project):
    result = runner.invoke(main, ["run", "--project", "nope"])
    assert result.exit_code == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_orchestrator.py::test_run_invokes_claude_runner -v 2>&1 | head -15
```

Expected: FAIL — `run` 커맨드가 `ClaudeRunner`를 쓰지 않음

- [ ] **Step 3: cli.py `run` 커맨드 업데이트**

`cli.py` 상단 import에 추가:
```python
from core.claude_runner import ClaudeRunner
```

`run` 커맨드 전체 교체:

```python
@main.command()
@click.option("--project", required=True, help="project_id")
@click.option("--from", "from_task", default=None, help="특정 태스크부터 실행")
@click.option("--only", default=None, help="단일 태스크만 실행")
def run(project, from_task, only):
    """프로젝트 실행 — Claude Orchestrator Agent 시작"""
    db = get_db()
    p = db.get_project(project)
    if not p:
        click.echo(f"프로젝트 '{project}'를 찾을 수 없습니다.", err=True)
        raise SystemExit(1)

    skill_path = _HERE / "skills" / "agents" / "orchestrator" / "SKILL.md"
    if not skill_path.exists():
        click.echo(f"Orchestrator SKILL.md 없음: {skill_path}", err=True)
        raise SystemExit(1)

    skill = skill_path.read_text(encoding="utf-8")

    opts = []
    if from_task:
        opts.append(f"--from {from_task}")
    if only:
        opts.append(f"--only {only}")

    prompt = f"""{skill}

## 실행 파라미터
PROJECT_ID={project}
PIPELINE_PATH={_HERE / 'tasks' / 'pipeline.json'}
OUTPUT_DIR={_HERE / 'output' / f'{project}_{p["slug"]}'}
CLAUDE_BIN={Path.home() / '.local' / 'bin' / 'claude'}
{chr(10).join(opts)}
"""

    click.echo(f"[kairos-pd] '{p['slug']}' 파이프라인 시작...")
    cr = ClaudeRunner()
    rc = cr.run(
        prompt=prompt,
        max_turns=200,
        tools=["Bash", "Read", "Write", "Edit"],
        env_extra={"PROJECT_ID": project, "KAIROS_PD_HOME": str(_HERE)},
        cwd=str(_HERE),
    )
    if rc != 0:
        click.echo(f"[kairos-pd] Orchestrator 종료 (exit {rc})", err=True)
        raise SystemExit(rc)
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_orchestrator.py -v
```

Expected: 7 passed

- [ ] **Step 5: 전체 테스트 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
```

Expected: 22 passed

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add cli.py tests/test_cli_orchestrator.py
git commit -m "feat: run command invokes Claude Orchestrator via ClaudeRunner"
```

---

## Task 5: 기획 인터뷰 SKILL.md + `/kairos-pd` 슬래시 스킬

**Files:**
- Create: `/Volumes/jleavens/Projects/kairos-pd/skills/agents/interviewer/SKILL.md`
- Create: `/Volumes/jleavens/Projects/kairos-pd/.claude/skills/kairos-pd.md`

- [ ] **Step 1: 디렉토리 생성**

```bash
mkdir -p /Volumes/jleavens/Projects/kairos-pd/skills/agents/interviewer
mkdir -p /Volumes/jleavens/Projects/kairos-pd/.claude/skills
```

- [ ] **Step 2: interviewer SKILL.md 작성**

`/Volumes/jleavens/Projects/kairos-pd/skills/agents/interviewer/SKILL.md`:

```markdown
# 기획 인터뷰 에이전트

당신은 kairos-pd 기획 인터뷰어입니다.
사용자와 대화하며 영상 프로젝트의 핵심 기획 정보를 수집하고,
최종적으로 `editorial_brief.json`을 생성합니다.

## 인터뷰 흐름

다음 항목을 한 번에 하나씩 질문합니다.
이미 사용자가 제공한 정보는 건너뜁니다.

1. **채널 선택**
   - 등록된 스타일 목록: `kairos-pd style list` 로 조회
   - 없으면 "신규 채널"로 진행

2. **주제 / 핵심 각도**
   - 영상의 핵심 주장이나 이야기 방향
   - 아직 없다면 함께 탐색

3. **분량**
   - 선택지: 1 / 3 / 5 / 10 / 15분
   - 기본값: 10분

4. **아트스타일**
   - `kairos-pd style list`에서 선택
   - 스타일 없으면 기본값 `realistic` 적용

5. **확정**
   - 수집된 정보를 요약해 사용자에게 보여줌
   - 수정 요청 있으면 해당 항목만 재질문

## 출력

인터뷰 완료 후 다음을 실행합니다:

```bash
kairos-pd new-from-brief \
  --topic "<주제>" \
  --channel "<채널>" \
  --duration <분> \
  --art-style "<스타일>" \
  --angle "<핵심각도>"
```

## 규칙

- 한 번에 하나의 질문만 합니다.
- 사용자 응답을 그대로 수용하고 강요하지 않습니다.
- 모든 질문이 끝나면 반드시 요약 확인 후 `new-from-brief`를 호출합니다.
```

- [ ] **Step 3: `.claude/skills/kairos-pd.md` 슬래시 스킬 작성**

`/Volumes/jleavens/Projects/kairos-pd/.claude/skills/kairos-pd.md`:

```markdown
---
name: kairos-pd
description: kairos-pd 기획 인터뷰 시작. 채널/주제/분량/아트스타일을 대화로 수집해 프로젝트를 생성한다.
---

# kairos-pd 기획 인터뷰

kairos-pd 기획 인터뷰를 시작합니다.

## 역할

당신은 kairos-pd 기획 인터뷰어입니다.
사용자와 대화하며 영상 프로젝트의 핵심 기획 정보를 수집하고,
`kairos-pd new-from-brief` 커맨드로 프로젝트를 생성합니다.

## 인터뷰 흐름 (한 번에 하나씩)

1. **채널 선택** — `kairos-pd style list` 조회 후 보여주기
2. **주제 / 핵심 각도** — 영상의 핵심 이야기 방향
3. **분량** — 1 / 3 / 5 / 10 / 15분 (기본: 10분)
4. **아트스타일** — 등록된 스타일 중 선택 (기본: realistic)
5. **요약 확인** → `kairos-pd new-from-brief` 호출

## 시작

먼저 `kairos-pd style list` 를 실행해 등록된 채널 스타일을 확인하고,
사용자에게 채널을 선택하거나 새 채널로 시작할지 물어보세요.
```

- [ ] **Step 4: 파일 확인**

```bash
cat /Volumes/jleavens/Projects/kairos-pd/.claude/skills/kairos-pd.md | head -5
cat /Volumes/jleavens/Projects/kairos-pd/skills/agents/interviewer/SKILL.md | head -5
```

Expected: 각 파일 첫 줄 출력

- [ ] **Step 5: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add skills/agents/interviewer/SKILL.md .claude/skills/kairos-pd.md
git commit -m "feat: add interviewer SKILL.md and /kairos-pd slash skill"
```

---

## Task 6: `new-from-brief` 커맨드 + `new` 커맨드 업데이트

**Files:**
- Modify: `/Volumes/jleavens/Projects/kairos-pd/cli.py`
- Test: `/Volumes/jleavens/Projects/kairos-pd/tests/test_cli_orchestrator.py`

- [ ] **Step 1: 테스트 추가**

`tests/test_cli_orchestrator.py` 하단에 추가:

```python
def test_new_from_brief_creates_project(runner, db_with_project):
    result = runner.invoke(main, [
        "new-from-brief",
        "--topic", "포켓몬 30주년",
        "--channel", "이로미즘",
        "--duration", "10",
        "--art-style", "realistic",
        "--angle", "게임 문화가 세대를 잇는 방식",
    ])
    assert result.exit_code == 0
    # project_id가 출력됐는지 확인
    assert "project_id" in result.output or "생성됨" in result.output


def test_new_from_brief_saves_editorial_brief(runner, db_with_project, tmp_path, monkeypatch):
    monkeypatch.setattr("cli._HERE", tmp_path)
    (tmp_path / "output").mkdir()

    result = runner.invoke(main, [
        "new-from-brief",
        "--topic", "테스트",
        "--channel", "이로미즘",
        "--duration", "5",
        "--art-style", "realistic",
        "--angle", "테스트 각도",
    ])
    assert result.exit_code == 0
    # output/{project_id}_테스트/ 디렉토리 확인
    output_dirs = list(tmp_path.glob("output/*_테스트"))
    assert len(output_dirs) == 1
    brief = output_dirs[0] / "editorial_brief.json"
    assert brief.exists()
    import json as _json
    data = _json.loads(brief.read_text(encoding="utf-8"))
    assert data["channel"] == "이로미즘"
    assert data["duration_minutes"] == 5
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_orchestrator.py::test_new_from_brief_creates_project -v 2>&1 | head -10
```

Expected: FAIL — `new-from-brief` 커맨드 없음

- [ ] **Step 3: cli.py에 `new-from-brief` 추가**

`new` 커맨드 아래에 추가:

```python
@main.command("new-from-brief")
@click.option("--topic", required=True)
@click.option("--channel", required=True)
@click.option("--duration", type=int, required=True)
@click.option("--art-style", "art_style", default="realistic")
@click.option("--angle", default="")
def new_from_brief(topic, channel, duration, art_style, angle):
    """기획 인터뷰 결과로 프로젝트 생성 (인터뷰어가 호출)"""
    import json as _json
    db = get_db()
    project_id = str(uuid.uuid4())
    slug = topic.replace(" ", "_")

    config = {
        "topic": topic,
        "channel": channel,
        "duration_minutes": duration,
        "art_style": art_style,
        "core_angle": angle,
    }
    db.create_project(project_id, slug, config)

    if PIPELINE_PATH.exists():
        pipeline = _json.loads(PIPELINE_PATH.read_text(encoding="utf-8"))
        task_ids = [t["id"] for t in pipeline["tasks"]]
        db.create_tasks(project_id, task_ids)

    # editorial_brief.json 저장
    output_dir = _HERE / "output" / f"{project_id}_{slug}"
    output_dir.mkdir(parents=True, exist_ok=True)
    brief = {
        "project_id": project_id,
        "slug": slug,
        "channel": channel,
        "duration_minutes": duration,
        "art_style": art_style,
        "core_angle": angle,
    }
    (output_dir / "editorial_brief.json").write_text(
        _json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    click.echo(f"\n프로젝트 생성됨:")
    click.echo(f"  project_id: {project_id}")
    click.echo(f"  slug      : {slug}")
    click.echo(f"  채널      : {channel}")
    click.echo(f"  분량      : {duration}분")
    click.echo(f"\n실행: kairos-pd run --project {project_id}")
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/test_cli_orchestrator.py -v
```

Expected: 9 passed

- [ ] **Step 5: 전체 테스트 확인**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
```

Expected: 26 passed

- [ ] **Step 6: 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add cli.py tests/test_cli_orchestrator.py
git commit -m "feat: add new-from-brief command for interview flow"
```

---

## Task 7: 최종 검증

**Files:**
- 수정 없음 — 통합 동작 확인

- [ ] **Step 1: 전체 테스트**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
```

Expected: 26 passed

- [ ] **Step 2: CLI 커맨드 목록 확인**

```bash
kairos-pd --help
```

Expected: new, new-from-brief, run, status, list, retry, skip, update-task, project-info, plugin, style 포함

- [ ] **Step 3: 슬래시 스킬 등록 확인**

```bash
ls /Volumes/jleavens/Projects/kairos-pd/.claude/skills/
```

Expected: `kairos-pd.md` 존재

- [ ] **Step 4: Orchestrator SKILL 확인**

```bash
wc -l /Volumes/jleavens/Projects/kairos-pd/skills/agents/orchestrator/SKILL.md
```

Expected: 80줄 이상

- [ ] **Step 5: 최종 커밋**

```bash
cd /Volumes/jleavens/Projects/kairos-pd
git add .
git commit -m "feat: kairos-pd Plan 2 완료 — Orchestrator + 기획 인터뷰"
```

---

## Verification

```bash
cd /Volumes/jleavens/Projects/kairos-pd
/opt/homebrew/bin/python3.12 -m pytest tests/ -v
# Expected: 26 passed

kairos-pd --help
# new-from-brief, update-task, project-info 커맨드 포함 확인

kairos-pd new-from-brief \
  --topic "테스트 영상" --channel "이로미즘" \
  --duration 5 --art-style realistic --angle "테스트"
# editorial_brief.json 생성 확인
```

---

## Self-Review

### Spec Coverage

| 스펙 요구사항 | 구현 태스크 |
|-------------|-----------|
| Orchestrator SKILL.md (DAG 순회, 서브에이전트 스폰, 실패 게이트) | Task 3 |
| `run` 커맨드 → Claude CLI subprocess | Task 4 |
| Orchestrator용 DB 도구 (status --json, update-task, project-info) | Task 1 |
| ClaudeRunner 헬퍼 (CLAUDECODE pop, 스트리밍 출력) | Task 2 |
| 기획 인터뷰 SKILL.md | Task 5 |
| `/kairos-pd` 슬래시 스킬 | Task 5 |
| `new-from-brief` 커맨드 + editorial_brief.json | Task 6 |

### 플레이스홀더 없음 ✅
### 타입 일관성 ✅ — ClaudeRunner.run 시그니처가 cli.py 호출과 일치
