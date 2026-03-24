"""
위키미디어 검색 CLI 도구.

에이전트가 Bash로 호출:
    python3 -m auto_agent.tools.wikimedia_search "query" [limit]

JSON 출력: 썸네일 URL, 원본 URL, 크기, 라이선스 포함.
"""
import json
import sys
import requests

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "KairosAgent/3.1 (educational video production)"}


def search_wikimedia(query: str, limit: int = 8) -> list:
    """위키미디어 커먼즈 검색. 썸네일 + 원본 URL 반환."""
    try:
        resp = requests.get(COMMONS_API, params={
            "action": "query",
            "generator": "search",
            "gsrsearch": query,
            "gsrnamespace": "6",  # File namespace
            "gsrlimit": str(limit),
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": "800",  # 미리보기용 썸네일
            "format": "json",
        }, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return [{"error": str(e)}]

    pages = data.get("query", {}).get("pages", {})
    results = []
    for pid, page in pages.items():
        info = page.get("imageinfo", [{}])[0]
        meta = info.get("extmetadata", {})

        # 라이선스 추출
        license_short = meta.get("LicenseShortName", {}).get("value", "unknown")
        description = meta.get("ImageDescription", {}).get("value", "")
        # HTML 태그 제거
        import re
        description = re.sub(r'<[^>]+>', '', description)[:200]

        # 원본 URL에서 1920px 썸네일 URL 생성
        original_url = info.get("url", "")
        thumb_url = info.get("thumburl", "")

        # 1920px 썸네일 URL 생성
        thumb_1920 = ""
        if thumb_url and "/thumb/" in thumb_url:
            # .../thumb/a/aa/file.jpg/800px-file.jpg → .../thumb/a/aa/file.jpg/1920px-file.jpg
            parts = thumb_url.rsplit("/", 1)
            if len(parts) == 2:
                filename_part = parts[1]
                # 800px- 를 1920px- 로 교체
                import re as _re
                new_filename = _re.sub(r'^\d+px-', '1920px-', filename_part)
                thumb_1920 = parts[0] + "/" + new_filename

        results.append({
            "title": page.get("title", "").replace("File:", ""),
            "thumbnail_url": thumb_url,
            "thumbnail_1920_url": thumb_1920,
            "original_url": original_url,
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "thumb_width": info.get("thumbwidth", 0),
            "thumb_height": info.get("thumbheight", 0),
            "mime": info.get("mime", ""),
            "size_bytes": info.get("size", 0),
            "license": license_short,
            "description": description,
        })

    # 해상도 순으로 정렬 (큰 것 우선)
    results.sort(key=lambda x: x["width"] * x["height"], reverse=True)
    return results


def download_image(url: str, output_path: str) -> dict:
    """이미지 다운로드. 원본 또는 1920px 썸네일."""
    import time
    try:
        # rate limit 방지 재시도
        for attempt in range(3):
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 429:
                wait = 3 * (attempt + 1)
                print(f"429 rate limit, {wait}초 대기...", file=sys.stderr)
                time.sleep(wait)
                continue
            resp.raise_for_status()

            from pathlib import Path
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(resp.content)
            return {
                "success": True,
                "path": str(out),
                "size_bytes": len(resp.content),
            }
        return {"success": False, "error": "429 rate limit 3회 초과"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def save_candidates(scene_number: int, query: str, candidates: list, images_dir: str):
    """검색 후보를 image_candidates.json에 자동 저장."""
    from pathlib import Path
    path = Path(images_dir) / "image_candidates.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = {"scenes": []}
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 기존 씬 데이터 업데이트 또는 추가
    scenes = existing.get("scenes", [])
    updated = False
    for s in scenes:
        if s.get("sceneNumber") == scene_number:
            s["query"] = query
            s["candidates"] = candidates
            updated = True
            break
    if not updated:
        scenes.append({
            "sceneNumber": scene_number,
            "query": query,
            "selected": 0,
            "candidates": candidates,
        })

    existing["scenes"] = sorted(scenes, key=lambda x: x.get("sceneNumber", 0))
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: wikimedia_search <query> [limit] [--scene N] [--save-dir path]"}))
        sys.exit(1)

    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else 8

    # --scene N --save-dir path 옵션 파싱
    scene_num = None
    save_dir = None
    for i, arg in enumerate(sys.argv):
        if arg == "--scene" and i + 1 < len(sys.argv):
            scene_num = int(sys.argv[i + 1])
        if arg == "--save-dir" and i + 1 < len(sys.argv):
            save_dir = sys.argv[i + 1]

    if query.startswith("download:"):
        # 다운로드 모드: download:<url> <output_path>
        url = query[len("download:"):]
        import tempfile
        output_path = sys.argv[2] if len(sys.argv) > 2 else str(Path(tempfile.gettempdir()) / "download.jpg")
        result = download_image(url, output_path)
        print(json.dumps(result, ensure_ascii=False))
    else:
        # 검색 모드
        results = search_wikimedia(query, limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        # 자동 저장 (--scene, --save-dir 옵션 있을 때)
        if scene_num is not None and save_dir:
            save_candidates(scene_num, query, results, save_dir)
            print(f"[SAVED] image_candidates.json에 씬{scene_num} 후보 {len(results)}개 저장", file=sys.stderr)


def check_art_style() -> dict:
    import os
    """프로젝트 아트스타일 확인 + 없으면 복제."""
    import shutil
    project_name = os.environ.get("PROJECT_NAME", "")
    if not project_name:
        return {"error": "PROJECT_NAME 미설정"}

    try:
        from auto_agent.paths import get_workspace_dir
        ws = get_workspace_dir()
    except ImportError:
        ws = Path.cwd()

    project_dir = ws / "output" / project_name

    # DB에서 config 읽기
    try:
        from auto_agent.db.project_manager import ProjectManager
        from auto_agent.db.connection import db_exists, init_db
        if not db_exists():
            init_db()
        pm = ProjectManager()
        project = pm.get_project(slug=project_name)
        config = project.get("config", {}) if project else {}
        if isinstance(config, str):
            import json as _j
            config = _j.loads(config)
    except Exception:
        config = {}

    art_style_rel = config.get("art_style", "")
    if not art_style_rel:
        return {"has_style": False, "reason": "config에 art_style 미설정"}

    style_path = ws / art_style_rel
    if not style_path.exists():
        return {"has_style": False, "reason": f"{art_style_rel} 파일 없음"}

    # 프로젝트에 복제
    project_art = project_dir / "artstyle"
    if not project_art.exists():
        project_art.mkdir(parents=True, exist_ok=True)
        shutil.copy(style_path, project_art / style_path.name)
        for ref in style_path.parent.glob(f"{style_path.stem}*"):
            if ref != style_path:
                shutil.copy(ref, project_art / ref.name)

    import json as _json
    try:
        data = _json.loads(style_path.read_text(encoding="utf-8"))
    except Exception:
        data = {}

    return {
        "has_style": True,
        "art_style": art_style_rel,
        "name": data.get("name", ""),
        "style_path": str(style_path),
        "project_art_dir": str(project_art),
    }
