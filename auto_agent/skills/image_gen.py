"""
이미지 생성 스킬 (캐릭터, 씬)

LLM 불필요 — FAL.ai API 직접 호출, ThreadPoolExecutor 병렬 처리.

auto_kairos_v2/src/skills/image_gen.py에서 이식.
- generate_sub_scenes / _parallel_generate_sub_scenes 제거 (auto_agent_v2 불필요)
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..tools.image_generate import (
    generate_character,
    generate_scene,
    generate_scene_flat,
    generate_gemini_edit,
)


def _load_staging_mode(style_path: str) -> str:
    """art_style.json에서 staging_mode를 읽어 반환 (기본: cinematic)"""
    try:
        with open(style_path, "r", encoding="utf-8") as f:
            art_style = json.load(f)
        return art_style.get("staging_mode", "cinematic")
    except Exception:
        return "cinematic"


# ── 캐릭터 생성 ──

def generate_characters(
    character_plan_path: Path,
    style_path: str,
    output_dir: Path,
    log_fn=None,
) -> dict:
    """character_plan.json 기반 캐릭터 변이 이미지 병렬 생성.

    Returns:
        {"success": bool, "generated": int, "total": int, "results": dict}
    """
    log = log_fn or (lambda msg: print(f"[char_gen] {msg}"))

    if not character_plan_path.exists():
        return {"success": True, "generated": 0, "total": 0, "results": {}}

    plan = json.loads(character_plan_path.read_text(encoding="utf-8"))
    characters = plan.get("characters", [])

    # variants를 평탄화
    all_variants = []
    for ch in characters:
        person_photo = ch.get("person_photo")
        variants = ch.get("variants", [])
        if not variants:
            variants = [{"variant_id": ch["name"], "prompt_base": ch.get("prompt_base", ""),
                         "output": ch.get("output", f"characters/{ch['name']}.png"),
                         "scenes": []}]
        for v in variants:
            v["person_photo"] = person_photo
            v["character_name"] = ch["name"]
            # prompt_base → prompt 호환
            if "prompt_base" in v and "prompt" not in v:
                v["prompt"] = v["prompt_base"]
            all_variants.append(v)

    # 이미 존재하는 파일 스킵
    to_generate = []
    for v in all_variants:
        out_path = output_dir / v["output"]
        if out_path.exists():
            log(f"  스킵: {v['variant_id']}")
        else:
            to_generate.append(v)

    if not to_generate:
        return {"success": True, "generated": 0, "total": 0, "results": {}}

    log(f"캐릭터 변이 병렬 생성: {len(to_generate)}개")
    results = _parallel_generate_characters(to_generate, style_path, output_dir, log)

    ok = sum(1 for r in results.values() if r.get("success"))
    log(f"캐릭터 생성 완료: {ok}/{len(to_generate)}")

    # character_casting.json 저장
    _save_character_casting(characters, output_dir)

    return {"success": ok > 0 or len(to_generate) == 0,
            "generated": ok, "total": len(to_generate), "results": results}


def _parallel_generate_characters(variants: list, style_path: str, output_dir: Path, log_fn) -> dict:
    results = {}

    def gen_one(v):
        vid = v["variant_id"]
        t0 = time.time()
        log_fn(f"  [START] {vid}")
        try:
            person_photo = None
            if v.get("person_photo"):
                pp = output_dir / v["person_photo"]
                if pp.exists():
                    person_photo = str(pp)

            out_path = str(output_dir / v["output"])
            result = generate_character(
                prompt=v.get("prompt", v.get("prompt_base", "")),
                output_path=out_path,
                style_path=style_path,
                person_photo=person_photo,
            )
            elapsed = time.time() - t0
            ok = result.get("success", False)
            log_fn(f"  [{'OK' if ok else 'FAIL'}] {vid} ({elapsed:.1f}s)")
            return vid, result
        except Exception as e:
            elapsed = time.time() - t0
            log_fn(f"  [ERROR] {vid} ({elapsed:.1f}s) {e}")
            return vid, {"success": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(gen_one, v): v["variant_id"] for v in variants}
        for fut in as_completed(futures):
            vid, res = fut.result()
            results[vid] = res

    return results


def _save_character_casting(characters: list, output_dir: Path):
    """character_casting.json 저장"""
    casting = {"characters": []}
    for ch in characters:
        variants_info = []
        for v in ch.get("variants", []):
            out_path = output_dir / v["output"]
            variants_info.append({
                "variant_id": v["variant_id"],
                "context": v.get("label", v.get("context", "")),
                "image": str(out_path) if out_path.exists() else None,
                "scenes": v.get("scenes", []),
            })
        casting["characters"].append({
            "name": ch["name"],
            "is_real_person": ch.get("is_real_person", False),
            "person_photo": ch.get("person_photo"),
            "variants": variants_info,
        })
    casting_path = output_dir / "character_casting.json"
    casting_path.write_text(json.dumps(casting, ensure_ascii=False, indent=2), encoding="utf-8")


def regenerate_characters(
    review_path: Path,
    plan_path: Path,
    style_path: str,
    output_dir: Path,
    log_fn=None,
) -> dict:
    """리뷰 결과 기반 거부된 캐릭터 재생성.

    Returns:
        {"success": bool, "regenerated": int}
    """
    log = log_fn or (lambda msg: print(f"[char_regen] {msg}"))

    if not review_path.exists():
        return {"success": True, "regenerated": 0}

    review = json.loads(review_path.read_text(encoding="utf-8"))

    # 원본 변이 정보 조회
    plan_variants = {}
    if plan_path.exists():
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        for ch in plan.get("characters", []):
            for v in ch.get("variants", []):
                plan_variants[v["variant_id"]] = {
                    **v,
                    "person_photo": ch.get("person_photo"),
                    "character_name": ch["name"],
                }

    to_regen = []
    for r in review.get("reviews", []):
        if not r.get("approved") and r.get("regen_prompt"):
            vid = r["variant_id"]
            orig = plan_variants.get(vid, {})
            to_regen.append({
                "variant_id": vid,
                "character_name": orig.get("character_name", vid),
                "prompt": r["regen_prompt"],
                "person_photo": r.get("person_photo", orig.get("person_photo")),
                "output": r["image"],
            })

    if not to_regen:
        return {"success": True, "regenerated": 0}

    log(f"캐릭터 재생성: {len(to_regen)}개")
    for v in to_regen:
        old = output_dir / v["output"]
        if old.exists():
            old.unlink()

    results = _parallel_generate_characters(to_regen, style_path, output_dir, log)
    ok = sum(1 for r in results.values() if r.get("success"))

    return {"success": True, "regenerated": ok}


# ── 씬 이미지 생성 ──

def generate_scenes(
    scene_plan_path: Path,
    style_path: str,
    output_dir: Path,
    scenes_dir: Path,
    log_fn=None,
) -> dict:
    """scene_plan.json 기반 씬 이미지 병렬 생성.

    Returns:
        {"success": bool, "generated": int, "total": int, "results": dict}
    """
    log = log_fn or (lambda msg: print(f"[scene_gen] {msg}"))

    if not scene_plan_path.exists():
        return {"success": True, "generated": 0, "total": 0, "results": {}}

    plan = json.loads(scene_plan_path.read_text(encoding="utf-8"))
    scenes = plan.get("scenes", [])

    to_generate = []
    for sc in scenes:
        out_path = scenes_dir / f"{sc['id']}.png"
        if out_path.exists():
            log(f"  스킵: {sc['id']}")
        else:
            to_generate.append(sc)

    if not to_generate:
        return {"success": True, "generated": 0, "total": 0, "results": {}}

    staging_mode = _load_staging_mode(style_path)
    log(f"씬 이미지 병렬 생성: {len(to_generate)}개 (staging: {staging_mode})")
    results = _parallel_generate_scenes(to_generate, style_path, output_dir, scenes_dir, log, staging_mode)

    ok = sum(1 for r in results.values() if r.get("success"))
    log(f"씬 이미지 생성 완료: {ok}/{len(to_generate)}")

    return {"success": ok > 0 or len(to_generate) == 0,
            "generated": ok, "total": len(to_generate), "results": results}


def _parallel_generate_scenes(scenes: list, style_path: str, output_dir: Path, scenes_dir: Path, log_fn, staging_mode: str = "cinematic") -> dict:
    results = {}

    def gen_one(sc):
        sid = sc["id"]
        t0 = time.time()
        log_fn(f"  [START] {sid}")
        try:
            char_paths = []
            for cp in sc.get("characters", []):
                full = output_dir / cp
                if full.exists():
                    char_paths.append(str(full))

            out_path = str(scenes_dir / f"{sid}.png")
            if staging_mode == "flat":
                result = generate_scene_flat(
                    prompt=sc["prompt"],
                    output_path=out_path,
                    style_path=style_path,
                    characters=char_paths if char_paths else None,
                    characters_info=sc.get("characters_info"),
                    background=sc.get("background"),
                )
            else:
                result = generate_scene(
                    prompt=sc["prompt"],
                    output_path=out_path,
                    style_path=style_path,
                    characters=char_paths if char_paths else None,
                    characters_info=sc.get("characters_info"),
                    background=sc.get("background"),
                    camera=sc.get("camera"),
                )
            elapsed = time.time() - t0
            ok = result.get("success", False)
            log_fn(f"  [{'OK' if ok else 'FAIL'}] {sid} ({elapsed:.1f}s)")
            return sid, result
        except Exception as e:
            elapsed = time.time() - t0
            log_fn(f"  [ERROR] {sid} ({elapsed:.1f}s) {e}")
            return sid, {"success": False, "error": str(e)}

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(gen_one, sc): sc["id"] for sc in scenes}
        for fut in as_completed(futures):
            sid, res = fut.result()
            results[sid] = res

    return results


def regenerate_scenes(
    review_path: Path,
    style_path: str,
    output_dir: Path,
    scenes_dir: Path,
    log_fn=None,
) -> dict:
    """리뷰 결과 기반 거부된 씬 재생성.

    Returns:
        {"success": bool, "regenerated": int}
    """
    log = log_fn or (lambda msg: print(f"[scene_regen] {msg}"))

    if not review_path.exists():
        return {"success": True, "regenerated": 0}

    review = json.loads(review_path.read_text(encoding="utf-8"))
    to_regen = [
        {
            "id": r["id"],
            "prompt": r["regen_prompt"],
            "characters": r.get("characters", []),
            "characters_info": r.get("characters_info"),
            "background": r.get("background"),
            "camera": r.get("camera"),
        }
        for r in review.get("reviews", [])
        if not r.get("approved") and r.get("regen_prompt")
    ]

    if not to_regen:
        return {"success": True, "regenerated": 0}

    log(f"씬 재생성: {len(to_regen)}개")
    for sc in to_regen:
        old = scenes_dir / f"{sc['id']}.png"
        if old.exists():
            old.unlink()

    staging_mode = _load_staging_mode(style_path)
    results = _parallel_generate_scenes(to_regen, style_path, output_dir, scenes_dir, log, staging_mode)
    ok = sum(1 for r in results.values() if r.get("success"))

    return {"success": True, "regenerated": ok}


