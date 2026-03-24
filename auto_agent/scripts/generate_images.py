"""
Image Asset Generation Script
통합 이미지 생성 파이프라인: 캐릭터 -> 검색 이미지 -> 씬 이미지 -> 시각화 배경

패턴: scripts/generate_tts.py와 동일한 skip-if-exists + 결과 JSON 저장

이미지 폴더 구조:
  images/
  ├── search/          <- 검색 이미지 원본 (scene_NNN.{ext})
  ├── generated/       <- AI 생성 이미지 원본 (scene_NNN.png)
  ├── viz_bg/          <- 시각화 배경
  ├── scene_NNN.png    <- 최종 이미지 (search/ 또는 generated/에서 복사)
  └── image_assets.json <- 에셋 레지스트리
"""
import json
import os
import shutil
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
        print("[Step 1] character_plan.json 없음 -- 스킵")
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
    """2단계: 이미지 검색 (wikimedia/serper/pixabay)
    검색 이미지는 images/search/ 에 저장 후 images/scene_NNN.{ext} 로 복사."""
    from auto_agent.tools.image_search import ImageSearcher

    scenes = specs.get("scenes", [])
    search_scenes = []

    for s in scenes:
        # 맵씬은 이미지 검색 불필요
        if s.get("mapScene") and (s["mapScene"].get("markers") or s["mapScene"].get("center")):
            continue
        asset = s.get("imageAsset")
        if not asset:
            continue
        source = asset.get("source", "")
        if source in ("wikimedia", "search"):
            scene_num = s.get("sceneNumber", 0)
            # 최종 이미지가 이미 있으면 스킵
            final_path = output_dir / "images" / f"scene_{scene_num:03d}.png"
            if final_path.exists():
                print(f"  [SKIP] scene_{scene_num:03d}.png (이미 존재)")
                continue
            placement = asset.get("placement", "background")
            preferred = "1:1" if placement in ("left", "right") else "16:9"
            search_scenes.append({
                "scene_number": scene_num,
                "source": source,
                "query": asset.get("query", asset.get("subject", "")),
                "subject": asset.get("subject", ""),
                "preferred_aspect": preferred,
            })

    if not search_scenes:
        print("[Step 2] 검색 대상 없음 -- 스킵")
        return {"searched": 0, "total": 0}

    print(f"[Step 2] 이미지 검색 시작: {len(search_scenes)}개")
    # 검색 이미지 전용 서브폴더
    search_dir = output_dir / "images" / "search"
    search_dir.mkdir(parents=True, exist_ok=True)  # images/ 도 자동 생성
    images_dir = search_dir.parent

    searcher = ImageSearcher(images_dir=search_dir)
    results = {}
    licenses = []

    # 씬당 후보 수
    CANDIDATES_PER_SCENE = 5

    def search_one(item):
        from auto_agent.tools.image_search import score_image
        scene_num = item["scene_number"]
        scene_key = f"scene_{scene_num:03d}"
        preferred = item.get("preferred_aspect", "16:9")
        n = CANDIDATES_PER_SCENE
        t0 = time.time()
        try:
            source = item["source"]
            query = item["query"]

            # 프로젝트 config의 search_engine 우선 적용
            config_engine = os.environ.get("SEARCH_ENGINE", "").lower()
            effective_source = source
            if config_engine == "wikimedia" and source in ("search", "wikimedia"):
                effective_source = "wikimedia"

            # source에 따라 검색, 실패 시 워터폴
            if effective_source == "wikimedia":
                downloaded = searcher.search_and_download(query, n, "wikimedia", preferred)
                # fallback: 쿼리 단순화 후 재시도
                if not downloaded and " " in query:
                    simple_query = " ".join(query.split()[:2])
                    downloaded = searcher.search_and_download(simple_query, n, "wikimedia", preferred)
                if not downloaded:
                    # fallbackQuery가 있으면 시도
                    fallback_q = item.get("fallbackQuery", "")
                    if fallback_q:
                        downloaded = searcher.search_and_download(fallback_q, n, "wikimedia", preferred)
                if not downloaded:
                    downloaded = searcher.search_waterfall(query, n, preferred)
            elif effective_source == "search":
                try:
                    downloaded = searcher.search_and_download(query, n, "serper", preferred)
                except ValueError:
                    downloaded = []
                if not downloaded:
                    downloaded = searcher.search_waterfall(query, n, preferred)
            else:
                downloaded = searcher.search_waterfall(query, n, preferred)

            if not downloaded:
                return scene_key, {"success": False, "error": "검색 결과 없음"}

            elapsed = time.time() - t0

            # 모든 후보를 scene_NNN_01 ~ _05 형식으로 저장
            candidates = []
            for rank, img in enumerate(downloaded, 1):
                if not img.local_path:
                    continue
                src = Path(img.local_path)
                ranked_name = search_dir / f"{scene_key}_{rank:02d}{src.suffix}"
                if src != ranked_name:
                    shutil.copy2(src, ranked_name)
                    src.unlink(missing_ok=True)
                img_score = score_image(img, query, preferred)
                candidates.append({
                    "rank": rank,
                    "path": str(ranked_name),
                    "filename": ranked_name.name,
                    "source": img.source,
                    "source_url": img.source_page or img.image_url,
                    "license": img.license,
                    "title": img.title,
                    "score": img_score,
                    "width": img.width,
                    "height": img.height,
                })

            if not candidates:
                return scene_key, {"success": False, "error": "다운로드 실패"}

            # 1등을 최종 이미지로 복사
            best = candidates[0]
            best_src = Path(best["path"])
            final_path = images_dir / f"{scene_key}{best_src.suffix}"
            shutil.copy2(best_src, final_path)

            # 전체 검색 결과 메타데이터 수집 (다운로드하지 않은 후보 포함)
            all_ranked_meta = []
            for rank_idx, img in enumerate(getattr(searcher, 'last_all_ranked', []), 1):
                img_score = score_image(img, query, preferred)
                all_ranked_meta.append({
                    "rank": rank_idx,
                    "title": img.title,
                    "thumbnail_url": img.thumbnail_url,
                    "image_url": img.image_url,
                    "source": img.source,
                    "source_page": img.source_page,
                    "width": img.width,
                    "height": img.height,
                    "license": img.license,
                    "score": img_score,
                    "downloaded": rank_idx <= len(candidates),
                })

            print(f"  [OK] {scene_key} ({elapsed:.1f}s) -- {best['source']} "
                  f"score={best['score']} {len(candidates)}개 다운로드 / {len(all_ranked_meta)}개 후보")
            return scene_key, {
                "success": True,
                "path": str(final_path),
                "selected_rank": 1,
                "candidates": candidates,
                "all_candidates": all_ranked_meta,
                "source_url": best["source_url"],
                "source": best["source"],
                "license": best["license"],
                "title": best["title"],
                "score": best["score"],
                "type": "search",
            }
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

    # search/ 폴더의 미사용 해시파일 정리
    _cleanup_hash_files(search_dir)

    ok = sum(1 for r in results.values() if r.get("success"))
    print(f"[Step 2] 완료: {ok}/{len(search_scenes)} 검색 성공")

    # 전체 검색 후보 메타데이터 저장 (썸네일 URL 포함)
    all_candidates_data = {}
    for key, res in results.items():
        if res.get("all_candidates"):
            all_candidates_data[key] = {
                "query": next((s["query"] for s in search_scenes if f"scene_{s['scene_number']:03d}" == key), ""),
                "selected_rank": res.get("selected_rank", 1),
                "downloaded_count": len(res.get("candidates", [])),
                "total_count": len(res["all_candidates"]),
                "candidates": res["all_candidates"],
            }
    if all_candidates_data:
        candidates_path = output_dir / "image_candidates.json"
        candidates_path.write_text(
            json.dumps(all_candidates_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        total_candidates = sum(d["total_count"] for d in all_candidates_data.values())
        print(f"[Step 2] image_candidates.json 저장: {total_candidates}개 후보 메타데이터")

    return {"searched": ok, "total": len(search_scenes), "results": results, "licenses": licenses}


def _cleanup_hash_files(search_dir: Path):
    """search/ 폴더에서 scene_NNN 형식이 아닌 해시파일 정리."""
    import re
    scene_pattern = re.compile(r"^scene_\d{3}\.")
    for f in search_dir.iterdir():
        if f.is_file() and not scene_pattern.match(f.name):
            f.unlink(missing_ok=True)


def step_3_generate_scene_images(output_dir: Path, style_path: str):
    """3단계: 씬 이미지 생성 (scene_plan.json 기반, 캐릭터 참조)
    생성 이미지는 images/generated/ 에 저장 후 images/ 로 복사."""
    from auto_agent.skills.image_gen import generate_scenes

    # 프로젝트 디렉토리 우선, 루트 폴백
    scene_plan = output_dir / "scene_plan.json"
    if not scene_plan.exists():
        scene_plan = PROJECT_ROOT / "scene_plan.json"
    if not scene_plan.exists():
        print("[Step 3] scene_plan.json 없음 -- 스킵")
        return

    # generated/ 서브폴더에 생성
    generated_dir = output_dir / "images" / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)  # images/ 도 자동 생성
    images_dir = generated_dir.parent

    print("[Step 3] 씬 이미지 생성 시작...")
    result = generate_scenes(
        scene_plan_path=scene_plan,
        style_path=style_path,
        output_dir=output_dir,
        scenes_dir=generated_dir,
    )

    # generated/ 에서 images/ 로 복사
    for f in generated_dir.glob("scene_*.png"):
        final = images_dir / f.name
        if not final.exists():
            shutil.copy2(f, final)

    print(f"[Step 3] 완료: {result.get('generated', 0)}/{result.get('total', 0)} 생성")
    return result


def step_4_generate_standalone_images(output_dir: Path, style_path: str, specs: dict):
    """4단계: 캐릭터 참조 없는 단발 씬 이미지 직접 생성
    생성 이미지는 images/generated/ 에 저장 후 images/scene_NNN.png 로 복사."""
    from auto_agent.tools.image_generate import generate_scene, generate_scene_flat

    scenes = specs.get("scenes", [])
    standalone = []

    for s in scenes:
        # 맵씬은 이미지 생성 불필요
        if s.get("mapScene") and (s["mapScene"].get("markers") or s["mapScene"].get("center")):
            continue
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
            "placement": placement,
        })

    if not standalone:
        print("[Step 4] 단발 이미지 생성 대상 없음 -- 스킵")
        return

    print(f"[Step 4] 단발 이미지 생성: {len(standalone)}개")
    images_dir = output_dir / "images"
    generated_dir = images_dir / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)

    ok = 0
    for item in standalone:
        scene_num = item["scene_number"]
        scene_key = f"scene_{scene_num:03d}"
        placement = item.get("placement", "background")

        # placement에 따라 aspect_ratio 결정
        if placement in ("left", "right"):
            aspect = "1:1"
        else:
            aspect = "16:9"

        # generated/ 서브폴더에 먼저 생성
        gen_path = str(generated_dir / f"{scene_key}.png")
        try:
            result = generate_scene(
                prompt=item["prompt"],
                output_path=gen_path,
                style_path=style_path,
                aspect_ratio=aspect,
            )
            if result.get("success"):
                ok += 1
                # 최종 images/ 폴더로 복사
                final_path = images_dir / f"{scene_key}.png"
                shutil.copy2(gen_path, final_path)
                print(f"  [OK] {scene_key} ({placement}, {aspect})")
            else:
                print(f"  [FAIL] {scene_key}: {result.get('error', '')}")
        except Exception as e:
            print(f"  [ERROR] {scene_key}: {e}")

    print(f"[Step 4] 완료: {ok}/{len(standalone)} 생성")


