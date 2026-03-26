"""
auto_agent 프로젝트 관리 대시보드.
FastAPI + Jinja2 + htmx + xterm.js.
"""
import asyncio
import json
import os
import platform
import select
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

IS_WINDOWS = platform.system() == "Windows"

if not IS_WINDOWS:
    import pty

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_agent.db.cleanup import CleanupManager
from auto_agent.paths import get_data_dir, get_workspace_dir
from auto_agent.supabase_client import supabase_enabled

USE_SUPABASE = supabase_enabled()
from auto_agent.dashboard.helpers import (
    load_project_json,
    load_project_text,
    get_file_status,
    get_scene_image_url,
    get_scene_audio_url,
    parse_manuscript_chapters,
    get_pipeline_progress,
    enrich_scenes_with_media,
    format_headline,
    resolve_layout,
    render_scene_preview,
    get_recent_images,
)
from auto_agent.dashboard.actions import router as actions_router
from auto_agent.dashboard.json_editor import router as json_editor_router
from auto_agent.dashboard.sse import router as sse_router
from auto_agent.dashboard.memory_routes import router as memory_router
from auto_agent.dashboard.vault_routes import router as vault_router
from auto_agent.dashboard.scene_editor import router as scene_editor_router
from auto_agent.dashboard.scene_editor import manifest_router
from auto_agent.dashboard.design_presets import router as design_presets_router

app = FastAPI(title="Auto Agent Dashboard")

# ─── 신규 라우터 등록 ───
app.include_router(actions_router)
app.include_router(json_editor_router)
app.include_router(sse_router)
app.include_router(memory_router)
app.include_router(vault_router)
app.include_router(scene_editor_router)
app.include_router(manifest_router)
app.include_router(design_presets_router)
from auto_agent.dashboard.agent_messenger import router as messenger_router
app.include_router(messenger_router)

DASHBOARD_DIR = Path(__file__).parent / "auto_agent" / "dashboard"
DATA_DIR = get_data_dir()

app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")

# output 디렉토리 마운트 (이미지/오디오 직접 서빙)
workspace = get_workspace_dir()

# Remotion 폰트 서빙 (/fonts/ → remotion/public/fonts/)
_fonts_dir = workspace / "remotion" / "public" / "fonts"
if _fonts_dir.exists():
    app.mount("/fonts", StaticFiles(directory=str(_fonts_dir)), name="fonts")

# Remotion 배경 이미지 서빙 (/background/ → remotion/public/background/)
_bg_dir = workspace / "remotion" / "public" / "background"
if _bg_dir.exists():
    app.mount("/background", StaticFiles(directory=str(_bg_dir)), name="background")
output_dir = workspace / "output"
if output_dir.exists():
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

templates = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))
# Jinja2 필터 등록
templates.env.filters["format_headline"] = format_headline


USE_SUPABASE = False  # 로컬 DB 기반으로 전환


@app.get("/p/background/{file_path:path}")
async def proxy_background_no_slug(file_path: str):
    """Remotion 번들이 /p/background/... 로 요청하는 배경 이미지 서빙."""
    from fastapi.responses import FileResponse
    bg_file = workspace / "remotion" / "public" / "background" / file_path
    if bg_file.exists() and bg_file.is_file():
        return FileResponse(str(bg_file))
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/p/{slug}/background/{file_path:path}")
async def proxy_background_under_project(slug: str, file_path: str):
    """Remotion 번들이 /p/{slug}/background/... 로 요청하는 배경 이미지 서빙."""
    from fastapi.responses import FileResponse
    bg_file = workspace / "remotion" / "public" / "background" / file_path
    if bg_file.exists() and bg_file.is_file():
        return FileResponse(str(bg_file))
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/api/manifest/{dir_name}")
async def get_manifest_for_project(dir_name: str):
    """프로젝트별 manifest.json 반환. project/ 경로를 /output/{dir_name}/ 으로 rewrite."""
    p = workspace / "remotion" / "public" / "manifests" / f"{dir_name}.json"
    if not p.exists():
        return JSONResponse({"error": "manifest not found"}, status_code=404)
    data = json.loads(p.read_text(encoding="utf-8"))
    # project/ 경로 → /output/{dir_name}/ 으로 서버 사이드 rewrite
    prefix = f"/output/{dir_name}/"
    manifest = data.get("manifest", data)
    for scene in manifest.get("scenes", []):
        for key in ("imagePath", "vizBackgroundPath", "audioPath"):
            val = scene.get(key, "")
            if val and val.startswith("project/"):
                scene[key] = prefix + val[len("project/"):]
    return JSONResponse(content=data)


def get_pm():
    """로컬 ProjectManager 반환."""
    from auto_agent.db.project_manager import ProjectManager
    from auto_agent.db.connection import db_exists, init_db
    if not db_exists():
        init_db()
    return ProjectManager()


def _scan_and_register_output_projects() -> int:
    """output/ 폴더를 스캔해 DB에 없는 프로젝트를 자동 등록. 등록 수 반환."""
    import re
    pm = get_pm()
    output_root = get_workspace_dir() / "output"
    if not output_root.exists():
        return 0

    all_projects = pm.list_projects()

    # 역방향 체크: output_dir 폴더가 없으면 DB에서 제거
    for p in all_projects:
        out = p.get("output_dir", "")
        if out and not Path(out).exists():
            pm.delete_project(p["id"])
            print(f"  [SCAN] 폴더 없음 → DB 삭제: {Path(out).name}")

    # 기존 DB 프로젝트의 output_dir 집합 (삭제 후 재조회)
    existing = {p["output_dir"] for p in pm.list_projects() if p.get("output_dir")}

    registered = 0
    # {8자_uuid}_{slug} 패턴 디렉토리만 처리
    pattern = re.compile(r'^([0-9a-f]{8})_(.+)$')

    for d in sorted(output_root.iterdir()):
        if not d.is_dir():
            continue
        m = pattern.match(d.name)
        if not m:
            continue
        if str(d) in existing:
            continue  # 이미 등록됨

        uuid_prefix, slug = m.group(1), m.group(2)

        # pipeline_state.json에서 메타 읽기
        state_path = d / "pipeline_state.json"
        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # topic: research_report.json 우선, 없으면 slug
        topic = slug
        rr_path = d / "research_report.json"
        if rr_path.exists():
            try:
                rr = json.loads(rr_path.read_text(encoding="utf-8"))
                topic = rr.get("topic") or slug
            except Exception:
                pass

        config = state.get("config", {})

        try:
            pm.create_project(
                name=slug,
                slug=slug,
                topic=topic,
                theme=config.get("theme", "simple"),
                config=config,
                uuid=uuid_prefix,
            )
            registered += 1
            print(f"  [SCAN] 프로젝트 등록: {d.name}")
        except Exception as e:
            # UNIQUE 제약 등 — 무시
            print(f"  [SCAN] 등록 스킵 ({d.name}): {e}")

    return registered


@app.on_event("startup")
async def startup_scan():
    """대시보드 시작 시 output/ 폴더 스캔 → 누락 프로젝트 자동 등록."""
    try:
        count = _scan_and_register_output_projects()
        if count:
            print(f"[startup] output 스캔 완료: {count}개 프로젝트 등록")
    except Exception as e:
        print(f"[startup] output 스캔 실패 (무시): {e}")


