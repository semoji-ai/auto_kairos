#!/usr/bin/env python3
"""세모지 기준 캐릭터 시트를 편집해 인물 시트를 만든다.

**그림체를 말로 묘사하지 않는다.** 텍스트로 "외곽선 없음, 4등신, 면 그림자"를
아무리 정확히 써도 등신과 대비가 어긋난다(실제로 세 번 실패). 기준 시트를
**편집**하라고 지시하면 비율·레이아웃·화풍이 구조적으로 보존된다.

기준: artstyle/styles/semoji_character_sheet.png (세모지 공식 캐릭터 시트)

실존 인물은 **실제 초상을 함께 첨부**한다(roster의 `ref`). 기준 시트가 화풍과
레이아웃을, 초상이 얼굴 특징을 담당한다. 초상이 없는 인물은 유추이며 roster에
`inferred: true`로 남고 화면에서 `일러스트 재현` 배지를 단다.

    윗줄:   전신 정면 · 전신 측면 · 전신 후면 · 얼굴 클로즈업
    아랫줄: 표정 5종 (기본 미소 · 놀람 · 낙담 · 걱정 · 활짝 웃음)

이 구성이 필요한 이유
  - 후면: 뒷머리 모양이 정해지지 않으면 씬마다 다르게 나온다.
          땋은 머리·쪽 찐 머리처럼 긴 머리는 뒤가 정보량의 대부분이다.
  - 측면: 세모지는 외곽선 없이 면으로만 형태를 만들어, 정면만으로는
          콧대의 그림자 면이 사라져 코가 애매해진다.
  - 클로즈업: 씬 생성 시 얼굴 참조가 바로 된다.

    python3 scripts/gen_character_sheets.py <roster.json> -o <out>
    python3 scripts/gen_character_sheets.py <roster.json> -o <out> --only koo_inhoe_20s
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SHEET = """$imagegen

첨부한 세모지 기준 캐릭터 시트를 **편집**해 새 인물의 시트를 만드세요.
새로 그리지 말고 이 시트를 고치는 겁니다.

기준 시트: {base}
{ref_block}
이 캐릭터를 **{era}의 {name}({age})**로 바꾸세요.
**레이아웃과 컷 구성은 기준 시트와 완전히 똑같이 유지합니다.**

- 윗줄: 전신 정면 · 전신 측면 · 전신 후면 · 얼굴 클로즈업
- 아랫줄: 표정 5종 (기본 미소 · 놀람 · 낙담 · 걱정 · 활짝 웃음)

각 컷의 위치, 크기, 간격, 전신의 키와 비례를 기준 시트 그대로 두세요.

바꿀 것은 세 가지입니다.
- 얼굴: {look}
- 머리: {hair}
- 옷: {outfit}

**나머지는 기준 시트 그대로입니다.** 등신 비율, 팔다리 길이, 그림체, 외곽선 처리,
면 그림자 방식, 색면 대비, 배경색, 눈 모양, 코와 입선 처리를 전혀 건드리지 마세요.

후면 컷에서는 얼굴이 보이지 않으므로 **뒷머리의 형태와 옷의 뒷면 구조**로만
이 인물을 알아볼 수 있어야 합니다. 그 두 가지를 분명하게 그리세요.

표정 5종은 모두 같은 인물입니다. 얼굴 크기와 높이, 머리 모양, 옷깃이 같고
표정만 다릅니다.

글자는 넣지 않습니다. size는 1536x1024입니다.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


REF_BLOCK = """
실제 인물 사진: {ref}

이 사진은 **얼굴 특징의 근거**입니다. 그림체나 구도는 여기서 가져오지 마세요.
사진에서 가져올 것은 얼굴형, 이마 넓이, 눈매의 각도와 크기, 눈썹, 코의 폭,
입 모양, 턱선, 헤어라인, 안경과 수염의 유무뿐입니다.
{ref_note}
"""


def split_look(entry: dict) -> tuple[str, str]:
    look = entry["look"]
    hair = entry.get("hair") or ""
    if hair:
        return look, hair
    parts = [p.strip() for p in look.split(",")]
    hair = next((p for p in parts if "머리" in p), "원본과 같은 머리")
    return ", ".join(p for p in parts if p != hair), hair


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roster", type=Path)
    ap.add_argument("--base", type=Path,
                    default=Path("artstyle/styles/semoji_character_sheet.png"),
                    help="기준 캐릭터 시트 (기본: 세모지 공식 시트)")
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--only", help="특정 id만")
    args = ap.parse_args()

    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    if args.only:
        roster = [r for r in roster if r["id"] == args.only]
    args.out.mkdir(parents=True, exist_ok=True)
    base = args.base.resolve()

    ok = 0
    for e in roster:
        look, hair = split_look(e)
        out = (args.out / f"{e['id']}_sheet.png").resolve()

        ref_block = ""
        if e.get("ref"):
            ref = (args.roster.parent / e["ref"]).resolve()
            if ref.exists():
                ref_block = REF_BLOCK.format(ref=ref, ref_note=e.get("ref_note", ""))
            else:
                print(f"  ! {e['id']} 참조 사진 없음: {ref}")

        prompt = SHEET.format(base=base, ref_block=ref_block, era=e.get("era", ""),
                              name=e["name"], age=e.get("age", ""), look=look,
                              hair=hair, outfit=e["outfit"], out=out)
        subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900,
        )
        got = out.exists()
        ok += got
        print(f"  {'✓' if got else '✗'} {e['id']:18s} {e['name']} {e.get('age','')}")

    print(f"\n완료 {ok}/{len(roster)}")
    return 0 if ok == len(roster) else 1


if __name__ == "__main__":
    sys.exit(main())
