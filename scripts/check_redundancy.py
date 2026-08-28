#!/usr/bin/env python3
"""**같은 말을 두 번 하는 문장**을 찾는다 — 원고에서 걷어낼 것.

세모지 시청자 넷이 세 번의 평가에서 세 번 다 같은 처방을 냈다.

    1차  컷을 더 잘 그리는 것보다 덜 그리는 것이 먼저입니다
    2차  이야기가 아니라 화면의 되풀이를 끊는 것
    3차  요약 씬을 지웁니다

그리고 이유를 이렇게 적었다 — **늘어지는 이유는 화면이 나빠서가 아니라
같은 말을 두 번 하기 때문이고, 화면은 그 말을 따라 두 번 그려졌을 뿐이다.**

LG 1편에서 이런 자리가 나왔다.

    956  자리도 허투루 고른 것이 아니었습니다
    990  진주 식산은행 건너편, 사람과 돈이 가장 많이 지나는 길목이었죠
    991  '북평양 남진주'라는 말이 괜히 나온 게 아니었거든요
    957  그러니까 …사람과 돈, 혼례 수요가 모이는 상권 한복판을 택한 겁니다

앞 셋이 하나도 어렵지 않다. 957 은 못 알아들었을까 봐 한 번 더 말해 준
것이고, 그래서 지루하다.

## 반복이 정당한 경우는 하나뿐이다

    앞이 어려웠다   →  한 번 더 쉽게 푸는 것은 친절
    앞이 쉬웠다     →  같은 말을 또 하는 것은 사족

**이건 화면으로 때울 일이 아니다.** 씬을 묶으면 사족 문장이 화면만 줄인
채 그대로 남는다. 원고에서 걷어내야 한다.

자리는 **씬을 쪼개기 전**이다. 쪼갠 뒤에 잡으면 이미 그림이 붙어 늦다.
지금 파이프라인에는 원고를 다 쓴 뒤 이것을 묻는 스텝이 없다.

    python3 scripts/check_redundancy.py EP01
    python3 scripts/check_redundancy.py EP01 --manuscript <원고.md>
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

WINDOW = 16
OVERLAP = 5

PROMPT = """원고에서 **같은 말을 두 번 하는 문장**을 찾습니다.

## 읽을 것

앞에 나온 문장부터 차례로 읽습니다. `▶` 가 붙은 줄만 판정합니다 —
그 앞의 줄들은 맥락으로만 봅니다.

{lines}

## 판정 — 문장마다 하나

```
keep     새로운 것을 말한다. 앞에 없던 사실·장면·판단이 들어 있다
풀이     앞 문장이 어려웠고 이 문장이 처음으로 이해시킨다   ← 반드시 남긴다
사족     앞에서 이미 알아들은 것을 한 번 더 말한다          ← 걷어낸다
```

## 사족을 가르는 물음은 하나입니다

**앞 문장이 어려웠는가.**

어려웠으면 다시 말해 주는 것이 친절입니다. 쉬웠으면 사족입니다.
「진주 식산은행 건너편, 사람과 돈이 가장 많이 지나는 길목」은 어렵지
않습니다. 그러니 그 뒤의 「그러니까 상권 한복판을 택한 겁니다」는 사족입니다.

반대로 「이건 단순한 배짱이 아니었습니다」는 그것만으로는 무슨 말인지
모릅니다. 그 뒤의 「재난이 지나간 뒤 생활이 어떤 순서로 돌아오는지를 읽어
낸 판단이었죠」는 반복이 아니라 **처음으로 이해시키는 문장**이라 `풀이`입니다.

## 사족의 모양

```
그러니까 · 결국 · 요컨대 로 앞을 묶는 문장
앞의 여러 문장을 한 줄로 정리하는 문장
같은 판단을 다른 말로 바꿔 다시 말하는 문장
「~한 게 아니라 ~였다」를 두 번 이상 되풀이하는 자리
```

## 사족처럼 보이지만 반드시 남겨야 하는 것 셋

「앞이 어려웠는가」만 물으면 이 셋을 놓칩니다. LG 1편에서 사족으로 잘못
지목한 다섯 줄이 전부 여기에 해당했고, 시청자 넷이 되돌리라고 했습니다.

**① 숫자를 닫는 줄.** 수치를 던져 놓고 뜻을 안 닫으면 대목이 허공에서
끝납니다. 「다섯 배·오백 가마」 뒤의 「나라 되찾는 일에 통째로 내놨다」는
반복이 아니라 **그 숫자가 왜 대단한지를 매듭짓는 유일한 줄**입니다.

