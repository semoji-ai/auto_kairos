#!/usr/bin/env python3
"""씬 하나를 훑어 **어떤 층으로 가를지 계획만** 세운다.

가르기 전에 사람이 목록을 보고 고칠 수 있어야 한다. 한 번 가르면 fal 비용이
들고 몇 분이 걸리는데, 무엇을 가를지 잘못 정했으면 그 시간이 통째로 버려진다.
계획은 글이라 고치기 쉽다.

결과는 `_imggen/<ep>_anim/s<번호>/layer_plan.json` 에 남는다.
`animate_scene.py`는 이 파일이 있으면 다시 묻지 않고 그대로 쓴다.

    python3 scripts/plan_scene_layers.py EP05 1
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from animate_scene import plan_layers, scene_image_of  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("scene", type=int)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    project, ep = resolve_project(args.ep)
    out = root / "_imggen" / f"{ep.lower()}_anim" / f"s{args.scene:03d}"

    spec = {s["sceneNumber"]: s for s in json.loads(
        (project / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
    s = spec.get(args.scene)
    if not s:
        print(f"씬 {args.scene}이 없습니다")
        return 1

    img = scene_image_of(project, args.scene)
    if not img or not img.exists():
        print(f"씬 {args.scene}: 고른 이미지가 없습니다 — 이미지를 먼저 확정하세요")
        return 1

    if plan_layers(img, s.get("narration") or "", out):
        print(f"  → {out / 'layer_plan.json'}")
        return 0
    print(f"씬 {args.scene}: 계획을 세우지 못했습니다")
    return 1


if __name__ == "__main__":
    sys.exit(main())
