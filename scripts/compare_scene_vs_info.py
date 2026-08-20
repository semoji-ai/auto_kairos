#!/usr/bin/env python3
"""씬 그림과 인포그래픽을 **나란히 보고** 어느 쪽으로 갈지 정한다.

인포그래픽이 남발되면 영상이 재미없어진다. 도해가 이어지면 사람이 사라지고,
사람이 사라지면 이야기가 아니라 발표가 된다.

그래서 씬마다 둘을 실제로 보고 고른다. 기준이 둘이다.

  **알아듣는가** — 나레이션이 하는 말을 화면이 설명하는가
  **보고 싶은가** — 다음 장면이 궁금해지는가, 아니면 설명을 듣는 기분인가

둘 다 인포그래픽이 이길 때만 인포그래픽이다. 어느 하나라도 씬 그림이 나으면
씬 그림이다 — 이해가 조금 늦어도 사람이 남는 편이 낫다.

    python3 scripts/compare_scene_vs_info.py EP01
    python3 scripts/compare_scene_vs_info.py EP01 --scenes 14,15,43
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROMPT = """다큐멘터리 한 장면을 어떤 화면으로 보여줄지 고릅니다.
Read 도구로 **두 그림을 모두** 열어 보고 판단하세요.

A. 씬 그림(사람이 있는 재연): {scene_img}
B. 인포그래픽(요소를 배치한 도해): {info_img}

## 이 장면이 하는 말

{narration}

앞 장면: {prev}
뒤 장면: {next}

## 무엇을 보나

두 가지를 따로 봅니다.

**① 알아듣는가** — 이 말을 처음 듣는 사람이 어느 화면에서 더 빨리 알아듣나.
수치가 합쳐지거나, 둘을 견주거나, 「없음」을 보여야 하면 도해가 낫습니다.
사람이 무엇을 하거나 감정이 실린 순간이면 재연이 낫습니다.

**② 보고 싶은가** — 어느 화면이 다음을 궁금하게 만드나. 도해가 이어지면
사람이 사라지고, 사람이 사라지면 이야기가 아니라 발표가 됩니다. 앞뒤가
모두 도해라면 여기서는 사람이 나오는 편이 숨이 트입니다.

**둘 다 B가 이길 때만 B입니다.** 하나라도 A가 나으면 A입니다 —
이해가 조금 늦어도 사람이 남는 편이 낫습니다.

셋째 길도 있습니다. 씬 그림 위에 도해를 **얹는** 것(overlay). 그림이
한산하고, 얹을 것이 그림이 말하지 않는 것일 때만 됩니다. 그림이 이미 같은
내용을 보여주면 얹지 마세요.

## 낼 것 — JSON만

{{"pick": "scene | info | overlay",
  "understand": "scene 또는 info — 어느 쪽이 더 빨리 이해되나",
  "watch": "scene 또는 info — 어느 쪽이 더 보고 싶나",
  "why": "고른 이유 한두 문장",
  "note": "overlay를 골랐다면 무엇만 얹을지"}}
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
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    proj = Path(next(v["dir"] for k, v in emap.items() if k.startswith(args.ep)))
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    order = [s.get("sceneNumber") for s in scenes]
    by_n = {s.get("sceneNumber"): s for s in scenes}

    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected

    shots = root / "_imggen" / f"{args.ep.lower()}_render"
    out_dir = root / "_imggen" / f"{args.ep.lower()}_pick"
    out_dir.mkdir(parents=True, exist_ok=True)

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    jobs = []
    for p in sorted(shots.glob("s*.png")):
        n = int(p.stem[1:])
        if want and n not in want:
            continue
        sel = get_selected(proj / "images", n)
        if not sel:
            continue
        jobs.append((n, proj / "images" / sel, p))

    def neighbor(n: int, step: int) -> str:
        try:
            i = order.index(n) + step
        except ValueError:
            return ""
        if 0 <= i < len(order):
            return (by_n[order[i]].get("narration") or "")[:90]
        return ""

    def run(job):
        n, a, b = job
        f = out_dir / f"s{n:03d}.json"
        if f.exists():
            return n, "이미 봄"
        d = ask(PROMPT.format(
            scene_img=a.resolve(), info_img=b.resolve(),
            narration=(by_n.get(n, {}).get("narration") or "")[:300],
            prev=neighbor(n, -1), next=neighbor(n, 1)))
        if not d:
            return n, "실패"
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        return n, (f"{d.get('pick'):8s} 이해 {d.get('understand','')[:5]:5s} "
                   f"보고싶음 {d.get('watch','')[:5]:5s} {d.get('why','')[:44]}")

    print(f"{args.ep}  {len(jobs)}씬 비교")
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, msg in ex.map(run, jobs):
            print(f"  씬{n:>3}  {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
