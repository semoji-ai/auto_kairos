"""
Step Executor CLI -- Director Agent가 Bash로 호출하는 스텝 실행기.

사용법:
  python -m auto_agent.orchestrator.step_executor --project <slug> --step <step_id>
  python -m auto_agent.orchestrator.step_executor --project <slug> --steps <id1>,<id2>
  python -m auto_agent.orchestrator.step_executor --project <slug> --step <id> --retry --feedback "..."
  python -m auto_agent.orchestrator.step_executor --project <slug> --step <id> --skip --reason "..."
  python -m auto_agent.orchestrator.step_executor --project <slug> --status
  python -m auto_agent.orchestrator.step_executor --project <slug> --message "..." --level info
  python -m auto_agent.orchestrator.step_executor --project <slug> --log-preference "..." --preset-id <id>

크로스플랫폼 규칙:
  - Path() 사용, encoding="utf-8" 필수, ASCII 출력만
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path


def _get_runner(project_slug: str):
    """PipelineRunner 인스턴스 생성 (최소 초기화)."""
    from auto_agent.orchestrator.runner import PipelineRunner
    return PipelineRunner(project_slug)


def _find_step(runner, step_id: str) -> dict | None:
    for phase in runner.pipeline.get("phases", []):
        for step in phase.get("steps", []):
            if step["id"] == step_id:
                return step
    return None


def cmd_run_step(runner, step_id: str, feedback: str = "") -> dict:
    """단일 스텝 실행."""
    step = _find_step(runner, step_id)
    if not step:
        return {"step_id": step_id, "status": "failed", "error": f"step not found: {step_id}"}

    if feedback:
        step["_director_feedback"] = feedback

    result = runner._execute_step(step)
    result = runner._validate_step(step_id, result)
    runner.state.results[step_id] = result.__dict__

    if result.status == "completed":
        if step_id not in runner.state.completed_steps:
            runner.state.completed_steps.append(step_id)
        # failed에서 제거 (재시도 성공 시)
        if step_id in runner.state.failed_steps:
            runner.state.failed_steps.remove(step_id)
    elif result.status == "skipped":
        if step_id not in runner.state.skipped_steps:
            runner.state.skipped_steps.append(step_id)
    else:
        if step_id not in runner.state.failed_steps:
            runner.state.failed_steps.append(step_id)

    runner._save_state()
    step.pop("_director_feedback", None)

    return {
        "step_id": step_id,
        "status": result.status,
        "error": result.error or "",
        "duration_sec": getattr(result, "duration_sec", 0),
    }


def cmd_run_parallel(runner, step_ids: list[str]) -> dict:
    """여러 스텝 병렬 실행."""
    results = {}
    steps = []
    for sid in step_ids:
        step = _find_step(runner, sid)
        if not step:
            results[sid] = {"status": "failed", "error": f"step not found: {sid}"}
        else:
            steps.append((sid, step))

    with ThreadPoolExecutor(max_workers=min(len(steps), 10)) as pool:
        futures = {
            pool.submit(runner._execute_step, step): (sid, step)
            for sid, step in steps
        }
        for fut in as_completed(futures):
            sid, step = futures[fut]
            result = fut.result()
            result = runner._validate_step(sid, result)
            runner.state.results[sid] = result.__dict__
            if result.status == "completed":
                if sid not in runner.state.completed_steps:
                    runner.state.completed_steps.append(sid)
            elif result.status == "skipped":
                if sid not in runner.state.skipped_steps:
                    runner.state.skipped_steps.append(sid)
            else:
                if sid not in runner.state.failed_steps:
                    runner.state.failed_steps.append(sid)
            results[sid] = {"status": result.status, "error": result.error or ""}

    runner._save_state()
    return results


def cmd_skip_step(runner, step_id: str, reason: str) -> dict:
    """스텝 스킵."""
    if step_id not in runner.state.skipped_steps:
        runner.state.skipped_steps.append(step_id)
    if step_id in runner.state.failed_steps:
        runner.state.failed_steps.remove(step_id)
    runner.state.results[step_id] = {
        "step_id": step_id, "status": "skipped", "error": reason,
    }
    runner._save_state()

    from auto_agent.orchestrator.runner import _notify
    _notify("Director", f"[SKIP] {step_id}: {reason}",
            phase=runner.state.current_phase, project=runner.project_slug)

    return {"step_id": step_id, "status": "skipped", "reason": reason}


def cmd_status(runner) -> dict:
    """파이프라인 상태."""
    return {
        "completed": runner.state.completed_steps,
        "failed": runner.state.failed_steps,
        "skipped": runner.state.skipped_steps,
        "current_phase": runner.state.current_phase,
    }


def cmd_message(runner, text: str, level: str = "info") -> dict:
    """메신저 메시지 전송."""
    from auto_agent.orchestrator.runner import _notify
    _notify("Director", text,
            phase=runner.state.current_phase,
            project=runner.project_slug, level=level)
    return {"status": "sent"}


def cmd_log_preference(runner, note: str, preset_id: str = "general") -> dict:
    """볼트에 선호도 기록."""
    from auto_agent.paths import get_workspace_dir
    pref_dir = get_workspace_dir() / ".vault" / "preferences"
    pref_dir.mkdir(parents=True, exist_ok=True)
    pref_file = pref_dir / f"{preset_id}.md"

    if pref_file.exists():
        content = pref_file.read_text(encoding="utf-8")
    else:
        content = f"# {preset_id} preferences\n\n"

    date = datetime.now().strftime("%Y-%m-%d")
    content += f"- {note} ({date}, {runner.project_slug})\n"
    pref_file.write_text(content, encoding="utf-8")

    return {"status": "saved", "file": str(pref_file)}


def main():
    parser = argparse.ArgumentParser(
        prog="step_executor",
        description="Director Agent step executor CLI",
    )
    parser.add_argument("--project", required=True, help="project slug")
    parser.add_argument("--step", help="step ID to execute")
    parser.add_argument("--steps", help="comma-separated step IDs for parallel execution")
    parser.add_argument("--retry", action="store_true", help="retry failed step")
    parser.add_argument("--feedback", default="", help="director feedback for retry")
    parser.add_argument("--skip", action="store_true", help="skip step")
    parser.add_argument("--reason", default="", help="skip reason")
    parser.add_argument("--status", action="store_true", help="show pipeline status")
    parser.add_argument("--message", help="send messenger message")
    parser.add_argument("--level", default="info", help="message level")
    parser.add_argument("--log-preference", dest="log_preference", help="log preference to vault")
    parser.add_argument("--preset-id", dest="preset_id", default="general", help="preset ID")

    args = parser.parse_args()

    # .env 로드
    try:
        from dotenv import load_dotenv
        from auto_agent.paths import get_workspace_dir
        load_dotenv(get_workspace_dir() / ".env")
    except ImportError:
        pass

    runner = _get_runner(args.project)

    if args.status:
        result = cmd_status(runner)
    elif args.message:
        result = cmd_message(runner, args.message, args.level)
    elif args.log_preference:
        result = cmd_log_preference(runner, args.log_preference, args.preset_id)
    elif args.step and args.skip:
        result = cmd_skip_step(runner, args.step, args.reason)
    elif args.step and args.retry:
        result = cmd_run_step(runner, args.step, feedback=args.feedback)
    elif args.step:
        result = cmd_run_step(runner, args.step)
    elif args.steps:
        step_ids = [s.strip() for s in args.steps.split(",") if s.strip()]
        result = cmd_run_parallel(runner, step_ids)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
