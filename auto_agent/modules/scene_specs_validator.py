"""
scene_specs.json v5 검증 도구.

사용:
    python3 -m auto_agent.modules.scene_specs_validator <project_slug>
    python3 -m auto_agent.modules.scene_specs_validator <path/to/scene_specs.json>

위반 사항 발견 시 exit 1, 깨끗하면 exit 0.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from auto_agent.modules.scene_helpers import validate_scene_specs


def _resolve_path(arg: str) -> Path:
    p = Path(arg)
    if p.exists() and p.is_file():
        return p
    # slug로 가정 → DB에서 조회
    try:
        from auto_agent.db.project_manager import ProjectManager
        pm = ProjectManager()
        proj = pm.get_project(slug=arg) or pm.get_project(uuid=arg)
        if proj:
            return Path(proj["output_dir"]) / "scene_specs.json"
    except Exception:
        pass
    raise SystemExit(f"파일/프로젝트 없음: {arg}")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(f"사용: python3 -m auto_agent.modules.scene_specs_validator <slug|path>")

    spec_path = _resolve_path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    result = validate_scene_specs(spec)
    print(f"scene_specs: {spec_path}")
    print(f"총 {result['total_scenes']}씬")
    print(f"visual_kind 분포: {result['kind_counts']}")
    print(f"위반 {result['violation_count']}건")

    if result["violations"]:
        for v in result["violations"]:
            print(f"\n  씬 #{v['sceneNumber']} (idx={v['scene_index']}, kind={v['visual_kind']})")
            for issue in v["issues"]:
                print(f"    - {issue}")
        sys.exit(1)
    print("✓ 통과 — Layer 1 단일성 무결")
    sys.exit(0)


if __name__ == "__main__":
    main()
