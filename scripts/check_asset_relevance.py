#!/usr/bin/env python3
"""실물 자료가 그 씬의 내용과 직접 이어지는지 검사한다.

조사는 「이 사진이 진짜인가」는 잘 검증했다. 원장의 `desc`는 정확하다 —
"1945년 일본에서 부산으로 돌아오는 한국인들"처럼 찍힌 것을 그대로 적었다.

**그런데 그 씬은 해방 뒤 사업 거점을 부산으로 옮긴 이야기였다.**
시청자 평가에서 "한국전쟁기 피란으로 오해된다"는 지적이 나왔다. 같은 방식으로
1940년대 동업 설명에 2005년 GS 출범식 사진이, 1931년 개업에 노년 초상이 붙었다.

원인은 하나다. `relevance`(이 자료가 이 씬 내용과 어떻게 이어지는지)를
규칙으로만 요구하고 **코드로 강제하지 않았다.** 12편 180건 중 58건이 공란이었고,
시청자가 짚은 3건이 전부 그 공란에 있었다.

검사 두 단계
  1. 공란   — relevance가 없으면 실패. 사람이 이유를 못 적었으면 근거가 없는 것이다.
  2. 판정   — 적혀 있어도 「같은 시대라서」류는 이유가 아니다. --judge를 주면
              나레이션과 desc를 나란히 놓고 멀티모달이 직접 이어지는지 본다.

    python3 scripts/check_asset_relevance.py <project_dir> --ledger <ledger.json>
    python3 scripts/check_asset_relevance.py <project_dir> --ledger <l.json> --judge
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# 이유처럼 보이지만 이유가 아닌 말. "같은 시대라서"는 규칙이 명시적으로 배제한다.
WEAK = re.compile(
    r"같은 (시대|시기|연대|무렵)|비슷한 (시대|시기|분위기|장면)|시대 ?(분위기|배경)"
    r"|분위기를? (맞|보여|전달)|당시 (모습|풍경|거리)를? 보여|참고용|대체(용|재)"
)

JUDGE = """다음은 다큐멘터리 한 편의 씬과, 그 씬에 붙일 실물 자료입니다.

물음은 하나입니다.
**이 씬의 나레이션을 들은 사람이 이 자료를 보고 「이게 방금 그 이야기구나」
하고 바로 알 수 있습니까?**

「같은 시대라서」「분위기가 맞아서」는 이유가 되지 않습니다. 그 정도면 없는 것이
낫습니다 — 시청자가 다른 사건으로 잘못 기억하기 때문입니다.

실제로 이런 것들이 통과해 문제가 됐습니다.
  · 사업 거점을 부산으로 옮긴 이야기에 1945년 귀환선 사진 → 한국전쟁 피란으로 읽힘
  · 1940년대 동업 이야기에 2005년 GS 출범식 사진 → 시대가 건너뜀
  · 1931년 개업 이야기에 노년 초상 → 젊은 창업자로 안 보임

각 항목을 ok / risky / wrong 으로 판정하세요.
  ok     직접 이어진다
  risky  이어지긴 하나 시대·인물·사건이 어긋나 오해 여지가 있다
  wrong  다른 사건으로 읽힌다

입력: __INPUT__
결과를 __OUTPUT__ 에 저장하세요. 형식:
{"items":[{"n":0,"verdict":"ok|risky|wrong","why":"","instead":""}]}
`instead`에는 wrong·risky일 때 대신 어떤 자료를 찾아야 하는지 구체적으로 씁니다.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--ledger", required=True, type=Path)
    ap.add_argument("--judge", action="store_true", help="멀티모달로 내용 일치까지 본다")
    ap.add_argument("-o", "--out", type=Path)
    args = ap.parse_args()

    scenes = {s["sceneNumber"]: s for s in json.loads(
        (args.project / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
    led = json.loads(args.ledger.read_text(encoding="utf-8"))
    entries = [e for e in led.get("scenes", led) if e.get("found")]

    blank, weak = [], []
    for e in entries:
        r = (e.get("relevance") or "").strip()
        if not r:
            blank.append(e["n"])
        elif WEAK.search(r):
            weak.append({"n": e["n"], "relevance": r})

    judged = []
    if args.judge and entries:
        payload = [{"n": e["n"],
                    "narration": (scenes.get(e["n"], {}).get("narration") or "")[:400],
                    "desc": e.get("desc", ""), "relevance": e.get("relevance", "")}
                   for e in entries]
        with tempfile.TemporaryDirectory() as td:
            fin, fout = Path(td) / "in.json", Path(td) / "out.json"
            fin.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            subprocess.run(
                ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write",
                 JUDGE.replace("__INPUT__", str(fin)).replace("__OUTPUT__", str(fout))],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1800)
            if fout.exists():
                judged = json.loads(fout.read_text(encoding="utf-8")).get("items", [])

    bad = [j for j in judged if j.get("verdict") in ("wrong", "risky")]
    out = {"blank_relevance": blank, "weak_relevance": weak, "judged": judged}
    if args.out:
        args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.project.name}: 실물 {len(entries)}건"
          f" / 근거 공란 {len(blank)} / 근거 부실 {len(weak)}"
          + (f" / 내용 어긋남 {len(bad)}" if args.judge else ""))
    if blank:
        print(f"      근거 공란 — 씬 {blank[:14]}")
    for w in weak[:5]:
        print(f"      씬 {w['n']:>3} 부실 — {w['relevance'][:60]}")
    for b in bad[:8]:
        print(f"      씬 {b['n']:>3} {b['verdict']} — {b.get('why','')[:70]}")
    return 1 if (blank or weak or bad) else 0


if __name__ == "__main__":
    sys.exit(main())
