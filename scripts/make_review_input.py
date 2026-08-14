#!/usr/bin/env python3
"""검수 입력을 만든다 — 선택된 생성 이미지를 축소해 붙인다."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from PIL import Image

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep"); ap.add_argument("-o", "--out", required=True, type=Path)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    D = Path(next(v["dir"] for k, v in emap.items() if k.startswith(a.ep)))
    db = json.loads((D / "images" / "image_assets.json").read_text(encoding="utf-8"))
    sel = {e["sceneNumber"]: next((i["file"] for i in e["images"] if i.get("selected")), None)
           for e in db["scenes"]}
    sm = root / "_imggen" / "review_small"; sm.mkdir(exist_ok=True)
    rows = []
    for s in json.loads((D / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]:
        n = s["sceneNumber"]
        if (s.get("imageAsset") or {}).get("source") != "generate" or not sel.get(n):
            continue
        t = sm / f"{a.ep.lower()}_{n:03d}.jpg"
        Image.open(D / "images" / sel[n]).convert("RGB").resize((1024, 585)).save(t, quality=85)
        rows.append({"n": n, "narration": (s.get("narration") or "")[:300],
                     "cast": s.get("cast"), "people": s.get("people"), "small": str(t)})
    a.out.write_text(json.dumps({"scenes": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {a.ep}: 검수 대상 {len(rows)}컷")
    return 0

if __name__ == "__main__":
    sys.exit(main())
