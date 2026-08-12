#!/usr/bin/env python3
"""관련성 재조사 결과를 원장에 반영한다.

`relevance` 공란이던 자료를 셋 중 하나로 처리한다.

    keep      근거를 채운다 — 자료는 그대로
    replace   다른 자료로 갈아끼운다 — URL·권리·근거를 통째로 교체
    drop      쓸 수 없다 — found:false로 내리고 씬은 재현(generate)으로 돌린다

**drop한 URL은 원장에서 지워야 한다.** 남겨 두면 나중에 자산 수집이 다시
내려받는다. EP01 씬 53에서 실제로 그랬다 — 인용구 그래픽으로 판정해 걸러낸
자료가 원장에 남아 되살아났다.

    python3 scripts/apply_relevance_recheck.py EP01
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    res_path = root / "_imggen" / f"{args.ep}_relck.json"
    if not res_path.exists():
        print(f"  {args.ep}: 재조사 결과 없음")
        return 1
    items = {i["n"]: i for i in json.loads(res_path.read_text(encoding="utf-8"))["items"]}

    led_path = root / "_imggen" / f"{args.ep}_ledger.json"
    led = json.loads(led_path.read_text(encoding="utf-8"))
    entries = led.get("scenes", led)

    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    proj = Path(next(v["dir"] for k, v in emap.items() if k.startswith(args.ep)))
    spec_path = proj / "scene_specs.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data["scenes"]}

    kept = replaced = dropped = 0
    for e in entries:
        it = items.get(e["n"])
        if not it:
            continue
        act = it.get("action")
        if act == "keep":
            e["relevance"] = it["relevance"]
            kept += 1
        elif act == "replace":
            for k in ("image_url", "page_url", "holder", "license",
                      "checked", "desc", "relevance"):
                if it.get(k):
                    e[k] = it[k]
            e["found"] = True
            e["replaced_reason"] = it.get("why", "")
            replaced += 1
        elif act == "drop":
            # URL을 지운다. 남기면 자산 수집이 다시 내려받는다.
            for k in ("image_url", "page_url", "holder", "license"):
                e.pop(k, None)
            e["found"] = False
            e["reason"] = it.get("why", "씬 내용과 이어지지 않음")
            s = scenes.get(e["n"])
            if s:
                s.setdefault("imageAsset", {})["source"] = "generate"
            dropped += 1

    if not args.dry_run:
        led_path.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
        if dropped:
            spec_path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                 encoding="utf-8")

    print(f"  {args.ep}: 근거 보완 {kept} / 자료 교체 {replaced} / 폐기 {dropped}"
          + ("  [dry-run]" if args.dry_run else ""))
    if dropped:
        ns = [n for n, i in items.items() if i.get("action") == "drop"]
        print(f"      폐기 → 재현으로 전환: 씬 {ns}")
        print("      ⚠ 이 씬들은 imageAsset.prompt를 새로 써야 합니다"
              " (빈 프롬프트면 장면이 날조됩니다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
