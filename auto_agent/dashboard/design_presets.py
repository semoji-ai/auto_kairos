"""
디자인 프리셋 API — 테마/컬러/애니메이션 설정을 저장·불러오기·적용
프리셋 저장 위치: workspace/.auto_agent/design_presets/*.json
"""
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from auto_agent.paths import get_workspace_dir

router = APIRouter(tags=["design-presets"])

PRESETS_DIR = get_workspace_dir() / ".auto_agent" / "design_presets"
PRESETS_DIR.mkdir(parents=True, exist_ok=True)

# ── 기본 내장 프리셋 ──
BUILTIN_PRESETS = {
    "dark_cinematic": {
        "name": "Dark Cinematic",
        "description": "어두운 배경 + 앰버 액센트, 극적 연출",
        "builtin": True,
        "global": {
            "videoTheme": "dark",
            "artStyle": "",
            "accentColor": "#F59E0B",
            "vizFont": "Pretendard",
        },
        "defaults": {
            "mood": "dramatic",
            "reveal": "stagger",
            "emphasis": "keyword",
            "layout": "",
        },
        "animation": {
            "stagger": 8,
            "itemDuration": 20,
            "easing": "easeOut",
            "titleFadeIn": 15,
        },
        "designPreset": {
            "baseTheme": "dark",
            "colors": {
                "accent": "#F59E0B",
                "accentRgb": "245,158,11",
            },
            "fonts": {
                "body": {"family": "Pretendard", "fallback": "'Apple SD Gothic Neo', sans-serif"},
            },
            "map": {"defaultTheme": "modern_clean"},
            "subtitle": {"keywordColor": "#F7D94C"},
        },
    },
    "white_clean": {
        "name": "White Clean",
        "description": "밝은 배경 + 블루 액센트, 정보 전달 중심",
        "builtin": True,
        "global": {
            "videoTheme": "white",
            "artStyle": "",
            "accentColor": "#2563EB",
            "vizFont": "Pretendard",
        },
        "defaults": {
            "mood": "informative",
            "reveal": "fade_in",
            "emphasis": "number",
            "layout": "",
        },
        "animation": {
            "stagger": 6,
            "itemDuration": 15,
            "easing": "easeOut",
            "titleFadeIn": 12,
        },
        "designPreset": {
            "baseTheme": "white",
            "colors": {
                "bg": "#FAFAFA",
                "text": "#1A1A2E",
                "textMuted": "#4A4A5A",
                "textDim": "#6A6A7A",
                "accent": "#2563EB",
                "accentRgb": "37,99,235",
                "accentBg": "rgba(37,99,235,0.06)",
                "accentBorder": "rgba(37,99,235,0.25)",
                "accentSoft": "rgba(37,99,235,0.10)",
                "cardBg": "rgba(37,99,235,0.04)",
                "cardBorder": "rgba(37,99,235,0.18)",
                "divider": "rgba(0,0,0,0.06)",
                "positive": "#16A34A",
                "negative": "#DC2626",
                "warning": "#D97706",
            },
            "fonts": {
                "body": {"family": "Pretendard", "fallback": "'Apple SD Gothic Neo', sans-serif"},
            },
            "map": {"defaultTheme": "modern_clean"},
            "subtitle": {"keywordColor": "#2563EB", "color": "#1A1A2E", "strokeColor": "#FFFFFF"},
        },
    },
    "urgent_red": {
        "name": "Urgent Red",
        "description": "긴박한 뉴스 스타일, 빠른 전개",
        "builtin": True,
        "global": {
            "videoTheme": "dark",
            "artStyle": "lego",
            "accentColor": "#EF4444",
            "vizFont": "Pretendard",
        },
        "defaults": {
            "mood": "urgent",
            "reveal": "cascade",
            "emphasis": "keyword",
            "layout": "",
            "imagePlacement": "background",
        },
        "animation": {
            "stagger": 5,
            "itemDuration": 12,
            "easing": "easeOut",
            "titleFadeIn": 8,
        },
        "designPreset": {
            "baseTheme": "dark",
            "colors": {
                "accent": "#EF4444",
                "accentRgb": "239,68,68",
            },
            "fonts": {
                "body": {"family": "Pretendard", "fallback": "'Apple SD Gothic Neo', sans-serif"},
            },
            "map": {"defaultTheme": "modern_clean"},
            "subtitle": {"keywordColor": "#EF4444"},
        },
    },
    "calm_green": {
        "name": "Calm Green",
        "description": "차분한 다큐멘터리, 느린 전개",
        "builtin": True,
        "global": {
            "videoTheme": "dark",
            "artStyle": "stickman_cute",
            "accentColor": "#10B981",
            "vizFont": "Pretendard",
        },
        "defaults": {
            "mood": "contemplative",
            "reveal": "fade_in",
            "emphasis": "none",
            "layout": "",
        },
        "animation": {
            "stagger": 12,
            "itemDuration": 30,
            "easing": "easeOut",
            "titleFadeIn": 20,
        },
        "designPreset": {
            "baseTheme": "dark",
            "colors": {
                "accent": "#10B981",
                "accentRgb": "16,185,129",
            },
            "fonts": {
                "body": {"family": "Pretendard", "fallback": "'Apple SD Gothic Neo', sans-serif"},
            },
            "map": {"defaultTheme": "modern_clean"},
            "subtitle": {"keywordColor": "#10B981"},
        },
    },
}


