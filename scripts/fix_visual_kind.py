#!/usr/bin/env python3
"""scene_specs의 `visual_kind`를 `imageAsset.source`와 맞춘다.

`visual_kind`는 매니페스트가 이미지를 실을지 정하는 **관문**이다.
`build_manifest.py`는 이 값이 `search_image`나 `generate_image`가 아니면
이미지 탐색 자체를 건너뛴다. 그래서 **파일이 있어도 화면에 안 뜬다.**

실제로 EP01에서 18씬이 그랬다. 새로 그린 씬 48은 `source: generate`에
그림 파일까지 있는데 `visual_kind`가 `none`으로 남아 매니페스트에서 빠졌다.
스토리보드 미리보기가 비어 보인 원인이다.

`source`를 바꾸는 스크립트들(enforce_real_first, apply_relevance_recheck,
apply_dropped_fill)이 `visual_kind`를 함께 갱신하지 않아 생긴 어긋남이다.

map·chart·video는 건드리지 않는다 — 이미지보다 우선하는 시각 요소다.

    python3 scripts/fix_visual_kind.py <project_dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KEEP = {"map", "chart", "video"}
WANT = {"search": "search_image", "generate": "generate_image", "none": "none"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec = args.project / "scene_specs.json"
    data = json.loads(spec.read_text(encoding="utf-8"))

    fixed = []
    for s in data["scenes"]:
        vk = s.get("visual_kind")
        if vk in KEEP:
            continue
        src = (s.get("imageAsset") or {}).get("source")
        want = WANT.get(src)
        if want and vk != want:
            fixed.append((s["sceneNumber"], vk, want, s.get("layout")))
            s["visual_kind"] = want

    if not args.dry_run and fixed:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.project.name}: visual_kind 교정 {len(fixed)}씬"
          + ("  [dry-run]" if args.dry_run else ""))
    for n, before, after, layout in fixed[:20]:
        print(f"      씬 {n:>3} {before} → {after}  ({layout})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
