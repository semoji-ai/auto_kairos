#!/usr/bin/env python3
"""폐기한 실물 자료 자리를 무엇으로 채울지 정한 결과를 반영한다.

관련성 관문에서 버린 22씬은 화면이 비었다. 판단은 셋으로 갈렸다.

    search   더 찾아보니 그 사실을 직접 증명하는 다른 기록이 있었다
             (사진만이 기록이 아니다 — 실적표, 공시, 연혁, 신문 지면)
    graphic  관계·수치·구조를 말하는 씬이라 사람 얼굴로는 안 보인다
             초상 대신 도표를 넣는다
    scene    사건·행동의 순간이 있다 — 그림이 낫다

`graphic`의 `layout`은 산문으로 오므로 실제 쓰는 값으로 옮긴다. 없는 값을
넣으면 렌더러가 화면을 못 그린다.

    python3 scripts/apply_dropped_fill.py EP01
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 산문 서술 → 실제 layout. 위에서부터 먼저 맞는 것을 쓴다.
LAYOUT = [
    (re.compile(r"저울|비교|양면|좌우 (가지|갈라|비교)|대칭|두 (기준|쪽)|병렬|이분할"), "before_after"),
    (re.compile(r"스포트라이트|큰 숫자|화면 높이의 절반|카운터"), "metric_spotlight"),
    (re.compile(r"관문|차례로 통과|단계|화살표|분기|인과|레일|정거장"), "flow"),
    (re.compile(r"타임라인|연표|1[89]\d\d\s*→|연도별"), "timeline"),
    (re.compile(r"막대|게이지|점유율|그래프|곡선"), "bar"),
]


def pick_layout(text: str, n_elements: int) -> str:
    for rx, name in LAYOUT:
        if rx.search(text or ""):
            return name
    return "items_list" if n_elements > 4 else "split"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    fp = root / "_imggen" / f"{args.ep}_fill.json"
    if not fp.exists():
        print(f"  {args.ep}: 판단 결과 없음")
        return 1
    items = json.loads(fp.read_text(encoding="utf-8"))["items"]

    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    proj = Path(next(v["dir"] for k, v in emap.items() if k.startswith(args.ep)))
    spec_path = proj / "scene_specs.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data["scenes"]}

    led_path = root / "_imggen" / f"{args.ep}_ledger.json"
    led = json.loads(led_path.read_text(encoding="utf-8"))
    entries = {e["n"]: e for e in led.get("scenes", led)}

    done = {"search": 0, "graphic": 0, "scene": 0}
    for it in items:
        n, kind = it["n"], it["kind"]
        s = scenes.get(n)
        if not s:
            continue
        if kind == "search":
            e = entries.setdefault(n, {"n": n})
            e.update({k: it[k] for k in ("image_url", "page_url", "holder", "license",
                                         "checked", "desc", "relevance") if it.get(k)})
            e["found"] = True
            e.pop("reason", None)
            s.setdefault("imageAsset", {})["source"] = "search"
        elif kind == "graphic":
            # 도표는 이미지가 필요 없다. 화면에 뜨는 것은 글자와 숫자다.
            s["layout"] = pick_layout(it.get("layout", ""), len(it.get("elements") or []))
            if it.get("headline"):
                s["headline"] = it["headline"].replace("\\n", "\n")
            if it.get("elements"):
                s["items"] = it["elements"]
            s["imageAsset"] = {"source": "none", "note": it.get("layout", "")}
            s["graphicNote"] = it.get("layout", "")
        elif kind == "scene":
            ia = s.setdefault("imageAsset", {})
            ia["source"] = "generate"
            ia["prompt"] = it.get("prompt", "")
            ia["moment"] = it.get("moment", "")
            if it.get("cast"):
                s["cast"] = it["cast"]
        done[kind] += 1

    if not args.dry_run:
        spec_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        led["scenes"] = sorted(entries.values(), key=lambda x: x["n"]) \
            if isinstance(led, dict) else list(entries.values())
        led_path.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.ep}: 자료 회수 {done['search']} / 도표 {done['graphic']}"
          f" / 재현 {done['scene']}" + ("  [dry-run]" if args.dry_run else ""))
    for it in items:
        if it["kind"] == "graphic":
            print(f"      씬 {it['n']:>3} → {scenes[it['n']]['layout']}"
                  f"  「{(it.get('headline') or '').splitlines()[0]}」")
    return 0


if __name__ == "__main__":
    sys.exit(main())
