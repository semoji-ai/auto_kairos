"""chart_batch_module — chartagent SVG 차트 일괄 생성 모듈.

scene_specs.json에서 차트 씬(bar/pie/line/timeline 등)을 찾아
chartagent CLI로 render.svg를 생성하고, scene_specs에 chartSvgPath를 주입합니다.

환경변수:
  PROJECT_DIR   프로젝트 디렉토리 경로 (필수)

출력: stdout에 JSON {"status": "completed", "success": N, "fail": N, "skip": N}
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _progress(msg: str) -> None:
    try:
        print(f"[chart_batch] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[chart_batch] {msg.encode('ascii', errors='replace').decode()}", flush=True)


def run_chart_batch(project_dir: Path) -> dict[str, Any]:
    """
    project_dir의 scene_specs.json에서 차트 씬을 찾아 chartagent SVG를 생성합니다.

    Returns
    -------
    {"status": "completed", "success": N, "fail": N, "skip": N}
    """
    from auto_agent.modules.chartagent_adapter import (
        CHART_VIZ_TYPES,
        run_chartagent_for_scene,
        inject_chart_svg,
        save_project_chartagent_style,
        _resolve_viz_type,
    )

    project_dir = Path(project_dir)
    specs_path = project_dir / "scene_specs.json"
    if not specs_path.exists():
        raise FileNotFoundError(f"scene_specs.json 없음: {specs_path}")

    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    scenes: list[dict] = specs.get("scenes") or specs.get("scene_specs") or []
    meta = specs.get("meta") or {}

    # 아트스타일 design_tokens 로드
    art_style = meta.get("art_style") or meta.get("artStyle") or "semoji"
    dt: dict = {}
    styles_dir = Path(__file__).resolve().parent.parent / "data" / "artstyle" / "styles"
    style_json = styles_dir / f"{art_style}.json"
    if style_json.exists():
        dt = json.loads(style_json.read_text(encoding="utf-8")).get("design_tokens", {})

    charts_dir = project_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    success, fail, skip = 0, 0, 0
    updated_scenes: list[dict] = []

    for scene in scenes:
        scene_num = scene.get("sceneNumber", 0)
        viz_type = _resolve_viz_type(scene)

        if viz_type not in CHART_VIZ_TYPES:
            updated_scenes.append(scene)
            skip += 1
            continue

        # 이미 SVG가 생성된 경우 스킵
        existing_svg = charts_dir / f"scene_{scene_num:03d}" / "render.svg"
        if existing_svg.exists() and scene.get("imageAsset", {}).get("chartSvgPath"):
            _progress(f"  [SKIP] 씬 {scene_num:03d} — 이미 생성됨")
            updated_scenes.append(scene)
            skip += 1
            continue

        _progress(f"  [RUN] 씬 {scene_num:03d} ({viz_type})")
        try:
            svg_path = run_chartagent_for_scene(scene, charts_dir, design_tokens=dt)
            if svg_path is None:
                updated_scenes.append(scene)
                skip += 1
                continue

            updated_scene = inject_chart_svg(scene, svg_path)
            updated_scenes.append(updated_scene)
            success += 1
            _progress(f"  [OK] 씬 {scene_num:03d} → {svg_path.name}")
        except Exception as e:
            logger.warning(f"씬 {scene_num:03d} chartagent 실패: {e}")
            _progress(f"  [FAIL] 씬 {scene_num:03d}: {e}")
            updated_scenes.append(scene)
            fail += 1

    # scene_specs.json 업데이트
    if success > 0:
        key = "scenes" if "scenes" in specs else "scene_specs"
        specs[key] = updated_scenes
        specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
        _progress(f"scene_specs.json 업데이트 완료 (차트 씬 {success}개 주입)")

        # chartagent_style.json 생성 (가장 많이 사용된 theme_set 대표 spec)
        try:
            save_project_chartagent_style(charts_dir, base_tokens=dt)
            _progress("chartagent_style.json 저장 완료")
        except Exception as e:
            logger.warning(f"chartagent_style.json 저장 실패: {e}")

    _progress(f"완료: 성공 {success}개, 실패 {fail}개, 스킵 {skip}개")
    return {"status": "completed", "success": success, "fail": fail, "skip": skip}


def main() -> None:
    project_dir_env = os.environ.get("PROJECT_DIR", "")
    if not project_dir_env and len(sys.argv) > 1:
        project_dir_env = sys.argv[1]

    if not project_dir_env:
        print(json.dumps({"status": "failed", "error": "PROJECT_DIR 환경변수 또는 인수 필요"}))
        sys.exit(1)

    try:
        result = run_chart_batch(Path(project_dir_env))
        print(json.dumps(result, ensure_ascii=False))
    except Exception as e:
        logger.exception("chart_batch_module 실행 실패")
        print(json.dumps({"status": "failed", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
