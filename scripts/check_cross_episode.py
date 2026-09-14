#!/usr/bin/env python3
"""편 사이에 같은 이야기를 두 번 하고 있는지 본다.

한 편 안의 되풀이는 `check_redundancy.py` 가 잡는다. 이 검사는 **편과 편
사이**를 본다. 시리즈는 한 편씩 만들기 때문에, 앞 편에 이미 있는 이야기를
다음 편이 또 하는 것을 아무도 보지 못한다.

**되짚기와 중복은 다르다.**

앞 편 이야기를 짧게 풀고 넘어가는 것은 필요하다. 그것이 없으면 중간부터 본
사람이 따라오지 못하고, 시리즈가 한 덩어리로 읽히지 않는다. LG 12부작을
실측해 건강한 되짚기의 모양을 얻었다.

    소재 하나당 1~2 문장    그리고 곧바로 그 편의 논지로 이어진다

    EP12  「홍수로 비단이 젖었을 때 구인회는 도망치지 않았습니다」  ← 한 줄
          「크림통과 빗을 뽑던 플라스틱 기술이 그대로 라디오의 겉이
            된 거죠」                                          ← 한 줄

반대로 **문장이 글자까지 같으면 중복이다.** 실측에서 두 편이 이런 문장을
공유하고 있었다.

    「진주의 만석꾼, 허만정.」
    「그런데 허만정은 돈만 댄 게 아닙니다.」

같은 재료를 두 편이 나눠 쓰면 시청자는 같은 이야기를 두 번 듣는다.
어느 편이 그 이야기의 주인인지 정하고, 다른 편은 한 줄로 줄인다.

    python3 scripts/check_cross_episode.py                 # 시리즈 전체
    python3 scripts/check_cross_episode.py --min-ratio 0.8 # 더 느슨하게
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import get_workspace_dir  # noqa: E402

# 되짚기로 넘어갈 수 있는 한도. 이보다 많으면 그 편이 그 이야기를 「하고」 있는 것이다.
BRIDGE_MAX = 2
# 문장이 이만큼 닮으면 같은 문장으로 본다.
SAME_RATIO = 0.85
# 너무 짧은 문장은 우연히 닮는다 (「그런데,」 같은 반전 카드).
MIN_LEN = 14


def sentences(spec: Path) -> list[str]:
    try:
        scenes = json.loads(spec.read_text(encoding="utf-8"))["scenes"]
    except Exception:
        return []
    out = []
    for s in scenes:
        for x in re.split(r"(?<=[.?!다요죠])\s+", (s.get("narration") or "").strip()):
            x = x.strip()
            if len(re.sub(r"\s", "", x)) >= MIN_LEN:
                out.append(x)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--glob", default="*lg_brand_encyclopedia*",
                    help="어느 프로젝트들을 한 시리즈로 볼 것인가")
    ap.add_argument("--min-ratio", type=float, default=SAME_RATIO)
    args = ap.parse_args()

    root = get_workspace_dir() / "output"
    eps: dict[str, list[str]] = {}
    for d in sorted(root.glob(args.glob)):
        s = sentences(d / "scene_specs.json")
        if s:
            eps[d.name.split("_")[-1]] = s
    if len(eps) < 2:
        print("견줄 편이 둘 이상 있어야 합니다")
        return 1

    print(f"시리즈 {len(eps)}편 — {' · '.join(eps)}\n")

    # ── 같은 문장을 나눠 쓰는 편
    names = list(eps)
    dup: dict[tuple[str, str], list[tuple[str, str, float]]] = defaultdict(list)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for x in eps[a]:
                for y in eps[b]:
                    r = difflib.SequenceMatcher(None, x, y).ratio()
                    if r >= args.min_ratio:
                        dup[(a, b)].append((x, y, r))

    if dup:
        print("■ 같은 문장을 두 편이 나눠 쓴다 — 한쪽으로 몰아야 합니다\n")
        for (a, b), rows in sorted(dup.items(), key=lambda kv: -len(kv[1])):
            print(f"  {a} ↔ {b}   {len(rows)}문장")
            for x, y, r in rows[:4]:
                print(f"     {r*100:.0f}%  {a}: {x[:70]}")
                print(f"          {b}: {y[:70]}")
            if len(rows) > 4:
                print(f"     … 그 밖 {len(rows)-4}문장")
            print()
    else:
        print("■ 같은 문장을 나눠 쓰는 편 없음 ✓\n")

    print("  되짚기는 잘못이 아닙니다. 앞 편을 한 줄로 풀고 이 편의 논지로")
    print(f"  넘어가는 것은 시리즈의 문법입니다. 소재 하나당 {BRIDGE_MAX}문장까지 봅니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
