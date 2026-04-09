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
from .agents.editor import EditorAgent
from .agents.researcher import ResearcherAgent
from .agents.skeleton_identify import SkeletonIdentifyAgent
from .agents.validator import ValidatorAgent
from .agents.writer import WriterAgent
from .base_agent import BaseAgent
from .claude_cli import call_claude_cli_with_retry
from .workspace import SwarmWorkspace

import json
import re

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# 2026-04-08: Writer-only recovery 패턴.
# swarm이 stalled로 끝났는데 claims pool은 충분하고 manuscript가 부분적으로만
# 작성된 경우, writer를 단발 호출 모드로 한 번 더 돌려서 manuscript 완성.
# Researcher는 다시 돌리지 않음 (이미 모인 fact 그대로 사용).
# 검증 결과: 78초 / $0.40 / 5 beats 한 번에 완성 (배의역사 1분 케이스).
WRITER_RECOVERY_MIN_CLAIMS = 30  # 이 값 이상이면 recovery 시도


async def _writer_only_recovery(
    workspace: SwarmWorkspace,
    *,
    topic: str,
    duration_min: int,
    writing_style: str,
    reference_examples: str,
    writer_model: str = "claude-opus-4-6",
) -> bool:
    """stalled swarm을 writer 단발 호출로 복구.

    조건:
      - claims.jsonl 충분 (>= WRITER_RECOVERY_MIN_CLAIMS)
      - outline.json 존재
      - manuscript는 부분/없음, status != complete

    동작:
      - 남은 beats 모두 한 번에 작성하라는 prompt로 단발 호출
      - 성공 시 outline_state.status = "complete" 가 자동 갱신됨
      - 호출 1회 (max_turns 30, timeout 400s)

    Returns: True if recovery succeeded (manuscript completed).
    """
    print("[Swarm] Recovery: writer-only single-shot mode ...", flush=True)
    workspace.emit_event("orchestrator", "recovery_started", level="info")

    outline = workspace.read_json("outline.json", default={})
    if not isinstance(outline, dict) or "chapters" not in outline:
        workspace.emit_event(
            "orchestrator", "recovery_skipped",
            level="warning", reason="no outline",
        )
        return False

    state = workspace.read_json("outline_state.json", default={})
    if state.get("status") == "complete":
        # 이미 완성된 상태 — recovery 불필요
        return True

    claims = workspace.all_jsonl("claims.jsonl")
    if len(claims) < WRITER_RECOVERY_MIN_CLAIMS:
        workspace.emit_event(
            "orchestrator", "recovery_skipped",
            level="warning",
            reason=f"insufficient claims ({len(claims)} < {WRITER_RECOVERY_MIN_CLAIMS})",
        )
        return False

    manuscript = workspace.read_text("manuscript.md") or ""
    register = workspace.read_json("character_register.json", default={"characters": []})
    characters = register.get("characters", [])

    beats_done = state.get("beats_done", [])
    beats_pending = state.get("beats_pending", [])

    # 첫 시도라 outline_state.json 초기화 안 된 케이스: outline의 모든 beat을 pending으로
    if not beats_pending and not beats_done:
        chapter = outline["chapters"][0]
        beats_pending = chapter.get("key_beats", [])
        # key_beats는 보통 string 리스트 (id가 아닌 설명문)이라 그대로 인덱스로
        beats_pending = [f"beat_{i}" for i in range(len(beats_pending))]

    # recovery는 beat 전체를 한 번에 써야 하므로 최근 30개 + 앞쪽 5개(초반 context)
    # claims[:60] 대신 최근 30개로 축소. 오래된 claims는 이미 manuscript에 반영됨.
    recovery_claims = claims[:5] + claims[-25:] if len(claims) > 30 else claims
    claims_summary = "\n".join(
        f"  - [{c.get('id','?')}] {c.get('text','')[:130]}"
        for c in recovery_claims
    )
    if len(claims) > 30:
        claims_summary = f"(전체 {len(claims)}개 중 대표 {len(recovery_claims)}개)\n" + claims_summary
    char_summary = "\n".join(
        f"  - id={c.get('id','?')} | {c.get('name_ko','')} ({c.get('name_en','')})"
        for c in characters
    )
    if not char_summary:
        char_summary = "  (없음)"

    target_chars = {1: 400, 3: 1200, 5: 2000, 10: 4000}.get(duration_min, duration_min * 400)
    ref_block = f"\n<reference_examples>\n{reference_examples}\n</reference_examples>\n" if reference_examples else ""

    # stable system prompt (캐시 대상): outline, project config, reference
    system_prompt = f"""당신은 swarm Phase 2의 writer (RECOVERY mode).
역할: 부분 작성된 manuscript를 한 번의 호출로 **완성**하기.
workspace_path: {workspace.dir}

⚠️ Recovery mode: 남은 beats 전부를 한 번에 작성해야 합니다. 추가 step 없습니다.

<project_config>
topic: {topic}
duration_min: {duration_min}
writing_style: {writing_style}
target_chars: 약 {target_chars}자 (±10%)
</project_config>
{ref_block}
<outline>
{json.dumps(outline, ensure_ascii=False, indent=2)[:3000]}
</outline>
"""

    # dynamic prompt: state, claims, manuscript (단발 호출이라 캐시 효과는 작지만 구조 통일)
    prompt = f"""<current_manuscript>
{manuscript if manuscript else "(빈 상태 — 처음부터 작성)"}
</current_manuscript>

<beats_already_done>
{beats_done}
</beats_already_done>

<beats_pending_to_finish>
{beats_pending}
</beats_pending_to_finish>

<available_claims>
사용 가능한 fact (출처 있는 것만 [claim:cXXX] 태그):

{claims_summary}
</available_claims>

<character_register>
{char_summary}
</character_register>

<task>
**Recovery 작업 — 한 번에 완성:**

1. current_manuscript 뒤에 이어서 outline의 beats_pending을 모두 작성, target_chars 도달.
2. 각 사실은 반드시 [claim:R*_cXXX] 태그로 출처 표시.
3. 인물 등장 시 [char:id] 태그.
   ⚠️ **register에 없는 인물 id는 절대 사용 금지**. 새 인물이 등장하면:
       - 먼저 character_register.json을 Edit로 열어서 새 entry append
       - 형식: {{"id": "snake_case_id", "name_ko": "한글이름", "name_en": "EnglishName", "role": "역할 한 줄"}}
       - 그 다음에 [char:snake_case_id] 태그 사용
   ❌ [char:_], [char:?], [char:placeholder] 같은 빈/모호한 id 금지.
4. {writing_style} 톤 유지 (도발적 후킹, 자문자답, 인물 중심).
5. 완료 후 manuscript.md 전체를 Write로 덮어쓰기.
6. outline_state.json도 status: "complete", beats_done에 모든 beat 추가, manuscript_chars 갱신.
7. 작업 완료 후 즉시 종료.

⚠️ 한 번에 모두 끝내야 합니다. 추가 호출 없습니다.
</task>
"""

    workspace.emit_event(
        "orchestrator", "recovery_call_start",
        level="info",
        prompt_chars=len(prompt) + len(system_prompt),
        claims_count=len(claims),
        manuscript_chars=len(manuscript),
    )

    result = await call_claude_cli_with_retry(
        prompt,
        system_prompt=system_prompt,
        model=writer_model,
        allowed_tools=["Read", "Write", "Edit", "Glob", "Bash"],
        max_turns=20,  # 30→20: beat 전체를 한 번에 쓰는 작업 — 20 turns으로 충분
        timeout_sec=300,  # 400→300s
        project_dir=workspace.dir,
        max_retries=1,
    )

    if not result.success:
        workspace.emit_event(
            "orchestrator", "recovery_failed",
            level="error",
            error=result.error[:300],
            elapsed_sec=result.elapsed_sec,
        )
        print(f"[Swarm] Recovery failed: {result.error[:200]}", flush=True)
        return False

    # 결과 확인
    new_manuscript = workspace.read_text("manuscript.md") or ""
    new_state = workspace.read_json("outline_state.json", default={})
    new_status = new_state.get("status", "")

    workspace.emit_event(
        "orchestrator", "recovery_completed",
        level="success",
        elapsed_sec=result.elapsed_sec,
        cost_usd=result.cost_usd,
        manuscript_chars=len(new_manuscript),
        new_status=new_status,
    )
    print(
        f"[Swarm] Recovery done — manuscript {len(new_manuscript)}자, "
        f"status={new_status}, ${result.cost_usd:.4f}, {result.elapsed_sec:.1f}s",
        flush=True,
    )

    # status가 complete가 됐으면 meta도 done으로
    if new_status == "complete":
        meta = workspace.read_json("meta.json", default={})
        meta["status"] = "done"
        meta["recovered_via_writer_only"] = True
        workspace.write_json_atomic("meta.json", meta)
        return True

    return False


