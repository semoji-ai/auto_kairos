"""
씬 레이아웃 에디터 API.

3가지 저장 모드:
  1. 저장만 ($0) — JSON 직접 패치
  2. 저장+보정 (~$0.03) — Haiku 1회 호출로 정합성 수정
  3. 미리보기 ($0) — 변경 사항 diff만 반환
"""
import json
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from auto_agent.dashboard.helpers import resolve_project_by_slug
from auto_agent.orchestrator.context_memory import HAIKU_MODEL

router = APIRouter(prefix="/api/p/{slug}/editor", tags=["scene-editor"])


# ─── 매니페스트 메타/재빌드 (에디터 외부에서 호출) ───

from fastapi import APIRouter as _AR
manifest_router = _AR(prefix="/api/p/{slug}", tags=["manifest-utils"])


@manifest_router.get("/manifest-meta")
async def manifest_meta(slug: str):
    """매니페스트 메타 데이터 반환 (get_editor_manifest_meta로 위임)."""
    return await get_editor_manifest_meta(slug)


@manifest_router.post("/rebuild-manifest")
async def rebuild_manifest(slug: str):
    """manifest.json 재빌드 트리거."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    import subprocess, shutil
    python = shutil.which("python3") or shutil.which("python") or "python3"

    # 로컬 모드: output 디렉토리에서 직접 빌드
    out_dir = project.get("output_dir", "")
    if not out_dir:
        return JSONResponse({"error": "output_dir 없음"}, status_code=400)
    args = [python, "-m", "auto_agent.scripts.build_manifest", "--local", out_dir]

    try:
        import os
        env = {**os.environ}
        result = subprocess.run(
            args,
            capture_output=True, text=True, timeout=120,
            env=env,
        )
        if result.returncode == 0:
            return {"ok": True, "message": "manifest 재빌드 완료"}
        return {"ok": False, "error": result.stderr[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 썸네일 (Remotion renderStill) ───

_thumbnail_tasks: dict = {}  # slug → asyncio.Task


@manifest_router.get("/thumbnails/scene/{scene_num}")
async def get_scene_thumbnail(slug: str, scene_num: int):
    """씬 썸네일 PNG 반환 (캐시). 없으면 placeholder."""
    from fastapi.responses import FileResponse
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    output_dir = project.get("output_dir", "")
    thumb_path = Path(output_dir) / "thumbnails" / f"scene_{str(scene_num).zfill(3)}.png"

    if thumb_path.exists():
        return FileResponse(
            thumb_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=300"},
        )

    # 썸네일 아직 없음 → 1x1 transparent PNG (placeholder)
    import base64
    PIXEL = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPj/HwADBwIAMCbHYQAAAABJRU5ErkJggg=="
    )
    from fastapi.responses import Response
    return Response(
        content=PIXEL,
        media_type="image/png",
        headers={"Cache-Control": "no-cache"},
    )


@manifest_router.post("/generate-thumbnails")
async def generate_thumbnails(slug: str):
    """Remotion renderStill로 모든 씬 썸네일 배치 생성 (비동기)."""
    import asyncio
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    output_dir = project.get("output_dir", "")
    # 디렉토리명(uuid_slug 형식) 기준으로 manifest 파일명 구성
    dir_name = Path(output_dir).name if output_dir else slug

    # manifest 경로 탐색 (여러 위치)
    from auto_agent.paths import get_workspace_dir
    workspace = get_workspace_dir()
    manifest_candidates = [
        Path(output_dir) / "manifest.json",
        workspace / "remotion" / "public" / "manifests" / f"{dir_name}.json",
        workspace / "remotion" / "public" / "manifest.json",
    ]
    manifest_path = None
    for p in manifest_candidates:
        if p.exists():
            manifest_path = p
            break

    if not manifest_path:
        # manifest 빌드 시도
        import subprocess, shutil
        python = shutil.which("python3") or "python3"
        subprocess.run(
            [python, "-m", "auto_agent.scripts.build_manifest",
             "--project", output_dir],
            capture_output=True, text=True, timeout=60,
            cwd=str(workspace),
        )
        # 다시 탐색
        for p in manifest_candidates:
            if p.exists():
                manifest_path = p
                break

    if not manifest_path:
        return JSONResponse({"error": "manifest.json 없음"}, status_code=404)

    # 이미 진행 중?
    if slug in _thumbnail_tasks and not _thumbnail_tasks[slug].done():
        return {"ok": True, "status": "already_running"}

    async def _run():
        from auto_agent.utils.platform import get_env_with_node, get_node_bin_dir
        import shutil
        try:
            node_env = get_env_with_node()
            node_bin_dir = get_node_bin_dir()
        except EnvironmentError:
            return

        node_exe = "node.exe" if __import__("sys").platform == "win32" else "node"
        node = str(node_bin_dir / node_exe)

        script = Path(__file__).parent.parent.parent / "remotion" / "generate-thumbnails.mjs"
        if not script.exists():
            return

        proc = await asyncio.create_subprocess_exec(
            node, str(script), str(manifest_path), output_dir,
            "--width=480",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=node_env,
            cwd=str(script.parent),
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            import logging
            logging.getLogger("thumbnails").error(
                f"썸네일 생성 실패: {stderr.decode()[:500]}"
            )

    _thumbnail_tasks[slug] = asyncio.create_task(_run())
    return {"ok": True, "status": "started"}


@manifest_router.get("/thumbnails/status")
async def thumbnails_status(slug: str):
    """썸네일 생성 상태 확인."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    output_dir = project.get("output_dir", "")
    thumb_dir = Path(output_dir) / "thumbnails"
    count = len(list(thumb_dir.glob("scene_*.png"))) if thumb_dir.exists() else 0

    running = slug in _thumbnail_tasks and not _thumbnail_tasks[slug].done()

    return {"count": count, "running": running}

