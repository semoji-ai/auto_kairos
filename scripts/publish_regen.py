#!/usr/bin/env python3
"""재생성한 씬 이미지를 프로젝트에 등록한다 (버전 올림, 기존 파일 유지)."""
from __future__ import annotations
import argparse, json, re, shutil, sys, time
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep"); ap.add_argument("--since-hours", type=float, default=6.0)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    D = Path(next(v["dir"] for k, v in emap.items() if k.startswith(a.ep)))
    src = root / "_imggen" / a.ep.lower() / "out"
    if not src.exists():
        print(f"  {a.ep}: 산출 폴더 없음"); return 1
    cut = time.time() - a.since_hours * 3600
    latest: dict[int, Path] = {}
    for p in src.glob("scene_*.png"):
        m = re.match(r"scene_(\d+)", p.name)
        if not m or p.stat().st_mtime < cut:
            continue
        n = int(m.group(1))
        if n not in latest or p.stat().st_mtime > latest[n].stat().st_mtime:
            latest[n] = p
    g = D / "images" / "generated"; g.mkdir(parents=True, exist_ok=True)
    f = D / "images" / "image_assets.json"
    db = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"scenes": []}
    by = {e["sceneNumber"]: e for e in db["scenes"]}
    spec = {s["sceneNumber"]: (s.get("imageAsset") or {}).get("source")
            for s in json.loads((D / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]}
    ok = 0
    for n, p in sorted(latest.items()):
        if spec.get(n) != "generate":
            continue          # 실물을 쓰기로 한 씬은 건드리지 않는다
        vs = [int(x.group(1)) for q in g.glob(f"scene_{n:03d}_gen_*.png")
              if (x := re.search(r"_gen_(\d+)", q.name))]
        dst = g / f"scene_{n:03d}_gen_{max(vs, default=0) + 1:02d}.png"
        shutil.copy2(p, dst)
        e = by.setdefault(n, {"sceneNumber": n, "images": []})
        for i in e["images"]:
            i["selected"] = False
        e["images"].append({"file": f"generated/{dst.name}", "type": "generated",
                            "selected": True})
        ok += 1
    db["scenes"] = sorted(by.values(), key=lambda x: x["sceneNumber"])
    f.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {a.ep}: 등록 {ok}컷")
    return 0

if __name__ == "__main__":
    sys.exit(main())