TAB_TEMPLATES = {
    "overview": "partials/_overview.html",
    "pipeline": "partials/_pipeline.html",
    "research": "partials/_research.html",
    "manuscript": "partials/_manuscript.html",
    "storyboard": "partials/_storyboard.html",
    "studio": "partials/_studio.html",
    "versions": "partials/_versions.html",
    "costs": "partials/_costs.html",
    "design": "partials/_design.html",
    "agent": "partials/_agent.html",
}

# ─────────────────────────────
# Remotion Studio 프로세스 관리
# ─────────────────────────────
REMOTION_DIR = get_workspace_dir() / "remotion"
STUDIO_PORT = 3100

# Node.js 경로는 subprocess 호출 시 platform.get_env_with_node()로 주입
# (os.environ 전역 수정 제거 — COMPAT: was _node_candidates loop)
from auto_agent.utils.platform import get_env_with_node as _get_node_env
from auto_agent.utils.platform import get_npm_cmd as _get_npm_cmd
from auto_agent.utils.platform import get_npx_cmd as _get_npx_cmd
_studio_proc: Optional[subprocess.Popen] = None


def _load_tab_data(pm, project: dict, tab: str) -> dict:
    """탭별 데이터 로딩."""
    project_id = project["id"]
    out_dir = project.get("output_dir", "")
    slug = project.get("slug", "")
    # URL 경로용: output 디렉토리명 (uuid_{slug} 형식)
    dir_name = Path(out_dir).name if out_dir else slug
    context = {"project": project, "tab": tab, "slug": slug, "dir_name": dir_name}

    def _load_json(filename):
        return load_project_json(out_dir, filename)

    def _load_text(filename):
        return load_project_text(out_dir, filename)

    def _image_url(scene_num):
        return get_scene_image_url(dir_name, scene_num, out_dir)

    def _audio_url(scene_num):
        return get_scene_audio_url(dir_name, scene_num, out_dir)

    if tab == "overview":
        context["asset_counts"] = pm.get_asset_counts(project_id)
        context["cost"] = pm.get_cost_summary(project_id)
        context["file_status"] = _get_file_status(pm, project_id)
        context["recent_images"] = _get_recent_images(pm, project_id)
        runs = pm.get_pipeline_history(project_id)
        context["pipeline_progress"] = get_pipeline_progress(
            out_dir, str(DATA_DIR), db_runs=runs
        )

    elif tab == "pipeline":
        context["runs"] = pm.get_pipeline_history(project_id)
        context["pipeline_progress"] = get_pipeline_progress(
            out_dir, str(DATA_DIR), db_runs=context["runs"]
        )

    elif tab == "research":
        context["research"] = _load_json("research_report.json")
        # JSON 없으면 .md fallback
        if not context["research"]:
            md_text = _load_text("research_report.md")
            if md_text:
                context["research_md"] = md_text

    elif tab == "manuscript":
        specs = _load_json("scene_specs.json")
        context["scenes"] = specs.get("scenes", []) if specs else []

    elif tab == "storyboard":
        specs = _load_json("scene_specs.json")
        scenes = specs.get("scenes", []) if specs else []
        tts = _load_json("tts_results.json")
        _meta = specs.get("meta", {}) if specs else {}
        _dp_accent = (_meta.get("designPreset") or {}).get("colors", {}).get("accent")
        _proj_accent = _dp_accent or _meta.get("accentColor")
        _art_style = _meta.get("artStyle", "")
        scenes = enrich_scenes_with_media(scenes, dir_name, out_dir, tts,
                                          project_accent=_proj_accent, art_style=_art_style)
        context["scenes"] = scenes
        ch_set = sorted(set(s.get("chapter", 0) for s in scenes))
        context["chapters_list"] = ch_set

    elif tab == "studio":
        # Studio 탭 진입 시 해당 프로젝트 매니페스트 자동 설정
        _setup_studio_project(slug)

    elif tab == "assets":
        context["asset_counts"] = pm.get_asset_counts(project_id)
        context["assets"] = pm.get_assets(project_id)

    elif tab == "versions":
        version_types = [
            "scene_specs", "motion_plan", "manuscript",
            "scene_decomposition", "outline", "manifest",
        ]
        context["all_versions"] = {}
        for ft in version_types:
            versions = pm.get_versions(project_id, ft)
            if versions:
                context["all_versions"][ft] = versions

    elif tab == "costs":
        context["cost"] = pm.get_cost_summary(project_id)
        context["cost_by_agent"] = pm.get_cost_by_agent(project_id)

    return context


# ─────────────────────────────
# HTML Pages
# ─────────────────────────────

@app.get("/vault/search", response_class=HTMLResponse)
async def vault_search_page(request: Request):
    """볼트 시맨틱 검색 페이지."""
    return templates.TemplateResponse("vault_search.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """프로젝트 목록 페이지."""
    pm = get_pm()
    projects = pm.list_projects()
    for p in projects:
        p["asset_counts"] = pm.get_asset_counts(p["id"])
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects,
    })


@app.get("/p/{slug}", response_class=HTMLResponse)
async def project_by_slug(request: Request, slug: str, tab: str = "research"):
    """slug 기반 프로젝트 상세 페이지."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    context["request"] = request
    return templates.TemplateResponse("project.html", context)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int, tab: str = "research"):
    """레거시 ID 기반 → slug 리디렉트."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    return RedirectResponse(
        url=f"/p/{project['slug']}?tab={tab}",
        status_code=301,
    )


# ─────────────────────────────
# Manuscript 편집 API
# ─────────────────────────────

@app.get("/api/p/{slug}/manuscript/raw")
async def manuscript_raw(slug: str):
    """원고 raw 텍스트 반환."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    out_dir = project.get("output_dir", "")
    text = load_project_text(out_dir, "final_manuscript.md")
    return {"text": text or "", "chars": len(text) if text else 0}


