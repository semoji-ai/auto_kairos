"""
Director Agent Phase 2 -- Claude CLI Tool Loop

Director Agent를 Claude CLI로 실행하는 모듈.
프리셋 검증, 컨텍스트 빌드, Claude CLI 기반 파이프라인 제어를 담당한다.

Director는 Read/Write/Bash/Glob 도구를 사용하여:
  - Bash로 step_executor.py를 호출해 스텝 실행
  - Read로 결과 파일 검토
  - Write로 볼트에 선호도 기록

크로스플랫폼 규칙:
  - Path() 사용, 문자열 결합 경로 금지
  - open/read_text/write_text에 encoding="utf-8" 필수
  - print()에 유니코드 특수문자 금지 (ASCII만)
  - subprocess 호출 시 encoding="utf-8" 필수
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from auto_agent.orchestrator.runner import PipelineRunner


# ═══════════════════════════════════════
# 1. build_director_context
# ═══════════════════════════════════════

def build_director_context(runner: "PipelineRunner") -> str:
    """프리셋 + 볼트 선호도 + pipeline 요약 + 프로젝트 상태를 조립."""
    config = runner.state.config
    preset_path = config.get("art_style", "")

    # 1. 프리셋 로드
    preset_text = ""
    if preset_path:
        from auto_agent.paths import get_workspace_dir, get_data_dir
        for base in [get_workspace_dir(), get_data_dir()]:
            full = base / preset_path
            if full.exists():
                from auto_agent.data.artstyle.preset_schema import load_preset
                preset = load_preset(full)
                preset_text = json.dumps(preset, indent=2, ensure_ascii=False)
                break

    # 2. 볼트 선호도 로드
    vault_prefs = ""
    preset_id = Path(preset_path).stem if preset_path else "general"
    from auto_agent.paths import get_workspace_dir
    pref_file = get_workspace_dir() / ".vault" / "preferences" / f"{preset_id}.md"
    if pref_file.exists():
        vault_prefs = pref_file.read_text(encoding="utf-8")

    # 3. pipeline.json 요약 (step별 한 줄)
    pipeline_summary = []
    for phase in runner.pipeline.get("phases", []):
        pipeline_summary.append(
            f"\n## {phase.get('name', phase['id'])} ({phase.get('execution', 'sequential')})"
        )
        for step in phase.get("steps", []):
            deps = step.get("depends_on", "")
            skip = " [skip]" if step.get("skip") else ""
            agent = step.get("agent", step.get("module", ""))
            pipeline_summary.append(
                f"  {step['id']}: {step.get('name', '')} -- {step.get('type', '')} "
                f"[{agent}]"
                f"{f' depends_on={deps}' if deps else ''}{skip}"
            )

    # 4. 프로젝트 정보
    topic = runner.project.get("topic") or config.get("topic", runner.project_slug)

    return f"""<project>
project: {runner.project_slug}
topic: {topic}
duration: {config.get('duration_minutes', '?')}min
writing_style: {config.get('writing_style', 'N/A')}
project_dir: {runner.project_dir}
</project>

<preset>
{preset_text if preset_text else "(preset not loaded)"}
</preset>

<vault_preferences>
{vault_prefs if vault_prefs else "(no accumulated preferences)"}
</vault_preferences>

<pipeline_steps>
{chr(10).join(pipeline_summary)}
</pipeline_steps>

<current_state>
completed: {runner.state.completed_steps}
failed: {runner.state.failed_steps}
skipped: {runner.state.skipped_steps}
</current_state>"""


# ═══════════════════════════════════════
# 2. build_director_prompt
# ═══════════════════════════════════════

def _build_step_executor_guide(runner: "PipelineRunner") -> str:
    """Director가 Bash로 스텝을 실행하기 위한 CLI 가이드."""
    python = sys.executable
    project_slug = runner.project_slug
    workspace = runner.project_dir

    return f"""<step_execution_guide>
스텝을 실행하려면 Bash 도구로 아래 명령을 사용하세요.

## 스텝 실행 (한 개)
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --step <step_id>
```
결과는 JSON으로 출력됩니다: {{"step_id": "...", "status": "completed|failed|skipped", "error": "..."}}

## 스텝 병렬 실행 (여러 개)
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --steps <step_id1>,<step_id2>,<step_id3>
```

## 스텝 재시도 (피드백 포함)
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --step <step_id> --retry --feedback "수정 지시 내용"
```

## 스텝 스킵
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --step <step_id> --skip --reason "스킵 사유"
```

## 파이프라인 상태 확인
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --status
```

## 메신저 메시지 전송
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --message "메시지 내용" --level info
```

## 볼트 선호도 기록
```bash
{python} -m auto_agent.orchestrator.step_executor --project {project_slug} --log-preference "선호도 내용" --preset-id quirky_cartoon
```

