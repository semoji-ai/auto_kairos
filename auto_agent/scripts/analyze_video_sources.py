#!/usr/bin/env python3
"""
video_sources/ 폴더의 모든 mp4를 Gemini로 분석하여 video_scenes.json 생성.

사용법:
    python3 -m auto_agent.scripts.analyze_video_sources \
        --project 9f202fb4_포켓몬스터_30주년_브랜드백과사전_1편

출력:
    output/{project}/video_sources/video_scenes.json
"""
import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from auto_agent.paths import get_workspace_dir
from auto_agent.tools.video_analyzer import analyze_video


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="output/ 하위 프로젝트 폴더명")
    parser.add_argument("--force", action="store_true", help="이미 분석된 파일도 재분석")
    args = parser.parse_args()

    ws = get_workspace_dir()
    video_dir = ws / "output" / args.project / "video_sources"
    if not video_dir.exists():
        print(f"[error] video_sources 폴더 없음: {video_dir}")
        sys.exit(1)

    out_path = video_dir / "video_scenes.json"
    # 기존 결과 로드 (증분 실행 지원)
    existing: dict = {}
    if out_path.exists() and not args.force:
        existing = json.loads(out_path.read_text(encoding="utf-8"))

    mp4_files = sorted(video_dir.glob("*.mp4"))
    if not mp4_files:
        print("[warn] mp4 파일 없음")
        sys.exit(0)

    results: dict = dict(existing)

    for mp4 in mp4_files:
        key = mp4.name
        if key in results and not args.force and "error" not in results[key]:
            print(f"[skip] {key} (already analyzed)")
            continue
        print(f"[analyze] {key} ({mp4.stat().st_size / 1024 / 1024:.1f}MB)...")
        try:
            data = analyze_video(mp4)
            data["file"] = key
            results[key] = data
            print(f"  → {len(data.get('scenes', []))}개 장면, {data.get('duration_sec', 0):.1f}초")
        except Exception as e:
            print(f"  [error] {key}: {e}")
            results[key] = {"file": key, "error": str(e), "scenes": []}

        # 중간 저장 (중단 대비)
        out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n완료: {out_path}")
    print(f"분석된 영상: {len(results)}개")


if __name__ == "__main__":
    main()