@app.post("/api/p/{slug}/manuscript/save")
async def manuscript_save(slug: str, request: Request):
    """원고 저장."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    body = await request.json()
    text = body.get("text", "")
    if not text.strip():
        return JSONResponse({"error": "빈 원고는 저장할 수 없습니다."}, 400)
    pm.save_project_text(project["id"], "final_manuscript.md", text)
    return {"ok": True, "chars": len(text)}


# ─────────────────────────────
# HTMX Partials — 탭 콘텐츠
# ─────────────────────────────

@app.get("/api/p/{slug}/tab/{tab}", response_class=HTMLResponse)
async def project_tab_by_slug(request: Request, slug: str, tab: str):
    """slug 기반 탭 콘텐츠 (HTMX partial)."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project or tab not in TAB_TEMPLATES:
        return HTMLResponse("Not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    context["request"] = request
    return templates.TemplateResponse(TAB_TEMPLATES[tab], context)


@app.get("/api/projects/{project_id}/tab/{tab}", response_class=HTMLResponse)
async def project_tab_content(request: Request, project_id: int, tab: str):
    """레거시 탭 콘텐츠 (HTMX partial)."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project or tab not in TAB_TEMPLATES:
        return HTMLResponse("Not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    context["request"] = request
    return templates.TemplateResponse(TAB_TEMPLATES[tab], context)


# ─────────────────────────────
# HTMX Partials — 씬 상세
# ─────────────────────────────

@app.get("/api/p/{slug}/storyboard/scene/{scene_num}", response_class=HTMLResponse)
async def storyboard_scene_detail_by_slug(request: Request, slug: str, scene_num: int):
    """slug 기반 씬 상세 패널 (HTMX partial)."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return HTMLResponse("Not found", status_code=404)

    out_dir = project["output_dir"]
    pid = project["id"]

    specs = load_project_json(out_dir,"scene_specs.json")
    scene = None
    if specs:
        for s in specs.get("scenes", []):
            if s["sceneNumber"] == scene_num:
                scene = s
                break

    if not scene:
        return HTMLResponse(f"Scene {scene_num} not found", status_code=404)

    slug = project.get("slug", "")
    # URL 경로용: output 디렉토리명 (uuid_{slug} 형식)
    dir_name = Path(out_dir).name if out_dir else slug
    scene["_image_url"] = get_scene_image_url(dir_name, scene_num, out_dir)
    scene["_audio_url"] = get_scene_audio_url(dir_name, scene_num, out_dir)

    tts = load_project_json(out_dir,"tts_results.json")
    if tts:
        for r in tts.get("results", []):
            if r["scene"] == scene_num:
                scene["_tts_duration"] = r.get("duration")
                break

    subtitles = load_project_json(out_dir,"subtitles.json")
    scene_subs = None
    if subtitles:
        for sub in subtitles.get("scenes", []):
            if sub["sceneNumber"] == scene_num:
                scene_subs = sub
                break

    return templates.TemplateResponse("partials/_storyboard_scene.html", {
        "request": request,
        "scene": scene,
        "subtitles": scene_subs,
        "slug": slug,
        "dir_name": dir_name,
    })


@app.get("/api/projects/{project_id}/storyboard/scene/{scene_num}", response_class=HTMLResponse)
async def storyboard_scene_detail(request: Request, project_id: int, scene_num: int):
    """레거시 씬 상세 패널 (HTMX partial)."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return HTMLResponse("Not found", status_code=404)
    return RedirectResponse(
        url=f"/api/p/{project['slug']}/storyboard/scene/{scene_num}",
        status_code=301,
    )


# ─────────────────────────────
# JSON API
# ─────────────────────────────

@app.get("/api/projects")
async def api_projects():
    pm = get_pm()
    projects = pm.list_projects()
    for p in projects:
        p["asset_counts"] = pm.get_asset_counts(p["id"])
        p["cost"] = pm.get_cost_summary(p["id"])
    return projects


@app.get("/api/projects/{project_id}/summary")
async def api_project_summary(project_id: int):
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    project["asset_counts"] = pm.get_asset_counts(project_id)
    project["cost"] = pm.get_cost_summary(project_id)
    project["cost_by_agent"] = pm.get_cost_by_agent(project_id)
    return project


@app.get("/api/p/{slug}/summary")
async def api_project_summary_by_slug(slug: str):
    """slug 기반 프로젝트 요약 (Supabase 모드 대응)."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    pid = project["id"]
    project["asset_counts"] = pm.get_asset_counts(pid)
    project["cost"] = pm.get_cost_summary(pid)
    project["cost_by_agent"] = pm.get_cost_by_agent(pid)
    return project


@app.get("/api/p/{slug}/scenes")
async def api_scenes_by_slug(slug: str):
    """씬 목록 JSON (이미지/오디오 URL 포함)."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    out_dir = project.get("output_dir", "")
    specs = load_project_json(out_dir, "scene_specs.json")
    if not specs:
        return {"scenes": []}
    scenes = specs.get("scenes", [])
    tts = load_project_json(out_dir, "tts_results.json")
    dir_name = Path(out_dir).name if out_dir else slug
    print(f"[DEBUG] out_dir={out_dir}, dir_name={dir_name}, slug={slug}", flush=True)
    _meta = specs.get("meta", {}) if specs else {}
    _dp_accent = (_meta.get("designPreset") or {}).get("colors", {}).get("accent")
    _proj_accent = _dp_accent or _meta.get("accentColor")
    _art_style = _meta.get("artStyle", "")
    enriched = enrich_scenes_with_media(scenes, dir_name, out_dir, tts,
                                        project_accent=_proj_accent, art_style=_art_style)
    # image_assets.json에서 출처/라이선스 정보 병합
    img_assets = load_project_json(out_dir, "image_assets.json")
    if img_assets:
        img_map = {}
        for ia in img_assets.get("images", []):
            img_map[ia.get("scene_number")] = ia
        for s in enriched:
            ia = img_map.get(s.get("sceneNumber"))
            if ia:
                s["_image_source"] = ia.get("source", "")
                s["_image_license"] = ia.get("license", "")
                s["_image_source_url"] = ia.get("source_url", "")
                s["_image_title"] = ia.get("title", "")
    return JSONResponse(content={"scenes": enriched})


@app.get("/api/p/{slug}/images/candidates/{scene_num}")
async def image_candidates(slug: str, scene_num: int, q: str = "", source: str = "wikimedia"):
    """씬의 이미지 검색 후보 반환. q=커스텀 쿼리, source=wikimedia|serper."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")

    # 커스텀 쿼리가 없으면 저장된 후보 확인
    if not q:
        candidates_path = Path(out_dir) / "images" / "image_candidates.json"
        if candidates_path.exists():
            try:
                import json as _json
                data = _json.loads(candidates_path.read_text(encoding="utf-8"))
                for s in data.get("scenes", []):
                    if s.get("sceneNumber") == scene_num:
                        return JSONResponse({"query": s.get("query", ""), "candidates": s.get("candidates", []), "cached": True, "source": "cached"})
            except Exception:
                pass

    # 쿼리 결정: 커스텀 > scene_specs
    query = q
    if not query:
        specs = load_project_json(out_dir, "scene_specs.json")
        if not specs:
            return JSONResponse({"error": "no specs"}, 404)
        scene = None
        for s in specs.get("scenes", []):
            if s.get("sceneNumber") == scene_num:
                scene = s
                break
        if not scene:
            return JSONResponse({"error": "scene not found"}, 404)
        query = (scene.get("imageAsset") or {}).get("searchQuery") or (scene.get("imageAsset") or {}).get("query", "")
    if not query:
        return JSONResponse({"candidates": [], "query": ""})

    # 검색 실행 — wikimedia 우선, 결과 없으면 serper fallback
    candidates = []
    used_source = source
    if source == "serper":
        try:
            from auto_agent.tools.serper_search import search_images
            candidates = search_images(query, 12)
        except Exception as e:
            return JSONResponse({"error": f"serper 검색 실패: {e}", "candidates": [], "query": query})
    else:
        from auto_agent.tools.wikimedia_search import search_wikimedia, save_candidates
        candidates = search_wikimedia(query, 8)
        # wikimedia 결과 없으면 serper fallback
        if not candidates:
            try:
                from auto_agent.tools.serper_search import search_images
                candidates = search_images(query, 12)
                used_source = "serper"
            except Exception:
                pass
        if candidates:
            save_candidates(scene_num, query, candidates, str(Path(out_dir) / "images"))

    return JSONResponse({"query": query, "candidates": candidates, "cached": False, "source": used_source})


