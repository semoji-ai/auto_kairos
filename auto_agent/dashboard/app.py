"""
auto_agent_v2 프로젝트 관리 대시보드.
FastAPI + Jinja2 + htmx.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_agent.db.connection import db_exists, init_db
from auto_agent.db.project_manager import ProjectManager
from auto_agent.db.cleanup import CleanupManager

app = FastAPI(title="Auto Agent V2 Dashboard")

DASHBOARD_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))


def get_pm() -> ProjectManager:
    if not db_exists():
        init_db()
    return ProjectManager()


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
    """프로젝트 상세 페이지."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project:
        return HTMLResponse("Project not found", status_code=404)

    context = {
        "request": request,
        "project": project,
        "tab": tab,
    }

    if tab == "overview":
        context["asset_counts"] = pm.get_asset_counts(project_id)
        context["cost"] = pm.get_cost_summary(project_id)

    elif tab == "pipeline":
        context["runs"] = pm.get_pipeline_history(project_id)

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

    return templates.TemplateResponse("project.html", context)


@app.post("/projects/{project_id}/cleanup", response_class=HTMLResponse)
async def run_cleanup(request: Request, project_id: int):
    """클린업 실행."""
    pm = get_pm()
    cm = CleanupManager(pm)
    result = cm.full_cleanup(project_id, dry_run=True)
    return JSONResponse(result)


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