## 결과 파일 확인
Read 도구로 프로젝트 디렉토리의 파일을 직접 읽으세요:
- 리서치: {workspace}/research_report.json
- 원고: {workspace}/final_manuscript.md
- 씬 분할: {workspace}/scene_decomposition.json
- 씬 스펙: {workspace}/scene_specs.json
- 파이프라인 상태: {workspace}/pipeline_state.json
</step_execution_guide>"""


# ═══════════════════════════════════════
# 3. run_director
# ═══════════════════════════════════════

def run_director(runner: "PipelineRunner", from_step: Optional[str] = None) -> None:
    """Director Agent를 Claude CLI로 실행."""
    from auto_agent.orchestrator.runner import _notify

    # 1. 프리셋 preflight 검증
    config = runner.state.config
    preset_path = config.get("art_style", "")
    if preset_path:
        from auto_agent.paths import get_workspace_dir, get_data_dir
        from auto_agent.data.artstyle.preset_schema import load_preset, validate_preset
        preset_loaded = False
        for base in [get_workspace_dir(), get_data_dir()]:
            full = base / preset_path
            if full.exists():
                preset = load_preset(full)
                errors = validate_preset(preset)
                if errors:
                    print("\n  [ERROR] preset validation failed:")
                    for e in errors:
                        print(f"    - {e}")
                    raise SystemExit(1)
                staging = preset.get("image", {}).get("staging", "")
                if staging and staging not in ("cinematic", "flat"):
                    print(f"\n  [ERROR] unsupported staging mode: {staging}")
                    raise SystemExit(1)
                preset_loaded = True
                break
        if not preset_loaded:
            print(f"  [WARN] preset file not found: {preset_path}")

    # 2. 프로젝트 상태 업데이트
    runner.pm.update_project(runner.project["id"], status="in_progress")

    # 3. 컨텍스트 + 시스템 프롬프트 + 실행 가이드 조합
    context = build_director_context(runner)

    system_prompt_path = (
        Path(__file__).resolve().parent.parent / "data" / "prompts" / "director-system.md"
    )
    system_prompt = system_prompt_path.read_text(encoding="utf-8")

    step_guide = _build_step_executor_guide(runner)

    # from_step 처리
    start_instruction = ""
    if from_step:
        start_instruction = (
            f"\n\n{from_step}부터 시작하세요. 이전 스텝은 이미 완료되어 있습니다."
        )

    full_prompt = (
        f"{system_prompt}\n\n"
        f"{context}\n\n"
        f"{step_guide}"
        f"{start_instruction}\n\n"
        f"파이프라인을 시작하세요."
    )

    # 4. 초기 메시지
    cfg = runner.state.config
    art_name = Path(cfg.get("art_style", "")).stem if cfg.get("art_style") else "N/A"
    config_summary = (
        f"pipeline start | "
        f"style: {cfg.get('writing_style', 'N/A')} | "
        f"art: {art_name} | "
        f"duration: {cfg.get('duration_minutes', '?')}min"
    )
    _notify(
        "Director", config_summary,
        phase="pipeline", project=runner.project_slug, level="info",
    )

    # 5. 프롬프트 파일 저장
    prompt_file = runner.project_dir / ".director_prompt.md"
    prompt_file.write_text(full_prompt, encoding="utf-8")

    # 6. Claude CLI 실행
    _run_claude_cli(runner, prompt_file)

    # 7. 완료 처리
    runner._finalize()


# ═══════════════════════════════════════
# 4. _run_claude_cli
# ═══════════════════════════════════════

def _run_claude_cli(runner: "PipelineRunner", prompt_file: Path) -> None:
    """Claude CLI로 Director 세션 실행."""
    cli_path = runner._find_claude_cli()
    model = os.environ.get("DIRECTOR_MODEL", "claude-sonnet-4-5-20250929")
    max_turns = int(os.environ.get("DIRECTOR_MAX_TURNS", "80"))

    cmd = [
        cli_path,
        "--print",
        "--output-format", "json",
        "--model", model,
        "--max-turns", str(max_turns),
        "--allowedTools", "Read",
        "--allowedTools", "Write",
        "--allowedTools", "Bash",
        "--allowedTools", "Glob",
    ]

    print(f"\n  [Director] starting CLI session (model={model}, max_turns={max_turns})")

    env = os.environ.copy()
    env["PROJECT_NAME"] = runner.project_slug
    env.pop("CLAUDECODE", None)  # 중첩 세션 방지 해제

    prompt_text = prompt_file.read_text(encoding="utf-8")

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(runner.project_dir),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )

        stdout, stderr = proc.communicate(input=prompt_text, timeout=3600)

        if proc.returncode == 0:
            print("  [Director] CLI session completed successfully")
            # JSON 출력 파싱
            try:
                result = json.loads(stdout)
                cost = result.get("cost_usd", 0)
                turns = result.get("num_turns", 0)
                print(f"  [Director] turns={turns}, cost=${cost:.4f}")
            except (json.JSONDecodeError, TypeError):
                pass
        else:
            print(f"  [Director] CLI session failed (exit={proc.returncode})")
            if stderr:
                print(f"  [Director] stderr: {stderr[:500]}")

    except subprocess.TimeoutExpired:
        print("  [Director] CLI session timed out (1h)")
        proc.kill()
    except Exception as e:
        print(f"  [Director] error: {e}")
