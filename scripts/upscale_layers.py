#!/usr/bin/env python3
"""레이어 폴더의 PNG 를 로컬 Upscayl(digital-art-4x)로 키운다 — image-layerkit 의 업스케일 단계.

`<layers>/<key>/elements.json` 이 있는 폴더마다 레이어 PNG(배경판 포함)를 `<key>/up/` 에
같은 이름으로 2배 저장한다. 원본은 그대로 둔다. 이미 있는 파일은 건너뛴다.
Upscayl 은 RGBA 알파를 함께 키운다(실측: 투명 비율 43.7% → 43.9%).

elements.json 에 `"upscale": {"scale": 2, "model": ...}` 를 적어 둔다 — 좌표(bbox)는
원본 캔버스 기준이므로, 업스케일본을 쓸 때는 scale 로 나눠 배치한다.

    python3 scripts/upscale_layers.py <layers_dir> [--scale 2] [-j 3] [--only k1,k2]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path.home() / "Projects" / "image-layerkit"))
from layerkit.upscale import status, upscale_image  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("layers", type=Path)
    ap.add_argument("--scale", type=int, default=2)
    ap.add_argument("-j", "--jobs", type=int, default=3)
    ap.add_argument("--only")
    a = ap.parse_args()
    st = status()
    if not st["installed"] or not st["models"]:
        raise SystemExit(f"Upscayl 사용 불가: {st['hint']}")

    dirs = [d for d in sorted(a.layers.iterdir()) if (d / "elements.json").exists()]
    if a.only:
        want = set(a.only.split(","))
        dirs = [d for d in dirs if d.name in want]
    todo = []
    for d in dirs:
        for f in sorted(d.glob("*.png")):
            if f.name.startswith("_"):
                continue                      # _matte·_plate 같은 중간 산출물
            out = d / "up" / f.name
            if not out.exists():
                todo.append((f, out))

    def one(t):
        return t[0], upscale_image(t[0], t[1], content="illustration", scale=a.scale)

    ok = fail = 0
    model = None
    with ThreadPoolExecutor(max_workers=a.jobs) as ex:
        for f, r in ex.map(one, todo):
            if r["status"] == "completed":
                ok += 1
                model = r["model"]
            else:
                fail += 1
                print(f"  ✗ {f.parent.name}/{f.name}: {r.get('error')}", flush=True)
    for d in dirs:
        p = d / "elements.json"
        m = json.loads(p.read_text(encoding="utf-8"))
        m["upscale"] = {"scale": a.scale, "model": model or "digital-art-4x", "dir": "up"}
        p.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"업스케일 {ok}장 · 실패 {fail} · 폴더 {len(dirs)}")
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
