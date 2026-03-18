"""
JSON 편집 API.

씬 데이터를 패치 방식으로 업데이트.
변경 전 자동 백업 (버전 관리).
"""
import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auto_agent.dashboard.helpers import resolve_project_by_slug

router = APIRouter(prefix="/api/p/{slug}", tags=["json-editor"])


def _set_nested(data: dict, key_path: str, value):
    """중첩 키 지원. 'scenes[0].layout' → data["scenes"][0]["layout"]."""
    keys = []
    for part in key_path.replace("]", "").split("."):
        if "[" in part:
            name, idx = part.split("[", 1)
            keys.append(name)
            keys.append(int(idx))
        else:
            keys.append(part)

    obj = data
    for k in keys[:-1]:
        obj = obj[k]

    obj[keys[-1]] = value


def _backup_json(file_path: Path):
    """변경 전 백업 (.bak.{timestamp})."""
    if file_path.exists():
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = file_path.with_suffix(f".bak.{ts}.json")
        backup.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")


@router.get("/scenes")
async def list_scenes(slug: str):
    """씬 목록 반환 (이미지/오디오 URL 포함)."""
    from auto_agent.dashboard.helpers import (
        load_project_json, enrich_scenes_with_media,
    )
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    out_dir = project.get("output_dir", "")
    specs = load_project_json(out_dir, "scene_specs.json")
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    scenes = specs.get("scenes", [])
    tts = load_project_json(out_dir, "tts_results.json")
    enriched = enrich_scenes_with_media(scenes, slug, out_dir, tts)
    return JSONResponse(content={"total": len(enriched), "scenes": enriched})


@router.get("/scenes/{scene_num}")
async def get_scene(slug: str, scene_num: int):
    """개별 씬 데이터 반환."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    specs_path = Path(project["output_dir"]) / "scene_specs.json"
    if not specs_path.exists():
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            return scene

    return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)


@router.put("/scenes/{scene_num}")
async def update_scene(slug: str, scene_num: int, request: Request):
    """씬 데이터 패치 업데이트.

    Body: {"patch": {"layout": "full-bleed-image", "mood": "dramatic"}}
    중첩 키: {"patch": {"items[0].text": "새 텍스트"}}
    """
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    patch = body.get("patch", {})
    if not patch:
        return JSONResponse({"error": "patch 데이터 필요"}, status_code=400)

    specs_path = Path(project["output_dir"]) / "scene_specs.json"
    if not specs_path.exists():
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scenes = specs.get("scenes", [])

    target_idx = None
    for i, scene in enumerate(scenes):
        if scene["sceneNumber"] == scene_num:
            target_idx = i
            break

    if target_idx is None:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    # 백업
    _backup_json(specs_path)

    # 패치 적용
    for key, value in patch.items():
        if "." in key or "[" in key:
            _set_nested(scenes[target_idx], key, value)
        else:
            scenes[target_idx][key] = value

    specs["scenes"] = scenes
    specs_path.write_text(
        json.dumps(specs, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {"ok": True, "scene": scenes[target_idx]}
