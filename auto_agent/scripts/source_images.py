"""
이미지 소싱 스크립트 — Python 기반 + Sonnet 1회 판단.

1. 위키미디어 검색 (씬별 후보 수집)
2. Sonnet 1회 호출 (전체 씬 최적 이미지 선택 + 생성 프롬프트)
3. 선택된 이미지 다운로드 / FAL.ai 생성
4. image_assets.json + scene_specs 업데이트
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


def run(project_dir: str):
    project_dir = Path(project_dir)
    load_dotenv(project_dir.parent.parent / ".env")

    specs_path = project_dir / "scene_specs.json"
    if not specs_path.exists():
        print("[ERROR] scene_specs.json 없음")
        return

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scenes = specs.get("scenes", [])
    slug = project_dir.name

    img_dir = project_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    # progress 파일
    progress_file = project_dir / ".progress_step_8b.jsonl"

    def log(agent, text, level="info"):
        msg = json.dumps({"agent": agent, "text": text, "level": level}, ensure_ascii=False)
        with open(progress_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        print(f"  [{agent}] {text}")

    # ── Step 1: 위키미디어 검색 ──
    log("image-sourcer", f"이미지 소싱 시작: {len(scenes)}씬")

    from auto_agent.tools.wikimedia_search import search_wikimedia, save_candidates, download_image
    from auto_agent.tools.image_assets import add_version, next_filename, get_selected

    search_results = {}  # {scene_num: [candidates]}
    for scene in scenes:
        sn = scene.get("sceneNumber")
        img = scene.get("imageAsset") or {}
        query = img.get("query", "")
        if not query:
            continue

        # 이미 이미지 있으면 스킵
        existing = list(img_dir.glob(f"scene_{sn:03d}.*")) + list(img_dir.glob(f"scene_{sn:03d}_*.*"))
        has_image = any(f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") for f in existing)
        if has_image:
            log("image-sourcer", f"씬{sn} 이미지 이미 존재 → 스킵")
            continue

        candidates = search_wikimedia(query, 8)
        search_results[sn] = candidates
        save_candidates(sn, query, candidates, str(img_dir))
        log("image-sourcer", f"씬{sn} 검색 완료: \"{query}\" → {len(candidates)}건")
        time.sleep(0.5)  # API 부담 줄이기

    # 검색 안 한 씬 (이미 이미지 있거나 쿼리 없음) 제외
    if not search_results:
        log("image-sourcer", "모든 씬에 이미지 존재 → 소싱 완료", "success")
        return

    # ── Step 2: Sonnet 판단 ──
    log("image-sourcer", "Sonnet에게 최적 이미지 선택 요청 중...")

    # 판단 프롬프트 구성
    selection_prompt = "각 씬에 가장 적합한 이미지를 선택하세요.\n\n"
    selection_prompt += "규칙:\n"
    selection_prompt += "- 16:9 영상에 적합한 가로형 이미지 우선\n"
    selection_prompt += "- 해상도 1280px 이상 우선\n"
    selection_prompt += "- 씬의 제목/나레이션과 관련성 높은 것\n"
    selection_prompt += "- 검색 결과가 없거나 부적합하면 generate로 표시\n"
    selection_prompt += "- generate일 때 스틸컷 이미지 프롬프트 작성 (동작 금지, 텍스트 금지)\n\n"

    for scene in scenes:
        sn = scene.get("sceneNumber")
        if sn not in search_results:
            continue  # 이미 이미지 있는 씬은 Sonnet에게 안 보냄
        img = scene.get("imageAsset") or {}
        query = img.get("query", "")
        title = scene.get("title", "")
        narration = scene.get("narration", "")[:100]

        selection_prompt += f"## 씬{sn}: {title}\n"
        selection_prompt += f"나레이션: {narration}\n"

        candidates = search_results.get(sn, [])
        if candidates:
            for i, c in enumerate(candidates):
                selection_prompt += f"  [{i}] {c.get('title','')} ({c.get('width',0)}x{c.get('height',0)}, {c.get('license','')})\n"
        else:
            selection_prompt += "  검색 결과 없음\n"
        selection_prompt += "\n"

    selection_prompt += """
