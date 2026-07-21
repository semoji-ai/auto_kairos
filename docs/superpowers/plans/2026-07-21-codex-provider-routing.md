# codex 프로바이더 라우팅 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 웹 리서치 에이전트 2종(flesh-researcher, targeted-researcher)을 codex CLI 기본으로 실행하고, 이미지 생성을 codex-fleet(codex 내장 image_gen 병렬) 기본 + FAL 폴백으로 전환한다.

**Architecture:** codex exec 호출을 `auto_agent/utils/codex_cli.py` 공용 유틸로 추출하고, `orchestrator/runner.py::_run_agent_step`에 provider 분기(codex 실패 시 claude 폴백)를 추가한다. 이미지는 `image_batch_module.py`에 backend 라우터를 두고, codex 경로는 기존 `tools/codex_image.codex_generate`(세션 자체가 out_path로 복사 → 레이스 없음)를 ThreadPool로 병렬화한 `tools/codex_fleet.py`가 담당하며, 실패 씬만 기존 FAL 경로로 개별 폴백한다.

**Tech Stack:** Python 3 (pathlib, subprocess, concurrent.futures), codex CLI, FAL(폴백), pytest.

## Global Constraints

- 한글 답변/주석 규칙: 코드 주석은 기존 파일 스타일(한글) 유지.
- 절대경로 하드코딩 금지 — `pathlib.Path`, `CODEX_HOME = os.environ.get("CODEX_HOME", ~/.codex)`.
- 이미지 파일 삭제 절대 금지 — 재생성은 버전 번호, `image_assets.json` selected만 전환.
- codex 이미지 경로는 `env -u OPENAI_API_KEY` (OpenAI API 직접 호출 금지).
- 서브프로세스 env에서 `CLAUDECODE` pop 필수.
- 새 환경변수(`AUTO_AGENT_RESEARCH_PROVIDER`, `IMAGE_BACKEND`)는 `.env.example`에도 추가.
- 커밋은 태스크 단위로 자주. 테스트는 `python3 -m pytest tests/<파일> -v`.
- gpt-image-2 프롬프트는 공냥 규격: 네거티브 금지, 끝에 `AR x:y` 토큰만, 사이즈 락 6종.

---

### Task 1: codex exec --search 스모크 테스트 (블로커 게이트)

**Files:**
- Create: `/private/tmp/claude-501/.../scratchpad/codex_search_smoke/` (스크래치, 커밋 안 함)

**Interfaces:**
- Produces: `--search` 플래그 동작 여부 판정. 실패 시 이후 리서치 태스크(2~6)는 설계 재검토로 중단하고 사용자에게 보고.

- [ ] **Step 1: codex CLI 존재/버전 확인**

Run: `which codex && codex --version`
Expected: 경로와 버전 출력. 없으면 즉시 중단·보고.

- [ ] **Step 2: --search 플래그 인식 확인**

Run: `codex exec --help | grep -i search`
Expected: `--search` (또는 web search 관련 config) 항목 존재. 없으면 `codex exec -c 'tools.web_search=true'` 형태를 대신 시험.

- [ ] **Step 3: 실제 웹 검색 + 파일 산출 스모크**

Run (스크래치 디렉토리에서):
```bash
mkdir -p "$SCRATCH/codex_search_smoke" && cd "$SCRATCH/codex_search_smoke"
echo "오늘 기준 최신 뉴스에서 'ISS 국제우주정거장' 관련 헤드라인 2개를 웹 검색으로 찾아 smoke_result.md 파일로 저장하라. 각 항목에 출처 URL 포함." | \
  codex exec -C "$PWD" --skip-git-repo-check --ephemeral --sandbox workspace-write --search --json --output-last-message last.txt
cat smoke_result.md
```
Expected: `smoke_result.md`가 생성되고 URL 포함 헤드라인이 들어 있음. 미생성/검색 불가면 **블로커** — 사용자 보고 후 대기.

- [ ] **Step 4: 결과 기록**

성공한 정확한 플래그 조합을 Task 2의 `build_codex_exec_cmd` 구현에 반영 (기본 `--search`, 다르면 해당 조합으로 교체).

---

### Task 2: 공용 유틸 `utils/codex_cli.py`

**Files:**
- Create: `auto_agent/utils/codex_cli.py`
- Test: `tests/test_codex_cli.py`

**Interfaces:**
- Produces:
  - `find_codex_cli() -> str` (없으면 `FileNotFoundError`)
  - `codex_available() -> bool`
  - `build_codex_exec_cmd(*, workdir: Path, output_last_message: str, model: str | None = None, reasoning_effort: str = "medium", search: bool = False) -> list[str]`
  - `read_output_last_message(path: str | None, fallback: str = "") -> str`

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_codex_cli.py`)

```python
from pathlib import Path
from unittest.mock import patch
import pytest

