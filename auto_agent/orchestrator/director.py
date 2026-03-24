"""
Director Agent Phase 2 -- Anthropic API Tool Loop

Director Agent를 Anthropic API 도구 루프로 실행하는 모듈.
프리셋 검증, 컨텍스트 빌드, 도구 기반 파이프라인 제어를 담당한다.

크로스플랫폼 규칙:
  - Path() 사용, 문자열 결합 경로 금지
  - open/read_text/write_text에 encoding="utf-8" 필수
  - print()에 유니코드 특수문자 금지 (ASCII만)
  - subprocess 호출 시 encoding="utf-8" 필수
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

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
workspace: {runner.project_dir}
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
# 2. run_director
# ═══════════════════════════════════════

def run_director(runner: "PipelineRunner", from_step: str = None) -> None:
    """Director Agent를 Anthropic API 도구 루프로 실행."""
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

    # 3. 컨텍스트 빌드
    context = build_director_context(runner)

    # 4. 시스템 프롬프트 로드
    system_prompt_path = (
        Path(__file__).resolve().parent.parent / "data" / "prompts" / "director-system.md"
    )
    system_prompt = system_prompt_path.read_text(encoding="utf-8")

    # 5. 도구 실행기
    from auto_agent.orchestrator.director_tools import DirectorToolExecutor
    tool_executor = DirectorToolExecutor(runner)

    # 6. 초기 메시지
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

    # 7. from_step 처리
    start_instruction = ""
    if from_step:
        start_instruction = (
            f"\n\n{from_step}부터 시작하세요. 이전 스텝은 이미 완료되어 있습니다."
        )

    # 8. 프롬프트 조합
    initial_prompt = f"{context}{start_instruction}\n\n파이프라인을 시작하세요."

    # 9. API 도구 루프 실행
    from auto_agent.orchestrator.tools import DIRECTOR_TOOL_SCHEMAS
    _run_tool_loop(runner, tool_executor, system_prompt, initial_prompt, DIRECTOR_TOOL_SCHEMAS)

    # 10. 완료 처리
    runner._finalize()


# ═══════════════════════════════════════
# 3. _run_tool_loop
# ═══════════════════════════════════════

def _run_tool_loop(
    runner: "PipelineRunner",
    executor,
    system_prompt: str,
    initial_prompt: str,
    tool_schemas: list,
) -> None:
    """Anthropic API로 Director 도구 루프 실행."""
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": initial_prompt}]

    model = os.environ.get("DIRECTOR_MODEL", "claude-sonnet-4-5-20250929")
    max_iterations = 100

    print(f"\n  [Director] starting tool loop (model={model}, max_iter={max_iterations})")

    for i in range(max_iterations):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                tools=tool_schemas,
                messages=messages,
            )
        except Exception as e:
            print(f"  [Director] API error: {e}")
            break

        # 응답을 messages에 추가
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # 도구 호출 수집
        tool_calls = [b for b in assistant_content if b.type == "tool_use"]

        if not tool_calls:
            # 도구 호출 없음 = Director가 완료 판단
            for block in assistant_content:
                if hasattr(block, "text") and block.text:
                    print(f"  [Director] {block.text[:300]}")
            break

        # 도구 실행 + 결과 반환
        tool_results = []
        for tc in tool_calls:
            input_summary = json.dumps(tc.input, ensure_ascii=False)
            if len(input_summary) > 100:
                input_summary = input_summary[:100] + "..."
            print(f"  [Director] -> {tc.name}({input_summary})")
            result = executor.execute(tc.name, tc.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

        # stop_reason 확인
        if response.stop_reason == "end_turn" and not tool_calls:
            break
    else:
        print(f"  [Director] max iterations ({max_iterations}) reached")
