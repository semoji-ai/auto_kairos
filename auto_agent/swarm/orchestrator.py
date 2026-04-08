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
from .claude_cli import call_claude_cli_with_retry
from .workspace import SwarmWorkspace

import json

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

    claims_summary = "\n".join(
        f"  - [{c.get('id','?')}] {c.get('text','')[:130]}"
        for c in claims[:60]
    )
    char_summary = "\n".join(
        f"  - id={c.get('id','?')} | {c.get('name_ko','')} ({c.get('name_en','')})"
        for c in characters
    )
    if not char_summary:
        char_summary = "  (없음)"

    target_chars = {1: 400, 3: 1200, 5: 2000, 10: 4000}.get(duration_min, duration_min * 400)
    ref_block = f"\n<reference_examples>\n{reference_examples}\n</reference_examples>\n" if reference_examples else ""

    prompt = f"""<system_context>
당신은 swarm Phase 2의 writer (RECOVERY mode).
역할: 부분 작성된 manuscript를 한 번의 호출로 **완성**하기.
workspace_path: {workspace.dir}

⚠️ Recovery mode: 평소 1 step에 1~2 문장만 쓰지만, 지금은 **남은 beats 전부를 한 번에 작성**해야 합니다.
이 호출이 끝나면 swarm 종료입니다. 추가 step 없습니다.
</system_context>

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

<current_manuscript>
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
        prompt_chars=len(prompt),
        claims_count=len(claims),
        manuscript_chars=len(manuscript),
    )

    result = await call_claude_cli_with_retry(
        prompt,
        model=writer_model,
        allowed_tools=["Read", "Write", "Edit", "Glob", "Bash"],
        max_turns=30,
        timeout_sec=400,
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
    #
    # 핵심 원칙 (코덱스 리뷰 2026-04-08):
    #   - validator의 swarm_done_signaled (validator passes 통과)만 유일한 종료 트리거
    #   - 이전의 force_done_after_writer_complete는 품질 게이트 우회 위험으로 제거
    #   - writer hang은 별도 안전망(writer hang detection)으로 처리
    async def watch_done() -> None:
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout_sec
        last_writer_progress_check = loop.time()
        last_writer_chars = -1
        writer_stall_check_interval = 30.0  # 30초마다 writer 진전 체크
        writer_stall_grace_sec = 300.0  # writer가 5분 이상 진전 없으면 hang 판정

        while True:
            now = loop.time()
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

            # Writer hang 안전망 — validator를 우회하지 않음.
            # writer가 일정 시간 진전 없고 + manuscript가 비어 있지도 않은 상태가 지속되면
            # status를 "stalled"로 표시하고 종료. 이 상태로 종료된 산출물은 compile하지 않음.
            if now - last_writer_progress_check >= writer_stall_check_interval:
                last_writer_progress_check = now
                outline_state = workspace.read_json("outline_state.json", default={})
                current_chars = outline_state.get("manuscript_chars", 0)
                writer_iter = outline_state.get("iteration", 0)
                writer_status = outline_state.get("status", "")

                if last_writer_chars < 0:
                    last_writer_chars = current_chars
                elif current_chars == last_writer_chars and writer_status != "complete":
                    # 진전 없음 — stall 시작 시간 추적
                    stall_start = m.get("writer_stall_start_at_loop", now)
                    if "writer_stall_start_at_loop" not in m:
                        m["writer_stall_start_at_loop"] = now
                        workspace.write_json_atomic("meta.json", m)
                    elif now - stall_start >= writer_stall_grace_sec:
                        # writer_stall_grace_sec 이상 진전 없음 → stalled
                        workspace.emit_event(
                            "orchestrator", "writer_stalled",
                            level="warning",
                            stalled_sec=int(now - stall_start),
                            chars=current_chars,
                            iteration=writer_iter,
                        )
                        m["status"] = "stalled"
                        workspace.write_json_atomic("meta.json", m)
                        for a in all_agents:
                            a.stop()
                        return
                else:
                    # 진전 있음 — stall 카운터 리셋
                    last_writer_chars = current_chars
                    if "writer_stall_start_at_loop" in m:
                        del m["writer_stall_start_at_loop"]
                        workspace.write_json_atomic("meta.json", m)

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

    # done = validator가 모든 검증 통과
    # timeout = phase 2 timeout (compile은 하되 품질 보증 없음)
    # stalled = writer가 진전 없음 → 이전엔 즉시 fail이었으나
    #           2026-04-08부터: writer-only recovery 시도
    if phase_2_status == "stalled":
        recovered = await _writer_only_recovery(
            workspace,
            topic=topic,
            duration_min=duration_min,
            writing_style=writing_style,
            reference_examples=reference_examples,
            writer_model=writer_model,
        )
        if recovered:
            # recovery로 manuscript complete됨 → compile 단계로 진행
            phase_2_status = "done"
            final_meta = workspace.read_json("meta.json", default={})
        else:
            return {
                "status": "failed",
                "phase": "phase_2",
                "reason": "writer_stalled_recovery_failed",
                "meta_status": phase_2_status,
            }
    if phase_2_status not in ("done", "timeout"):
        return {"status": "failed", "phase": "phase_2", "meta_status": phase_2_status}

    # ─────────────────────────────────────
    # Phase 3: compile
    # ─────────────────────────────────────
    print(f"[Swarm] Phase 3: compile to output (safe_mode={safe_mode}) ...", flush=True)
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