from auto_agent.utils.codex_cli import (
    build_codex_exec_cmd, codex_available, find_codex_cli, read_output_last_message,
)


@patch("auto_agent.utils.codex_cli.shutil.which", return_value="/usr/local/bin/codex")
def test_build_cmd_basic(mock_which):
    cmd = build_codex_exec_cmd(workdir=Path("/tmp/w"), output_last_message="/tmp/last.txt")
    assert cmd[0] == "/usr/local/bin/codex"
    assert cmd[1] == "exec"
    assert ["-C", "/tmp/w"] == cmd[2:4]
    assert "--ephemeral" in cmd and "--skip-git-repo-check" in cmd
    assert ["--sandbox", "workspace-write"] == [cmd[i] for i in (cmd.index("--sandbox"), cmd.index("--sandbox") + 1)]
    assert "--search" not in cmd
    assert "-m" not in cmd  # model 미지정 시 CLI 기본


@patch("auto_agent.utils.codex_cli.shutil.which", return_value="/usr/local/bin/codex")
def test_build_cmd_search_and_model(mock_which):
    cmd = build_codex_exec_cmd(
        workdir=Path("/tmp/w"), output_last_message="/tmp/last.txt",
        model="o4-mini", search=True,
    )
    assert "--search" in cmd
    assert cmd[cmd.index("-m") + 1] == "o4-mini"


@patch("auto_agent.utils.codex_cli.shutil.which", return_value=None)
def test_find_codex_cli_missing(mock_which):
    assert codex_available() is False
    with pytest.raises(FileNotFoundError):
        find_codex_cli()


