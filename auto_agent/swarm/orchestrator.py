"""SwarmOrchestrator — multi-agent swarm 전체 실행기.

흐름:
  Phase 1: SkeletonIdentifyAgent (sequential, 단일)
    → outline.json + research_targets.json + research_queue.jsonl 초기화
  Phase 2: parallel swarm (asyncio.gather)
    ├ ResearcherAgent x N (병렬)
    ├ WriterAgent x 1
    └ ValidatorAgent x 1 (실시간 환각 감시 + done 신호)
  Phase 3: compile_swarm (sequential, 단일)
    → workspace 산출물을 기존 파이프라인 형식으로 변환

종료 조건:
  - validator가 meta.status = "done" 설정 (writer complete + citation_rate OK + invalid=0)
  - 또는 timeout (기본 1800s)
  - 또는 모든 agent가 idle + queue empty (deadlock 방지)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .agents.compiler import compile_swarm
from .agents.researcher import ResearcherAgent
from .agents.skeleton_identify import SkeletonIdentifyAgent
from .agents.validator import ValidatorAgent
from .agents.writer import WriterAgent
from .base_agent import BaseAgent
from .workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_swarm(
    *,
    workspace_dir: Path,
    output_dir: Path,
    topic: str,
    duration_min: int = 1,
    writing_style: str = "iromism",
    creative_brief: str = "",
    reference_examples: str = "",
    n_researchers: int = 5,
    timeout_sec: int = 1800,
    skeleton_model: str = "claude-opus-4-6",
    researcher_model: str = "claude-sonnet-4-6",
    writer_model: str = "claude-opus-4-6",
) -> Dict[str, Any]:
    """Swarm 전체 실행. Phase 1 → Phase 2 (parallel) → Phase 3 (compile).

    Returns: {"status", "phase", "summary"}
    """
    workspace = SwarmWorkspace(workspace_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    started_at = _utcnow()
    meta = {
        "topic": topic,
        "duration_min": duration_min,
        "writing_style": writing_style,
        "started_at": started_at,
        "status": "phase_1",
        "n_researchers": n_researchers,
    }
    workspace.write_json_atomic("meta.json", meta)
    workspace.emit_event("orchestrator", "swarm_started",
                         topic=topic, n_researchers=n_researchers, duration_min=duration_min)

    # ─────────────────────────────────────
    # Phase 1: skeleton + identify (sequential)
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 1: skeleton + identify (model={skeleton_model}) ...", flush=True)
    si_agent = SkeletonIdentifyAgent(
        workspace=workspace,
        topic=topic,
        duration_min=duration_min,
        creative_brief=creative_brief,
        reference_examples=reference_examples,
        model=skeleton_model,
    )
    await si_agent.run()

    if not (workspace.exists("outline.json") and workspace.exists("research_targets.json")):
        workspace.emit_event("orchestrator", "phase_1_failed",
                             level="error", reason="missing outputs")
        meta = workspace.read_json("meta.json")
        meta["status"] = "failed"
        meta["failed_phase"] = "phase_1"
        workspace.write_json_atomic("meta.json", meta)
        return {"status": "failed", "phase": "phase_1", "reason": "missing outputs"}

    outline = workspace.read_json("outline.json")
    targets = workspace.read_json("research_targets.json")
    n_chapters = len(outline.get("chapters", []))
    n_targets = len(targets.get("targets", []))
    n_queries = len(workspace.all_jsonl("research_queue.jsonl"))
    print(f"[Swarm] Phase 1 done: {n_chapters} chapters, {n_targets} targets, {n_queries} queries", flush=True)

    meta = workspace.read_json("meta.json")
    meta["status"] = "phase_2"
    meta["phase_2_started_at"] = _utcnow()
    meta["chapters_count"] = n_chapters
    meta["targets_count"] = n_targets
    meta["queries_count"] = n_queries
    workspace.write_json_atomic("meta.json", meta)

    # ─────────────────────────────────────
    # Phase 2: parallel swarm
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 2: parallel swarm (researchers={n_researchers}, writer=1, validator=1) ...", flush=True)

    researchers: List[BaseAgent] = [
        ResearcherAgent(
            workspace=workspace,
            instance_id=f"R{i+1}",
            model=researcher_model,
        )
        for i in range(n_researchers)
    ]
    writer = WriterAgent(
        workspace=workspace,
        topic=topic,
        duration_min=duration_min,
        writing_style=writing_style,
        creative_brief=creative_brief,
        reference_examples=reference_examples,
        model=writer_model,
    )
    validator = ValidatorAgent(workspace=workspace)

    all_agents: List[BaseAgent] = list(researchers) + [writer, validator]

    # Done watcher — meta.status가 done/timeout/failed면 모든 agent stop
    async def watch_done() -> None:
        deadline = asyncio.get_event_loop().time() + timeout_sec
        while True:
            now = asyncio.get_event_loop().time()
            if now >= deadline:
                workspace.emit_event("orchestrator", "phase_2_timeout",
                                     level="warning", timeout_sec=timeout_sec)
                m = workspace.read_json("meta.json", default={})
                m["status"] = "timeout"
                workspace.write_json_atomic("meta.json", m)
                for a in all_agents:
                    a.stop()
                return

            m = workspace.read_json("meta.json", default={})
            if m.get("status") in ("done", "compiled", "stopped", "failed", "timeout"):
                for a in all_agents:
                    a.stop()
                return

            # Deadlock 검사: writer가 일정 시간 동안 진전 없고 queue도 비었으면 강제 종료
            # (간단 휴리스틱 — 30초마다)
            if int(now) % 30 == 0:
                queue_left = sum(
                    1 for q in workspace.all_jsonl("research_queue.jsonl")
                    if workspace.task_status(q.get("id", "")) == "pending"
                )
                outline_state = workspace.read_json("outline_state.json", default={})
                if outline_state.get("status") == "complete":
                    # Writer 끝났는데 validator가 done 신호 안 줌 → 강제 종료
                    workspace.emit_event("orchestrator", "force_done_after_writer_complete",
                                         level="info")
                    m = workspace.read_json("meta.json", default={})
                    m["status"] = "done"
                    workspace.write_json_atomic("meta.json", m)
                    for a in all_agents:
                        a.stop()
                    return

            await asyncio.sleep(2)

    # 모든 agent를 parallel로 실행 + watch_done
    agent_tasks = [asyncio.create_task(a.run()) for a in all_agents]
    watch_task = asyncio.create_task(watch_done())

    try:
        await asyncio.gather(*agent_tasks, return_exceptions=True)
    except Exception as e:
        logger.exception("Swarm Phase 2 error")
        workspace.emit_event("orchestrator", "phase_2_error",
                             level="error", error=f"{type(e).__name__}: {e}")
    finally:
        watch_task.cancel()
        try:
            await watch_task
        except asyncio.CancelledError:
            pass

    final_meta = workspace.read_json("meta.json", default={})
    phase_2_status = final_meta.get("status", "unknown")
    print(f"[Swarm] Phase 2 done (status={phase_2_status})", flush=True)

    if phase_2_status not in ("done", "timeout"):
        return {"status": "failed", "phase": "phase_2", "meta_status": phase_2_status}

    # ─────────────────────────────────────
    # Phase 3: compile
    # ─────────────────────────────────────
    print("[Swarm] Phase 3: compile to output ...", flush=True)
    try:
        summary = compile_swarm(workspace, output_dir)
    except Exception as e:
        logger.exception("Compile error")
        workspace.emit_event("orchestrator", "compile_error",
                             level="error", error=f"{type(e).__name__}: {e}")
        return {"status": "failed", "phase": "phase_3", "error": str(e)}

    meta = workspace.read_json("meta.json")
    meta["status"] = "compiled"
    meta["compiled_at"] = _utcnow()
    meta["compile_summary"] = {k: v for k, v in summary.items() if k != "outputs"}
    workspace.write_json_atomic("meta.json", meta)

    workspace.emit_event("orchestrator", "swarm_completed",
                         level="success",
                         manuscript_chars=summary.get("manuscript_chars", 0),
                         claims_total=summary.get("claims_total", 0),
                         claims_used=summary.get("claims_used", 0))

    print(f"[Swarm] ✓ Completed — manuscript {summary.get('manuscript_chars', 0)}자, "
          f"claims {summary.get('claims_used', 0)}/{summary.get('claims_total', 0)}", flush=True)

    return {
        "status": "success",
        "phase": "compiled",
        "summary": summary,
        "meta": meta,
    }
