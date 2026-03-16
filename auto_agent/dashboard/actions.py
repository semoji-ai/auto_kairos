"""
웹 액션 API.

허용된 저비용 작업만 웹에서 실행 가능.
에이전트 루프가 필요한 작업은 차단.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auto_agent.db.project_manager import ProjectManager
from auto_agent.dashboard.helpers import resolve_project_by_slug
from auto_agent.paths import get_workspace_dir, PACKAGE_DIR

router = APIRouter(prefix="/api/p/{slug}/action", tags=["actions"])

# ─── 허용/차단 액션 ───

ALLOWED_ACTIONS = {
    "qa_check": {
        "description": "QA 검증 (규칙 기반, $0)",
        "module": "scripts/validate_data.py",
        "cost": 0,
    },
    "build_manifest": {
        "description": "매니페스트 빌드 ($0)",
        "module": "scripts/build_manifest.py",
        "cost": 0,
    },
    "subtitle_sync": {
        "description": "자막 동기화 ($0)",
        "module": "scripts/generate_subtitles.py",
        "cost": 0,
    },
    "tts_regenerate": {
        "description": "TTS 재생성 (ElevenLabs API, ~$0.01/씬)",
        "module": "scripts/generate_tts.py",
        "cost": 0.01,
    },
    "image_search": {
        "description": "이미지 검색 (Serper API, ~$0.01)",
        "module": "scripts/generate_images.py",
        "cost": 0.01,
    },
    "layout_check": {
        "description": "레이아웃 검증 ($0)",
        "module": "scripts/layout_check.py",
        "cost": 0,
    },
}

BLOCKED_ACTIONS = {
    "visual_compose", "write_manuscript", "research",
    "character_plan", "fact_verify",
}


@router.get("")
async def list_actions(slug: str):
    """사용 가능한 액션 목록."""
    return {
        "allowed": {
            k: {"description": v["description"], "cost": v["cost"]}
            for k, v in ALLOWED_ACTIONS.items()
        },
        "blocked": list(BLOCKED_ACTIONS),
    }


@router.post("/{action_name}")
async def execute_action(slug: str, action_name: str, request: Request):
    """액션 실행."""
    # 차단 확인
    if action_name in BLOCKED_ACTIONS:
        return JSONResponse(
            {"error": f"'{action_name}'은 에이전트 루프가 필요한 작업입니다. CLI에서 실행하세요."},
            status_code=403,
        )

    action = ALLOWED_ACTIONS.get(action_name)
    if not action:
        return JSONResponse(
            {"error": f"알 수 없는 액션: {action_name}"},
            status_code=404,
        )

    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    # 요청 body에서 추가 파라미터
    try:
        body = await request.json()
    except Exception:
        body = {}

    # 스크립트 실행
    script_path = PACKAGE_DIR / action["module"]
    if not script_path.exists():
        return JSONResponse(
            {"error": f"스크립트 없음: {action['module']}"},
            status_code=500,
        )

    env_vars = {
        "PROJECT_NAME": slug,
    }
    # 프로젝트 config에서 voice 설정 주입
    pm = ProjectManager()
    config = pm.get_config(project["id"])
    if config.get("voice_id"):
        env_vars["ELEVENLABS_VOICE_ID"] = config["voice_id"]
    if config.get("voice_settings"):
        env_vars["ELEVENLABS_VOICE_SETTINGS"] = json.dumps(config["voice_settings"])

    env = os.environ.copy()
    env.update(env_vars)

    # 씬 번호 등 추가 인자
    cmd_args = [sys.executable, str(script_path)]
    if body.get("scene_number"):
        cmd_args.extend(["--scene", str(body["scene_number"])])

    try:
        result = subprocess.run(
            cmd_args,
            cwd=str(get_workspace_dir()),
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode == 0:
            return {
                "ok": True,
                "action": action_name,
                "output": result.stdout[-1000:] if result.stdout else "",
            }
        else:
            return JSONResponse(
                {
                    "ok": False,
                    "action": action_name,
                    "error": result.stderr[-500:] or result.stdout[-500:],
                },
                status_code=500,
            )
    except subprocess.TimeoutExpired:
        return JSONResponse(
            {"ok": False, "error": "타임아웃 (120초)"},
            status_code=504,
        )