def test_read_output_last_message(tmp_path):
    p = tmp_path / "last.txt"
    p.write_text("  결과  ", encoding="utf-8")
    assert read_output_last_message(str(p), fallback="fb") == "결과"
    assert read_output_last_message(str(tmp_path / "none.txt"), fallback="fb") == "fb"
    assert read_output_last_message(None, fallback="fb") == "fb"
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest tests/test_codex_cli.py -v`
Expected: FAIL (`ModuleNotFoundError: auto_agent.utils.codex_cli`)

- [ ] **Step 3: 구현** (`auto_agent/utils/codex_cli.py`)

```python
"""codex CLI 공용 유틸 — 명령 빌드 + 출력 회수.

agent_runner(파이프라인 외부)와 orchestrator/runner(파이프라인)가 공유한다.
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional


def find_codex_cli() -> str:
    """Codex CLI 바이너리 경로. 없으면 FileNotFoundError."""
    path = shutil.which("codex")
    if path:
        return path
    raise FileNotFoundError("Codex CLI를 찾을 수 없습니다. 'codex'가 PATH에 있는지 확인하세요.")


def codex_available() -> bool:
    return shutil.which("codex") is not None


def build_codex_exec_cmd(
    *,
    workdir: Path,
    output_last_message: str,
    model: Optional[str] = None,
    reasoning_effort: str = "medium",
    search: bool = False,
) -> List[str]:
    """codex exec 명령 빌드. 프롬프트는 stdin으로 전달한다."""
    cmd = [
        find_codex_cli(),
        "exec",
        "-C", str(workdir),
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox", "workspace-write",
        "-c", f'model_reasoning_effort="{reasoning_effort}"',
        "--json",
        "--output-last-message", output_last_message,
    ]
    if search:
        cmd.append("--search")  # Task 1 스모크에서 확정한 플래그
    if model:
        cmd += ["-m", model]
    return cmd


def read_output_last_message(path: Optional[str], fallback: str = "") -> str:
    if not path:
        return fallback
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
        return text or fallback
    except Exception:
        return fallback
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest tests/test_codex_cli.py -v`
Expected: PASS (4건)

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/utils/codex_cli.py tests/test_codex_cli.py
git commit -m "feat(utils): codex CLI 공용 유틸 — 명령 빌드/출력 회수"
```

---

### Task 3: `modules/agent_runner.py`를 공용 유틸로 리팩터

**Files:**
- Modify: `auto_agent/modules/agent_runner.py` (`_build_codex_cmd` 1391행 부근, `_find_codex_cli`, `_read_output_last_message`)

**Interfaces:**
- Consumes: Task 2의 `build_codex_exec_cmd`, `find_codex_cli`, `read_output_last_message`
- Produces: 기존 메서드 시그니처 유지 (호출부 변경 없음)

- [ ] **Step 1: 위임으로 교체**

`agent_runner.py` 상단 import에 추가:
```python
from auto_agent.utils import codex_cli as codex_cli_util
```

`_build_codex_cmd` 본문을 다음으로 교체 (시그니처 유지):
```python
    def _build_codex_cmd(
        self,
        model: str,
        reasoning_effort: str,
        output_last_message: str,
        workdir: Optional[Path] = None,
    ) -> List[str]:
        """Codex CLI 명령어 빌드 — 공용 유틸 위임."""
        return codex_cli_util.build_codex_exec_cmd(
            workdir=workdir or self._vault_dir,
            output_last_message=output_last_message,
            model=model,
            reasoning_effort=reasoning_effort,
        )
```

`_find_codex_cli` 본문 → `return codex_cli_util.find_codex_cli()`
`_read_output_last_message` 본문 → `return codex_cli_util.read_output_last_message(path, fallback)`

- [ ] **Step 2: 회귀 확인**

Run: `python3 -m pytest tests/ -k "agent_runner or codex" -v` 후 전체 `python3 -m pytest tests/ -q`
Expected: 전체 그린 (기존 427 + 신규)

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/modules/agent_runner.py
git commit -m "refactor(agent_runner): codex 명령 빌드를 utils/codex_cli로 위임"
```

---

### Task 4: 리서치 provider 해석 + `_run_agent_step` codex 분기

**Files:**
- Modify: `auto_agent/orchestrator/runner.py` (`_run_agent_step` 3967행 부근)
- Test: `tests/test_codex_provider_routing.py`

**Interfaces:**
- Consumes: Task 2 유틸 전부
- Produces:
  - `PipelineRunner._resolve_agent_provider(agent: str, agent_def: dict) -> str` ("claude"|"codex")
  - `PipelineRunner._run_codex_agent_step(step, step_id, agent_def, prompt, outputs, timeout_sec) -> StepResult`
  - 우선순위: 프로젝트 config `research_provider` > env `AUTO_AGENT_RESEARCH_PROVIDER` > agents.json `provider` > "claude"

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_codex_provider_routing.py`)

runner 클래스명/생성 방식은 `orchestrator/runner.py` 기존 테스트(`tests/`에서 grep)를 따라 최소 인스턴스를 만들거나, 해석 로직을 모듈 함수로 두고 직접 테스트한다. 해석 로직은 **모듈 레벨 함수**로 구현해 러너 인스턴스 없이 테스트 가능하게 한다:

```python
import os
from unittest.mock import patch

from auto_agent.orchestrator.runner import resolve_agent_provider

FLESH_DEF = {"provider": "codex"}


def test_default_codex_from_agents_json():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("AUTO_AGENT_RESEARCH_PROVIDER", None)
        assert resolve_agent_provider("flesh-researcher", FLESH_DEF, {}) == "codex"


def test_env_overrides_agents_json():
    with patch.dict(os.environ, {"AUTO_AGENT_RESEARCH_PROVIDER": "claude"}):
        assert resolve_agent_provider("targeted-researcher", FLESH_DEF, {}) == "claude"


def test_project_config_overrides_env():
    with patch.dict(os.environ, {"AUTO_AGENT_RESEARCH_PROVIDER": "claude"}):
        assert resolve_agent_provider("flesh-researcher", FLESH_DEF, {"research_provider": "codex"}) == "codex"


def test_non_research_agent_always_claude():
    assert resolve_agent_provider("script-director", {"provider": "codex"}, {"research_provider": "codex"}) == "claude"


def test_invalid_value_falls_back():
    assert resolve_agent_provider("flesh-researcher", {"provider": "gemini"}, {}) == "claude"
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest tests/test_codex_provider_routing.py -v`
Expected: FAIL (`ImportError: resolve_agent_provider`)

- [ ] **Step 3: 해석 함수 구현** (`orchestrator/runner.py` 모듈 레벨, `_run_agent_step` 위쪽)

```python
# codex로 라우팅 가능한 웹 리서치 에이전트 (토큰 절약 대상)
CODEX_RESEARCH_AGENTS = {"flesh-researcher", "targeted-researcher"}


def resolve_agent_provider(agent: str, agent_def: dict, project_config: dict) -> str:
    """리서치 에이전트 provider 해석. 우선순위: 프로젝트 config > env > agents.json > claude."""
    if agent not in CODEX_RESEARCH_AGENTS:
        return "claude"
    for candidate in (
        project_config.get("research_provider"),
        os.getenv("AUTO_AGENT_RESEARCH_PROVIDER"),
        agent_def.get("provider"),
    ):
        if isinstance(candidate, str) and candidate.strip().lower() in {"claude", "codex"}:
            return candidate.strip().lower()
    return "claude"
```

- [ ] **Step 4: 해석 테스트 통과 확인**

Run: `python3 -m pytest tests/test_codex_provider_routing.py -v`
Expected: PASS (5건)

- [ ] **Step 5: codex 실행 메서드 추가** (`PipelineRunner` 내부, `_run_agent_step` 아래)

```python
    def _run_codex_agent_step(
        self, step: dict, step_id: str, agent_def: dict,
        prompt: str, outputs: list, timeout_sec: int,
    ) -> StepResult:
        """codex exec로 에이전트 스텝 실행. 실패 시 status=failed 반환(호출부가 claude 폴백)."""
        from auto_agent.utils import codex_cli as codex_cli_util

        last_msg = self.project_dir / f".codex_last_{step_id}.txt"
        try:
            cmd = codex_cli_util.build_codex_exec_cmd(
                workdir=self.project_dir,
                output_last_message=str(last_msg),
                model=agent_def.get("codex_model"),
                search=True,
            )
        except FileNotFoundError as e:
            return StepResult(step_id=step_id, status="failed", error=str(e))

        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        env.pop("CLAUDECODE", None)

        print(f"\n    → codex {step['agent']} (search=on, timeout={timeout_sec}s)", flush=True)
        try:
            proc = subprocess.Popen(
                cmd, cwd=str(self.project_dir), env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", **subprocess_kwargs(),
            )
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            proc.kill()
            return StepResult(step_id=step_id, status="failed", error=f"codex timeout ({timeout_sec}s)")
        except Exception as e:
            return StepResult(step_id=step_id, status="failed", error=f"codex 실행 오류: {e}")

        if proc.returncode != 0:
            return StepResult(step_id=step_id, status="failed",
                              error=f"codex exit={proc.returncode}: {(stderr or stdout)[-400:]}")

        # 산출물 검증 — 하나라도 없으면 실패 처리 (claude 폴백 유도)
        missing = [o for o in outputs if not self._agent_output_exists(o)]
        if missing:
            return StepResult(step_id=step_id, status="failed",
                              error=f"codex 산출물 미생성: {missing}")
        return StepResult(
            step_id=step_id, status="completed",
            output_files=[str(self._resolve_output_path(o)) for o in outputs],
        )

    def _agent_output_exists(self, out: str) -> bool:
        """출력 계약 존재 확인 — resume 체크와 동일한 규칙(디렉토리/패턴/파일)."""
        out_path = self._resolve_output_path(out)
        if out.endswith("/") or out.endswith("\\"):
            return out_path.exists() and out_path.is_dir() and any(out_path.iterdir())
        if "{" in out:
            pattern = out_path.name.replace("{", "*").replace("}", "*")
            return out_path.parent.exists() and any(out_path.parent.glob(pattern))
        return out_path.exists()
```

> 참고: `_run_agent_step`의 resume 체크 블록(디렉토리/패턴 검사)과 동일 규칙이므로, 구현 시 resume 블록도 `_agent_output_exists`를 쓰도록 정리해 중복을 제거한다.

- [ ] **Step 6: `_run_agent_step`에 분기 삽입**

프롬프트 빌드(`prompt = self._build_agent_prompt(step)`) 직후, Claude CLI 명령 구성 **앞**에:

```python
        # ── codex provider 분기 (웹 리서치 에이전트 토큰 절약) ──
        provider = resolve_agent_provider(agent, agent_def, self.state.config)
        if provider == "codex":
            result = self._run_codex_agent_step(step, step_id, agent_def, prompt, outputs, timeout_sec)
            if result.status == "completed":
                return result
            print(f"    [codex→claude 폴백] {result.error}", flush=True)
            # 이하 기존 claude CLI 경로로 계속 진행
```

- [ ] **Step 7: 전체 테스트 + 임포트 확인**

Run: `python3 -c "from auto_agent.orchestrator.runner import resolve_agent_provider" && python3 -m pytest tests/ -q`
Expected: 임포트 OK, 전체 그린

- [ ] **Step 8: 커밋**

```bash
git add auto_agent/orchestrator/runner.py tests/test_codex_provider_routing.py
git commit -m "feat(runner): 웹 리서치 에이전트 codex provider 분기 + claude 폴백"
```

---

### Task 5: agents.json provider 필드 + SKILL.md 중립화 + .env.example

**Files:**
- Modify: `auto_agent/data/agents.json` (flesh-researcher 78행 부근, targeted-researcher 113행 부근)
- Modify: `auto_agent/data/skills/agents/flesh-researcher/SKILL.md`, `auto_agent/data/skills/agents/targeted-researcher/SKILL.md`
- Modify: `.env.example`

- [ ] **Step 1: agents.json에 provider 추가**

flesh-researcher, targeted-researcher 정의 각각에 (JSON 필드 추가, Edit 도구 사용):
```json
"provider": "codex",
```

- [ ] **Step 2: SKILL.md 도구 지시 중립화**

두 SKILL.md에서 `WebSearch`/`WebFetch` 도구명을 직접 지시하는 문장을 검색(`grep -n "WebSearch\|WebFetch" auto_agent/data/skills/agents/{flesh-researcher,targeted-researcher}/SKILL.md`)해서, "사용 가능한 웹 검색 도구로 검색하고, 웹 페이지를 열람하여" 같은 중립 표현으로 수정. 산출물 계약(파일명·스키마) 문장은 변경 금지.

- [ ] **Step 3: .env.example 추가**

```bash
# 리서치 에이전트 provider (claude|codex) — 기본 codex, 프로젝트 config research_provider가 우선
AUTO_AGENT_RESEARCH_PROVIDER=codex
```

- [ ] **Step 4: JSON 유효성 + 전체 테스트**

Run: `python3 -c "import json; json.load(open('auto_agent/data/agents.json'))" && python3 -m pytest tests/ -q`
Expected: 에러 없음, 전체 그린

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/data/agents.json auto_agent/data/skills/agents/flesh-researcher/SKILL.md auto_agent/data/skills/agents/targeted-researcher/SKILL.md .env.example
git commit -m "feat(agents): 리서치 2종 provider=codex 기본 + SKILL.md 도구 지시 중립화"
```

---

### Task 6: 리서치 codex 실전 스모크 (1스텝)

**Files:** 없음 (검증 전용)

- [ ] **Step 1: targeted-researcher 단독 실행**

기존 프로젝트 중 `research_questions.json`이 있는 slug를 골라:
Run: `auto-agent run --project <slug> --only step_2_target --force` (또는 `--from`/강제 재실행 플래그는 CLI `--help`로 확인)
Expected: 로그에 `→ codex targeted-researcher`가 찍히고 `targeted_claims.json` 생성/갱신, 스키마 유효.

- [ ] **Step 2: 폴백 경로 확인**

Run: `AUTO_AGENT_RESEARCH_PROVIDER=claude auto-agent run --project <slug> --only step_2_target --force`
Expected: 기존 claude CLI 경로로 실행됨 (`→ CLI targeted-researcher`).

- [ ] **Step 3: 결과를 사용자에게 보고** (토큰 소모 비교 포함 가능하면)

---

### Task 7: gpt-image-2 프롬프트 빌더 `tools/codex_prompt.py`

**Files:**
- Create: `auto_agent/tools/codex_prompt.py`
- Test: `tests/test_codex_prompt.py`

**Interfaces:**
- Consumes: `auto_agent/tools/image_generate._translate_to_english`, `_load_art_style`
- Produces:
  - `SIZE_LOCK: dict[str, str]` (AR → WxH)
  - `build_codex_image_prompt(description: str, style_keywords: str, ar: str = "16:9") -> tuple[str, str]` — (프롬프트, size). 프롬프트 끝은 `AR x:y`.
  - `validate_prompt(prompt: str) -> tuple[bool, str]` — check_prompt.mjs 존재 시 실행, 없으면 (True, "validator absent")

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_codex_prompt.py`)

```python
from unittest.mock import patch

from auto_agent.tools.codex_prompt import SIZE_LOCK, build_codex_image_prompt, validate_prompt


def test_size_lock_table():
    assert SIZE_LOCK["16:9"] == "1792x1024"
    assert SIZE_LOCK["9:16"] == "1024x1792"
    assert SIZE_LOCK["1:1"] == "1024x1024"
    assert SIZE_LOCK["2:3"] == "1024x1536"


@patch("auto_agent.tools.codex_prompt._translate", side_effect=lambda t: t)
def test_prompt_ends_with_ar_token(mock_tr):
    prompt, size = build_codex_image_prompt("a lighthouse on a cliff", "warm watercolor", ar="16:9")
    assert prompt.rstrip().endswith("AR 16:9")
    assert size == "1792x1024"
    assert not prompt.startswith("[")  # 앞머리 브래킷 금지


@patch("auto_agent.tools.codex_prompt._translate", side_effect=lambda t: t)
def test_prompt_contains_style(mock_tr):
    prompt, _ = build_codex_image_prompt("a cat", "bold flat colors", ar="1:1")
    assert "bold flat colors" in prompt


def test_validate_prompt_absent_validator(tmp_path, monkeypatch):
    monkeypatch.setattr("auto_agent.tools.codex_prompt.VALIDATOR_PATH", tmp_path / "none.mjs")
    ok, msg = validate_prompt("hello AR 1:1")
    assert ok is True
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest tests/test_codex_prompt.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 3: 구현** (`auto_agent/tools/codex_prompt.py`)

```python
"""gpt-image-2(codex 내장 image_gen)용 프롬프트 빌더 — 공냥 규격.

