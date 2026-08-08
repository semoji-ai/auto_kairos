#!/usr/bin/env python3
"""같은 실물 자료가 여러 씬에 반복되는 것을 막는다.

**한 사진은 한 씬에서만 쓴다.** 연달아 같은 화면이 뜨면 실물을 쓴 효과가
오히려 반감된다. EP03은 18개 씬에 사진 8장을 돌려 썼고, EP09는 같은 인물
사진이 씬 9·11·12에 연속으로 나왔다. 전체로는 채택 215건 중 58건(27%)이
중복이었다.

첫 등장을 남긴다. 처음 나올 때가 그 자료를 보여 주는 순간이고, 뒤에서
같은 걸 또 꺼내면 새로 알려 주는 것이 없다. 밀려난 씬은 재현 이미지로
돌리고 배지를 단다.

**재사용은 정말 특수한 상황에만 허용한다.** 원장에 `reuse_reason`을 적은
항목만 남긴다. 편의 처음과 끝을 잇는 수미상관처럼, 되풀이 자체가 뜻을
갖는 경우가 아니면 쓰지 않는다.

    python3 scripts/dedupe_assets.py <ledger.json> [-o <out.json>] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ledger", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    data = json.loads(args.ledger.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    by_url: dict[str, list[dict]] = defaultdict(list)
    for e in scenes:
        if e.get("found") and e.get("image_url"):
            by_url[e["image_url"]].append(e)

    dropped, kept_extra = 0, 0
    for url, group in by_url.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda e: e.get("n", 0))
        for e in group[1:]:
            if e.get("reuse_reason"):
                # 되풀이 자체가 뜻을 갖는 경우만 남긴다
                kept_extra += 1
                continue
            e["found"] = False
            e["reason"] = (f"같은 자료가 씬 {group[0]['n']}에 이미 쓰인다 — "
                           f"반복을 피해 재현으로 돌린다")
            e["duplicate_of"] = group[0]["n"]
            e.pop("image_url", None)
            dropped += 1

    out = args.out or args.ledger
    if not args.dry_run:
        out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    found = sum(1 for e in scenes if e.get("found"))
    uniq = len({e.get("image_url") for e in scenes if e.get("found")})
    print(f"  {args.ledger.stem}: 중복 해제 {dropped}건"
          + (f" / 특수 허용 {kept_extra}건" if kept_extra else "")
          + f" → 채택 {found}건, 고유 {uniq}장"
          + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
