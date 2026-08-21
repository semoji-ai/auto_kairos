#!/usr/bin/env python3
"""그려 놓은 인포그래픽 화면을 **보고** 잘못된 것을 찾는다.

좌표만 적고 끝내면 숫자로는 멀쩡한데 화면은 엉망인 일이 생긴다. 실제로
그려서 보니 이런 것들이 나왔다.

  · `+` 기호가 라벨 위에 겹쳐 찍혔다
  · 흐름을 보여주는 화면인데 세로 구분선이 가운데를 갈라 놓았다
  · 씬 그림을 배경으로 깔았더니 그 그림이 이미 같은 내용을 말하고 있어
    얹은 요소가 군더더기가 됐다
  · 먹색 글자를 그림 위에 올려 묻혔다

셋 다 좌표만 봐서는 알 수 없다. 그려서 보는 수밖에 없다.

결과는 씬마다 `_imggen/<ep>_check/sNNN.json`. 판정이 셋이다.
  keep        그대로 쓴다
  fix         고칠 곳이 있다 (무엇을 어떻게 고칠지 함께 적는다)
  scene_only  얹지 말고 씬 그림만 쓴다

    python3 scripts/check_infographic.py EP01 --scenes 14,15
    python3 scripts/check_infographic.py EP01
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

PROMPT = """첨부한 그림은 다큐멘터리 한 장면의 **인포그래픽 화면**입니다.
Read 도구로 그림을 열어 보고 판단하세요.

{path}

## 이 화면이 해야 하는 말

나레이션: {narration}

## 무엇을 보나

**말이 화면으로 설명되는가**가 첫 기준입니다. 예쁜지가 아닙니다.

그리고 이런 사고를 찾으세요. 실제로 났던 것들입니다.

1. **겹침** — 기호(+ = →)가 라벨을 덮거나, 요소끼리 포개졌거나,
   글자가 다른 글자 위에 찍혔다
2. **화면 밖** — 요소나 글자가 가장자리에서 잘렸다
3. **묻힌 글자** — 배경 그림 위에 먹색 글자를 올려 읽히지 않는다
4. **쓸데없는 선** — 흐름을 보여주는 화면인데 세로 구분선이 가운데를 갈랐다
   (구분선은 좌우를 **대비**할 때만)
5. **군더더기** — 배경으로 깐 씬 그림이 이미 같은 내용을 말하고 있어
   얹은 요소가 덧붙임이 됐다. 이때는 얹지 말아야 한다
6. **뜻이 틀린 요소** — 「쌀 844가마」인데 자루가 하나만 그려졌다처럼,
   많음을 낱개로 보여주고 있다
7. **나열** — 항이 묶이지도 이어지지도 않고 그냥 늘어서 있다

## 판정

  `keep`        그대로 써도 된다
  `fix`         고칠 곳이 있다 — 무엇을 어떻게 바꿀지 적는다
  `scene_only`  얹지 말고 씬 그림만 쓰는 편이 낫다

## 낼 것 — JSON만

{{"verdict": "keep | fix | scene_only",
  "problems": [{{"kind": "겹침 | 화면밖 | 묻힘 | 쓸데없는선 | 군더더기 | 뜻이틀림 | 나열",
                 "detail": "무엇이 어떻게 잘못됐나",
                 "fix": "어떻게 고치나 (좌표를 바꾸라면 숫자로)"}}],
  "say": "한 문장 총평"}}
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
    ap.add_argument("--force", action="store_true",
                    help="이미 본 화면도 다시 본다 (고친 뒤에는 반드시)")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    proj, ep = resolve_project(args.ep)
    specs = {s["sceneNumber"]: s for s in
             json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}

    shots = root / "_imggen" / f"{ep.lower()}_render"
    out_dir = root / "_imggen" / f"{ep.lower()}_check"
    out_dir.mkdir(parents=True, exist_ok=True)

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    jobs = []
    for p in sorted(shots.glob("s*.png")):
        n = int(p.stem[1:])
        if want and n not in want:
            continue
        jobs.append((n, p))

    def run(job):
        n, p = job
        f = out_dir / f"s{n:03d}.json"
        if f.exists():
            if not args.force:
                return n, "이미 봄"
        d = ask(PROMPT.format(path=p.resolve(),
                              narration=(specs.get(n, {}).get("narration") or "")[:300]))
        if not d:
            return n, "실패"
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        kinds = ", ".join(x.get("kind", "") for x in d.get("problems") or [])
        return n, f"{d.get('verdict')}  {kinds}"

    print(f"{ep}  {len(jobs)}장 검수")
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, msg in ex.map(run, jobs):
            print(f"  씬{n:>3}  {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