def step_5_generate_viz_backgrounds(output_dir: Path, style_path: str):
    """5단계: 시각화 배경 이미지 생성"""
    from auto_agent.skills.image_gen import generate_viz_backgrounds

    scene_specs_path = SCENE_SPECS

    if not Path(style_path).exists():
        print("[Step 5] art_style.json 없음 -- 스킵")
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
    print(f"[Step 6] 라이선스 저장: {len(existing)}개 항목 -> {license_path}")


def step_7_build_asset_registry(output_dir: Path, search_result: dict):
    """7단계: 이미지 에셋 레지스트리(image_assets.json) 생성.
    각 이미지의 소스 타입, 원본 경로, 스코어 등을 기록."""
    images_dir = output_dir / "images"
    search_dir = images_dir / "search"
    generated_dir = images_dir / "generated"

    assets = []

    # 검색 이미지 등록 (후보 포함)
    registered_search_scenes = set()
    search_results = (search_result or {}).get("results", {})
    for scene_key, sr in search_results.items():
        if not sr.get("success"):
            continue
        registered_search_scenes.add(scene_key)
        entry = {
            "scene": scene_key, "type": "search",
            "selected_rank": sr.get("selected_rank", 1),
            "source": sr.get("source", ""),
            "source_url": sr.get("source_url", ""),
            "license": sr.get("license", ""),
            "score": sr.get("score", 0),
            "title": sr.get("title", ""),
            "candidates": sr.get("candidates", []),
        }
        assets.append(entry)

    # search/ 폴더에 있지만 results에 없는 씬 (레거시)
    if search_dir.exists():
        import re
        base_pattern = re.compile(r"^(scene_\d{3})(?:_\d{2})?\.(.+)$")
        legacy_scenes = set()
        for f in sorted(search_dir.glob("scene_*")):
            m = base_pattern.match(f.name)
            if m:
                legacy_scenes.add(m.group(1))
        for scene_key in sorted(legacy_scenes - registered_search_scenes):
            assets.append({
                "scene": scene_key, "type": "search",
                "origin": f"images/search/{scene_key}_01.png",
            })

    # 생성 이미지 등록
    registered_scenes = {a["scene"] for a in assets}
    if generated_dir.exists():
        for f in sorted(generated_dir.glob("scene_*")):
            scene_key = f.stem
            # 이미 검색으로 등록된 씬은 스킵
            if scene_key in registered_scenes:
                continue
            registered_scenes.add(scene_key)
            assets.append({
                "scene": scene_key, "type": "generated",
                "origin": f"images/generated/{f.name}",
                "final": f"images/{f.name}",
                "source": "fal_ai",
            })

    # 최종 이미지 중 서브폴더에 원본이 없는 것 (레거시/수동 추가)
    if images_dir.exists():
        for f in sorted(images_dir.glob("scene_*")):
            if f.is_file() and f.stem not in registered_scenes:
                assets.append({
                    "scene": f.stem, "type": "unknown",
                    "origin": f"images/{f.name}",
                    "final": f"images/{f.name}",
                })

    registry = {
        "version": "1.0",
        "total": len(assets),
        "search_count": sum(1 for a in assets if a["type"] == "search"),
        "generated_count": sum(1 for a in assets if a["type"] == "generated"),
        "assets": assets,
    }

    registry_path = images_dir / "image_assets.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Step 7] 에셋 레지스트리: {len(assets)}개 항목 -> {registry_path}")


