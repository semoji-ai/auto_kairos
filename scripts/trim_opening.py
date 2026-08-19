#!/usr/bin/env python3
"""오프닝의 사족을 걷어낸다.

편마다 도입부 끝에 「오늘은 ~ 이야기입니다」류의 예고가 한두 씬씩 붙어 있었다.
훅으로 붙잡아 놓고 다시 설명으로 늘어지면 그 사이에 시청자가 빠진다.
사건에서 곧장 본론으로 넘어가는 편이 낫다.

1편만 다르다. 시리즈의 첫 편이라 「열두 편짜리 대장정」을 선언하는 자리가
필요하다 — 다만 한 마디로 끝내고 타이틀로 넘어간다.

**씬을 지우되 파일은 그대로 둔다.** 나중에 되돌릴 수 있고, 이미지·음성은
지우지 않는 것이 이 프로젝트의 원칙이다. 번호도 다시 매기지 않는다 —
image_assets.json이 씬 번호로 묶여 있어 새로 매기면 그림이 어긋난다.

    python3 scripts/trim_opening.py            # 무엇을 뺄지 보여만 준다
    python3 scripts/trim_opening.py --apply
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# 편 번호 → 뺄 씬 번호
CUTS = {
    1: [9, 10],    # 9는 타이틀(4로 옮긴다) · 10은 「95년은 …오늘은 그 첫 번째 이야기」
    4: [5],        # 「오늘은 그 숙제를 25년 동안 푼 사람의 이야기입니다」
    5: [4],        # 「오늘은 한국에서 가장 유명한 얼굴 하나가 태어난 이야기입니다」
    7: [5],        # 「오늘은 LG가 휴대폰으로 세계 3위까지 올라갔던 시절 이야기입니다」
    8: [6],        # 「오늘은 LG가 26년 만에 휴대폰을 손에서 놓기까지의 이야기입니다」
}

# 1편 씬4 — 다리 문장을 시리즈 선언 + 타이틀로 바꾼다
EP1_SCENE4 = {
    "narration": "이번에 브랜드백과사전 장편 시리즈, LG 편을 준비했습니다. "
                 "열두 편에 걸쳐 자세히 파헤쳐 볼 테니 기대해 주세요.",
    "title": "시리즈 예고 + 타이틀",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    live = {int(re.match(r"EP(\d+)", k).group(1)): v["dir"] for k, v in emap.items()}
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for ep in sorted(CUTS):
        d = Path(live[ep])
        f = d / "scene_specs.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        by_n = {s.get("sceneNumber"): s for s in scenes}

        print(f"══ {ep}편")
        for n in CUTS[ep]:
            s = by_n.get(n)
            if not s:
                print(f"   씬{n} 없음 — 건너뜁니다")
                continue
            t = (s.get("narration") or "").replace("\n", " ").strip()
            print(f"   뺌  씬{n}  {t[:64] or '(타이틀)'}")

        if ep == 1:
            s4, s9 = by_n.get(4), by_n.get(9)
            if s4 and s9:
                print(f"   바꿈 씬4  → {EP1_SCENE4['narration'][:52]}…")
                print(f"           헤드라인은 옛 타이틀 씬에서 가져옵니다")
                if args.apply:
                    s4["narration"] = EP1_SCENE4["narration"]
                    s4["title"] = EP1_SCENE4["title"]
                    s4["headline"] = s9.get("headline", "")
                    s4["layout"] = "headline_only"
                    # 이 씬은 말이 바뀌었으니 음성을 다시 만들어야 한다
                    s4["narration_dirty"] = True

        if args.apply:
            shutil.copy2(f, f.with_suffix(f".json.bak_trim_{stamp}"))
            data["scenes"] = [s for s in scenes if s.get("sceneNumber") not in CUTS[ep]]
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"   저장 — {len(scenes)}씬 → {len(data['scenes'])}씬")

    if not args.apply:
        print("\n--apply 를 붙이면 실제로 고칩니다. 파일(이미지·음성)은 지우지 않습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
