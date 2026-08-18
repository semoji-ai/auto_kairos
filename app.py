"""
auto_agent 프로젝트 관리 대시보드.
FastAPI + Jinja2 + htmx + xterm.js.
"""
# .env 로드 (TTS/이미지 API 키 등 — 대시보드에서 재생성 시 필요)
try:
    from pathlib import Path as _P
    from dotenv import load_dotenv
    load_dotenv(_P(__file__).resolve().parent / ".env", override=True)
except Exception:
    pass

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
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from auto_agent.db.cleanup import CleanupManager
from auto_agent.paths import get_data_dir, get_workspace_dir
from auto_agent.supabase_client import supabase_enabled

USE_SUPABASE = supabase_enabled()
from auto_agent.dashboard.project_ref import (
    resolve_project_ref,
    canonical_uuid_url,
)
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
from auto_agent.dashboard.tools_routes import router as tools_router
app.include_router(tools_router)
from auto_agent.dashboard.enrichment_routes import router as enrichment_router
app.include_router(enrichment_router)

DASHBOARD_DIR = Path(__file__).parent / "auto_agent" / "dashboard"
DATA_DIR = get_data_dir()

app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR / "static")), name="static")

# output 디렉토리 마운트 (이미지/오디오 직접 서빙)
workspace = get_workspace_dir()

# 정적 에셋 서빙 — 워크스페이스와 코드 루트를 **둘 다** 본다.
#
# 워크스페이스는 NAS를 가리키고(output·DB가 거기 있다) 저장소는 로컬이라,
# 같은 이름의 폴더가 양쪽에 따로 자란다. 실제로 배경 이미지는 저장소에만,
# 폰트 셋은 NAS 쪽이 더 많았다. 한쪽만 걸면 어느 쪽을 골라도 파일을 잃는다.
from auto_agent.paths import get_charsheet_dir, get_package_dir

_ASSET_ROOTS = [workspace, get_package_dir().parent]


def _mount_asset(prefix: str, rel: str, extra: "Path | None" = None) -> None:
    """prefix로 들어온 파일을 여러 뿌리에서 찾아 낸다. 먼저 찾은 것을 준다."""
    dirs = [d for d in ([extra] if extra else []) + [r / rel for r in _ASSET_ROOTS]
            if d and d.is_dir()]
    if not dirs:
        return

    @app.get(prefix + "/{name:path}", name=prefix.strip("/"))
    async def _serve(name: str, _dirs=tuple(dirs)):
        for d in _dirs:
            f = (d / name).resolve()
            # 뿌리 밖으로 나가는 경로는 거절한다 (../ 방지)
            if f.is_file() and d.resolve() in f.parents:
                return FileResponse(f)
        return JSONResponse({"detail": "Not Found"}, status_code=404)


_mount_asset("/fonts", "remotion/public/fonts")
_mount_asset("/background", "remotion/public/background")
_mount_asset("/charsheets", "_imggen/characters/final_v2", extra=get_charsheet_dir())

output_dir = workspace / "output"
if output_dir.exists():
    app.mount("/output", StaticFiles(directory=str(output_dir)), name="output")

# 아트스타일 이미지 서빙 (/static/artstyle/ → auto_agent/data/artstyle/styles/)
_mount_asset("/artstyle", "auto_agent/data/artstyle/styles")

# 분리된 레이어 서빙 (/layers/<ep>_anim/s041b/03_박정희.png)
#
# 레이어는 프로젝트 폴더가 아니라 `_imggen/<ep>_anim/s<번호>/`에 쌓인다.
# 그 아래만 열어 준다 — _imggen 전체를 통째로 여는 것과는 다르다.
_LAYER_ROOT = get_package_dir().parent / "_imggen"


@app.get("/layers/{name:path}")
async def serve_layer(name: str):
    import re as _re

    if not _re.match(r"^[A-Za-z0-9_]+_anim/s\d{3}[a-z]?/[^/]+$", name):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    f = (_LAYER_ROOT / name).resolve()
    if f.is_file() and _LAYER_ROOT.resolve() in f.parents:
        return FileResponse(f)
    return JSONResponse({"detail": "Not Found"}, status_code=404)


def _ep_of(project: dict) -> str:
    """이 프로젝트의 **편 번호** 라벨(EP05 …).

    슬러그 꼬리를 그대로 쓰면 안 된다. 5편의 슬러그는 ep06b이고 6편은 ep05다
    — 원고를 다시 쓰면서 어긋난 것이라, 지도(_imggen/ep_map.json)가 정본이다.
    스크립트도 이 라벨로 폴더를 잡으므로 여기서 어긋나면 서로 다른 곳을 본다.
    """
    import json as _json
    import re as _re

    slug = project.get("slug") or ""
    f = get_package_dir().parent / "_imggen" / "ep_map.json"
    try:
        emap = _json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        emap = {}
    for key, v in emap.items():
        if v.get("slug") == slug:
            m = _re.match(r"(EP\d+)", key)
            if m:
                return m.group(1)
    return slug.rsplit("_", 1)[-1].upper() if "_ep" in slug else ""


def _scene_dir(ep: str, n: int) -> Path:
    return get_package_dir().parent / "_imggen" / f"{ep.lower()}_anim" / f"s{n:03d}"


@app.get("/api/p/{project_ref}/health")
async def project_health(project_ref: str):
    """진행 상태 · 다음 할 일 · 평가 · 수상한 것."""
    from auto_agent.dashboard import health

    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    try:
        return health.collect(project)
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


@app.post("/api/p/{project_ref}/layers/plan")
async def plan_layers_api(project_ref: str, request: Request):
    """고른 씬을 훑어 **어떤 층으로 가를지 계획만** 세운다.

    가르기 전에 사람이 목록을 보고 고칠 수 있어야 한다. 한 번 가르면 몇 분과
    비용이 드는데, 무엇을 가를지 잘못 정했으면 그 시간이 통째로 버려진다.
    계획은 글이라 고치기 쉽다.
    """
    import subprocess as _sp
    import threading as _th

    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    ep = _ep_of(project)
    if not ep:
        return JSONResponse({"error": "편 번호를 알 수 없습니다"}, status_code=422)
    body = await request.json()
    scenes = [int(x) for x in (body.get("scenes") or [])]
    if not scenes:
        return JSONResponse({"error": "고른 씬이 없습니다"}, status_code=422)

    root = get_package_dir().parent
    force = bool(body.get("force"))
    for n in scenes:                     # 훑는 중임을 씬마다 표시한다
        d = _scene_dir(ep, n)
        d.mkdir(parents=True, exist_ok=True)
        if force:                        # 다시 훑기 — 옛 계획을 비운다
            (d / "layer_plan.json").unlink(missing_ok=True)
        (d / "_planning").write_text("", encoding="utf-8")

    def one(n: int) -> None:
        d = _scene_dir(ep, n)
        try:
            with (d / "plan.log").open("w", encoding="utf-8") as f:
                _sp.run([str(root / ".venv/bin/python"),
                         "scripts/plan_scene_layers.py", ep, str(n)],
                        cwd=root, stdout=f, stderr=_sp.STDOUT, stdin=_sp.DEVNULL)
        finally:
            (d / "_planning").unlink(missing_ok=True)

    def run() -> None:
        # 훑기는 그림을 읽고 답하는 일이라 서로 기다릴 이유가 없다. 나란히
        # 돌린다. 넷을 넘기면 모델 쪽에서 막히므로 그 선에서 멈춘다.
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=min(4, len(scenes))) as ex:
            list(ex.map(one, scenes))

    _th.Thread(target=run, name=f"plan-{ep}", daemon=True).start()
    return {"started": scenes}


@app.get("/api/p/{project_ref}/layers/plan/{scene_num}")
async def get_layer_plan(project_ref: str, scene_num: int):
    """씬의 층 계획 상태 — 훑는 중 / 준비됨 / 실패 / 없음."""
    import json as _json

    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    d = _scene_dir(_ep_of(project), scene_num)
    if (d / "_planning").exists():
        return {"status": "running"}
    if (d / "_splitting").exists():
        return {"status": "splitting"}
    err = d / "split_error.txt"
    if err.is_file() and not (d / "layers.json").is_file():
        return {"status": "split_failed", "message": err.read_text(encoding="utf-8")}
    f = d / "layer_plan.json"
    if f.is_file():
        try:
            plan = _json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return {"status": "failed", "message": "계획 파일을 읽지 못했습니다"}
        return {"status": "ready", "layers": plan.get("layers") or [],
                "note": plan.get("note", ""),
                "split": (d / "layers.json").is_file()}
    log = d / "plan.log"
    if log.is_file():
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]
        return {"status": "failed", "message": "\n".join(tail)}
    return {"status": "none"}


@app.post("/api/p/{project_ref}/layers/plan/{scene_num}")
async def save_layer_plan(project_ref: str, scene_num: int, request: Request):
    """사람이 고친 층 목록을 저장한다. 가를 때 이 목록을 그대로 쓴다."""
    import json as _json

    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    body = await request.json()
    rows = [r for r in (body.get("layers") or []) if (r.get("name") or "").strip()]
    if not rows:
        return JSONResponse({"error": "층이 비어 있습니다"}, status_code=422)
    d = _scene_dir(_ep_of(project), scene_num)
    d.mkdir(parents=True, exist_ok=True)
    (d / "layer_plan.json").write_text(
        _json.dumps({"layers": rows, "note": body.get("note", "")},
                    ensure_ascii=False, indent=1), encoding="utf-8")
    return {"saved": len(rows)}


@app.post("/api/p/{project_ref}/layers/split")
async def split_layers(project_ref: str, request: Request):
    """체크한 씬들을 레이어로 가른다.

    롱폼은 이미지 검수가 끝난 뒤에 가르는 것이 맞다 — 이미지를 다시 뽑으면
    가른 것이 통째로 버려진다. 그래서 씬을 골라 한꺼번에 돌리는 형태다.

    한 씬에 몇 분이 걸리고 fal 비용이 드는 일이라 순차로 돌린다.
    """
    import subprocess as _sp
    import threading as _th

    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    body = await request.json()
    scenes = [int(x) for x in (body.get("scenes") or [])]
    if not scenes:
        return JSONResponse({"error": "고른 씬이 없습니다"}, status_code=422)

    slug = project.get("slug") or ""
    ep = _ep_of(project)
    if not ep:
        return JSONResponse({"error": f"편 번호를 알 수 없습니다: {slug}"}, status_code=422)

    root = get_package_dir().parent
    log = root / "_imggen" / f"{ep}_split.log"

    def run() -> None:
        with log.open("w", encoding="utf-8") as f:
            for n in scenes:
                d = _scene_dir(ep, n)
                d.mkdir(parents=True, exist_ok=True)
                (d / "_splitting").write_text("", encoding="utf-8")   # 씬마다 진행 표시
                f.write(f"=== 씬 {n} 시작\n"); f.flush()
                try:
                    r = _sp.run([str(root / ".venv/bin/python"), "scripts/animate_scene.py",
                                 ep, str(n)],
                                cwd=root, stdout=f, stderr=_sp.STDOUT, stdin=_sp.DEVNULL)
                    # 실패를 씬에 남긴다 — 로그 파일을 열어 봐야만 알 수 있으면
                    # 화면에서는 「그냥 아무 일도 없는 것」과 구별되지 않는다.
                    if r.returncode != 0:
                        (d / "split_error.txt").write_text(
                            f"분리에 실패했습니다 (코드 {r.returncode})\n"
                            f"자세한 내용: _imggen/{ep}_split.log", encoding="utf-8")
                    else:
                        (d / "split_error.txt").unlink(missing_ok=True)
                finally:
                    (d / "_splitting").unlink(missing_ok=True)
                f.write(f"=== 씬 {n} 끝\n"); f.flush()

    _th.Thread(target=run, name=f"split-{ep}", daemon=True).start()
    return {"started": scenes, "log": f"/api/p/{project_ref}/layers/split/log"}


