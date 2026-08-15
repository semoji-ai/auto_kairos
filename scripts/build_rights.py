#!/usr/bin/env python3
"""실물 자료의 권리 상태를 판정해 scene_specs에 출처와 상태를 심는다.

세 갈래다.

    free        공공누리·CC·퍼블릭 도메인·권리 정리 완료 — 그냥 쓴다
    lg          LG 계열사 자료 — 별도 협의 없이 쓴다 (사용자 지시)
    negotiate   보도 인용·개별 허락 필요 — **협의 전까지 화면에 붉게 표시한다**

붉은 출처 자막은 「아직 정리 안 된 자료」를 눈으로 잡기 위한 것이다. 렌더 화면을
넘겨보다 붉은 글씨가 보이면 그 컷은 아직 못 나간다. 협의가 끝나면 `owner_cleared`로
바꾸고 다시 돌리면 흰색이 된다.

    python3 scripts/build_rights.py            # 전 편
    python3 scripts/build_rights.py --report   # 협의 목록만 출력
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FREE = re.compile(r"public[_ ]domain|cc[_ ]?by|kogl|공공누리|owner_cleared|자유 ?이용", re.I)
LG = re.compile(r"LG|금성|락희|GS그룹")
NEED = re.compile(r"permission_required|press_quote|all rights reserved|미표기|인용", re.I)


def classify(entry: dict) -> str:
    lic = str(entry.get("license") or "")
    holder = str(entry.get("holder") or "")
    # LG 계열사 자료는 협의 없이 쓴다 — 다만 자유 라이선스와는 구분해 둔다
    if LG.search(lic) or (LG.search(holder) and not FREE.search(lic)):
        return "lg"
    if FREE.search(lic):
        return "free"
    if NEED.search(lic) or not lic:
        return "negotiate"
    return "negotiate"


def credit(entry: dict) -> str:
    h = (entry.get("holder") or "").split(";")[0].strip()
    return h or "출처 미상"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="협의 목록만 낸다")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    rows: list[dict] = []
    stat = {"free": 0, "lg": 0, "negotiate": 0}

    for key in sorted(emap, key=lambda x: x[:4]):
        ep = key[:4]
        led = root / "_imggen" / f"{ep}_ledger.json"
        if not led.exists():
            continue
        D = Path(emap[key]["dir"])
        sp = D / "scene_specs.json"
        data = json.loads(sp.read_text(encoding="utf-8"))
        scenes = {s["sceneNumber"]: s for s in data["scenes"]}

        for e in json.loads(led.read_text(encoding="utf-8")).get("scenes", []):
            if not e.get("found"):
                continue
            s = scenes.get(e["n"])
            if not s or (s.get("imageAsset") or {}).get("source") != "search":
                continue
            st = classify(e)
            stat[st] += 1
            s["attribution"] = credit(e)
            s["attributionStatus"] = st       # 렌더러가 붉은색 여부를 이걸로 정한다
            rows.append({"ep": ep, "n": e["n"], "status": st,
                         "holder": credit(e), "license": e.get("license"),
                         "page_url": e.get("page_url"), "desc": (e.get("desc") or "")[:70]})
        if not args.report:
            sp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    out = root / "_imggen" / "rights.json"
    if not args.report:
        out.write_text(json.dumps({"summary": stat, "items": rows},
                                  ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  실물 {sum(stat.values())}건 — 자유 {stat['free']} / LG {stat['lg']}"
          f" / 협의 필요 {stat['negotiate']}")
    if args.report:
        for r in [x for x in rows if x["status"] == "negotiate"]:
            print(f"    {r['ep']} 씬{r['n']:>3}  {r['holder'][:28]:<28} {r['license']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
