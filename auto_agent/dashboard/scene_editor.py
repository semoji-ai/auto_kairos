"""
씬 레이아웃 에디터 API.

3가지 저장 모드:
  1. 저장만 ($0) — JSON 직접 패치
  2. 저장+보정 (~$0.03) — Haiku 1회 호출로 정합성 수정
  3. 미리보기 ($0) — 변경 사항 diff만 반환
"""
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File
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

    # project_id로 빌드 (DB config에서 art_style 등 로드)
    out_dir = project.get("output_dir", "")
    if not out_dir:
        return JSONResponse({"error": "output_dir 없음"}, status_code=400)
    project_id = str(project.get("id", ""))
    storage_key = Path(out_dir).name if out_dir else slug
    args = [python, "-m", "auto_agent.scripts.build_manifest", project_id, storage_key, out_dir]

    try:
        import os
        env = {**os.environ}
        result = subprocess.run(
            args,
            capture_output=True, text=True, encoding="utf-8", timeout=120,
            env=env,
        )
        if result.returncode == 0:
            return {"ok": True, "message": "manifest 재빌드 완료"}
        return {"ok": False, "error": result.stderr[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _rebuild_manifest_sync(project: dict) -> None:
    """매니페스트 동기 리빌드 후 manifest.json 교체."""
    import subprocess, shutil, os, sys
    out_dir = project.get("output_dir", "")
    if not out_dir:
        return
    python = sys.executable  # 현재 서버와 동일한 Python 사용
    project_id = str(project.get("id", ""))
    storage_key = project.get("storage_key") or Path(out_dir).name
    try:
        subprocess.run(
            [python, "-m", "auto_agent.scripts.build_manifest", project_id, storage_key, out_dir],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
            env={**os.environ},
        )
        # 빌드된 manifest를 manifest.json으로 복사 (Remotion Studio 즉시 반영)
        from auto_agent.paths import get_workspace_dir
        remotion_public = get_workspace_dir() / "remotion" / "public"
        built = remotion_public / "manifests" / f"{storage_key}.json"
        manifest_dst = remotion_public / "manifest.json"
        if built.exists():
            shutil.copy2(str(built), str(manifest_dst))
    except Exception as e:
        print(f"[WARN] 에디터 매니페스트 리빌드 실패: {e}")


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
            headers={"Cache-Control": "public, max-age=10"},
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
            capture_output=True, text=True, encoding="utf-8", timeout=60,
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


@manifest_router.get("/images/all")
async def get_all_images(slug: str):
    """전체 이미지 갤러리 — search/ + generated/ 폴더 스캔."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else project.get("slug", "")
    img_dir = Path(out_dir) / "images"

    # image_assets.json에서 selected 맵 구성 (신 포맷 images[].selected boolean + 구 포맷 selected 문자열 모두 지원)
    selected_map: dict = {}
    assets_path = img_dir / "image_assets.json"
    if assets_path.exists():
        try:
            assets = json.loads(assets_path.read_text(encoding="utf-8"))
            for entry in assets.get("scenes", []):
                sn = entry.get("sceneNumber")
                if sn is None:
                    continue
                # 신 포맷: images[].selected == True 인 파일
                for img in entry.get("images", []):
                    if img.get("selected") and img.get("file"):
                        f = img["file"]
                        selected_map[f] = sn
                        selected_map[f.split("/")[-1]] = sn
                # 구 포맷 fallback
                sel = entry.get("selected", "")
                if sel and sel not in selected_map:
                    selected_map[sel] = sn
                    selected_map[sel.split("/")[-1]] = sn
        except Exception:
            pass

    images = []
    for subdir, src_type in [("search", "search"), ("generated", "generated")]:
        d = img_dir / subdir
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
                continue
            rel = f"{subdir}/{f.name}"
            url = f"/output/{dir_name}/images/{rel}"
            sn = selected_map.get(rel) or selected_map.get(f.name)
            images.append({
                "file": rel,
                "url": url,
                "type": src_type,
                "sceneNumber": sn,
                "selected": sn is not None,
            })

    return JSONResponse({"images": images}, headers={"Cache-Control": "no-store"})


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
    """씬의 이미지 후보 목록 — image_assets.json 신 스키마 기준 (스토리보드와 동일).

    스토리보드의 /api/p/{slug}/images/versions/{scene_num}과 같은 데이터 소스를 사용.
    "이미지 없음" 특수 항목을 첫 번째로 포함.
    """
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    _out_dir = project.get("output_dir", "")
    _dir_name = Path(_out_dir).name if _out_dir else project.get("slug", "")
    img_dir = Path(_out_dir) / "images"

    # "이미지 없음" 항목은 항상 첫 번째
    candidates = [
        {
            "id": "__none__",
            "url": "",
            "file_name": "",
            "type": "none",
            "selected": False,
        }
    ]

    # image_assets.json 신 스키마 로드
    assets_path = img_dir / "image_assets.json"
    if assets_path.exists():
        try:
            assets = json.loads(assets_path.read_text(encoding="utf-8"))
            raw_selected = ""
            for entry in assets.get("scenes", []):
                if entry.get("sceneNumber") != scene_num:
                    continue
                raw_selected = entry.get("selected", "")
                for v in entry.get("images") or entry.get("versions") or []:
                    fname = v.get("file", "")
                    if not fname:
                        continue
                    fpath = img_dir / fname
                    if not fpath.exists():
                        continue
                    src_type = v.get("type") or v.get("source") or "unknown"
                    # ImageSelector type 필드에 맞게 정규화
                    type_map = {"search": "search", "wikimedia": "search", "generate": "generated", "generated": "generated"}
                    candidates.append({
                        "id": fname,
                        "url": f"/output/{_dir_name}/images/{fname}",
                        "file_name": fname.split("/")[-1],
                        "type": type_map.get(src_type, src_type),
                        "selected": False,
                    })
            # selected 표시
            if raw_selected:
                sel_base = raw_selected.split("/")[-1]
                for c in candidates:
                    if c["id"] == raw_selected or (c["file_name"] and c["file_name"] == sel_base):
                        c["selected"] = True
                        break
            # 선택된 항목이 없으면 source: none 체크
            if not any(c["selected"] for c in candidates[1:]):
                # scene_specs에서 source가 none인지 확인
                specs_path = Path(_out_dir) / "scene_specs.json"
                if specs_path.exists():
                    specs = json.loads(specs_path.read_text(encoding="utf-8"))
                    for s in specs.get("scenes", []):
                        if s.get("sceneNumber") == scene_num:
                            if (s.get("imageAsset") or {}).get("source") == "none":
                                candidates[0]["selected"] = True
                            break
        except Exception as e:
            print(f"[WARN] editor images load error: {e}")

    return JSONResponse(
        {"scene_number": scene_num, "candidates": candidates},
        headers={"Cache-Control": "no-store"},
    )


@router.post("/scenes/{scene_num}/select-image")
async def select_scene_image(slug: str, scene_num: int, request: Request):
    """씬 이미지 선택 — scene_specs + image_assets.json 동기화.

    image_url == "" → source:"none" 처리 (이미지 없음).
    """
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    # image_url, url 둘 다 허용 (갤러리 드래그는 url로 전송)
    image_url = body.get("image_url") or body.get("url", "")
    src_file = body.get("file", "")  # 기존 버전 선택 또는 갤러리 드래그 원본 파일명
    # file만 있는 경우(기존 버전 직접 선택)는 is_none이 아님
    is_none = (image_url == "" or image_url is None) and not src_file

    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    out_dir = project["output_dir"]
    img_dir = Path(out_dir) / "images"

    # 해당 씬의 sceneId 조회 (씬 분할/통합에 안전한 자산 매핑용)
    scene_id_for_file: str | None = None
    for sc in specs.get("scenes", []):
        if sc.get("sceneNumber") == scene_num:
            scene_id_for_file = sc.get("sceneId")
            break

    def _filename_prefix() -> str:
        if scene_id_for_file:
            return f"scene_{scene_id_for_file}_search_"
        return f"scene_{scene_num:03d}_search_"

    # ── 이미지를 search/ 폴더에 로컬 저장 (갤러리 드래그 또는 외부 URL) ──
    import re as _re
    if not is_none:
        search_dir = img_dir / "search"
        search_dir.mkdir(exist_ok=True)
        # sceneId + 레거시 sceneNumber 패턴 모두 카운트해 인덱스 충돌 회피
        prefix = _filename_prefix()
        legacy_prefix = f"scene_{scene_num:03d}_search_"
        pat_id = _re.compile(rf"{_re.escape(prefix)}(\d+)\.[^.]+")
        pat_num = _re.compile(rf"{_re.escape(legacy_prefix)}(\d+)\.[^.]+")
        existing = []
        for f in search_dir.iterdir():
            m = pat_id.match(f.name) or (pat_num.match(f.name) if scene_id_for_file else None)
            if m:
                existing.append(int(m.group(1)))
        next_idx = max(existing, default=0) + 1
        dir_name = Path(out_dir).name

        if src_file:
            src_path = img_dir / src_file
            if src_path.exists():
                # 이미 images/ 하위에 있는 기존 버전이면 복사 없이 직접 선택
                image_url = f"/output/{dir_name}/images/{src_file}"
            else:
                # 갤러리 드래그 등 외부 파일: search/로 복사
                ext = Path(src_file).suffix
                dest_name = f"{prefix}{next_idx:02d}{ext}"
                try:
                    shutil.copy2(src_path, search_dir / dest_name)
                    image_url = f"/output/{dir_name}/images/search/{dest_name}"
                except Exception:
                    pass
        elif image_url.startswith("http://") or image_url.startswith("https://"):
            # 외부 URL: 다운로드 후 로컬 저장
            try:
                import requests as _req
                from urllib.parse import urlparse as _urlparse
                parsed = _urlparse(image_url)
                url_ext = Path(parsed.path).suffix.lower()
                if url_ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                    url_ext = ".jpg"
                dest_name = f"{prefix}{next_idx:02d}{url_ext}"
                resp = _req.get(image_url, timeout=30)
                resp.raise_for_status()
                (search_dir / dest_name).write_bytes(resp.content)
                image_url = f"/output/{dir_name}/images/search/{dest_name}"
            except Exception as e:
                print(f"[WARN] URL 다운로드 실패: {e}")

    # ── scene_specs 업데이트 ──
    found = False
    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            if is_none:
                # 이미지 없음: imagePath 제거, imageAsset.source = "none"
                scene.pop("imagePath", None)
                scene.pop("vizBackgroundPath", None)
                ia = scene.get("imageAsset") or {}
                ia["source"] = "none"
                scene["imageAsset"] = ia
            else:
                scene["imagePath"] = image_url
                if scene.get("visualization"):
                    scene["vizBackgroundPath"] = image_url
                # imageAsset.source가 none이었다면 복원
                ia = scene.get("imageAsset") or {}
                if ia.get("source") == "none":
                    ia.pop("source", None)
                    scene["imageAsset"] = ia
            found = True
            break

    if not found:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    specs_path = Path(out_dir) / "scene_specs.json"
    specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── image_assets.json selected 동기화 ──
    assets_path = img_dir / "image_assets.json"
    if assets_path.exists():
        try:
            assets = json.loads(assets_path.read_text(encoding="utf-8"))
            dir_name = Path(out_dir).name
            prefix = f"/output/{dir_name}/images/"

            # 씬 엔트리 찾기 (없으면 생성)
            scene_entry = None
            for entry in assets.get("scenes", []):
                if entry.get("sceneNumber") == scene_num:
                    scene_entry = entry
                    break
            if scene_entry is None:
                scene_entry = {"sceneNumber": scene_num, "images": []}
                assets.setdefault("scenes", []).append(scene_entry)
                assets["scenes"].sort(key=lambda x: x.get("sceneNumber", 0))

            if is_none:
                # 이미지 없음: 모든 images[].selected = False, selected 필드 제거
                for img in scene_entry.get("images", []):
                    img["selected"] = False
                scene_entry.pop("selected", None)
            else:
                rel_path = image_url[len(prefix):] if image_url.startswith(prefix) else ""
                if rel_path:
                    # 모든 기존 images[].selected = False
                    for img in scene_entry.get("images", []):
                        img["selected"] = False
                    # 새 파일이 images[]에 없으면 추가
                    existing_files = [img.get("file", "") for img in scene_entry.get("images", [])]
                    if rel_path not in existing_files:
                        new_type = "search" if rel_path.startswith("search/") else "generated"
                        scene_entry.setdefault("images", []).append({
                            "file": rel_path,
                            "type": new_type,
                            "selected": True,
                        })
                    else:
                        for img in scene_entry.get("images", []):
                            if img.get("file") == rel_path:
                                img["selected"] = True
                                break
                    # 구 포맷 호환 (get_all_images에서 사용)
                    scene_entry["selected"] = rel_path

            assets_path.write_text(json.dumps(assets, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[WARN] image_assets sync failed: {e}")

    # 매니페스트 리빌드
    _rebuild_manifest_sync(project)

    return {"ok": True, "image_url": image_url, "is_none": is_none}


@router.post("/scenes/{scene_num}/select-images")
async def select_scene_images(slug: str, scene_num: int, request: Request):
    """person_card / images_grid용 복수 이미지 저장.

    body: {"images": [url, url, ...]}
    scene_specs.json의 해당 씬에 images[] 배열로 저장한다.
    """
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    images = body.get("images", [])

    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    found = False
    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            scene["images"] = images
            found = True
            break

    if not found:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    out_dir = project["output_dir"]
    specs_path = Path(out_dir) / "scene_specs.json"
    specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    _rebuild_manifest_sync(project)
    return {"ok": True, "images": images}


@router.post("/scenes/{scene_num}/upload-image")
async def upload_scene_image(slug: str, scene_num: int, file: UploadFile = File(...)):
    """파일 직접 업로드 → search/ 폴더 저장 후 select-image와 동일하게 등록."""
    import re as _re
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    out_dir = project["output_dir"]
    img_dir = Path(out_dir) / "images"
    search_dir = img_dir / "search"
    search_dir.mkdir(parents=True, exist_ok=True)

    # 다음 버전 파일명
    pattern = _re.compile(rf"scene_{scene_num:03d}_search_(\d+)\.[^.]+")
    existing = [int(m.group(1)) for f in search_dir.iterdir() if (m := pattern.match(f.name))]
    next_idx = max(existing, default=0) + 1

    suffix = Path(file.filename or "upload.jpg").suffix.lower()
    if suffix not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        suffix = ".jpg"
    dest_name = f"scene_{scene_num:03d}_search_{next_idx:02d}{suffix}"
    dest_path = search_dir / dest_name
    dest_path.write_bytes(await file.read())

    dir_name = Path(out_dir).name
    image_url = f"/output/{dir_name}/images/search/{dest_name}"

    # image_assets.json 등록
    assets_path = img_dir / "image_assets.json"
    try:
        from auto_agent.tools.image_assets import add_version
        add_version(img_dir, scene_num, f"search/{dest_name}", "search")
    except Exception:
        pass

    # scene_specs imagePath 업데이트
    specs = _load_specs(project)
    if specs:
        for scene in specs.get("scenes", []):
            if scene["sceneNumber"] == scene_num:
                scene["imagePath"] = image_url
                ia = scene.get("imageAsset") or {}
                if ia.get("source") == "none":
                    ia.pop("source", None)
                    scene["imageAsset"] = ia
                break
        specs_path = Path(out_dir) / "scene_specs.json"
        specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    _rebuild_manifest_sync(project)
    return {"ok": True, "image_url": image_url}


@router.get("/scenes/{scene_num}/image-prompt")
async def get_scene_image_prompt(slug: str, scene_num: int):
    """씬의 imageAsset.prompt를 반환 — 생성 패널 미리채우기용."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"prompt": ""})
    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            ia = scene.get("imageAsset") or {}
            return {"prompt": ia.get("prompt", "")}
    return {"prompt": ""}


@router.get("/characters")
async def get_characters(slug: str):
    """캐릭터 패널용 — character_plan + characters 폴더 이미지 매핑."""
    import unicodedata as _ud, re as _re
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    out_dir = Path(project["output_dir"])
    dir_name = out_dir.name

    # character_plan.json 로드
    cp_path = out_dir / "character_plan.json"
    if not cp_path.exists():
        return {"characters": []}
    cp = json.loads(cp_path.read_text(encoding="utf-8"))
    char_list = cp.get("characters", [])

    # characters/ 폴더 이미지 맵 (NFC 정규화)
    char_dir = out_dir / "characters"
    char_files_by_stem: dict = {}
    if char_dir.exists():
        for f in char_dir.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                char_files_by_stem[_ud.normalize("NFC", f.stem)] = f

    # scene_specs에서 캐릭터별 등장 씬(generate 타입) 수집
    specs = _load_specs(project)
    char_gen_scenes: dict[str, list[int]] = {}
    if specs:
        for s in specs.get("scenes", []):
            ia = s.get("imageAsset") or {}
            if ia.get("source") == "generate":
                for c in s.get("characters", []):
                    char_gen_scenes.setdefault(c, []).append(s["sceneNumber"])

    result = []
    for ch in char_list:
        char_id = ch.get("name", "")
        char_key = _ud.normalize("NFC", char_id.replace(" ", "_"))
        # 이미지 매핑
        match = next((f for stem, f in char_files_by_stem.items() if stem.startswith(char_key) and "semoji_3D" in stem), None)
        if not match:
            match = char_files_by_stem.get(char_key)
        thumb_url = f"/output/{dir_name}/characters/{match.name}" if match else ""
        result.append({
            "id": ch.get("id", ""),
            "name": char_id,
            "tags": ch.get("tags", []),
            "scenes": ch.get("scenes", []),
            "gen_scenes": char_gen_scenes.get(char_id, []),
            "thumb_url": thumb_url,
            "has_image": bool(match),
        })

    return {"characters": result}


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
                data = json.loads(p.read_text(encoding="utf-8"))
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
    """에디터용 씬 데이터 — manifest 우선, scene_specs fallback."""
    import json as _json
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    # 1. manifest에서 읽기 (Remotion Studio와 동일 데이터)
    from auto_agent.paths import get_workspace_dir
    out_dir = project.get("output_dir", "")
    dir_name = Path(out_dir).name if out_dir else project.get("slug", "")
    manifest_path = get_workspace_dir() / "remotion" / "public" / "manifests" / f"{dir_name}.json"
    if manifest_path.exists():
        try:
            mdata = _json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest = mdata.get("manifest", mdata)
            for mscene in manifest.get("scenes", []):
                if mscene.get("sceneNumber") == scene_num:
                    # manifest 경로 rewrite: project/ → /output/{dir}/
                    prefix = f"/output/{dir_name}/"
                    for key in ("imagePath", "vizBackgroundPath", "audioPath", "videoPath", "videoThumbPath"):
                        val = mscene.get(key, "")
                        if val and val.startswith("project/"):
                            mscene[key] = prefix + val[len("project/"):]
                    # images[] 배열도 rewrite (person_card 등)
                    if mscene.get("images"):
                        mscene["images"] = [
                            prefix + v[len("project/"):] if v and v.startswith("project/") else v
                            for v in mscene["images"]
                        ]
                    layout = (mscene.get("visualization") or {}).get("layout", mscene.get("sceneType", ""))
                    constraints = LAYOUT_CONSTRAINTS.get(layout, {})
                    # narration/concept은 manifest에 없으므로 scene_specs에서 보강
                    if not mscene.get("narration") or not mscene.get("concept"):
                        specs = _load_specs(project)
                        if specs:
                            spec = next((s for s in specs.get("scenes", []) if s.get("sceneNumber") == scene_num), None)
                            if spec:
                                if not mscene.get("narration"):
                                    mscene["narration"] = spec.get("narration", "")
                                if not mscene.get("concept"):
                                    mscene["concept"] = spec.get("concept", "")
                    return JSONResponse(
                        {"scene": mscene, "constraints": constraints, "layout": layout},
                        headers={"Cache-Control": "no-store"},
                    )
        except Exception:
            pass

    # 2. fallback: scene_specs에서 읽기
    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            _inject_image_url(project, scene, scene_num)
            _transform_map_scene(scene)
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
        # imageAsset.source가 있으면 씬 이미지 (imagePath)
        # 없으면 시각화 배경 (vizBackgroundPath)
        has_image_asset = bool((scene.get("imageAsset") or {}).get("source"))
        if has_image_asset:
            scene["imagePath"] = url
        else:
            scene["vizBackgroundPath"] = url


def _transform_map_scene(scene: dict):
    """mapScene 좌표 변환: scene_specs [lat,lng] → MapLibre [lng,lat].

    build_manifest.py와 동일한 변환을 적용하여 스토리보드 썸네일에서도
    맵이 올바르게 렌더링되도록 한다.
    """
    ms = scene.get("mapScene")
    if not ms:
        return
    if not ms.get("mapStyle"):
        ms["mapStyle"] = "modern_clean"
    if not ms.get("mapType"):
        ms["mapType"] = "location_reveal"
    # markers 변환: {lat, lng, label} → {coordinates: [lng, lat], label}
    if ms.get("markers"):
        converted = []
        for mk in ms["markers"]:
            if "coordinates" in mk:
                converted.append(mk)
            elif "lat" in mk and "lng" in mk:
                converted.append({
                    "coordinates": [mk["lng"], mk["lat"]],
                    "label": mk.get("label", ""),
                    "style": mk.get("style", "pin"),
                })
            else:
                converted.append(mk)
        ms["markers"] = converted
    # center: [lat, lng] → [lng, lat]
    if ms.get("center") and len(ms["center"]) == 2:
        ms["center"] = [ms["center"][1], ms["center"][0]]
    # camera keyframes 자동 생성
    center_lnglat = ms.get("center", [0, 0])
    if not ms.get("camera"):
        zoom = ms.get("zoom", 5)
        dur = scene.get("durationFrames", 150)
        ms["camera"] = {
            "keyframes": [
                {"frame": 0, "center": list(center_lnglat), "zoom": max(2, zoom - 2)},
                {"frame": int(dur * 0.4), "center": list(center_lnglat), "zoom": zoom},
            ],
            "easing": "easeInOutCubic",
        }


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

    # 저장 — imageAsset은 deep merge (source:"none" 등 개별 필드 보존)
    merged = {**old_scene, **scene_data}
    old_ia = old_scene.get("imageAsset") or {}
    new_ia = scene_data.get("imageAsset")
    if new_ia is not None and old_ia:
        # old_ia 기준으로 new_ia를 덮어씀 (old에만 있는 필드 보존)
        merged["imageAsset"] = {**old_ia, **new_ia}
    scenes[target_idx] = merged
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

    # 이미지/오디오/visualization 변경 시 매니페스트 리빌드
    _MANIFEST_FIELDS = {"imagePath", "vizBackgroundPath", "imageAsset", "narration_tts", "visualization", "layout", "headline", "items"}
    # imageAsset.source 변경도 감지 (이미지 없음 처리)
    old_ia_source = (old_scene.get("imageAsset") or {}).get("source")
    new_ia_source = (scene_data.get("imageAsset") or {}).get("source")
    needs_rebuild = bool(diff.keys() & _MANIFEST_FIELDS) or (old_ia_source != new_ia_source)
    if needs_rebuild:
        _rebuild_manifest_sync(project)

    return {
        "ok": True,
        "mode": mode,
        "diff": diff,
        "warnings": warnings,
        "fixes": fix_log,
        "scene": scenes[target_idx],
    }


@router.post("/scenes/{scene_num}/split")
async def split_scene(slug: str, scene_num: int, request: Request):
    """씬 분할 — 1단계(즉시): 구조 변경 + 파일 rename + 매니페스트 재빌드."""
    import json as _json
    from datetime import datetime
    from auto_agent.tools.scene_split import apply_split_to_specs, renumber_files
    from auto_agent.tools.image_assets import _load as ia_load, _save as ia_save

    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "not found"}, status_code=404)

    out_dir = project.get("output_dir", "")
    body = await request.json()
    narration_a = (body.get("narration_a") or "").strip()
    narration_b = (body.get("narration_b") or "").strip()

    if not narration_a or not narration_b:
        return JSONResponse({"error": "narration_a, narration_b 모두 필요합니다"}, status_code=400)

    specs_path = Path(out_dir) / "scene_specs.json"
    if not specs_path.exists():
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    specs = _json.loads(specs_path.read_text(encoding="utf-8"))
    target = next((s for s in specs.get("scenes", []) if s["sceneNumber"] == scene_num), None)
    if not target:
        return JSONResponse({"error": f"씬 {scene_num} 없음"}, status_code=404)

    # 레거시 여부: 프로젝트 내 sceneId 없는 씬이 과반이면 레거시 (scene_NNN.mp3 rename 필요)
    all_scenes = specs.get("scenes", [])
    no_id_count = sum(1 for s in all_scenes if not s.get("sceneId"))
    is_legacy = no_id_count > len(all_scenes) // 2

    # 백업
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(out_dir) / f"scene_specs.bak.{ts}.json"
    bak.write_text(specs_path.read_text(encoding="utf-8"), encoding="utf-8")

    # 분할 적용
    new_specs = apply_split_to_specs(specs, scene_num, narration_a, narration_b)
    new_scene_num = scene_num + 1
    new_scene = next(s for s in new_specs["scenes"] if s["sceneNumber"] == new_scene_num)
    new_scene_id = new_scene.get("sceneId", "")

    # image_assets sceneNumber 동기화
    img_dir = Path(out_dir) / "images"
    if img_dir.exists() and (img_dir / "image_assets.json").exists():
        ia = ia_load(img_dir)
        for s in ia.get("scenes", []):
            if s["sceneNumber"] >= new_scene_num and not s.get("sceneId"):
                s["sceneNumber"] += 1
        ia_save(img_dir, ia)

    # video_assets sceneNumber 동기화
    va_path = Path(out_dir) / "video_assets.json"
    if va_path.exists():
        va = _json.loads(va_path.read_text(encoding="utf-8"))
        for s in va.get("scenes", []):
            if s.get("sceneNumber", 0) >= new_scene_num and not s.get("sceneId"):
                s["sceneNumber"] += 1
        va_path.write_text(_json.dumps(va, ensure_ascii=False, indent=2), encoding="utf-8")

    # 레거시 파일 rename
    renumber_files(Path(out_dir), from_scene=new_scene_num, is_legacy=is_legacy)

    # scene_specs 저장
    specs_path.write_text(_json.dumps(new_specs, ensure_ascii=False, indent=2), encoding="utf-8")

    # 매니페스트 재빌드 + 스튜디오용 manifest.json 갱신
    try:
        from auto_agent.scripts.build_manifest import build_manifest
        import shutil as _shutil
        storage_key = Path(out_dir).name if out_dir else f"{project.get('uuid', '')}_{slug}"
        build_manifest(str(project.get("id", "")), storage_key, out_dir)
        # remotion/public/manifest.json 갱신 (스튜디오 반영)
        from app import REMOTION_DIR
        built = REMOTION_DIR / "public" / "manifests" / f"{storage_key}.json"
        manifest_dst = REMOTION_DIR / "public" / "manifest.json"
        if built.exists():
            _shutil.copy2(str(built), str(manifest_dst))
    except Exception as e:
        print(f"[WARN] 분할 후 매니페스트 리빌드 실패: {e}")

    # 백그라운드 태스크 시작
    import asyncio as _asyncio
    from app import _bg_split_postprocess
    _asyncio.create_task(_bg_split_postprocess(slug, project, scene_num, new_scene_num))

    return JSONResponse({
        "status": "splitting",
        "scene_a": scene_num,
        "scene_b": new_scene_num,
        "scene_b_id": new_scene_id,
    })


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