@app.get("/api/p/{project_ref}/layers/split/log")
async def split_log(project_ref: str):
    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    ep = _ep_of(project)
    f = get_package_dir().parent / "_imggen" / f"{ep}_split.log"
    if not f.exists():
        return {"lines": [], "running": False}
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    started = sum(1 for x in lines if x.startswith("=== 씬") and x.endswith("시작"))
    done = sum(1 for x in lines if x.startswith("=== 씬") and x.endswith("끝"))
    return {"lines": lines[-40:], "running": started > done, "done": done, "started": started}


@app.get("/api/p/{project_ref}/layers/{scene_num}")
async def scene_layers(project_ref: str, scene_num: int):
    """이 씬에 분리된 레이어가 있으면 목록을 낸다.

    분리 결과를 눈으로 확인할 길이 없었다 — 파일을 직접 찾아 열어야 했고,
    어느 것이 어디에 놓이는지는 layers.json을 읽어야 알 수 있었다.
    """
    import json as _json

    pm = get_pm()
    project, _ = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    ep = _ep_of(project)
    sets = []
    for d in sorted(_LAYER_ROOT.glob(f"{ep.lower()}_anim/s{scene_num:03d}*")):
        meta_f = d / "layers.json"
        if not meta_f.is_file():
            continue
        try:
            meta = _json.loads(meta_f.read_text(encoding="utf-8"))
        except Exception:
            continue
        zf = d / "z_order.json"
        layers = []
        for m in meta:
            png = Path(m.get("path", "")).name
            svg = Path(m.get("svg") or "").name
            layers.append({
                "name": m.get("name"), "role": m.get("role"), "z": m.get("z"),
                "bbox": m.get("bbox"),
                "png": f"/layers/{d.parent.name}/{d.name}/{png}" if png else "",
                "svg": f"/layers/{d.parent.name}/{d.name}/{svg}" if svg else "",
            })
        videos = [f"/layers/{d.parent.name}/{d.name}/{v.name}" for v in sorted(d.glob("*.mp4"))]
        sets.append({
            "id": d.name, "dir": f"{d.parent.name}/{d.name}",
            "layers": layers, "videos": videos,
            "vision_ordered": zf.is_file(),
        })
    return {"sets": sets}


# chartagent 정적 대시보드 서빙 (/chartagent-dash/ → workspace/chartagent_dashboard/)
_chartagent_dash_dir = workspace / "chartagent_dashboard"
_chartagent_dash_dir.mkdir(parents=True, exist_ok=True)
app.mount("/chartagent-dash", StaticFiles(directory=str(_chartagent_dash_dir), html=True), name="chartagent-dash")

templates = Jinja2Templates(directory=str(DASHBOARD_DIR / "templates"))
# Jinja2 필터 등록
templates.env.filters["format_headline"] = format_headline
# v4 dashboard markdown filter
import markdown as _md
templates.env.filters["markdown"] = lambda text: _md.markdown(
    text or "",
    extensions=["fenced_code", "tables", "nl2br"],
)


def _static_version(rel_path: str) -> str:
    """정적 파일의 mtime을 캐시버스터로 반환 (random 대신 — 캐시 효율화).

    rel_path는 dashboard/static/ 기준 상대 경로 (예: 'scene-editor.js').
    """
    try:
        f = DASHBOARD_DIR / "static" / rel_path.lstrip("/")
        return str(int(f.stat().st_mtime))
    except Exception:
        return "0"


templates.env.globals["static_version"] = _static_version


USE_SUPABASE = False  # 로컬 DB 기반으로 전환


def _safe_background_file(file_path: str) -> Path | None:
    """배경 폴더 내부 파일만 허용 — 경로 탈출(../) 차단."""
    bg_root = (workspace / "remotion" / "public" / "background").resolve()
    try:
        bg_file = (bg_root / file_path).resolve()
    except (OSError, ValueError):
        return None
    if not bg_file.is_relative_to(bg_root):
        return None
    return bg_file if bg_file.is_file() else None


@app.get("/p/background/{file_path:path}")
async def proxy_background_no_slug(file_path: str):
    """Remotion 번들이 /p/background/... 로 요청하는 배경 이미지 서빙."""
    from fastapi.responses import FileResponse
    bg_file = _safe_background_file(file_path)
    if bg_file:
        return FileResponse(str(bg_file))
    return JSONResponse({"error": "not found"}, status_code=404)


@app.get("/p/{slug}/background/{file_path:path}")
async def proxy_background_under_project(slug: str, file_path: str):
    """Remotion 번들이 /p/{slug}/background/... 로 요청하는 배경 이미지 서빙."""
    from fastapi.responses import FileResponse
    bg_file = _safe_background_file(file_path)
    if bg_file:
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
        for key in ("imagePath", "vizBackgroundPath", "audioPath", "videoPath", "videoThumbPath"):
            val = scene.get(key, "")
            if val and val.startswith("project/"):
                scene[key] = prefix + val[len("project/"):]
        # images[] 배열도 rewrite (person_card 등)
        if scene.get("images"):
            scene["images"] = [
                prefix + v[len("project/"):] if v and v.startswith("project/") else v
                for v in scene["images"]
            ]
    return JSONResponse(content=data)


def get_pm():
    """로컬 ProjectManager 반환."""
    from auto_agent.db.project_manager import ProjectManager
    from auto_agent.db.connection import db_exists, init_db
    if not db_exists():
        init_db()
    return ProjectManager()


def _find_wiki_dir(wiki_root: Path):
    """research/wiki/ 아래 첫 번째 서브디렉토리 반환 (slug와 무관)."""
    if not wiki_root.exists():
        return None
    for d in sorted(wiki_root.iterdir()):
        if d.is_dir():
            return d
    return None


def _scan_and_register_output_projects() -> int:
    """output/ 폴더를 스캔해 DB에 없는 프로젝트를 자동 등록. 등록 수 반환."""
    import re
    pm = get_pm()
    output_root = get_workspace_dir() / "output"
    if not output_root.exists():
        return 0

    all_projects = pm.list_projects()

    # 역방향 체크: output_dir 폴더가 없으면 DB에서 제거
    # 단, output_root 자체가 현재 스캔 가능한 경우에만 삭제 (NAS 미연결 시 오삭제 방지)
    for p in all_projects:
        out = p.get("output_dir", "")
        if not out:
            continue
        out_path = Path(out)
        # output_root 하위 경로인 경우만 삭제 대상 (외부 마운트 경로는 건드리지 않음)
        try:
            out_path.relative_to(output_root)
        except ValueError:
            continue
        if not out_path.exists():
            pm.delete_project(p["id"])
            print(f"  [SCAN] 폴더 없음 → DB 삭제: {out_path.name}")

    # uuid → DB 프로젝트 맵 (삭제 후 재조회)
    current_projects = pm.list_projects()
    uuid_to_project = {p["uuid"]: p for p in current_projects if p.get("uuid")}

    registered = 0
    updated = 0
    # {8자_uuid}_{slug} 패턴 디렉토리만 처리
    pattern = re.compile(r'^([0-9a-f]{8})_(.+)$')

    for d in sorted(output_root.iterdir()):
        if not d.is_dir():
            continue
        m = pattern.match(d.name)
        if not m:
            continue

        uuid_prefix, slug = m.group(1), m.group(2)

        # 이미 같은 uuid가 DB에 있는 경우 — 경로만 갱신 (다른 머신 import 대응)
        if uuid_prefix in uuid_to_project:
            existing_path = uuid_to_project[uuid_prefix].get("output_dir", "")
            if existing_path != str(d):
                pm.update_project_path(uuid_prefix, str(d))
                updated += 1
                print(f"  [SCAN] 경로 갱신: {d.name} ({existing_path} → {d})")
            continue

        # 빈 디렉토리(orphan)는 등록하지 않음
        if not any(d.iterdir()):
            print(f"  [SCAN] 빈 디렉토리 스킵: {d.name}")
            continue

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
            print(f"  [SCAN] 등록 실패 ({d.name}): {e}")

    if updated:
        print(f"  [SCAN] 경로 갱신: {updated}개")
    return registered


@app.on_event("startup")
async def startup_scan():
    """output/ 스캔 → 누락 프로젝트 자동 등록. **백그라운드로 돌린다.**

    output/이 NAS라 os.listdir이 오래 걸린다. 앞단에서 기다리면 서버가 뜨지
    않는다 — 데스크톱 앱으로 띄웠을 때 실제로 「Waiting for application startup」
    에서 멈췄다(Finder로 띄운 프로세스는 네트워크 볼륨 접근이 더 느리다).
    스캔은 화면을 그리는 데 필수가 아니므로 뒤로 미룬다."""
    import threading

    def run() -> None:
        try:
            count = _scan_and_register_output_projects()
            if count:
                print(f"[startup] output 스캔 완료: {count}개 프로젝트 등록", flush=True)
        except Exception as e:
            print(f"[startup] output 스캔 실패 (무시): {e}", flush=True)

    threading.Thread(target=run, name="output-scan", daemon=True).start()


