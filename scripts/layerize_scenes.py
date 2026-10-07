#!/usr/bin/env python3
"""씬 그림·도해를 Seedream 5.0 layerize(fal)로 요소별 투명 PNG 레이어로 나눈다.

레이어 이름 목록(names.json: {"<key>": {"image": 경로, "names": [...]}} )을 받아
키마다 한 번 호출하고, 결과를 `<out>/<key>/` 에 저장한다.

    <key>/z00_background.png   배경판(인페인팅된 판, 이름 없음)
    <key>/z01_<name>.png ...   요소 레이어
    <key>/elements.json        layer · name · z · bbox [l,t,r,b] · kind · motion  (shared-vs-branch 정본)

이미 `elements.json` 이 있는 키는 건너뛴다(다시 돌려도 과금이 겹치지 않는다).
과금은 레이어 1장당이라, 호출마다 실제 레이어 수를 `usage.jsonl` 에 남긴다.

    python3 scripts/layerize_scenes.py <names.json> -o <out_dir> [--only k1,k2] [-j 4]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "adobe"))
from backend.fal_api import FalError, layerize  # noqa: E402

PERSON = re.compile(r"\b(man|woman|boy|girl|person|people|soldier|worker|officer|student|"
                    r"child|children|crowd|extras|baby|bride|groom|teacher|official|"
                    r"kim|smith|rhee|park|matsumuro|shin|magruder|berger)\b", re.I)


def slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", s or "").strip("_")[:40] or "layer"


def run_one(key: str, item: dict, out: Path) -> dict:
    d = out / key
    if (d / "elements.json").exists():
        return {"key": key, "skipped": True}
    d.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    layers = layerize(item["image"], item["names"])
    from PIL import Image
    import io
    elements = []
    for L in layers:
        name = L["name"] or "background"
        fn = f"z{(L['z'] or 0):02d}_{slug(name)}.png"
        (d / "_raw").mkdir(exist_ok=True)
        (d / "_raw" / fn).write_bytes(L["data"])          # 받은 그대로 보존
        im = Image.open(io.BytesIO(L["data"]))
        if im.mode == "RGBA":
            # Seedream 은 사물 안쪽 알파를 250~254 로 준다(98% 불투명). 레이어가 겹쳐
            # 움직이면 뒤가 희미하게 비치므로 250 이상은 완전 불투명으로 올린다.
            import numpy as np
            a = np.asarray(im).copy()
            a[..., 3] = np.where(a[..., 3] >= 250, 255, a[..., 3])
            im = Image.fromarray(a)
        im.save(d / fn)
        w, h = im.size
        bbox = L["bbox"]
        if bbox and len(bbox) == 4 and bbox[2] < bbox[0]:   # [x, y, w, h] 로 온 경우 대비
            bbox = [bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]
        person = bool(L["name"] and PERSON.search(L["name"]))
        elements.append({"layer": fn, "name": name, "z": L["z"], "bbox": bbox, "size": [w, h],
                         "kind": "background" if not L["name"] else ("character" if person else "object"),
                         "motion": "bob" if person and "crowd" not in name.lower() and "extras" not in name.lower() else None})
    base = next((e for e in elements if e["kind"] == "background"), elements[0])
    (d / "elements.json").write_text(json.dumps({"key": key, "source": item["image"], "names": item["names"],
                                                 "elements": elements}, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    return {"key": key, "layers": len(layers), "base_size": base["size"], "sec": round(time.time() - t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("names", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--only")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()
    items = json.loads(args.names.read_text(encoding="utf-8"))
    keys = list(items)
    if args.only:
        want = [k.strip() for k in args.only.split(",")]
        keys = [k for k in keys if k in want]
    args.out.mkdir(parents=True, exist_ok=True)
    usage = args.out / "usage.jsonl"

    def job(k):
        try:
            return run_one(k, items[k], args.out)
        except FalError as e:
            return {"key": k, "error": str(e)}

    total = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(job, keys):
            if r.get("layers"):
                total += r["layers"]
                with usage.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            mark = "·" if r.get("skipped") else ("✗" if r.get("error") else "✓")
            print(f"  {mark} {r['key']:<12} {r.get('layers', '')} {r.get('base_size', '')} {r.get('error', '')}",
                  flush=True)
    print(f"\n새로 나눈 레이어 {total}장")
    return 0


if __name__ == "__main__":
    sys.exit(main())