@router.post("/scenes/{scene_num}/upload-video")
async def upload_scene_video(slug: str, scene_num: int, file: UploadFile = File(...)):
    """비디오 파일 드래그 업로드 → video_sources/ 복사 → video_assets.json 등록."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    out_dir = Path(project["output_dir"])
    vs_dir = out_dir / "video_sources"
    vs_dir.mkdir(parents=True, exist_ok=True)

    original_name = file.filename or f"scene_{scene_num:03d}_video.mp4"
    dest_path = vs_dir / original_name
    # 중복 파일명 처리
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        idx = 1
        while dest_path.exists():
            dest_path = vs_dir / f"{stem}_{idx}{suffix}"
            idx += 1
    dest_path.write_bytes(await file.read())

    # video_assets.json 업데이트
    va_path = out_dir / "video_assets.json"
    va_data = {"scenes": []}
    if va_path.exists():
        try:
            va_data = json.loads(va_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 해당 씬의 sceneId 조회 (분할/통합에 안전한 매핑용)
    scene_id_for_va: str | None = None
    specs_for_va = _load_specs(project) or {"scenes": []}
    for sc in specs_for_va.get("scenes", []):
        if sc.get("sceneNumber") == scene_num:
            scene_id_for_va = sc.get("sceneId")
            break

    # 기존 해당 씬 엔트리 제거 (sceneId 우선 + sceneNumber 모두) 후 새로 추가
    scenes = va_data.get("scenes", [])
    scenes = [s for s in scenes
              if not (
                  (scene_id_for_va and s.get("sceneId") == scene_id_for_va)
                  or s.get("sceneNumber") == scene_num
              )]
    scenes.append({
        "sceneId": scene_id_for_va,
        "sceneNumber": scene_num,
        "videoFile": dest_path.name,
        "startSec": 0,
        "endSec": None,
        "placement": "fullscreen",
        "opacity": 1.0,
        "volume": 0,
    })
    scenes.sort(key=lambda s: s.get("sceneNumber", 0))
    va_data["scenes"] = scenes
    va_path.write_text(json.dumps(va_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # scene_specs videoAsset 등록 + imageAsset 비활성화
    specs = _load_specs(project)
    if specs:
        for scene in specs.get("scenes", []):
            if scene["sceneNumber"] == scene_num:
                scene["videoAsset"] = {
                    "placement": "fullscreen",
                    "startSec": 0,
                    "endSec": None,
                    "opacity": 1.0,
                    "volume": 0,
                }
                scene.pop("imagePath", None)
                break
        (out_dir / "scene_specs.json").write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    _rebuild_manifest_sync(project)
    return {"ok": True, "video_file": dest_path.name}


@router.get("/videos")
async def list_videos(slug: str):
    """프로젝트 video_sources/ 파일 목록."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    out_dir = Path(project["output_dir"])
    vs_dir = out_dir / "video_sources"
    if not vs_dir.exists():
        return JSONResponse({"videos": []})
    exts = {".mp4", ".mov", ".webm", ".mkv"}
    videos = []
    for f in sorted(vs_dir.iterdir()):
        if f.suffix.lower() in exts:
            dir_name = out_dir.name
            videos.append({
                "file": f.name,
                "url": f"/output/{dir_name}/video_sources/{f.name}",
                "size": f.stat().st_size,
            })
    return JSONResponse({"videos": videos})


