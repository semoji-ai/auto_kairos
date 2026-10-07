#!/usr/bin/env python3
"""씬 그림·도해를 Seedream 5.0 layerize(fal)로 요소별 투명 PNG 레이어로 나눈다.

레이어 이름 목록(names.json: {"<key>": {"image": 경로, "names": [...]}} )을 받아
키마다 한 번 호출하고, 결과를 `<out>/<key>/` 에 저장한다.

    <key>/z00_background.png   배경판(인페인팅된 판, 이름 없음)
    <key>/z01_<name>.png ...   요소 레이어
    <key>/elements.json        layer · name · z · bbox [l,t,r,b] · kind · motion  (shared-vs-branch 정본)

이미 `elements.json` 이 있는 키는 건너뛴다(다시 돌려도 과금이 겹치지 않는다).
과금은 레이어 1장당이라, 호출마다 실제 레이어 수를 `usage.jsonl` 에 남긴다.

**레이어 분리는 이 경로(fal bytedance/seedream/v5/pro/layerize) 하나만 쓴다.**
Codex 마젠타 매트(codex_matte_layers.py)·OCR 사각 자르기·layerkit 다시 그리기는 금지
(예외는 사용자 승인 — docs/rules/scene-visual-decision.md ⑥).

점검(돈이 드는 호출 앞뒤로):
  · 이름 목록 완전성 — 항목에 `"expected": [...]`(씬에서 등장시킬 요소 전부: 글자 덩어리,
    연결선, 화살표, 건물에 딸린 나무·연기 …)를 주면 names 에 빠진 것을 호출 전에 알린다.
    `--strict` 면 빠진 키는 호출하지 않고 실패로 남긴다. `--expected <json>` 으로 따로 줄 수도 있다.
  · 응답 누락 — 보낸 이름의 레이어가 안 돌아오면 elements.json `missing_layers` 에 남긴다.
  · 배경판 잔상 — 요소가 z0 배경판에 그대로 남았는지(이중 표시) 원본과 비교해
    elements.json 요소마다 `bg_residue` 를 달고 `<out>/layer_report.json` 에 모은다.
    이미 나눈 폴더는 `--recheck` 로 호출 없이 점검만 한다.

    python3 scripts/layerize_scenes.py <names.json> -o <out_dir> [--only k1,k2] [-j 4]
                                       [--expected exp.json] [--strict] [--recheck]
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

sys.path.insert(0, str(ROOT))
from auto_agent.tools.layer_checks import check_layer_dir, missing_expected, missing_returned  # noqa: E402

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
    lost = missing_returned(item["names"], [L["name"] for L in layers])
    meta = {"key": key, "source": item["image"], "names": item["names"], "elements": elements}
    if item.get("expected"):
        meta["expected"] = item["expected"]
    if lost:
        meta["missing_layers"] = lost
    (d / "elements.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    residue = check_layer_dir(d)
    return {"key": key, "layers": len(layers), "base_size": base["size"], "sec": round(time.time() - t0, 1),
            "missing_layers": lost, "residue": residue}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("names", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--only")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--expected", type=Path, help='{"<key>": [등장시킬 요소 …]} — names 완전성 검사')
    ap.add_argument("--strict", action="store_true", help="이름 목록에 빠진 요소가 있으면 그 키는 호출하지 않는다")
    ap.add_argument("--recheck", action="store_true", help="호출 없이 이미 나눈 폴더의 잔상만 다시 점검")
    args = ap.parse_args()
    items = json.loads(args.names.read_text(encoding="utf-8"))
    if args.expected:
        for k, exp in json.loads(args.expected.read_text(encoding="utf-8")).items():
            if k in items:
                items[k] = {**items[k], "expected": exp}
    keys = list(items)
    if args.only:
        want = [k.strip() for k in args.only.split(",")]
        keys = [k for k in keys if k in want]
    args.out.mkdir(parents=True, exist_ok=True)
    usage = args.out / "usage.jsonl"

    # 이름 목록 완전성 — 호출(과금) 전에 본다
    gaps = {k: missing_expected(items[k].get("expected"), items[k]["names"]) for k in keys}
    gaps = {k: v for k, v in gaps.items() if v}
    for k, v in gaps.items():
        print(f"  ! {k}: 이름 목록에 없는 등장 요소 {v} — 배경판에 그대로 남는다", flush=True)

    def job(k):
        if args.recheck:
            d = args.out / k
            if not (d / "elements.json").exists():
                return {"key": k, "skipped": True}
            return {"key": k, "rechecked": True, "residue": check_layer_dir(d)}
        if args.strict and k in gaps:
            return {"key": k, "error": f"이름 목록 누락 {gaps[k]} (--strict)"}
        try:
            return run_one(k, items[k], args.out)
        except FalError as e:
            return {"key": k, "error": str(e)}

    total, report = 0, {"name_gaps": gaps, "missing_layers": {}, "residue": [], "errors": {}}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(job, keys):
            if r.get("layers"):
                total += r["layers"]
                with usage.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({k: v for k, v in r.items() if k != "residue"}, ensure_ascii=False) + "\n")
            if r.get("missing_layers"):
                report["missing_layers"][r["key"]] = r["missing_layers"]
            if r.get("error"):
                report["errors"][r["key"]] = r["error"]
            report["residue"].extend(x for x in r.get("residue") or [] if "error" not in x)
            mark = "·" if r.get("skipped") else ("✗" if r.get("error") else "✓")
            print(f"  {mark} {r['key']:<12} {r.get('layers', '')} {r.get('base_size', '')} {r.get('error', '')}",
                  flush=True)
            for x in r.get("residue") or []:
                if "error" in x:
                    print(f"      ? 잔상 점검 못 함: {x['error']}")
                else:
                    print(f"      {'✗' if x['level'] == 'flag' else '!'} 배경판 잔상 {x['score']}: {x['name']}")
            if r.get("missing_layers"):
                print(f"      ! 안 돌아온 레이어: {r['missing_layers']}")
    (args.out / "layer_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    n_flag = sum(1 for x in report["residue"] if x["level"] == "flag")
    print(f"\n새로 나눈 레이어 {total}장 · 배경판 잔상 {n_flag}건(+확인 {len(report['residue']) - n_flag}) · "
          f"이름 누락 {len(gaps)}키 → {args.out / 'layer_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
