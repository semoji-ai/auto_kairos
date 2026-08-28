#!/usr/bin/env python3
"""**이 줄을 빼면 어떤가**를 시청자에게 그 자리에서 묻는다.

편 전체 점수는 둔하다. 세모지 시청자 기준 100점은 네 번 재서 69·66·68·70 이
나왔다 — 흔들림이 ±3 쯤이라 141줄 중 11줄을 빼도 움직이지 않는다.
움직이지 않는 것이 「효과가 없다」인지 「못 잰다」인지 구분이 안 된다.

그래서 **그 자리만 떼어 내 앞뒤와 함께 보여 주고 둘 중 어느 쪽이 나은지**
묻는다. 같은 사람이 같은 자리를 두 판으로 읽으니 비교가 정확하다.

    python3 scripts/ask_removal.py EP01
    python3 scripts/ask_removal.py EP01 --removed _imggen/EP01_removed_scenes.json

`_imggen/<EP>_removed_scenes.json` 은 빼면서 남긴 복원 파일이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402
from youtube_eval import PERSONAS  # noqa: E402
from viewer_eval import ask  # noqa: E402

BEFORE, AFTER = 3, 2

PROMPT = """{personas}

## 물을 것

이 편에서 한 줄을 빼려고 합니다. **뺀 쪽이 나은지** 그 자리만 놓고 봅니다.

같은 대목을 두 판으로 보여 드립니다. 소리 내어 읽어 보고 답하세요.

{cases}

## 판정 — 대목마다 하나

```
빼는 게 낫다   그 줄이 없어도 다 알아들었고, 없으니 더 빨라진다
두는 게 낫다   그 줄이 없으면 못 알아듣거나, 리듬이 끊기거나, 마무리가 허전하다
```

## 볼 것

**뺐을 때 잃는 것이 있는가.** 사실이 사라졌는지, 이해가 막히는지,
챕터를 닫는 맛이 없어지는지 봅니다. 아무것도 안 잃으면 빼는 게 낫습니다.

**말맛과 리듬도 봅니다.** 긴 문장이 이어지다 짧게 끊어 주는 자리였다면,
없앴을 때 숨 쉴 곳이 사라집니다. 그건 잃는 것입니다.

**빠져서 좋아지는 것도 적으세요.** 지루함이 줄었는지, 다음으로 빨리
넘어가는지.

## 낼 것 — JSON만

{{"cases": [
  {{"scene": 씬번호, "verdict": "빼는 게 낫다 | 두는 게 낫다",
    "lost": "뺐을 때 잃는 것 (없으면 빈 문자열)",
    "gained": "뺐을 때 좋아지는 것",
    "why": "한 줄로"}}
]}}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--removed")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    cur = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    rf = Path(args.removed) if args.removed else root / "_imggen" / f"{ep}_removed_scenes.json"
    removed = json.loads(rf.read_text(encoding="utf-8"))["removed"]

    # 뺀 씬을 제자리에 도로 꽂아 「빼기 전」을 되살린다
    full = list(cur)
    for r in sorted(removed, key=lambda x: x["index"]):
        full.insert(r["index"], r["scene"])
    say = [(s["sceneNumber"], (s.get("narration") or "").strip())
           for s in full if (s.get("narration") or "").strip()]
    pos = {n: i for i, (n, _) in enumerate(say)}

    print(f"{ep}  뺀 {len(removed)}줄을 그 자리에서 묻습니다")

    def case(r):
        n = r["scene"]["sceneNumber"]
        if n not in pos:
            return ""
        i = pos[n]
        a = say[max(0, i - BEFORE):i]
        b = say[i + 1:i + 1 + AFTER]
        L = [f"### 대목 — 씬{n}", "", "**있는 판**"]
        L += [f"  {t}" for _, t in a]
        L += [f"  ▶ {say[i][1]}"]
        L += [f"  {t}" for _, t in b]
        L += ["", "**뺀 판**"]
        L += [f"  {t}" for _, t in a]
        L += [f"  {t}" for _, t in b]
        return "\n".join(L)

    cases = [c for c in (case(r) for r in removed) if c]
    chunks = [cases[i:i + 4] for i in range(0, len(cases), 4)]

    def run(chunk):
        return (ask(PROMPT.format(personas=PERSONAS, cases="\n\n".join(chunk)))
                or {}).get("cases") or []

    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            rows.extend(r)

    keep = [r for r in rows if r.get("verdict") == "두는 게 낫다"]
    print(f"\n  빼는 게 낫다 {len(rows) - len(keep)} · 두는 게 낫다 {len(keep)}\n")
    for r in rows:
        mark = "되돌림" if r in keep else "뺀다  "
        print(f"  [{mark}] 씬{r.get('scene')}  {r.get('why','')[:66]}")
        if (r.get("lost") or "").strip():
            print(f"            잃는 것: {r['lost'][:66]}")
        if (r.get("gained") or "").strip():
            print(f"            얻는 것: {r['gained'][:66]}")

    f = root / "_imggen" / f"{ep}_removal_ask.json"
    f.write_text(json.dumps({"episode": ep, "cases": rows}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"\n{f}")
    if keep:
        print(f"  되돌릴 씬: {sorted(r['scene'] for r in keep)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
