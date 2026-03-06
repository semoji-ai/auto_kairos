"""
Image Asset Generation Script
통합 이미지 생성 파이프라인: 캐릭터 → 검색 이미지 → 씬 이미지 → 시각화 배경

패턴: scripts/generate_tts.py와 동일한 skip-if-exists + 결과 JSON 저장
"""
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

# Load .env
from auto_agent.paths import get_workspace_dir; load_dotenv(get_workspace_dir() / ".env")

from auto_agent.scripts.project_paths import PROJECT_ROOT, get_project_dir, get_scene_specs_path

SCENE_SPECS = get_scene_specs_path()


def _load_scene_specs(path: Path) -> dict:
    """scene_specs.json 로드"""
    if not path.exists():
        print(f"ERROR: {path} not found")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def step_1_generate_characters(output_dir: Path, style_path: str):
    """1단계: 캐릭터 생성 (character_plan.json 기반)"""
    from auto_agent.skills.image_gen import generate_characters

    # 프로젝트 디렉토리 우선, 루트 폴백
    character_plan = output_dir / "character_plan.json"
    if not character_plan.exists():
        character_plan = PROJECT_ROOT / "character_plan.json"
    if not character_plan.exists():
        print("[Step 1] character_plan.json 없음 — 스킵")
        return

    print("[Step 1] 캐릭터 생성 시작...")
    result = generate_characters(
        character_plan_path=character_plan,
        style_path=style_path,
        output_dir=output_dir,
    )
    print(f"[Step 1] 완료: {result.get('generated', 0)}/{result.get('total', 0)} 생성")
    return result


def step_2_search_images(output_dir: Path, specs: dict):
    """2단계: 이미지 검색 (wikimedia/serper/pixabay)"""
    from auto_agent.tools.image_search import ImageSearcher

    scenes = specs.get("scenes", [])
    search_scenes = []

    for s in scenes:
        asset = s.get("imageAsset")
        if not asset:
            continue
        source = asset.get("source", "")
        if source in ("wikimedia", "search"):
            scene_num = s.get("sceneNumber", 0)
            out_path = output_dir / "images" / f"scene_{scene_num:03d}.png"
            if out_path.exists():
                print(f"  [SKIP] scene_{scene_num:03d}.png (이미 존재)")
                continue
            search_scenes.append({
                "scene_number": scene_num,
                "source": source,
                "query": asset.get("query", asset.get("subject", "")),
                "subject": asset.get("subject", ""),
                "output_path": str(out_path),
            })

    if not search_scenes:
        print("[Step 2] 검색 대상 없음 — 스킵")
        return {"searched": 0, "total": 0}

    print(f"[Step 2] 이미지 검색 시작: {len(search_scenes)}개")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    searcher = ImageSearcher(images_dir=images_dir)
    results = {}
    licenses = []

    def search_one(item):
        scene_key = f"scene_{item['scene_number']:03d}"
        t0 = time.time()
        try:
            source = item["source"]
            query = item["query"]

            # source_hint에 따라 우선 검색, 실패 시 워터폴
            if source == "wikimedia":
                downloaded = searcher.search_and_download(query, 3, "wikimedia")
                if not downloaded:
                    downloaded = searcher.search_waterfall(query, 3)
            elif source == "search":
                try:
                    downloaded = searcher.search_and_download(query, 3, "serper")
                except ValueError:
                    downloaded = []
                if not downloaded:
                    downloaded = searcher.search_waterfall(query, 3)
            else:
                downloaded = searcher.search_waterfall(query, 3)

            if not downloaded:
                return scene_key, {"success": False, "error": "검색 결과 없음"}

            best = downloaded[0]
            elapsed = time.time() - t0

            if best.local_path:
                print(f"  [OK] {scene_key} ({elapsed:.1f}s) — {best.source}")
                return scene_key, {
                    "success": True,
                    "path": best.local_path,
                    "source_url": best.source_page or best.image_url,
                    "source": best.source,
                    "license": best.license,
                    "title": best.title,
                }
            else:
                print(f"  [FAIL] {scene_key} ({elapsed:.1f}s) — 다운로드 실패")
                return scene_key, {"success": False, "error": "다운로드 실패"}
        except Exception as e:
            elapsed = time.time() - t0
            print(f"  [ERROR] {scene_key} ({elapsed:.1f}s) {e}")
            return scene_key, {"success": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(search_one, item): item["scene_number"] for item in search_scenes}
        for fut in as_completed(futures):
            key, res = fut.result()
            results[key] = res
            if res.get("success"):
                licenses.append({
                    "scene": key,
                    "source_url": res.get("source_url"),
                    "source": res.get("source"),
                    "license": res.get("license"),
                    "title": res.get("title"),
                })

    ok = sum(1 for r in results.values() if r.get("success"))
    print(f"[Step 2] 완료: {ok}/{len(search_scenes)} 검색 성공")

    return {"searched": ok, "total": len(search_scenes), "results": results, "licenses": licenses}