# ─── 레이아웃 제약 ───

LAYOUT_CONSTRAINTS = {
    "full-bleed-image": {"items_min": 0, "items_max": 0, "requires": []},
    "title-card": {"items_min": 0, "items_max": 0, "requires": ["headline"]},
    "cinematic-text": {"items_min": 0, "items_max": 2, "requires": ["headline"]},
    "lower-third": {"items_min": 1, "items_max": 3, "requires": ["headline"]},
    "split-left": {"items_min": 1, "items_max": 4, "requires": []},
    "split-right": {"items_min": 1, "items_max": 4, "requires": []},
    "picture-in-picture": {"items_min": 0, "items_max": 2, "requires": []},
    "ken-burns": {"items_min": 0, "items_max": 0, "requires": []},
    "parallax-layers": {"items_min": 0, "items_max": 0, "requires": []},
    "info-list": {"items_min": 2, "items_max": 6, "requires": ["headline"]},
    "comparison": {"items_min": 2, "items_max": 2, "requires": ["headline"]},
    "timeline": {"items_min": 2, "items_max": 6, "requires": ["headline"]},
    "stat-counter": {"items_min": 1, "items_max": 4, "requires": []},
    "quote-highlight": {"items_min": 0, "items_max": 0, "requires": ["headline"]},
    "map-zoom": {"items_min": 0, "items_max": 2, "requires": []},
    "before-after": {"items_min": 2, "items_max": 2, "requires": []},
    "text-focus": {"items_min": 0, "items_max": 3, "requires": ["headline"]},
    "data-visualization": {"items_min": 1, "items_max": 4, "requires": ["headline"]},
    "reveal-sequence": {"items_min": 2, "items_max": 5, "requires": []},
    "chapter-title": {"items_min": 0, "items_max": 0, "requires": ["headline"]},
    "closing-card": {"items_min": 0, "items_max": 0, "requires": ["headline"]},
    "full-bleed-video": {"items_min": 0, "items_max": 0, "requires": []},
    "dual-panel": {"items_min": 2, "items_max": 4, "requires": ["headline"]},
    "montage-grid": {"items_min": 3, "items_max": 6, "requires": []},
}


@router.get("/meta")
async def editor_meta(slug: str):
    """에디터 메타데이터 (레이아웃 제약, 드롭다운 옵션 등)."""
    return {
        "layouts": LAYOUT_CONSTRAINTS,
        "mood_options": [
            "neutral", "dramatic", "hopeful", "dark", "tense",
            "melancholic", "epic", "mysterious", "warm", "cold",
        ],
        "reveal_options": [
            "none", "fade", "slide-up", "slide-left", "zoom-in",
            "typewriter", "split", "blur-in",
        ],
        "emphasis_options": [
            "none", "pulse", "glow", "underline", "highlight", "shake",
        ],
    }


def _load_specs(project: dict):
    """로컬 scene_specs.json 로드."""
    specs_path = Path(project.get("output_dir", "")) / "scene_specs.json"
    if specs_path.exists():
        return json.loads(specs_path.read_text(encoding="utf-8"))
    return None


