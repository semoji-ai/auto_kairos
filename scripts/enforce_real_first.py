#!/usr/bin/env python3
"""실물 우선 원칙을 scene_specs에 강제한다.

**쓸 수 있는 실물이 있으면 실물을 쓴다.** 생성 이미지는 실물이 없을 때의 대안이지
기본값이 아니다(`docs/rules/direction-standard.md` 1절).

scene_specs를 재생성하면 에이전트가 `source`를 다시 판단해 실물이 생성으로
뒤집힌다. EP04 한 편에서만 25건이 뒤집혔다. 조사 원장(search_assets.json)이
있으면 그것을 진실로 삼아 되돌린다.

    python3 scripts/enforce_real_first.py <project_dir> --ledger <search_assets.json>
    python3 scripts/enforce_real_first.py <project_dir> --restore <이전 scene_specs.json>

--ledger  조사 원장 기준으로 확정 (권장)
--restore 조사 전이라면 이전 판정을 되살려 최소한 뒤집힘만 막는다
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 바로 쓸 수 있는 라이선스
FREE = {"public_domain", "cc_by", "cc_by_sa", "cc0", "kogl_type1", "kogl_type2"}
# 실물은 있으나 권리 협의가 필요 — 실물 우선이므로 search로 두고 협의 대상에 올린다
NEGOTIABLE = {"permission_required", "press_quote"}


def apply_ledger(scenes: list[dict], ledger: dict) -> dict:
    by_n = {e["n"]: e for e in ledger.get("scenes", ledger)}
    stat = {"clear": 0, "negotiate": 0, "no_asset": 0, "flipped_back": 0}
    for s in scenes:
        e = by_n.get(s.get("sceneNumber"))
        ia = s.get("imageAsset")
        if not e or ia is None:
            continue
        if not e.get("found"):
            # 실물이 없는데 search로 두면 '출처 기록'에서 계속 깎인다.
            # 없는 자료는 코드가 만들어낼 수 없다 — 재현으로 확정하고 배지를 단다.
            ia["source"] = "generate"
            ia["assetStatus"] = "no_usable_asset"
            ia["assetNote"] = e.get("reason") or e.get("desc") or "조사에서 확인되지 않음"
            s.setdefault("badge", "일러스트 재현")
            stat["no_asset"] += 1
            continue
        lic = e.get("license")
        was = ia.get("source")
        ia["source"] = "search"
        ia["url"] = e.get("image_url")
        ia["license"] = lic
        ia["assetCandidates"] = [{
            "desc": e.get("desc", ""), "url": e.get("image_url", ""),
            "page": e.get("page_url", ""), "holder": e.get("holder", ""),
            "license": lic, "checked": e.get("checked", ""),
        }]
        if lic in FREE:
            ia["assetStatus"] = "clear"
            stat["clear"] += 1
        elif lic in NEGOTIABLE:
            ia["assetStatus"] = "permission_required"
            stat["negotiate"] += 1
        if was == "generate":
            stat["flipped_back"] += 1
    return stat


def apply_restore(scenes: list[dict], prev: list[dict]) -> dict:
    """조사 전이라면 이전 판정을 되살린다 — 실물로 잡혔던 것만 되돌린다."""
    by_n = {x.get("sceneNumber"): x for x in prev}
    stat = {"restored": 0, "kept": 0}
    for s in scenes:
        p = by_n.get(s.get("sceneNumber"))
        ia, pia = s.get("imageAsset"), (p or {}).get("imageAsset") or {}
        if ia is None or not p:
            continue
        if pia.get("source") == "search" and ia.get("source") == "generate":
            ia["source"] = "search"
            for f in ("assetCandidates", "url", "license", "assetStatus", "query"):
                if pia.get(f) is not None:
                    ia[f] = pia[f]
            stat["restored"] += 1
        else:
            stat["kept"] += 1
    return stat


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--ledger", type=Path)
    ap.add_argument("--restore", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not (args.ledger or args.restore):
        ap.error("--ledger 또는 --restore 중 하나가 필요합니다")

    spec = args.project / "scene_specs.json"
    data = json.loads(spec.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    if args.ledger:
        stat = apply_ledger(scenes, json.loads(args.ledger.read_text(encoding="utf-8")))
    else:
        prev = json.loads(args.restore.read_text(encoding="utf-8"))
        stat = apply_restore(scenes, prev.get("scenes", prev))

    # 조사조차 안 된 search 씬 — URL이 없으면 근거가 없는 것이다
    orphan = 0
    for s in scenes:
        ia = s.get("imageAsset") or {}
        if ia.get("source") == "search" and not ia.get("url") and not ia.get("assetCandidates"):
            ia["source"] = "generate"
            ia["assetStatus"] = "no_usable_asset"
            ia["assetNote"] = "조사 대상에 들지 않았고 확인된 자료가 없음"
            s.setdefault("badge", "일러스트 재현")
            orphan += 1
    if orphan:
        stat["orphan_to_generate"] = orphan

    if not args.dry_run:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    n_search = sum(1 for s in scenes if (s.get("imageAsset") or {}).get("source") == "search")
    print(f"  {args.project.name}: {stat}  → search {n_search}/{len(scenes)}씬"
          + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
