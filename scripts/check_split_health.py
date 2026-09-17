#!/usr/bin/env python3
"""나눈 뒤에 **세어 본다.** 규칙 6절이 시키는 검사를 실제로 돌린다.

`scene-splitting-rules.md` 6절에 「같은 프롬프트를 나눠 가진 씬 — 0」이
적혀 있는데, LG 1편에서 한 번도 돌리지 않았다. 세어 보니 9묶음 18씬이
같은 프롬프트로 그려져 있었다.

무엇이 잘못되는가.

  씬20   「보통 첫 실패 뒤에는 물건을 줄이기 마련인데요」
  씬997  「구인회는 반대로 구색을 늘렸습니다」            ← 반전

  둘의 프롬프트가 같다 — 「…두 선택 사이에서 풍성한 쪽을 고르는 구인회…」

**질문 컷에 답이 이미 그려져 있다.** 반전이 나오기 전에 소진되고, 두 컷은
사실상 같은 그림이 된다.

원인은 쪼갠 조각이 원래 씬의 `imageAsset` 을 통째로 물려받았기 때문이다.
원래 프롬프트는 **합쳐진 문장 전체**를 그린 것이라 조각 하나에는 너무
많은 것이 들어 있다.

    python3 scripts/check_split_health.py EP01
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    args = ap.parse_args()

    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    assets = {e["sceneNumber"]: e for e in json.loads(
        (proj / "images" / "image_assets.json").read_text(encoding="utf-8"))["scenes"]}

    real = [s for s in scenes
            if not s.get("isChapterCard") and not s.get("isTurnCard")]
    body = [s for s in real if s.get("visual_kind") not in ("infographic", "map")]

    print(f"{ep}  씬 {len(scenes)}  실컷 {len(real)}  그림 씬 {len(body)}\n")

    bad = 0

    # ── ① 같은 프롬프트를 나눠 가진 씬 — 규칙은 0을 요구한다
    def group(getp, label):
        nonlocal bad
        by = collections.defaultdict(list)
        for s in body:
            p = (getp(s) or "").strip()
            if p:
                by[p].append(s["sceneNumber"])
        dup = {p: ns for p, ns in by.items() if len(ns) > 1}
        n = sum(len(v) for v in dup.values())
        mark = "  " if not dup else "✗ "
        print(f"{mark}{label}: {len(dup)}묶음 · {n}씬   (있어야 할 값 0)")
        for p, ns in sorted(dup.items(), key=lambda x: -len(x[1]))[:8]:
            print(f"     씬 {sorted(ns)}")
            print(f"       {p[:96]}")
        if dup:
            bad += 1
        return dup

    group(lambda s: (s.get("imageAsset") or {}).get("prompt"),
          "씬 명세의 프롬프트가 같은 씬")

    def sel_prompt(s):
        for i in (assets.get(s["sceneNumber"]) or {}).get("images") or []:
            if i.get("selected"):
                return i.get("prompt")
        return None

    print()
    group(sel_prompt, "실제로 쓰인 그림의 프롬프트가 같은 씬")

    # ── ② 남의 그림을 물려받은 씬 — 물려주기 자체는 옳다. 안 물어본 것이 문제다
    print()
    own = inherited = 0
    rows = []
    for s in body:
        f = None
        for i in (assets.get(s["sceneNumber"]) or {}).get("images") or []:
            if i.get("selected"):
                f = i.get("file")
        if not f:
            continue
        m = re.search(r"scene_(\d+)", f)
        src = int(m.group(1)) if m else None
        if src == s["sceneNumber"]:
            own += 1
        else:
            inherited += 1
            rows.append((s["sceneNumber"], src))
    print(f"  제 번호의 그림을 쓰는 씬 {own} · 남의 그림을 물려받은 씬 {inherited}")
    if inherited:
        print("     물려주기 자체는 옳습니다(그림을 버리지 않으니까요). 다만")
        print("     물려준 뒤 「이 그림이 이 말을 하는가」를 반드시 물어야 합니다.")
        print(f"     → python3 scripts/judge_visual_by_text.py {ep}")

    # ── ③ 화면이 없는 씬
    print()
    gap = []
    for s in real:
        n, k = s["sceneNumber"], s.get("visual_kind")
        if k in ("infographic", "map"):
            ok = bool((s.get("infographic") or {}).get("items")) or k == "map"
        else:
            ok = any(i.get("selected") for i in (assets.get(n) or {}).get("images") or [])
        if not ok:
            gap.append(n)
    print(f"  화면이 없는 실컷: {len(gap)}" + (f"  {gap}" if gap else ""))
    if gap:
        bad += 1

    print("\n" + ("문제 없습니다." if not bad else f"손볼 항목 {bad}가지."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