def step_3_generate_scene_images(output_dir: Path, style_path: str):
    """3단계: 씬 이미지 생성 (scene_plan.json 기반, 캐릭터 참조)"""
    from auto_agent.skills.image_gen import generate_scenes

    # 프로젝트 디렉토리 우선, 루트 폴백
    scene_plan = output_dir / "scene_plan.json"
    if not scene_plan.exists():
        scene_plan = PROJECT_ROOT / "scene_plan.json"
    if not scene_plan.exists():
        print("[Step 3] scene_plan.json 없음 — 스킵")
        return

    scenes_dir = output_dir / "images"
    scenes_dir.mkdir(parents=True, exist_ok=True)

    print("[Step 3] 씬 이미지 생성 시작...")
    result = generate_scenes(
        scene_plan_path=scene_plan,
        style_path=style_path,
        output_dir=output_dir,
        scenes_dir=scenes_dir,
    )
    print(f"[Step 3] 완료: {result.get('generated', 0)}/{result.get('total', 0)} 생성")
    return result


def step_4_generate_standalone_images(output_dir: Path, style_path: str, specs: dict):
    """4단계: 캐릭터 참조 없는 단발 씬 이미지 직접 생성"""
    from auto_agent.tools.image_generate import generate_scene, generate_scene_flat

    scenes = specs.get("scenes", [])
    standalone = []

    for s in scenes:
        asset = s.get("imageAsset")
        if not asset:
            continue
        source = asset.get("source", "")
        if source != "generate":
            continue
        placement = asset.get("placement", "")
        if placement == "background":
            continue  # 배경은 step 5에서 처리

        scene_num = s.get("sceneNumber", 0)
        out_path = output_dir / "images" / f"scene_{scene_num:03d}.png"
        if out_path.exists():
            print(f"  [SKIP] scene_{scene_num:03d}.png (이미 존재)")
            continue

        # scene_plan.json에서 이미 생성된 경우 스킵
        scene_plan = output_dir / "scene_plan.json"
        if not scene_plan.exists():
            scene_plan = PROJECT_ROOT / "scene_plan.json"
        if scene_plan.exists():
            plan = json.loads(scene_plan.read_text(encoding="utf-8"))
            plan_ids = {sc["id"] for sc in plan.get("scenes", [])}
            if f"scene_{scene_num:03d}" in plan_ids:
                continue

        standalone.append({
            "scene_number": scene_num,
            "prompt": asset.get("query", s.get("title", "")),
            "output_path": str(out_path),
        })

    if not standalone:
        print("[Step 4] 단발 이미지 생성 대상 없음 — 스킵")
        return

    print(f"[Step 4] 단발 이미지 생성: {len(standalone)}개")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for item in standalone:
        try:
            result = generate_scene(
                prompt=item["prompt"],
                output_path=item["output_path"],
                style_path=style_path,
            )
            if result.get("success"):
                ok += 1
                print(f"  [OK] scene_{item['scene_number']:03d}")
            else:
                print(f"  [FAIL] scene_{item['scene_number']:03d}: {result.get('error', '')}")
        except Exception as e:
            print(f"  [ERROR] scene_{item['scene_number']:03d}: {e}")

    print(f"[Step 4] 완료: {ok}/{len(standalone)} 생성")


