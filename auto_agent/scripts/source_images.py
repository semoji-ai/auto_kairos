"""
이미지 소싱 스크립트 — 검색/생성 병렬 실행.

source별로 분류:
  - search 씬 → 위키미디어 검색 → Sonnet 판단 → 다운로드
  - generate 씬 → 캐릭터 분석 → 캐릭터 생성 → FAL.ai 씬 이미지 생성
두 트랙이 병렬 실행.
"""
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def phase_a_character_analysis(scene_specs: dict, output_dir: Path, style_path: str = None) -> Optional[Path]:
    """generate 씬에서 2씬+ 등장 캐릭터 식별 → character_plan.json 생성."""
    scenes = scene_specs.get("scenes", [])
    gen_scenes = [
        s for s in scenes
        if s.get("imageAsset", {}).get("source") == "generate"
        or s.get("visualization", {}).get("creative", {}).get("layout") == "cinematic"
    ]
    if not gen_scenes:
        print("[Phase A] generate 씬 없음 — 캐릭터 분석 스킵")
        return None

    person_scenes = {}
    for scene in gen_scenes:
        sn = scene.get("sceneNumber", 0)
        profile = scene.get("visualization", {}).get("profileName")
        if profile:
            person_scenes.setdefault(profile, []).append(sn)

    recurring = {name: sns for name, sns in person_scenes.items() if len(sns) >= 2}
    if not recurring:
        print("[Phase A] 2씬+ 등장 캐릭터 없음 — 캐릭터 생성 스킵")
        return None

    characters = []
    for name, sns in recurring.items():
        characters.append({
            "name": name, "name_en": "", "is_real_person": True,
            "variants": [{
                "variant_id": name.replace(" ", "_").lower(),
                "label": f"{name} 기본", "scenes": sns,
                "visual_guide": {}, "prompt_base": "",
                "output": f"characters/{name.replace(' ', '_').lower()}.png"
            }]
        })

    plan = {"characters": characters}
    plan_path = output_dir / "character_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Phase A] character_plan.json 생성: {len(characters)}명")
    return plan_path


# ═══════════════════════════════════════════
# 검색 트랙 (search 씬)
# ═══════════════════════════════════════════

def _run_search_track(search_scenes: list, img_dir: Path, project_dir: Path, log_fn):
    """search 씬: 위키미디어 검색 → Sonnet 판단 → 다운로드."""
    if not search_scenes:
        return 0

    from auto_agent.tools.wikimedia_search import search_wikimedia, save_candidates, download_image
    from auto_agent.tools.image_assets import add_version, next_filename

    log_fn("image-search", f"검색 트랙 시작: {len(search_scenes)}씬")

    # Step 1: 위키미디어 검색
    search_results = {}
    for scene in search_scenes:
        sn = scene.get("sceneNumber")
        img = scene.get("imageAsset") or {}
        query = img.get("searchQuery") or img.get("query", "")
        if not query:
            continue

        existing = list(img_dir.glob(f"scene_{sn:03d}.*")) + list(img_dir.glob(f"scene_{sn:03d}_*.*"))
        if any(f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") for f in existing):
            log_fn("image-search", f"씬{sn} 이미 존재 → 스킵")
            continue

        candidates = search_wikimedia(query, 8)
        # fallback 검색
        if not candidates:
            fallback = img.get("fallbackQuery", "")
            if fallback:
                log_fn("image-search", f"씬{sn} 0건 → fallback: \"{fallback[:40]}\"")
                candidates = search_wikimedia(fallback, 8)
        search_results[sn] = candidates
        save_candidates(sn, query, candidates, str(img_dir))
        log_fn("image-search", f"씬{sn} 검색: \"{query[:40]}\" → {len(candidates)}건")
        time.sleep(0.5)

    if not search_results:
        log_fn("image-search", "검색 대상 없음", "success")
        return 0

    # Step 2: Sonnet 판단
    log_fn("image-search", "Sonnet에게 최적 이미지 선택 요청...")
    selections = _sonnet_judge(search_scenes, search_results)
    log_fn("image-search", f"Sonnet 판단 완료: {len(selections)}씬")

    # Step 3: 다운로드
    downloaded = 0
    for sel in selections:
        sn = sel.get("scene")
        action = sel.get("action", "skip")
        if action == "download":
            idx = sel.get("index", 0)
            candidates = search_results.get(sn, [])
            if idx < len(candidates):
                c = candidates[idx]
                url = c.get("thumbnail_1920_url", "") or c.get("original_url", "")
                if not url:
                    continue
                fname = next_filename(img_dir, sn, "search", Path(url).suffix or ".jpg")
                log_fn("image-search", f"씬{sn} 다운로드 중: {c.get('title', '')[:30]}")
                result = download_image(url, str(img_dir / fname))
                if result.get("success"):
                    add_version(img_dir, sn, fname, "search",
                                title=c.get("title", ""), license=c.get("license", ""),
                                source_url=url)
                    downloaded += 1
                    log_fn("image-search", f"씬{sn} 다운로드 완료 ✓", "success")
                else:
                    log_fn("image-search", f"씬{sn} 다운로드 실패", "warning")
                time.sleep(3)

    log_fn("image-search", f"검색 트랙 완료: {downloaded}건 다운로드", "success")
    return downloaded


def _sonnet_judge(scenes: list, search_results: dict) -> list:
    """Sonnet 1회 호출로 search 씬의 최적 이미지 선택."""
    prompt = "각 씬에 가장 적합한 이미지를 선택하세요.\n\n"
    prompt += "규칙:\n- 16:9 가로형, 1280px 이상 우선\n- 부적합하면 skip\n\n"

    for scene in scenes:
        sn = scene.get("sceneNumber")
        if sn not in search_results:
            continue
        title = scene.get("title", "")
        narration = scene.get("narration", "")[:100]
        prompt += f"## 씬{sn}: {title}\n나레이션: {narration}\n"
        for i, c in enumerate(search_results.get(sn, [])):
            prompt += f"  [{i}] {c.get('title','')} ({c.get('width',0)}x{c.get('height',0)})\n"
        prompt += "\n"

    prompt += 'JSON으로만 답하세요: {"selections": [{"scene": 1, "action": "download", "index": 0}, {"scene": 2, "action": "skip"}]}\n'

    try:
        import re
        cli_path = str(Path.home() / ".local/bin/claude")
        proc = subprocess.run(
            [cli_path, "--print", "--output-format", "json",
             "--model", "claude-sonnet-4-5-20250929", "--max-turns", "1"],
            input=prompt, capture_output=True, text=True, timeout=180,
            env={**os.environ, "CLAUDECODE": ""},
        )
        result_text = proc.stdout.strip()
        try:
            cli_out = json.loads(result_text)
            if isinstance(cli_out, dict) and "result" in cli_out:
                result_text = cli_out["result"]
                if isinstance(result_text, list):
                    result_text = " ".join(b.get("text", "") for b in result_text if isinstance(b, dict))
        except json.JSONDecodeError:
            pass
        md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', result_text, re.DOTALL)
        if md_match:
            result_text = md_match.group(1)
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result_text[start:end]).get("selections", [])
    except Exception:
        pass
    return []


