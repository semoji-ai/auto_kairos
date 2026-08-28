#!/usr/bin/env python3
"""**화면이 받을 수 없는 말**을 사건·사람·물건이 든 말로 바꾼다.

그림을 36컷 고쳐 시청자 총점을 56 → 62 로 올렸는데, 「화면이 말을 못 받는
씬」은 44에서 한 컷도 줄지 않았다. 두 번의 평가에서 **두 번 다** 걸린 씬을
꺼내 보니 원인이 분명했다.

    56    이 말도 후대 전기에 정리된 대사입니다.
    1012  이건 단순한 배짱이 아니었습니다.
    1024  당시 구인회상회 자본금의 다섯 배쯤 되는 돈이었습니다.

하나도 사건이 아니다. 출처를 밝히거나 해석하거나 견주는 문장이라, 그림이
받을 사람도 사물도 행동도 없다. **어떤 그림을 붙여도 안 받는다.** 그림을
더 고치는 것은 여기서 수익이 끝난다.

그래서 말을 바꾼다. 다만 **사실은 한 톨도 새로 만들지 않는다** — 지금 문장이
이미 가진 사실을 다르게 말할 뿐이다. 수치·이름·연도·귀속(「전해집니다」)은
그대로 둔다. 귀속을 떨구면 전해지는 이야기가 확정처럼 읽힌다.

    python3 scripts/ground_narration.py EP01
    python3 scripts/ground_narration.py EP01 --apply
    python3 scripts/ground_narration.py EP01 --scenes 56,58,1012

고친 씬은 `subtitle_lines` 를 떨군다. 그 값은 씬을 쪼개기 전의 낡은 분할이라
(씬61 의 둘째 줄은 실제로 씬1064 의 대사였다) 새 말과 어긋난다.
`generate_tts` 가 새 narration 에서 다시 뽑는다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

WINDOW = 6

PROMPT = """세모지 브랜드 다큐멘터리의 **내레이션 몇 줄**을 고칩니다.

시청자 셋이 두 번의 평가에서 **두 번 다** 「화면이 이 말을 못 받는다」고
지적한 문장들입니다.

## 왜 못 받는가

출처를 밝히거나(「후대 전기에 정리된 대사입니다」), 해석하거나(「단순한
배짱이 아니었습니다」), 견주는(「자본금의 다섯 배쯤 되는 돈이었습니다」)
문장이라 **화면에 놓을 사람도 사물도 행동도 없습니다.** 어떤 그림을 붙여도
「핵심이 화면에 없다」가 됩니다.

## 볼 것

{scenes}

## 해야 할 일

씬마다 둘 중 하나를 고릅니다.

```
keep      이미 사람·사물·행동이 들어 있다 — 이건 그림 쪽 문제다
rewrite   화면이 받을 수 있는 말로 바꾼다
```

**keep 을 아끼지 마세요.** 「밑천 2,000원을 내주며」에는 아버지와 돈이
있습니다. 이런 문장은 그림이 못 따라온 것이지 말이 잘못된 것이 아닙니다.

### 바꾸는 법 — 추상을 사물로 내린다

```
「자본금의 다섯 배쯤 되는 돈이었습니다」
  → 「가게를 다섯 채 살 수 있는 돈이었습니다」        (셀 수 있는 것으로)

「이건 단순한 배짱이 아니었습니다」
  → 「그는 장부를 펴 놓고 지난 삼 년의 혼례 수를 셌습니다」  (행동으로)

「이 말도 후대 전기에 정리된 대사입니다」
  → 앞 문장에 붙여 없애거나, 기록을 든 사람의 손으로 옮긴다
```

## 반드시 지킬 것

**① 사실을 새로 만들지 않습니다.** 지금 문장이 가진 사실만 다르게 말합니다.
수치·이름·연도는 글자 그대로 옮기고, 없던 장면·대사·인물을 지어내지
않습니다. 무엇으로 바꿔야 할지 모르겠으면 `keep` 을 고르세요.

**② 귀속을 떨구지 않습니다.** 「전해집니다」·「후대 기록에 따르면」이 붙어
있으면 새 문장에도 그 뜻이 남아야 합니다. 떨구면 전해지는 이야기가
확정된 사실처럼 읽힙니다.

**③ 문체를 지킵니다.** 위에 앞뒤 문장을 붙여 두었습니다. 그 목소리 그대로
씁니다 — 해요체 존댓말, 한 문장에 한 가지, 짧은 문장과 긴 문장을 섞습니다.
문어체로 굳거나(「~하였다」) 설명조로 늘어지지 않게 합니다.

