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
            placement = asset.get("placement", "background")
            preferred = "1:1" if placement in ("left", "right") else "16:9"
            search_scenes.append({
                "scene_number": scene_num,
                "source": source,
                "query": asset.get("query", asset.get("subject", "")),
                "subject": asset.get("subject", ""),
                "output_path": str(out_path),
                "preferred_aspect": preferred,
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
        from auto_agent.tools.image_search import score_image
        scene_key = f"scene_{item['scene_number']:03d}"
        preferred = item.get("preferred_aspect", "16:9")
        t0 = time.time()
        try:
            source = item["source"]
            query = item["query"]

            # source_hint에 따라 우선 검색, 실패 시 워터폴
            # 스코어링 + 워터마크 필터링은 searcher 내부에서 자동 수행
            if source == "wikimedia":
                downloaded = searcher.search_and_download(query, 3, "wikimedia", preferred)
                if not downloaded:
                    downloaded = searcher.search_waterfall(query, 3, preferred)
            elif source == "search":
                try:
                    downloaded = searcher.search_and_download(query, 3, "serper", preferred)
                except ValueError:
                    downloaded = []
                if not downloaded:
                    downloaded = searcher.search_waterfall(query, 3, preferred)
            else:
                downloaded = searcher.search_waterfall(query, 3, preferred)

            if not downloaded:
                return scene_key, {"success": False, "error": "검색 결과 없음"}

            best = downloaded[0]
            best_score = score_image(best, query, preferred)
            elapsed = time.time() - t0

            if best.local_path:
                print(f"  [OK] {scene_key} ({elapsed:.1f}s) — {best.source} "
                      f"score={best_score} {best.width}x{best.height}")
                return scene_key, {
                    "success": True,
                    "path": best.local_path,
                    "source_url": best.source_page or best.image_url,
                    "source": best.source,
                    "license": best.license,
                    "title": best.title,
                    "score": best_score,
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

        placement = asset.get("placement", "background")
        standalone.append({
            "scene_number": scene_num,
            "prompt": asset.get("query", s.get("title", "")),
            "output_path": str(out_path),
            "placement": placement,
        })

    if not standalone:
        print("[Step 4] 단발 이미지 생성 대상 없음 — 스킵")
        return

    print(f"[Step 4] 단발 이미지 생성: {len(standalone)}개")
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for item in standalone:
        placement = item.get("placement", "background")
        # placement에 따라 aspect_ratio 결정
        if placement in ("left", "right"):
            aspect = "1:1"  # 인물/에셋은 정사각형
        else:
            aspect = "16:9"  # 배경은 와이드
        try:
            result = generate_scene(
                prompt=item["prompt"],
                output_path=item["output_path"],
                style_path=style_path,
                aspect_ratio=aspect,
            )
            if result.get("success"):
                ok += 1
                print(f"  [OK] scene_{item['scene_number']:03d} ({placement}, {aspect})")
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


def step_0_preflight(output_dir: Path, style_path: str, specs: dict) -> bool:
    """0단계: 프리플라이트 — 아트스타일 + 캐릭터 이미지 검증"""
    print("[Step 0] 프리플라이트 검증...")
    errors = []
    warnings = []

    # 1) 아트스타일 파일 검증
    style_file = Path(style_path)
    if not style_file.exists():
        errors.append(f"아트스타일 파일 없음: {style_path}")
        errors.append("  → 'auto-agent config set art_style <스타일경로> --project <slug>' 로 설정하세요")
        errors.append("  → 'auto-agent style list' 로 사용 가능한 스타일 목록 확인")
    else:
        try:
            style_data = json.loads(style_file.read_text(encoding="utf-8"))
            # 필수 필드 확인
            if not style_data.get("reference_image"):
                errors.append(f"아트스타일에 reference_image 없음: {style_path}")
            else:
                ref_img = Path(style_data["reference_image"])
                if not ref_img.is_absolute():
                    # 패키지 데이터 디렉토리 기준 해석
                    from auto_agent.paths import get_data_dir
                    ref_img = get_data_dir() / ref_img
                if not ref_img.exists():
                    errors.append(f"아트스타일 참조 이미지 없음: {ref_img}")
            if not style_data.get("scene_style_description"):
                warnings.append(f"아트스타일에 scene_style_description 없음 (프롬프트 품질 저하)")
            print(f"  [OK] 아트스타일: {style_data.get('name', '?')} ({style_file.name})")
        except json.JSONDecodeError as e:
            errors.append(f"아트스타일 파일 JSON 파싱 실패: {e}")

    # 2) 캐릭터 플랜 + 캐릭터 이미지 검증
    character_plan_path = output_dir / "character_plan.json"
    if not character_plan_path.exists():
        character_plan_path = PROJECT_ROOT / "character_plan.json"

    if character_plan_path.exists():
        try:
            plan = json.loads(character_plan_path.read_text(encoding="utf-8"))
            chars = plan.get("characters", [])
            print(f"  [OK] 캐릭터 플랜: {len(chars)}명")

            for char in chars:
                # 실존 인물 참조 사진 확인
                person_photo = char.get("person_photo")
                if char.get("is_real_person") and person_photo:
                    photo_path = output_dir / person_photo
                    if not photo_path.exists():
                        photo_path = PROJECT_ROOT / person_photo
                    if not photo_path.exists():
                        warnings.append(f"실존 인물 참조 사진 없음: {char.get('name', '?')} → {person_photo}")

                # 이미 생성된 캐릭터 이미지 확인
                for variant in char.get("variants", []):
                    variant_output = variant.get("output", "")
                    if variant_output:
                        variant_path = output_dir / variant_output
                        if variant_path.exists():
                            print(f"    [OK] {variant.get('variant_id', '?')}: {variant_path.name}")
        except json.JSONDecodeError as e:
            warnings.append(f"character_plan.json 파싱 실패: {e}")
    else:
        print("  [INFO] character_plan.json 없음 — 캐릭터 생성 스킵 예정")

    # 3) 이미지 에셋 필요 씬 카운트
    scenes = specs.get("scenes", [])
    generate_count = sum(1 for s in scenes if s.get("imageAsset", {}).get("source") == "generate")
    search_count = sum(1 for s in scenes if s.get("imageAsset", {}).get("source") in ("search", "wikimedia"))
    total_asset = generate_count + search_count
    print(f"  [INFO] 이미지 에셋 씬: 생성 {generate_count}개 + 검색 {search_count}개 = {total_asset}개")

    # 결과 출력
    if warnings:
        print()
        for w in warnings:
            print(f"  [WARN] {w}")

    if errors:
        print()
        for e in errors:
            print(f"  [ERROR] {e}")
        print()
        print("[Step 0] 프리플라이트 실패 — 위 오류를 해결한 뒤 다시 실행하세요.")
        return False

    print("[Step 0] 프리플라이트 통과")
    print()
    return True


def main():
    output_dir = get_project_dir()
    print(f"Output directory: {output_dir}")

    # art_style 경로 해석 (DB config 우선)
    style_path = _resolve_art_style(output_dir)

    # scene_specs.json: 프로젝트 루트
    scene_specs_path = SCENE_SPECS
    specs = _load_scene_specs(scene_specs_path)

    print(f"Scenes: {len(specs.get('scenes', []))}개")
    print()

    # Step 0: 프리플라이트 검증
    if not step_0_preflight(output_dir, style_path, specs):
        sys.exit(1)

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
