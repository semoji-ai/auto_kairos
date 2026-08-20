#!/usr/bin/env python3
"""인포그래픽 씬의 화면을 설계한다 — 무엇을 어디에 놓고 무엇으로 이을지.

앞서 form 이름만 보고 규칙으로 자리를 나눴더니 **그냥 가로로 늘어놓은 화면**이
나왔다. 시험작과 견줘 보니 빠진 것이 배치가 아니라 **문법**이었다.

  · 항을 묶는다      「아버지 2,000원 + 구철회 1,800원」이 한 덩어리
  · 기호로 잇는다     +  =  →  구분선
  · 결론을 키우고 색을 준다   쌀 844가마가 가장 크고 주황
  · 제목을 얹는다     「포목점 창업 자금」

이건 규칙 몇 개로 안 된다. 씬마다 뜻이 다르기 때문이다. 그래서 요소와
라벨과 나레이션을 함께 보여 주고 화면을 짜게 한다.

**인포그래픽이 안 어울리면 그렇게 답하게 한다.** 재분석이 인포그래픽으로
돌린 씬 중에는 사람이 움직이는 장면이 더 나은 것이 섞여 있다.

    python3 scripts/plan_infographic_layout.py EP01 --scenes 14,43
    python3 scripts/plan_infographic_layout.py EP01           # 전부
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

PROMPT = """다큐멘터리 한 장면을 **인포그래픽 화면**으로 짭니다.

## 이 씬

나레이션: {narration}

만들어 둔 요소(배경 없는 그림):
{assets}

화면에 얹을 글자(라벨): {labels}
재분석이 적어 둔 배치 의도: {note}
이미 그려 둔 씬 그림: {scene_img}

## 화면 문법

단순히 늘어놓지 마세요. 화면이 **한 문장**이 되어야 합니다.

  · **항을 묶습니다.** 「아버지 2,000원 + 구철회 1,800원」처럼 한 뜻을 이루는
    것들은 가까이 세로로 붙입니다.
  · **기호로 잇습니다.** `+` `=` `→` 를 항 사이에 놓습니다. 좌우를 대비할
    때는 가운데에 세로 구분선을 둡니다.
  · **결론을 키웁니다.** 가장 중요한 항이 가장 큽니다. 그 라벨에는 강조를 줍니다.
  · **제목을 답니다.** 이 화면이 무엇을 말하는지 한 줄로.
  · 요소 사이는 넉넉히 띄웁니다. 붙어 있으면 뭉쳐 보이고, 균등하면 성겨 보입니다.

**무엇보다, 나레이션이 하는 말을 화면이 그대로 해야 합니다.** 예쁜 배치가
아니라 「이 말이 화면으로 설명되는가」가 기준입니다.

## 인포그래픽이 아닌 편이 나으면

사람이 무엇을 하는 장면, 감정이 실린 순간, 공간의 분위기가 중요한 씬은
도해로 만들면 오히려 힘이 빠집니다. 그럴 때는 `"skip": true` 로 답하고
이유를 적으세요. 억지로 짜지 마세요.

## 배경을 고릅니다

이 씬에는 이미 그려 둔 **씬 그림**이 있습니다. 도해를 흰 바탕에 따로 만들
수도 있고, 그 그림 위에 얹을 수도 있습니다.

  `grid`        밝은 모눈 바탕 — 수치·비교처럼 화면이 오롯이 도해일 때
  `scene`       씬 그림 위에 그대로 얹는다 — 그림이 배경 노릇을 하고
                요소가 그 위에서 말할 때 (그림이 한산해야 한다)
  `scene_blur`  씬 그림을 흐려서 깔고 그 위에 얹는다 — 장소나 분위기는
                남기되 도해를 읽혀야 할 때
  `map`         지도를 깔고 그 위에 얹는다 — 「어디」가 내용일 때

씬 그림이 복잡한데 `scene`을 고르면 글자가 묻힙니다. 그때는 `scene_blur`입니다.

## 글자가 읽히게

  `contrast` 로 정합니다.
  `plain`   밝은 바탕에 먹색 글자 (grid에 어울린다)
  `shadow`  흰 글자에 그림자 (어두운 그림 위)
  `box`     글자 뒤에 반투명 판 (그림이 복잡할 때 — 가장 확실하다)

## 나레이션이 길면

한 화면에 다 담으려 하지 마세요. 말이 길어 화면이 빽빽해지면
`"split_hint"` 에 어디서 끊으면 좋을지 적으세요(그 문장 그대로).
씬을 나누는 건 사람이 합니다.

## 좌표

화면 대비 백분율입니다. `left`·`top`은 **요소의 가운데**, `size`는 가로 너비.
화면은 16:9입니다.

## 낼 것 — JSON만

{{"skip": false,
  "title": "화면 제목 한 줄",
  "background": "grid | scene | scene_blur | map",
  "contrast": "plain | shadow | box",
  "divider": "none 또는 vertical",
  "split_hint": "나레이션을 나눌 자리 (필요 없으면 빈 문자열)",
  "items": [
    {{"id": "요소 id", "left": 22, "top": 45, "size": 18,
      "label": "이 요소에 붙일 글자(없으면 빈 문자열)",
      "emphasis": "normal 또는 accent"}}
  ],
  "marks": [{{"text": "+", "left": 22, "top": 62}}],
  "why": "이렇게 짠 이유 한 문장"}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=600, env=env)
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
    ap.add_argument("--scenes", help="쉼표로 구분한 씬 번호 (없으면 전부)")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    proj, ep = resolve_project(args.ep)
    mode = json.loads((root / "_imggen" / f"{ep}_mode.json").read_text(encoding="utf-8"))
    specs = {s["sceneNumber"]: s for s in
             json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}

    asset_dir = root / "_imggen" / f"{ep.lower()}_info"
    have = {p.stem for p in asset_dir.glob("*.png") if "_raw" not in p.name}

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    jobs = []
    for s in mode["scenes"]:
        n = s.get("n")
        if s.get("mode") != "infographic" or (want and n not in want):
            continue
        assets = [a for a in (s.get("assets") or [])
                  if f"s{n:03d}_{a['id']}" in have]
        if assets:
            jobs.append((n, s, assets))

    out_dir = root / "_imggen" / f"{ep.lower()}_layout"
    out_dir.mkdir(parents=True, exist_ok=True)

    def run(job):
        n, s, assets = job
        f = out_dir / f"s{n:03d}.json"
        if f.exists():
            return n, "이미 있음"
        prompt = PROMPT.format(
            narration=(specs.get(n, {}).get("narration") or "").strip()[:400],
            assets="\n".join(f"  - {a['id']}: {a.get('role') or a.get('prompt','')[:60]}"
                             for a in assets),
            labels=", ".join(s.get("labels") or []) or "(없음)",
            note=(s.get("composition") or {}).get("note", ""),
            scene_img=(specs.get(n, {}).get("imageAsset") or {}).get("prompt", "")[:200]
            or "(그려 둔 씬 그림 없음)",
        )
        d = ask(prompt)
        if not d:
            return n, "실패"
        ids = {a["id"] for a in assets}
        d["items"] = [it for it in (d.get("items") or []) if it.get("id") in ids]
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        if d.get("skip"):
            return n, f"인포그래픽 아님 — {d.get('why', '')[:50]}"
        return n, f"{len(d['items'])}요소 · {d.get('title', '')[:28]}"

    print(f"{ep}  {len(jobs)}씬 설계")
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, msg in ex.map(run, jobs):
            print(f"  씬{n:>3}  {msg}")
    print(f"\n→ {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
