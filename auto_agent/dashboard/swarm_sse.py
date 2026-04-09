"""Swarm SSE — 실시간 swarm 활동 스트리밍.

swarm workspace의 4개 파일을 polling/tail해서 SSE event로 push:
  - events.jsonl (tail, since_offset)
  - status.json (mtime poll)
  - manuscript.md (mtime poll)
  - character_register.json (mtime poll)

연결 직후 첫 메시지로 전체 snapshot, 이후 delta만 전송.

사용:
  GET  /api/swarm/events?workspace=/path/to/workspace
  GET  /api/swarm/snapshot?workspace=/path/to/workspace
  POST /api/swarm/start    (body: {topic, duration, writing_style, ...})

swarm orchestrator는 변경 없음 — 이미 events.jsonl에 모든 audit trail emit 중.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/swarm", tags=["swarm"])

# 진행 중인 swarm process registry (단일 프로세스 가정 — 확장 가능)
# key: workspace path (str), value: {"pid": int, "started_at": str, "args": dict}
_running_swarms: Dict[str, Dict[str, Any]] = {}


# ─────────────────────────────────────
# Snapshot / state aggregation
# ─────────────────────────────────────


def _read_jsonl_lines(path: Path, since_offset: int = 0) -> tuple[List[Dict[str, Any]], int]:
    """JSONL 파일 tail. since_offset 이후 라인만 반환."""
    if not path.exists():
        return [], since_offset
    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        f.seek(since_offset)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # 부분 쓰기 중일 수 있음
        new_offset = f.tell()
    return records, new_offset


def _safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _safe_read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _build_snapshot(workspace: Path) -> Dict[str, Any]:
    """전체 swarm 상태 snapshot — 첫 SSE 연결 시 전송."""
    meta = _safe_read_json(workspace / "meta.json") or {}
    status = _safe_read_json(workspace / "status.json") or {}
    outline_state = _safe_read_json(workspace / "outline_state.json") or {}
    outline = _safe_read_json(workspace / "outline.json") or {}
    register = _safe_read_json(workspace / "character_register.json") or {"characters": []}
    manuscript = _safe_read_text(workspace / "manuscript.md")

    # claims 카운트 + researcher 분포
    claims_path = workspace / "claims.jsonl"
    claims, _ = _read_jsonl_lines(claims_path, 0)
    findings_path = workspace / "findings.jsonl"
    findings, _ = _read_jsonl_lines(findings_path, 0)

    researchers: Dict[str, Dict[str, Any]] = {}
    for c in claims:
        rid = c.get("researcher", "?")
        if rid not in researchers:
            researchers[rid] = {"id": rid, "claims": 0, "last_q": ""}
        researchers[rid]["claims"] += 1
    for f in findings:
        rid = f.get("researcher", "?")
        if rid in researchers:
            researchers[rid]["last_q"] = f.get("q_id", "")

    # research_queue pending count
    queue_path = workspace / "research_queue.jsonl"
    queue, _ = _read_jsonl_lines(queue_path, 0)
    overrides_path = workspace / "status_overrides.jsonl"
    overrides, _ = _read_jsonl_lines(overrides_path, 0)
    completed_ids = {o["task_id"] for o in overrides if o.get("status") == "completed"}
    claimed_ids = {o["task_id"] for o in overrides if o.get("status") == "claimed"}
    queue_pending = sum(
        1 for q in queue
        if q.get("id") not in completed_ids and q.get("id") not in claimed_ids
    )

    return {
        "meta": meta,
        "status": status,
        "outline_state": outline_state,
        "outline": {
            "topic": outline.get("topic", ""),
            "core_thesis": outline.get("core_thesis", ""),
            "tone": outline.get("tone", ""),
            "duration_min": outline.get("duration_min", 0),
            "chapters_count": len(outline.get("chapters", [])),
        },
        "characters": register.get("characters", []),
        "manuscript": manuscript,
        "manuscript_chars": len(manuscript),
        "claims": claims,
        "claims_total": len(claims),
        "findings_total": len(findings),
        "queue_total": len(queue),
        "queue_pending": queue_pending,
        "researchers": list(researchers.values()),
        "running": str(workspace) in _running_swarms,
    }


# ─────────────────────────────────────
# SSE stream
# ─────────────────────────────────────


async def _swarm_event_generator(workspace: Path, request: Request):
    """swarm workspace 변경을 SSE로 push.

    첫 메시지: snapshot (전체 상태)
    이후: type별 delta 메시지
    """
    # ── 첫 snapshot ─────────────
    snapshot = _build_snapshot(workspace)
    yield f"event: snapshot\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n"

    # ── 추적 상태 ───────────────
    log_offset = 0
    claims_offset = 0
    findings_offset = 0
    last_manuscript_mtime = 0.0
    last_status_mtime = 0.0
    last_register_mtime = 0.0
    last_outline_state_mtime = 0.0

    # 첫 offset은 현재 파일 끝으로 (snapshot 이후만 추적)
    log_path = workspace / "log.jsonl"
    if log_path.exists():
        log_offset = log_path.stat().st_size
    claims_path = workspace / "claims.jsonl"
    if claims_path.exists():
        claims_offset = claims_path.stat().st_size
    findings_path = workspace / "findings.jsonl"
    if findings_path.exists():
        findings_offset = findings_path.stat().st_size

    manuscript_path = workspace / "manuscript.md"
    status_path = workspace / "status.json"
    register_path = workspace / "character_register.json"
    outline_state_path = workspace / "outline_state.json"

    while True:
        if await request.is_disconnected():
            return

        try:
            # 1. log.jsonl tail (모든 agent의 활동)
            new_logs, log_offset = _read_jsonl_lines(log_path, log_offset)
            for entry in new_logs:
                msg = {
                    "type": "agent_event",
                    "agent": entry.get("agent", "?"),
                    "event": entry.get("event", ""),
                    "level": entry.get("level", "info"),
                    "payload": entry.get("payload", {}),
                    "ts": entry.get("ts", ""),
                }
                yield f"event: agent_event\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 2. claims.jsonl tail (새 claim 추가 → 종이비행기 트리거)
            new_claims, claims_offset = _read_jsonl_lines(claims_path, claims_offset)
            for c in new_claims:
                msg = {
                    "type": "claim_added",
                    "claim_id": c.get("id", ""),
                    "researcher": c.get("researcher", ""),
                    "q_id": c.get("q_id", ""),
                    "text": c.get("text", "")[:200],
                    "source_url": c.get("source_url", ""),
                    "confidence": c.get("confidence", "medium"),
                }
                yield f"event: claim_added\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 3. findings.jsonl tail (researcher가 query 완료)
            new_findings, findings_offset = _read_jsonl_lines(findings_path, findings_offset)
            for f in new_findings:
                msg = {
                    "type": "finding_added",
                    "researcher": f.get("researcher", ""),
                    "q_id": f.get("q_id", ""),
                    "claims_count": f.get("claims_count", 0),
                    "elapsed_sec": f.get("elapsed_sec", 0),
                }
                yield f"event: finding_added\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 4. manuscript.md mtime poll
            if manuscript_path.exists():
                mtime = manuscript_path.stat().st_mtime
                if mtime != last_manuscript_mtime:
                    last_manuscript_mtime = mtime
                    text = _safe_read_text(manuscript_path)
                    msg = {
                        "type": "manuscript_updated",
                        "chars": len(text),
                        "full_text": text,
                    }
                    yield f"event: manuscript_updated\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 5. status.json mtime poll (validator 결과)
            if status_path.exists():
                mtime = status_path.stat().st_mtime
                if mtime != last_status_mtime:
                    last_status_mtime = mtime
                    data = _safe_read_json(status_path) or {}
                    msg = {
                        "type": "validator_status",
                        "validator": data.get("validator", {}),
                        "last_validated_at": data.get("last_validated_at", ""),
                    }
                    yield f"event: validator_status\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 6. character_register.json mtime poll
            if register_path.exists():
                mtime = register_path.stat().st_mtime
                if mtime != last_register_mtime:
                    last_register_mtime = mtime
                    data = _safe_read_json(register_path) or {"characters": []}
                    msg = {
                        "type": "register_updated",
                        "characters": data.get("characters", []),
                    }
                    yield f"event: register_updated\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 7. outline_state.json mtime poll (writer iteration / status)
            if outline_state_path.exists():
                mtime = outline_state_path.stat().st_mtime
                if mtime != last_outline_state_mtime:
                    last_outline_state_mtime = mtime
                    data = _safe_read_json(outline_state_path) or {}
                    msg = {
                        "type": "writer_state",
                        "iteration": data.get("iteration", 0),
                        "status": data.get("status", ""),
                        "manuscript_chars": data.get("manuscript_chars", 0),
                        "claims_used": data.get("claims_used", 0),
                        "todo_count": data.get("todo_count", 0),
                        "current_beat": data.get("current_beat", ""),
                        "beats_done": data.get("beats_done", []),
                        "beats_pending": data.get("beats_pending", []),
                    }
                    yield f"event: writer_state\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # 8. heartbeat — swarm process 살아있는지
            ws_key = str(workspace)
            if ws_key in _running_swarms:
                proc_info = _running_swarms[ws_key]
                pid = proc_info.get("pid")
                alive = pid and _is_process_alive(pid)
                if not alive:
                    # process 끝남 → registry에서 제거
                    _running_swarms.pop(ws_key, None)
                    yield f"event: swarm_ended\ndata: {json.dumps({'pid': pid}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

        await asyncio.sleep(1.0)  # 1초 폴링


def _is_process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


# ─────────────────────────────────────
# Style → reference 자동 매핑
# ─────────────────────────────────────
#
# writing_style별로 default reference 원고가 있으면 자동 적용.
# swarm_start 시 reference_file이 명시되지 않은 경우에만 default 사용.
# 사용자가 명시적으로 reference_file을 줬으면 그게 우선.

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

STYLE_REFERENCE_DEFAULTS: Dict[str, str] = {
    "iromism": str(PROJECT_ROOT / "auto_agent/data/references/iromism/nuclear_submarine_history.md"),
    # 다른 style도 추가 가능:
    # "semoji": str(PROJECT_ROOT / "auto_agent/data/references/semoji/sample.md"),
}


def _resolve_reference_file(writing_style: str, explicit: str = "") -> str:
    """style에 맞는 reference 파일 경로를 결정.

    우선순위:
      1. explicit (사용자가 명시) — 그대로 사용
      2. STYLE_REFERENCE_DEFAULTS[style] — 자동 매핑
      3. 빈 문자열 (reference 없음)
    """
    if explicit:
        return explicit
    default_path = STYLE_REFERENCE_DEFAULTS.get(writing_style, "")
    if default_path and Path(default_path).exists():
        return default_path
    return ""


# ─────────────────────────────────────
# Routes
# ─────────────────────────────────────


@router.get("/snapshot")
async def swarm_snapshot(workspace: str):
    """현재 swarm workspace의 전체 snapshot (1회성)."""
    ws = Path(workspace)
    if not ws.exists():
        raise HTTPException(404, f"workspace not found: {workspace}")
    return JSONResponse(_build_snapshot(ws))


@router.get("/events")
async def swarm_events(workspace: str, request: Request):
    """SSE stream — swarm workspace 실시간 변경."""
    ws = Path(workspace)
    if not ws.exists():
        raise HTTPException(404, f"workspace not found: {workspace}")
    return StreamingResponse(
        _swarm_event_generator(ws, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────
# Swarm process management
# ─────────────────────────────────────


class SwarmStartRequest(BaseModel):
    topic: str
    duration: int = 1
    writing_style: str = "iromism"
    workspace_dir: Optional[str] = None  # 없으면 자동 생성
    output_dir: Optional[str] = None
    n_researchers: int = 5
    timeout: int = 1800
    creative_brief_file: str = ""
    reference_file: str = ""
    safe_mode: bool = False  # 기존 파일 보호 (manuscript 탭 통합 시 True)
    project_slug: Optional[str] = None  # 프로젝트 컨텍스트에서 시작한 경우


@router.post("/start")
async def swarm_start(req: SwarmStartRequest):
    """swarm CLI를 background로 실행. dashboard SSE는 events 엔드포인트로 따로 연결."""
    # workspace 자동 생성 (지정 없으면 임시 디렉토리)
    if req.workspace_dir:
        ws = Path(req.workspace_dir)
    else:
        slug = "".join(c if c.isalnum() else "_" for c in req.topic)[:32]
        run_id = uuid.uuid4().hex[:8]
        ws = Path("/tmp") / f"swarm_{run_id}_{slug}" / "workspace"
    out = Path(req.output_dir) if req.output_dir else ws.parent / "output"
    ws.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    ws_key = str(ws)
    if ws_key in _running_swarms:
        raise HTTPException(409, f"swarm already running for workspace {ws}")

    # writing_style → reference 자동 매핑 (사용자 명시가 없으면)
    resolved_reference = _resolve_reference_file(req.writing_style, req.reference_file)

    cmd = [
        sys.executable, "-m", "auto_agent.swarm",
        "--topic", req.topic,
        "--duration", str(req.duration),
        "--writing-style", req.writing_style,
        "--workspace-dir", str(ws),
        "--output-dir", str(out),
        "--n-researchers", str(req.n_researchers),
        "--timeout", str(req.timeout),
    ]
    if req.creative_brief_file:
        cmd.extend(["--creative-brief-file", req.creative_brief_file])
    if resolved_reference:
        cmd.extend(["--reference-file", resolved_reference])
    if req.safe_mode:
        cmd.append("--safe-mode")

    log_file = ws.parent / "swarm_run.log"
    log_fh = open(log_file, "w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        cwd=str(Path(__file__).resolve().parent.parent.parent),  # project root
        start_new_session=True,
    )
    _running_swarms[ws_key] = {
        "pid": proc.pid,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "args": req.model_dump(),
        "log_file": str(log_file),
    }
    return {
        "status": "started",
        "pid": proc.pid,
        "workspace": str(ws),
        "output": str(out),
        "log_file": str(log_file),
        "reference_file": resolved_reference,  # 실제로 적용된 reference (자동 매핑 결과)
        "events_url": f"/api/swarm/events?workspace={ws}",
        "snapshot_url": f"/api/swarm/snapshot?workspace={ws}",
    }


@router.post("/stop")
async def swarm_stop(workspace: str):
    """진행 중인 swarm process 종료 (SIGTERM)."""
    ws_key = str(Path(workspace))
    if ws_key not in _running_swarms:
        raise HTTPException(404, f"no running swarm for workspace {workspace}")
    info = _running_swarms[ws_key]
    pid = info.get("pid")
    if pid:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    _running_swarms.pop(ws_key, None)
    return {"status": "stopped", "pid": pid}


@router.get("/list")
async def swarm_list():
    """현재 진행 중인 swarm 목록."""
    return {
        "running": [
            {"workspace": ws, **info}
            for ws, info in _running_swarms.items()
        ]
    }