**② 반전을 준비하는 줄.** 반전은 앞을 인정해 줘야 뒤집는 맛이 납니다.
걱정을 늘어놓은 뒤의 「충분히 합리적인 두려움이었죠」는 그 인정이라,
빼면 바로 뒤의 뒤집기가 힘을 잃습니다.

**③ 뒤 문장의 주어가 되는 줄.** 빼면 문법이 아니라 뜻이 끊깁니다.
「상인이 짊어져야 할 질문도 달라졌습니다」를 빼면 다음 문장
「무엇이 팔릴까에서 그치지 않고…」가 누구 얘긴지 붕 뜹니다.

**그래서 앞만 보지 말고 뒤도 보세요.** 이 줄을 지운 뒤 **다음 문장을 소리
내어 읽어** 보고, 붕 뜨거나 힘이 빠지면 `keep` 입니다.

## 조심할 것

**후킹과 마무리는 사족이 아닙니다.** 편을 여는 선언, 챕터를 닫는 한 줄,
다음 편으로 넘기는 문장은 같은 말처럼 보여도 제 몫이 있습니다.

**추론의 결론을 빼지 마세요.** 여러 줄이 단계를 밟아 도달한 결론은 그
대목에서 가장 재미있는 줄입니다. 앞 단계와 같은 뜻으로 보여도, 그것이
없으면 앞 단계들이 왜 나왔는지가 사라집니다.

**결론을 먼저 던지고 푸는 구조를 깨지 마세요.** 그때는 앞의 결론 문장이
아니라 **둘 중 약한 쪽**을 지목합니다. 어느 쪽을 빼야 하는지 적으세요.

**확신이 없으면 keep 입니다.** 걷어내는 쪽이 되돌리기 어렵습니다.

## 낼 것 — JSON만

{{"lines": [
  {{"scene": 씬번호, "verdict": "keep | 풀이 | 사족",
    "same_as": "사족이면 어느 씬의 말과 같은지 씬번호, 아니면 빈 문자열",
    "why": "왜 그렇게 봤는가 한 줄 — 앞이 어려웠는지 쉬웠는지를 반드시 적는다",
    "drop": "사족이면 이 씬을 빼는지, 아니면 앞 씬을 빼는지"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=1800, env=env)
    except Exception:
        return None
    out = r.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(out[i:j + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]

    # 카드는 말이 아니라 화면 장치다 — 판정 대상이 아니다
    seq = [(s["sceneNumber"], (s.get("narration") or "").strip())
           for s in scenes
           if (s.get("narration") or "").strip()
           and not s.get("isChapterCard") and not s.get("isTurnCard")]
    print(f"{ep}  말 {len(seq)}줄에서 되풀이를 찾습니다")

    chunks = []
    i = 0
    while i < len(seq):
        head = max(0, i - OVERLAP)
        chunks.append((head, i, seq[head:i + WINDOW]))
        i += WINDOW

    def run(job):
        head, start, part = job
        L = []
        for n, t in part:
            mark = "▶" if seq.index((n, t)) >= start else " "
            L.append(f"  {mark} 씬{n}: {t}")
        d = ask(PROMPT.format(lines="\n".join(L)))
        return (d or {}).get("lines") or []

    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            rows.extend(r)

    by = {n: t for n, t in seq}
    seen, out = set(), []
    for r in rows:                     # 겹친 구간은 첫 판정만 쓴다
        n = r.get("scene")
        if n in seen or n not in by:
            continue
        seen.add(n)
        out.append(r)

    import collections
    c = collections.Counter(r.get("verdict") for r in out)
    print(f"\n  keep {c['keep']} · 풀이 {c['풀이']} · 사족 {c['사족']}   (본 것 {len(out)})\n")
    drop = [r for r in out if r.get("verdict") == "사족"]
    for r in drop:
        n = r["scene"]
        print(f"  씬{n}  {by[n][:64]}")
        print(f"        같은 말: 씬{r.get('same_as','')} · {r.get('why','')[:70]}")
        if r.get("drop"):
            print(f"        뺄 것: {r['drop'][:70]}")

    f = root / "_imggen" / f"{ep}_redundancy.json"
    f.write_text(json.dumps({"episode": ep, "lines": out}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"\n{f}")
    print(f"  걷어낼 후보 {len(drop)}줄 — 확인 뒤 반영하세요")
    return 0


if __name__ == "__main__":
    sys.exit(main())
