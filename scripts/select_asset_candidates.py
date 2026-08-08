#!/usr/bin/env python3
"""실물 자료를 찾아볼 씬을 고른다 — 전 씬에서, source와 무관하게.

**source가 search인 씬만 조사하면 실물 우선이 봉쇄된다.** 에이전트는 기본적으로
generate로 기울고, 한 번 generate로 찍힌 씬은 조사 대상에서 빠져 실물이 있어도
영영 안 쓰인다. EP02는 65씬 중 search가 5개뿐이었다(EP01은 68씬 중 29개).

그래서 판단 순서를 뒤집는다.
    (X) source가 search인 씬을 조사한다
    (O) 실물이 있을 법한 씬을 조사하고, 있으면 search로 올린다

전 씬을 다 조사하면 편당 한 시간이 넘고, 은유·심리 장면은 조사해도 빈손이다.
그래서 **사료가 있을 자리만 골라낸다.**

    python3 scripts/select_asset_candidates.py <project_dir> -o <out.json>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 실물이 남아 있을 법한 신호 — 나레이션·헤드라인·프롬프트에서 찾는다
SIGNALS = [
    # 고유명사·조직
    (r"[가-힣]{2,}(전자|화학|산업|그룹|반도체|텔레콤|디스플레이|이노텍|생활건강)", "기업"),
    (r"(금성사|락희|럭키|LG|GS|삼성|현대|대우|소니|애플|구글|모토로라|노키아)", "브랜드"),
    # 제품
    (r"(라디오|텔레비전|냉장고|세탁기|에어컨|휴대폰|스마트폰|배터리|반도체|크림|치약)", "제품"),
    (r"(초콜릿폰|프라다폰|샤인폰|옵티머스|롤러블|트롬|디오스|휘센|싸이언)", "제품명"),
    # 인물
    (r"(구인회|구자경|구본무|구광모|허만정|허준구|허창수|이병철|정주영)", "인물"),
    (r"(회장|사장|창업자|대표이사|연구원|기술자)", "직함"),
    # 사건·시점
    (r"\b(19|20)\d{2}년", "연도"),
    (r"(출시|발표|준공|창업|설립|합병|인수|파업|화재|소송|상장|철수|매각)", "사건"),
    # 문서·기록
    (r"(광고|신문|기사|보도|사사|연혁|특허|주권|계약서|약관|보고서|사진)", "기록"),
    # 장소
    (r"(공장|본사|사옥|매장|연구소|단지|박람회|전시회)", "장소"),
]

# 실물이 없는 자리 — 조사해도 빈손이다
SKIP = [
    (r"(마음|생각|믿음|불안|두려움|자존심|각오|의지)", "심리"),
    (r"(상징|은유|비유|처럼|같이 보이는|떠올리)", "은유"),
    (r"^\s*\*\*[^*]+\*\*\s*$", "명제"),  # 강조만 있는 한 줄 = 메시지 씬
]

# 이 레이아웃은 화면에 실물 이미지가 필요하다
IMAGE_LAYOUTS = {"cinematic", "quote_portrait", "images_grid", "before_after", "split"}


def classify(scene: dict) -> tuple[bool, list[str], str]:
    text = " ".join(str(scene.get(f) or "") for f in ("narration", "headline"))
    ia = scene.get("imageAsset") or {}
    text += " " + str(ia.get("prompt") or "") + " " + str(ia.get("query") or "")

    hits = sorted({label for pat, label in SIGNALS if re.search(pat, text)})
    skips = sorted({label for pat, label in SKIP if re.search(pat, text, re.M)})

    layout = scene.get("layout") or ""
    needs_image = layout in IMAGE_LAYOUTS

    # 실물을 특정할 수 있는 강한 신호 — 이게 없으면 검색어를 만들 수 없다
    strong = {"인물", "브랜드", "제품명", "기업"} & set(hits)

    # 강한 신호 + 뒷받침 신호가 있어야 조사할 값어치가 있다.
    # "1970년대 어느 공장"으로는 특정 사진을 찾지 못한다.
    worth = bool(strong) and len(hits) >= 2
    # 이미지가 필요한 레이아웃이면 신호 하나로도 찾아본다
    if strong and needs_image:
        worth = True
    # 은유·심리 장면은 사료가 없다
    if skips and len(hits) < 3:
        worth = False
    reason = ("+".join(hits) or "신호없음") + (f" / 제외:{'+'.join(skips)}" if skips else "")
    return worth, hits, reason


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    picked = []
    for s in scenes:
        worth, hits, reason = classify(s)
        if not worth:
            if args.verbose:
                print(f"    - {s.get('sceneNumber'):>3} 제외  {reason}")
            continue
        picked.append({
            "n": s.get("sceneNumber"),
            "layout": s.get("layout"),
            "currentSource": (s.get("imageAsset") or {}).get("source"),
            "signals": hits,
            "narration": (s.get("narration") or "")[:200],
            "headline": s.get("headline"),
            "hint": (s.get("imageAsset") or {}).get("query")
                    or (s.get("imageAsset") or {}).get("prompt", "")[:120],
        })

    args.out.write_text(json.dumps({"scenes": picked}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    gen = sum(1 for p in picked if p["currentSource"] == "generate")
    print(f"  {args.project.name}: 전체 {len(scenes)}씬 → 조사 대상 {len(picked)}씬 "
          f"(그중 지금 generate로 잡힌 것 {gen}씬)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
