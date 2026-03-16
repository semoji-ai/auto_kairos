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

from auto_agent.db.connection import db_exists, init_db
from auto_agent.db.project_manager import ProjectManager
from auto_agent.db.cleanup import CleanupManager
from auto_agent.paths import get_data_dir, get_workspace_dir
from auto_agent.supabase_client import supabase_enabled
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
    get_recent_images,
)
from auto_agent.dashboard.actions import router as actions_router
from auto_agent.dashboard.json_editor import router as json_editor_router
from auto_agent.dashboard.sse import router as sse_router
from auto_agent.dashboard.memory_routes import router as memory_router
from auto_agent.dashboard.scene_editor import router as scene_editor_router
from auto_agent.dashboard.scene_editor import manifest_router
from auto_agent.dashboard.design_presets import router as design_presets_router

app = FastAPI(title="Auto Agent Dashboard")

# ─── 신규 라우터 등록 ───
app.include_router(actions_router)
app.include_router(json_editor_router)
app.include_router(sse_router)
app.include_router(memory_router)
app.include_router(scene_editor_router)
app.include_router(manifest_router)
app.include_router(design_presets_router)

DASHBOARD_DIR = Path(__file__).parent
DATA_DIR = get_data_dir()

app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")

# output 디렉토리 마운트 (이미지/오디오 직접 서빙)
workspace = get_workspace_dir()
output_dir = workspace / "output"
if output_dir.exists():
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

templates = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))
# Jinja2 필터 등록
templates.env.filters["format_headline"] = format_headline


# Supabase 모드: SUPABASE_URL + SUPABASE_KEY 환경변수 설정 시 활성화
USE_SUPABASE = supabase_enabled()


def get_pm():
    """데이터 소스에 따라 ProjectManager 반환.
    Supabase 환경변수가 있으면 SupabaseProjectManager, 없으면 로컬 SQLite."""
    if USE_SUPABASE:
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        return SupabaseProjectManager()
    if not db_exists():
        init_db()
    return ProjectManager()


TAB_TEMPLATES = {
    "overview": "partials/_overview.html",
    "pipeline": "partials/_pipeline.html",
    "research": "partials/_research.html",
    "manuscript": "partials/_manuscript.html",
    "storyboard": "partials/_storyboard.html",
    "studio": "partials/_studio.html",
    "assets": "partials/_assets.html",
    "versions": "partials/_versions.html",
    "costs": "partials/_costs.html",
    "design": "partials/_design.html",
}

# ─────────────────────────────
# Remotion Studio 프로세스 관리
# ─────────────────────────────
REMOTION_DIR = get_workspace_dir() / "remotion"
STUDIO_PORT = 3100

# Node.js PATH 보장 (homebrew/nvm/fnm/volta/winget 등 커버)
_node_candidates = [
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path.home() / ".nvm" / "current" / "bin",
    Path.home() / ".fnm" / "current" / "bin",
    Path.home() / ".volta" / "bin",
    Path.home() / "local" / "nodejs" / f"node-v22.14.0-darwin-x64" / "bin",
]
# nvm: 실제 버전 디렉토리 탐색
_nvm_dir = Path.home() / ".nvm" / "versions" / "node"
if _nvm_dir.exists():
    for _v in sorted(_nvm_dir.iterdir(), reverse=True):
        _node_candidates.insert(0, _v / "bin")

_node_exe = "node.exe" if IS_WINDOWS else "node"
for _np in _node_candidates:
    if (_np / _node_exe).exists() and str(_np) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{_np}{os.pathsep}{os.environ.get('PATH', '')}"
        break
_studio_proc: Optional[subprocess.Popen] = None