# ═══════════════════════════════════════════
# 생성 트랙 (generate 씬)
# ═══════════════════════════════════════════

def _run_generate_track(gen_scenes: list, img_dir: Path, project_dir: Path, specs: dict, log_fn):
    """generate 씬: 캐릭터 분석 → 캐릭터 생성 → FAL.ai 씬 이미지 생성."""
    if not gen_scenes:
        return 0

    from auto_agent.tools.image_assets import add_version, next_filename

    log_fn("image-gen", f"생성 트랙 시작: {len(gen_scenes)}씬")

    # 1. 캐릭터 분석 + 생성
    character_plan_path = project_dir / "character_plan.json"
    if not character_plan_path.exists():
        phase_a_character_analysis(specs, project_dir)

    # 캐릭터 이미지 경로 수집 (생성된 캐릭터가 있으면)
    character_images = {}
    if character_plan_path.exists():
        try:
            plan = json.loads(character_plan_path.read_text(encoding="utf-8"))
            for ch in plan.get("characters", []):
                for v in ch.get("variants", []):
                    char_path = project_dir / v.get("output", "")
                    if char_path.exists():
                        for sn in v.get("scenes", []):
                            character_images.setdefault(sn, []).append(str(char_path))
        except Exception:
            pass

    # 2. 아트스타일 경로
    try:
        from auto_agent.db.project_manager import resolve_art_style_path
        config = {}
        try:
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            slug = os.environ.get("PROJECT_NAME", project_dir.name)
            proj = pm.resolve_project(slug)
            if proj:
                cfg = proj.get("config", {})
                config = json.loads(cfg) if isinstance(cfg, str) else cfg
        except Exception:
            pass
        art_style = config.get("art_style", "")
        style_path = resolve_art_style_path(art_style)
        style_arg = str(style_path) if style_path else ""
    except Exception:
        style_arg = ""

    # 3. 씬별 이미지 생성
    generated = 0
    for scene in gen_scenes:
        sn = scene.get("sceneNumber")
        img = scene.get("imageAsset") or {}
        prompt = img.get("query", "")
        if not prompt:
            continue

        # 이미 이미지 있으면 스킵
        existing = list(img_dir.glob(f"scene_{sn:03d}.*")) + list(img_dir.glob(f"scene_{sn:03d}_*.*"))
        if any(f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") for f in existing):
            log_fn("image-gen", f"씬{sn} 이미 존재 → 스킵")
            continue

        fname = next_filename(img_dir, sn, "gen", ".png")
        log_fn("image-gen", f"씬{sn} 생성 중: {prompt[:50]}...")

        cmd = [sys.executable, "-m", "auto_agent.tools.image_generate", "scene",
               "--prompt", prompt, "--output", str(img_dir / fname),
               "--aspect-ratio", "16:9"]
        if style_arg:
            cmd.extend(["--style", style_arg])

        # 캐릭터 참조 첨부
        chars = character_images.get(sn, [])
        if chars:
            cmd.extend(["--characters", ",".join(chars)])

        try:
            ws = str(project_dir.parent.parent) if "output" in str(project_dir) else str(project_dir)
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=ws)
            if result.returncode == 0:
                add_version(img_dir, sn, fname, "generate", prompt=prompt[:200],
                            art_style=style_arg)
                generated += 1
                log_fn("image-gen", f"씬{sn} 생성 완료 ✓", "success")
            else:
                err = result.stderr[:200] or result.stdout[:200]
                log_fn("image-gen", f"씬{sn} 생성 실패: {err}", "warning")
        except Exception as e:
            log_fn("image-gen", f"씬{sn} 생성 에러: {e}", "error")

    log_fn("image-gen", f"생성 트랙 완료: {generated}건 생성", "success")
    return generated


