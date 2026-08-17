#!/usr/bin/env python3
"""한 화면 요소가 넷을 넘는 인포그래픽 씬을 줄인다.

다섯을 넘으면 배치가 성기고 시선이 흩어진다(규칙 5). 줄이는 방법은 둘이고,
어느 쪽인지는 **뜻을 봐야** 정해진다.

  합친다  「빗·세면기·대야」가 각각이 아니라 「생활용품으로 번졌다」가 뜻이면
          한 덩어리로 그린다 (규칙 1)
  덜어낸다 다른 요소가 이미 보여주는 것이면 뺀다

그래서 기계로 자르지 않고 규칙을 준 채 코덱스에 맡긴다. 낱개가 의미인 것을
합쳐 버리면 「많다」가 「세 개」로 읽히던 실패를 반대 방향으로 반복한다.

    python3 scripts/fix_info_overflow.py EP03
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

MAX = 4

PROMPT = """인포그래픽 씬의 요소가 너무 많습니다. 각 씬을 **{max}개 이하**로 줄입니다.

## 규칙

**1. 하나의 뜻 = 하나의 에셋.** 「쌀 844가마」는 포대 한 개가 아니라 쌓인
더미 하나입니다. 여러 개로 보여야 하는 것을 낱개로 자르면 「많다」가
「세 개」로 읽힙니다. 반대로 **낱개가 뜻일 때는 합치면 안 됩니다** —
「3대에 걸쳐」는 인장이 하나씩 찍히는 것이 뜻입니다.

**2. 다른 요소가 이미 보여주는 것은 덜어냅니다.** 비교 대상 둘을 마주 놓았다면
「포장 형태」 같은 기준은 그 둘이 이미 보여주고 있습니다.

**3. 은유는 시청자가 즉시 아는 것만.** 톱니바퀴=생산 능력, 레일=영역처럼
설명을 들어야 아는 것은 그 편에 실제로 있던 물건으로 바꿉니다.

**4. 프롬프트는 긍정형으로만.** 「문자 없음」·「배경 없음」처럼 빼고 싶은 것을
부정문으로 적으면 그 단어가 오히려 그려집니다. 「매끈한 빈 색면」처럼 적습니다.

## 대상

{path} 의 아래 씬들입니다. 각 씬의 `narration`·`why`·`composition`을 읽고
무엇이 뜻인지 판단하세요.

{scenes}

## 낼 것

{out} 에 이렇게 저장합니다. **줄인 씬만** 넣습니다.

{{"scenes":[
  {{"n":0,
    "assets":[{{"id":"","prompt":"","role":""}}],
    "composition":{{"form":"","note":""}},
    "labels":[],
    "why_reduced":"무엇을 합치고 무엇을 덜어냈는지 한 문장"}}]}}

`assets`는 {max}개 이하여야 합니다. `composition.note`와 `labels`도 줄인
구성에 맞게 다시 씁니다.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--timeout", type=int, default=5400)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    f = root / "_imggen" / f"{args.ep}_mode.json"
    data = json.loads(f.read_text(encoding="utf-8"))

    over = [s for s in data.get("scenes", [])
            if s.get("mode") == "infographic" and len(s.get("assets") or []) > MAX]
    if not over:
        print(f"{args.ep}  줄일 씬 없음")
        return 0

    src = root / "_imggen" / f"{args.ep}_overflow_in.json"
    dst = root / "_imggen" / f"{args.ep}_overflow_out.json"
    src.write_text(json.dumps(over, ensure_ascii=False, indent=1), encoding="utf-8")

    prompt = PROMPT.format(
        max=MAX, path=src.relative_to(root), out=dst.relative_to(root),
        scenes="\n".join(f"  씬{s['n']}  요소 {len(s['assets'])}개" for s in over),
    )
    log = root / "_imggen" / f"{args.ep}_overflow.log"
    with log.open("w", encoding="utf-8") as fh:
        subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write",
             "-c", "model_reasoning_effort=high", prompt],
            cwd=root, stdin=subprocess.DEVNULL, stdout=fh, stderr=subprocess.STDOUT,
            timeout=args.timeout,
        )
    if not dst.exists():
        print(f"{args.ep}  결과 없음 — {log}")
        return 1

    fixed = {s["n"]: s for s in json.loads(dst.read_text(encoding="utf-8"))["scenes"]}
    shutil.copy2(f, f.with_suffix(f".json.bak_overflow"))
    done = 0
    for s in data["scenes"]:
        r = fixed.get(s.get("n"))
        if not r:
            continue
        if len(r.get("assets") or []) > MAX:
            print(f"  ! 씬{s['n']}  여전히 {len(r['assets'])}개 — 그대로 둔다")
            continue
        s["assets"] = r["assets"]
        if r.get("composition"):
            s["composition"] = r["composition"]
        if r.get("labels"):
            s["labels"] = r["labels"]
        s["why_reduced"] = r.get("why_reduced", "")
        done += 1
        print(f"  ✓ 씬{s['n']}  → {len(r['assets'])}개  {r.get('why_reduced', '')[:60]}")

    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{args.ep}  {done}/{len(over)}씬 줄임")
    return 0 if done == len(over) else 1


if __name__ == "__main__":
    sys.exit(main())
