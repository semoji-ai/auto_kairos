#!/usr/bin/env python3
"""씬에 등장 인물을 명시하고, 익명 표현과 실루엣 안티패턴을 교정한다.

**왜 필요한가.** scene_specs의 인물 레이어가 "젊은 상인", "작은 실루엣들"처럼
익명으로 쓰이면 씬마다 다른 얼굴이 나온다. 실제로는 대부분 같은 인물이다.
등장 인물을 `cast`로 못박아야 시트를 첨부해 얼굴을 고정할 수 있다.

`docs/rules/character-sheet-rules.md`의 안티패턴도 함께 잡는다.
  ❌ "Subject: 작은 실루엣들"  — 인물이 배경이 되면 등신도 옷 색도 안 보인다

    python3 scripts/assign_scene_cast.py <project_dir> <cast.json>

cast.json:
    {"6": ["koo_inhoe_20s"], "36": ["koo_inhoe_40s", "koo_sunja"]}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 익명 표현 → 실명. cast에 그 인물이 있을 때만 바꾼다.
ANON = {
    "koo_inhoe_20s": [
        (r"젊은 한국인 상인", "20대 구인회"),
        (r"젊은 포목상", "20대 구인회"),
        (r"젊은 상인", "20대 구인회"),
        (r"주판 앞에 앉은 20대 한국인", "주판 앞에 앉은 20대 구인회"),
        (r"30세 안팎 한국인 상인", "30세 무렵 구인회"),
        (r"20대 장손", "20대 구인회"),
        (r"상인의 실루엣", "구인회"),
        (r"상인 실루엣", "구인회"),
        (r"상인의 뒷모습", "구인회의 뒷모습"),
        (r"\b상인\b", "구인회"),
    ],
    "koo_inhoe_40s": [(r"양복 차림 구인회", "40대 구인회"), (r"\b상인\b", "구인회")],
    "koo_jaeseo": [(r"아버지가", "아버지 구재서가"), (r"한복 두루마기 차림 아버지", "구재서")],
    "koo_sunja": [(r"딸에게", "딸 구순자에게")],
}

# 실루엣 안티패턴 — 인물이 화면에서 읽히지 않는다
SILHOUETTE = [
    (r"작은 실루엣들", "얼굴과 옷이 또렷하게 보이는 사람들"),
    (r"작은 (\S+) 실루엣", r"\1"),
    (r"(\S+)의 실루엣", r"\1"),
    (r"(\S+) 실루엣", r"\1"),
]


def apply(text: str, cast: list[str]) -> tuple[str, list[str]]:
    notes = []
    for cid in cast:
        for pat, rep in ANON.get(cid, []):
            new = re.sub(pat, rep, text)
            if new != text:
                notes.append(f"{pat}→{rep}")
                text = new
    for pat, rep in SILHOUETTE:
        new = re.sub(pat, rep, text)
        if new != text:
            notes.append("실루엣 해제")
            text = new
    return text, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("cast", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec = args.project / "scene_specs.json"
    data = json.loads(spec.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)
    cast_map = json.loads(args.cast.read_text(encoding="utf-8"))

    changed = 0
    for s in scenes:
        n = str(s.get("sceneNumber"))
        cast = cast_map.get(n)
        ia = s.get("imageAsset") or {}
        if not cast or ia.get("source") != "generate":
            continue
        s["cast"] = cast
        prompt, notes = apply(ia.get("prompt") or "", cast)
        if notes:
            ia["prompt"] = prompt
            changed += 1
            print(f"  {n:>3} {', '.join(cast):28s} {'; '.join(dict.fromkeys(notes))[:60]}")
        else:
            print(f"  {n:>3} {', '.join(cast):28s} (인물 지정만)")

    if not args.dry_run:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ncast 지정 {sum(1 for s in scenes if s.get('cast'))}씬 / 프롬프트 교정 {changed}씬"
          + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
