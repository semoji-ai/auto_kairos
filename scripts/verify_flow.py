#!/usr/bin/env python3
"""이야기 흐름이 그대로인지 확인한다 — 자료에 맞춰 연출을 바꾼 뒤에.

좋은 실물 자료가 있으면 그 자료를 쓸 수 있게 연출을 바꾼다. 다만 **자료가
이야기를 끌고 가서는 안 된다.** 사진이 있다는 이유로 씬의 역할이 달라지면
편 전체의 흐름이 어긋난다.

그래서 바꿔도 되는 것과 손대면 안 되는 것을 갈라 둔다.

    손대면 안 되는 것   narration, beat, infoStructure, keyVisual, 씬 순서
    바꿔도 되는 것      imageAsset(source·prompt), layout(허용 범위 안), motion, items

나레이션은 코드가 원고에서 잘라 붙이므로 구조적으로 안전하지만, 나머지는
사람이나 스크립트가 실수로 건드릴 수 있다. 그것을 여기서 잡는다.

    python3 scripts/verify_flow.py <project_dir> --before <이전 scene_specs.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# 흐름을 이루는 것들 — 자료 때문에 바뀌면 안 된다
FROZEN = ("narration", "beat", "infoStructure", "keyVisual")


def digest(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8")).hexdigest()[:8]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--before", required=True, type=Path)
    args = ap.parse_args()

    cur = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    old = json.loads(args.before.read_text(encoding="utf-8"))
    cur, old = cur.get("scenes", cur), old.get("scenes", old)

    problems: list[str] = []

    # 1) 씬 순서와 개수
    cn = [s.get("sceneNumber") for s in cur]
    on = [s.get("sceneNumber") for s in old]
    if cn != on:
        gone, new = set(on) - set(cn), set(cn) - set(on)
        if gone:
            problems.append(f"씬이 사라졌다: {sorted(gone)[:8]}")
        if new:
            problems.append(f"씬이 생겼다: {sorted(new)[:8]}")
        if not gone and not new:
            problems.append("씬 순서가 바뀌었다")

    # 2) 얼어 있어야 할 필드
    ob = {s.get("sceneNumber"): s for s in old}

    # 비어 있던 것을 채우는 건 훼손이 아니다. 원래 한 개도 없던 keyVisual을
    # beat에서 유도해 세우는 것은 흐름을 바꾸는 게 아니라 빠진 것을 채우는 일이다.
    had_kv = any(s.get("keyVisual") for s in old)
    frozen = FROZEN if had_kv else tuple(f for f in FROZEN if f != "keyVisual")
    if not had_kv and any(s.get("keyVisual") for s in cur):
        print("      · keyVisual이 없던 편에 새로 세움 (훼손 아님)")

    changed = {f: [] for f in frozen}
    for s in cur:
        o = ob.get(s.get("sceneNumber"))
        if not o:
            continue
        for f in frozen:
            a, b = s.get(f), o.get(f)
            if json.dumps(a, ensure_ascii=False, sort_keys=True) != \
               json.dumps(b, ensure_ascii=False, sort_keys=True):
                changed[f].append(s.get("sceneNumber"))
    for f, ns in changed.items():
        if ns:
            problems.append(f"{f}가 바뀐 씬 {len(ns)}개: {ns[:8]}")

    # 3) 나레이션 전체 (한 글자도 달라지면 안 된다)
    a = digest("".join(s.get("narration") or "" for s in cur))
    b = digest("".join(s.get("narration") or "" for s in old))
    if a != b:
        problems.append(f"나레이션 전체가 달라졌다 ({b} → {a})")

    name = args.project.name
    if problems:
        print(f"  ✗ {name}")
        for p in problems:
            print(f"      {p}")
        return 1

    moved = sum(1 for s in cur
                if (s.get("imageAsset") or {}).get("source")
                != ((ob.get(s.get("sceneNumber")) or {}).get("imageAsset") or {}).get("source"))
    print(f"  ✓ {name}: 흐름 그대로 (연출만 변경 — source 바뀐 씬 {moved}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
