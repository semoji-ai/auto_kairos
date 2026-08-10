#!/usr/bin/env python3
"""이미지 프롬프트가 그 씬의 나레이션과 맞는지 검사한다.

**빈 프롬프트만 막아서는 부족했다.** 채워져 있어도 엉뚱한 장면일 수 있다.
EP02를 검수하니 이런 것들이 나왔다.

    씬 26  나레이션 "기계는 그해 8월 무렵에야 들어옵니다"
           프롬프트 "서류에 도장을 찍는 사업가"          ← 다른 장면
    씬 41·42  프롬프트가 글자 하나까지 같음              ← 복사된 것

생성한 뒤 멀티모달로 잡으면 이미 돈과 시간을 쓴 뒤다. 생성 전에 잡는다.

검사 두 가지
  1. 중복  — 다른 씬과 프롬프트가 같거나 거의 같다
  2. 무관  — 나레이션과 겹치는 말이 하나도 없다

무관 판정은 낱말이 겹치는지만 본다. 은유나 상징은 겹치지 않아도 맞을 수 있으니
**의심 목록**으로 내보내고, 최종 판단은 사람이나 멀티모달 검수에 맡긴다.

    python3 scripts/check_prompt_match.py <project_dir> [-o <out.json>]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# 어느 프롬프트에나 나오는 말 — 겹쳐도 근거가 되지 않는다
STOP = {"한국", "모습", "장면", "배경", "인물", "전경", "중경", "레이어", "분리형",
        "위에", "앞에", "옆에", "사이", "가운데", "화면", "차림", "표정", "그리고",
        "년대", "시대", "당시", "사람", "남성", "여성", "하나", "여러"}
WORD = re.compile(r"[가-힣]{2,}|[A-Za-z]{3,}|\d{4}")


def words(text: str) -> set[str]:
    return {w for w in WORD.findall(text or "") if w not in STOP}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", type=Path)
    ap.add_argument("--sim", type=float, default=0.85,
                    help="이 비율 이상 닮으면 중복으로 본다")
    args = ap.parse_args()

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    targets = [(s["sceneNumber"], (s.get("imageAsset") or {}).get("prompt") or "",
                s.get("narration") or "", s.get("headline") or "")
               for s in scenes
               if (s.get("imageAsset") or {}).get("source") == "generate"]

    dup: list[dict] = []
    seen: dict[str, int] = {}
    for n, p, _, _ in targets:
        key = re.sub(r"\s+", "", p)
        if not key:
            continue
        if key in seen:
            dup.append({"n": n, "same_as": seen[key], "kind": "완전 동일"})
            continue
        for k2, n2 in seen.items():
            if SequenceMatcher(None, key, k2).ratio() >= args.sim:
                dup.append({"n": n, "same_as": n2, "kind": "거의 동일"})
                break
        seen[key] = n

    unrelated: list[dict] = []
    for n, p, narr, head in targets:
        if not p.strip():
            continue
        pw, nw = words(p), words(narr + " " + head)
        common = pw & nw
        if not common:
            unrelated.append({"n": n, "narration": narr[:90], "prompt": p[:90]})

    out = {"duplicate": dup, "unrelated": unrelated}
    if args.out:
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    name = args.project.name
    print(f"  {name}: 생성 {len(targets)}컷 / 중복 {len(dup)} / 무관 의심 {len(unrelated)}")
    for d in dup[:6]:
        print(f"      씬 {d['n']} — 씬 {d['same_as']}와 {d['kind']}")
    for u in unrelated[:6]:
        print(f"      씬 {u['n']} 의심 — {u['narration'][:44]}")
        print(f"                 → {u['prompt'][:44]}")
    return 1 if (dup or unrelated) else 0


if __name__ == "__main__":
    sys.exit(main())
