#!/usr/bin/env python3
"""씬 이미지의 최신본만 따로 모은다 — 버전이 섞여 헷갈리지 않게.

한 씬을 여러 번 다시 그리면 `scene_023.png`, `scene_023_v2.png` … 가 한 폴더에
쌓인다. 어느 것이 쓰이는지 눈으로 알 수 없다.

    out/       그린 것 전부 (지우지 않는다 — 이미지 삭제 금지 규칙)
    current/   씬마다 최신본 하나씩, 하드링크로 (용량이 늘지 않는다)

    python3 scripts/organize_versions.py _imggen/ep01
"""
from __future__ import annotations
import argparse, re, sys
from pathlib import Path

def latest(out: Path) -> dict[int, Path]:
    best: dict[int, tuple[int, Path]] = {}
    for p in out.glob("scene_*.png"):
        m = re.match(r"scene_(\d+)(?:_v(\d+))?$", p.stem)
        if not m:
            continue
        n, v = int(m.group(1)), int(m.group(2) or 1)
        if v >= best.get(n, (0, None))[0]:
            best[n] = (v, p)
    return {n: p for n, (v, p) in best.items()}

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("epdir", type=Path)
    args = ap.parse_args()
    out = args.epdir / "out"
    if not out.exists():
        print(f"  {args.epdir.name}: out 폴더 없음")
        return 1
    cur = args.epdir / "current"
    cur.mkdir(exist_ok=True)
    for f in cur.glob("scene_*.png"):
        f.unlink()
    picked = latest(out)
    older = 0
    for n, src in sorted(picked.items()):
        dst = cur / f"scene_{n:03d}.png"
        try:
            dst.hardlink_to(src)
        except OSError:
            dst.write_bytes(src.read_bytes())
    older = len(list(out.glob("scene_*.png"))) - len(picked)
    print(f"  {args.epdir.name}: 최신 {len(picked)}장 → current/  (이전 버전 {older}장은 out/에 보존)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
