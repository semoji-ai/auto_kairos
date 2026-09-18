"""App and web share the same project-scoped track API."""
import json
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from auto_agent import video_tracks as vt
from auto_agent.dashboard.project_ref import resolve_project_ref

router = APIRouter(prefix="/api/p/{project_ref}/video-tracks", tags=["video-tracks"])


def project_root(project_ref):
    from auto_agent.db.project_manager import ProjectManager
    project, _ = resolve_project_ref(ProjectManager(), project_ref)
    return Path(project["output_dir"]) if project and project.get("output_dir") else None


def payload(root, data):
    resolved = vt.resolve(root, data)
    resolved["covered"] = sorted(resolved["covered"])
    for clip in resolved["clips"]:
        clip["sourcePath"] = Path(clip["sourcePath"]).relative_to(root.resolve()).as_posix()
        clip["url"] = "/output/" + quote(root.name) + "/" + quote(clip["sourcePath"])
    timings = vt.project_timings(root)
    return {"data": data, "resolved": resolved, "fps": 30, "projectFolder": root.name,
            "scenes": [{"sceneId": s["sceneId"], "sceneNumber": s["sceneNumber"],
                        "start": start, "duration": d} for s, start, d in timings],
            "files": [p.relative_to(root).as_posix() for p in sorted((root / "video_sources").glob("*.mp4"))
                      if p.is_file() and root.resolve() in p.resolve().parents]}


@router.get("")
def get_tracks(project_ref: str):
    root = project_root(project_ref)
    if root is None:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    try:
        return JSONResponse(payload(root, vt.load(root)), headers={"Cache-Control": "no-store"})
    except (ValueError, OSError, KeyError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)


@router.post("")
async def save_tracks(project_ref: str, request: Request):
    root = project_root(project_ref)
    if root is None:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    try:
        body = await request.json()
        if not isinstance(body, dict) or not isinstance(body.get("data"), dict):
            raise ValueError("data object required")
        result = vt.save(root, body["data"], expect_revision=body.get("revision"))
        if result.get("error"):
            return JSONResponse(result, status_code=409 if "revision" in result else 422)
        return {**result, **payload(root, vt.load(root))}
    except (ValueError, OSError, KeyError, TypeError) as e:
        return JSONResponse({"error": str(e)}, status_code=422)
