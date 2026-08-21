#!/usr/bin/env python3
"""검수에서 나온 지적대로 배치를 고친다 — 보고, 고치고, 다시 본다.

검수는 「+ 기호를 x=195 y=420으로 내려라」처럼 숫자까지 짚어 준다. 그걸
그대로 반영한다. 고친 뒤에는 **다시 그려서 다시 본다** — 한 번에 맞는 일이
드물고, 고치다 다른 것을 깨뜨리기도 한다.

에셋 자체가 틀린 것(「쌀 844가마인데 자루 하나」)은 여기서 못 고친다.
그림을 다시 그려야 하므로 `pending_asset` 으로 남겨 둔다.

    python3 scripts/fix_infographic_layout.py EP01 --scenes 14,43
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

PROMPT = """인포그래픽 화면을 고칩니다. Read 도구로 지금 화면을 열어 보세요.

{path}

## 이 화면이 하는 말

{narration}

## 지금 배치 (백분율, left·top은 요소의 가운데)

{layout}

## 검수에서 나온 지적

{problems}

## 고칠 때

- 지적대로 좌표를 옮기되, **옮긴 뒤 다른 것과 겹치지 않는지** 함께 보세요.
- 라벨은 요소 아래에 붙습니다. 기호(+ = →)는 항과 항 **사이 빈 자리**에
  두고 라벨과 세로로 최소 6%는 떨어뜨리세요.
- 구분선은 좌우를 **대비**할 때만 둡니다. 흐름이면 없앱니다(`"divider": "none"`).
- 글자가 묻히면 `contrast`를 `box`로 올리세요.
- 그림 자체가 뜻과 다른 것(많음인데 낱개 하나 등)은 좌표로 못 고칩니다.
  그건 `pending_asset` 에 무엇을 다시 그려야 하는지 적으세요.

## 낼 것 — 고친 배치 JSON만

{{"title": "", "background": "", "contrast": "", "divider": "",
  "items": [{{"id": "", "left": 0, "top": 0, "size": 0, "label": "", "emphasis": ""}}],
  "marks": [{{"text": "", "left": 0, "top": 0}}],
  "pending_asset": [{{"id": "", "need": "어떻게 다시 그려야 하나"}}],
  "why": "무엇을 어떻게 고쳤는지 한 문장"}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--allowedTools", "Read", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True, timeout=600, env=env)
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
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    proj, ep = resolve_project(args.ep)
    specs = {s["sceneNumber"]: s for s in
             json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}

    lay_dir = root / "_imggen" / f"{ep.lower()}_layout"
    chk_dir = root / "_imggen" / f"{ep.lower()}_check"
    shots = root / "_imggen" / f"{ep.lower()}_render"

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    jobs = []
    for c in sorted(chk_dir.glob("s*.json")):
        n = int(c.stem[1:])
        if want and n not in want:
            continue
        chk = json.loads(c.read_text(encoding="utf-8"))
        if chk.get("verdict") != "fix":
            continue
        # 지금 도해가 아닌 씬은 고치지 않는다 — 쓰지 않을 화면이다
        if specs.get(n, {}).get("visual_kind") != "infographic":
            continue
        lay_f = lay_dir / f"s{n:03d}.json"
        shot = shots / f"s{n:03d}.png"
        if lay_f.exists() and shot.exists():
            jobs.append((n, lay_f, shot, chk))

    def run(job):
        n, lay_f, shot, chk = job
        lay = json.loads(lay_f.read_text(encoding="utf-8"))
        probs = "\n".join(
            f"  · [{p.get('kind')}] {p.get('detail')}\n    고침: {p.get('fix')}"
            for p in chk.get("problems") or [])
        d = ask(PROMPT.format(
            path=shot.resolve(),
            narration=(specs.get(n, {}).get("narration") or "")[:300],
            layout=json.dumps({k: lay.get(k) for k in
                               ("title", "background", "contrast", "divider", "items", "marks")},
                              ensure_ascii=False, indent=1),
            problems=probs))
        if not d:
            return n, "실패"
        # 요소 목록은 원래 있던 것만 남긴다 — 없는 그림을 부르면 화면이 빈다
        ids = {it["id"] for it in lay.get("items") or []}
        d["items"] = [it for it in (d.get("items") or []) if it.get("id") in ids]
        if not d["items"]:
            return n, "고친 배치에 요소가 없다 — 그대로 둔다"
        lay_f.with_suffix(".json.bak").write_text(
            json.dumps(lay, ensure_ascii=False, indent=1), encoding="utf-8")
        lay.update({k: d[k] for k in ("title", "background", "contrast", "divider",
                                      "items", "marks") if k in d})
        lay["fix_note"] = d.get("why", "")
        if d.get("pending_asset"):
            lay["pending_asset"] = d["pending_asset"]
        lay_f.write_text(json.dumps(lay, ensure_ascii=False, indent=1), encoding="utf-8")
        pend = len(d.get("pending_asset") or [])
        return n, f"고침 — {d.get('why','')[:52]}" + (f" (다시 그릴 것 {pend})" if pend else "")

    print(f"{ep}  {len(jobs)}씬 손봄")
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, msg in ex.map(run, jobs):
            print(f"  씬{n:>3}  {msg}")
    print("\n다시 조립하고 그려서 확인하세요:")
    print(f"  python3 scripts/compose_infographics.py {args.ep} --apply")
    print(f"  python3 scripts/render_infographic.py {args.ep}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
