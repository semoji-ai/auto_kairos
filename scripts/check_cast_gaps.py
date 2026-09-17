#!/usr/bin/env python3
"""시트가 있는 인물인데 cast에 안 잡힌 씬을 찾는다 — 생성 전에.

같은 인물을 어떤 씬은 시트로, 어떤 씬은 글로 그리면 얼굴이 달라진다.
LG편 시청자 평가에서 그 지적이 나왔고 76씬이 그 상태였다.

세 가지를 본다.
  1. people에 실명이 적혔는데 cast가 빈 씬
  2. 나레이션에 실명이 나오는데 cast도 people도 없는 씬
  3. 같은 인물이 실물 사진과 재현 이미지에 섞여 나오는 편
     (실사진 속 얼굴과 재현 얼굴이 다르면 시청자는 다른 사람으로 본다)

    python3 scripts/check_cast_gaps.py <project_dir>
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--roster", type=Path, default=Path("_imggen/characters/roster.json"))
    ap.add_argument("--sheets", type=Path, default=Path("_imggen/characters/sheets"))
    args = ap.parse_args()

    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    names = {e["name"] for e in roster
             if (args.sheets / f"{e['id']}_sheet.png").exists()}
    if not names:
        print("  쓸 수 있는 시트가 없습니다")
        return 1
    pat = re.compile("|".join(sorted(names, key=len, reverse=True)))

    scenes = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = scenes.get("scenes", scenes)

    in_people, in_narr = [], []
    real, drawn = defaultdict(list), defaultdict(list)
    for s in scenes:
        ia = s.get("imageAsset") or {}
        n = s.get("sceneNumber")
        hits = set(pat.findall(" ".join(str(s.get(f) or "")
                                        for f in ("narration", "headline"))))
        if ia.get("source") == "search" and hits:
            for h in hits:
                real[h].append(n)
            continue
        if ia.get("source") != "generate":
            continue
        if s.get("cast"):
            for h in hits:
                drawn[h].append(n)
            continue
        if any(pat.search(p) for p in (s.get("people") or [])):
            in_people.append(n)
        elif hits:
            in_narr.append(n)

    mixed = {k: (real[k], drawn[k]) for k in real if k in drawn}
    name = args.project.name
    print(f"  {name}")
    print(f"    people에 실명, cast 없음   {len(in_people)}씬 {in_people[:10]}")
    print(f"    나레이션에 실명, 둘 다 없음 {len(in_narr)}씬 {in_narr[:10]}")
    for k, (r, d) in mixed.items():
        print(f"    ⚠ {k}: 실물 {r[:4]} ↔ 재현 {d[:6]} — 같은 사람으로 보이는지 확인")
    return 1 if (in_people or in_narr) else 0


if __name__ == "__main__":
    sys.exit(main())