def _resolve_art_style(output_dir: Path) -> str:
    """art_style 경로 해석: resolve_art_style_path() 통합 resolve."""
    # 1) DB config -> resolve_art_style_path
    try:
        from auto_agent.db.connection import db_exists
        if db_exists():
            from auto_agent.db.project_manager import ProjectManager, resolve_art_style_path
            pm = ProjectManager()
            project = pm.get_active_project()
            if project:
                config = pm.get_config(project["id"])
                art_style = config.get("art_style", "")
                project_dir = pm.get_project_dir(project_id=project["id"])
                resolved = resolve_art_style_path(art_style, project_dir)
                if resolved:
                    return str(resolved)
    except Exception:
        pass

    # 2) 프로젝트 디렉토리 내 직접 탐색
    try:
        from auto_agent.db.project_manager import resolve_art_style_path
        for name in ["quirky_cartoon", "semoji", "lego", "stickman_cute"]:
            resolved = resolve_art_style_path(name, output_dir)
            if resolved:
                return str(resolved)
    except Exception:
        pass

    # 3) 레거시 폴백
    local = output_dir / "art_style.json"
    if local.exists():
        return str(local)
    alt = PROJECT_ROOT / "art_style.json"
    if alt.exists():
        return str(alt)
    return str(local)


def step_0_preflight(output_dir: Path, style_path: str, specs: dict) -> tuple:
    """0단계: 프리플라이트 -- 아트스타일 + 캐릭터 이미지 검증.

    Returns:
        (통과 여부, 최종 style_path) -- 자동 프로비저닝 시 경로 변경 가능
    """
    print("[Step 0] 프리플라이트 검증...")
    errors = []
    warnings = []

    # 1) 아트스타일 파일 검증 -- 중앙 참조로 resolve
    style_file = Path(style_path)
    if not style_file.exists():
        print("  [AUTO] 아트스타일 경로 resolve 시도...")
        try:
            from auto_agent.db.project_manager import resolve_art_style_path
            resolved = resolve_art_style_path(style_path)
            if resolved:
                style_path = str(resolved)
                style_file = resolved
                print(f"  [AUTO] resolve 완료: {resolved}")
        except Exception as e:
            print(f"  [AUTO] resolve 실패: {e}")

    if not style_file.exists():
        errors.append(f"아트스타일 파일 없음: {style_path}")
        errors.append("  -> 'auto-agent config set art_style <스타일경로> --project <slug>' 로 설정하세요")
        errors.append("  -> 'auto-agent style list' 로 사용 가능한 스타일 목록 확인")
    else:
        try:
            style_data = json.loads(style_file.read_text(encoding="utf-8"))
            # 필수 필드 확인
            if not style_data.get("reference_image"):
                errors.append(f"아트스타일에 reference_image 없음: {style_path}")
            else:
                ref_img = Path(style_data["reference_image"])
                if not ref_img.is_absolute():
                    # 프로젝트 폴더 기준 먼저, 없으면 패키지 데이터 기준
                    local_ref = output_dir / ref_img
                    if local_ref.exists():
                        ref_img = local_ref
                    else:
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
                        warnings.append(f"실존 인물 참조 사진 없음: {char.get('name', '?')} -> {person_photo}")

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
        print("  [INFO] character_plan.json 없음 -- 캐릭터 생성 스킵 예정")

    # 3) 이미지 에셋 필요 씬 카운트
    scenes = specs.get("scenes", [])
    generate_count = sum(1 for s in scenes if (s.get("imageAsset") or {}).get("source") == "generate")
    search_count = sum(1 for s in scenes if (s.get("imageAsset") or {}).get("source") in ("search", "wikimedia"))
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
        print("[Step 0] 프리플라이트 실패 -- 위 오류를 해결한 뒤 다시 실행하세요.")
        return False, style_path

    print("[Step 0] 프리플라이트 통과")
    print()
    return True, style_path


