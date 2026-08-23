#!/usr/bin/env python3
"""어도비가 뗀 레이어를 리모션 쪽 사슬에 물린다.

**새 형식을 만들지 않는다.** 리모션에는 이미 사슬이 있다.

    layers.json(메타 목록) → build_layered_props.py → props.json → LayeredScene

지금까지 그 `layers.json` 은 `animate_scene.py` 가 만들었다 — 리모션 전용으로
따로 뗀 레이어다. 어도비 패널로 뗀 레이어(`layers/<sid>__*.png`)는 같은 그림을
같은 방식으로 갈라 놓고도 이 사슬에 못 물렸다. **서로 어휘가 달랐을 뿐이다.**

이 스크립트는 그 어휘를 옮긴다. 정본은 `layers/<sid>__elements.json` 이고,
여기서 리모션이 읽는 메타 목록을 굽는다.

    layers/<sid>__elements.json      ← 정본: bbox · kind · z · motion
            ├─ manifest.json          어도비  (컴프 좌표 · 널 + 핑퐁)
            └─ layers/<sid>__remotion.json
                    → build_layered_props.py → props.json  (씬 좌표 · scaleY)

**의도는 공유하고 구현은 각자다.** 「이 인물은 까딱인다」는 정본에 적혀 있고,
그것을 널로 풀지 스프링으로 풀지는 렌더러가 정한다.

    어도비                       리모션
    kind: "character"        →   role: "person"
    motion: "bob"            →   bob: {amp, period, phase}   (props 단계에서)
    "__bg" 이름 규칙          →   bbox 없음 = 배경판

    python3 scripts/build_remotion_layers.py <project_dir> [--scene 100]
    python3 scripts/build_layered_props.py \
        <proj>/layers/<sid>__remotion.json -o props.json --name s100
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def scene_meta(proj: Path, sid: str) -> list:
    """한 씬의 레이어를 리모션 메타 목록으로. 뒤 → 앞 순서.

    `bbox` 는 `[x0, y0, x1, y1]` 그대로 둔다 — `build_layered_props.py` 가
    `[x, y, w, h]` 로 바꾼다. 여기서 미리 바꾸면 두 번 바뀐다.
    """
    L = proj / "layers"
    specs = {}
    fp = L / f"{sid}__elements.json"
    if fp.is_file():
        try:
            for e in json.loads(fp.read_text(encoding="utf-8")):
                specs[e.get("layer")] = e
        except Exception:
            pass

    rows = []
    for p in sorted(L.glob(f"{sid}__*.png")):
        e = specs.get(p.stem) or {}
        is_bg = "__bg" in p.name
        m = {"name": e.get("name") or p.stem, "path": str(p)}
        svg = L / (p.stem + ".svg")
        if svg.is_file():
            m["svg"] = str(svg)          # 있으면 벡터를 쓴다 — 확대해도 다시 그린다
        if not is_bg:
            b = e.get("bbox")
            if b and len(b) == 4:
                m["bbox"] = list(b)
        m["role"] = "bg" if is_bg else (
            "person" if e.get("kind") == "character" else "prop")
        if e.get("motion"):
            m["motion"] = e["motion"]    # 의도를 그대로 실어 보낸다
        rows.append((0 if is_bg else 1,
                     e.get("z") if e.get("z") is not None else 999, p.stem, m))
    rows.sort(key=lambda x: (x[0], x[1], x[2]))
    return [r[3] for r in rows]


def build(proj: Path, only=None) -> list:
    fp = proj / "scenes.json"
    if not fp.is_file():
        raise SystemExit(f"scenes.json 없음: {proj}")
    data = json.loads(fp.read_text(encoding="utf-8"))
    rows = data.get("scenes") if isinstance(data, dict) else data
    made = []
    for s in rows or []:
        sid = s.get("sceneId")
        n = s.get("sceneNumber")
        if not sid or (only is not None and float(n) != float(only)):
            continue
        meta = scene_meta(proj, sid)
        if len(meta) < 2:               # 배경 하나뿐이면 레이어 씬이 아니다
            continue
        out = proj / "layers" / f"{sid}__remotion.json"
        out.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        made.append((n, sid, meta))
    return made


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", type=Path)
    ap.add_argument("--scene", help="이 씬만")
    a = ap.parse_args()
    made = build(a.project, a.scene)
    nb = sum(1 for _n, _s, m in made for x in m if x.get("motion") == "bob")
    nl = sum(len(m) for _n, _s, m in made)
    print(f"  레이어 씬 {len(made)}개 · 레이어 {nl}장 · 까딱임 {nb}장"
          f" → layers/<sid>__remotion.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
