#!/usr/bin/env python3
"""연출 채점에서 반복으로 깎이는 두 항목을 코드로 채운다 — 배지와 숫자 시각화.

**왜 코드인가.** 둘 다 규칙이 명확해 사람이나 에이전트가 매번 판단할 일이 아니다.
그런데 scene_specs를 재생성하면 통째로 날아간다. EP01은 배지 44개가 있었지만
EP02·EP07은 0개였고, 그 탓에 '오도 방지' 7점을 전부 잃었다.

1. 배지 (오도 방지 7점)
   생성 이미지는 촬영물이 아니므로 무엇에 근거했는지 화면에 밝힌다.
     일러스트 재현    — 사료로 확인되는 사실의 재현
     기업 사사 기록   — 회사가 펴낸 기록에만 있는 내용
     독립 근거 미확인 — 널리 알려졌으나 독립 자료가 없는 일화

2. 숫자 시각화 (지식 전달 15점)
   나레이션에 숫자가 나오면 화면에도 띄운다. metric 계열 레이아웃인데
   values가 비어 있으면 나레이션에서 뽑아 채운다.
   단위가 섞이면 unit을 비우고 라벨에 넣는다(direction-standard 5절).

    python3 scripts/apply_direction_fixes.py <project_dir> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 회사 기록에만 남은 내용을 가리키는 말
CORPORATE = re.compile(r"(사사|사보|회사 기록|기업 기록|공식 연혁|자서전|평전|전기에)")
# 독립 근거가 없다고 본문이 스스로 밝히는 경우
UNVERIFIED = re.compile(r"(전해집니다|전해진다|알려져 있습니다|확인되지 않|기록은 없|"
                        r"일화|말이 있습니다|한다고 합니다|고 합니다)")

METRIC_LAYOUTS = {"counter", "metric_spotlight", "metric_wall", "bar", "bar_horizontal",
                  "pie", "donut", "line", "icon_stat", "annotated_chart"}

# 숫자 + 단위. 연도는 timeline이 items로 다루므로 여기서 뺀다.
NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(억원|만원|조원|억|만|원|달러|퍼센트|%|배|위|"
                 r"명|개|대|가마|필|년|개월|일|시간|분|초|mm|cm|kg|톤|건|종|곳|위안|엔)")


def pick_badge(scene: dict) -> str | None:
    ia = scene.get("imageAsset") or {}
    if ia.get("source") != "generate":
        return None
    text = " ".join(str(scene.get(f) or "") for f in ("narration", "headline"))
    if UNVERIFIED.search(text):
        return "독립 근거 미확인"
    if CORPORATE.search(text):
        return "기업 사사 기록"
    return "일러스트 재현"


def fill_values(scene: dict) -> bool:
    """metric 계열인데 values가 비었으면 나레이션에서 채운다."""
    if scene.get("layout") not in METRIC_LAYOUTS or scene.get("values"):
        return False
    found = NUM.findall(scene.get("narration") or "")
    if not found:
        return False
    vals, labels, units = [], [], set()
    for raw, unit in found[:4]:
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        vals.append(int(v) if v == int(v) else v)
        labels.append(unit)
        units.add(unit)
    if not vals:
        return False
    scene["values"] = vals
    # 단위가 하나면 unit으로, 섞이면 라벨에 넣는다 (unit은 씬당 하나뿐이다)
    if len(units) == 1:
        scene["unit"] = labels[0]
        if not scene.get("items"):
            scene["items"] = [f"{l}" for l in labels]
    else:
        scene["unit"] = ""
        scene["items"] = [f"({u})" for u in labels]
    return True


# infoStructure → layout 대응표 (direction-standard 3절)
# 표준 하나만 두면 연출 폭이 죽는다. 뜻이 통하는 대안은 허용하고, 그 밖만 고친다.
MAP = {
    "metric": "metric_spotlight", "metric_group": "metric_wall",
    "chronology": "timeline", "enumeration": "items_list",
    "contrast": "split", "correction": "before_after", "causal": "flow",
    "scene": "cinematic", "quote": "quote_portrait", "statement": "headline_only",
}
ALLOWED = {
    "scene": {"cinematic", "split", "images_grid"},
    "enumeration": {"items_list", "items_grid", "rank_list", "card_carousel"},
    "contrast": {"split", "before_after", "comparison_table"},
    "correction": {"before_after", "split"},
    "chronology": {"timeline", "flow"},
    "metric": {"counter", "metric_spotlight", "icon_stat", "bar"},
    "metric_group": {"metric_wall", "bar", "bar_horizontal", "comparison_table",
                     "pie", "donut", "stacked_progress"},
    "causal": {"flow", "before_after", "split"},
    "quote": {"quote_portrait"},
    "statement": {"headline_only", "quote_portrait"},
}
# 이 레이아웃들은 화면에 수치나 항목을 띄울 수 있다
CAN_SHOW = METRIC_LAYOUTS | {"timeline", "items_list", "items_grid", "split",
                             "before_after", "flow", "metric_wall", "comparison_table"}


def align_layout(scene: dict) -> str | None:
    """정보 구조에 맞지 않는 레이아웃을 바로잡는다.

    가장 나쁜 경우는 statement→cinematic이다. cinematic은 이미지 전체화면이라
    텍스트가 없어서, 그 편이 하려는 말이 화면에 아예 뜨지 않는다(18건).
    causal→headline_only도 마찬가지로 인과의 단계가 사라진다.

    허용 대안은 건드리지 않는다. contrast를 before_after로 잡는 건 정상이다.
    """
    info = scene.get("infoStructure")
    want = MAP.get(info)
    if not want:
        return None
    cur = scene.get("layout")
    if cur in ALLOWED.get(info, {want}):
        return None
    scene["layout"] = want
    return f"{cur}→{want}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    spec = args.project / "scene_specs.json"
    data = json.loads(spec.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    badged, valued, aligned = 0, 0, []
    for s in scenes:
        if not s.get("badge"):
            b = pick_badge(s)
            if b:
                s["badge"] = b
                badged += 1
        ch = align_layout(s)
        if ch:
            aligned.append(f"{s.get('sceneNumber')} {ch}")
        if fill_values(s):
            valued += 1

    if not args.dry_run:
        spec.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    gen = sum(1 for s in scenes if (s.get("imageAsset") or {}).get("source") == "generate")
    have = sum(1 for s in scenes if s.get("badge"))
    print(f"  {args.project.name}: 배지 +{badged} (생성 {gen}씬 중 {have}씬 보유) / "
          f"수치 보강 +{valued} / 레이아웃 정렬 {len(aligned)}"
          + (" [dry-run]" if args.dry_run else ""))
    for a in aligned:
        print(f"      씬 {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