def main():
    # PROJECT_DIR 우선 (uuid 마이그레이션 후 정확한 경로)
    project_dir_env = os.environ.get("PROJECT_DIR")
    if project_dir_env:
        output_dir = Path(project_dir_env)
    else:
        project_slug = os.environ.get("PROJECT_NAME", "")
        if project_slug:
            # DB에서 정확한 output_dir 조회
            try:
                from auto_agent.db.project_manager import ProjectManager
                pm = ProjectManager()
                project = pm.resolve_project(project_slug)
                if project:
                    output_dir = Path(project["output_dir"])
                else:
                    output_dir = PROJECT_ROOT / "output" / project_slug
            except Exception:
                output_dir = PROJECT_ROOT / "output" / project_slug
        else:
            output_dir = get_project_dir()
    print(f"Output directory: {output_dir}")

    # art_style 경로 해석 (DB config 우선)
    style_path = _resolve_art_style(output_dir)

    # scene_specs.json: 프로젝트 루트
    scene_specs_path = SCENE_SPECS
    specs = _load_scene_specs(scene_specs_path)

    print(f"Scenes: {len(specs.get('scenes', []))}개")
    print()

    # Step 0: 프리플라이트 검증 (자동 프로비저닝으로 style_path 변경 가능)
    passed, style_path = step_0_preflight(output_dir, style_path, specs)
    if not passed:
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

    # Step 7: 에셋 레지스트리 생성
    step_7_build_asset_registry(output_dir, search_result)

    # 결과 요약
    images_dir = output_dir / "images"
    char_dir = output_dir / "characters"
    viz_dir = output_dir / "images" / "viz_bg"
    search_dir = output_dir / "images" / "search"
    generated_dir = output_dir / "images" / "generated"

    image_count = len(list(images_dir.glob("scene_*.png"))) + len(list(images_dir.glob("scene_*.jpg"))) if images_dir.exists() else 0
    char_count = len(list(char_dir.glob("*.png"))) if char_dir.exists() else 0
    viz_count = len(list(viz_dir.glob("*.png"))) if viz_dir.exists() else 0
    search_count = len(list(search_dir.glob("scene_*"))) if search_dir.exists() else 0
    gen_count = len(list(generated_dir.glob("scene_*"))) if generated_dir.exists() else 0

    summary = {
        "total_images": image_count,
        "total_characters": char_count,
        "total_viz_backgrounds": viz_count,
        "search_images": search_count,
        "generated_images": gen_count,
        "output_dir": str(output_dir),
    }

    print(f"\n=== 이미지 생성 완료 ===")
    print(f"  씬 이미지: {image_count}개 (검색: {search_count}, 생성: {gen_count})")
    print(f"  캐릭터: {char_count}개")
    print(f"  시각화 배경: {viz_count}개")

    summary_path = output_dir / "image_gen_results.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── Supabase 즉시 업로드 + 에셋 등록 ──
    _upload_assets_to_supabase(output_dir)