철칙: 네거티브 문구 금지(긍정형만), 앞머리 브래킷 금지, 끝에 `AR x:y` 토큰 하나,
사이즈 락 6종. FAL 프롬프트 빌더(image_generate)와 별도 경로.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Tuple

from auto_agent.tools.image_generate import _translate_to_english as _translate

# 사이즈 락 (codex 6종, auto 금지)
SIZE_LOCK = {
    "16:9": "1792x1024",
    "3:2": "1536x1024",
    "4:3": "1536x1024",
    "9:16": "1024x1792",
    "1:1": "1024x1024",
    "2:3": "1024x1536",
    "3:4": "1024x1536",
    "4:5": "1024x1536",
}

VALIDATOR_PATH = Path.home() / ".claude/skills/image-prompt/scripts/check_prompt.mjs"


def build_codex_image_prompt(description: str, style_keywords: str, ar: str = "16:9") -> Tuple[str, str]:
    """씬 묘사(한글 가능) + 스타일 키워드 → (완성 프롬프트, size).

    6섹션 축약형: Scene → Texture/Medium(스타일) → 끝 AR 토큰.
    조명/색은 스타일 키워드에 이미 녹아 있는 경우가 대부분이라 중복 주입하지 않는다.
    """
    size = SIZE_LOCK.get(ar, SIZE_LOCK["16:9"])
    scene_en = _translate(description).strip().rstrip(".")
    style = style_keywords.strip().rstrip(".")
    parts = [scene_en]
    if style:
        parts.append(style)
    prompt = ". ".join(parts) + f". AR {ar}"
    return prompt, size