@router.post("/scenes/{scene_num}/set-video-trim")
async def set_video_trim(slug: str, scene_num: int, request: Request):
    """비디오 트림 구간(startSec/endSec) 및 파일 저장."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)
    body = await request.json()
    video_file = body.get("videoFile", "")
    start_sec = float(body.get("startSec", 0))
    end_sec = body.get("endSec")
    if end_sec is not None:
        end_sec = float(end_sec)

    out_dir = Path(project["output_dir"])

    # video_assets.json 업데이트
    va_path = out_dir / "video_assets.json"
    va_data = {"scenes": []}
    if va_path.exists():
        try:
            va_data = json.loads(va_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    scenes = va_data.get("scenes", [])
    entry = next((s for s in scenes if s.get("sceneNumber") == scene_num), None)
    if entry is None:
        entry = {"sceneNumber": scene_num}
        scenes.append(entry)
        scenes.sort(key=lambda s: s.get("sceneNumber", 0))
    if video_file:
        entry["videoFile"] = video_file
    entry["startSec"] = start_sec
    entry["endSec"] = end_sec
    va_data["scenes"] = scenes
    va_path.write_text(json.dumps(va_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # scene_specs.json videoAsset 동기화
    specs = _load_specs(project)
    if specs:
        for scene in specs.get("scenes", []):
            if scene["sceneNumber"] == scene_num:
                va = scene.get("videoAsset") or {}
                if video_file:
                    va["staticPath"] = video_file
                va["startSec"] = start_sec
                va["endSec"] = end_sec
                scene["videoAsset"] = va
                break
        (out_dir / "scene_specs.json").write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    _rebuild_manifest_sync(project)
    return JSONResponse({"ok": True})


@router.post("/scenes/{scene_num}/set-asset-type")
async def set_scene_asset_type(slug: str, scene_num: int, request: Request):
    """씬 에셋 타입 전환 — image(videoAsset 제거) / video(imageAsset 비활성화)."""
    project = resolve_project_by_slug(slug)
    if not project:
        return JSONResponse({"error": "프로젝트 없음"}, status_code=404)

    body = await request.json()
    asset_type = body.get("type", "image")  # "image" or "video"

    out_dir = Path(project["output_dir"])
    specs = _load_specs(project)
    if not specs:
        return JSONResponse({"error": "scene_specs.json 없음"}, status_code=404)

    for scene in specs.get("scenes", []):
        if scene["sceneNumber"] == scene_num:
            scene_id_va = scene.get("sceneId")
            # Layer 1 단일성: image/video로 전환 시 mapScene/chartConfig는 무조건 제거
            scene.pop("mapScene", None)
            scene.pop("chartConfig", None)
            if asset_type == "image":
                scene.pop("videoAsset", None)
                # video_assets.json에서도 제거 (sceneId 우선)
                va_path = out_dir / "video_assets.json"
                if va_path.exists():
                    try:
                        va_data = json.loads(va_path.read_text(encoding="utf-8"))
                        va_data["scenes"] = [
                            s for s in va_data.get("scenes", [])
                            if not (
                                (scene_id_va and s.get("sceneId") == scene_id_va)
                                or s.get("sceneNumber") == scene_num
                            )
                        ]
                        va_path.write_text(json.dumps(va_data, ensure_ascii=False, indent=2), encoding="utf-8")
                    except Exception:
                        pass
                # Layer 1 단일성: visual_kind를 image 종류로 (기존 imageAsset.source 따라)
                ia = scene.get("imageAsset") or {}
                if ia.get("source") == "search":
                    scene["visual_kind"] = "search_image"
                else:
                    # 기본: generate (작성 시 default)
                    if ia.get("source") in (None, "none"):
                        ia["source"] = "generate"
                        scene["imageAsset"] = ia
                    scene["visual_kind"] = "generate_image"
            else:
                # video 모드: Layer 1 단일성 — imageAsset 통째 제거 + visual_kind 변경
                scene.pop("imagePath", None)
                scene.pop("vizBackgroundPath", None)
                scene.pop("imageAsset", None)
                scene["visual_kind"] = "video"
                # video_assets.json에 기존 항목이 있으면 videoAsset 동기화 (sceneId 우선)
                va_path = out_dir / "video_assets.json"
                if va_path.exists() and not scene.get("videoAsset"):
                    try:
                        va_data = json.loads(va_path.read_text(encoding="utf-8"))
                        va_entry = next(
                            (s for s in va_data.get("scenes", [])
                             if (scene_id_va and s.get("sceneId") == scene_id_va)
                             or s.get("sceneNumber") == scene_num),
                            None,
                        )
                        if va_entry:
                            scene["videoAsset"] = {
                                "staticPath": va_entry.get("videoFile", va_entry.get("staticPath", "")),
                                "startSec": va_entry.get("startSec", 0),
                                "endSec": va_entry.get("endSec"),
                                "placement": va_entry.get("placement", "fullscreen"),
                                "opacity": va_entry.get("opacity", 1.0),
                                "volume": va_entry.get("volume", 0),
                            }
                    except Exception:
                        pass
                if not scene.get("videoAsset"):
                    scene["videoAsset"] = {"startSec": 0, "endSec": None}
            break

    (out_dir / "scene_specs.json").write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    _rebuild_manifest_sync(project)
    return {"ok": True, "type": asset_type}
