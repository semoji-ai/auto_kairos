"""
컨텍스트 메모리 웹 API.

프로젝트별 context_memory.json 조회/수정/메모 추가.
"""
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auto_agent.dashboard.helpers import resolve_project_by_slug
from auto_agent.orchestrator.context_memory import ContextMemory

router = APIRouter(prefix="/api/p/{slug}/memory", tags=["memory"])


def _get_memory(slug: str) -> tuple:
    """프로젝트 → ContextMemory 인스턴스 반환."""
    project = resolve_project_by_slug(slug)
    if not project:
        return None, None
    project_dir = Path(project["output_dir"])
    return project, ContextMemory(project_dir)


@router.get("")
async def get_memory(slug: str):
    """전체 컨텍스트 메모리 조회."""
    project, cm = _get_memory(slug)
    if not cm:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    memory = cm.load()
    return memory


@router.put("")
async def update_memory_entry(slug: str, request: Request):
    """특정 step의 메모리 엔트리 수정.

    Body: {"step_id": "step_3", "patch": {"summary": "수정된 요약"}}
    """
    project, cm = _get_memory(slug)
    if not cm:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    step_id = body.get("step_id")
    patch = body.get("patch", {})

    if not step_id or not patch:
        return JSONResponse(
            {"error": "step_id와 patch 필요"}, status_code=400
        )

    cm.update_entry(step_id, patch)
    return {"ok": True, "step_id": step_id}


@router.post("/notes")
async def add_note(slug: str, request: Request):
    """수동 메모 추가.

    Body: {"note": "이 부분은 다음 실행에서 주의 필요"}
    """
    project, cm = _get_memory(slug)
    if not cm:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    note = body.get("note", "").strip()
    if not note:
        return JSONResponse({"error": "note 내용 필요"}, status_code=400)

    added_by = body.get("added_by", "web_editor")
    cm.add_manual_note(note, added_by=added_by)
    return {"ok": True, "note": note}


@router.delete("/notes/{note_index}")
async def delete_note(slug: str, note_index: int):
    """수동 메모 삭제."""
    project, cm = _get_memory(slug)
    if not cm:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    memory = cm.load()
    notes = memory.get("manual_notes", [])

    if note_index < 0 or note_index >= len(notes):
        return JSONResponse({"error": "잘못된 인덱스"}, status_code=400)

    removed = notes.pop(note_index)
    cm.save(memory)
    return {"ok": True, "removed": removed}