@router.get("/scenes/{scene_num}/images")
async def get_scene_images(slug: str, scene_num: int):
    """씬의 이미지 후보 목록."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    from auto_agent.dashboard.helpers import get_scene_image_candidates
    _out_dir = project.get("output_dir", "")
    _dir_name = Path(_out_dir).name if _out_dir else project.get("slug", "")
    candidates = get_scene_image_candidates(
        _dir_name, scene_num, _out_dir
    )

    return JSONResponse(
        {"scene_number": scene_num, "candidates": candidates},
        headers={"Cache-Control": "no-store"},
    )


@router.post("/scenes/{scene_num}/select-image")
async def select_scene_image(slug: str, scene_num: int, request: Request):
    """씬 이미지 선택 — scene_specs의 imagePath를 선택한 URL로 교체."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    image_url = body.get("image_url")
    if not image_url:
        return JSONResponse({"error": "image_url 필요"}, status_code=400)

    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    # 해당 씬 찾아서 imagePath 업데이트
    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            scene["imagePath"] = image_url
            # vizBackgroundPath도 업데이트 (시각화 씬인 경우)
            if scene.get("visualization"):
                scene["vizBackgroundPath"] = image_url
            break
    else:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    # 저장
    specs_path = Path(project["output_dir"]) / "scene_specs.json"
    specs_path.write_text(
        json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {"ok": True, "image_url": image_url}


@router.get("/scene-list")
async def get_scene_list(slug: str):
    """에디터용 씬 목록 (번호 + 제목/헤드라인 요약)."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)
    scenes = []
    for s in specs.get("scenes", []):
        num = s.get("sceneNumber") or s.get("scene_number", 0)
        viz = s.get("visualization") or {}
        creative = viz.get("creative") or {}
        title = creative.get("headline") or viz.get("title") or s.get("title") or ""
        dur = s.get("audioDurationSec") or s.get("durationFrames", 150) / 30
        scenes.append({
            "sceneNumber": num,
            "title": title[:60],
            "hasMap": bool(s.get("mapScene")),
            "audioDurationSec": round(float(dur), 2) if dur else 5.0,
        })
    return {"scenes": scenes}


@router.get("/manifest-meta")
async def get_editor_manifest_meta(slug: str):
    """에디터용 매니페스트 메타 데이터 (fps, resolution, font 등).
    로컬 manifest → 로컬 scene_specs → 기본값 순서로 탐색."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    from auto_agent.dashboard.helpers import load_project_json
    out_dir = project.get("output_dir", "")

    # 로컬 파일에서 시도 (remotion/public/manifests/{dir_name}.json 포함)
    from auto_agent.paths import get_workspace_dir
    workspace = get_workspace_dir()
    _manifest_dir_name = Path(out_dir).name if out_dir else slug
    candidates = [
        Path(out_dir) / "manifest.json" if out_dir else None,
        workspace / "remotion" / "public" / "manifests" / f"{_manifest_dir_name}.json",
        workspace / "remotion" / "public" / "manifest.json",
    ]
    for p in candidates:
        if p and p.exists():
            try:
                data = json.loads(p.read_text("utf-8"))
                m = data.get("manifest", data)
                meta = m.get("meta")
                if meta:
                    return {"meta": meta}
            except Exception:
                pass

    # 3) scene_specs.json에서 시도
    if out_dir:
        specs = load_project_json(out_dir, "scene_specs.json")
        if specs and specs.get("meta"):
            return {"meta": specs["meta"]}

    # 4) 기본값
    return {"meta": {"fps": 30, "resolution": {"width": 1920, "height": 1080},
                     "subtitleFont": "Pretendard", "vizFont": "Pretendard"}}


@router.get("/scenes/{scene_num}")
async def get_scene_for_editor(slug: str, scene_num: int):
    """에디터용 씬 데이터 + 레이아웃 제약 정보."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            # 이미지 URL 주입 (scene_specs에는 메타만 있음)
            _inject_image_url(project, scene, scene_num)
            layout = scene.get("layout", "")
            constraints = LAYOUT_CONSTRAINTS.get(layout, {})
            return JSONResponse(
                {"scene": scene, "constraints": constraints, "layout": layout},
                headers={"Cache-Control": "no-store"},
            )

    return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)


def _inject_image_url(project: dict, scene: dict, scene_num: int):
    """scene에 imagePath / vizBackgroundPath가 비어있으면 로컬에서 URL 주입."""
    if scene.get("imagePath") or scene.get("vizBackgroundPath"):
        return  # 이미 URL이 있으면 스킵

    from auto_agent.dashboard.helpers import get_scene_image_url
    _out_dir = project.get("output_dir", "")
    _dir_name = Path(_out_dir).name if _out_dir else project.get("slug", "")
    url = get_scene_image_url(_dir_name, scene_num, _out_dir)

    if url:
        placement = (scene.get("imageAsset") or {}).get("placement", "background")
        if scene.get("visualization"):
            scene["vizBackgroundPath"] = url
        else:
            scene["imagePath"] = url


@router.post("/scenes/{scene_num}")
async def save_scene(slug: str, scene_num: int, request: Request):
    """씬 저장.

    Body:
    {
        "scene_data": { ... },
        "mode": "save" | "save_fix" | "preview"
    }
    """
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    scene_data = body.get("scene_data", {})
    mode = body.get("mode", "save")

    if not scene_data:
        return JSONResponse({"error": "scene_data 필요"}, status_code=400)

    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    scenes = specs.get("scenes", [])

    target_idx = None
    old_scene = None
    for i, s in enumerate(scenes):
        if s["sceneNumber"] == scene_num:
            target_idx = i
            old_scene = s.copy()
            break

    if target_idx is None:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    # 레이아웃 제약 검증
    layout = scene_data.get("layout", old_scene.get("layout", ""))
    constraints = LAYOUT_CONSTRAINTS.get(layout, {})
    items = scene_data.get("items", old_scene.get("items", []))
    items_count = len(items) if items else 0

    warnings = []
    if constraints.get("items_min") and items_count < constraints["items_min"]:
        warnings.append(
            f"items {items_count}개 < 최소 {constraints['items_min']}개"
        )
    if constraints.get("items_max") is not None and items_count > constraints["items_max"]:
        warnings.append(
            f"items {items_count}개 > 최대 {constraints['items_max']}개"
        )
    for req in constraints.get("requires", []):
        if not scene_data.get(req) and not old_scene.get(req):
            warnings.append(f"필수 필드 '{req}' 없음")

    # diff 계산
    diff = {}
    for key, value in scene_data.items():
        if old_scene.get(key) != value:
            diff[key] = {"old": old_scene.get(key), "new": value}

    # 모드별 처리
    if mode == "preview":
        return {
            "ok": True,
            "mode": "preview",
            "diff": diff,
            "warnings": warnings,
        }

    if mode == "save_fix":
        # Haiku 1회 호출로 정합성 보정
        fixed_data = _coherence_fix(old_scene, scene_data, diff)
        scene_data = fixed_data["scene"]
        fix_log = fixed_data.get("fixes", [])
    else:
        fix_log = []

    # 저장
    scenes[target_idx] = {**old_scene, **scene_data}
    specs["scenes"] = scenes

    # 로컬 파일에 저장
    output_dir = project.get("output_dir", "")
    if output_dir:
        specs_path = Path(output_dir) / "scene_specs.json"
        if specs_path.exists():
            from auto_agent.dashboard.json_editor import _backup_json
            _backup_json(specs_path)
        specs_path.parent.mkdir(parents=True, exist_ok=True)
        specs_path.write_text(
            json.dumps(specs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "ok": True,
        "mode": mode,
        "diff": diff,
        "warnings": warnings,
        "fixes": fix_log,
        "scene": scenes[target_idx],
    }


def _coherence_fix(old_scene: dict, new_scene: dict, diff: dict) -> dict:
    """Haiku 1회 호출로 정합성 보정.

    비용: ~$0.03 (입력 ~1K tokens, 출력 ~500 tokens)
    """
    if not diff:
        return {"scene": {**old_scene, **new_scene}, "fixes": []}

    try:
        import anthropic

        client = anthropic.Anthropic()
        diff_text = json.dumps(diff, ensure_ascii=False, indent=2)
        scene_text = json.dumps(
            {**old_scene, **new_scene}, ensure_ascii=False, indent=2
        )

        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"씬 레이아웃이 수정되었습니다. 변경된 부분:\n"
                        f"{diff_text}\n\n"
                        f"현재 씬 데이터:\n{scene_text}\n\n"
                        f"레이아웃 변경에 따라 다른 필드(items, headline, "
                        f"duration 등)의 정합성을 확인하고 필요한 수정만 "
                        f"JSON으로 반환하세요.\n\n"
                        f'출력: {{"fixes": ["수정 설명"], '
                        f'"patch": {{"필드명": "수정값"}}}}'
                    ),
                }
            ],
        )

        result = json.loads(response.content[0].text)
        patch = result.get("patch", {})
        fixes = result.get("fixes", [])

        merged = {**old_scene, **new_scene, **patch}
        return {"scene": merged, "fixes": fixes}

    except Exception as e:
        # API 실패 시 보정 없이 저장
        return {
            "scene": {**old_scene, **new_scene},
            "fixes": [f"보정 실패: {e}"],
        }