def _upload_assets_to_supabase(output_dir: Path):
    """생성된 이미지 에셋을 Supabase Storage에 업로드하고 assets 테이블에 등록."""
    try:
        from auto_agent.supabase_client import supabase_enabled
        if not supabase_enabled():
            return
    except ImportError:
        return

    project_slug = os.environ.get("PROJECT_NAME", "")
    if not project_slug:
        return

    try:
        from auto_agent.sync import SyncManager
        sync = SyncManager(
            project_slug=project_slug,
            project_dir=output_dir,
        )
        # 프로젝트 ID 조회
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        pm = SupabaseProjectManager()
        project = pm.get_project(slug=project_slug)
        if not project:
            return
        pid = project["id"]
    except Exception as e:
        print(f"  [SYNC] Supabase 초기화 실패: {e}")
        return

    from auto_agent.progress import report

    images_dir = output_dir / "images"
    uploaded = 0

    # 씬 이미지 업로드
    if images_dir.exists():
        for img in sorted(images_dir.glob("scene_*")):
            if not img.is_file():
                continue
            # scene_NNN 에서 씬 번호 추출
            import re
            m = re.match(r"scene_(\d{3})", img.stem)
            scene_num = int(m.group(1)) if m else None
            try:
                url = sync.register_asset(
                    project_id=pid,
                    local_path=img,
                    asset_type="image",
                    scene_number=scene_num,
                )
                uploaded += 1
                report("Image Generator", f"씬 {scene_num} 이미지 업로드 완료", level="success")
            except Exception as e:
                report("Image Generator", f"씬 {scene_num} 업로드 실패: {e}", level="warning")

    # 캐릭터 이미지 업로드
    char_dir = output_dir / "characters"
    if char_dir.exists():
        for img in sorted(char_dir.glob("*.png")):
            try:
                sync.register_asset(
                    project_id=pid,
                    local_path=img,
                    asset_type="character",
                )
                uploaded += 1
            except Exception:
                pass

    # 시각화 배경 업로드
    viz_dir = output_dir / "images" / "viz_bg"
    if viz_dir.exists():
        for img in sorted(viz_dir.glob("*.png")):
            m = re.match(r"scene_(\d{3})", img.stem)
            scene_num = int(m.group(1)) if m else None
            try:
                sync.register_asset(
                    project_id=pid,
                    local_path=img,
                    asset_type="viz_bg",
                    scene_number=scene_num,
                )
                uploaded += 1
            except Exception:
                pass

    print(f"\n  [SYNC] Supabase 에셋 업로드 완료: {uploaded}개")


if __name__ == "__main__":
    main()