JSON으로만 답하세요:
{
  "selections": [
    {"scene": 1, "action": "download", "index": 0},
    {"scene": 2, "action": "download", "index": 3},
    {"scene": 5, "action": "generate", "prompt": "영어 프롬프트..."},
    {"scene": 10, "action": "skip"}
  ]
}
action: "download" (후보 선택), "generate" (AI 생성), "skip" (이미지 불필요)
"""

    # Sonnet 호출
    try:
        cli_path = str(Path.home() / ".local/bin/claude")
        proc = subprocess.run(
            [cli_path, "--print", "--output-format", "json",
             "--model", "claude-sonnet-4-5-20250929", "--max-turns", "1"],
            input=selection_prompt, capture_output=True, text=True, timeout=180,
            env={**os.environ, "CLAUDECODE": ""},
        )

        # CLI 출력 파싱
        result_text = proc.stdout.strip()
        try:
            cli_out = json.loads(result_text)
            if isinstance(cli_out, dict) and "result" in cli_out:
                result_text = cli_out["result"]
                if isinstance(result_text, list):
                    result_text = " ".join(b.get("text", "") for b in result_text if isinstance(b, dict))
        except json.JSONDecodeError:
            pass

        # JSON 추출
        import re
        md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', result_text, re.DOTALL)
        if md_match:
            result_text = md_match.group(1)
        start = result_text.find("{")
        end = result_text.rfind("}") + 1
        if start >= 0 and end > start:
            selections = json.loads(result_text[start:end])
        else:
            selections = {"selections": []}

    except Exception as e:
        log("image-sourcer", f"Sonnet 호출 실패: {e}", "error")
        selections = {"selections": []}

    log("image-sourcer", f"Sonnet 판단 완료: {len(selections.get('selections', []))}씬")

    # ── Step 3: 다운로드 / 생성 ──
    downloaded = 0
    generated = 0

    for sel in selections.get("selections", []):
        sn = sel.get("scene")
        action = sel.get("action", "skip")

        if action == "download":
            idx = sel.get("index", 0)
            candidates = search_results.get(sn, [])
            if idx < len(candidates):
                c = candidates[idx]
                # 1920px 썸네일 우선 (rate limit 방지), 없으면 원본
                url = c.get("thumbnail_1920_url", "") or c.get("original_url", "")
                if not url:
                    continue
                fname = next_filename(img_dir, sn, "search", Path(url).suffix or ".jpg")
                log("image-sourcer", f"씬{sn} 다운로드 중: {c.get('title', '')[:30]}")
                result = download_image(url, str(img_dir / fname))
                if result.get("success"):
                    add_version(img_dir, sn, fname, "search",
                                query=search_results.get(sn, [{}])[0].get("query", "") if search_results.get(sn) else "",
                                title=c.get("title", ""), license=c.get("license", ""),
                                source_url=url)
                    downloaded += 1
                    log("image-sourcer", f"씬{sn} 다운로드 완료 ✓", "success")
                else:
                    log("image-sourcer", f"씬{sn} 다운로드 실패: {result.get('error', '')}", "warning")
                time.sleep(3)  # rate limit

        elif action == "generate":
            prompt = sel.get("prompt", "")
            if not prompt:
                continue
            fname = next_filename(img_dir, sn, "gen", ".png")
            # art_style — DB에서 읽기
            try:
                from auto_agent.db.project_manager import ProjectManager
                from auto_agent.db.connection import db_exists, init_db
                if not db_exists(): init_db()
                _pm = ProjectManager()
                _proj = _pm.get_project(slug=os.environ.get("PROJECT_NAME", ""))
                _cfg = _proj.get("config", {}) if _proj else {}
                if isinstance(_cfg, str):
                    _cfg = json.loads(_cfg)
                style_path = _cfg.get("art_style", "")
            except Exception:
                style_path = ""

            log("image-sourcer", f"씬{sn} 생성 중: {prompt[:40]}...")
            cmd = [sys.executable, "-m", "auto_agent.tools.image_generate", "scene",
                   "--prompt", prompt, "--output", str(img_dir / fname)]
            if style_path:
                ws = project_dir.parent.parent
                cmd.extend(["--style", str(ws / style_path)])
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                        cwd=str(project_dir.parent.parent))
                if result.returncode == 0:
                    add_version(img_dir, sn, fname, "generate", prompt=prompt[:200],
                                art_style=style_path)
                    generated += 1
                    log("image-sourcer", f"씬{sn} 생성 완료 ✓", "success")
                else:
                    err = result.stderr[:200] or result.stdout[:200]
                    log("image-sourcer", f"씬{sn} 생성 실패: {err}", "warning")
            except Exception as e:
                log("image-sourcer", f"씬{sn} 생성 에러: {e}", "error")

    # ── Step 4: scene_specs 업데이트 ──
    for scene in scenes:
        sn = scene.get("sceneNumber")
        selected = get_selected(img_dir, sn)
        if selected:
            if not scene.get("imageAsset"):
                scene["imageAsset"] = {}
            ext = Path(selected).suffix
            scene["imageAsset"]["src"] = f"/output/{slug}/images/scene_{sn:03d}{ext}"

    specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")

    log("image-sourcer", f"이미지 소싱 완료: 다운로드 {downloaded}, 생성 {generated}", "success")

    # 결과 JSON
    result = {
        "total_images": downloaded + generated,
        "downloaded": downloaded,
        "generated": generated,
        "total_scenes": len(scenes),
    }
    result_path = project_dir / "image_gen_results.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        project_name = os.environ.get("PROJECT_NAME", "")
        if project_name:
            from auto_agent.paths import get_workspace_dir
            run(str(get_workspace_dir() / "output" / project_name))
        else:
            print("Usage: source_images.py <project_dir>")
    else:
        run(sys.argv[1])
