#!/usr/bin/env python3
"""인포그래픽 설계가 규칙을 지키는지 본다 — 그리기 전에.

`docs/rules/infographic-asset-rules.md`를 코드로 옮긴 것이다. EP01 시험에서
두 번 틀렸고 **둘 다 배치로는 복구되지 않았다.** 잘못 자른 에셋은 다시
그리는 수밖에 없으므로, 그리기 전에 거른다.

    python3 scripts/check_info_assets.py EP02
    python3 scripts/check_info_assets.py EP02 --strict   # 경고도 실패로 친다
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_info_assets import clean_subject  # noqa: E402  같은 세척을 거친 뒤에 본다

MAX_ASSETS = 4  # 다섯을 넘으면 배치가 성기고 시선이 흩어진다 (규칙 5)

# 프롬프트에 섞이면 해로운 말들 (규칙 4·7)
#
# 부정문 전부를 잡지는 않는다. 「끊김 없이 한 바퀴 도는」의 「끊김」은 그릴
# 수 있는 것이 아니라 그림에 찍히지 않는다. 문제가 되는 것은 **그려질 수
# 있는 대상**을 부정할 때다 — 그 단어를 오히려 렌더한다.
DRAWABLE = "문자|글자|텍스트|숫자|로고|상표|눈금|라벨|표기|사람|인물|배경"
BANNED = [
    (re.compile(rf"({DRAWABLE})[^,.]{{0,12}}(없는|없이|없음|제외|배제)"),
     "그릴 수 있는 대상을 부정했다 — 그 단어를 오히려 렌더한다. 긍정형으로 적는다"),
    (re.compile(r"세모지[^,]*화풍|3D\s*화풍"), "화풍을 이름으로 부르면 첨부 그림을 제쳐 두고 재해석한다"),
    (re.compile(r"\b(8k|4k|masterpiece|ultra[- ]detailed|sharp focus)\b", re.I), "SD 폐기 어휘"),
    (re.compile(r"--(ar|v)\b|:\d+\.\d+\)"), "가중치·미드저니 문법"),
]

# 설명을 들어야 아는 은유 (규칙 3) — EP01에서 실제로 실패한 것들
FOGGY = ["레일", "게이트", "인장", "관(", "파이프", "톱니", "저울추", "나침반"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    f = root / "_imggen" / f"{args.ep}_mode.json"
    if not f.exists():
        raise SystemExit(f"재분석 결과가 없습니다: {f}")
    data = json.loads(f.read_text(encoding="utf-8"))

    errors: list[str] = []
    warns: list[str] = []
    total = 0

    for s in data.get("scenes", []):
        if s.get("mode") != "infographic":
            continue
        n = s.get("n")
        assets = s.get("assets") or []
        total += len(assets)

        if not assets:
            errors.append(f"씬{n:>3}  인포그래픽인데 요소가 없다")
        if len(assets) > MAX_ASSETS:
            errors.append(f"씬{n:>3}  요소 {len(assets)}개 — {MAX_ASSETS}개를 넘는다. 씬을 나누거나 덩어리로 합친다")
        if not (s.get("composition") or {}).get("note"):
            warns.append(f"씬{n:>3}  배치 설명이 비어 있다")

        ids = [a.get("id") for a in assets]
        if len(ids) != len(set(ids)):
            errors.append(f"씬{n:>3}  요소 id가 겹친다: {ids}")

        for a in assets:
            # 재분석이 내는 문구에는 「투명 배경」·「문자 없음」·화풍 이름이 섞여
            # 온다. 셋 다 생성 직전에 gen_info_assets가 지우므로, 지운 뒤의
            # 문장으로 본다 — 안 그러면 이미 처리되는 것을 사고로 센다.
            p = clean_subject(a.get("prompt") or "")
            where = f"씬{n:>3} {a.get('id')}"
            if not p.strip():
                errors.append(f"{where}  프롬프트가 비어 있다")
                continue
            for rx, why in BANNED:
                if rx.search(p):
                    errors.append(f"{where}  {why}\n        → {p[:70]}")
                    break
            for word in FOGGY:
                if word in p:
                    warns.append(f"{where}  「{word}」 — 설명을 들어야 아는 은유일 수 있다")
                    break

    modes: dict[str, int] = {}
    for s in data.get("scenes", []):
        modes[s.get("mode", "?")] = modes.get(s.get("mode", "?"), 0) + 1

    print(f"{args.ep}  {sum(modes.values())}씬  {modes}")
    print(f"인포그래픽 요소 {total}개")
    if errors:
        print(f"\n■ 고쳐야 함 {len(errors)}건")
        for e in errors:
            print("  " + e)
    if warns:
        print(f"\n□ 살펴볼 것 {len(warns)}건")
        for w in warns:
            print("  " + w)
    if not errors and not warns:
        print("\n규칙 위반 없음")

    return 1 if errors or (args.strict and warns) else 0


if __name__ == "__main__":
    sys.exit(main())
