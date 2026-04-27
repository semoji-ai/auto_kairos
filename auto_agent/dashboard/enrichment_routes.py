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

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/enrichment", tags=["enrichment"])


def _get_project_dir(project_slug: str) -> Path:
    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    proj = pm.get_project(slug=project_slug) or pm.get_project(uuid=project_slug)
    if not proj:
        raise HTTPException(404, detail=f"프로젝트 없음: {project_slug}")
    return Path(proj["output_dir"])


@router.get("/{project_slug}/queue")
def get_queue(project_slug: str):
    out_dir = _get_project_dir(project_slug)
    queue_path = out_dir / "enrichment_queue.json"
    if not queue_path.exists():
        return JSONResponse({"summary": None, "queue": [], "exists": False})
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    data["exists"] = True
    return JSONResponse(data)


@router.post("/{project_slug}/run")
def run_enrichment(project_slug: str):
    from auto_agent.modules.scene_enricher_module import enrich_project
    out_dir = _get_project_dir(project_slug)
    try:
        result = enrich_project(out_dir, dry_run=False)
        return JSONResponse({"ok": True, "summary": result["summary"]})
    except Exception as e:
        logger.exception("enrichment 실패")
        raise HTTPException(500, detail=str(e))


class SelectionPayload(BaseModel):
    scene_index: int
    candidate: dict


@router.post("/{project_slug}/select")
def select_candidate(project_slug: str, payload: SelectionPayload):
    from auto_agent.modules.scene_enricher_module import apply_user_selection
    out_dir = _get_project_dir(project_slug)
    try:
        apply_user_selection(out_dir, payload.scene_index, payload.candidate)
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.exception("선택 적용 실패")
        raise HTTPException(500, detail=str(e))