# ═══════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════

def run(project_dir: str):
    project_dir = Path(project_dir)
    load_dotenv(project_dir.parent.parent / ".env")

    specs_path = project_dir / "scene_specs.json"
    if not specs_path.exists():
        print("[ERROR] scene_specs.json 없음")
        return

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scenes = specs.get("scenes", [])
    dir_name = project_dir.name

    img_dir = project_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    progress_file = project_dir / ".progress_step_8b.jsonl"

    def log(agent, text, level="info"):
        msg = json.dumps({"agent": agent, "text": text, "level": level}, ensure_ascii=False)
        with open(progress_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        print(f"  [{agent}] {text}")

    log("image-sourcer", f"이미지 소싱 시작: {len(scenes)}씬")

    # source별 분류
    search_scenes = [s for s in scenes if s.get("imageAsset", {}).get("source") == "search"]
    generate_scenes = [s for s in scenes if s.get("imageAsset", {}).get("source") == "generate"]
    # cinematic 레이아웃인데 source 미지정이면 generate로 간주
    for s in scenes:
        layout = s.get("visualization", {}).get("creative", {}).get("layout", "")
        source = s.get("imageAsset", {}).get("source", "")
        if layout == "cinematic" and not source and s not in generate_scenes:
            generate_scenes.append(s)

    log("image-sourcer", f"분류: search {len(search_scenes)}씬, generate {len(generate_scenes)}씬")

    # 병렬 실행
    downloaded = 0
    generated = 0

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {}
        if search_scenes:
            futures["search"] = executor.submit(
                _run_search_track, search_scenes, img_dir, project_dir, log)
        if generate_scenes:
            futures["generate"] = executor.submit(
                _run_generate_track, generate_scenes, img_dir, project_dir, specs, log)

        for key, future in futures.items():
            try:
                result = future.result(timeout=600)
                if key == "search":
                    downloaded = result
                else:
                    generated = result
            except Exception as e:
                log("image-sourcer", f"{key} 트랙 에러: {e}", "error")

    # scene_specs 업데이트 (이미지 경로 반영)
    from auto_agent.tools.image_assets import get_selected
    for scene in scenes:
        sn = scene.get("sceneNumber")
        selected = get_selected(img_dir, sn)
        if selected:
            if not scene.get("imageAsset"):
                scene["imageAsset"] = {}
            ext = Path(selected).suffix
            scene["imageAsset"]["src"] = f"/output/{dir_name}/images/scene_{sn:03d}{ext}"

    specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    log("image-sourcer", f"이미지 소싱 완료: 다운로드 {downloaded}, 생성 {generated}", "success")

    result = {
        "total_images": downloaded + generated,
        "downloaded": downloaded,
        "generated": generated,
        "total_scenes": len(scenes),
    }
    result_path = project_dir / "image_gen_results.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        run(sys.argv[1])
    elif os.environ.get("PROJECT_DIR"):
        run(os.environ["PROJECT_DIR"])
    elif os.environ.get("PROJECT_NAME"):
        try:
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            project = pm.resolve_project(os.environ["PROJECT_NAME"])
            if project:
                run(project["output_dir"])
            else:
                from auto_agent.paths import get_workspace_dir
                run(str(get_workspace_dir() / "output" / os.environ["PROJECT_NAME"]))
        except Exception:
            from auto_agent.paths import get_workspace_dir
            run(str(get_workspace_dir() / "output" / os.environ["PROJECT_NAME"]))
    else:
        print("Usage: source_images.py <project_dir>")