def validate_prompt(prompt: str) -> Tuple[bool, str]:
    """check_prompt.mjs 검증. 스크립트/node 부재 시 통과 처리(경고 메시지 반환)."""
    node = shutil.which("node")
    if not node or not VALIDATOR_PATH.exists():
        return True, "validator absent"
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(prompt)
        tmp = f.name
    try:
        res = subprocess.run([node, str(VALIDATOR_PATH), tmp],
                             capture_output=True, text=True, timeout=30)
        out = (res.stdout or "").strip()
        try:
            ok = bool(json.loads(out).get("ok"))
        except Exception:
            ok = res.returncode == 0
        return ok, out[-300:]
    except Exception as e:
        return True, f"validator error(통과 처리): {e}"
    finally:
        Path(tmp).unlink(missing_ok=True)
```

> 구현 시 `check_prompt.mjs`의 실제 입출력(파일 인자 형태, `ok` 필드)을 `node ~/.claude/skills/image-prompt/scripts/check_prompt.mjs --help` 또는 소스로 먼저 확인하고 위 파싱을 맞춘다.

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest tests/test_codex_prompt.py -v`
Expected: PASS (4건)

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/codex_prompt.py tests/test_codex_prompt.py
git commit -m "feat(tools): gpt-image-2 공냥 규격 프롬프트 빌더 + check_prompt 검증 훅"
```

---

### Task 8: 병렬 러너 `tools/codex_fleet.py`

**Files:**
- Create: `auto_agent/tools/codex_fleet.py`
- Test: `tests/test_codex_fleet.py`

**Interfaces:**
- Consumes: `auto_agent/tools/codex_image.codex_generate(prompt, out_path, *, ref_images=None, size=None, cd=None, timeout=420) -> tuple[bool, str]` (세션이 out_path로 직접 복사 + 세션ID 2차 회수 → 병렬 레이스 없음)
- Produces:
  - `@dataclass CodexImageJob(idx: int, prompt: str, size: str, out_path: Path, ref_images: list | None = None)`
  - `@dataclass CodexImageResult(idx: int, success: bool, error: str = "")`
  - `run_codex_batch(jobs: list[CodexImageJob], *, on_done=None, timeout: int = 240) -> list[CodexImageResult]`
  - 병렬 수: env `CODEX_IMG_PARALLEL` (기본 auto = min(작업수, 여유RAM//0.4GB, 32), 최소 1)

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_codex_fleet.py`)

