#!/usr/bin/env python3
"""나레이션에 등장하는 인물을 찾아 cast로 지정한다.

**cast가 비면 캐릭터 시트가 안 붙고, 그러면 스타일 기준 시트의 인물이 그대로
복사된다.** EP01 씬 24에서 실제로 그랬다 — 1930년대 포목점 장면에 기준 시트의
현대 복장 인물이 그려졌다.

인물이 여럿 나오는 12부작을 손으로 지정하기는 어렵다. 이름과 연도를 보고
roster의 어느 시트를 붙일지 고른다. 같은 인물이라도 시기가 다르면 다른 시트다
(구인회 20대 / 40대).

    python3 scripts/auto_cast.py <project_dir> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

YEAR = re.compile(r"(18|19|20)\d{2}")


def load_roster(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def era_year(entry: dict) -> int | None:
    m = YEAR.search(str(entry.get("era") or ""))
    return int(m.group(0)) if m else None


def pick(entries: list[dict], years: set[int]) -> dict:
    """같은 인물의 시트가 여럿이면 씬의 연도에 가장 가까운 것을 고른다."""
    if len(entries) == 1 or not years:
        return entries[0]
    def dist(e: dict) -> int:
        y = era_year(e)
        return min(abs(y - x) for x in years) if y else 9999
    return min(entries, key=dist)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--roster", type=Path, default=Path("_imggen/characters/roster.json"))
    ap.add_argument("--sheets", type=Path, default=Path("_imggen/characters/final3"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roster = load_roster(args.roster)
    by_name: dict[str, list[dict]] = {}
    for e in roster:
        if (args.sheets / f"{e['id']}_sheet.png").exists():
            by_name.setdefault(e["name"], []).append(e)
    if not by_name:
        print("  쓸 수 있는 시트가 없습니다")
        return 1
    name_re = re.compile("|".join(sorted(by_name, key=len, reverse=True)))

    spec = args.project / "scene_specs.json"
    data = json.loads(spec.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    assigned, missing = 0, {}
    for s in scenes:
        if (s.get("imageAsset") or {}).get("source") != "generate" or s.get("cast"):
            continue
        text = " ".join(str(s.get(f) or "") for f in ("narration", "headline"))
        found = list(dict.fromkeys(name_re.findall(text)))
        if not found:
            continue
        years = {int(m.group(0)) for m in YEAR.finditer(text)}
        # 연도가 없으면 앞 씬들의 연도를 물려받는다 — 한 장면이 여러 씬에 걸친다
        if not years:
            for prev in reversed(scenes[:scenes.index(s)][-6:]):
                py = {int(m.group(0)) for m in YEAR.finditer(prev.get("narration") or "")}
                if py:
                    years = py
                    break
        s["cast"] = [pick(by_name[n], years)["id"] for n in found[:3]]
        assigned += 1

    # 시트가 없어 못 붙인 인물 — 이 씬들은 기준 시트 인물이 복사될 위험이 있다
    known = set(by_name)
    ALL = re.compile(r"(구[인철자본광재]\w|허[만준창신]\w|안희제|이병철|정주영|박정희)")
    for s in scenes:
        if (s.get("imageAsset") or {}).get("source") != "generate" or s.get("cast"):
            continue
        for n in set(ALL.findall(" ".join(str(s.get(f) or "")
                                          for f in ("narration", "headline")))):
            if n not in known:
                missing.setdefault(n, []).append(s["sceneNumber"])

    if not args.dry_run:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(1 for s in scenes if s.get("cast"))
    print(f"  {args.project.name}: cast 지정 +{assigned} (전체 {total}씬)"
          + (" [dry-run]" if args.dry_run else ""))
    for n, ns in sorted(missing.items(), key=lambda x: -len(x[1])):
        print(f"      ⚠ 시트 없음 — {n}: 씬 {ns[:6]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