def step_5_generate_viz_backgrounds(output_dir: Path, style_path: str):
    """5단계: 시각화 배경 이미지 생성"""
    from auto_agent.skills.image_gen import generate_viz_backgrounds

    scene_specs_path = SCENE_SPECS

    if not Path(style_path).exists():
        print("[Step 5] art_style.json 없음 — 스킵")
        return

    print("[Step 5] 시각화 배경 생성 시작...")
    result = generate_viz_backgrounds(
        scene_specs_path=scene_specs_path,
        style_path=style_path,
        output_dir=output_dir,
    )
    print(f"[Step 5] 완료: {result.get('generated', 0)}/{result.get('total', 0)} 생성")
    return result


def step_6_save_licenses(output_dir: Path, search_licenses: list):
    """6단계: 라이선스 메타데이터 저장"""
    if not search_licenses:
        return

    license_path = output_dir / "image_licenses.json"

    # 기존 라이선스 병합
    existing = []
    if license_path.exists():
        existing = json.loads(license_path.read_text(encoding="utf-8"))

    existing_keys = {e.get("scene") for e in existing}
    for lic in search_licenses:
        if lic.get("scene") not in existing_keys:
            existing.append(lic)

    license_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Step 6] 라이선스 저장: {len(existing)}개 항목 → {license_path}")


def _resolve_art_style(output_dir: Path) -> str:
    """art_style 경로 해석: DB config → 프로젝트 디렉토리 → 루트 폴백."""
    # 1) DB config
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            project = pm.get_active_project()
            if project:
                path = pm.get_art_style_path(project["id"])
                if path:
                    return path
    except Exception:
        pass

    # 2) 프로젝트 디렉토리 내
    local = output_dir / "art_style.json"
    if local.exists():
        return str(local)

    # 3) 루트 폴백
    alt = PROJECT_ROOT / "art_style.json"
    if alt.exists():
        return str(alt)

    return str(local)  # 존재하지 않아도 경로 반환 (이후 경고)


def main():
    output_dir = get_project_dir()
    print(f"Output directory: {output_dir}")

    # art_style 경로 해석 (DB config 우선)
    style_path = _resolve_art_style(output_dir)
    if not Path(style_path).exists():
        print("WARNING: art_style.json 없음 — 캐릭터/씬/배경 생성 불가")

    # scene_specs.json: 프로젝트 루트
    scene_specs_path = SCENE_SPECS
    specs = _load_scene_specs(scene_specs_path)

    print(f"Scenes: {len(specs.get('scenes', []))}개")
    print()

    # Step 1: 캐릭터 생성 (캐릭터가 씬의 입력이므로 먼저)
    step_1_generate_characters(output_dir, style_path)
    print()

    # Step 2: 이미지 검색 (wikimedia/serper/pixabay)
    search_result = step_2_search_images(output_dir, specs) or {}
    search_licenses = search_result.get("licenses", [])
    print()

    # Step 3: 씬 이미지 생성 (캐릭터 참조 포함)
    step_3_generate_scene_images(output_dir, style_path)
    print()

    # Step 4: 캐릭터 참조 없는 단발 이미지 직접 생성
    step_4_generate_standalone_images(output_dir, style_path, specs)
    print()

    # Step 5: 시각화 배경 생성
    step_5_generate_viz_backgrounds(output_dir, style_path)
    print()

    # Step 6: 라이선스 메타데이터 저장
    step_6_save_licenses(output_dir, search_licenses)

    # 결과 요약
    images_dir = output_dir / "images"
    char_dir = output_dir / "characters"
    viz_dir = output_dir / "images" / "viz_bg"

    image_count = len(list(images_dir.glob("scene_*.png"))) if images_dir.exists() else 0
    char_count = len(list(char_dir.glob("*.png"))) if char_dir.exists() else 0
    viz_count = len(list(viz_dir.glob("*.png"))) if viz_dir.exists() else 0

    summary = {
        "total_images": image_count,
        "total_characters": char_count,
        "total_viz_backgrounds": viz_count,
        "output_dir": str(output_dir),
    }

    print(f"\n=== 이미지 생성 완료 ===")
    print(f"  씬 이미지: {image_count}개")
    print(f"  캐릭터: {char_count}개")
    print(f"  시각화 배경: {viz_count}개")

    summary_path = output_dir / "image_gen_results.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
