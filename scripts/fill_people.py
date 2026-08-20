#!/usr/bin/env python3
"""화면마다 **누가 나오는지** 못 박는다. 사람이 없는 화면은 없다고 못 박는다.

이 칸이 비면 생성기가 짐작한다. 짐작이 틀리면 두 방향으로 어긋난다.

  · 「여인들이 옷에 돈을 썼다」인데 화면에 사람이 하나도 없다
  · 구인회 한 명이 나와야 할 컷에 넷이 몰려 나온다

실제로 EP01 에서 새로 그린 39컷 중 24컷이 그랬다. 짐작을 없애는 길은
**화면을 짤 때 정해 두는 것**뿐이다.

  people: ["열네 살의 구인회, 사모관대 차림"]     → 이 한 명만 그린다
  people: []                                      → 사물만. 사람을 그리지 않는다

손이나 뒷모습만 나와도 사람이다.

    python3 scripts/fill_people.py EP01 --apply
    python3 scripts/fill_people.py EP01 --scenes 970,986
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

WINDOW = 14

PROMPT = """화면마다 **누가 나오는지** 정합니다.

## 씬

{scenes}

## 가르는 기준

  사람이 있어야 한다   누가 무엇을 한다 · 감정이 실린 순간 ·
                       **사람이 주어인 말** (진학했습니다 · 돈을 썼습니다 ·
                       판단했습니다 · 돌아왔습니다)
  사물만으로 충분하다   현판 · 문서 · 간판 · 장부 · 물건이 곧 내용일 때
                       (「그 집을 구교리댁이라 불렀다」 → 현판)

**손이나 뒷모습만 나와도 사람입니다.** 그때도 적으세요.

**꼭 필요한 사람만 적습니다.** 화면을 채우려 사람을 늘리면 누가 주인공인지
흐려집니다 — 구인회 한 명인 컷에 넷이 나온 적이 있습니다.

사람마다 **누구이고 어떤 차림인지** 한 줄로 적습니다. 나이와 옷차림이 있어야
매번 다른 얼굴로 그려지지 않습니다.

## 낼 것 — JSON만. 씬 전부에 대해 한 줄씩.

{{"scenes": [
  {{"scene": 씬번호, "people": ["스물다섯의 구인회, 무명 두루마기 차림"]}},
  {{"scene": 씬번호, "people": []}}
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
    ap.add_argument("--scenes")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    todo = [s for s in scenes
            if s.get("visual_kind") in (None, "", "generate_image")
            and not s.get("isChapterCard") and not s.get("isTurnCard")
            and (s.get("narration") or "").strip()]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")

    print(f"{ep}  씬 {len(todo)}개")

    def run(chunk):
        body = "\n".join(
            f"  씬{s['sceneNumber']}\n"
            f"    말: {(s.get('narration') or '').strip()[:120]}\n"
            f"    화면: {(s.get('imageAsset') or {}).get('prompt', '')[:160]}"
            for s in chunk)
        return (ask(PROMPT.format(scenes=body)) or {}).get("scenes") or []

    made = []
    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for rows in ex.map(run, chunks):
            made.extend(rows)

    empty = [r["scene"] for r in made if not r.get("people")]
    print(f"  사람 있는 화면 {len(made) - len(empty)} · 사물만 {len(empty)}")
    print(f"  사물만: {empty}")

    if not args.apply:
        print("\n--apply 를 붙이면 반영합니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_people_{datetime.now():%Y%m%d_%H%M%S}"))
    by_n = {s.get("sceneNumber"): s for s in scenes}
    for r in made:
        s = by_n.get(r.get("scene"))
        if s is not None:
            s["people"] = [str(x).strip() for x in (r.get("people") or []) if str(x).strip()]
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(made)}개 씬에 못 박았습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