@app.post("/api/p/{slug}/images/select/{scene_num}")
async def select_image(request: Request, slug: str, scene_num: int):
    """이미지 선택 — URL 다운로드 또는 기존 버전 선택."""
    from auto_agent.tools.image_assets import add_version, select_version, next_filename
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    img_dir = Path(out_dir) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    body = await request.json()
    url = body.get("url", "")
    file_name = body.get("file", "")  # 기존 버전 선택

    if file_name:
        # 기존 버전 선택
        ok = select_version(img_dir, scene_num, file_name)
        if ok:
            _update_scene_specs_src(out_dir, slug, scene_num)
            _setup_studio_project(slug)
            return JSONResponse({"ok": True, "selected": file_name})
        return JSONResponse({"error": "version not found"}, 404)

    if not url:
        return JSONResponse({"error": "url or file required"}, 400)

    # URL 다운로드 → images/search/ 에 저장
    from auto_agent.tools.wikimedia_search import download_image
    from urllib.parse import urlparse
    ext = Path(urlparse(url).path).suffix or ".jpg"
    search_dir = img_dir / "search"
    search_dir.mkdir(parents=True, exist_ok=True)
    fname = next_filename(img_dir, scene_num, "search", ext)
    result = download_image(url, str(search_dir / fname))

    if result.get("success"):
        title = body.get("title", "")
        license_info = body.get("license", "")
        add_version(img_dir, scene_num, "search/" + fname, "search",
                    query=body.get("query", ""), source_url=url,
                    title=title, license=license_info)
        _update_scene_specs_src(out_dir, slug, scene_num)
        _setup_studio_project(slug)
        return JSONResponse({"ok": True, "file": fname})
    return JSONResponse({"error": result.get("error", "download failed")}, 500)


@app.get("/api/p/{slug}/images/versions/{scene_num}")
async def image_versions(slug: str, scene_num: int):
    """씬의 모든 이미지 버전."""
    from auto_agent.tools.image_assets import get_scene_versions
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else slug
    img_dir = Path(out_dir) / "images"
    try:
        scene_data = get_scene_versions(img_dir, scene_num)
        # URL 추가
        for v in scene_data.get("versions", []):
            if v.get("file"):
                v["url"] = f"/output/{dir_name}/images/{v['file']}"
        return JSONResponse(scene_data)
    except Exception:
        return JSONResponse({"sceneNumber": scene_num, "selected": None, "versions": []})