TAB_TEMPLATES = {
    "overview": "partials/_overview.html",
    "pipeline": "partials/_pipeline.html",
    "research": "partials/_research.html",
    "brief": "partials/_brief.html",
    "manuscript": "partials/_manuscript.html",
    "storyboard": "partials/_storyboard.html",
    "studio": "partials/_studio.html",
    "costs": "partials/_costs.html",
    "agent": "partials/_agent.html",
    "upload_info": "partials/_upload_info.html",
    "thumbnail_canvas": "partials/_thumbnail_canvas.html",
    "multiformat": "partials/_multiformat.html",
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

    elif tab == "brief":
        # 최신 버전 우선: editorial_brief.v3.json > v2 > v1 > editorial_brief.json
        brief = None
        brief_version = None
        for ver in ("editorial_brief.v3.json", "editorial_brief.v2.json",
                    "editorial_brief.v1.json", "editorial_brief.json"):
            data = _load_json(ver)
            if data:
                brief = data
                brief_version = ver
                break
        context["brief"] = brief
        context["brief_version"] = brief_version
        # 리뷰 피드백 (최신 버전)
        review_data = None
        for ver in ("brief_review_feedback.v3.json", "brief_review_feedback.v2.json",
                    "brief_review_feedback.v1.json"):
            data = _load_json(ver)
            if data:
                review_data = data
                break
        context["brief_review"] = review_data
        # 에피소드 brief (시리즈)
        context["episode_brief"] = _load_json("episode_brief.json")
        # v4 PD 워크플로 plan.md fallback — editorial_brief.json이 없을 때 표시
        if not brief:
            from auto_agent.dashboard.v4_artifacts import load_research_v4
            v4r = load_research_v4(Path(out_dir))
            if v4r["plan_md"]:
                context["v4_plan_md"] = v4r["plan_md"]

    elif tab == "research":
        context["research"] = _load_json("research_report.json")
        # JSON 없으면 .md fallback
        if not context["research"]:
            md_text = _load_text("research_report.md")
            if md_text:
                context["research_md"] = md_text
        # v4 PD 워크플로 컨텍스트 — 조건부
        from auto_agent.dashboard.v4_artifacts import load_research_v4
        context["v4_research"] = load_research_v4(Path(out_dir))

    elif tab == "manuscript":
        specs = _load_json("scene_specs.json")
        scenes = specs.get("scenes", []) if specs else []
        context["scenes"] = scenes
        context["final_manuscript"] = _load_text("final_manuscript.md") or ""
        chapters_seen: list[dict] = []
        seen_ids: set = set()
        for s in scenes:
            ch = s.get("chapter")
            ch_title = s.get("chapter_title") or s.get("chapterTitle") or ""
            if ch is not None and ch not in seen_ids:
                seen_ids.add(ch)
                chapters_seen.append({"id": ch, "title": ch_title})
        context["chapters"] = chapters_seen
        # v4 PD 워크플로 컨텍스트 — 조건부
        from auto_agent.dashboard.v4_artifacts import load_manuscript_v4
        context["v4_manuscript"] = load_manuscript_v4(Path(out_dir))

    elif tab == "storyboard":
        specs = _load_json("scene_specs.json")
        scenes = specs.get("scenes", []) if specs else []
        tts = _load_json("tts_results.json")
        _meta = specs.get("meta", {}) if specs else {}
        _dp_accent = (_meta.get("designPreset") or {}).get("colors", {}).get("accent")
        _proj_accent = _dp_accent or _meta.get("accentColor")
        _art_style_raw = _meta.get("artStyle", "")
        # "artstyle/styles/semoji_3D.json" → "semoji_3D"
        _art_style = Path(_art_style_raw).stem if _art_style_raw else ""
        scenes = enrich_scenes_with_media(scenes, dir_name, out_dir, tts,
                                          project_accent=_proj_accent, art_style=_art_style)
        # visual_kind 주입 — Jinja 템플릿이 단일 진입점으로 분기 가능
        try:
            from auto_agent.modules.scene_helpers import get_visual_kind
            for sc in scenes:
                sc["visual_kind"] = get_visual_kind(sc)
        except Exception:
            pass
        context["scenes"] = scenes
        ch_set = sorted(set(s.get("chapter", 0) for s in scenes))
        context["chapters_list"] = ch_set

    elif tab == "studio":
        # Studio 탭 진입 시 해당 프로젝트 매니페스트 자동 설정
        _setup_studio_project(slug)

    elif tab == "upload_info":
        raw = _load_json("upload_info.json")
        context["upload_info"] = raw.get("data", raw) if raw else None

    elif tab == "thumbnail_canvas":
        # 이미지 소스 목록
        images_dir = Path(out_dir) / "images"
        source_images = []
        if images_dir.exists():
            for subdir in ("generated", "search", ""):
                sub = images_dir / subdir if subdir else images_dir
                if sub.exists():
                    for f in sorted(sub.iterdir()):
                        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"} and f.is_file():
                            rel = f.relative_to(images_dir)
                            source_images.append({
                                "filename": f.name,
                                "url": f"/output/{dir_name}/images/{rel.as_posix()}",
                            })
        context["source_images"] = source_images[:60]  # 최대 60개
        # 썸네일 스펙 (upload_info.json)
        raw_ui = _load_json("upload_info.json")
        ui_data = (raw_ui.get("data", raw_ui) if raw_ui else {}) or {}
        specs = ui_data.get("thumbnail_specs", [])
        context["thumbnail_specs"] = specs
        import json as _json
        context["thumbnail_specs_json"] = _json.dumps(specs, ensure_ascii=False)
        # 저장된 캔버스 상태 로드
        canvas_state_path = Path(out_dir) / "thumbnail_canvas_state.json"
        canvas_state = None
        if canvas_state_path.exists():
            try:
                canvas_state = _json.loads(canvas_state_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        context["canvas_state_json"] = _json.dumps(canvas_state, ensure_ascii=False) if canvas_state else "null"
        context["output_dir_name"] = dir_name
        # 프로젝트 아트스타일 폰트 로드
        artstyle = project.get("artstyle") or "quirky_cartoon"
        artstyle_path = get_data_dir() / "artstyle" / "styles" / f"{artstyle}.json"
        project_fonts = []
        if artstyle_path.exists():
            try:
                as_data = _json.loads(artstyle_path.read_text(encoding="utf-8"))
                raw_fonts = (as_data.get("design_tokens") or as_data).get("fonts", {})
                for role, fd in raw_fonts.items():
                    project_fonts.append({
                        "role": role,
                        "family": fd.get("family", ""),
                        "files": fd.get("files", []),
                    })
            except Exception:
                pass
        context["project_fonts_json"] = _json.dumps(project_fonts, ensure_ascii=False)

    elif tab == "multiformat":
        context["multiformat"] = _load_json("multiformat_report.json")
        # 실제 콘텐츠 파일 로드
        context["blog_content"] = _load_text("blog.md")
        context["card_news"] = _load_json("card_news.json")
        context["threads"] = _load_json("threads.json")
        context["shorts_manifest"] = _load_json("shorts_manifest.json")

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
    return templates.TemplateResponse(request, "vault_search.html", {})


@app.get("/styles", response_class=HTMLResponse)
async def styles_page(request: Request):
    """아트스타일 관리 페이지."""
    styles_dir = workspace / "auto_agent" / "data" / "artstyle" / "styles"
    fonts_dir = workspace / "remotion" / "public" / "fonts"
    styles = []
    for json_path in sorted(styles_dir.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        dt = data.get("design_tokens", {})
        fonts = dt.get("fonts", {})
        subtitle = dt.get("subtitle", {})
        colors = dt.get("colors", {})
        voice = data.get("voice", {})

        # 폰트 파일 존재 여부 확인 (role 순서 고정)
        role_order = ["body", "headline", "value", "mono", "subtitle"]
        font_files = []
        for role in role_order:
            fdef = fonts.get(role)
            if not fdef:
                continue
            for ff in fdef.get("files", []):
                fname = Path(ff["file"]).name
                exists = (fonts_dir / fname).exists()
                font_files.append({
                    "role": role,
                    "family": fdef.get("family", ""),
                    "file": fname,
                    "weight": ff.get("weight", "400"),
                    "exists": exists,
                })

        # 레퍼런스 이미지 URL — 최상위 reference_image 필드 사용
        ref_img = data.get("reference_image", "")
        ref_img_url = None
        if ref_img:
            img_path = workspace / "auto_agent" / "data" / ref_img
            if img_path.exists():
                ref_img_url = f"/artstyle/{Path(ref_img).name}"

        # 아트스타일 프롬프트 전문 구성 (이미지 생성 시 실제 사용하는 텍스트)
        scene_desc = data.get("scene_style_description", "")
        style_obj = data.get("style", {})
        # style 섹션을 읽기 좋은 블록으로 조립
        style_lines = []
        if style_obj.get("art_style"):
            style_lines.append(style_obj["art_style"])
        for key in ["linework", "shapes", "color_palette", "shading", "character_design",
                    "mood_and_tone", "background"]:
            val = style_obj.get(key)
            if isinstance(val, dict):
                style_lines.append(f"{key}: " + " / ".join(f"{k}: {v}" for k, v in val.items()))
            elif isinstance(val, str) and val:
                style_lines.append(f"{key}: {val}")
        technical = data.get("technical", {})
        critical = technical.get("critical_requirements", [])

        styles.append({
            "id": data.get("id", json_path.stem),
            "name": data.get("name", json_path.stem),
            "description": data.get("description", ""),
            "channel": data.get("channel"),
            "base_theme": dt.get("baseTheme", "dark"),
            "accent": colors.get("accent", "#888"),
            "accent_rgb": colors.get("accentRgb", "136,136,136"),
            "colors": colors,
            "moods": dt.get("moods", {}),
            "layout": dt.get("layout", {}),
            "voice_id": voice.get("voice_id", ""),
            "voice_settings": voice.get("voice_settings", {}),
            "font_files": font_files,
            "subtitle": subtitle,
            "ref_img_url": ref_img_url,
            "scene_style_description": scene_desc,
            "style_detail_lines": style_lines,
            "critical_requirements": critical,
            "writing_style": data.get("writing_style", ""),
            "guidelines": data.get("guidelines", ""),
        })

    # 전체 스타일에서 고유 @font-face 목록 추출
    seen_font_files: set[str] = set()
    all_font_faces: list[dict] = []
    for s in styles:
        for ff in s["font_files"]:
            key = ff["file"]
            if key not in seen_font_files and ff["exists"]:
                seen_font_files.add(key)
                ext = Path(ff["file"]).suffix.lower()
                fmt = "opentype" if ext == ".otf" else "truetype" if ext == ".ttf" else "woff2" if ext == ".woff2" else "woff"
                all_font_faces.append({
                    "family": ff["family"],
                    "weight": ff["weight"],
                    "file": ff["file"],
                    "format": fmt,
                })

    return templates.TemplateResponse(request, "styles.html", {
        "styles": styles,
        "all_font_faces": all_font_faces,
    })


@app.get("/api/styles/voice-preview-url/{voice_id}")
async def voice_preview_url(voice_id: str):
    """ElevenLabs voice preview_url 조회 — 별도 TTS 생성 없이 제공된 샘플 오디오 URL 반환."""
    import httpx
    api_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not api_key:
        return JSONResponse({"error": "ELEVENLABS_API_KEY 미설정"}, status_code=500)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.elevenlabs.io/v1/voices/{voice_id}",
                headers={"xi-api-key": api_key},
            )
        if resp.status_code != 200:
            return JSONResponse({"error": f"ElevenLabs 오류 {resp.status_code}"}, status_code=502)
        data = resp.json()
        preview_url = data.get("preview_url", "")
        if not preview_url:
            return JSONResponse({"error": "preview_url 없음"}, status_code=404)
        return JSONResponse({"preview_url": preview_url})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, archived: bool = False):
    """프로젝트 목록 페이지.

    보관(archived)한 것은 기본으로 감춘다. 같은 회차의 옛 원고가 목록에
    남아 있으면 어느 쪽이 살아 있는 판인지 헷갈린다 — 실제로 LG편에서
    이미지가 없는 옛 6편을 열어 보고 「안 뜬다」고 판단한 일이 있었다.
    `?archived=1` 로 볼 수 있다.
    """
    pm = get_pm()
    all_projects = pm.list_projects()
    archived_count = sum(1 for p in all_projects if p.get("status") == "archived")
    projects = (all_projects if archived
                else [p for p in all_projects if p.get("status") != "archived"])
    for p in projects:
        p["asset_counts"] = pm.get_asset_counts(p["id"])
    return templates.TemplateResponse(request, "projects.html", {
        "projects": projects,
        "archived_count": archived_count,
        "showing_archived": archived,
    })


@app.get("/p/{project_ref}", response_class=HTMLResponse)
async def project_page(request: Request, project_ref: str, tab: str = "pipeline"):
    """프로젝트 상세 페이지. project_ref는 uuid(8자 hex) 또는 slug.

    slug로 진입 시 canonical uuid URL로 301 redirect.
    """
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""), project["uuid"]),
            status_code=307,
        )

    context = _load_tab_data(pm, project, tab)
    return templates.TemplateResponse(request, "project.html", context)


