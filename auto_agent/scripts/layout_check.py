"""
레이아웃 시각 검증 스크립트

이미지 에셋이 있는 씬의 스틸 프레임을 렌더링하여
레이아웃 문제를 시각적으로 검증한다.

사용법:
  python scripts/layout_check.py [--project <name>] [--scene <num>]

출력:
  output/{project}/layout_check/
    ├── scene_001.png   # 렌더링된 스틸
    ├── scene_008.png
    └── report.json     # 검증 결과
"""
import json
import subprocess
import sys
import os
from pathlib import Path

from auto_agent.paths import get_workspace_dir
from auto_agent.scripts.project_paths import get_project_dir

PROJECT_ROOT = get_workspace_dir()  # 하위 호환


def calc_scene_frames(manifest: dict) -> list:
    """각 씬의 시작/중간/끝 프레임을 계산한다."""
    fps = manifest["meta"].get("fps", 30)
    scenes = manifest["scenes"]
    result = []
    offset = 0

    for scene in scenes:
        dur_frames = max(int(scene["audioDurationSec"] * fps), 1)
        mid_frame = offset + dur_frames // 2
        result.append({
            "sceneNumber": scene["sceneNumber"],
            "startFrame": offset,
            "midFrame": mid_frame,
            "endFrame": offset + dur_frames,
            "durationFrames": dur_frames,
            "hasImage": bool(scene.get("imagePath")),
            "imageAsset": scene.get("imageAsset"),
        })
        offset += dur_frames

    return result


def render_still(frame: int, output_path: str, remotion_dir: str) -> bool:
    """Remotion CLI로 특정 프레임의 스틸 이미지를 렌더링한다."""
    cmd = [
        "npx", "remotion", "still",
        "SimpleVideo",
        output_path,
        f"--frame={frame}",
        "--overwrite",
    ]
    print(f"    Rendering frame {frame} → {Path(output_path).name}")
    try:
        result = subprocess.run(
            cmd,
            cwd=remotion_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return True
        else:
            print(f"    ERROR: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("    ERROR: Render timeout (120s)")
        return False
    except FileNotFoundError:
        print("    ERROR: npx not found. Node.js 환경을 확인하세요.")
        return False


def main():
    project_dir = get_project_dir()
    remotion_dir = str(PROJECT_ROOT / "remotion")

    # manifest.json 읽기
    manifest_path = PROJECT_ROOT / "remotion" / "public" / "manifest.json"
    if not manifest_path.exists():
        print("ERROR: manifest.json 없음. build_manifest.py를 먼저 실행하세요.")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    manifest = raw.get("manifest", raw)

    # 특정 씬만 체크할 경우
    target_scene = None
    for i, arg in enumerate(sys.argv):
        if arg == "--scene" and i + 1 < len(sys.argv):
            target_scene = int(sys.argv[i + 1])

    # 프레임 계산
    scene_frames = calc_scene_frames(manifest)

    # 이미지 에셋이 있는 씬만 필터
    check_targets = []
    for sf in scene_frames:
        if not sf["hasImage"]:
            continue
        if target_scene and sf["sceneNumber"] != target_scene:
            continue
        check_targets.append(sf)

    if not check_targets:
        print("체크할 이미지 씬이 없습니다.")
        return

    # 출력 디렉토리
    output_dir = project_dir / "layout_check"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"레이아웃 검증 대상: {len(check_targets)}개 씬")
    print(f"출력 디렉토리: {output_dir}")

    results = []
    for t in check_targets:
        num = t["sceneNumber"]
        placement = t["imageAsset"]["placement"] if t["imageAsset"] else "background"
        opacity = t["imageAsset"]["opacity"] if t["imageAsset"] else 0.4

        still_path = str(output_dir / f"scene_{num:03d}.png")

        print(f"\n[Scene {num}] placement={placement}, opacity={opacity}")
        ok = render_still(t["midFrame"], still_path, remotion_dir)

        results.append({
            "sceneNumber": num,
            "placement": placement,
            "opacity": opacity,
            "midFrame": t["midFrame"],
            "rendered": ok,
            "stillPath": still_path if ok else None,
        })

    # 리포트 저장
    report = {
        "total": len(results),
        "rendered": sum(1 for r in results if r["rendered"]),
        "scenes": results,
        "checkRules": [
            "텍스트가 이미지 에셋과 겹치지 않는지 확인",
            "배경 이미지 위 텍스트가 읽기 쉬운지 확인",
            "left/right 배치 시 텍스트가 반대편에 정렬되는지 확인",
            "자막 영역과 이미지가 겹치지 않는지 확인",
            "전체적인 시각적 밸런스 확인",
        ],
    }

    report_path = output_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {report['rendered']}/{report['total']}개 렌더링됨")
    print(f"리포트: {report_path}")
    print(f"\n렌더링된 스틸을 확인하여 레이아웃 문제가 없는지 검토하세요.")


if __name__ == "__main__":
    main()
