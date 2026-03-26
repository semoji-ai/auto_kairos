"""이미지 배치 생성 파이프라인 모듈.

환경변수:
  PROJECT_DIR     프로젝트 디렉토리 경로
  PROGRESS_FILE   진행 상황 JSONL 파일 경로 (선택)
  FAL_API_KEY / FAL_KEY  FAL AI API 키

출력: stdout에 JSON {"status": "completed", ...}
"""
from __future__ import annotations
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from auto_agent.tools import fal_queue as fal_queue
from auto_agent.tools.fal_queue import FalJob
from auto_agent.tools.character_library import CharacterLibrary
from auto_agent.tools.image_generate import (
    _build_character_fal_input,
    _build_scene_fal_input,
)
from auto_agent.tools import image_assets

logger = logging.getLogger(__name__)

_PROGRESS_FILE: Optional[Path] = None


def _progress(msg: str, level: str = "info") -> None:
    # Windows cp949 인코딩 에러 방지 - 출력 불가 문자는 ? 대체
    try:
        print(f"[image_batch] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[image_batch] {msg.encode('ascii', errors='replace').decode()}", flush=True)
    if _PROGRESS_FILE:
        with open(_PROGRESS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"message": msg, "level": level}) + "\n")


def _save_image_from_url(url: str, dest: Path) -> Path:
    """URL에서 이미지를 다운로드해 저장. 실패 시 부분 파일 정리."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        urllib.request.urlretrieve(url, str(tmp))
        if tmp.stat().st_size < 1024:  # 1KB 미만은 실패로 간주
            tmp.unlink(missing_ok=True)
            raise ValueError(f"다운로드 파일이 너무 작음: {tmp.stat().st_size}B")
        tmp.rename(dest)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return dest


def _build_char_result_path(project_dir: Path, char_id: str) -> Path:
    """캐릭터 결과 파일 경로 반환."""
    return project_dir / "characters" / f"{char_id}.png"


def run_batch(
    project_dir: Path,
    library: Optional[CharacterLibrary] = None,
) -> dict:
    """메인 배치 실행. summary dict 반환."""
    if library is None:
        library = CharacterLibrary()

    # ── 입력 로드 ──
    style_json_path = project_dir / "art_style.json"
    if not style_json_path.exists():
        _progress("art_style.json 누락 - 이미지 생성 스킵", level="error")
        return {"chars_reused": 0, "chars_generated": 0, "scenes_success": 0,
                "scenes_fail": 0, "scenes_skipped": 0, "status": "failed",
                "error": "art_style.json 누락"}
    style_path = str(style_json_path)
    art_style  = json.loads(style_json_path.read_text(encoding="utf-8"))
    art_style_id = art_style.get("id", "default")

    char_plan_path = project_dir / "character_plan.json"
    characters = []
    if char_plan_path.exists():
        characters = json.loads(char_plan_path.read_text(encoding="utf-8")).get("characters", [])

    # ── Phase 1: 캐릭터 배치 ──
    char_paths: dict[str, Optional[Path]] = {}
    reused, to_generate = [], []

    for char in characters:
        char_id   = char["id"]
        char_name = char["name"]
        tags      = char.get("tags", [])
        record = library.search(char_name, art_style_id, tags)
        if record:
            dest = library.copy_to_project(record, project_dir)
            char_paths[char_id] = dest
            reused.append(char_id)
            _progress(f"캐릭터 재사용: {char_name}")
        else:
            person_photo = char.get("person_photo")
            endpoint, arguments = _build_character_fal_input(
                prompt=char.get("description", char_name),
                style_path=style_path,
                person_photo=person_photo,
            )
            to_generate.append((char, FalJob(idx=len(to_generate), endpoint=endpoint, arguments=arguments)))

    if to_generate:
        jobs = [job for _, job in to_generate]
        _progress(f"캐릭터 {len(jobs)}개 FAL 배치 시작...")

        def on_char_done(result):
            char, _ = to_generate[result.idx]
            char_id = char["id"]
            if result.success and result.images:
                url  = result.images[0].get("url", "")
                dest = _build_char_result_path(project_dir, char_id)
                try:
                    _save_image_from_url(url, dest)
                    library.register(dest, {
                        "character_name": char["name"],
                        "art_style":      art_style_id,
                        "tags":           ",".join(char.get("tags", [])),
                        "features":       char.get("description", ""),
                        "source_project": project_dir.name,
                    })
                    char_paths[char_id] = dest
                    _progress(f"캐릭터 저장 완료: {char['name']}")
                except Exception as e:
                    logger.warning("캐릭터 저장 실패 (%s): %s", char_id, e)
            else:
                char_paths[char_id] = None
                _progress(f"캐릭터 생성 실패: {char['name']} - {result.error}", level="warning")

        fal_queue.run_batch(jobs, on_done=on_char_done, max_workers=10)

    _progress(
        f"캐릭터 완료: 재사용 {len(reused)}개, 신규 생성 {len(to_generate)}개, "
        f"성공 {sum(1 for v in char_paths.values() if v is not None)}개"
    )

    # ── 씬 데이터 로드 ──
    scene_specs_path = project_dir / "scene_specs.json"
    if not scene_specs_path.exists():
        return {"chars_reused": len(reused), "chars_generated": len(to_generate),
                "scenes_success": 0, "scenes_fail": 0, "scenes_skipped": 0}

    scene_specs = json.loads(scene_specs_path.read_text(encoding="utf-8"))
    images_dir = project_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # ── Phase 2 + 3 병렬: generate 배치 + search 순차 ──
    from concurrent.futures import ThreadPoolExecutor

    def _run_generate():
        """generate 씬 FAL 배치."""
        success, fail, skip = 0, 0, 0
        scene_jobs: list[tuple[dict, FalJob]] = []
        for scene in scene_specs.get("scenes", []):
            if (scene.get("imageAsset") or {}).get("source") != "generate":
                continue
            scene_num = scene.get("sceneNumber", 0)
            if image_assets.has_generated_version(images_dir, scene_num):
                skip += 1
                continue
            scene_char_paths = {cid: char_paths.get(cid) for cid in scene.get("characters", [])}
            try:
                endpoint, arguments = _build_scene_fal_input(scene, project_dir, scene_char_paths)
                scene_jobs.append((scene, FalJob(idx=len(scene_jobs), endpoint=endpoint, arguments=arguments)))
            except Exception as e:
                logger.warning("씬 %s 입력 빌드 실패: %s", scene.get("sceneNumber"), e)
                fail += 1

        if scene_jobs:
            jobs = [job for _, job in scene_jobs]
            _progress(f"generate {len(jobs)}개 FAL 배치 시작...")

            def on_done(result):
                nonlocal success, fail
                sc, _ = scene_jobs[result.idx]
                sn = sc.get("sceneNumber", result.idx + 1)
                if result.success and result.images:
                    gen_dir = images_dir / "generated"
                    gen_dir.mkdir(exist_ok=True)
                    fname = image_assets.next_filename(images_dir, sn, "gen", ".png")
                    try:
                        _save_image_from_url(result.images[0].get("url", ""), gen_dir / fname)
                        image_assets.add_version(images_dir, sn, "generated/" + fname, "generate")
                        success += 1
                        _progress(f"씬 {sn} 생성 완료: {fname}")
                    except Exception:
                        fail += 1
                else:
                    _progress(f"씬 {sn} 생성 실패: {result.error}", level="warning")
                    fail += 1

            fal_queue.run_batch(jobs, on_done=on_done, max_workers=10)
        return {"success": success, "fail": fail, "skip": skip}

    def _run_search():
        """search 씬 순차 검색 + 실패 시 generate fallback."""
        import shutil as _sh
        success, fail, skip = 0, 0, 0
        failed_scenes = []

        from auto_agent.tools.image_search import ImageSearcher
        search_dl_dir = images_dir / "search"
        search_dl_dir.mkdir(exist_ok=True)
        searcher = ImageSearcher(images_dir=search_dl_dir)

        for scene in scene_specs.get("scenes", []):
            ia = scene.get("imageAsset") or {}
            if ia.get("source") != "search":
                continue
            scene_num = scene.get("sceneNumber", 0)
            if image_assets.has_generated_version(images_dir, scene_num):
                skip += 1
                continue
            existing = list(search_dl_dir.glob(f"scene_{scene_num:03d}_search_*.*"))
            if existing:
                skip += 1
                continue
            query = ia.get("query") or ia.get("prompt") or ""
            if not query:
                fail += 1
                continue

            _progress(f"씬 {scene_num} 검색: {query[:40]}")
            try:
                results = searcher.search_waterfall(query, limit=3, preferred_aspect="16:9")
                if results and results[0].local_path and Path(results[0].local_path).exists():
                    best = results[0]
                    ext = Path(best.local_path).suffix or ".jpg"
                    fname = image_assets.next_filename(images_dir, scene_num, "search", ext)
                    dest = search_dl_dir / fname
                    _sh.copy2(best.local_path, dest)
                    try:
                        Path(best.local_path).unlink(missing_ok=True)
                    except Exception:
                        pass
                    image_assets.add_version(images_dir, scene_num, "search/" + fname, "search",
                                             source_url=best.source_page, license_info=best.license)
                    success += 1
                    _progress(f"씬 {scene_num} 검색 완료: {fname}")
                else:
                    fail += 1
                    failed_scenes.append(scene)
                    _progress(f"씬 {scene_num} 검색 실패 - fallback 예정", level="warning")
            except Exception as e:
                fail += 1
                failed_scenes.append(scene)
                _progress(f"씬 {scene_num} 검색 에러: {e}", level="warning")

        # search 실패 → generate fallback
        if failed_scenes:
            _progress(f"검색 실패 {len(failed_scenes)}개 → generate fallback")
            fb_jobs: list[tuple[dict, FalJob]] = []
            for sc in failed_scenes:
                try:
                    ep, args = _build_scene_fal_input(sc, project_dir, {})
                    fb_jobs.append((sc, FalJob(idx=len(fb_jobs), endpoint=ep, arguments=args)))
                except Exception:
                    pass
            if fb_jobs:
                gen_dir = images_dir / "generated"
                gen_dir.mkdir(exist_ok=True)
                jobs = [j for _, j in fb_jobs]

                def on_fb(result):
                    nonlocal success, fail
                    sc2, _ = fb_jobs[result.idx]
                    sn = sc2.get("sceneNumber", 0)
                    if result.success and result.images:
                        fname = image_assets.next_filename(images_dir, sn, "gen", ".png")
                        try:
                            _save_image_from_url(result.images[0].get("url", ""), gen_dir / fname)
                            image_assets.add_version(images_dir, sn, "generated/" + fname, "generate")
                            success += 1
                            fail -= 1  # 실패에서 성공으로 전환
                            _progress(f"씬 {sn} fallback 생성 완료")
                        except Exception:
                            pass
                    else:
                        _progress(f"씬 {sn} fallback 실패", level="warning")

                fal_queue.run_batch(jobs, on_done=on_fb, max_workers=10)

        return {"success": success, "fail": fail, "skip": skip}

    # ── 병렬 실행: generate + search ──
    _progress("이미지 generate + search 병렬 시작...")
    with ThreadPoolExecutor(max_workers=2) as pool:
        gen_future = pool.submit(_run_generate)
        search_future = pool.submit(_run_search)
        gen_result = gen_future.result()
        search_result = search_future.result()

    total_success = gen_result["success"] + search_result["success"]
    total_fail = gen_result["fail"] + search_result["fail"]
    total_skip = gen_result["skip"] + search_result["skip"]
    _progress(f"이미지 완료: 생성 {gen_result['success']}개 + 검색 {search_result['success']}개, 실패 {total_fail}개, 스킵 {total_skip}개")

    summary = {
        "chars_reused":    len(reused),
        "chars_generated": len(to_generate),
        "scenes_success":  total_success,
        "scenes_fail":     total_fail,
        "scenes_skipped":  total_skip,
    }
    total_attempted = total_success + total_fail
    if total_attempted > 0 and total_fail > total_attempted * 0.5:
        summary["status"] = "failed"
        summary["error"] = f"이미지 대량 실패: {total_fail}/{total_attempted}"
        _progress(summary["error"], level="error")
    return summary


def run_tts_batch(project_dir: Path) -> dict:
    """TTS 배치 생성 — generate_tts.py를 subprocess로 실행."""
    _progress("TTS 배치 시작...")
    try:
        import subprocess as _sp
        from auto_agent.utils.platform import subprocess_kwargs
        env = {**os.environ, "PROJECT_DIR": str(project_dir)}
        result = _sp.run(
            [sys.executable, "-m", "auto_agent.scripts.generate_tts", str(project_dir)],
            cwd=str(project_dir.parent.parent),
            env=env,
            capture_output=True, text=True, encoding="utf-8",
            timeout=1800,
            **subprocess_kwargs(),
        )
        if result.returncode != 0:
            _progress(f"TTS 실패: {result.stderr[:200]}", level="warning")
            return {"status": "failed", "error": result.stderr[:200]}
        _progress("TTS 배치 완료 - 자막 정렬 시작...")

        # TTS 완료 후 자막 정렬 (WhisperX)
        sub_result = _sp.run(
            [sys.executable, "-m", "auto_agent.scripts.generate_subtitles", str(project_dir)],
            cwd=str(project_dir.parent.parent),
            env=env,
            capture_output=True, text=True, encoding="utf-8",
            timeout=600,
            **subprocess_kwargs(),
        )
        if sub_result.returncode == 0:
            _progress("자막 정렬 완료")
        else:
            _progress(f"자막 정렬 실패: {sub_result.stderr[:200]}", level="warning")

        return {"status": "completed"}
    except Exception as e:
        _progress(f"TTS/자막 에러: {e}", level="warning")
        return {"status": "failed", "error": str(e)}


def main():
    """파이프라인 runner가 subprocess로 실행하는 진입점."""
    global _PROGRESS_FILE
    project_dir_str = os.environ.get("PROJECT_DIR", "")
    if not project_dir_str:
        print(json.dumps({"status": "failed", "error": "PROJECT_DIR 환경변수 없음"}))
        sys.exit(1)

    project_dir = Path(project_dir_str)
    progress_path = os.environ.get("PROGRESS_FILE", "")
    if progress_path:
        _PROGRESS_FILE = Path(progress_path)

    try:
        # 이미지 배치와 TTS를 병렬 실행
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=2) as pool:
            img_future = pool.submit(run_batch, project_dir)
            tts_future = pool.submit(run_tts_batch, project_dir)

            img_summary = img_future.result()
            tts_result = tts_future.result()

        img_summary["tts_status"] = tts_result.get("status", "unknown")
        img_summary["status"] = "completed"
        print(json.dumps(img_summary, ensure_ascii=False))
    except Exception as e:
        logger.exception("image_batch_module 실행 실패")
        print(json.dumps({"status": "failed", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