async def _run_backbone_research(
    workspace: SwarmWorkspace,
    *,
    n_researchers: int,
    researcher_model: str,
    timeout_sec: int = 600,
) -> bool:
    """Phase 2: backbone researchers만 실행. 큐가 빌 때까지."""
    researchers: List[BaseAgent] = [
        ResearcherAgent(workspace=workspace, instance_id=f"R{i+1}", model=researcher_model)
        for i in range(n_researchers)
    ]

    async def watch_queue_empty() -> None:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_sec
        while True:
            if loop.time() >= deadline:
                workspace.emit_event("orchestrator", "backbone_research_timeout", level="warning")
                for r in researchers:
                    r.stop()
                return
            # 큐에 pending 항목이 없으면 종료
            queue = workspace.all_jsonl("research_queue.jsonl")
            pending = [q for q in queue if q.get("status") not in ("completed", "failed", "skipped")]
            if not pending and workspace.all_jsonl("findings.jsonl"):
                workspace.emit_event("orchestrator", "backbone_research_done",
                                     level="success", findings=len(workspace.all_jsonl("findings.jsonl")))
                for r in researchers:
                    r.stop()
                return
            await asyncio.sleep(3)

    agent_tasks = [asyncio.create_task(r.run()) for r in researchers]
    watch_task = asyncio.create_task(watch_queue_empty())
    try:
        await asyncio.gather(*agent_tasks, return_exceptions=True)
    finally:
        watch_task.cancel()
        try:
            await watch_task
        except asyncio.CancelledError:
            pass

    claims = workspace.all_jsonl("claims.jsonl")
    print(f"[Swarm] Phase 2 done: {len(claims)} backbone claims", flush=True)
    return len(claims) > 0