@app.get("/projects/{project_ref}", response_class=HTMLResponse)
async def project_detail(request: Request, project_ref: str, tab: str = "pipeline"):
    """uuid(8자 hex) 또는 숫자 ID 기반 → slug 리디렉트."""
    pm = get_pm()
    # 숫자면 레거시 DB id, 8자 hex면 uuid
    if project_ref.isdigit():
        project = pm.get_project(project_id=int(project_ref))
    else:
        project = pm.get_project(uuid=project_ref)
    if not project:
        return HTMLResponse("Project not found", status_code=404)
    return RedirectResponse(
        url=f"/p/{project['slug']}?tab={tab}",
        status_code=301,
    )


# ─────────────────────────────
# Manuscript 편집 API
# ─────────────────────────────

@app.get("/api/p/{project_ref}/research/canvas")
async def research_canvas(request: Request, project_ref: str):
    """리서치 캔버스용 데이터 반환.

    Returns:
        outline: 챕터 목록 (flow bar용)
        claims: outline 챕터별 그룹핑된 claims
        sources: 소스 목록
        skeleton: skeleton.json 요약
    """
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project.get("output_dir", ""))

    # outline 로드
    outline_data: dict = {}
    outline_path = out_dir / "outline.json"
    if outline_path.exists():
        try:
            outline_data = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # skeleton 로드
    skeleton_data: dict = {}
    skeleton_path = out_dir / "skeleton.json"
    if skeleton_path.exists():
        try:
            skeleton_data = json.loads(skeleton_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # claims.jsonl 로드 (research/ 폴더 탐색)
    research_root = out_dir / "research"
    claims: list[dict] = []
    sources: list[dict] = []

    def _load_jsonl(p: Path) -> list[dict]:
        if not p.exists():
            return []
        result = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                result.append(json.loads(line))
            except Exception:
                pass
        return result

    if research_root.exists():
        manifests_dir = research_root / "manifests"
        if manifests_dir.exists():
            for topic_dir in sorted(manifests_dir.iterdir()):
                if topic_dir.is_dir():
                    claims.extend(_load_jsonl(topic_dir / "claims.jsonl"))
                    sources.extend(_load_jsonl(topic_dir / "sources.jsonl"))

    # claims_ledger.jsonl도 읽음 (Phase 3 — script-director가 manuscript 작성 중 누적)
    ledger_path = research_root / "claims_ledger.jsonl"
    if ledger_path.exists():
        claims.extend(_load_jsonl(ledger_path))

    # manifests claims + ledger 모두 비어있으면 wiki claims.md 파싱으로 폴백
    if not claims:
        import re as _re2
        wiki_dir = _find_wiki_dir(research_root / "wiki")
        if wiki_dir:
            claims_md = wiki_dir / "claims.md"
            if claims_md.exists():
                text = _re2.sub(r'^---\s*\n.*?\n---\s*\n', '', claims_md.read_text(encoding="utf-8"), flags=_re2.DOTALL)
                current: dict = {}
                for line in text.split("\n"):
                    line = line.strip()
                    if line.startswith("## claim_"):
                        if current.get("claim"):
                            claims.append(current)
                        current = {}
                    elif line.startswith("- claim:"):
                        current["claim"] = line[len("- claim:"):].strip()
                    elif line.startswith("- kind:"):
                        current["kind"] = line[len("- kind:"):].strip().strip("`")
                    elif line.startswith("- confidence:"):
                        current["confidence"] = line[len("- confidence:"):].strip().strip("`")
                    elif line.startswith("- status:"):
                        current["status"] = line[len("- status:"):].strip().strip("`")
                    elif line.startswith("- evidence:"):
                        current["evidence"] = line[len("- evidence:"):].strip()
                if current.get("claim"):
                    claims.append(current)

    # outline 챕터 기준으로 claims 그룹핑
    chapters = outline_data.get("chapters", [])
    chapter_map: dict[int, str] = {}
    for ch in chapters:
        ch_id = ch.get("chapter_number") or ch.get("id") or ch.get("chapter") or 0
        ch_title = ch.get("title") or ch.get("name") or f"Chapter {ch_id}"
        chapter_map[int(ch_id)] = ch_title

    # claims를 챕터 키워드 기반 매핑 (chapter 필드 or 순서)
    # claims에 chapter 필드가 있으면 사용, 없으면 unassigned
    grouped: dict[str, list[dict]] = {}
    for c in claims:
        # ledger는 'used_in_chapter', 옛 형식은 'chapter'
        ch_key = str(c.get("chapter", "") or c.get("used_in_chapter", "") or "")
        if not ch_key:
            ch_key = "unassigned"
        if ch_key not in grouped:
            grouped[ch_key] = []
        grouped[ch_key].append({
            "claim_id": c.get("claim_id", ""),
            "claim": c.get("claim", ""),
            "kind": c.get("kind", "factual"),
            "confidence": c.get("confidence", "medium"),
            "evidence": c.get("evidence", ""),
            "status": c.get("status", ""),
            # Phase 3 ledger 필드 (UI에서 ✨ 승격 매칭에 사용)
            "source_id": c.get("source_id", ""),
            "source_ids": c.get("source_ids", []),
            "source_url": c.get("source_url", ""),
            "evidence_span": c.get("evidence_span", ""),
            "tier": c.get("tier", ""),
            "used_in_chapter": c.get("used_in_chapter"),
        })

    # unassigned claims는 순서대로 챕터에 배분 (챕터 없을 때 fallback)
    if "unassigned" in grouped and chapters:
        unassigned = grouped.pop("unassigned")
        chunk = max(1, len(unassigned) // max(1, len(chapters)))
        for i, ch in enumerate(chapters):
            ch_id = str(ch.get("chapter_number") or ch.get("id") or i + 1)
            start = i * chunk
            end = start + chunk if i < len(chapters) - 1 else len(unassigned)
            if ch_id not in grouped:
                grouped[ch_id] = []
            grouped[ch_id].extend(unassigned[start:end])

    # targeted_claims.json 로드
    targeted_claims: list[dict] = []
    tc_path = out_dir / "targeted_claims.json"
    if tc_path.exists():
        try:
            raw_tc = json.loads(tc_path.read_text(encoding="utf-8"))
            targeted_claims = raw_tc if isinstance(raw_tc, list) else raw_tc.get("claims", raw_tc.get("targeted_claims", []))
        except Exception:
            pass

    # research_questions.json 로드
    research_questions: list[dict] = []
    rq_path = out_dir / "research_questions.json"
    if rq_path.exists():
        try:
            raw_rq = json.loads(rq_path.read_text(encoding="utf-8"))
            research_questions = raw_rq if isinstance(raw_rq, list) else raw_rq.get("questions", raw_rq.get("research_questions", []))
        except Exception:
            pass

    return JSONResponse({
        "outline": outline_data,
        "skeleton": skeleton_data,
        "chapters": chapters,
        "grouped_claims": grouped,
        "chapter_map": chapter_map,
        "sources": sources[:50],
        "total_claims": len(claims),
        "total_sources": len(sources),
        "targeted_claims": targeted_claims,
        "research_questions": research_questions,
    })


@app.get("/api/p/{project_ref}/manuscript/raw")
async def manuscript_raw(request: Request, project_ref: str):
    """원고 raw 텍스트 반환."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    text = load_project_text(out_dir, "final_manuscript.md")
    return {"text": text or "", "chars": len(text) if text else 0}


@app.post("/api/p/{project_ref}/manuscript/save")
async def manuscript_save(request: Request, project_ref: str):
    """원고 저장."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    body = await request.json()
    text = body.get("text", "")
    if not text.strip():
        return JSONResponse({"error": "빈 원고는 저장할 수 없습니다."}, 400)
    pm.save_project_text(project["id"], "final_manuscript.md", text)
    return {"ok": True, "chars": len(text)}


@app.get("/api/p/{project_ref}/research/images")
async def research_images(request: Request, project_ref: str):
    """리서치 단계에서 수집된 이미지 목록 반환 (image_manifest.jsonl 기반)."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project.get("output_dir", ""))
    research_root = out_dir / "research"

    images: list[dict] = []
    seen: set[str] = set()

    def _load_jsonl(p: Path) -> list[dict]:
        if not p.exists():
            return []
        result = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    result.append(json.loads(line))
                except Exception:
                    pass
        return result

    # 1. run 폴더의 image_manifest.jsonl (최신 run부터)
    raw_dir = research_root / "raw"
    if raw_dir.exists():
        for slug_dir in sorted(raw_dir.iterdir(), reverse=True):
            if not slug_dir.is_dir():
                continue
            for run_dir in sorted(slug_dir.iterdir(), reverse=True):
                if not run_dir.is_dir():
                    continue
                for rec in _load_jsonl(run_dir / "image_manifest.jsonl"):
                    url = rec.get("image_url", "")
                    if url and url not in seen:
                        seen.add(url)
                        images.append(rec)

    # 2. manifests/<slug>/images.jsonl 보완
    manifests_dir = research_root / "manifests"
    if manifests_dir.exists():
        for topic_dir in sorted(manifests_dir.iterdir()):
            if topic_dir.is_dir():
                for rec in _load_jsonl(topic_dir / "images.jsonl"):
                    url = rec.get("image_url", "")
                    if url and url not in seen:
                        seen.add(url)
                        images.append(rec)

    return JSONResponse({"images": images, "total": len(images)})


@app.get("/api/p/{project_ref}/research/wiki")
async def research_wiki_index(request: Request, project_ref: str):
    """위키 페이지 목록 반환."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project.get("output_dir", ""))
    wiki_root = out_dir / "research" / "wiki"
    wiki_dir = _find_wiki_dir(wiki_root)
    if not wiki_dir:
        return JSONResponse({"pages": []})
    pages = [p.stem for p in sorted(wiki_dir.glob("*.md"))]
    return JSONResponse({"pages": pages})


@app.get("/api/p/{project_ref}/research/wiki/{page}")
async def research_wiki_page(request: Request, project_ref: str, page: str):
    """위키 마크다운 파일 내용 반환. claims 페이지는 파싱해서 구조화된 데이터로 반환."""
    import re as _re
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "project not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = Path(project.get("output_dir", ""))
    wiki_root = out_dir / "research" / "wiki"
    wiki_dir = _find_wiki_dir(wiki_root)
    wiki_file = (wiki_dir / f"{page}.md") if wiki_dir else None
    if not wiki_file or not wiki_file.exists():
        return JSONResponse({"error": "not found"}, 404)
    text = wiki_file.read_text(encoding="utf-8")
    # frontmatter 제거
    text = _re.sub(r'^---\s*\n.*?\n---\s*\n', '', text, flags=_re.DOTALL)
    text = text.strip()

    # claims 페이지는 파싱해서 카드용 구조화 데이터로 반환
    if page == "claims":
        claims = []
        current = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("## claim_"):
                if current.get("claim"):
                    claims.append(current)
                current = {}
            elif line.startswith("- claim:"):
                current["claim"] = line[len("- claim:"):].strip()
            elif line.startswith("- kind:"):
                current["kind"] = line[len("- kind:"):].strip().strip("`")
            elif line.startswith("- confidence:"):
                current["confidence"] = line[len("- confidence:"):].strip().strip("`")
            elif line.startswith("- status:"):
                current["status"] = line[len("- status:"):].strip().strip("`")
            elif line.startswith("- evidence:"):
                current["evidence"] = line[len("- evidence:"):].strip()
        if current.get("claim"):
            claims.append(current)
        return JSONResponse({"page": page, "claims": claims})

    return JSONResponse({"content": text, "page": page})


# ─────────────────────────────
# HTMX Partials — 탭 콘텐츠
# ─────────────────────────────

@app.get("/api/p/{project_ref}/tab/{tab}", response_class=HTMLResponse)
async def project_tab_by_slug(request: Request, project_ref: str, tab: str):
    """slug 기반 탭 콘텐츠 (HTMX partial)."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project or tab not in TAB_TEMPLATES:
        return HTMLResponse("Not found", status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    context = _load_tab_data(pm, project, tab)
    return templates.TemplateResponse(request, TAB_TEMPLATES[tab], context)


@app.get("/api/projects/{project_id}/tab/{tab}", response_class=HTMLResponse)
async def project_tab_content(request: Request, project_id: int, tab: str):
    """레거시 탭 콘텐츠 (HTMX partial)."""
    pm = get_pm()
    project = pm.get_project(project_id=project_id)
    if not project or tab not in TAB_TEMPLATES:
        return HTMLResponse("Not found", status_code=404)

    context = _load_tab_data(pm, project, tab)
    return templates.TemplateResponse(request, TAB_TEMPLATES[tab], context)


# ─────────────────────────────
# HTMX Partials — 씬 상세
# ─────────────────────────────

@app.get("/api/p/{project_ref}/storyboard/scene/{scene_num}", response_class=HTMLResponse)
async def storyboard_scene_detail_by_slug(request: Request, project_ref: str, scene_num: int):
    """slug 기반 씬 상세 패널 (HTMX partial)."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return HTMLResponse("Not found", status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
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

    return templates.TemplateResponse(request, "partials/_storyboard_scene.html", {
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


@app.get("/api/p/{project_ref}/summary")
async def api_project_summary_by_slug(request: Request, project_ref: str):
    """slug 기반 프로젝트 요약 (Supabase 모드 대응)."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    pid = project["id"]
    project["asset_counts"] = pm.get_asset_counts(pid)
    project["cost"] = pm.get_cost_summary(pid)
    project["cost_by_agent"] = pm.get_cost_by_agent(pid)
    return project


@app.get("/api/p/{project_ref}/scenes")
async def api_scenes_by_slug(request: Request, project_ref: str):
    """씬 목록 JSON (이미지/오디오 URL 포함)."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    specs = load_project_json(out_dir, "scene_specs.json")
    if not specs:
        return {"scenes": []}
    scenes = specs.get("scenes", [])
    tts = load_project_json(out_dir, "tts_results.json")
    dir_name = Path(out_dir).name if out_dir else project["slug"]
    print(f"[DEBUG] out_dir={out_dir}, dir_name={dir_name}, slug={project['slug']}", flush=True)
    _meta = specs.get("meta", {}) if specs else {}
    _dp_accent = (_meta.get("designPreset") or {}).get("colors", {}).get("accent")
    _proj_accent = _dp_accent or _meta.get("accentColor")
    _art_style_raw = _meta.get("artStyle", "")
    _art_style = Path(_art_style_raw).stem if _art_style_raw else ""
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


def _load_enrichment_candidates_for_scene(out_dir: str, scene_num: int) -> list:
    """enrichment_queue.json에서 특정 씬의 후보를 image-grid 호환 포맷으로 변환."""
    queue_path = Path(out_dir) / "enrichment_queue.json"
    if not queue_path.exists():
        return []
    try:
        import json as _json
        data = _json.loads(queue_path.read_text(encoding="utf-8"))
        scene_index = scene_num - 1
        for item in data.get("queue", []):
            if item.get("scene_index") != scene_index:
                continue
            if item.get("asset_kind") != "search_image":
                continue
            out = []
            for c in item.get("candidates", []):
                out.append({
                    "title": c.get("title", ""),
                    "image_url": c.get("image_url", ""),
                    "thumbnail_url": c.get("thumbnail_url") or c.get("image_url", ""),
                    "source": c.get("source", ""),
                    "source_domain": c.get("source_domain", ""),
                    "source_page": c.get("source_page", ""),
                    "width": c.get("width", 0),
                    "height": c.get("height", 0),
                    "license": c.get("license", ""),
                    "from_enrichment": True,  # UI 마커 — 검토 대기 후보
                })
            return out
    except Exception:
        pass
    return []


@app.get("/api/p/{project_ref}/images/candidates/{scene_num}")
async def image_candidates(request: Request, project_ref: str, scene_num: int, q: str = "", source: str = "wikimedia"):
    """씬의 이미지 검색 후보 반환. q=커스텀 쿼리, source=wikimedia|serper.

    응답에 enrichment_queue 항목도 병합 — 자료 검토 패널과 이미지 리스트 통합.
    """
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")

    # enrichment 후보 (있으면 우선 표시)
    enrichment_cands = _load_enrichment_candidates_for_scene(out_dir, scene_num)

    # 커스텀 쿼리가 없으면 저장된 후보 확인
    if not q:
        candidates_path = Path(out_dir) / "images" / "image_candidates.json"
        if candidates_path.exists():
            try:
                import json as _json
                data = _json.loads(candidates_path.read_text(encoding="utf-8"))
                for s in data.get("scenes", []):
                    if s.get("sceneNumber") == scene_num:
                        merged = enrichment_cands + s.get("candidates", [])
                        return JSONResponse({"query": s.get("query", ""), "candidates": merged, "cached": True, "source": "cached"})
            except Exception:
                pass
        # cache miss but enrichment 있으면 그것만 반환
        if enrichment_cands:
            return JSONResponse({"query": "", "candidates": enrichment_cands, "cached": True, "source": "enrichment"})

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


@app.post("/api/p/{project_ref}/images/select/{scene_num}")
async def select_image(request: Request, project_ref: str, scene_num: int):
    """이미지 선택 — URL 다운로드 또는 기존 버전 선택."""
    from auto_agent.tools.image_assets import add_version, select_version, next_filename
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
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


@app.get("/api/p/{project_ref}/images/versions/{scene_num}")
async def image_versions(request: Request, project_ref: str, scene_num: int):
    """씬의 모든 이미지 버전."""
    from auto_agent.tools.image_assets import get_scene_versions
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else project["slug"]
    img_dir = Path(out_dir) / "images"
    try:
        scene_data = get_scene_versions(img_dir, scene_num)
        # URL 추가 — 파일이 실제로 존재하는 것만 포함
        existing_versions = []
        for v in scene_data.get("versions", []):
            if v.get("file"):
                file_path = img_dir / v["file"]
                if file_path.exists():
                    v["url"] = f"/output/{dir_name}/images/{v['file']}"
                    existing_versions.append(v)
                else:
                    # 파일 없음 → gen_* 패턴으로 대체 탐색
                    import glob as _glob
                    scene_key = f"scene_{scene_num:03d}"
                    for subdir in ("generated", "search", ""):
                        base = img_dir / subdir if subdir else img_dir
                        matches = sorted(base.glob(f"{scene_key}_*.png")) + sorted(base.glob(f"{scene_key}_*.jpg"))
                        if matches:
                            rel = (Path(subdir) / matches[0].name).as_posix() if subdir else matches[0].name
                            v["file"] = rel
                            v["url"] = f"/output/{dir_name}/images/{rel}"
                            existing_versions.append(v)
                            break
        scene_data["versions"] = existing_versions
        # imageAsset.source = "none" 여부 확인
        specs = load_project_json(out_dir, "scene_specs.json")
        is_none = False
        if specs:
            for s in specs.get("scenes", []):
                if s.get("sceneNumber") == scene_num:
                    ia = s.get("imageAsset") or {}
                    is_none = ia.get("source") == "none"
                    break
        scene_data["is_none"] = is_none
        return JSONResponse(scene_data)
    except Exception:
        return JSONResponse({"sceneNumber": scene_num, "selected": None, "versions": [], "is_none": False})


@app.post("/api/p/{project_ref}/tts/regenerate/{scene_num}")
async def regenerate_tts(request: Request, project_ref: str, scene_num: int):
    """씬별 TTS 재생성."""
    import json as _json
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
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

    # TTS 생성 — audio_assets 기반 (sceneId 우선)
    from auto_agent.tools.audio_assets import add_version, next_filename
    # 해당 씬의 sceneId 조회 (canonical 파일명 일관성용)
    scene_id_for_audio: str = ""
    specs_for_sid = load_project_json(out_dir, "scene_specs.json")
    if specs_for_sid:
        for s in specs_for_sid.get("scenes", []):
            if s.get("sceneNumber") == scene_num:
                scene_id_for_audio = s.get("sceneId") or ""
                break
    audio_dir = Path(out_dir) / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    fname = next_filename(audio_dir, scene_num, scene_id=scene_id_for_audio)
    output_path = audio_dir / fname

    try:
        import requests as _requests
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            return JSONResponse({"error": "ELEVENLABS_API_KEY 미설정"}, 500)

        # 대시보드 재생성: 사용자가 입력한 텍스트 그대로 전송 (전처리 안 함)
        # 처음 표시되는 텍스트가 이미 전처리된 narration_tts이므로, 사용자 수정본을 존중

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
            # audio_assets에 버전 등록 + canonical 파일(<sceneId>.mp3 또는 scene_NNN.mp3) 갱신
            add_version(audio_dir, scene_num, fname, "regen",
                        voice_id=voice_id, text=text[:100],
                        scene_id=scene_id_for_audio)
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
                    [sys.executable, "-m", "auto_agent.scripts.generate_subtitles", out_dir, "--scene", str(scene_num)],
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


async def _bg_split_postprocess(slug: str, project: dict, scene_a: int, scene_b: int):
    """분할 후 백그라운드 처리: 양쪽 씬 TTS 재생성 + 씬 재분석."""
    import asyncio as _asyncio
    out_dir = project.get("output_dir", "")

    async def _process_one(scene_num: int):
        specs_path = Path(out_dir) / "scene_specs.json"
        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        scene = next((s for s in specs.get("scenes", []) if s["sceneNumber"] == scene_num), None)
        if not scene:
            return

        narration = scene.get("narration", "")
        scene_id = scene.get("sceneId", "")

        # 기존 SRT 삭제 — 새 나레이션에 맞게 재생성 강제
        sub_dir = Path(out_dir) / "subtitles"
        for _srt_name in ([f"{scene_id}.srt"] if scene_id else []) + [f"scene_{scene_num:03d}.srt"]:
            _srt_p = sub_dir / _srt_name
            if _srt_p.exists():
                _srt_p.unlink()

        # 1. TTS 재생성
        try:
            config = project.get("config", {})
            if isinstance(config, str):
                config = json.loads(config)
            STYLE_VOICE = {
                "semoji": "W7FnAxJNpD5WGjrF5GLp",
                "iromism": "9Sj8ugvpK1DmcAXyvi3a",
                "default": "4JJwo477JUAx3HV0T7n7",
            }
            voice_id = config.get("voice_id") or STYLE_VOICE.get(config.get("writing_style", "default"), STYLE_VOICE["default"])

            import requests as _requests
            from auto_agent.tools.audio_assets import add_version as audio_add, next_filename as audio_next
            audio_dir = Path(out_dir) / "audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            fname = audio_next(audio_dir, scene_num, scene_id=scene_id)
            output_path = audio_dir / fname

            voice_settings = {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "use_speaker_boost": True}
            resp = _requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={"xi-api-key": os.environ.get("ELEVENLABS_API_KEY", ""), "Content-Type": "application/json"},
                json={"text": narration, "model_id": "eleven_multilingual_v2", "voice_settings": voice_settings},
                timeout=60,
            )
            if resp.status_code == 200:
                output_path.write_bytes(resp.content)
                audio_add(audio_dir, scene_num, fname, "split_tts",
                          scene_id=scene_id, voice_id=voice_id, text=narration[:100])
            # 자막 동기화 (PROJECT_DIR 환경변수로 경로 전달)
            _sub_env = os.environ.copy()
            _sub_env["PROJECT_DIR"] = str(out_dir)
            _sub_script = Path(__file__).parent / "auto_agent" / "scripts" / "generate_subtitles.py"
            subprocess.run(
                [sys.executable, str(_sub_script), "--scene", str(scene_num)],
                cwd=str(get_workspace_dir()), env=_sub_env, capture_output=True, timeout=120,
            )
        except Exception as e:
            print(f"[WARN] 분할 TTS 실패 씬{scene_num}: {e}")

        # 2. 씬 재분석 (script-director)
        try:
            scene_ctx = json.dumps(scene, ensure_ascii=False, indent=2)
            prompt = f"""아래 씬의 연출을 다시 검토하고 개선하세요.
씬 번호, 나레이션, 챕터는 변경하지 마세요.
layout, mood, imageAsset, motion, title, concept, headline/items 등 연출 요소 전체를 개선합니다.

현재 씬:
{scene_ctx}

반드시 씬 전체를 JSON으로만 응답하세요 (설명 없이 JSON만).
"""
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            result = subprocess.run(
                ["claude", "--model", "claude-sonnet-4-6", "--max-turns", "3",
                 "--output-format", "text"],
                input=prompt, capture_output=True, text=True, env=env,
                cwd=str(get_workspace_dir()), timeout=180,
            )
            raw = (result.stdout or "").strip()
            if "```" in raw:
                lines = raw.split("\n")
                start = 1 if lines[0].strip().startswith("```") else 0
                end = -1 if lines[-1].strip() == "```" else len(lines)
                raw = "\n".join(lines[start:end]).strip()
            updated = json.loads(raw)
            # scene_specs 업데이트
            specs2 = json.loads(specs_path.read_text(encoding="utf-8"))
            for i, s in enumerate(specs2.get("scenes", [])):
                if s["sceneNumber"] == scene_num:
                    updated["sceneId"] = s.get("sceneId", updated.get("sceneId"))
                    updated["sceneNumber"] = scene_num
                    updated["narration"] = s["narration"]
                    specs2["scenes"][i] = updated
                    break
            specs_path.write_text(json.dumps(specs2, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] 분할 씬재분석 실패 씬{scene_num}: {e}")

    # 양쪽 씬 병렬 처리
    await _asyncio.gather(_process_one(scene_a), _process_one(scene_b))

    # 매니페스트 재빌드
    try:
        from auto_agent.scripts.build_manifest import build_manifest
        dir_name = Path(out_dir).name
        build_manifest(str(project.get("id", "")), dir_name, out_dir)
    except Exception as e:
        print(f"[WARN] 분할 백그라운드 매니페스트 리빌드 실패: {e}")

    print(f"[SPLIT] 백그라운드 처리 완료: 씬{scene_a}, 씬{scene_b}")


@app.get("/api/p/{project_ref}/tts/versions/{scene_num}")
async def tts_versions(request: Request, project_ref: str, scene_num: int):
    """씬의 TTS 버전 목록."""
    from auto_agent.tools.audio_assets import get_scene_versions
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else project["slug"]
    audio_dir = Path(out_dir) / "audio"
    scene_data = get_scene_versions(audio_dir, scene_num)
    for v in scene_data.get("versions", []):
        v["url"] = f"/output/{dir_name}/audio/{v['file']}"
    return JSONResponse(scene_data)


@app.post("/api/p/{project_ref}/tts/select/{scene_num}")
async def select_tts(request: Request, project_ref: str, scene_num: int):
    """TTS 버전 선택."""
    from auto_agent.tools.audio_assets import select_version
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
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


@app.get("/api/p/{project_ref}/tts/text/{scene_num}")
async def get_tts_text(request: Request, project_ref: str, scene_num: int):
    """씬의 TTS 텍스트 반환."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    specs = load_project_json(out_dir, "scene_specs.json")
    if not specs:
        return JSONResponse({"error": "no specs"}, 404)
    for s in specs.get("scenes", []):
        if s.get("sceneNumber") == scene_num:
            narration = s.get("narration", "")
            narration_tts = s.get("narration_tts", "")
            if not narration_tts:
                # narration_tts 없으면 TTSPreprocessor 적용해서 반환
                try:
                    from auto_agent.tools.elevenlabs import TTSPreprocessor
                    narration_tts = TTSPreprocessor().preprocess(narration, language="ko")
                except Exception:
                    narration_tts = narration
            return JSONResponse({
                "text": narration_tts,
                "narration": narration,
            })
    return JSONResponse({"error": "scene not found"}, 404)


def _scene_id_for_num(out_dir: str, scene_num: int) -> str:
    """scene_specs.json에서 scene_num 에 해당하는 sceneId 조회 (없으면 빈 문자열)."""
    import json as _json
    try:
        specs_path = Path(out_dir) / "scene_specs.json"
        if not specs_path.exists():
            return ""
        specs = _json.loads(specs_path.read_text(encoding="utf-8"))
        for s in specs.get("scenes", []):
            if s.get("sceneNumber") == scene_num:
                return s.get("sceneId") or ""
    except Exception:
        pass
    return ""


def _resolve_scene_file(out_dir: str, scene_num: int, subdir: str, suffix: str) -> Path:
    """sceneId 기반 파일명을 우선 시도하고, 없으면 scene_NNN 레거시 경로 반환.

    파일이 둘 다 없으면 sceneId 기반 경로를 우선해 반환 (쓰기/존재검사 양쪽에 사용)."""
    base = Path(out_dir) / subdir
    sid = _scene_id_for_num(out_dir, scene_num)
    if sid:
        cand = base / f"{sid}{suffix}"
        if cand.exists():
            return cand
    legacy = base / f"scene_{scene_num:03d}{suffix}"
    if legacy.exists():
        return legacy
    if sid:
        return base / f"{sid}{suffix}"
    return legacy


@app.get("/api/p/{project_ref}/subtitles/{scene_num}")
async def get_subtitles(request: Request, project_ref: str, scene_num: int):
    """씬의 SRT 엔트리 + timestamps.json 단어 데이터 반환."""
    import json as _json
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    srt_path = _resolve_scene_file(out_dir, scene_num, "subtitles", ".srt")
    ts_path = _resolve_scene_file(out_dir, scene_num, "audio", ".timestamps.json")

    entries = []
    if srt_path.exists():
        from auto_agent.scripts.generate_subtitles import parse_srt
        try:
            entries = parse_srt(srt_path.read_text(encoding="utf-8"))
        except Exception:
            entries = []

    words = []
    if ts_path.exists():
        try:
            sidecar = _json.loads(ts_path.read_text(encoding="utf-8"))
            from auto_agent.scripts.generate_subtitles import chars_to_words
            words = chars_to_words(sidecar)
        except Exception:
            words = []

    return JSONResponse({"entries": entries, "words": words})


def _normalize_subtitle_entries(entries):
    normalized = []
    for idx, entry in enumerate(entries or []):
        text = str(entry.get("text", "")).strip()
        if not text:
            continue
        try:
            start_sec = round(float(entry["startSec"]), 3)
            end_sec = round(float(entry["endSec"]), 3)
        except (KeyError, TypeError, ValueError):
            raise KeyError(f"invalid timing in entry {idx}")
        normalized.append({
            "text": text,
            "startSec": start_sec,
            "endSec": end_sec,
        })
    return normalized


def _snap_to_word_boundary(start_sec: float, out_dir: str, scene_num: int) -> float:
    """ElevenLabs 문자 타임스탬프에서 start_sec 이후 가장 가까운 단어 시작점으로 스냅.

    숫자/영문 혼합 텍스트는 TTS 발음이 표기와 달라 텍스트 검색이 실패하므로,
    단어 경계(공백 직후 문자) 중 start_sec에 가장 가까운 것을 선택한다.
    """
    import json as _json
    ts_path = _resolve_scene_file(out_dir, scene_num, "audio", ".timestamps.json")
    if not ts_path.exists():
        return start_sec
    try:
        ts = _json.loads(ts_path.read_text(encoding="utf-8"))
        chars = ts.get("characters", [])
        starts = ts.get("character_start_times_seconds", [])
        if not chars or len(chars) != len(starts):
            return start_sec
        # 단어 시작 = 공백 다음 문자 or 첫 문자
        word_starts = []
        for i, ch in enumerate(chars):
            if i == 0 or chars[i - 1] in (" ", " "):
                word_starts.append(starts[i])
        if not word_starts:
            return start_sec
        # start_sec 이후 가장 가까운 단어 시작 (±0.3s 이내만 스냅)
        best = min(word_starts, key=lambda t: abs(t - start_sec))
        if abs(best - start_sec) <= 0.3:
            return round(best, 3)
    except Exception:
        pass
    return start_sec


def _resolve_subtitle_audio_duration(out_dir: str, scene_num: int, fallback_end_sec: float = 0.0) -> float:
    audio_path = _resolve_scene_file(out_dir, scene_num, "audio", ".mp3")
    if audio_path.exists():
        try:
            from mutagen.mp3 import MP3
            return round(MP3(str(audio_path)).info.length, 3)
        except Exception:
            pass
    return round(float(fallback_end_sec or 0.0), 3)


@app.post("/api/p/{project_ref}/subtitles/{scene_num}")
async def save_subtitles(request: Request, project_ref: str, scene_num: int):
    """편집된 SRT 엔트리를 .srt 파일로 저장."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    body = await request.json()
    out_dir = project.get("output_dir", "")
    entries = _normalize_subtitle_entries(body.get("entries", []))
    if not entries:
        return JSONResponse({"error": "entries required"}, 400)

    # 단어 경계 스냅 — 숫자/영문 혼합 텍스트의 타이밍 오류 방지
    entries = [
        {**e, "startSec": _snap_to_word_boundary(e["startSec"], out_dir, scene_num)}
        for e in entries
    ]
    sid = _scene_id_for_num(out_dir, scene_num)
    srt_path = Path(out_dir) / "subtitles" / (f"{sid}.srt" if sid else f"scene_{scene_num:03d}.srt")
    srt_path.parent.mkdir(parents=True, exist_ok=True)

    from auto_agent.scripts.generate_subtitles import format_srt_time
    lines = []
    try:
        for i, e in enumerate(entries, 1):
            lines.append(str(i))
            lines.append(f"{format_srt_time(e['startSec'])} --> {format_srt_time(e['endSec'])}")
            lines.append(e["text"])
            lines.append("")
    except KeyError as exc:
        return JSONResponse({"error": f"missing field in entry: {exc}"}, 500)
    srt_path.write_text("\n".join(lines), encoding="utf-8")

    # subtitles.json 갱신
    try:
        import json as _json
        subtitles_json_path = Path(out_dir) / "subtitles.json"
        if subtitles_json_path.exists():
            subtitles_data = _json.loads(subtitles_json_path.read_text(encoding="utf-8"))
        else:
            subtitles_data = {"scenes": []}
        scenes_list = subtitles_data.get("scenes", [])
        new_entry = {
            "sceneNumber": scene_num,
            "audioDurationSec": _resolve_subtitle_audio_duration(out_dir, scene_num, entries[-1]["endSec"]),
            "entries": entries,
            "wordCount": sum(len(e["text"].split()) for e in entries),
            "source": "manual_edit",
        }
        updated = False
        for i, s in enumerate(scenes_list):
            if s.get("sceneNumber") == scene_num:
                scenes_list[i] = new_entry
                updated = True
                break
        if not updated:
            scenes_list.append(new_entry)
        subtitles_data["scenes"] = sorted(scenes_list, key=lambda x: x.get("sceneNumber", 0))
        subtitles_json_path.write_text(
            _json.dumps(subtitles_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"[WARN] subtitles.json 갱신 실패: {e}", flush=True)

    # 매니페스트 리빌드
    try:
        from auto_agent.scripts.build_manifest import build_manifest
        dir_name = Path(out_dir).name
        build_manifest(str(project.get("id", "")), dir_name, out_dir)
    except Exception as e:
        print(f"[WARN] 매니페스트 리빌드 실패: {e}", flush=True)

    return JSONResponse({"ok": True, "count": len(entries)})


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


@app.post("/api/p/{project_ref}/images/auto-prompt/{scene_num}")
async def auto_prompt(request: Request, project_ref: str, scene_num: int):
    """Sonnet으로 씬 컨텍스트에서 이미지 프롬프트 자동 생성."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
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


@app.post("/api/p/{project_ref}/images/generate/{scene_num}")
async def generate_image(request: Request, project_ref: str, scene_num: int):
    """FAL.ai로 이미지 생성."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
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
    if art_style:
        # output_dir 내 로컬 복사본 우선, 없으면 data/ 아래 canonical 경로
        _local = Path(out_dir) / "art_style.json"
        if _local.exists():
            style_path = str(_local)
        else:
            from auto_agent.db.project_manager import resolve_art_style_path
            _resolved = resolve_art_style_path(art_style, Path(out_dir))
            style_path = str(_resolved) if _resolved and _resolved.exists() else ""
    else:
        style_path = ""

    from auto_agent.tools.image_assets import add_version, next_filename
    img_dir = Path(out_dir) / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # 버전 파일명 생성 → images/generated/
    gen_dir = img_dir / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    fname = next_filename(img_dir, scene_num, "gen", ".png")
    output_path = str(gen_dir / fname)

    # scene_specs에서 캐릭터 이미지 경로 수집
    char_paths = []
    try:
        import unicodedata as _ud
        specs_path = Path(out_dir) / "scene_specs.json"
        char_dir = Path(out_dir) / "characters"
        if specs_path.exists() and char_dir.exists():
            specs_data = _json.loads(specs_path.read_text(encoding="utf-8"))
            char_files = {_ud.normalize("NFC", f.stem): f for f in char_dir.iterdir()
                          if f.suffix.lower() in (".png", ".jpg", ".webp") and "_bak" not in f.stem}
            for sc in specs_data.get("scenes", []):
                if sc["sceneNumber"] == scene_num:
                    for char_id in sc.get("characters", []):
                        char_key = _ud.normalize("NFC", char_id.replace(" ", "_"))
                        match = next((f for stem, f in char_files.items()
                                      if _ud.normalize("NFC", char_key.split("(")[0]) in stem
                                      and "semoji_3D" in stem), None)
                        if match:
                            char_paths.append(str(match))
                    break
    except Exception as _ce:
        import traceback as _tb
        print(f"[char_paths error] {_tb.format_exc()}", flush=True)

    print(f"[generate_image] scene={scene_num} char_paths={char_paths}", flush=True)

    # FAL.ai 호출
    try:
        cmd = [sys.executable, "-m", "auto_agent.tools.image_generate", mode,
               "--prompt", prompt, "--output", output_path]
        if style_path:
            cmd.extend(["--style", style_path])
        if char_paths:
            cmd.extend(["--characters", "|".join(char_paths)])
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
            full_err = result.stderr or result.stdout
            print(f"[image_generate error]\n{full_err}", flush=True)
            return JSONResponse({"error": full_err[:2000]}, 500)
    except Exception as e:
        import traceback
        print(f"[generate_image exception]\n{traceback.format_exc()}", flush=True)
        return JSONResponse({"error": str(e)}, 500)


@app.get("/api/p/{project_ref}/art-style")
async def get_art_style(request: Request, project_ref: str):
    """프로젝트 아트스타일 정보 + 사용 가능한 스타일 목록."""
    import json as _json
    from auto_agent.db.project_manager import resolve_art_style_path

    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    config = pm.get_config(project["id"])
    current = config.get("art_style", "")

    # 현재 스타일 정보 — 프로젝트 로컬 복사본 우선, 없으면 canonical 스타일 사용
    current_info = {}
    if current:
        project_dir = Path(project.get("output_dir", ""))
        local_style_path = project_dir / "art_style.json"
        style_path = local_style_path if local_style_path.exists() else resolve_art_style_path(current, project_dir)
        if style_path and style_path.exists():
            try:
                current_info = _json.loads(style_path.read_text(encoding="utf-8"))
                ref = current_info.get("reference_image", "")
                if ref:
                    _art_out_dir = project.get("output_dir", "")
                    _art_dir_name = Path(_art_out_dir).name if _art_out_dir else project["slug"]
                    local_ref = Path(_art_out_dir) / Path(ref).name
                    if local_ref.exists():
                        current_info["reference_image_url"] = f"/output/{_art_dir_name}/{Path(ref).name}"
                    else:
                        current_info["reference_image_url"] = f"/artstyle/{Path(ref).name}"
            except Exception:
                pass

    # 사용 가능한 스타일 목록 — canonical package data 기준 (enabled=False 제외)
    styles = []
    styles_dir = get_data_dir() / "artstyle" / "styles"
    for p in sorted(styles_dir.glob("*.json")):
        try:
            d = _json.loads(p.read_text(encoding="utf-8"))
            if d.get("enabled", True) is False:
                continue  # 비활성화된 스타일 제외
            styles.append({"path": f"artstyle/styles/{p.name}", "name": d.get("name", p.stem), "file": p.name})
        except Exception:
            styles.append({"path": f"artstyle/styles/{p.name}", "name": p.stem, "file": p.name})

    return JSONResponse({"current": current, "current_info": current_info, "available": styles})


@app.post("/api/p/{project_ref}/art-style")
async def set_art_style(request: Request, project_ref: str):
    """프로젝트 아트스타일 변경 + 로컬 복사 + manifest 재빌드."""
    from auto_agent.db.project_manager import resolve_art_style_path
    from auto_agent.scripts.build_manifest import build_manifest

    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
    body = await request.json()
    new_style = body.get("art_style", "")
    if not resolve_art_style_path(new_style, Path(project.get("output_dir", ""))):
        return JSONResponse({"error": "invalid art_style"}, status_code=400)

    config = pm.get_config(project["id"])
    config["art_style"] = new_style
    pm.set_config(project["id"], config)

    provisioned = pm.provision_art_style(project["id"])
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else slug
    try:
        build_manifest(str(project.get("id", "")), dir_name, out_dir)
    except Exception as e:
        return JSONResponse({
            "ok": False,
            "error": f"manifest rebuild failed: {e}",
            "art_style": new_style,
            "provisioned": provisioned,
        }, status_code=500)

    _setup_studio_project(slug)
    return JSONResponse({"ok": True, "art_style": new_style, "provisioned": provisioned})


@app.post("/api/p/{project_ref}/thumbnail-canvas/export")
async def thumbnail_canvas_export(request: Request, project_ref: str):
    """썸네일 캔버스 PNG 내보내기 — Base64 데이터 수신 후 파일 저장."""
    import base64, re as _re, json as _json
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    body = await request.json()
    data_url = body.get("image_data", "")
    filename = body.get("filename", f"thumbnail_{int(__import__('time').time())}.png")
    # data:image/png;base64,XXXX
    match = _re.match(r"data:image/\w+;base64,(.+)", data_url)
    if not match:
        return JSONResponse({"ok": False, "error": "invalid image data"})
    img_bytes = base64.b64decode(match.group(1))
    save_dir = Path(out_dir) / "images" / "thumbnails"
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / filename
    save_path.write_bytes(img_bytes)
    dir_name = Path(out_dir).name if out_dir else project["slug"]
    return JSONResponse({"ok": True, "filename": filename, "url": f"/output/{dir_name}/images/thumbnails/{filename}"})


@app.get("/api/p/{project_ref}/thumbnail-canvas/state")
async def thumbnail_canvas_state_load(request: Request, project_ref: str):
    """캔버스 레이어 상태 로드."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"ok": False})
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    state_path = Path(project.get("output_dir", "")) / "thumbnail_canvas_state.json"
    if not state_path.exists():
        return JSONResponse({"ok": False})
    import json as _json
    try:
        data = _json.loads(state_path.read_text(encoding="utf-8"))
        return JSONResponse({"ok": True, "state": data})
    except Exception:
        return JSONResponse({"ok": False})


@app.post("/api/p/{project_ref}/thumbnail-canvas/state")
async def thumbnail_canvas_state_save(request: Request, project_ref: str):
    """캔버스 레이어 상태 저장."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"ok": False, "error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    body = await request.json()
    state_path = Path(project.get("output_dir", "")) / "thumbnail_canvas_state.json"
    import json as _json
    state_path.write_text(_json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return JSONResponse({"ok": True})


@app.get("/api/p/{project_ref}/images/all")
async def images_all(request: Request, project_ref: str):
    """프로젝트의 모든 씬 이미지(selected 포함 전체 버전) 반환 — 갤러리 패널용."""
    from auto_agent.tools.image_assets import get_scene_versions
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else project["slug"]
    img_dir = Path(out_dir) / "images"
    assets_path = img_dir / "image_assets.json"
    if not assets_path.exists():
        return JSONResponse({"images": []})
    import json as _json
    assets = _json.loads(assets_path.read_text(encoding="utf-8"))
    result = []
    for entry in assets.get("scenes", []):
        sn = entry.get("sceneNumber")
        raw_selected = entry.get("selected", "")
        # selected 값은 "images/search/..." 형태일 수 있음 — 파일명 부분만 비교
        def _basename(p): return p.split("/")[-1] if p else ""
        sel_base = _basename(raw_selected)
        # images 키 (현행 스키마) 또는 versions 키 (구 스키마)
        img_list = entry.get("images") or entry.get("versions") or []
        for v in img_list:
            fname = v.get("file", "")
            if not fname:
                continue
            # fname은 "search/scene_009_search_01.jpg" 형태일 수 있음
            rel_path = fname  # 상대 경로 그대로 URL에 사용
            fpath = img_dir / fname
            if not fpath.exists():
                continue
            fname_base = _basename(fname)
            is_selected = (fname == raw_selected or fname_base == sel_base) if raw_selected else False
            result.append({
                "sceneNumber": sn,
                "file": fname,
                "url": f"/output/{dir_name}/images/{rel_path}",
                "selected": is_selected,
                "source": v.get("type", v.get("source", "")),
            })
    return JSONResponse({"images": result})


@app.get("/api/p/{project_ref}/images/history/{scene_num}")
async def image_history(request: Request, project_ref: str, scene_num: int):
    """씬의 이미지 생성 히스토리."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, 404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else project["slug"]
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


@app.put("/api/p/{project_ref}/scenes/{scene_num}")
async def api_update_scene(request: Request, project_ref: str, scene_num: int):
    """씬 편집 → Supabase Storage에 저장."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    pid = project["id"]
    out_dir = project["output_dir"]

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


@app.post("/api/p/{project_ref}/scenes/{scene_num}/rerun")
async def api_rerun_scene(request: Request, project_ref: str, scene_num: int):
    """씬 단위 재연출 — script-director를 해당 씬에만 실행."""
    import subprocess, sys
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )

    out_dir = project.get("output_dir", "")
    if not out_dir:
        return JSONResponse({"error": "output_dir not set"}, status_code=400)

    specs_path = Path(out_dir) / "scene_specs.json"
    if not specs_path.exists():
        return JSONResponse({"error": "scene_specs.json not found"}, status_code=404)

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    target = next((s for s in specs.get("scenes", []) if s["sceneNumber"] == scene_num), None)
    if not target:
        return JSONResponse({"error": f"Scene {scene_num} not found"}, status_code=404)

    # 씬 컨텍스트 구성
    scene_ctx = json.dumps(target, ensure_ascii=False, indent=2)
    prompt = f"""아래 씬의 연출을 다시 검토하고 개선하세요.
씬 번호, 나레이션, 챕터는 변경하지 마세요.
layout, mood, imageAsset, motion, headline/items 등 연출 요소만 개선합니다.

현재 씬:
{scene_ctx}

반드시 씬 전체를 JSON으로만 응답하세요 (설명 없이 JSON만).
"""

    try:
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        result = subprocess.run(
            ["claude", "--model", "claude-sonnet-4-6", "--max-turns", "3",
             "--output-format", "text"],
            input=prompt, capture_output=True, text=True, env=env,
            cwd=str(get_workspace_dir()), timeout=120,
        )
        raw = (result.stdout or "").strip()
        # JSON 블록 추출
        if "```" in raw:
            lines = raw.split("\n")
            start = 1 if lines[0].strip().startswith("```") else 0
            end = -1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[start:end]).strip()

        updated_scene = json.loads(raw)
        # sceneNumber, narration, chapter 보호
        for protect in ("sceneNumber", "narration", "chapter"):
            if protect in target:
                updated_scene[protect] = target[protect]

        # scene_specs.json 업데이트
        for i, s in enumerate(specs["scenes"]):
            if s["sceneNumber"] == scene_num:
                specs["scenes"][i] = updated_scene
                break

        specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
        pm.save_project_json(project["id"], "scene_specs.json", specs)

        return {"ok": True, "scene_number": scene_num, "narration": updated_scene.get("narration", "")}

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "재연출 타임아웃 (120s)"}, status_code=504)
    except json.JSONDecodeError as e:
        return JSONResponse({"error": f"JSON 파싱 실패: {e}"}, status_code=500)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/projects/{project_id}/cleanup", response_class=HTMLResponse)
async def run_cleanup(request: Request, project_id: int):
    pm = get_pm()
    cm = CleanupManager(pm)
    result = cm.full_cleanup(project_id, dry_run=True)
    return JSONResponse(result)


# ─────────────────────────────
# Image Candidates API
# ─────────────────────────────

@app.get("/api/p/{project_ref}/scene/{scene_num}/image-candidates")
async def get_image_candidates_by_slug(request: Request, project_ref: str, scene_num: int, include_all: bool = False):
    """slug 기반 씬 이미지 후보 목록.

    include_all=true: 다운로드하지 않은 후보까지 썸네일 URL로 반환.
    """
    from auto_agent.dashboard.helpers import get_scene_image_candidates
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    out_dir = project["output_dir"]
    dir_name = Path(out_dir).name if out_dir else project["slug"]
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


@app.post("/api/p/{project_ref}/scene/{scene_num}/download-candidate")
async def download_candidate_image(request: Request, project_ref: str, scene_num: int):
    """썸네일에서 선택한 미다운로드 후보의 원본을 다운로드 + 적용."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]

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


@app.post("/api/p/{project_ref}/scene/{scene_num}/select-image")
async def select_image_candidate_by_slug(request: Request, project_ref: str, scene_num: int):
    """slug 기반 이미지 선택."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
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


@app.post("/api/p/{project_ref}/pipeline/start")
async def pipeline_start(request: Request, project_ref: str):
    """파이프라인 백그라운드 실행."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
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
    _out_dir = project.get("output_dir", "")
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


@app.get("/api/p/{project_ref}/pipeline/status")
async def pipeline_status(request: Request, project_ref: str):
    """파이프라인 실행 상태 확인."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
    running = _is_pipeline_running(slug)
    result = {"running": running, "slug": slug}
    if not running:
        proc = _pipeline_procs.get(slug)
        if proc:
            result["exit_code"] = proc.returncode
    return result


@app.post("/api/p/{project_ref}/pipeline/stop")
async def pipeline_stop(request: Request, project_ref: str):
    """파이프라인 중지."""
    pm = get_pm()
    project, needs_redirect = resolve_project_ref(pm, project_ref)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)
    if needs_redirect:
        return RedirectResponse(
            url=canonical_uuid_url(
                str(request.url.path) + (f"?{request.url.query}" if request.url.query else ""),
                project["uuid"],
            ),
            status_code=307,
        )
    slug = project["slug"]
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
        storage_key = Path(out_dir).name if out_dir else f"{project.get('uuid', '')}_{slug}"

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

    try:
        env = _get_node_env()
        env["BROWSER"] = "none"  # 자동 브라우저 열기 방지
        # Node 25 호환: npx symlink 깨짐 → remotion-cli.js 직접 실행
        from auto_agent.utils.platform import get_node_bin_dir
        try:
            node_bin = str(get_node_bin_dir() / "node")
        except Exception:
            node_bin = "node"
        cli_js = REMOTION_DIR / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
        _studio_proc = subprocess.Popen(
            [node_bin, str(cli_js), "studio", "src/index.ts", "--port", str(STUDIO_PORT)],
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