def _slug_from_name(name: str) -> str:
    """프리셋 이름 → 파일명 슬러그."""
    import re
    s = re.sub(r"[^\w\s-]", "", name.strip().lower())
    return re.sub(r"[\s-]+", "_", s)[:60]


def _list_user_presets() -> list[dict]:
    """사용자 저장 프리셋 목록."""
    result = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text("utf-8"))
            data["_file"] = f.stem
            result.append(data)
        except Exception:
            pass
    return result


# ── API 엔드포인트 ──

@router.get("/api/design-presets")
async def list_presets():
    """모든 프리셋 (내장 + 사용자) 목록."""
    presets = []
    for key, p in BUILTIN_PRESETS.items():
        presets.append({**p, "_id": key})
    for p in _list_user_presets():
        presets.append({**p, "_id": p["_file"], "builtin": False})
    return {"presets": presets}


@router.get("/api/design-presets/{preset_id}")
async def get_preset(preset_id: str):
    """프리셋 1개 조회."""
    if preset_id in BUILTIN_PRESETS:
        return {**BUILTIN_PRESETS[preset_id], "_id": preset_id}
    fp = PRESETS_DIR / f"{preset_id}.json"
    if fp.exists():
        data = json.loads(fp.read_text("utf-8"))
        return {**data, "_id": preset_id}
    return JSONResponse({"error": "not found"}, 404)


@router.post("/api/design-presets")
async def create_preset(request: Request):
    """새 프리셋 저장."""
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "name required"}, 400)

    slug = _slug_from_name(name)
    fp = PRESETS_DIR / f"{slug}.json"

    preset = {
        "name": name,
        "description": body.get("description", ""),
        "global": body.get("global", {}),
        "defaults": body.get("defaults", {}),
        "animation": body.get("animation", {}),
        "designPreset": body.get("designPreset", {}),
    }
    fp.write_text(json.dumps(preset, ensure_ascii=False, indent=2), "utf-8")
    return {"ok": True, "_id": slug, "preset": preset}


@router.put("/api/design-presets/{preset_id}")
async def update_preset(preset_id: str, request: Request):
    """프리셋 업데이트."""
    if preset_id in BUILTIN_PRESETS:
        return JSONResponse({"error": "builtin preset cannot be modified"}, 400)
    fp = PRESETS_DIR / f"{preset_id}.json"
    if not fp.exists():
        return JSONResponse({"error": "not found"}, 404)

    body = await request.json()
    existing = json.loads(fp.read_text("utf-8"))
    existing.update({
        "name": body.get("name", existing.get("name", "")),
        "description": body.get("description", existing.get("description", "")),
        "global": body.get("global", existing.get("global", {})),
        "defaults": body.get("defaults", existing.get("defaults", {})),
        "animation": body.get("animation", existing.get("animation", {})),
        "designPreset": body.get("designPreset", existing.get("designPreset", {})),
    })
    fp.write_text(json.dumps(existing, ensure_ascii=False, indent=2), "utf-8")
    return {"ok": True, "preset": existing}


