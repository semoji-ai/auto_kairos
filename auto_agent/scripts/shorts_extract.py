"""쇼츠 구간 추출 — shorts_manifest.json + tts_results.json → 씬별 타임코드 매핑.

shorts_manifest.json의 씬 번호를 실제 오디오/이미지 파일과 타임코드에 매핑하여
shorts_timeline.json을 생성합니다. 이후 ffmpeg으로 구간별 오디오 추출 가능.

Usage:
  python -m auto_agent.scripts.shorts_extract --project <slug>
  python -m auto_agent.scripts.shorts_extract --project <slug> --cut  # ffmpeg으로 실제 오디오 커팅
"""
import argparse
import json
import logging
import subprocess
import shutil
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(prog="shorts-extract")
    parser.add_argument("--project", required=True, help="프로젝트 slug")
    parser.add_argument("--cut", action="store_true", help="ffmpeg으로 실제 오디오 커팅")
    args = parser.parse_args()

    # 프로젝트 경로 찾기
    from auto_agent.db.project_manager import get_project_by_slug
    project = get_project_by_slug(args.project)
    if not project:
        logger.error(f"프로젝트 '{args.project}' 를 찾을 수 없습니다")
        sys.exit(1)

    project_dir = Path(project["output_dir"])
    shorts_manifest = project_dir / "multi-contents" / "shorts_manifest.json"
    tts_results = project_dir / "tts_results.json"

    if not shorts_manifest.exists():
        logger.error(f"shorts_manifest.json 없음 — 먼저 /multi-contents를 실행하세요")
        sys.exit(1)
    if not tts_results.exists():
        logger.error(f"tts_results.json 없음 — Stage 3이 완료되지 않았습니다")
        sys.exit(1)

    # 1. TTS 결과에서 씬별 타임코드 빌드
    tts = json.loads(tts_results.read_text(encoding="utf-8"))
    scene_timing = {}  # {scene_num: {duration, path, start_sec, end_sec}}

    cumulative = 0.0
    for r in tts.get("results", []):
        sn = r["scene"]
        dur = r.get("duration", 0)
        scene_timing[sn] = {
            "scene": sn,
            "duration_sec": round(dur, 2),
            "start_sec": round(cumulative, 2),
            "end_sec": round(cumulative + dur, 2),
            "audio_path": r.get("path", ""),
        }
        cumulative += dur

    # 이미지 매핑
    images_dir = project_dir / "images"
    for sn in scene_timing:
        # scene_001.png, scene_001_gen_01.png 등
        img_candidates = sorted(images_dir.glob(f"scene_{sn:03d}*"))
        if img_candidates:
            scene_timing[sn]["image_path"] = str(img_candidates[-1])  # 최신 버전

    logger.info(f"씬 타이밍: {len(scene_timing)}개, 총 {cumulative:.0f}초 ({cumulative/60:.1f}분)")

    # 2. shorts_manifest 로드 및 타임라인 생성
    manifest = json.loads(shorts_manifest.read_text(encoding="utf-8"))
    shorts = manifest.get("shorts", [])

    timeline = []
    for short in shorts:
        short_id = short.get("short_id", "?")
        scene_nums = short.get("scenes", [])

        # 씬별 타이밍 수집
        scenes_detail = []
        total_dur = 0.0
        for sn in scene_nums:
            t = scene_timing.get(sn, {})
            if t:
                scenes_detail.append(t)
                total_dur += t.get("duration_sec", 0)

        if not scenes_detail:
            logger.warning(f"[{short_id}] 씬 매핑 실패: {scene_nums}")
            continue

        entry = {
            "short_id": short_id,
            "title": short.get("title_youtube", ""),
            "scenes": scene_nums,
            "total_duration_sec": round(total_dur, 2),
            "start_sec": scenes_detail[0]["start_sec"],
            "end_sec": scenes_detail[-1]["end_sec"],
            "audio_files": [s["audio_path"] for s in scenes_detail if s.get("audio_path")],
            "image_files": [s.get("image_path", "") for s in scenes_detail if s.get("image_path")],
            "hook": short.get("hook", {}),
            "platform_titles": {
                "youtube": short.get("title_youtube", ""),
                "tiktok": short.get("title_tiktok", ""),
                "reels": short.get("title_reels", ""),
            },
        }
        timeline.append(entry)

    # 3. 저장
    out_path = project_dir / "multi-contents" / "shorts_timeline.json"
    out_path.write_text(json.dumps({
        "project": args.project,
        "total_shorts": len(timeline),
        "total_longform_sec": round(cumulative, 1),
        "timeline": timeline,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(f"타임라인 생성: {len(timeline)}개 쇼츠 → {out_path}")

    # 요약 출력
    for t in timeline:
        dur = t["total_duration_sec"]
        mark = "✓" if 30 <= dur <= 60 else "⚠" if dur < 30 else "⚠ 길어"
        logger.info(f"  [{t['short_id']}] {dur:.0f}초 {mark} | 씬{t['scenes'][0]}-{t['scenes'][-1]} | {t['title'][:40]}")

    # 4. ffmpeg 커팅 (--cut 옵션)
    if args.cut:
        _cut_shorts_audio(project_dir, timeline)


def _cut_shorts_audio(project_dir: Path, timeline: list):
    """ffmpeg으로 쇼츠별 오디오를 추출합니다."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        logger.error("ffmpeg이 설치되어 있지 않습니다")
        return

    shorts_audio_dir = project_dir / "multi-contents" / "shorts_audio"
    shorts_audio_dir.mkdir(parents=True, exist_ok=True)

    for t in timeline:
        audio_files = t.get("audio_files", [])
        if not audio_files:
            continue

        out_file = shorts_audio_dir / f"{t['short_id']}.mp3"

        if len(audio_files) == 1:
            # 단일 파일 복사
            shutil.copy2(audio_files[0], out_file)
        else:
            # 여러 파일 concat
            concat_list = shorts_audio_dir / f"{t['short_id']}_list.txt"
            concat_list.write_text(
                "\n".join(f"file '{f}'" for f in audio_files),
                encoding="utf-8",
            )
            try:
                subprocess.run(
                    [ffmpeg, "-y", "-f", "concat", "-safe", "0",
                     "-i", str(concat_list), "-c", "copy", str(out_file)],
                    capture_output=True, timeout=30,
                )
                concat_list.unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"[{t['short_id']}] ffmpeg concat 실패: {e}")
                continue

        logger.info(f"  [{t['short_id']}] → {out_file.name} ({t['total_duration_sec']:.0f}초)")

    logger.info(f"오디오 커팅 완료: {shorts_audio_dir}")


if __name__ == "__main__":
    main()