**④ 한글만 씁니다.** 한자와 일본어 가나를 쓰지 않습니다.

**⑤ 비문을 만들지 않습니다.** 주어와 서술어가 맞는지, 목적어가 빠지지
않았는지, 시제가 앞뒤와 맞는지 소리 내어 읽어 보고 냅니다. 수식어가 어느
말을 꾸미는지 헷갈리는 자리를 남기지 않습니다.

**⑥ 길이를 지킵니다.** 지금 문장의 ±25% 안에 둡니다. 녹음 길이와 화면
길이가 이미 이 분량에 맞춰져 있습니다.

## 낼 것 — JSON만

{{"scenes": [
  {{"scene": 씬번호,
    "action": "keep | rewrite",
    "narration": "바꾼 문장 전문 (keep 이면 지금 문장 그대로)",
    "why": "무엇을 화면이 받을 수 있게 만들었는가 한 줄",
    "kept_facts": ["그대로 옮긴 수치·이름·연도·귀속"]}}
]}}
"""


PROOF = """고쳐 쓴 내레이션 문장들의 **비문**만 봅니다. 내용은 건드리지 않습니다.

말을 고치면 뜻은 맞는데 문장이 어긋나는 자리가 생깁니다. 눈으로는 잘
안 잡힙니다 — 뜻이 통하니까 읽고 넘어갑니다.

## 볼 것

{scenes}

## 잡을 것

```
주술 불일치    주어와 서술어가 맞지 않는다
목적어 누락    무엇을 하는지가 빠졌다
이중 주어      한 문장에 주어가 둘이라 누구 이야기인지 흐려진다
수식 모호      꾸미는 말이 어느 말에 붙는지 두 갈래로 읽힌다
시제 어긋남    앞뒤 문장과 때가 맞지 않는다
호응 어긋남    「~뿐만 아니라」·「비록」 같은 말이 짝을 못 만났다
조사 오용      은/는·이/가·을/를 이 자리에 맞지 않는다
```

**말투는 보지 않습니다.** 해요체·구어체·짧은 문장은 이 원고의 문체입니다.
문장이 문법으로 어긋난 자리만 잡습니다. 이상이 없으면 `ok` 로 둡니다.

## 낼 것 — JSON만

