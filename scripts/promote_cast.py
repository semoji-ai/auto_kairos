#!/usr/bin/env python3
"""people에 적힌 실명 인물을 cast로 올린다 — 시트가 있으면 시트를 쓴다.

**같은 인물을 어떤 씬은 그림으로, 어떤 씬은 글로 그리면 얼굴이 달라진다.**
EP01 시청자 평가에서 「구인회의 얼굴형과 안경이 너무 자주 바뀐다」는 지적이
나왔고, 원인이 이것이었다. 씬 36·37은 시트를 붙였는데 씬 35·49·65는
people에 「구인회 (남), 40대, 가는 은테 안경…」으로 글만 적혀 있었다.

글은 매번 재해석된다. 시트가 있는 인물은 반드시 시트를 붙인다.

연령대가 여럿인 인물(구인회 20대/40대)은 씬의 연도로 고른다.

    python3 scripts/promote_cast.py <project_dir> [--dry-run]
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

YEAR = re.compile(r"(18|19|20)\d{2}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--roster", type=Path, default=Path("_imggen/characters/roster.json"))
    ap.add_argument("--sheets", type=Path, default=Path("_imggen/characters/final_v2_up"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    roster = json.loads(args.roster.read_text(encoding="utf-8"))
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

    def pick(entries: list[dict], years: set[int]) -> dict:
        if len(entries) == 1 or not years:
            return entries[0]
        def dist(e: dict) -> int:
            m = YEAR.search(str(e.get("era") or ""))
            return min(abs(int(m.group(0)) - y) for y in years) if m else 9999
        return min(entries, key=dist)

    moved = 0
    for i, s in enumerate(scenes):
        if (s.get("imageAsset") or {}).get("source") != "generate" or s.get("cast"):
            continue
        people = s.get("people") or []
        found = list(dict.fromkeys(n for p in people for n in name_re.findall(p)))
        if not found:
            continue
        text = " ".join(str(s.get(f) or "") for f in ("narration", "headline"))
        years = {int(m.group(0)) for m in YEAR.finditer(text)}
        if not years:                       # 앞 씬의 연도를 물려받는다
            for prev in reversed(scenes[:i][-6:]):
                py = {int(m.group(0)) for m in YEAR.finditer(prev.get("narration") or "")}
                if py:
                    years = py
                    break
        s["cast"] = [pick(by_name[n], years)["id"] for n in found[:3]]
        # 시트로 그리는 인물은 people에서 뺀다 — 글과 그림이 충돌한다
        keep = [p for p in people if not name_re.search(p)]
        if keep:
            s["people"] = keep
        else:
            s.pop("people", None)
        moved += 1

    if not args.dry_run:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {args.project.name}: cast 승격 {moved}씬" + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
