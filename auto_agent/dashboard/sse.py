"""
SSE (Server-Sent Events) 파이프라인 실시간 모니터링.

두 개의 스트림:
  1. /events   — pipeline_events.jsonl tailing (스텝별 실시간 이벤트)
  2. /stream   — 출력 파일 변경 감지 (원고/씬스펙/스켈레톤)
  3. /status   — 현재 상태 스냅샷 (1회성 JSON)
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from auto_agent.dashboard.helpers import resolve_project_by_slug

router = APIRouter(prefix="/api/p/{slug}/pipeline", tags=["sse"])


# ─────────────────────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────────────────────

def _read_jsonl_since(path: Path, offset: int) -> tuple[list[dict], int]:
    """JSONL 파일에서 offset 이후 라인만 읽어 반환."""
    if not path.exists():
        return [], offset
    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        f.seek(offset)
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        new_offset = f.tell()
    return records, new_offset


def _safe_read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _live_state(project_dir: Path) -> dict:
    """pipeline_live.json → pipeline_state.json 순으로 현재 상태 조회."""
    for fname in ("pipeline_live.json", "pipeline_state.json"):
        p = project_dir / fname
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                return data
            except Exception:
                pass
    return {}


# ─────────────────────────────────────────────────────────────
# 이벤트 스트림 (pipeline_events.jsonl tail)
# ─────────────────────────────────────────────────────────────

async def _event_generator(project_dir: Path, request: Request):
    """
    pipeline_events.jsonl을 1초마다 tail.

    첫 메시지: snapshot (현재 전체 상태)
    이후: 스텝별 이벤트 delta
    """
    events_path = project_dir / "pipeline_events.jsonl"
    live_path = project_dir / "pipeline_live.json"
    state_path = project_dir / "pipeline_state.json"

    # ── 첫 snapshot ──
    state = _live_state(project_dir)
    snapshot = {
        "type": "snapshot",
        "current_step": state.get("current_step", ""),
        "current_phase": state.get("current_phase", ""),
        "completed": state.get("completed_steps", []),
        "failed": state.get("failed_steps", []),
        "skipped": state.get("skipped_steps", []),
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
        "status": "completed" if state.get("finished_at") else ("running" if state else "waiting"),
    }
    yield f"event: snapshot\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n"

    # ── 추적 상태 ──
    events_offset = events_path.stat().st_size if events_path.exists() else 0
    last_live_mtime = live_path.stat().st_mtime if live_path.exists() else 0.0
    last_state_mtime = state_path.stat().st_mtime if state_path.exists() else 0.0

    while True:
        if await request.is_disconnected():
            return

        try:
            # 1. pipeline_events.jsonl tail → 스텝 이벤트
            new_events, events_offset = _read_jsonl_since(events_path, events_offset)
            for entry in new_events:
                yield f"event: step_event\ndata: {json.dumps(entry, ensure_ascii=False)}\n\n"

            # 2. pipeline_live.json mtime 변경 → 현재 상태 갱신
            if live_path.exists():
                mtime = live_path.stat().st_mtime
                if mtime != last_live_mtime:
                    last_live_mtime = mtime
                    data = json.loads(live_path.read_text(encoding="utf-8"))
                    live_msg = {
                        "type": "live_update",
                        "current_step": data.get("current_step", ""),
                        "current_phase": data.get("current_phase", ""),
                        "completed": data.get("completed_steps", []),
                        "failed": data.get("failed_steps", []),
                        "skipped": data.get("skipped_steps", []),
                    }
                    yield f"event: live_update\ndata: {json.dumps(live_msg, ensure_ascii=False)}\n\n"

            # 3. pipeline_state.json (완료 시 최종 업데이트)
            if state_path.exists():
                mtime = state_path.stat().st_mtime
                if mtime != last_state_mtime:
                    last_state_mtime = mtime
                    data = json.loads(state_path.read_text(encoding="utf-8"))
                    if data.get("finished_at"):
                        fin_msg = {
                            "type": "pipeline_finished",
                            "finished_at": data["finished_at"],
                            "completed": data.get("completed_steps", []),
                            "failed": data.get("failed_steps", []),
                        }
                        yield f"event: pipeline_finished\ndata: {json.dumps(fin_msg, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        await asyncio.sleep(1.0)


# ─────────────────────────────────────────────────────────────
# 파일 내용 스트리밍 (원고/씬스펙 등 실시간 변경 감지)
# ─────────────────────────────────────────────────────────────

# 감시 대상 파일 목록 (경로 상대, 이벤트 type, 텍스트 여부)
_WATCH_FILES: list[tuple[str, str, bool]] = [
    ("skeleton.json",            "skeleton_updated",           False),
    ("outline.json",             "outline_updated",            False),
    (".manuscript_stream.md",    "manuscript_stream_updated",  True),
    ("draft.md",                 "draft_updated",              True),
    ("final_manuscript.md",      "manuscript_updated",         True),
    ("scene_specs.json",         "scene_specs_updated",        False),
    ("review_feedback.json",     "review_updated",             False),
    ("targeted_claims.json",     "claims_updated",             False),
]


async def _file_stream_generator(project_dir: Path, request: Request):
    """출력 파일 mtime 감지 → 변경된 파일 내용 스트리밍."""
    # 초기 mtime 기록
    mtimes: dict[str, float] = {}
    for rel, _, _ in _WATCH_FILES:
        p = project_dir / rel
        mtimes[rel] = p.stat().st_mtime if p.exists() else 0.0

    # chapter_facts/ 폴더 내 파일 mtime 기록
    chapter_facts_dir = project_dir / "chapter_facts"
    chapter_mtimes: dict[str, float] = {}

    def _scan_chapter_facts() -> dict[str, float]:
        if not chapter_facts_dir.exists():
            return {}
        return {
            str(p): p.stat().st_mtime
            for p in sorted(chapter_facts_dir.glob("*.json"))
        }

    # 초기 스냅샷: 이미 존재하는 파일은 즉시 전송
    for rel, event_type, is_text in _WATCH_FILES:
        p = project_dir / rel
        if not p.exists():
            continue
        try:
            if is_text:
                content = p.read_text(encoding="utf-8")
                msg = {"type": event_type, "chars": len(content), "text": content}
            else:
                data = json.loads(p.read_text(encoding="utf-8"))
                msg = {"type": event_type, "data": data}
            yield f"event: {event_type}\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
        except Exception:
            pass

    # chapter_facts/ 초기 스냅샷
    chapter_mtimes = _scan_chapter_facts()
    for path_str, _ in chapter_mtimes.items():
        p = Path(path_str)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            msg = {"type": "chapter_facts_updated", "chapter": p.stem, "data": data}
            yield f"event: chapter_facts_updated\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
        except Exception:
            pass

    while True:
        if await request.is_disconnected():
            return

        for rel, event_type, is_text in _WATCH_FILES:
            p = project_dir / rel
            if not p.exists():
                continue
            try:
                mtime = p.stat().st_mtime
                if mtime != mtimes.get(rel, 0.0):
                    mtimes[rel] = mtime
                    if is_text:
                        content = _safe_read_text(p)
                        msg = {"type": event_type, "chars": len(content), "text": content}
                    else:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        msg = {"type": event_type, "data": data}
                    yield f"event: {event_type}\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except Exception:
                pass

        # chapter_facts/ 폴더 변경 감지 (신규 파일 + 기존 파일 수정)
        current = _scan_chapter_facts()
        for path_str, mtime in current.items():
            if mtime != chapter_mtimes.get(path_str, 0.0):
                chapter_mtimes[path_str] = mtime
                p = Path(path_str)
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    msg = {"type": "chapter_facts_updated", "chapter": p.stem, "data": data}
                    yield f"event: chapter_facts_updated\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"
                except Exception:
                    pass

        await asyncio.sleep(2.0)


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@router.get("/events")
async def pipeline_events(slug: str, request: Request):
    """SSE: 파이프라인 스텝 진행 이벤트 스트림."""
    project = resolve_project_by_slug(slug)
    if not project:
        return StreamingResponse(
            iter([f"data: {json.dumps({'error': '프로젝트 없음'})}\n\n"]),
            media_type="text/event-stream",
        )
    project_dir = Path(project["output_dir"])
    return StreamingResponse(
        _event_generator(project_dir, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/stream")
async def pipeline_stream(slug: str, request: Request):
    """SSE: 출력 파일 변경 감지 스트림 (원고, 씬스펙 등)."""
    project = resolve_project_by_slug(slug)
    if not project:
        return StreamingResponse(
            iter([f"data: {json.dumps({'error': '프로젝트 없음'})}\n\n"]),
            media_type="text/event-stream",
        )
    project_dir = Path(project["output_dir"])
    return StreamingResponse(
        _file_stream_generator(project_dir, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status")
async def pipeline_status(slug: str):
    """현재 파이프라인 상태 스냅샷 (1회성 JSON)."""
    project = resolve_project_by_slug(slug)
    if not project:
        return {"error": "프로젝트 없음"}

    project_dir = Path(project["output_dir"])
    state = _live_state(project_dir)
    if not state:
        return {"status": "not_started"}

    return {
        "status": "completed" if state.get("finished_at") else "running",
        "current_step": state.get("current_step", ""),
        "current_phase": state.get("current_phase", ""),
        "completed_steps": state.get("completed_steps", []),
        "failed_steps": state.get("failed_steps", []),
        "skipped_steps": state.get("skipped_steps", []),
        "started_at": state.get("started_at"),
        "finished_at": state.get("finished_at"),
    }
