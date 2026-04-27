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
from auto_agent.tools.scene_id import load_scene_specs
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

    scene_specs = load_scene_specs(scene_specs_path)
    images_dir = project_dir / "images"
    images_dir.mkdir(exist_ok=True)

    # videoAsset이 확보된 씬 번호 집합 — 이미지 생성/검색 스킵용
    _video_asset_sns: set[int] = set()
    _va_path = project_dir / "video_assets.json"
    if _va_path.exists():
        try:
            _va_data = json.loads(_va_path.read_text(encoding="utf-8"))
            for _va in _va_data.get("scenes", []):
                sn_ = _va.get("sceneNumber")
                vf_ = _va.get("videoFile", "")
                if sn_ is not None and vf_ and (project_dir / "video_sources" / vf_).exists():
                    _video_asset_sns.add(sn_)
        except Exception:
            pass

    # ── Phase 2 + 3 병렬: generate 배치 + search 순차 ──
    from concurrent.futures import ThreadPoolExecutor

    def _run_generate():
        """generate 씬 FAL 배치 — visual_kind=generate_image인 씬만."""
        from auto_agent.modules.scene_helpers import get_visual_kind
        success, fail, skip = 0, 0, 0
        scene_jobs: list[tuple[dict, FalJob]] = []
        for scene in scene_specs.get("scenes", []):
            if get_visual_kind(scene) != "generate_image":
                continue
            scene_num = scene.get("sceneNumber", 0)
            if scene_num in _video_asset_sns:
                skip += 1
                continue
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

    def _load_research_images() -> list[dict]:
        """project_dir 내 최신 image_manifest.jsonl 로드."""
        research_root = project_dir / "research"
        raw_dir = research_root / "raw"
        images: list[dict] = []
        if not raw_dir.exists():
            return images
        # 모든 run 폴더를 최신순으로 순회
        for slug_dir in sorted(raw_dir.iterdir(), reverse=True):
            if not slug_dir.is_dir():
                continue
            for run_dir in sorted(slug_dir.iterdir(), reverse=True):
                manifest = run_dir / "image_manifest.jsonl"
                if not manifest.exists():
                    continue
                for line in manifest.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        try:
                            images.append(json.loads(line))
                        except Exception:
                            pass
                if images:
                    return images  # 최신 run에서 찾으면 즉시 반환
        return images

    def _vision_select_best(candidates: list, scene: dict) -> Optional[object]:
        """상위 후보 이미지를 Claude 비전으로 보고 씬에 가장 적합한 것을 선택."""
        if not candidates:
            return None
        if len(candidates) == 1:
            return candidates[0]

        valid = [c for c in candidates if c.local_path and Path(c.local_path).exists()]
        if not valid:
            return None
        if len(valid) == 1:
            return valid[0]

        import base64, subprocess as _sp, tempfile as _tf
        narration = scene.get("narration", "")[:200]
        query = (scene.get("imageAsset") or {}).get("query", "")
        title = scene.get("title", "")

        # 이미지 base64 인코딩
        img_parts = []
        for i, c in enumerate(valid[:5]):
            try:
                data = Path(c.local_path).read_bytes()
                b64 = base64.b64encode(data).decode()
                ext = Path(c.local_path).suffix.lstrip(".").lower() or "jpeg"
                if ext == "jpg":
                    ext = "jpeg"
                img_parts.append((i, b64, ext, c))
            except Exception:
                pass

        if not img_parts:
            return valid[0]

        # Claude API로 비전 선택
        try:
            import anthropic
            client = anthropic.Anthropic()
            content = []
            for i, b64, ext, _ in img_parts:
                content.append({"type": "text", "text": f"[이미지 {i+1}]"})
                content.append({"type": "image", "source": {"type": "base64", "media_type": f"image/{ext}", "data": b64}})
            content.append({"type": "text", "text": (
                f"씬 제목: {title}\n검색 쿼리: {query}\n나레이션: {narration}\n\n"
                f"위 {len(img_parts)}장의 이미지 중 이 씬에 가장 적합한 이미지 번호를 숫자 하나만 답하세요. (예: 2)"
            )})
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": content}],
            )
            answer = resp.content[0].text.strip()
            import re as _re
            m = _re.search(r"\d+", answer)
            if m:
                idx = int(m.group()) - 1
                if 0 <= idx < len(img_parts):
                    return img_parts[idx][3]
        except Exception as e:
            _progress(f"비전 선택 실패 ({e}) — 1순위 사용", level="warning")

        return valid[0]

    def _match_research_image(research_images: list[dict], query: str, scene_title: str = "") -> Optional[dict]:
        """쿼리와 씬 제목을 기반으로 리서치 이미지 중 가장 적합한 것을 반환."""
        if not research_images or not query:
            return None
        q_words = set(query.lower().split())
        t_words = set(scene_title.lower().split()) if scene_title else set()
        best: Optional[dict] = None
        best_score = 0
        for img in research_images:
            title = (img.get("title") or "").lower()
            src_url = (img.get("source_url") or "").lower()
            img_url = (img.get("image_url") or "")
            if not img_url:
                continue
            # 실패했던 이미지는 건너뜀
            if img.get("hash_failed"):
                continue
            t = set(title.split())
            score = len(q_words & t) + len(t_words & t) * 0.5
            # 출처 URL에 쿼리 키워드가 있으면 보너스
            score += sum(1 for w in q_words if len(w) > 3 and w in src_url) * 0.3
            if score > best_score:
                best_score = score
                best = img
        # 최소 1개 단어 이상 겹쳐야 유효
        return best if best_score >= 1.0 else None

    def _run_search():
        """search 씬 순차 검색 + 실패 시 generate fallback.

        우선순위: 1) 리서치에서 수집된 이미지 → 2) 실시간 검색 → 3) generate fallback
        """
        import shutil as _sh
        success, fail, skip = 0, 0, 0
        failed_scenes = []

        from auto_agent.tools.image_search import ImageSearcher
        search_dl_dir = images_dir / "search"
        search_dl_dir.mkdir(exist_ok=True)
        searcher = ImageSearcher(images_dir=search_dl_dir)

        # 리서치 단계에서 수집한 이미지 목록 로드
        research_images = _load_research_images()
        if research_images:
            _progress(f"리서치 이미지 {len(research_images)}개 로드 완료 — 씬 매칭 시도")

        from auto_agent.modules.scene_helpers import get_visual_kind
        for scene in scene_specs.get("scenes", []):
            if get_visual_kind(scene) != "search_image":
                continue
            ia = scene.get("imageAsset") or {}
            scene_num = scene.get("sceneNumber", 0)
            if scene_num in _video_asset_sns:
                skip += 1
                continue
            if image_assets.has_generated_version(images_dir, scene_num):
                skip += 1
                continue
            # 파일 존재 여부가 아닌 image_assets 등록 여부로 스킵 결정
            # (image_assets에서 제거된 씬은 파일이 있어도 새 버전으로 재검색)
            if image_assets.has_search_version(images_dir, scene_num):
                skip += 1
                continue

            # ── step_2d (scene_enricher)가 사전 선택한 url 우선 사용 ──
            preselected_url = ia.get("url")
            preselected_status = ia.get("selection_status")
            if preselected_url and preselected_status in ("auto", "user_picked"):
                try:
                    ext = "." + preselected_url.split(".")[-1].split("?")[0].lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                        ext = ".jpg"
                    fname = image_assets.next_filename(images_dir, scene_num, "search", ext)
                    dest = search_dl_dir / fname
                    import urllib.request as _ur
                    _ur.urlretrieve(preselected_url, str(dest))
                    if dest.exists() and dest.stat().st_size > 1024:
                        image_assets.add_version(
                            images_dir, scene_num, "search/" + fname, "search",
                            source_url=preselected_url,
                            license_info=ia.get("license", ""),
                        )
                        success += 1
                        _progress(f"씬 {scene_num} step_2d 선택 자료 사용: {(ia.get('source_domain') or '')[:30]}")
                        continue
                    else:
                        dest.unlink(missing_ok=True)
                        _progress(f"씬 {scene_num} 사전 url 다운로드 실패 — 재검색 fallback", level="warning")
                except Exception as e:
                    _progress(f"씬 {scene_num} 사전 url 처리 실패 ({e}) — 재검색 fallback", level="warning")

            query = ia.get("query") or ia.get("prompt") or ""
            if not query:
                fail += 1
                continue

            # ── 1단계: 리서치 이미지에서 매칭 시도 ──
            scene_title = scene.get("title", "")
            matched = _match_research_image(research_images, query, scene_title)
            if matched:
                img_url = matched["image_url"]
                try:
                    ext = "." + img_url.split(".")[-1].split("?")[0].lower()
                    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                        ext = ".jpg"
                    fname = image_assets.next_filename(images_dir, scene_num, "search", ext)
                    dest = search_dl_dir / fname
                    import urllib.request as _ur
                    _ur.urlretrieve(img_url, str(dest))
                    if dest.exists() and dest.stat().st_size > 1024:
                        image_assets.add_version(
                            images_dir, scene_num, "search/" + fname, "search",
                            source_url=matched.get("source_url", img_url),
                            license_info=matched.get("image_license", ""),
                        )
                        success += 1
                        _progress(f"씬 {scene_num} 리서치 이미지 재활용: {matched.get('title','')[:40]}")
                        continue
                    else:
                        dest.unlink(missing_ok=True)
                except Exception as e:
                    _progress(f"씬 {scene_num} 리서치 이미지 다운로드 실패 ({e}) — 실시간 검색으로 폴백", level="warning")

            # ── 2단계: 실시간 검색 ──
            _progress(f"씬 {scene_num} 검색: {query[:40]}")
            try:
                results = searcher.search_waterfall(query, limit=5, preferred_aspect="16:9")
                best = _vision_select_best(results, scene)
                # 선택되지 않은 후보 임시 파일 정리
                for r in results:
                    if r is not best and r.local_path:
                        try:
                            Path(r.local_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                if best and best.local_path and Path(best.local_path).exists():
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
                    ep, args = _build_scene_fal_input(sc, project_dir, {}, is_search_fallback=True)
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

        # ── personImages: person_card 개인 사진 ──
        for scene in scene_specs.get("scenes", []):
            person_specs = scene.get("personImages")
            if not person_specs:
                continue
            scene_num = scene.get("sceneNumber", 0)
            scene_key_p = f"scene_{scene_num:03d}"
            for pi, pspec in enumerate(person_specs, start=1):
                dest_name = f"{scene_key_p}_person_{pi:02d}.jpg"
                dest_path = search_dl_dir / dest_name
                if dest_path.exists():
                    continue
                query = pspec.get("query", "")
                if not query:
                    continue
                _progress(f"씬 {scene_num} 인물{pi} 검색: {query[:50]}")
                try:
                    results = searcher.search_waterfall(query, limit=3, preferred_aspect="1:1")
                    if results and results[0].local_path and Path(results[0].local_path).exists():
                        import shutil as _sh2
                        _sh2.copy2(results[0].local_path, dest_path)
                        try:
                            Path(results[0].local_path).unlink(missing_ok=True)
                        except Exception:
                            pass
                        success += 1
                        _progress(f"씬 {scene_num} 인물{pi} 완료: {dest_name}")
                    else:
                        _progress(f"씬 {scene_num} 인물{pi} 검색 실패", level="warning")
                except Exception as e:
                    _progress(f"씬 {scene_num} 인물{pi} 에러: {e}", level="warning")

        return {"success": success, "fail": fail, "skip": skip}

    # ── 병렬 실행: generate + search ──
    _progress("이미지 generate + search 병렬 시작...")
    with ThreadPoolExecutor(max_workers=2) as pool:
        gen_future = pool.submit(_run_generate)
        search_future = pool.submit(_run_search)
        # generate 실패 시 search는 계속 진행
        try:
            gen_result = gen_future.result()
        except Exception as e:
            _progress(f"generate 배치 실패 (search는 계속): {e}", level="warning")
            gen_result = {"success": 0, "fail": 0, "skip": 0}
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
