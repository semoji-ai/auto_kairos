"""
SSE (Server-Sent Events) 파이프라인 모니터링.

pipeline_state.json 폴링으로 실시간 진행 상황 전송.
"""
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from auto_agent.dashboard.helpers import resolve_project_by_slug

router = APIRouter(prefix="/api/p/{slug}/pipeline", tags=["sse"])


async def _event_generator(project_dir: Path, request: Request):
    """pipeline_state.json 변경 감지 -> SSE 이벤트 전송."""
    state_path = project_dir / "pipeline_state.json"
    last_mtime = 0.0
    last_content = ""

    while True:
        # 클라이언트 연결 확인
        if await request.is_disconnected():
            break

        try:
            if state_path.exists():
                mtime = state_path.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    content = state_path.read_text(encoding="utf-8")
                    if content != last_content:
                        last_content = content
                        data = json.loads(content)
                        event_data = json.dumps({
                            "current_step": data.get("current_step", ""),
                            "completed": data.get("completed_steps", []),
                            "failed": data.get("failed_steps", []),
                            "finished_at": data.get("finished_at"),
                        }, ensure_ascii=False)
                        yield f"data: {event_data}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'waiting'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        await asyncio.sleep(2)  # 2초 폴링


@router.get("/events")
async def pipeline_events(slug: str, request: Request):
    """SSE 스트림으로 파이프라인 진행 상황 전송."""
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


@router.get("/status")
async def pipeline_status(slug: str):
    """현재 파이프라인 상태 (JSON)."""
    project = resolve_project_by_slug(slug)
    if not project:
        return {"error": "프로젝트 없음"}

    state_path = Path(project["output_dir"]) / "pipeline_state.json"
    if not state_path.exists():
        return {"status": "not_started"}

    data = json.loads(state_path.read_text(encoding="utf-8"))
    return {
        "status": "completed" if data.get("finished_at") else "running",
        "completed_steps": data.get("completed_steps", []),
        "failed_steps": data.get("failed_steps", []),
        "current_step": data.get("current_step", ""),
        "started_at": data.get("started_at"),
        "finished_at": data.get("finished_at"),
    }
