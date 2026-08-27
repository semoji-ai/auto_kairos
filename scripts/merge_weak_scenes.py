#!/usr/bin/env python3
"""**혼자 설 수 없는 씬**을 찾아 뒤 문장에 묶는다.

「한 문장 한 화면」으로 나누면 그림으로 그릴 것이 없는 문장도 제 화면을
갖는다. 그려 놓고 보면 「인물만 서 있을 뿐 말이 화면에 없는」 컷이 된다.

  확실한 것은 이겁니다 · 중요한 건 하나입니다 · 순서가 흥미롭습니다
  ~한 게 아니었습니다 (부정) · ~했다면 ~했을 겁니다 (가정)
  실제로도 그랬습니다 (앞을 받는 말)

이건 화면에서 때울 일이 아니라 **배분을 다시 할 일**이다. 뒤 문장이 답을
들고 있으므로 함께 두어야 화면이 선다.

정본은 `docs/rules/scene-splitting-rules.md` 1절 — 두 물음의 순서.

  ① 이 문장 혼자서 한 장면이 되는가   ← 먼저
  ② 앞뒤와 한 호흡인가, 길지 않은가

**뒤가 반전 카드면 카드에 붙이지 않는다.** 카드는 한 마디로 홀로 서야 하고
뒤집을 내용이 앞에 있어야 한다 — 그때는 건너뛰고 그 다음 문장에 붙인다.

    python3 scripts/merge_weak_scenes.py EP01
    python3 scripts/merge_weak_scenes.py EP01 --apply
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

WINDOW = 20

PROMPT = """씬마다 **이 문장 혼자서 한 장면이 되는가**를 봅니다.

## 씬

{scenes}

## 먼저 — 나눠야 할 자리인가

아래 셋 중 하나라도 걸리면 **그 씬은 그대로 둡니다.** 화면이 달라져야 하는
자리입니다.

  장면이 달라진다        때 · 곳 · 주체가 바뀐다
  앵글이 달라져야 한다    같은 자리라도 크기나 각도가 바뀌어야 말이 산다
  표현이나 타입이 바뀐다  재연 → 도해 · 실물 자료 · 인용 · 반전 카드

## 그다음 — 혼자 설 수 있는가

**가리키는 사물이나 동작이 있는가.**

  선다      종업원은 스무 명 남짓
            기계는 그해 8월 무렵에야 들어왔습니다
            상인들은 공장 앞에 줄을 섰습니다

  안 선다   확실한 것은 이겁니다 · 중요한 건 하나입니다
            순서가 흥미롭습니다 · 문제가 있었습니다
            이런 말이 있습니다          ← 다음 말을 여는 문장
            실제로도 그랬습니다          ← 앞을 받기만 하는 말
            ~한 게 아니었습니다          ← 부정문
            ~했다면 ~했을 겁니다         ← 가정문

**부정문과 가정문이 특히 그렇습니다.** 그림은 하지 않은 일을 그릴 수
없습니다. 무엇을 했는지는 뒤 문장에 있습니다.

말이 추상적이라고 다 안 서는 것은 아닙니다. 「값은 깎아 주지 않았습니다.
대신 자를 속이지 않았죠」는 자와 저울로 설 수 있습니다. **그릴 것이 떠오르면
서는 것**입니다.

**어느 쪽에 붙일지도 정하세요.** 답을 어느 쪽이 들고 있는지로 갈립니다.

  「확실한 것은 이겁니다」   → 뒤가 답을 들고 있다        → next
  「실제로도 그랬습니다」     → 앞을 받는 말이다           → prev

## 낼 것 — JSON만. 안 서는 씬만 적으세요.

{{"weak": [
  {{"scene": 씬번호, "side": "prev | next", "why": "왜 혼자 못 서는가 한 마디"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=1800, env=env)
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
    ap.add_argument("--scenes", help="이 씬들만 (쉼표로 구분)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    todo = [s for s in scenes
            if (s.get("narration") or "").strip()
            and not s.get("isTurnCard") and not s.get("isChapterCard")]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")

    print(f"{ep}  씬 {len(todo)}개")

    def run(chunk):
        body = "\n".join(f"  씬{s['sceneNumber']}: {(s.get('narration') or '').strip()[:110]}"
                         for s in chunk)
        return (ask(PROMPT.format(scenes=body)) or {}).get("weak") or []

    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    weak = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for rows in ex.map(run, chunks):
            weak.extend(rows)

    by_n = {s.get("sceneNumber"): s for s in scenes}
    order = [s.get("sceneNumber") for s in scenes]
    plan = []
    for w in weak:
        n = w.get("scene")
        if n not in by_n:
            continue
        i = order.index(n)
        # 뒤 문장을 찾는다. 반전 카드는 건너뛴다 — 카드는 홀로 서야 한다.
        tgt = None
        for k in range(i + 1, min(i + 4, len(order))):
            m = by_n[order[k]]
            if m.get("isChapterCard"):
                break
            if m.get("isTurnCard"):
                continue
            if (m.get("narration") or "").strip():
                tgt = order[k]
                break
        plan.append((n, tgt, w.get("why", "")))

    print(f"\n혼자 못 서는 씬 {len(plan)}개")
    for n, tgt, why in plan:
        head = (by_n[n].get("narration") or "").strip()[:46]
        tail = (by_n[tgt].get("narration") or "").strip()[:40] if tgt else "(뒤 문장 없음)"
        print(f"  씬{n:>5} → 씬{tgt}   {head}  +  {tail}")
        if why:
            print(f"          {why[:70]}")

    if not args.apply:
        print("\n--apply 를 붙이면 묶습니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_weak_{datetime.now():%Y%m%d_%H%M%S}"))
    # 연쇄를 막는다. 하나씩 독립으로 물으면 「A는 약하니 B에」 「B도 약하니 C에」로
    # 이어져 194자짜리 씬이 나온다 — 나누기 전보다 나쁘다.
    #   · 이미 무언가를 받은 씬에는 더 붙이지 않는다
    #   · 붙인 결과가 90자를 넘으면 놓아둔다 (여는 말의 길이 예외는 한 번뿐이다)
    gone, got = set(), set()
    LIMIT = 90
    skipped = []
    for n, tgt, _ in plan:
        if tgt is None or n in gone or tgt in gone:
            continue
        if tgt in got:
            skipped.append((n, "이미 받은 씬"))
            continue
        merged = f"{by_n[n]['narration'].strip()} {by_n[tgt]['narration'].strip()}"
        if len(merged) > LIMIT:
            skipped.append((n, f"붙이면 {len(merged)}자"))
            continue
        got.add(tgt)
        by_n[tgt]["narration"] = merged
        by_n[tgt]["narration_dirty"] = True
        # 묶인 쪽의 그림은 버리지 않는다 — 뒤 씬이 이미 그림을 갖고 있으면
        # 그대로 두고, 없으면 「그려야 함」으로 남긴다.
        gone.add(n)
    data["scenes"] = [s for s in scenes if s.get("sceneNumber") not in gone]
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if skipped:
        print(f"\n놓아둔 씬 {len(skipped)}개 — 연쇄를 막았습니다")
        for n, why in skipped[:12]:
            print(f"  씬{n:>5} ({why})")
    print(f"\n{len(gone)}씬을 뒤 문장에 묶었습니다 · 씬 {len(scenes)} → {len(data['scenes'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
