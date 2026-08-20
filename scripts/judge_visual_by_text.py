#!/usr/bin/env python3
"""나레이션만 보고 재연이냐 인포그래픽이냐를 정한다 — 그림이 없어도.

그림을 그려 견주는 것이 가장 정확하지만, 그림이 없는 씬은 견줄 수가 없다.
그래서 글만 보고 정하는 길이 필요하다.

앞서 script-director가 글로 정했다가 크게 틀렸다(35씬 중 5씬만 맞음). 원인은
글로 판단해서가 아니라 **기준이 하나뿐이어서**였다 — 「어느 쪽이 이해가
빠른가」만 물으면 도해가 거의 언제나 이긴다.

EP01을 실제로 그려 견줘 보고 알아낸 것을 기준으로 삼는다.

  · 기본값은 **재연**이다. 인포그래픽이 예외다.
  · 인포그래픽은 아래 넷 중 하나에 해당할 때만.
      ① 「없음」을 보여야 한다      ② 수치가 합쳐지거나 환산된다
      ③ 둘을 견준다                ④ 구조가 바뀐다
  · 사람이 무엇을 하거나 감정이 실린 순간이면 그 넷에 걸려도 재연이다.

`--eval` 로 돌리면 이미 그려서 견준 판정과 맞춰 보고 정확도를 잰다.

    python3 scripts/judge_visual_by_text.py EP01 --eval
    python3 scripts/judge_visual_by_text.py EP03
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

PROMPT = """다큐멘터리 한 장면을 **재연 그림**으로 보여줄지 **인포그래픽**으로
보여줄지 정합니다.

## 이 장면

나레이션: {narration}

앞 장면: {prev}
뒤 장면: {next}

## 기본값은 재연입니다

인포그래픽은 예외입니다. 실제로 68씬을 그려서 견줘 보니, 도해가 이해는 빠른데
**보고 싶지가 않았습니다.** 도해가 이어지면 사람이 사라지고, 사람이 사라지면
이야기가 아니라 발표가 됩니다.

## 인포그래픽이 되는 자리는 넷뿐입니다

① **「없음」을 보여야 한다** — 「근거가 확인되지 않았다」, 「기록이 남아 있지
   않다」. 재연으로는 그릴 수 없습니다. 이것이 가장 확실한 자리입니다.
② **수치가 합쳐지거나 환산된다** — 2,000 + 1,800 = 3,800 = 쌀 844가마
③ **둘을 견준다** — 내려놓은 것 ↔ 새로 잡은 것, 국산 80대 ↔ 외제 1만 2,000대
④ **구조가 바뀐다** — 기둥 둘이 빠져도 남는 것

## 넷에 걸려도 재연인 경우

- 사람이 무엇을 **한다** (지붕으로 올라간다, 어른들 앞에서 말한다)
- 감정이 실린 순간
- 공간의 공기가 내용이다
- 앞뒤가 사람이 이어지는 구간이다 — 도해가 끼면 사람이 끊긴다

숫자가 나온다고 다 도해가 아닙니다. 「49대가 팔렸다」는 수치지만 그 장면의
핵심이 사람의 막막함이라면 재연입니다.

## 낼 것 — JSON만

{{"pick": "scene | info",
  "pattern": "없음 | 합산환산 | 대비 | 구조 | 해당없음",
  "why": "한 문장"}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=300, env=env)
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
    ap.add_argument("--scenes")
    ap.add_argument("--eval", action="store_true",
                    help="그려서 견준 판정과 맞춰 보고 정확도를 잰다")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    order = [s.get("sceneNumber") for s in scenes]
    by_n = {s.get("sceneNumber"): s for s in scenes}

    truth = {}
    pick_dir = root / "_imggen" / f"{ep.lower()}_pick"
    for f in pick_dir.glob("s*.json") if pick_dir.exists() else []:
        try:
            truth[int(f.stem[1:])] = json.loads(f.read_text(encoding="utf-8")).get("pick")
        except Exception:
            continue

    out_dir = root / "_imggen" / f"{ep.lower()}_textjudge"
    out_dir.mkdir(parents=True, exist_ok=True)

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    if args.eval:
        want = set(truth)                      # 정답이 있는 씬만
    targets = [n for n in order
               if (want is None or n in want)
               and (by_n[n].get("narration") or "").strip()
               and not by_n[n].get("isChapterCard")]

    def neighbor(n: int, step: int) -> str:
        i = order.index(n) + step
        return (by_n[order[i]].get("narration") or "")[:90] if 0 <= i < len(order) else ""

    def run(n: int):
        f = out_dir / f"s{n:03d}.json"
        if f.exists():
            return n, json.loads(f.read_text(encoding="utf-8"))
        d = ask(PROMPT.format(narration=(by_n[n].get("narration") or "")[:400],
                              prev=neighbor(n, -1), next=neighbor(n, 1)))
        if d:
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return n, d

    print(f"{ep}  {len(targets)}씬 판단")
    got = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, d in ex.map(run, targets):
            if d:
                got[n] = d

    if not args.eval:
        info = sorted(n for n, d in got.items() if d.get("pick") == "info")
        print(f"  인포그래픽: {info}")
        print(f"  재연: {len(got) - len(info)}씬")
        return 0

    # 그려서 견준 판정과 맞춰 본다
    hit = miss_info = miss_scene = 0
    wrong = []
    for n, d in sorted(got.items()):
        t = "info" if truth.get(n) == "info" else "scene"   # overlay 는 scene 쪽으로 본다
        p = d.get("pick")
        if p == t:
            hit += 1
        else:
            wrong.append((n, p, t, d.get("pattern"), d.get("why", "")[:56]))
            if p == "info":
                miss_info += 1
            else:
                miss_scene += 1
    tot = len(got)
    print(f"\n맞음 {hit}/{tot}  ({hit / tot * 100:.0f}%)")
    print(f"  글은 인포라 했는데 그림은 재연 (남발) : {miss_info}")
    print(f"  글은 재연이라 했는데 그림은 인포 (놓침): {miss_scene}")
    for n, p, t, pat, why in wrong:
        print(f"   씬{n:>3} 글={p:5s} 그림={t:5s} [{pat}] {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