def _load_tab_data(pm, project: dict, tab: str) -> dict:
    """탭별 데이터 로딩. Supabase/로컬 모드 자동 분기."""
    project_id = project["id"]
    out_dir = project.get("output_dir", "")
    slug = project.get("slug", "")
    context = {"project": project, "tab": tab, "slug": slug}

    # Supabase 모드에서는 pm.load_project_json() 사용
    def _load_json(filename):
        if USE_SUPABASE:
            return pm.load_project_json(project_id, filename)
        return load_project_json(out_dir, filename)

    def _load_text(filename):
        if USE_SUPABASE:
            return pm.load_project_text(project_id, filename)
        return load_project_text(out_dir, filename)

    def _image_url(scene_num):
        if USE_SUPABASE:
            return pm.get_scene_image_url(project_id, scene_num)
        return get_scene_image_url(slug, scene_num, out_dir)

    def _audio_url(scene_num):
        if USE_SUPABASE:
            return pm.get_scene_audio_url(project_id, scene_num)
        return get_scene_audio_url(slug, scene_num, out_dir)

    if tab == "overview":
        context["asset_counts"] = pm.get_asset_counts(project_id)
        context["cost"] = pm.get_cost_summary(project_id)
        if USE_SUPABASE:
            context["file_status"] = _supabase_file_status(pm, project_id)
            context["recent_images"] = _supabase_recent_images(pm, project_id)
        else:
            context["file_status"] = get_file_status(out_dir)
            context["recent_images"] = get_recent_images(slug, out_dir)
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

    elif tab == "manuscript":
        text = _load_text("final_manuscript.md")
        context["chapters"] = parse_manuscript_chapters(text) if text else []
        tts = _load_json("tts_results.json")
        tts_map = {}
        if tts:
            for r in tts.get("results", []):
                tts_map[r["scene"]] = r
        context["tts_map"] = tts_map

    elif tab == "storyboard":
        specs = _load_json("scene_specs.json")
        scenes = specs.get("scenes", []) if specs else []
        tts = _load_json("tts_results.json")
        if USE_SUPABASE:
            scenes = _supabase_enrich_scenes(pm, project_id, scenes, tts, slug=slug, out_dir=out_dir)
        else:
            scenes = enrich_scenes_with_media(scenes, slug, out_dir, tts)
        context["scenes"] = scenes
        ch_set = sorted(set(s.get("chapter", 0) for s in scenes))
        context["chapters_list"] = ch_set

    elif tab == "studio":
        pass  # Studio 탭은 별도 데이터 불필요 (JS로 상태 확인)

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
async def project_by_slug(request: Request, slug: str, tab: str = "overview"):
    """slug 기반 프로젝트 상세 페이지."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    context["request"] = request
    return templates.TemplateResponse("project.html", context)


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int, tab: str = "overview"):
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

    if USE_SUPABASE:
        specs = pm.load_project_json(pid, "scene_specs.json")
    else:
        specs = load_project_json(out_dir, "scene_specs.json")
    scene = None
    if specs:
        for s in specs.get("scenes", []):
            if s["sceneNumber"] == scene_num:
                scene = s
                break

    if not scene:
        return HTMLResponse(f"Scene {scene_num} not found", status_code=404)

    if USE_SUPABASE:
        scene["_image_url"] = pm.get_scene_image_url(pid, scene_num)
        scene["_audio_url"] = pm.get_scene_audio_url(pid, scene_num)
    else:
        scene["_image_url"] = get_scene_image_url(slug, scene_num, out_dir)
        scene["_audio_url"] = get_scene_audio_url(slug, scene_num, out_dir)

    if USE_SUPABASE:
        tts = pm.load_project_json(pid, "tts_results.json")
    else:
        tts = load_project_json(out_dir, "tts_results.json")
    if tts:
        for r in tts.get("results", []):
            if r["scene"] == scene_num:
                scene["_tts_duration"] = r.get("duration")
                break

    if USE_SUPABASE:
        subtitles = pm.load_project_json(pid, "subtitles.json")
    else:
        subtitles = load_project_json(out_dir, "subtitles.json")
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
    """씬 목록 JSON (Supabase Storage에서 로드)."""
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    pid = project["id"]
    if USE_SUPABASE:
        specs = pm.load_project_json(pid, "scene_specs.json")
    else:
        specs = load_project_json(project["output_dir"], "scene_specs.json")
    if not specs:
        return {"scenes": []}
    return {"scenes": specs.get("scenes", [])}


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
    if USE_SUPABASE:
        specs = pm.load_project_json(pid, "scene_specs.json")
    else:
        specs = load_project_json(project["output_dir"], "scene_specs.json")
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
    if USE_SUPABASE:
        pm.save_project_json(pid, "scene_specs.json", specs)
    else:
        import json as _json
        from pathlib import Path as _Path
        fp = _Path(project["output_dir"]) / "scene_specs.json"
        fp.write_text(_json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "scene_number": scene_num}


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
async def get_image_candidates_by_slug(slug: str, scene_num: int):
    """slug 기반 씬 이미지 후보 목록."""
    from auto_agent.dashboard.helpers import get_scene_image_candidates
    pm = get_pm()
    project = pm.get_project(slug=slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    candidates = get_scene_image_candidates(slug, scene_num, project["output_dir"])
    return {"scene_number": scene_num, "candidates": candidates}


@app.get("/api/projects/{project_id}/scene/{scene_num}/image-candidates")
async def get_image_candidates(project_id: int, scene_num: int):
    """레거시 씬 이미지 후보 목록."""
    from auto_agent.dashboard.helpers import get_scene_image_candidates
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    candidates = get_scene_image_candidates(project["slug"], scene_num, project["output_dir"])
    return {"scene_number": scene_num, "candidates": candidates}


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
    """이미지 선택 공통 로직. Supabase/로컬 자동 분기."""
    import shutil

    body = await request.json()
    scene_key = f"scene_{scene_num:03d}"

    # ── Supabase 모드: asset_id 또는 url 기반 선택 ──
    if USE_SUPABASE:
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
        specs = pm.load_project_json(project["id"], "scene_specs.json")
        if specs:
            for scene in specs.get("scenes", []):
                sn = scene.get("sceneNumber") or scene.get("scene_number")
                if sn == scene_num:
                    scene["imagePath"] = image_url
                    break
            pm.save_project_json(project["id"], "scene_specs.json", specs)

        return {"ok": True, "scene": scene_key, "image_url": image_url}

    # ── 로컬 모드: rank 기반 파일 복사 ──
    rank = body.get("rank")
    if not rank:
        return JSONResponse({"error": "rank required"}, status_code=400)

    out_dir = Path(project["output_dir"])
    search_dir = out_dir / "images" / "search"
    images_dir = out_dir / "images"

    # 선택된 후보 파일 찾기
    candidate = None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = search_dir / f"{scene_key}_{rank:02d}{ext}"
        if path.exists():
            candidate = path
            break

    if not candidate:
        return JSONResponse({"error": f"candidate rank {rank} not found"}, status_code=404)

    # 기존 최종 이미지 제거 후 교체
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        old = images_dir / f"{scene_key}{ext}"
        if old.exists():
            old.unlink()

    final_path = images_dir / f"{scene_key}{candidate.suffix}"
    shutil.copy2(candidate, final_path)

    # image_assets.json 업데이트
    registry_path = images_dir / "image_assets.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for asset in registry.get("assets", []):
            if asset.get("scene") == scene_key:
                asset["selected_rank"] = rank
                break
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"ok": True, "scene": scene_key, "selected_rank": rank,
            "image_url": f"/output/{project['slug']}/images/{final_path.name}"}


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
    """Studio 시작 전 manifest 설정. 로컬/Supabase 프로젝트 모두 지원."""
    ws = get_workspace_dir()
    public_dir = REMOTION_DIR / "public"
    manifest_dst = public_dir / "manifest.json"

    # Supabase에서 프로젝트 조회 → manifest 빌드
    try:
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()

        # proj-* 형태이면 storage_key로 직접 조회
        if slug.startswith("proj-"):
            cached = public_dir / "manifests" / f"{slug}.json"
            if cached.exists():
                import shutil
                shutil.copy2(str(cached), str(manifest_dst))
                return

        project = pm.get_project(slug=slug) if not slug.startswith("proj-") else None
        storage_key = project.get("storage_key", "") if project else slug
        pid = project.get("id", "") if project else slug

        if storage_key and pid:
            subprocess.run(
                [sys.executable, "-m", "auto_agent.scripts.build_manifest",
                 pid, storage_key],
                cwd=str(ws),
                timeout=120,
                capture_output=True,
            )
            built = public_dir / "manifests" / f"{storage_key}.json"
            if built.exists():
                import shutil
                shutil.copy2(str(built), str(manifest_dst))
    except Exception:
        pass


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
        npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"
        npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
        if not _find_cmd(npm_cmd):
            return "Node.js가 설치되지 않았습니다. install.sh를 실행하거나 https://nodejs.org 에서 설치하세요."
        try:
            result = subprocess.run(
                [npm_cmd, "install"],
                cwd=str(REMOTION_DIR),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                return f"npm install 실패: {result.stderr[:300]}"
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

    npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"
    try:
        env = os.environ.copy()
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
# Supabase 모드 헬퍼
# ─────────────────────────────

def _supabase_file_status(pm, project_id: str) -> dict:
    """Supabase assets 테이블에서 파일 상태 조회."""
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


def _supabase_recent_images(pm, project_id: str, limit: int = 3) -> list:
    """Supabase에서 최근 이미지 URL 목록."""
    assets = pm.get_assets(project_id, asset_type="image")
    urls = [a.get("storage_url") for a in assets if a.get("storage_url")]
    return urls[:limit]


def _supabase_enrich_scenes(pm, project_id: str, scenes: list,
                             tts_results: dict = None,
                             slug: str = "", out_dir: str = "") -> list:
    """Supabase 기반 씬 미디어 URL 보강 (배치 쿼리)."""
    tts_map = {}
    if tts_results:
        for r in tts_results.get("results", []):
            tts_map[r["scene"]] = r

    # 배치: 이미지/오디오 에셋을 한 번에 조회
    image_assets = pm.get_assets(project_id, asset_type="image")
    audio_assets = pm.get_assets(project_id, asset_type="audio")
    img_map = {a.get("scene_number"): a.get("storage_url") for a in image_assets}
    aud_map = {a.get("scene_number"): a.get("storage_url") for a in audio_assets}

    from auto_agent.dashboard.helpers import resolve_layout, render_scene_preview

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
        scene["_preview_html"] = render_scene_preview(scene)

        # Remotion 캡처 썸네일
        scene["_thumbnail_url"] = None
        if has_thumbs and slug:
            thumb_path = thumb_dir / f"scene_{str(sn).zfill(3)}.png"
            if thumb_path.exists():
                scene["_thumbnail_url"] = f"/api/p/{slug}/thumbnails/scene/{sn}"

    return scenes
