"""
enrichment_routes.py
--------------------
세모지/세모지3D scene-enricher 검토 대시보드 API.

엔드포인트:
- GET  /enrichment/{project_slug}/queue       — 큐 + summary 반환
- POST /enrichment/{project_slug}/run          — enrichment 실행 트리거
- POST /enrichment/{project_slug}/select       — 사용자가 선택한 후보를 scene_specs에 주입
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from auto_agent.dashboard.project_ref import resolve_project_ref, canonical_uuid_url

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enrichment", tags=["enrichment"])


def _resolve_project(project_ref: str):
    """project_ref(uuid 또는 slug) → (project, needs_redirect). project 없으면 (None, False)."""
    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    return resolve_project_ref(pm, project_ref)


@router.get("/{project_ref}/queue")
def get_queue(project_ref: str, request: Request):
    project, needs_redirect = _resolve_project(project_ref)
    if not project:
        raise HTTPException(404, detail=f"프로젝트 없음: {project_ref}")
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project["output_dir"])
    queue_path = out_dir / "enrichment_queue.json"
    if not queue_path.exists():
        return JSONResponse({"summary": None, "queue": [], "exists": False})
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    data["exists"] = True
    return JSONResponse(data)


@router.post("/{project_ref}/run")
def run_enrichment(project_ref: str, request: Request):
    from auto_agent.modules.scene_enricher_module import enrich_project
    project, needs_redirect = _resolve_project(project_ref)
    if not project:
        raise HTTPException(404, detail=f"프로젝트 없음: {project_ref}")
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project["output_dir"])
    try:
        result = enrich_project(out_dir, dry_run=False)
        return JSONResponse({"ok": True, "summary": result["summary"]})
    except Exception as e:
        logger.exception("enrichment 실패")
        raise HTTPException(500, detail=str(e))


class SelectionPayload(BaseModel):
    scene_index: int
    candidate: dict


@router.post("/{project_ref}/select")
def select_candidate(project_ref: str, payload: SelectionPayload, request: Request):
    from auto_agent.modules.scene_enricher_module import apply_user_selection
    project, needs_redirect = _resolve_project(project_ref)
    if not project:
        raise HTTPException(404, detail=f"프로젝트 없음: {project_ref}")
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project["output_dir"])
    try:
        apply_user_selection(out_dir, payload.scene_index, payload.candidate)
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.exception("선택 적용 실패")
        raise HTTPException(500, detail=str(e))