{{"scenes": [
  {{"scene": 씬번호, "verdict": "ok | 비문",
    "kind": "위 갈래 중 하나 (ok 면 빈 문자열)",
    "fixed": "고친 문장 — 뜻과 말투를 그대로 두고 문법만 (ok 면 빈 문자열)",
    "why": "무엇이 어긋났는가 한 줄 (ok 면 빈 문자열)"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=2400, env=env)
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


def confirmed_unclear(root: Path, ep: str) -> list[int]:
    """시청자 평가 **두 번 다** 「말을 못 받는다」고 한 씬.

    한 번 잡힌 것은 쓰지 않는다. 그림 검사와 같은 이유다 — 한 회차의
    지적은 흔들린다. 두 번 겹친 것만 실제 결함으로 본다.
    """
    a = root / "_imggen" / f"{ep}_viewer.json"
    b = root / "_imggen" / f"{ep}_viewer.prev.json"
    if not (a.exists() and b.exists()):
        raise SystemExit("시청자 평가가 두 번 있어야 합니다 (viewer_eval.py)")
    def load(p):
        return set(json.loads(p.read_text(encoding="utf-8")).get("unclear_scenes") or [])
    return sorted(load(a) & load(b))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--scenes", help="쉼표로 구분 — 비우면 두 번 다 잡힌 씬")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--from", dest="src", action="store_true",
                    help="다시 묻지 않고 지난 제안(_imggen/<EP>_ground.json)을 쓴다")
    ap.add_argument("--proofread", action="store_true",
                    help="이미 반영된 문장의 비문만 다시 본다")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    by_n = {s.get("sceneNumber"): s for s in scenes}
    order = [s.get("sceneNumber") for s in scenes]

    want = ([int(x) for x in args.scenes.split(",")] if args.scenes
            else confirmed_unclear(root, ep))
    todo = [n for n in want if n in by_n and (by_n[n].get("narration") or "").strip()]
    if not todo:
        raise SystemExit("고칠 씬이 없습니다")
    if args.proofread:
        args.apply = args.src = True

    print(f"{ep}  화면이 못 받는 말 {len(todo)}줄을 봅니다")

    def describe(n):
        s = by_n[n]
        i = order.index(n)
        def near(rng):
            out = []
            for k in rng:
                t = (by_n[order[k]].get("narration") or "").strip()
                if t:
                    out.append(f"      씬{order[k]}: {t[:80]}")
                if len(out) >= 2:
                    break
            return out
        L = [f"  씬{n} (챕터 {s.get('chapter')})",
             f"    지금 말: {(s.get('narration') or '').strip()}",
             "    앞:"] + near(range(i - 1, -1, -1)) + ["    뒤:"] + near(
                 range(i + 1, len(order)))
        L.append(f"    지금 화면: {((s.get('imageAsset') or {}).get('prompt') or '')[:180]}")
        return "\n".join(L)

    def run(chunk):
        return (ask(PROMPT.format(scenes="\n\n".join(describe(n) for n in chunk)))
                or {}).get("scenes") or []

    if args.src:
        out = json.loads(
            (root / "_imggen" / f"{ep}_ground.json").read_text(encoding="utf-8")
        ).get("scenes") or []
    else:
        chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
        out = []
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for r in ex.map(run, chunks):
                out.extend(r)

    rew = [m for m in out
           if m.get("action") == "rewrite"
           and (m.get("narration") or "").strip()
           and m.get("scene") in by_n
           and m["narration"].strip() != (by_n[m["scene"]].get("narration") or "").strip()]
    kept = [m for m in out if m.get("action") == "keep"]
    print(f"\n  그대로 두는 말 {len(kept)} (그림 쪽 문제) · 바꾸는 말 {len(rew)}\n")
    for m in rew:
        n = m["scene"]
        print(f"  씬{n}")
        print(f"    전: {(by_n[n].get('narration') or '').strip()}")
        print(f"    후: {m['narration'].strip()}")
        print(f"    왜: {m.get('why','')[:80]}")

    # 제안을 남긴다. 안 남기면 검토하고 반영하려 할 때 다시 물어야 하고,
    # 그때는 다른 문장이 돌아온다 — 검토한 것과 다른 것이 들어간다.
    pf = root / "_imggen" / f"{ep}_ground.json"
    pf.write_text(json.dumps({"episode": ep, "scenes": out}, ensure_ascii=False, indent=2),
                  encoding="utf-8")
    print(f"\n  제안: {pf}")

    if not args.apply:
        print("  --apply 를 붙이면 반영합니다 (--from 으로 이 제안을 그대로 반영).")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_ground_{datetime.now():%Y%m%d_%H%M%S}"))
    for m in rew:
        s = by_n[m["scene"]]
        s["narration"] = m["narration"].strip()
        s["narration_tts"] = m["narration"].strip()
        # 낡은 분할을 떨군다 — 씬을 쪼개기 전 값이라 새 말과 어긋난다.
        s.pop("subtitle_lines", None)
        s.pop("subtitle_lines_tts", None)
        s["narration_dirty"] = True
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(rew)}줄을 바꿨습니다.")

    # 말을 고치면 뜻은 맞는데 문장이 어긋나는 자리가 생긴다. 위험을 만든
    # 도구가 그 자리에서 검사한다 — 나중에 전편을 다시 돌리면 비싸고,
    # 무엇보다 잊는다.
    def proof(chunk):
        body = "\n\n".join(
            f"  씬{n} (챕터 {by_n[n].get('chapter')})\n"
            f"    앞: {_prev_text(by_n, order, n)[:70]}\n"
            f"    문장: {by_n[n]['narration']}" for n in chunk)
        return (ask(PROOF.format(scenes=body)) or {}).get("scenes") or []

    nums = [m["scene"] for m in rew] or (todo if args.proofread else [])
    checked = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(proof, [nums[i:i + WINDOW]
                                for i in range(0, len(nums), WINDOW)]):
            checked.extend(r)
    bad = [c for c in checked if c.get("verdict") != "ok" and (c.get("fixed") or "").strip()]
    print(f"\n  비문 검사 — 이상 없음 {len(checked) - len(bad)} · 고칠 것 {len(bad)}")
    for c in bad:
        n = c["scene"]
        print(f"    씬{n} [{c.get('kind','')}] {c.get('why','')[:60]}")
        print(f"      전: {by_n[n]['narration']}")
        print(f"      후: {c['fixed'].strip()}")
        by_n[n]["narration"] = c["fixed"].strip()
        by_n[n]["narration_tts"] = c["fixed"].strip()
    if bad:
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {len(bad)}줄의 비문을 고쳤습니다.")
    print("  다음: verify_voice.py(문체) · check_manuscript.py(정합성) 로 확인하세요")
    return 0


def _prev_text(by_n, order, n):
    i = order.index(n)
    for k in range(i - 1, -1, -1):
        t = (by_n[order[k]].get("narration") or "").strip()
        if t:
            return t
    return ""


if __name__ == "__main__":
    sys.exit(main())
