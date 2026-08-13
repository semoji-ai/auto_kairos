#!/usr/bin/env python3
"""scene_specs의 `source`와 image_assets.json의 `selected`를 맞춘다.

원장에서 자료를 내려도 화면은 안 바뀐다. 내려받은 파일이 `image_assets.json`에
`selected: true`로 남아 있기 때문이다. 실제로 관련성 관문에서 버린 EP01 씬 57이
시청자 재평가에서 **여전히 2005년 GS 출범식 사진으로 보였다.** 원장·스펙은
고쳤는데 화면만 그대로였다.

  source == "search"    → search 파일이 selected
  source == "generate"  → generated 파일이 selected
  source == "none"      → 아무것도 selected 하지 않는다 (도표는 이미지가 없다)

**파일은 지우지 않는다.** selected만 바꾼다(프로젝트 규칙).

    python3 scripts/sync_selected_assets.py <project_dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    scenes = {s["sceneNumber"]: s for s in json.loads(
        (args.project / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
    db_path = args.project / "images" / "image_assets.json"
    if not db_path.exists():
        print(f"  {args.project.name}: image_assets.json 없음")
        return 0
    db = json.loads(db_path.read_text(encoding="utf-8"))

    changed = []
    for entry in db.get("scenes", []):
        n = entry["sceneNumber"]
        src = (scenes.get(n, {}).get("imageAsset") or {}).get("source")
        want = {"search": "search", "generate": "generated"}.get(src)
        before = [i.get("file") for i in entry["images"] if i.get("selected")]
        if want is None:
            for i in entry["images"]:
                i["selected"] = False
        else:
            cands = [i for i in entry["images"] if i.get("type") == want
                     or str(i.get("file", "")).startswith(want)]
            # 아직 안 만든 경우 — 옛 선택을 남기면 search였던 자리에 버린 사진이
            # 계속 뜬다. 비워 두고 「이미지 없음」으로 드러나게 한다.
            if not cands:
                for i in entry["images"]:
                    i["selected"] = False
                after = []
                if before:
                    changed.append((n, before, ["(생성 대기)"], src))
                continue
            keep = cands[-1]          # 같은 종류가 여럿이면 최신본
            for i in entry["images"]:
                i["selected"] = i is keep
        after = [i.get("file") for i in entry["images"] if i.get("selected")]
        if before != after:
            changed.append((n, before, after, src))

    if not args.dry_run:
        db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.project.name}: 선택 교정 {len(changed)}씬"
          + ("  [dry-run]" if args.dry_run else ""))
    for n, b, a, src in changed[:12]:
        print(f"      씬 {n:>3} [{src}] {b or '없음'} → {a or '없음'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
