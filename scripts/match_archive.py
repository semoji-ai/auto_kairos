#!/usr/bin/env python3
"""아카이브 목록을 씬에 이어 붙인다 — 자료가 있는 쪽에서 시작하는 방식.

**씬을 보고 "이 장면에 맞는 사진이 있나" 묻는 방식은 씬이 추상적이면 빈손이다.**
EP01은 55씬을 조사해 9건, EP03은 42씬에 8건이었다. 1950~70년대처럼 공감대가
가장 클 시대에서 오히려 자료를 못 건졌다.

그래서 순서를 뒤집는다. 국가기록원·e영상역사관을 먼저 훑어 **실제로 있는 자료**
목록을 만들고(`archive_*.json`), 그 목록에 맞는 씬을 찾는다.

**붙이는 기준은 그대로다** — 그 씬이 말하는 바로 그 대상·사건·시점이어야 한다.
연도가 어긋나거나 낱말 하나만 겹치는 것은 붙이지 않는다(direction-standard 1-0절).

    python3 scripts/match_archive.py <project_dir> -a _imggen/archive_*.json -o <out.json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

YEAR = re.compile(r"(18|19|20)\d{2}")


def scene_years(scene: dict) -> set[int]:
    text = " ".join(str(scene.get(f) or "") for f in ("narration", "headline"))
    return {int(m.group(0)) for m in YEAR.finditer(text)}


def item_year(item: dict) -> int | None:
    m = YEAR.search(str(item.get("year") or ""))
    return int(m.group(0)) if m else None


def score(scene: dict, item: dict) -> tuple[int, list[str]]:
    """겹치는 근거를 센다. 근거가 약하면 붙이지 않는다."""
    text = " ".join(str(scene.get(f) or "") for f in ("narration", "headline"))
    ia = scene.get("imageAsset") or {}
    text += " " + str(ia.get("prompt") or "") + " " + str(ia.get("query") or "")

    why = []
    kw = [k for k in (item.get("keywords") or []) if len(k) >= 2 and k in text]
    if kw:
        why.append("낱말 " + "·".join(kw[:3]))

    sy, iy = scene_years(scene), item_year(item)
    year_ok = False
    if iy and sy:
        if iy in sy:
            why.append(f"{iy}년 일치")
            year_ok = True
        elif min(abs(iy - y) for y in sy) <= 2:
            why.append(f"{iy}년 근접")

    # 제목에 쓰인 고유명사가 씬에도 나오는가
    subj = str(item.get("subject") or "")
    proper = [w for w in re.findall(r"[가-힣A-Za-z0-9\-]{2,}", subj)
              if len(w) >= 2 and w in text]
    if len(proper) >= 2:
        why.append("대상 " + "·".join(proper[:3]))

    n = len(kw) + (2 if year_ok else 0) + (2 if len(proper) >= 2 else 0)
    return n, why


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-a", "--archive", nargs="+", type=Path, required=True)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--min-score", type=int, default=4,
                    help="이 점수 미만은 붙이지 않는다 (기본 4 — 근거 둘 이상)")
    args = ap.parse_args()

    items = []
    for f in args.archive:
        if f.exists():
            items += json.loads(f.read_text(encoding="utf-8")).get("items", [])
    if not items:
        print("  아카이브 목록이 비어 있습니다")
        return 1

    scenes = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = scenes.get("scenes", scenes)

    used: set[str] = set()
    out = []
    for s in scenes:
        best, best_item, best_why = 0, None, []
        for it in items:
            u = it.get("image_url")
            if not u or u in used:
                continue
            n, why = score(s, it)
            if n > best:
                best, best_item, best_why = n, it, why
        if best >= args.min_score and best_item:
            used.add(best_item["image_url"])
            out.append({
                "n": s["sceneNumber"], "found": True,
                "image_url": best_item["image_url"], "page_url": best_item.get("page_url"),
                "holder": best_item.get("holder"), "license": best_item.get("license"),
                "checked": best_item.get("checked"), "desc": best_item.get("subject"),
                "relevance": "; ".join(best_why), "match_score": best,
            })

    args.out.write_text(json.dumps({"scenes": out}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"  {args.project.name}: 목록 {len(items)}건 → {len(out)}씬에 연결")
    return 0


if __name__ == "__main__":
    sys.exit(main())
