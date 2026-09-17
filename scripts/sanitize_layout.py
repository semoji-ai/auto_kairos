#!/usr/bin/env python3
"""겹침·화면밖을 **계산으로** 막는다. 모델에게 다시 묻지 않는다.

도해 화면을 고칠 때 좌표를 모델에게 다시 물어봤다. 세 바퀴를 돌려도 겹침과
화면밖이 남았다 — 숫자를 눈대중으로 옮기는 일이라 그렇다. 씬12는 인물 넷이
세로로 겹쳐 쌓여 아래가 잘렸다.

기하는 계산으로 푼다.

  ① 화면 밖으로 나가지 않게 안쪽으로 당긴다
  ② 겹치면 서로 밀어낸다 (라벨 자리까지 헤아려서)
  ③ 요소가 많으면 크기를 줄인다 — 넷이 세로로 서면 하나가 클 수 없다

뜻이 어긋난 것은 여기서 못 고친다. 그건 요소나 설계를 다시 봐야 한다.

    python3 scripts/sanitize_layout.py EP01
    python3 scripts/sanitize_layout.py EP01 --scenes 12,43
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

MARGIN = 6.0          # 화면 가장자리에서 이만큼은 비운다 (%)
LABEL = 7.0           # 요소 아래 라벨이 차지하는 높이 (%)
GAP = 2.5             # 요소 사이 최소 틈 (%)
TITLE_BOTTOM = 14.0   # 제목이 차지하는 위쪽 (%)


def box(it: dict) -> tuple[float, float, float, float]:
    """요소가 차지하는 네모 (left, top, right, bottom) — 라벨 자리를 더한다."""
    w = float(it.get("size", 20))
    h = w * 9 / 16 * (16 / 9) / 1.0     # size 는 너비 기준(%), 높이도 대략 같게 본다
    h = w
    cx, cy = float(it.get("left", 50)), float(it.get("top", 50))
    b = cy + h / 2 + (LABEL if it.get("label") else 0)
    return cx - w / 2, cy - h / 2, cx + w / 2, b


def sanitize(lay: dict) -> tuple[dict, list]:
    items = lay.get("items") or []
    if not items:
        return lay, []
    notes = []

    # ③ 요소가 많으면 크기를 줄인다 — 넷이 세로로 서면 하나가 클 수 없다
    room = 100 - TITLE_BOTTOM - MARGIN * 2
    tall = sorted(items, key=lambda i: float(i.get("top", 50)))
    if len(items) >= 3:
        cap = max(10.0, (room - GAP * (len(items) - 1)) / len(items) - LABEL)
        for it in items:
            if float(it.get("size", 20)) > cap:
                it["size"] = round(cap, 1)
                notes.append(f"{it.get('id')} 크기 {cap:.0f}%로")

    # ② 겹치면 밀어낸다 — 다만 **가로로 이미 갈라진 것은 건드리지 않는다.**
    # 「3,800원 = 쌀 844가마」처럼 좌우로 놓은 두 항을 세로로 밀면 한쪽이
    # 아래로 내려가 저울이 기울어 보인다.
    def h_of(it):
        return float(it.get("size", 20)) + (LABEL if it.get("label") else 0)

    def overlaps_x(a, b):
        wa, wb = float(a.get("size", 20)), float(b.get("size", 20))
        ax, bx = float(a.get("left", 50)), float(b.get("left", 50))
        return abs(ax - bx) < (wa + wb) / 2

    y = TITLE_BOTTOM + MARGIN
    for idx, it in enumerate(tall):
        # 앞 요소들과 가로로 안 겹치면 세로로 밀 이유가 없다
        if any(not overlaps_x(it, o) for o in tall[:idx]) and tall[:idx]:
            if all(not overlaps_x(it, o) for o in tall[:idx]):
                continue
        h = h_of(it)
        want = float(it.get("top", 50)) - h / 2
        if want < y:
            it["top"] = round(y + h / 2, 1)
            notes.append(f"{it.get('id')} 아래로 내림")
            want = y
        y = max(y, want) + h + GAP

    # ① 화면 밖으로 나가지 않게 당긴다
    for it in items:
        w = float(it.get("size", 20))
        h = w + (LABEL if it.get("label") else 0)
        left = min(max(float(it.get("left", 50)), MARGIN + w / 2), 100 - MARGIN - w / 2)
        top = min(max(float(it.get("top", 50)), TITLE_BOTTOM + h / 2),
                  100 - MARGIN - h / 2)
        if abs(left - float(it.get("left", 50))) > 0.5 or \
           abs(top - float(it.get("top", 50))) > 0.5:
            notes.append(f"{it.get('id')} 안으로 당김")
        it["left"], it["top"] = round(left, 1), round(top, 1)

    # 글자가 그림 위에 겹치면 묻힌다. 겹치는지는 좌표로 알 수 있다 —
    # 「신용」이 공장 문 한가운데 놓여 읽히지 않았다.
    #
    #   겹치지 않으면   plain 그대로
    #   겹치면          box 로 바꿔 글자 뒤에 판을 깐다
    boxes = []
    for it in items:
        w = float(it.get("size", 20))
        h = w + (LABEL if it.get("label") else 0)
        cx, cy = float(it.get("left", 50)), float(it.get("top", 50))
        boxes.append((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    over = 0
    for m in lay.get("marks") or []:
        if m.get("style") in ("stamp", "label"):
            continue
        mx, my = float(m.get("left", 50)), float(m.get("top", 50))
        if any(x0 <= mx <= x1 and y0 <= my <= y1 for x0, y0, x1, y1 in boxes):
            over += 1
    if over and lay.get("contrast") == "plain":
        lay["contrast"] = "box"
        notes.append(f"글자 {over}개가 그림 위에 겹쳐 box 로")

    # 제목과 똑같은 말을 강조 라벨로 또 쓰면 군더더기다
    title = (lay.get("title") or "").strip()
    for it in items:
        lb = (it.get("label") or "").strip()
        if lb and title and (lb in title or title in lb) and len(items) > 1:
            it.pop("label", None)
            notes.append(f"{it.get('id')} 라벨이 제목과 같아 뺌")
    return lay, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--scenes")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    specs = {s["sceneNumber"]: s for s in
             json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
    lay_dir = root / "_imggen" / f"{ep.lower()}_layout"
    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None

    hit = 0
    for f in sorted(lay_dir.glob("s*.json")):
        n = int(f.stem[1:])
        if want and n not in want:
            continue
        if specs.get(n, {}).get("visual_kind") != "infographic":
            continue
        lay = json.loads(f.read_text(encoding="utf-8"))
        if lay.get("skip"):
            continue
        lay, notes = sanitize(lay)
        if not notes:
            print(f"  씬{n:>4} 그대로")
            continue
        f.write_text(json.dumps(lay, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  씬{n:>4} {' · '.join(notes[:4])}")
        hit += 1
    print(f"\n{hit}장 손봤습니다. 다시 조립하고 그려서 보세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
