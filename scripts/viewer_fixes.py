#!/usr/bin/env python3
"""평가한 시청자에게 **어떻게 했어야 했는지** 되묻는다.

`viewer_eval.py` 는 「어디서 넘겼는가」를 듣는다. 그건 진단이지 처방이
아니다. 넘긴 자리를 알아도 무엇으로 바꿔야 안 넘길지는 다른 질문이다.

그래서 두 번 묻는다.

  ① 평가   어디서 넘겼는가 · 무엇이 안 읽혔는가      viewer_eval.py
  ② 제안   무엇으로 바꿨으면 안 넘겼겠는가            여기
           더 재밌으려면 어떤 화면이었어야 하는가

**②는 ①의 불만을 손에 들고 묻는다.** 빈손으로 물으면 「좋았습니다」만
돌아온다. 자기가 적은 불만을 보여 주면 구체적인 화면을 말한다.

    python3 scripts/viewer_fixes.py EP01
    python3 scripts/viewer_fixes.py EP01 --chapter 3
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from viewer_eval import PERSONAS, ask, describe  # noqa: E402

WINDOW = 22

PROMPT = """{personas}

셋은 방금 이 편을 보고 아래처럼 말했습니다.

## 셋이 남긴 불만

{complaints}

## 그 장면들

첨부한 그림 파일을 **Read 로 직접 열어 보고** 답하세요.

{scenes}

## 물을 것

이제 **어떻게 했어야 했는지**를 말합니다. 불평이 아니라 처방입니다.

각 자리마다 이렇게 답하세요.

  무엇이 문제인가      한 줄
  무엇으로 바꾸는가    **화면에 실제로 보이는 것**으로 적습니다
  왜 그게 나은가       셋 중 누가 왜 안 넘기게 되는지

### 지킬 것

**「더 역동적으로」·「더 흥미롭게」 같은 말은 답이 아닙니다.**
화면에 무엇이 보이는지 적으세요.

```
안 됨   씬27을 더 긴장감 있게 만든다
됨      씬27에서 상자를 나르는 손 대신, 장부의 재고 숫자에 손가락을 얹은
        가까운 화면으로. 「줄일까」라는 판단이 손끝에 있어야 한다
```

**있는 것을 옮겨 쓰는 쪽을 먼저 봅니다.** 새로 그리는 것보다, 같은 그림이
여러 씬에 겹쳐 있으면 하나만 남기고 나머지를 다른 각도로 바꾸는 것이 낫습니다.

**말을 바꾸는 제안도 받습니다.** 화면이 못 받는 말이면 말 쪽이 문제일 수
있습니다. 그때는 `kind` 를 `말` 로 적으세요.

## 그리고 편 전체에 대해

「이렇게 했으면 훨씬 재밌었을 텐데」를 셋이 각각 하나씩 말합니다.
씬 하나가 아니라 **편 전체를 움직이는 것**이어야 합니다.

## 낼 것 — JSON만

{{"fixes": [
   {{"scene": 씬번호, "kind": "화면 | 말 | 순서",
     "problem": "무엇이 문제인가",
     "change": "무엇으로 바꾸는가 — 화면에 보이는 것으로",
     "why": "누가 왜 안 넘기게 되는가",
     "reuse": "옮겨 쓸 기존 그림이 있으면 그 씬번호, 없으면 빈 문자열"}}
 ],
 "episode_ideas": [
   {{"who": "김상현 | 박영자 | 이지우",
     "idea": "편 전체를 움직이는 제안",
     "why": "왜 훨씬 재밌어지는가"}}
 ]}}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--scenes")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    ap.add_argument("--eval", help="평가 결과 JSON (기본: _imggen/<EP>_viewer.json)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]

    ev_f = Path(args.eval) if args.eval else root / "_imggen" / f"{ep}_viewer.json"
    if not ev_f.exists():
        raise SystemExit(f"평가 결과가 없습니다: {ev_f}\n먼저 viewer_eval.py 를 돌리세요.")
    ev = json.loads(ev_f.read_text(encoding="utf-8"))

    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected

    todo = list(scenes)
    if args.chapter is not None:
        todo = [s for s in todo if s.get("chapter") == args.chapter]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")
    for s in todo:
        s["_ep"] = ep.lower()

    skip = set(ev.get("skip_scenes") or [])
    unclear = set(ev.get("unclear_scenes") or [])
    notes = ev.get("notes") or []
    ident = ev.get("identity_issues") or []

    print(f"{ep}  씬 {len(todo)}개 · 불만 {len(notes)}건을 들고 되묻습니다")

    def run(idx_chunk):
        idx, chunk = idx_chunk
        ns = {s["sceneNumber"] for s in chunk}
        # 이 구간에 해당하는 불만만 들려준다 — 남의 구간 얘기는 잡음이다
        mine = []
        if idx < len(notes):
            mine.append(notes[idx])
        hit_skip = sorted(ns & skip)
        hit_unclear = sorted(ns & unclear)
        if hit_skip:
            mine.append(f"넘기고 싶어진 씬: {hit_skip}")
        if hit_unclear:
            mine.append(f"화면이 말을 못 받는 씬: {hit_unclear}")
        for t in ident:
            if any(str(n) in t for n in ns):
                mine.append(t)
        body = "\n".join(
            describe(s, proj, root, get_selected(proj / "images", s["sceneNumber"]))
            for s in chunk)
        return ask(PROMPT.format(personas=PERSONAS,
                                 complaints="\n\n".join(f"  · {m}" for m in mine) or "  (없음)",
                                 scenes=body))

    chunks = list(enumerate(todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)))
    fixes, ideas = [], []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            if not r:
                continue
            fixes.extend(r.get("fixes") or [])
            ideas.extend(r.get("episode_ideas") or [])

    out = {"episode": ep, "fixes": fixes, "episode_ideas": ideas}
    f = root / "_imggen" / f"{ep}_viewer_fixes.json"
    if f.exists():
        f.replace(f.with_name(f"{f.stem}.prev{f.suffix}"))
    f.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    from collections import Counter
    kinds = Counter(x.get("kind", "?") for x in fixes)
    print(f"\n  고칠 자리 {len(fixes)}개  {dict(kinds)}")
    print(f"  옮겨 쓰면 되는 것 {sum(1 for x in fixes if (x.get('reuse') or '').strip())}개")
    print(f"  편 전체 제안 {len(ideas)}개")
    print(f"\n{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