@app.post("/api/p/{slug}/tts/regenerate/{scene_num}")
async def regenerate_tts(request: Request, slug: str, scene_num: int):
    """씬별 TTS 재생성."""
    import json as _json
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    body = await request.json()
    text = body.get("text", "")

    if not text:
        # scene_specs에서 narration_tts 읽기
        specs = load_project_json(out_dir, "scene_specs.json")
        if specs:
            for s in specs.get("scenes", []):
                if s.get("sceneNumber") == scene_num:
                    text = s.get("narration_tts", s.get("narration", ""))
                    break
    if not text:
        return JSONResponse({"error": "text required"}, 400)

    # voice_id 결정
    config = project.get("config", {})
    if isinstance(config, str):
        config = _json.loads(config)

    STYLE_VOICE = {
        "semoji": "W7FnAxJNpD5WGjrF5GLp",
        "iromism": "9Sj8ugvpK1DmcAXyvi3a",
        "default": "4JJwo477JUAx3HV0T7n7",
    }
    voice_id = config.get("voice_id") or STYLE_VOICE.get(config.get("writing_style", "default"), STYLE_VOICE["default"])

    # TTS 생성 — audio_assets 기반
    from auto_agent.tools.audio_assets import add_version, next_filename
    audio_dir = Path(out_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    fname = next_filename(audio_dir, scene_num)
    output_path = audio_dir / fname

    try:
        import requests as _requests
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            return JSONResponse({"error": "ELEVENLABS_API_KEY 미설정"}, 500)

        voice_settings = {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "use_speaker_boost": True}
        resp = _requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2", "voice_settings": voice_settings},
            timeout=60,
        )
        if resp.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(resp.content)
        else:
            return JSONResponse({"error": f"ElevenLabs {resp.status_code}: {resp.text[:100]}"}, 500)

        if output_path.exists():
            # audio_assets에 버전 등록
            add_version(audio_dir, scene_num, fname, "regen",
                        voice_id=voice_id, text=text[:100])
            # narration_tts 업데이트
            specs_path = Path(out_dir) / "scene_specs.json"
            if specs_path.exists():
                specs = _json.loads(specs_path.read_text(encoding="utf-8"))
                for s in specs.get("scenes", []):
                    if s.get("sceneNumber") == scene_num:
                        s["narration_tts"] = text
                        break
                specs_path.write_text(_json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
            _setup_studio_project(slug)
            # 자막 재정렬 (WhisperX)
            try:
                sub_result = subprocess.run(
                    [sys.executable, "-m", "auto_agent.scripts.generate_subtitles", out_dir],
                    cwd=str(get_workspace_dir()),
                    capture_output=True, text=True, encoding="utf-8", timeout=120,
                )
                if sub_result.returncode == 0:
                    print(f"[TTS] 씬 {scene_num} 자막 재정렬 완료", flush=True)
                else:
                    print(f"[WARN] 자막 재정렬 실패: {sub_result.stderr[:100]}", flush=True)
            except Exception as se:
                print(f"[WARN] 자막 재정렬 에러: {se}", flush=True)
            # 매니페스트 리빌드 (오디오 길이 + 자막 변경 반영)
            try:
                from auto_agent.scripts.build_manifest import build_manifest
                dir_name = Path(out_dir).name
                build_manifest(str(project.get("id", "")), dir_name, out_dir)
            except Exception as me:
                print(f"[WARN] TTS 재생성 후 매니페스트 리빌드 실패: {me}", flush=True)
            return JSONResponse({"ok": True, "file": fname, "voice_id": voice_id, "size": output_path.stat().st_size})
        else:
            return JSONResponse({"error": "생성 실패 — 파일 미생성"}, 500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/p/{slug}/tts/versions/{scene_num}")
async def tts_versions(slug: str, scene_num: int):
    """씬의 TTS 버전 목록."""
    from auto_agent.tools.audio_assets import get_scene_versions
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else slug
    audio_dir = Path(out_dir) / "audio"
    scene_data = get_scene_versions(audio_dir, scene_num)
    for v in scene_data.get("versions", []):
        v["url"] = f"/output/{dir_name}/audio/{v['file']}"
    return JSONResponse(scene_data)


@app.post("/api/p/{slug}/tts/select/{scene_num}")
async def select_tts(request: Request, slug: str, scene_num: int):
    """TTS 버전 선택."""
    from auto_agent.tools.audio_assets import select_version
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    body = await request.json()
    file_name = body.get("file", "")
    if not file_name:
        return JSONResponse({"error": "file required"}, 400)
    audio_dir = Path(project.get("output_dir", "")) / "audio"
    ok = select_version(audio_dir, scene_num, file_name)
    if ok:
        _setup_studio_project(slug)
        return JSONResponse({"ok": True, "selected": file_name})
    return JSONResponse({"error": "version not found"}, 404)


@app.get("/api/p/{slug}/tts/text/{scene_num}")
async def get_tts_text(slug: str, scene_num: int):
    """씬의 TTS 텍스트 반환."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    specs = load_project_json(out_dir, "scene_specs.json")
    if not specs:
        return JSONResponse({"error": "no specs"}, 404)
    for s in specs.get("scenes", []):
        if s.get("sceneNumber") == scene_num:
            return JSONResponse({
                "text": s.get("narration_tts", s.get("narration", "")),
                "narration": s.get("narration", ""),
            })
    return JSONResponse({"error": "scene not found"}, 404)


def _update_scene_specs_src(out_dir: str, slug: str, scene_num: int):
    """selected 이미지로 scene_specs.imageAsset.src 업데이트."""
    from auto_agent.tools.image_assets import get_selected
    img_dir = Path(out_dir) / "images"
    selected = get_selected(img_dir, scene_num)
    if not selected:
        return
    import json as _json
    # URL 경로용: output 디렉토리명 (uuid_{slug} 형식)
    dir_name = Path(out_dir).name if out_dir else slug
    specs_path = Path(out_dir) / "scene_specs.json"
    if specs_path.exists():
        specs = _json.loads(specs_path.read_text(encoding="utf-8"))
        for s in specs.get("scenes", []):
            if s.get("sceneNumber") == scene_num:
                if not s.get("imageAsset"):
                    s["imageAsset"] = {}
                ext = Path(selected).suffix
                s["imageAsset"]["src"] = f"/output/{dir_name}/images/scene_{scene_num:03d}{ext}"
                break
        specs_path.write_text(_json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")


@app.post("/api/p/{slug}/images/auto-prompt/{scene_num}")
async def auto_prompt(slug: str, scene_num: int):
    """Sonnet으로 씬 컨텍스트에서 이미지 프롬프트 자동 생성."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    specs = load_project_json(out_dir, "scene_specs.json")
    if not specs:
        return JSONResponse({"error": "no specs"}, 404)
    scene = None
    for s in specs.get("scenes", []):
        if s.get("sceneNumber") == scene_num:
            scene = s
            break
    if not scene:
        return JSONResponse({"error": "scene not found"}, 404)

    title = scene.get("title", "")
    narration = scene.get("narration", "")[:200]
    concept = (scene.get("visualization") or {}).get("creative", {}).get("concept", "")
    mood = (scene.get("visualization") or {}).get("creative", {}).get("mood", "")

    # 아트스타일 scene_style_description 가져오기
    import json as _json
    config = project.get("config", {})
    if isinstance(config, str):
        config = _json.loads(config)
    art_style_path = config.get("art_style", "")
    style_desc = ""
    if art_style_path:
        try:
            style_json = _json.loads((get_workspace_dir() / art_style_path).read_text(encoding="utf-8"))
            style_desc = style_json.get("scene_style_description", "")
        except Exception:
            pass

    prompt_input = (
        f"씬 제목: {title}\n나레이션: {narration}\n연출 컨셉: {concept}\n무드: {mood}\n"
        f"아트스타일: {style_desc}\n\n"
        f"위 씬의 이미지 생성 프롬프트를 아래 구조화 포맷으로 작성하세요.\n"
        f"프롬프트만 출력하세요. 설명이나 마크다운 없이.\n\n"
        f"포맷 규칙:\n"
        f"- 【스타일】 아트스타일 한 줄 설명\n"
        f"- 【상황】 정적인 스틸컷 묘사 (동작/움직임 표현 금지, 텍스트 요소 금지)\n"
        f"- 【배경】 시대, 장소, 시간대, 분위기\n"
        f"- 【등장 캐릭터】 인물이 있을 때만 — 외모, 복장, 표정, 자세 (선택)\n"
        f"- 【카메라 앵글】 샷 사이즈 + 앵글 + 구도\n\n"
        f"예시:\n"
        f"【스타일】 Loose quirky hand-drawn cartoon, doodle style, thick wobbly lines, bright flat colors\n"
        f"【상황】 부두에 모인 사람들이 손가락질하며 비웃고 있지만, 증기선은 굴뚝에서 연기를 힘차게 뿜으며 출발한다\n"
        f"【배경】 1807년 뉴욕 항구, 나무 부두, 맑은 낮\n"
        f"【등장 캐릭터】 군중(19세기 복장) - 조롱하는 표정. 풀턴(단정한 정장) - 배 위에서 팔짱 끼고 자신감 넘치는 미소\n"
        f"【카메라 앵글】 미디엄샷, 비웃는 군중과 출발하는 배가 동시에 잡히는 구도"
    )

    try:
        import shutil
        cli_path = shutil.which("claude") or str(Path.home() / ".local/bin/claude")
        proc = subprocess.run(
            [cli_path, "--print", "--model", "claude-sonnet-4-5-20250929", "--max-turns", "1"],
            input=prompt_input, capture_output=True, text=True, encoding="utf-8", timeout=30,
            env={**dict(os.environ), "CLAUDECODE": ""},
        )
        result_text = proc.stdout.strip()
        import json as _json
        try:
            cli_out = _json.loads(result_text)
            if isinstance(cli_out, dict) and "result" in cli_out:
                result_text = cli_out["result"]
                if isinstance(result_text, list):
                    result_text = " ".join(b.get("text", "") for b in result_text if isinstance(b, dict))
        except _json.JSONDecodeError:
            pass
        return JSONResponse({"prompt": result_text.strip()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.post("/api/p/{slug}/images/generate/{scene_num}")
async def generate_image(request: Request, slug: str, scene_num: int):
    """FAL.ai로 이미지 생성."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    body = await request.json()
    prompt = body.get("prompt", "")
    mode = body.get("mode", "scene")
    if not prompt:
        return JSONResponse({"error": "prompt required"}, 400)

    import json as _json
    config = project.get("config", {})
    if isinstance(config, str):
        config = _json.loads(config)
    art_style = config.get("art_style", "")
    style_path = str(get_workspace_dir() / art_style) if art_style else ""

    from auto_agent.tools.image_assets import add_version, next_filename
    img_dir = Path(out_dir) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # 버전 파일명 생성 → images/generated/
    gen_dir = img_dir / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    fname = next_filename(img_dir, scene_num, "gen", ".png")
    output_path = str(gen_dir / fname)

    # FAL.ai 호출
    try:
        cmd = [sys.executable, "-m", "auto_agent.tools.image_generate", mode,
               "--prompt", prompt, "--output", output_path]
        if style_path:
            cmd.extend(["--style", style_path])
        env = {**dict(os.environ), "PROJECT_NAME": slug}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120,
                                cwd=str(get_workspace_dir()), env=env)
        if result.returncode == 0:
            res = _json.loads(result.stdout)
            # image_assets에 버전 추가 + selected 설정
            add_version(img_dir, scene_num, "generated/" + fname, "generate",
                        prompt=prompt[:200], art_style=art_style, mode=mode)
            _update_scene_specs_src(out_dir, slug, scene_num)
            _setup_studio_project(slug)
            return JSONResponse({"ok": True, "path": output_path, "prompt_used": prompt[:200]})
        else:
            return JSONResponse({"error": result.stderr[:300] or result.stdout[:300]}, 500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/p/{slug}/art-style")
async def get_art_style(slug: str):
    """프로젝트 아트스타일 정보 + 사용 가능한 스타일 목록."""
    import json as _json
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    config = project.get("config", {})
    if isinstance(config, str):
        config = _json.loads(config)
    current = config.get("art_style", "")

    # 현재 스타일 정보
    current_info = {}
    if current:
        style_path = get_workspace_dir() / current
        if style_path.exists():
            try:
                current_info = _json.loads(style_path.read_text(encoding="utf-8"))
                # 참조 이미지 URL — output 디렉토리명(uuid_{slug}) 기반
                ref = current_info.get("reference_image", "")
                if ref:
                    _art_out_dir = project.get("output_dir", "")
                    _art_dir_name = Path(_art_out_dir).name if _art_out_dir else slug
                    current_info["reference_image_url"] = f"/output/{_art_dir_name}/artstyle/{Path(ref).name}"
            except Exception:
                pass

    # 사용 가능한 스타일 목록
    styles = []
    for p in sorted(Path("artstyle/styles").glob("*.json")):
        try:
            d = _json.loads(p.read_text(encoding="utf-8"))
            styles.append({"path": f"artstyle/styles/{p.name}", "name": d.get("name", p.stem), "file": p.name})
        except Exception:
            styles.append({"path": f"artstyle/styles/{p.name}", "name": p.stem, "file": p.name})

    return JSONResponse({"current": current, "current_info": current_info, "available": styles})


@app.post("/api/p/{slug}/art-style")
async def set_art_style(request: Request, slug: str):
    """프로젝트 아트스타일 변경."""
    import json as _json
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    body = await request.json()
    new_style = body.get("art_style", "")
    config = project.get("config", {})
    if isinstance(config, str):
        config = _json.loads(config)
    config["art_style"] = new_style
    pm.set_config(project["id"], config)
    return JSONResponse({"ok": True, "art_style": new_style})


@app.get("/api/p/{slug}/images/history/{scene_num}")
async def image_history(slug: str, scene_num: int):
    """씬의 이미지 생성 히스토리."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else slug
    history_dir = Path(out_dir) / "images" / "history"
    if not history_dir.exists():
        return JSONResponse({"versions": []})
    versions = []
    for f in sorted(history_dir.glob(f"scene_{scene_num:03d}_*")):
        versions.append({
            "filename": f.name,
            "url": f"/output/{dir_name}/images/history/{f.name}",
            "size_bytes": f.stat().st_size,
        })
    return JSONResponse({"versions": versions})


@app.put("/api/p/{slug}/scenes/{scene_num}")
async def api_update_scene(request: Request, slug: str, scene_num: int):
    """씬 편집 → Supabase Storage에 저장."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    pid = project["id"]

    body = await request.json()

    # scene_specs.json 로드
    specs = load_project_json(out_dir,"scene_specs.json")
    if not specs:
        return JSONResponse({"error": "scene_specs.json not found"}, status_code=404)

    # 해당 씬 찾아서 업데이트
    updated = False
    for i, scene in enumerate(specs.get("scenes", [])):
        if scene["sceneNumber"] == scene_num:
            specs["scenes"][i] = {**scene, **body}
            updated = True
            break

    if not updated:
        return JSONResponse({"error": f"Scene {scene_num} not found"}, status_code=404)

    # 저장
    pm.save_project_json(pid, "scene_specs.json", specs)

    # 씬 편집 시 해당 씬 썸네일 무효화 (다음 Capture 시 재생성)
    out_dir = project.get("output_dir", "")
    if out_dir:
        thumb_path = Path(out_dir) / "thumbnails" / f"scene_{str(scene_num).zfill(3)}.png"
        if thumb_path.exists():
            thumb_path.unlink(missing_ok=True)

    return {"ok": True, "scene_number": scene_num, "thumbnail_invalidated": True}


@app.post("/projects/{project_id}/cleanup", response_class=HTMLResponse)
async def run_cleanup(request: Request, project_id: int):
    pm = get_pm()
    cm = CleanupManager(pm)
    result = cm.full_cleanup(project_id, dry_run=True)
    return JSONResponse(result)


# ─────────────────────────────
# Image Candidates API
# ─────────────────────────────

@app.get("/api/p/{slug}/scene/{scene_num}/image-candidates")
async def get_image_candidates_by_slug(slug: str, scene_num: int, include_all: bool = False):
    """slug 기반 씬 이미지 후보 목록.

    include_all=true: 다운로드하지 않은 후보까지 썸네일 URL로 반환.
    """
    from auto_agent.dashboard.helpers import get_scene_image_candidates
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    out_dir = project["output_dir"]
    dir_name = Path(out_dir).name if out_dir else slug
    candidates = get_scene_image_candidates(dir_name, scene_num, out_dir)

    # 전체 후보 (썸네일 포함) 반환
    all_candidates = []
    if include_all:
        all_candidates = _load_all_candidates(out_dir, scene_num)

    return {
        "scene_number": scene_num,
        "candidates": candidates,
        "all_candidates": all_candidates,
    }


@app.get("/api/projects/{project_id}/scene/{scene_num}/image-candidates")
async def get_image_candidates(project_id: int, scene_num: int, include_all: bool = False):
    """레거시 씬 이미지 후보 목록."""
    from auto_agent.dashboard.helpers import get_scene_image_candidates
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    out_dir = project["output_dir"]
    dir_name = Path(out_dir).name if out_dir else project["slug"]
    candidates = get_scene_image_candidates(dir_name, scene_num, out_dir)
    all_candidates = []
    if include_all:
        all_candidates = _load_all_candidates(out_dir, scene_num)
    return {"scene_number": scene_num, "candidates": candidates, "all_candidates": all_candidates}


@app.post("/api/p/{slug}/scene/{scene_num}/download-candidate")
async def download_candidate_image(request: Request, slug: str, scene_num: int):
    """썸네일에서 선택한 미다운로드 후보의 원본을 다운로드 + 적용."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)

    body = await request.json()
    image_url = body.get("image_url", "")
    if not image_url:
        return JSONResponse({"error": "image_url required"}, status_code=400)

    output_dir = Path(project["output_dir"])
    images_dir = output_dir / "images"
    search_dir = images_dir / "search"
    search_dir.mkdir(parents=True, exist_ok=True)

    # 원본 다운로드
    try:
        import requests as req
        resp = req.get(image_url, timeout=30, headers={"User-Agent": "KairosAgent/1.0"})
        resp.raise_for_status()

        # 파일명: slug_scene_NNN_downloaded_hash.ext
        import hashlib
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        ext = ".jpg"
        ct = resp.headers.get("content-type", "")
        if "png" in ct:
            ext = ".png"
        elif "webp" in ct:
            ext = ".webp"

        scene_key = f"scene_{scene_num:03d}"
        filename = f"{scene_key}_dl_{url_hash}{ext}"
        save_path = search_dir / filename
        save_path.write_bytes(resp.content)

        # 최종 이미지로 복사
        final_path = images_dir / f"{scene_key}{ext}"
        import shutil
        shutil.copy2(save_path, final_path)

        # scene_specs.json 업데이트
        _out_dir = project.get("output_dir", "")
        _dir_name = Path(_out_dir).name if _out_dir else slug
        local_url = f"/output/{_dir_name}/images/{final_path.name}"
        specs = load_project_json(project.get("output_dir", ""),"scene_specs.json")
        if specs:
            for scene in specs.get("scenes", []):
                sn = scene.get("sceneNumber") or scene.get("scene_number")
                if sn == scene_num:
                    scene["imagePath"] = local_url
                    break
            pm.save_project_json(project["id"], "scene_specs.json", specs)

        return {"ok": True, "image_url": local_url, "saved_path": str(save_path)}

    except Exception as e:
        return JSONResponse({"error": f"다운로드 실패: {e}"}, status_code=500)


def _load_all_candidates(output_dir: str, scene_num: int) -> list:
    """image_candidates.json에서 해당 씬의 전체 후보 메타데이터 로드."""
    candidates_path = Path(output_dir) / "image_candidates.json"
    if not candidates_path.exists():
        return []
    try:
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
        scene_key = f"scene_{scene_num:03d}"
        scene_data = data.get(scene_key, {})
        return scene_data.get("candidates", [])
    except Exception:
        return []


@app.post("/api/p/{slug}/scene/{scene_num}/select-image")
async def select_image_candidate_by_slug(request: Request, slug: str, scene_num: int):
    """slug 기반 이미지 선택."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    return await _do_select_image(request, project, scene_num)


@app.post("/api/projects/{project_id}/scene/{scene_num}/select-image")
async def select_image_candidate(request: Request, project_id: int, scene_num: int):
    """레거시 이미지 선택."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    return await _do_select_image(request, project, scene_num)


async def _do_select_image(request: Request, project: dict, scene_num: int):
    """이미지 선택 공통 로직."""
    body = await request.json()
    scene_key = f"scene_{scene_num:03d}"

    asset_id = body.get("asset_id")
    image_url = body.get("url", "")
    if not asset_id and not image_url:
        rank = body.get("rank")
        if not rank:
            return JSONResponse({"error": "asset_id, url, or rank required"}, status_code=400)
        # rank → Supabase 후보에서 찾기
        pm = get_pm()
        candidates = pm.get_scene_image_candidates(project["id"], scene_num)
        if rank <= len(candidates):
            image_url = candidates[rank - 1].get("url", "")
        if not image_url:
            return JSONResponse({"error": f"candidate rank {rank} not found"}, status_code=404)

    # scene_specs.json의 imagePath를 Supabase URL로 업데이트
    pm = get_pm()
    specs = load_project_json(project.get("output_dir", ""),"scene_specs.json")
    if specs:
        for scene in specs.get("scenes", []):
            sn = scene.get("sceneNumber") or scene.get("scene_number")
            if sn == scene_num:
                scene["imagePath"] = image_url
                break
        pm.save_project_json(project["id"], "scene_specs.json", specs)

    return {"ok": True, "scene": scene_key, "image_url": image_url}


# ─────────────────────────────
# Pipeline 실행 API
# ─────────────────────────────

_pipeline_procs: dict[str, subprocess.Popen] = {}


def _is_pipeline_running(slug: str) -> bool:
    proc = _pipeline_procs.get(slug)
    if proc and proc.poll() is None:
        return True
    _pipeline_procs.pop(slug, None)
    return False


@app.post("/api/p/{slug}/pipeline/start")
async def pipeline_start(slug: str, request: Request):
    """파이프라인 백그라운드 실행."""
    if _is_pipeline_running(slug):
        return {"ok": True, "status": "already_running"}

    try:
        body = await request.json()
    except Exception:
        body = {}
    from_step = body.get("from_step")

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env["PYTHONPATH"] = str(get_workspace_dir())

    # .env 로드
    dotenv_path = get_workspace_dir() / ".env"
    if dotenv_path.exists():
        for line in dotenv_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    cmd = [
        sys.executable, "-m", "auto_agent.orchestrator.runner",
        "--project", slug,
    ]
    if from_step:
        cmd.extend(["--from", from_step])

    # output_dir에서 디렉토리명 결정 (uuid_{slug} 형식)
    _pm = get_pm()
    _proj = _pm.get_project(slug=slug)
    _out_dir = _proj.get("output_dir", "") if _proj else ""
    _dir_name = Path(_out_dir).name if _out_dir else slug
    log_path = get_workspace_dir() / "output" / _dir_name / "pipeline.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")

    proc = subprocess.Popen(
        cmd,
        cwd=str(get_workspace_dir()),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    _pipeline_procs[slug] = proc

    from auto_agent.dashboard.agent_messenger import post_message
    post_message("Director", "파이프라인 실행 시작", phase="pipeline",
                 project_slug=slug, level="info")

    return {"ok": True, "status": "started", "pid": proc.pid}


@app.get("/api/p/{slug}/pipeline/status")
async def pipeline_status(slug: str):
    """파이프라인 실행 상태 확인."""
    running = _is_pipeline_running(slug)
    result = {"running": running, "slug": slug}
    if not running:
        proc = _pipeline_procs.get(slug)
        if proc:
            result["exit_code"] = proc.returncode
    return result


@app.post("/api/p/{slug}/pipeline/stop")
async def pipeline_stop(slug: str):
    """파이프라인 중지."""
    proc = _pipeline_procs.get(slug)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        from auto_agent.dashboard.agent_messenger import post_message
        post_message("Director", "파이프라인 수동 중지", phase="pipeline",
                     project_slug=slug, level="warning")
        return {"ok": True, "status": "stopped"}
    return {"ok": True, "status": "not_running"}


# ─────────────────────────────
# Remotion Studio API
# ─────────────────────────────

def _is_studio_running() -> bool:
    """Remotion Studio 프로세스가 실행 중인지 확인."""
    global _studio_proc
    if _studio_proc and _studio_proc.poll() is None:
        return True
    _studio_proc = None
    # 포트로도 확인 (외부에서 시작된 경우)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", STUDIO_PORT)) == 0


@app.get("/api/studio/status")
async def studio_status():
    """Remotion Studio 상태 확인."""
    return {"running": _is_studio_running(), "port": STUDIO_PORT}


@app.post("/api/studio/setup")
async def studio_setup(request: Request):
    """프로젝트 symlink + manifest 갈아끼우기 (Studio 재시작 없이)."""
    try:
        body = await request.json()
        slug = body.get("slug", "")
    except Exception:
        slug = ""
    if not slug:
        return {"ok": False, "error": "slug required"}
    _setup_studio_project(slug)
    return {"ok": True, "slug": slug, "running": _is_studio_running(), "port": STUDIO_PORT}


def _setup_studio_project(slug: str):
    """Studio 시작 전 manifest 설정 — 로컬 PM 기반."""
    ws = get_workspace_dir()
    public_dir = REMOTION_DIR / "public"
    manifest_dst = public_dir / "manifest.json"

    try:
        pm = get_pm()
        project = pm.get_project(slug=slug)
        if not project:
            return

        pid = str(project["id"])
        out_dir = project.get("output_dir", "")
        storage_key = project.get("storage_key", f"proj-{slug}")

        # build_manifest 실행
        import shutil
        result = subprocess.run(
            [sys.executable, "-m", "auto_agent.scripts.build_manifest",
             pid, storage_key, out_dir],
            cwd=str(ws),
            timeout=120,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        # 빌드된 manifest를 메인으로 복사
        built = public_dir / "manifests" / f"{storage_key}.json"
        if built.exists():
            shutil.copy2(str(built), str(manifest_dst))
        elif manifest_dst.exists():
            pass  # 이미 build_manifest가 직접 생성했을 수 있음
    except Exception as e:
        print(f"[WARN] Studio setup 실패: {e}")


def _ensure_studio_ready() -> Optional[str]:
    """Studio 실행 전 환경 체크. 문제 있으면 에러 메시지 반환, 없으면 None."""
    if not REMOTION_DIR.exists():
        # remotion 템플릿 자동 복사 시도
        try:
            from auto_agent.paths import get_package_dir
            import shutil
            template = get_package_dir() / "remotion_template"
            if template.exists():
                shutil.copytree(template, REMOTION_DIR, dirs_exist_ok=True)
            else:
                return "remotion 디렉토리 없음. auto-kairos init을 먼저 실행하세요."
        except Exception as e:
            return f"remotion 복사 실패: {e}"

    # node_modules 체크 + 자동 설치
    node_modules = REMOTION_DIR / "node_modules"
    if not node_modules.exists():
        try:
            from auto_agent.utils.platform import get_node_bin_dir as _check_node
            _check_node()
        except EnvironmentError:
            return "Node.js가 설치되지 않았습니다. install.sh를 실행하거나 https://nodejs.org 에서 설치하세요."
        npm_cmd = _get_npm_cmd()
        try:
            result = subprocess.run(
                [npm_cmd, "install"],
                cwd=str(REMOTION_DIR),
                env=_get_node_env(),
                capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
            if result.returncode != 0:
                return f"npm install failed: {result.stderr[:300]}"
        except Exception as e:
            return f"npm install 에러: {e}"

    return None


def _find_cmd(name: str) -> bool:
    """명령이 PATH에 있는지 확인."""
    import shutil
    return shutil.which(name) is not None


@app.post("/api/studio/start")
async def studio_start(request: Request):
    """Remotion Studio 시작."""
    global _studio_proc
    if _is_studio_running():
        return {"ok": True, "message": "already running"}

    # 환경 체크 (remotion 디렉토리, node_modules 등)
    check_err = _ensure_studio_ready()
    if check_err:
        return {"ok": False, "error": check_err}

    # 프로젝트 slug로 manifest 설정
    try:
        body = await request.json()
        slug = body.get("slug", "")
    except Exception:
        slug = ""
    if slug:
        _setup_studio_project(slug)

    npx_cmd = _get_npx_cmd()
    try:
        env = _get_node_env()
        env["BROWSER"] = "none"  # 자동 브라우저 열기 방지
        _studio_proc = subprocess.Popen(
            [npx_cmd, "remotion", "studio", "--port", str(STUDIO_PORT)],
            cwd=str(REMOTION_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "pid": _studio_proc.pid}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.post("/api/studio/stop")
async def studio_stop():
    """Remotion Studio 중지."""
    global _studio_proc
    if _studio_proc and _studio_proc.poll() is None:
        _studio_proc.terminate()
        try:
            _studio_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _studio_proc.kill()
        _studio_proc = None
        return {"ok": True}
    _studio_proc = None
    return {"ok": False, "message": "not running"}


# ─────────────────────────────
# WebSocket Terminal
# ─────────────────────────────

@app.websocket("/ws/terminal")
async def terminal_ws(websocket: WebSocket):
    """xterm.js와 연결되는 WebSocket 터미널."""
    await websocket.accept()

    if IS_WINDOWS:
        await websocket.send_text("터미널은 macOS/Linux에서만 지원됩니다.\r\n")
        await websocket.close()
        return

    # pty 생성
    master_fd, slave_fd = pty.openpty()

    # 셸 프로세스 시작
    ws_dir = str(get_workspace_dir())
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "120"
    env["LINES"] = "30"

    shell = os.environ.get("SHELL", "/bin/bash")
    proc = subprocess.Popen(
        [shell, "--login"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=ws_dir,
        env=env,
        preexec_fn=os.setsid,
    )
    os.close(slave_fd)

    async def read_pty():
        """pty 출력을 WebSocket으로 전송."""
        try:
            while True:
                await asyncio.sleep(0.01)
                if select.select([master_fd], [], [], 0)[0]:
                    data = os.read(master_fd, 4096)
                    if data:
                        await websocket.send_text(data.decode("utf-8", errors="replace"))
                    else:
                        break
                if proc.poll() is not None:
                    break
        except (OSError, WebSocketDisconnect):
            pass

    read_task = asyncio.create_task(read_pty())

    try:
        while True:
            data = await websocket.receive_text()
            os.write(master_fd, data.encode("utf-8"))
    except WebSocketDisconnect:
        pass
    finally:
        read_task.cancel()
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
        os.close(master_fd)


# ─────────────────────────────
# 데이터 헬퍼
# ─────────────────────────────

def _get_file_status(pm, project_id: str) -> dict:
    """assets 테이블에서 파일 상태 조회."""
    filenames = [
        "research_report.json", "outline.json", "final_manuscript.md",
        "scene_decomposition.json", "scene_specs.json", "motion_plan.json",
        "tts_results.json", "subtitles.json", "pipeline_state.json",
    ]
    result = {}
    assets = pm.get_assets(project_id, asset_type="json") + pm.get_assets(project_id, asset_type="manuscript")
    asset_map = {a.get("file_name"): a for a in assets}
    for fname in filenames:
        a = asset_map.get(fname)
        if a:
            result[fname] = {
                "exists": True,
                "size": a.get("file_size", 0),
                "size_kb": round((a.get("file_size") or 0) / 1024, 1),
                "modified": (a.get("created_at") or "")[:16].replace("T", " "),
            }
        else:
            result[fname] = {"exists": False, "size": 0, "size_kb": 0, "modified": None}
    return result


def _get_recent_images(pm, project_id: str, limit: int = 3) -> list:
    """최근 이미지 URL 목록."""
    assets = pm.get_assets(project_id, asset_type="image")
    urls = [a.get("storage_url") for a in assets if a.get("storage_url")]
    return urls[:limit]


def _enrich_scenes(pm, project_id: str, scenes: list,
                    tts_results: dict = None,
                    slug: str = "", out_dir: str = "") -> list:
    """씬 미디어 URL 보강 (배치 쿼리)."""
    tts_map = {}
    if tts_results:
        for r in tts_results.get("results", []):
            tts_map[r["scene"]] = r

    # 배치: 이미지/오디오 에셋을 한 번에 조회
    image_assets = pm.get_assets(project_id, asset_type="image")
    audio_assets = pm.get_assets(project_id, asset_type="audio")
    img_map = {a.get("scene_number"): a.get("storage_url") for a in image_assets}
    aud_map = {a.get("scene_number"): a.get("storage_url") for a in audio_assets}

    # 썸네일 디렉토리 확인
    thumb_dir = Path(out_dir) / "thumbnails" if out_dir else None
    has_thumbs = thumb_dir and thumb_dir.exists()

    for scene in scenes:
        sn = scene["sceneNumber"]
        scene["_image_url"] = img_map.get(sn)
        scene["_audio_url"] = aud_map.get(sn)
        tts = tts_map.get(sn, {})
        scene["_tts_duration"] = tts.get("duration")
        scene["_tts_status"] = tts.get("status")
        layout, explicit = resolve_layout(scene)
        scene["_layout"] = layout
        scene["_layout_explicit"] = explicit

        # Remotion 캡처 썸네일
        scene["_thumbnail_url"] = None
        if has_thumbs and slug:
            thumb_path = thumb_dir / f"scene_{str(sn).zfill(3)}.png"
            if thumb_path.exists():
                scene["_thumbnail_url"] = f"/api/p/{slug}/thumbnails/scene/{sn}"

    return scenes
