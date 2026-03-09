"""
auto_agent 프로젝트 관리 대시보드.
FastAPI + Jinja2 + htmx + xterm.js.
"""
import asyncio
import json
import os
import pty
import select
import socket
import subprocess
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_agent.db.connection import db_exists, init_db
from auto_agent.db.project_manager import ProjectManager
from auto_agent.db.cleanup import CleanupManager
from auto_agent.paths import get_data_dir, get_workspace_dir
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

app = FastAPI(title="Auto Agent Dashboard")

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


def get_pm() -> ProjectManager:
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
}

# ─────────────────────────────
# Remotion Studio 프로세스 관리
# ─────────────────────────────
REMOTION_DIR = get_workspace_dir() / "remotion"
STUDIO_PORT = 3000

# Node.js PATH 보장 (homebrew/로컬 설치 모두 커버)
_node_paths = [
    Path.home() / "local" / "nodejs" / f"node-v22.14.0-darwin-x64" / "bin",
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
]
for _np in _node_paths:
    if (_np / "node").exists() and str(_np) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{_np}:{os.environ.get('PATH', '')}"
        break
_studio_proc: Optional[subprocess.Popen] = None


def _load_tab_data(pm: ProjectManager, project: dict, tab: str) -> dict:
    """탭별 데이터 로딩."""
    project_id = project["id"]
    out_dir = project.get("output_dir", "")
    slug = project.get("slug", "")
    context = {"project": project, "tab": tab, "slug": slug}

    if tab == "overview":
        context["asset_counts"] = pm.get_asset_counts(project_id)
        context["cost"] = pm.get_cost_summary(project_id)
        context["file_status"] = get_file_status(out_dir)
        context["recent_images"] = get_recent_images(slug, out_dir)
        context["pipeline_progress"] = get_pipeline_progress(out_dir, str(DATA_DIR))

    elif tab == "pipeline":
        context["runs"] = pm.get_pipeline_history(project_id)
        context["pipeline_progress"] = get_pipeline_progress(out_dir, str(DATA_DIR))

    elif tab == "research":
        context["research"] = load_project_json(out_dir, "research_report.json")

    elif tab == "manuscript":
        text = load_project_text(out_dir, "final_manuscript.md")
        context["chapters"] = parse_manuscript_chapters(text) if text else []
        tts = load_project_json(out_dir, "tts_results.json")
        tts_map = {}
        if tts:
            for r in tts.get("results", []):
                tts_map[r["scene"]] = r
        context["tts_map"] = tts_map

    elif tab == "storyboard":
        specs = load_project_json(out_dir, "scene_specs.json")
        scenes = specs.get("scenes", []) if specs else []
        tts = load_project_json(out_dir, "tts_results.json")
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


@app.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: int, tab: str = "overview"):
    """프로젝트 상세 페이지 — 초기 탭 콘텐츠 포함."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    context["request"] = request
    return templates.TemplateResponse("project.html", context)


# ─────────────────────────────
# HTMX Partials — 탭 콘텐츠
# ─────────────────────────────

@app.get("/api/projects/{project_id}/tab/{tab}", response_class=HTMLResponse)
async def project_tab_content(request: Request, project_id: int, tab: str):
    """탭 콘텐츠만 반환 (HTMX partial)."""
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

@app.get("/api/projects/{project_id}/storyboard/scene/{scene_num}", response_class=HTMLResponse)
async def storyboard_scene_detail(request: Request, project_id: int, scene_num: int):
    """씬 상세 패널 (HTMX partial)."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return HTMLResponse("Not found", status_code=404)

    out_dir = project["output_dir"]
    slug = project["slug"]

    specs = load_project_json(out_dir, "scene_specs.json")
    scene = None
    if specs:
        for s in specs.get("scenes", []):
            if s["sceneNumber"] == scene_num:
                scene = s
                break

    if not scene:
        return HTMLResponse(f"Scene {scene_num} not found", status_code=404)

    scene["_image_url"] = get_scene_image_url(slug, scene_num, out_dir)
    scene["_audio_url"] = get_scene_audio_url(slug, scene_num, out_dir)

    tts = load_project_json(out_dir, "tts_results.json")
    if tts:
        for r in tts.get("results", []):
            if r["scene"] == scene_num:
                scene["_tts_duration"] = r.get("duration")
                break

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


@app.post("/projects/{project_id}/cleanup", response_class=HTMLResponse)
async def run_cleanup(request: Request, project_id: int):
    pm = get_pm()
    cm = CleanupManager(pm)
    result = cm.full_cleanup(project_id, dry_run=True)
    return JSONResponse(result)


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
    return {"ok": True, "slug": slug, "running": _is_studio_running()}


def _setup_studio_project(slug: str):
    """Studio 시작 전 프로젝트 symlink + manifest 설정."""
    ws = get_workspace_dir()
    project_dir = ws / "output" / slug
    public_dir = REMOTION_DIR / "public"

    if not project_dir.exists():
        return

    # 1) public/project → output/{slug} symlink
    symlink = public_dir / "project"
    target = os.path.relpath(project_dir, public_dir)
    if symlink.is_symlink():
        if os.readlink(str(symlink)) != target:
            symlink.unlink()
            symlink.symlink_to(target)
    elif not symlink.exists():
        symlink.symlink_to(target)

    # 2) manifest 빌드 (motion_plan 있을 때만)
    if (project_dir / "scene_specs.json").exists() and (project_dir / "motion_plan.json").exists():
        try:
            env = os.environ.copy()
            env["PROJECT_NAME"] = slug
            subprocess.run(
                [sys.executable, "-m", "auto_agent.scripts.build_manifest", "--project", slug],
                cwd=str(ws),
                env=env,
                timeout=30,
                capture_output=True,
            )
        except Exception:
            pass


@app.post("/api/studio/start")
async def studio_start(request: Request):
    """Remotion Studio 시작."""
    global _studio_proc
    if _is_studio_running():
        return {"ok": True, "message": "already running"}

    if not REMOTION_DIR.exists():
        return {"ok": False, "error": "remotion directory not found"}

    # 프로젝트 slug로 symlink + manifest 설정
    try:
        body = await request.json()
        slug = body.get("slug", "")
    except Exception:
        slug = ""
    if slug:
        _setup_studio_project(slug)

    try:
        env = os.environ.copy()
        env["BROWSER"] = "none"  # 자동 브라우저 열기 방지
        _studio_proc = subprocess.Popen(
            ["npx", "remotion", "studio", "--port", str(STUDIO_PORT)],
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

    # pty 생성
    master_fd, slave_fd = pty.openpty()

    # bash 프로세스 시작
    ws_dir = str(get_workspace_dir())
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = "120"
    env["LINES"] = "30"

    proc = subprocess.Popen(
        ["/bin/bash", "--login"],
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
        loop = asyncio.get_event_loop()
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