```python
from pathlib import Path
from unittest.mock import patch

from auto_agent.tools.codex_fleet import CodexImageJob, run_codex_batch, _auto_parallel


def _job(i, tmp_path):
    return CodexImageJob(idx=i, prompt=f"p{i}. AR 16:9", size="1792x1024",
                         out_path=tmp_path / f"scene_{i:03d}_gen_01.png")


@patch("auto_agent.tools.codex_fleet.codex_generate", return_value=(True, ""))
def test_all_success(mock_gen, tmp_path):
    results = run_codex_batch([_job(i, tmp_path) for i in range(3)])
    assert [r.success for r in sorted(results, key=lambda r: r.idx)] == [True] * 3
    assert mock_gen.call_count == 3


@patch("auto_agent.tools.codex_fleet.codex_generate",
       side_effect=[(True, ""), (False, "moderation"), (True, "")])
def test_partial_failure_reported(mock_gen, tmp_path):
    results = sorted(run_codex_batch([_job(i, tmp_path) for i in range(3)]), key=lambda r: r.idx)
    assert sum(1 for r in results if not r.success) == 1


def test_auto_parallel_env_override(monkeypatch):
    monkeypatch.setenv("CODEX_IMG_PARALLEL", "7")
    assert _auto_parallel(100) == 7


def test_auto_parallel_bounds(monkeypatch):
    monkeypatch.delenv("CODEX_IMG_PARALLEL", raising=False)
    assert 1 <= _auto_parallel(2) <= 2
    assert _auto_parallel(1000) <= 32
```

