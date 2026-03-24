"""
시각적 QA 스틸 캡처 스크립트

모든 씬의 중간 프레임을 Remotion으로 렌더링하여
시각적 QA 검증용 스틸 이미지를 생성한다.

사용법:
  python -m auto_agent.scripts.layout_check [--project <name>] [--scene <num>]

출력:
  output/{project}/layout_check/
    ├── scene_001.png          # 렌더링된 스틸
    ├── scene_002.png
    ├── ...
    └── layout_check_report.json  # 씬별 메타데이터 + 경로
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from auto_agent.paths import get_workspace_dir
from auto_agent.scripts.project_paths import get_project_dir, get_scene_specs_path
from auto_agent.utils.platform import get_env_with_node, get_npx_cmd

PROJECT_ROOT = get_workspace_dir()


def calc_scene_frames(manifest: dict) -> list:
    """각 씬의 시작/중간/끝 프레임을 계산한다."""
    fps = manifest["meta"].get("fps", 30)
    scenes = manifest["scenes"]
    result = []
    offset = 0

    for scene in scenes:
        dur_frames = max(int(scene["audioDurationSec"] * fps), 1)
        preview_frame = offset + int(dur_frames * 0.9)
        result.append({
            "sceneNumber": scene["sceneNumber"],
            "startFrame": offset,
            "midFrame": preview_frame,  # 90% 지점 (프리뷰용)
            "endFrame": offset + dur_frames,
            "durationFrames": dur_frames,
            "hasImage": bool(scene.get("imagePath")),
            "imageAsset": scene.get("imageAsset"),
        })
        offset += dur_frames

    return result


def load_scene_specs_meta(project_dir: Path) -> dict:
    """scene_specs.json에서 씬별 메타데이터를 읽어온다."""
    specs_path = get_scene_specs_path()
    if not specs_path.exists():
        return {}

    with open(specs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data.get("scenes", [])
    meta = {}
    for s in scenes:
        num = s.get("sceneNumber")
        viz = s.get("visualization", {})
        creative = viz.get("creative", {})
        meta[num] = {
            "headline": creative.get("headline", ""),
            "layout": creative.get("layout", ""),
            "emphasis": creative.get("emphasis", ""),
            "reveal": creative.get("reveal", ""),
            "items": viz.get("items", []),
            "itemIcons": viz.get("itemIcons", []),
            "values": viz.get("values", []),
            "title": viz.get("title", ""),
            "narration": s.get("narration", ""),
            "hasImageAsset": bool(s.get("imageAsset")),
            "imagePlacement": s.get("imageAsset", {}).get("placement", "") if s.get("imageAsset") else "",
        }
    return meta


def render_still(frame: int, output_path: str, remotion_dir: str) -> bool:
    """Remotion CLI로 특정 프레임의 스틸 이미지를 렌더링한다."""
    cmd = [
        get_npx_cmd(), "remotion", "still",
        "SimpleVideo",
        output_path,
        f"--frame={frame}",
        "--overwrite",
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=remotion_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=get_env_with_node(),
        )
        if result.returncode == 0:
            return True
        else:
            print(f"    ERROR (frame {frame}): {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"    ERROR: Render timeout (frame {frame})")
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

    # scene_specs 메타데이터 로드
    specs_meta = load_scene_specs_meta(project_dir)

    # 특정 씬만 체크할 경우
    target_scene = None
    for i, arg in enumerate(sys.argv):
        if arg == "--scene" and i + 1 < len(sys.argv):
            target_scene = int(sys.argv[i + 1])

    # 프레임 계산 -- 모든 씬
    scene_frames = calc_scene_frames(manifest)

    # 타겟 필터 (--scene 옵션 시)
    check_targets = []
    for sf in scene_frames:
        if target_scene and sf["sceneNumber"] != target_scene:
            continue
        check_targets.append(sf)

    if not check_targets:
        print("체크할 씬이 없습니다.")
        return

    # 출력 디렉토리
    output_dir = project_dir / "layout_check"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"시각적 QA 스틸 캡처: {len(check_targets)}개 씬")
    print(f"출력 디렉토리: {output_dir}")

    # 병렬 렌더링 (최대 4 workers -- Remotion CLI 프로세스 부하 고려)
    results = []

    def _render_one(t):
        num = t["sceneNumber"]
        still_path = str(output_dir / f"scene_{num:03d}.png")
        print(f"  [Scene {num}] frame={t['midFrame']} -> {Path(still_path).name}")
        ok = render_still(t["midFrame"], still_path, remotion_dir)

        scene_meta = specs_meta.get(num, {})
        return {
            "sceneNumber": num,
            "midFrame": t["midFrame"],
            "durationFrames": t["durationFrames"],
            "rendered": ok,
            "stillPath": str(still_path) if ok else None,
            "stillFilename": f"scene_{num:03d}.png",
            # scene_specs 메타 (QA 에이전트 대조용)
            "headline": scene_meta.get("headline", ""),
            "layout": scene_meta.get("layout", ""),
            "emphasis": scene_meta.get("emphasis", ""),
            "items": scene_meta.get("items", []),
            "itemCount": len(scene_meta.get("items", [])),
            "hasImageAsset": scene_meta.get("hasImageAsset", False),
            "imagePlacement": scene_meta.get("imagePlacement", ""),
            "narrationLength": len(scene_meta.get("narration", "")),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(_render_one, t): t for t in check_targets}
        for future in as_completed(futures):
            results.append(future.result())

    # sceneNumber 순 정렬
    results.sort(key=lambda r: r["sceneNumber"])

    # 리포트 저장
    report = {
        "projectDir": str(project_dir),
        "totalScenes": len(results),
        "renderedCount": sum(1 for r in results if r["rendered"]),
        "failedCount": sum(1 for r in results if not r["rendered"]),
        "outputDir": str(output_dir),
        "scenes": results,
        "qaCheckItems": [
            "텍스트 넘침/줄바꿈: headline이나 items가 컨테이너를 넘어 잘렸는지",
            "headline-items 중복: 화면에 같은 내용이 두 번 표시되는지",
            "빈 화면: 데이터가 렌더링되지 않아 검정 화면만 보이는지",
            "이미지-텍스트 겹침: 이미지 에셋 위에 텍스트가 가려지는지",
            "레이아웃 의도 불일치: layout 대비 실제 배치가 다른지",
            "자막 영역 침범: 하단 자막 공간에 시각화 요소가 겹치는지",
            "accent 과다: {{}} 강조가 3개 이상으로 산만해 보이는지",
            "시각적 밸런스: 한쪽에 요소가 몰리거나 여백이 과도한지",
        ],
    }

    report_path = output_dir / "layout_check_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {report['renderedCount']}/{report['totalScenes']}개 렌더링됨")
    if report["failedCount"] > 0:
        print(f"실패: {report['failedCount']}개")
    print(f"리포트: {report_path}")
    print(f"스틸 디렉토리: {output_dir}")


if __name__ == "__main__":
    main()
