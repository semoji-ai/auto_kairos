#!/usr/bin/env python3
"""다시 쓴 원고가 **사실을 흔들지 않았는지** 본다.

말투를 고치다 보면 수치가 슬며시 바뀌거나, 「후대 회고는」 같은 귀속이
떨어져 나가 전해지는 이야기가 확정처럼 읽힌다. 눈으로는 안 잡힌다 —
문장이 자연스러워졌기 때문에 오히려 더 안 보인다.

네 가지를 본다.

  ① 근거 없는 수치   옛 원고에도 리서치에도 없는 숫자가 생겼나
  ② 사라진 수치      있던 숫자가 없어졌나
  ③ 귀속이 떨어졌나  신뢰도 낮은 대목에서 「전해집니다」가 빠졌나
  ④ 홀로 서는 단정   씬을 나누면 갈라질 문장이 근거 없이 단정하나
                     — **다투는 것**만 본다. 자료가 뒷받침하는 값이나
                     인물의 결까지 「전해집니다」를 달면 말맛이 죽는다

④가 특히 조용하다. 한 씬 안에서는 뒤 문장이 귀속을 달고 있어 멀쩡해
보이는데, 문장 단위로 나누면 앞 문장이 홀로 서면서 확정문이 된다.

    python3 scripts/check_rewrite_facts.py EP02
    python3 scripts/check_rewrite_facts.py EP02 --facts _imggen/ep02_facts.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

# 귀속을 나타내는 말 — 이 중 하나가 있으면 「전해지는 이야기」로 읽힌다
ATTRIB = ("전해", "전합니다", "라고 합니다", "고 합니다", "기록", "자료에", "전기",
          "보도", "따르면", "회고", "증언", "적혀", "적힌", "알려")

# 귀속이 반드시 필요한 자리 — **다투는 것**만이다.
#
# 자료가 뒷받침하는 값이나 인물의 결까지 「전해집니다」를 달면 문장이
# 늘어지고 말맛이 죽는다. 「5원 거스름돈까지 아끼던 사람이었는데요」는
# 그대로 두는 편이 낫다.
#
# 다투는 자리란 이런 것이다.
#   · 제3자가 한 말·행동을 옮길 때 (특히 유명인)
#   · 회사 스스로 쓴 기록에만 있는 일화
#   · 자료마다 값이 갈릴 때
NEEDS_ATTRIB = re.compile(
    r"(대통령|장관|의원"                      # 유명인의 말·행동
    r"|달라고 했|말했다고|라고 했다고"          # 남의 말을 옮김
    r"|일화|구전"                              # 스스로 일화라 부르는 것
    r")")

NUM = re.compile(r"\d[\d,\.]*")
SENT = re.compile(r"(?<=[.!?])\s+")


def load_new(root: Path, ep: str) -> dict:
    out = {}
    d = root / "_imggen" / f"{ep.lower()}_rewrite"
    for f in sorted(d.glob("ch*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")).get("scenes", []):
            fr = r.get("from")
            fr = fr if isinstance(fr, list) else [fr]
            fr = [x for x in fr if isinstance(x, int)]
            if fr:
                out[fr[0]] = r.get("narration", "")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--facts", help="자료 파일(.md) — 이번에 넣기로 한 것")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    cur = {s["sceneNumber"]: s for s in
           json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
    new = load_new(root, ep)
    if not new:
        raise SystemExit(f"다시 쓴 원고가 없습니다: _imggen/{ep.lower()}_rewrite")

    old_all = " ".join((s.get("narration") or "") for s in cur.values())
    base = old_all
    if args.facts and Path(args.facts).is_file():
        base += Path(args.facts).read_text(encoding="utf-8")
    for name in ("targeted_claims.json", "research_report.json", "factcheck_report.json"):
        p = proj / name
        if p.is_file():
            base += p.read_text(encoding="utf-8")
    for d in ("chapter_facts",):
        p = proj / d
        if p.is_dir():
            for f in p.glob("*.json"):
                base += f.read_text(encoding="utf-8")

    new_all = " ".join(new.values())
    bad = 0

    print(f"{ep}  다시 쓴 씬 {len(new)}개\n")

    print("① 근거 없는 수치")
    hits = []
    for n, t in sorted(new.items()):
        for m in set(NUM.findall(t)):
            if len(m) > 1 and m not in base:
                hits.append((n, m, t[:70]))
    for n, m, t in hits:
        print(f"   씬{n:>4} «{m}»  {t}")
    print(f"   {'없음' if not hits else str(len(hits)) + '건 ✗'}")
    bad += len(hits)

    print("\n② 사라진 수치")
    lost = [x for x in set(NUM.findall(old_all)) if len(x) > 1 and x not in new_all]
    print(f"   {sorted(lost) if lost else '없음'}")

    print("\n③ 귀속이 떨어진 대목")
    hits = []
    for n, t in sorted(new.items()):
        old = (cur.get(n, {}).get("narration") or "")
        had = any(a in old for a in ATTRIB)
        has = any(a in t for a in ATTRIB)
        if had and not has:
            hits.append((n, t[:80]))
    for n, t in hits:
        print(f"   씬{n:>4}  {t}")
    print(f"   {'없음' if not hits else str(len(hits)) + '건 ✗'}")
    bad += len(hits)

    print("\n④ 나누면 홀로 설 단정문")
    print("   (한 씬 안에서는 뒤 문장이 귀속을 다니 멀쩡해 보이지만,")
    print("    문장 단위로 나누면 앞 문장이 확정문이 된다)")
    hits = []
    for n, t in sorted(new.items()):
        sents = [s for s in SENT.split(t.strip()) if s]
        if len(sents) < 2:
            continue
        whole = any(a in t for a in ATTRIB)
        if not whole:
            continue
        for s in sents:
            if any(a in s for a in ATTRIB):
                continue
            if NEEDS_ATTRIB.search(s):
                hits.append((n, s.strip()[:76]))
    for n, s in hits:
        print(f"   씬{n:>4}  {s}")
    print(f"   {'없음' if not hits else str(len(hits)) + '건 — 확인 필요'}")

    print(f"\n{'통과' if bad == 0 else f'{bad}건 고쳐야 합니다'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
