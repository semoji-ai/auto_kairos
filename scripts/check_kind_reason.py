#!/usr/bin/env python3
"""**실물 자료로 정했으면 근거가 있어야 한다.** 없으면 재현으로 되돌린다.

LG 1편에서 판정문과 종류가 정반대로 저장돼 있었다.

  씬1023  이유 「archive 부재, 긴장감 있는 재현 필요」  → 종류 search_image
  씬1030  이유 「archive 부재, 무역항 분위기 재현」     → 종류 search_image
  씬60    이유 「archive 사진 부재, 시대 재현 필요」     → 종류 search_image

「자료가 없으니 그려라」고 판단해 놓고 「실물 자료」로 찍혀 나갔다. 다음
단계는 그 말을 곧이곧대로 읽고 자료를 찾으러 갔고, 맞는 자료가 없으니
**시대만 맞는 아무 사진**을 붙였다.

  「그의 이름은 안희제」      → 일본어 간판이 걸린 거리 사진
  「살림집에서 문을 엽니다」   → 대형 공장 단지 전경

이유문만 보고 잡으면 오탐이 난다. 씬25·52·1039 는 이유에 「부재」라고
적혀 있지만 그 뒤 좋은 자료를 실제로 찾았다(침수한 구인회포목상점 사진,
허만정 초상, 럭키크림 실물). **이유문은 낡는다.**

그래서 **관련성 칸**으로 가른다. 자료를 붙일 때 「이 자료가 이 말과 어떻게
이어지는가」를 적게 되어 있고, 그 칸이 비었다는 것은 이어진다는 근거가
없다는 뜻이다.

    python3 scripts/check_kind_reason.py EP01
    python3 scripts/check_kind_reason.py EP01 --apply
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    assets = {e["sceneNumber"]: e for e in json.loads(
        (proj / "images" / "image_assets.json").read_text(encoding="utf-8"))["scenes"]}

    bad = []
    for s in data["scenes"]:
        n = s.get("sceneNumber")
        if s.get("visual_kind") != "search_image":
            continue
        sel = [i for i in (assets.get(n) or {}).get("images") or [] if i.get("selected")]
        rel = (sel[0].get("relevance") if sel else "") or ""
        if rel.strip():
            continue
        bad.append((n, (s.get("narration") or "").strip()[:44],
                    (sel[0].get("desc") if sel else "") or "(붙은 자료 없음)"))

    print(f"{ep}  실물 자료로 정한 씬 중 **관련성이 빈** 씬 {len(bad)}개\n")
    for n, nar, desc in bad:
        print(f"  씬{n:>5}  {nar}")
        print(f"         자료: {desc[:70]}")

    if not bad:
        print("  근거 없는 자료는 없습니다.")
        return 0
    if not args.apply:
        print("\n--apply 를 붙이면 재현(generate_image)으로 되돌립니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_kindreason_{datetime.now():%Y%m%d_%H%M%S}"))
    ns = {n for n, _, _ in bad}
    for s in data["scenes"]:
        if s.get("sceneNumber") not in ns:
            continue
        s["visual_kind"] = "generate_image"
        s["visual_kind_reason"] = ("실물 자료로 정했으나 이 말과 이어진다는 근거(관련성)가 "
                                   "없어 시대만 맞는 사진이 붙어 있었다. 재현으로 되돌린다.")
        if not isinstance(s.get("imageAsset"), dict):
            s["imageAsset"] = {}
        s["imageAsset"]["source"] = "generate"
        s["needs_image"] = True
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(ns)}개 씬을 재현으로 되돌렸습니다: {sorted(ns)}")
    print("  다음: replan_direction.py → build_image_prompts.py → gen_scenes.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