> 참고: partial_failure 테스트의 `side_effect` 순서는 병렬 실행 시 어느 잡에 배정될지 비결정적이지만, 성공 2/실패 1 총계는 결정적이므로 총계만 단언한다.

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest tests/test_codex_fleet.py -v`
Expected: FAIL (모듈 없음)

- [ ] **Step 3: 구현** (`auto_agent/tools/codex_fleet.py`)

```python
"""codex 내장 image_gen 병렬 러너 (codex-fleet 패턴).

codex_generate가 세션 안에서 out_path로 직접 복사하므로(2차 회수는 세션ID 기반)
워커 간 파일 회수 레이스가 없다 — mtime 전역 스캔 방식을 쓰지 않는 이유.
계정 한도(250 IPM)·RAM이 실질 병목 → 병렬 수는 여유 RAM 기반 auto.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from auto_agent.tools.codex_image import codex_generate

HARD_CAP = 32
RAM_PER_PROC_GB = 0.4


@dataclass
class CodexImageJob:
    idx: int
    prompt: str
    size: str
    out_path: Path
    ref_images: Optional[list] = None


@dataclass
class CodexImageResult:
    idx: int
    success: bool
    error: str = ""


def _free_ram_gb() -> float:
    try:
        import psutil  # 선택 의존성
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        return 4.0  # 보수적 기본값 → 워커 ~10


def _auto_parallel(n_jobs: int) -> int:
    env = os.getenv("CODEX_IMG_PARALLEL", "").strip()
    if env.isdigit() and int(env) > 0:
        return int(env)
    cap = int(_free_ram_gb() / RAM_PER_PROC_GB)
    return max(1, min(n_jobs, cap, HARD_CAP))


def run_codex_batch(
    jobs: List[CodexImageJob],
    *,
    on_done: Optional[Callable[[CodexImageResult], None]] = None,
    timeout: int = 240,
) -> List[CodexImageResult]:
    if not jobs:
        return []
    workers = _auto_parallel(len(jobs))
    results: List[CodexImageResult] = []

    def _one(job: CodexImageJob) -> CodexImageResult:
        ok, err = codex_generate(
            job.prompt, job.out_path,
            ref_images=job.ref_images, size=job.size, timeout=timeout,
        )
        return CodexImageResult(idx=job.idx, success=ok, error=err)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, j): j for j in jobs}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            if on_done:
                on_done(res)
    return results
```

- [ ] **Step 4: 통과 확인**

Run: `python3 -m pytest tests/test_codex_fleet.py -v`
Expected: PASS (4건)

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/codex_fleet.py tests/test_codex_fleet.py
git commit -m "feat(tools): codex-fleet 병렬 이미지 러너 — RAM 기반 auto 병렬 + 세션 회수"
```

---

### Task 9: `image_batch_module.py` backend 라우터 + FAL 폴백

**Files:**
- Modify: `auto_agent/modules/image_batch_module.py` (run_batch 66행~, 씬 generate 루프 179행~, 캐릭터 루프 94행~)
- Test: `tests/test_image_backend_router.py`

**Interfaces:**
- Consumes: Task 7 `build_codex_image_prompt`/`validate_prompt`, Task 8 `run_codex_batch`/`CodexImageJob`, 기존 FAL 경로(`_build_scene_fal_input`, `fal_queue.run_batch`)
- Produces: `_resolve_image_backend() -> str` ("codex"|"fal"), summary dict에 `"backend"` 키 추가

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_image_backend_router.py`)

```python
from unittest.mock import patch

from auto_agent.modules.image_batch_module import _resolve_image_backend


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_default_codex(mock_av, monkeypatch):
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    assert _resolve_image_backend() == "codex"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_env_fal(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "fal")
    assert _resolve_image_backend() == "fal"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=False)
def test_degrade_to_fal_when_codex_missing(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "codex")
    assert _resolve_image_backend() == "fal"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_invalid_value_default_codex(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "midjourney")
    assert _resolve_image_backend() == "codex"
```

- [ ] **Step 2: 실패 확인**

Run: `python3 -m pytest tests/test_image_backend_router.py -v`
Expected: FAIL (`ImportError: _resolve_image_backend`)

- [ ] **Step 3: 라우터 구현** (`image_batch_module.py` 상단 import + 함수)

import 추가:
```python
from auto_agent.tools.codex_image import codex_available
from auto_agent.tools.codex_fleet import CodexImageJob, run_codex_batch
from auto_agent.tools.codex_prompt import build_codex_image_prompt, validate_prompt
```

```python
def _resolve_image_backend() -> str:
    """이미지 backend 결정: env IMAGE_BACKEND(codex|fal), 기본 codex, codex 부재 시 fal 강등."""
    val = (os.getenv("IMAGE_BACKEND") or "codex").strip().lower()
    if val not in {"codex", "fal"}:
        val = "codex"
    if val == "codex" and not codex_available():
        _progress("codex CLI 없음 — FAL로 강등", level="warn")
        val = "fal"
    return val
```

- [ ] **Step 4: 라우터 테스트 통과 확인**

Run: `python3 -m pytest tests/test_image_backend_router.py -v`
Expected: PASS (4건)

- [ ] **Step 5: 씬 generate 루프에 codex 경로 삽입**

`run_batch` 진입부에서 `backend = _resolve_image_backend()` 결정, summary에 `"backend": backend` 포함.

씬 generate 배치(179~222행 부근)를 다음 구조로 변경 — 기존 FAL 잡 빌드 루프는 그대로 두고, backend에 따라 실행 엔진만 교체:

```python
        # backend == "codex": 공냥 프롬프트로 codex-fleet 배치, 실패 씬만 FAL 폴백
        if backend == "codex":
            style_keywords = art_style.get("style_prompt", "") or art_style.get("prompt", "")
            codex_jobs, fal_fallback_scenes = [], []
            for i, (scene, out_path) in enumerate(gen_targets):  # gen_targets: 기존 루프에서 (scene, 저장경로) 수집
                desc = (scene.get("imageAsset") or {}).get("prompt", "") or scene.get("headline", "")
                prompt, size = build_codex_image_prompt(desc, style_keywords, ar="16:9")
                ok, msg = validate_prompt(prompt)
                if not ok:
                    _progress(f"scene {scene.get('id')}: 프롬프트 검증 실패 → FAL 폴백 ({msg})", level="warn")
                    fal_fallback_scenes.append(scene)
                    continue
                codex_jobs.append(CodexImageJob(idx=i, prompt=prompt, size=size, out_path=out_path))

            _progress(f"씬 {len(codex_jobs)}개 codex-fleet 배치 시작...")
            for res in run_codex_batch(codex_jobs, on_done=lambda r: _progress(
                    f"codex scene idx={r.idx} {'OK' if r.success else 'FAIL: ' + r.error[:120]}")):
                if not res.success:
                    fal_fallback_scenes.append(gen_targets[res.idx][0])

            if fal_fallback_scenes:
                _progress(f"codex 실패 {len(fal_fallback_scenes)}개 → FAL 폴백")
                # 기존 FAL 잡 빌드(_build_scene_fal_input) + fal_queue.run_batch 경로 재사용
```

> 구현 디테일: 기존 루프가 만드는 저장 경로/성공·실패 카운팅/`image_assets.json` 갱신 로직은 **그대로 재사용**한다. codex 성공 씬도 기존 성공 처리 함수(에셋 등록)를 통과시킨다. 기존 파일 삭제 없음 — 항상 `_gen_NN` 버전 규칙.

캐릭터 배치(94~140행)도 동일 라우팅: backend codex면 `CodexImageJob(prompt=build_codex_image_prompt(char description, style_keywords, ar="2:3")[0], size="1024x1536", ref_images=[person_photo] if person_photo else None)`, 실패 캐릭터만 기존 `_build_character_fal_input` FAL 경로로.

- [ ] **Step 6: 전체 테스트 회귀**

Run: `python3 -m pytest tests/ -q`
Expected: 전체 그린

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/modules/image_batch_module.py tests/test_image_backend_router.py
git commit -m "feat(image): backend 라우터 — codex-fleet 기본 + 실패분 FAL 개별 폴백"
```

---

### Task 10: env 문서화 + 이미지 실전 스모크

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: .env.example 추가**

```bash
# 이미지 생성 backend (codex|fal) — 기본 codex, codex CLI 부재 시 자동 FAL 강등
IMAGE_BACKEND=codex
# codex 이미지 병렬 수 (기본 auto: 여유RAM 기반, 최대 32)
# CODEX_IMG_PARALLEL=8
```

- [ ] **Step 2: 이미지 스모크 (2~3씬)**

기존 프로젝트에서 scene_specs가 있는 slug로, 씬 2~3개만 남긴 사본 scene_specs로 스크래치 프로젝트 디렉토리를 구성하거나, 대시보드 재생성 경로 대신 모듈 직접 호출:
Run: `PROJECT_DIR=<사본 프로젝트 경로> python3 -m auto_agent.modules.image_batch_module`
Expected: `codex-fleet 배치 시작` 로그, `images/`에 `_gen_NN.png` 생성, 기존 파일 삭제 없음, summary에 `"backend": "codex"`.

- [ ] **Step 3: FAL 강등 스모크**

Run: `IMAGE_BACKEND=fal PROJECT_DIR=<동일 경로> python3 -m auto_agent.modules.image_batch_module`
Expected: FAL 경로로 실행 (기존 동작 회귀 확인).

- [ ] **Step 4: 최종 커밋 + 보고**

```bash
git add .env.example
git commit -m "docs(env): IMAGE_BACKEND / CODEX_IMG_PARALLEL / AUTO_AGENT_RESEARCH_PROVIDER 문서화"
```

스모크 결과(생성 이미지 경로, 소요 시간, 폴백 발생 여부)를 사용자에게 보고.