async def _run_sequential_writer(
    workspace: SwarmWorkspace,
    *,
    topic: str,
    duration_min: int,
    writing_style: str,
    creative_brief: str,
    reference_examples: str,
    mode: str,
    model: str,
    timeout_sec: int = 600,
) -> bool:
    """Phase 3 (draft) 또는 Phase 5 (final) — writer 단독 실행."""
    state_file = "draft_state.json" if mode == "draft" else "outline_state.json"
    label = "draft_writer" if mode == "draft" else "final_writer"

    writer = WriterAgent(
        workspace=workspace,
        topic=topic,
        duration_min=duration_min,
        writing_style=writing_style,
        creative_brief=creative_brief,
        reference_examples=reference_examples,
        mode=mode,
        model=model,
        max_iterations=60,
        timeout_per_step_sec=200,
    )

    async def watch_writer() -> None:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_sec
        while True:
            if loop.time() >= deadline:
                workspace.emit_event("orchestrator", f"{label}_timeout", level="warning")
                writer.stop()
                return
            state = workspace.read_json(state_file, default={})
            if state.get("status") == "complete":
                writer.stop()
                return
            await asyncio.sleep(3)

    writer_task = asyncio.create_task(writer.run())
    watch_task = asyncio.create_task(watch_writer())
    try:
        await asyncio.gather(writer_task, return_exceptions=True)
    finally:
        watch_task.cancel()
        try:
            await watch_task
        except asyncio.CancelledError:
            pass

    state = workspace.read_json(state_file, default={})
    success = state.get("status") == "complete"
    print(f"[Swarm] {label} done: status={state.get('status')}, chars={state.get('manuscript_chars', 0)}", flush=True)
    return success