@router.delete("/api/design-presets/{preset_id}")
async def delete_preset(preset_id: str):
    """프리셋 삭제."""
    if preset_id in BUILTIN_PRESETS:
        return JSONResponse({"error": "builtin preset cannot be deleted"}, 400)
    fp = PRESETS_DIR / f"{preset_id}.json"
    if fp.exists():
        fp.unlink()
    return {"ok": True}


@router.post("/api/p/{slug}/apply-preset")
async def apply_preset_to_project(slug: str, request: Request):
    """프리셋을 프로젝트에 적용 — scene_specs.json의 meta + 전체 씬 기본값 업데이트."""
    body = await request.json()
    preset_id = body.get("preset_id", "")

    # 프리셋 로드
    if preset_id in BUILTIN_PRESETS:
        preset = BUILTIN_PRESETS[preset_id]
    else:
        fp = PRESETS_DIR / f"{preset_id}.json"
        if not fp.exists():
            return JSONResponse({"error": "preset not found"}, 404)
        preset = json.loads(fp.read_text("utf-8"))

    # scene_specs.json 찾기
    from auto_agent.dashboard.helpers import load_project_json
    from auto_agent.supabase_client import supabase_enabled

    if supabase_enabled():
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()
        project = pm.get_project(slug=slug)
        if not project:
            return JSONResponse({"error": "project not found"}, 404)
        specs = pm.load_project_json(project["id"], "scene_specs.json")
        out_dir = project.get("output_dir", "")
    else:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.get_project(slug=slug)
        if not project:
            return JSONResponse({"error": "project not found"}, 404)
        out_dir = project.get("output_dir", "")
        specs = load_project_json(out_dir, "scene_specs.json")

    if not specs:
        return JSONResponse({"error": "scene_specs.json not found"}, 404)

    gl = preset.get("global", {})
    defs = preset.get("defaults", {})
    anim = preset.get("animation", {})

    # meta 업데이트
    if "meta" not in specs:
        specs["meta"] = {}
    if gl.get("videoTheme"):
        specs["meta"]["videoTheme"] = gl["videoTheme"]
    if gl.get("artStyle"):
        specs["meta"]["artStyle"] = gl["artStyle"]
    if gl.get("vizFont"):
        specs["meta"]["vizFont"] = gl["vizFont"]

    # 새 designPreset 필드
    if preset.get("designPreset"):
        specs["meta"]["designPreset"] = preset["designPreset"]

    # 씬별 데이터(mood, reveal, emphasis, animation, placement, opacity)는 건드리지 않음
    # 프리셋은 meta.designPreset만 저장

    # 저장
    specs_path = Path(out_dir) / "scene_specs.json" if out_dir else None
    if specs_path and specs_path.exists():
        specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), "utf-8")

    return {"ok": True, "scenes_updated": len(specs.get("scenes", []))}


@router.post("/api/p/{slug}/save-design-preset")
async def save_design_preset_to_project(slug: str, request: Request):
    """디자인 프리셋을 프로젝트 meta에 저장 (씬 기본값은 건드리지 않음)."""
    body = await request.json()
    design_preset = body.get("designPreset", {})
    video_theme = body.get("videoTheme")
    art_style = body.get("artStyle")

    from auto_agent.dashboard.helpers import load_project_json
    from auto_agent.supabase_client import supabase_enabled

    if supabase_enabled():
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()
        project = pm.get_project(slug=slug)
        if not project:
            return JSONResponse({"error": "project not found"}, 404)
        specs = pm.load_project_json(project["id"], "scene_specs.json")
        out_dir = project.get("output_dir", "")
    else:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        project = pm.get_project(slug=slug)
        if not project:
            return JSONResponse({"error": "project not found"}, 404)
        out_dir = project.get("output_dir", "")
        specs = load_project_json(out_dir, "scene_specs.json")

    if not specs:
        return JSONResponse({"error": "scene_specs.json not found"}, 404)

    if "meta" not in specs:
        specs["meta"] = {}

    # meta 업데이트 (designPreset만 — 씬 데이터 건드리지 않음)
    specs["meta"]["designPreset"] = design_preset
    if video_theme:
        specs["meta"]["videoTheme"] = video_theme
    if art_style:
        specs["meta"]["artStyle"] = art_style

    specs_path = Path(out_dir) / "scene_specs.json" if out_dir else None
    if specs_path and specs_path.exists():
        specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), "utf-8")

    return {"ok": True}