async def _run_editor_swarm(
    workspace: SwarmWorkspace,
    *,
    topic: str,
    duration_min: int,
    writing_style: str,
    n_researchers: int,
    researcher_model: str,
    editor_model: str = "claude-opus-4-6",
    timeout_sec: int = 900,
) -> bool:
    """Phase 4: EditorAgent + targeted researchers 동시 실행.

    흐름:
    1. Editor가 draft.md 읽고 editorial_plan.json 작성 + 쿼리 추가
    2. Researchers가 쿼리 처리 (병렬)
    3. Editor 2번째 패스: TODO 해소 확인 → status="ready"
    """
    editor = EditorAgent(
        workspace=workspace,
        topic=topic,
        duration_min=duration_min,
        writing_style=writing_style,
        model=editor_model,
    )
    researchers: List[BaseAgent] = [
        ResearcherAgent(workspace=workspace, instance_id=f"E_R{i+1}", model=researcher_model)
        for i in range(n_researchers)
    ]

    async def watch_editor_done() -> None:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_sec
        while True:
            if loop.time() >= deadline:
                workspace.emit_event("orchestrator", "editor_swarm_timeout", level="warning")
                editor.stop()
                for r in researchers:
                    r.stop()
                return
            plan = workspace.read_json("editorial_plan.json", default={})
            if plan.get("status") == "ready":
                editor.stop()
                for r in researchers:
                    r.stop()
                workspace.emit_event("orchestrator", "editor_swarm_done",
                                     level="success",
                                     beats=len(plan.get("restructured_beats", [])))
                return
            await asyncio.sleep(4)

    all_agents = [editor] + researchers
    agent_tasks = [asyncio.create_task(a.run()) for a in all_agents]
    watch_task = asyncio.create_task(watch_editor_done())
    try:
        await asyncio.gather(*agent_tasks, return_exceptions=True)
    finally:
        watch_task.cancel()
        try:
            await watch_task
        except asyncio.CancelledError:
            pass

    plan = workspace.read_json("editorial_plan.json", default={})
    success = plan.get("status") == "ready"
    targeted_claims = workspace.all_jsonl("claims.jsonl")
    print(f"[Swarm] Phase 4 done: editorial_plan={plan.get('status')}, total_claims={len(targeted_claims)}", flush=True)
    return success


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
    # 2026-04-08 (저녁): sonnet 복귀 확인 → researcher default를 sonnet으로 되돌림.
    # claude_cli sonnet→opus 자동 fallback 가드가 있어서 다시 overload 와도 안전.
    researcher_model: str = "claude-sonnet-4-6",
    writer_model: str = "claude-opus-4-6",
    safe_mode: bool = False,
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
    # Phase 2: backbone research (parallel)
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 2: backbone research (researchers={n_researchers}) ...", flush=True)
    meta = workspace.read_json("meta.json")
    meta["status"] = "phase_2"
    meta["phase_2_started_at"] = _utcnow()
    workspace.write_json_atomic("meta.json", meta)

    backbone_ok = await _run_backbone_research(
        workspace,
        n_researchers=n_researchers,
        researcher_model=researcher_model,
        timeout_sec=600,
    )
    if not backbone_ok:
        workspace.emit_event("orchestrator", "backbone_research_failed", level="error")
        meta = workspace.read_json("meta.json")
        meta["status"] = "failed"
        meta["failed_phase"] = "phase_2"
        workspace.write_json_atomic("meta.json", meta)
        return {"status": "failed", "phase": "phase_2", "reason": "no backbone claims"}

    # ─────────────────────────────────────
    # Phase 3: draft_writer (chronological first draft)
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 3: draft_writer (model={writer_model}) ...", flush=True)
    meta = workspace.read_json("meta.json")
    meta["status"] = "phase_3"
    meta["phase_3_started_at"] = _utcnow()
    workspace.write_json_atomic("meta.json", meta)

    draft_ok = await _run_sequential_writer(
        workspace,
        topic=topic,
        duration_min=duration_min,
        writing_style=writing_style,
        creative_brief=creative_brief,
        reference_examples=reference_examples,
        mode="draft",
        model=writer_model,
        timeout_sec=max(600, duration_min * 180),
    )
    if not draft_ok:
        # draft 실패해도 계속 진행 (편집자가 부분 draft로도 작업 가능)
        workspace.emit_event("orchestrator", "draft_incomplete", level="warning")

    # ─────────────────────────────────────
    # Phase 4: editor + targeted researchers (swarm)
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 4: editor + targeted researchers ...", flush=True)
    meta = workspace.read_json("meta.json")
    meta["status"] = "phase_4"
    meta["phase_4_started_at"] = _utcnow()
    workspace.write_json_atomic("meta.json", meta)

    editor_ok = await _run_editor_swarm(
        workspace,
        topic=topic,
        duration_min=duration_min,
        writing_style=writing_style,
        n_researchers=min(n_researchers, 3),  # targeted research는 3개면 충분
        researcher_model=researcher_model,
        editor_model=skeleton_model,  # skeleton_model이 Opus
        timeout_sec=900,
    )
    if not editor_ok:
        workspace.emit_event("orchestrator", "editor_failed", level="warning",
                             reason="editorial_plan not ready — proceeding with partial plan")
        # 편집 실패해도 계속: 부분 plan으로 final_writer 진행

    # ─────────────────────────────────────
    # Phase 5: final_writer + validator
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 5: final_writer + validator (model={writer_model}) ...", flush=True)
    meta = workspace.read_json("meta.json")
    meta["status"] = "phase_5"
    meta["phase_5_started_at"] = _utcnow()
    workspace.write_json_atomic("meta.json", meta)

    final_writer = WriterAgent(
        workspace=workspace,
        topic=topic,
        duration_min=duration_min,
        writing_style=writing_style,
        creative_brief=creative_brief,
        reference_examples=reference_examples,
        mode="final",
        model=writer_model,
        max_iterations=60,
        timeout_per_step_sec=200,
    )
    validator = ValidatorAgent(workspace=workspace)
    phase5_agents: List[BaseAgent] = [final_writer, validator]

    async def watch_phase5_done() -> None:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_sec
        last_chars = -1
        stall_start: Optional[float] = None

        while True:
            now = loop.time()
            if now >= deadline:
                workspace.emit_event("orchestrator", "phase_5_timeout", level="warning")
                m = workspace.read_json("meta.json", default={})
                m["status"] = "timeout"
                workspace.write_json_atomic("meta.json", m)
                for a in phase5_agents:
                    a.stop()
                return
            m = workspace.read_json("meta.json", default={})
            if m.get("status") in ("done", "compiled", "stopped", "failed", "timeout"):
                for a in phase5_agents:
                    a.stop()
                return
            # writer stall 감지
            state = workspace.read_json("outline_state.json", default={})
            current_chars = state.get("manuscript_chars", 0)
            if last_chars < 0:
                last_chars = current_chars
            elif current_chars == last_chars and state.get("status") != "complete":
                if stall_start is None:
                    stall_start = now
                elif now - stall_start >= 300:
                    workspace.emit_event("orchestrator", "final_writer_stalled", level="warning")
                    m["status"] = "stalled"
                    workspace.write_json_atomic("meta.json", m)
                    for a in phase5_agents:
                        a.stop()
                    return
            else:
                last_chars = current_chars
                stall_start = None
            await asyncio.sleep(3)

    p5_tasks = [asyncio.create_task(a.run()) for a in phase5_agents]
    p5_watch = asyncio.create_task(watch_phase5_done())
    try:
        await asyncio.gather(*p5_tasks, return_exceptions=True)
    except Exception as e:
        logger.exception("Swarm Phase 5 error")
        workspace.emit_event("orchestrator", "phase_5_error",
                             level="error", error=f"{type(e).__name__}: {e}")
    finally:
        p5_watch.cancel()
        try:
            await p5_watch
        except asyncio.CancelledError:
            pass

    final_meta = workspace.read_json("meta.json", default={})
    phase_5_status = final_meta.get("status", "unknown")
    print(f"[Swarm] Phase 5 done (status={phase_5_status})", flush=True)

    # stalled → recovery 시도
    if phase_5_status == "stalled":
        recovered = await _writer_only_recovery(
            workspace,
            topic=topic,
            duration_min=duration_min,
            writing_style=writing_style,
            reference_examples=reference_examples,
            writer_model=writer_model,
        )
        if recovered:
            phase_5_status = "done"
            final_meta = workspace.read_json("meta.json", default={})
        else:
            return {
                "status": "failed",
                "phase": "phase_5",
                "reason": "final_writer_stalled_recovery_failed",
            }

    # safety net: outline complete + claims 충분 + 환각 없음
    if phase_5_status not in ("done", "timeout"):
        outline_state = workspace.read_json("outline_state.json", default={})
        all_claims = workspace.all_jsonl("claims.jsonl")
        valid_claim_ids = {c.get("id", "") for c in all_claims}
        manuscript = workspace.read_text("manuscript.md") or ""
        used_claim_ids = set()
        for tag in re.findall(r'\[claim:([^\]]+)\]', manuscript):
            for cid in tag.split(","):
                used_claim_ids.add(cid.strip())
        invalid_claim_ids = used_claim_ids - valid_claim_ids

        if (outline_state.get("status") == "complete"
                and len(used_claim_ids) >= 5
                and len(invalid_claim_ids) == 0):
            final_meta["status"] = "done"
            final_meta["safety_net_done"] = True
            workspace.write_json_atomic("meta.json", final_meta)
            phase_5_status = "done"
        else:
            return {
                "status": "failed",
                "phase": "phase_5",
                "meta_status": phase_5_status,
                "outline_status": outline_state.get("status"),
                "claims_used": len(used_claim_ids),
            }

    # ─────────────────────────────────────
    # Phase 6: compile
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 6: compile to output (safe_mode={safe_mode}) ...", flush=True)
    try:
        summary = compile_swarm(workspace, output_dir, safe_mode=safe_mode)
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
