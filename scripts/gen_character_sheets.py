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
import shutil
import subprocess
import sys
from pathlib import Path


def _quality(path: Path) -> tuple[float, float]:
    """결과물의 결과 경계 흐림을 잰다. 기준 시트는 결 16.1 / 경계 14.6."""
    sys.path.insert(0, str(Path(__file__).parent))
    from detect_hatch import grain_score, edge_score
    return grain_score(path), edge_score(path)

SHEET = """$imagegen

첨부한 1번 이미지는 세모지 기준 캐릭터 시트입니다.

이 캐릭터를 수정하여 {who} 캐릭터 시트를 그려줘.
기준 캐릭터 시트 인물의 헤어스타일과 의상은 변경해서 사용할 것.
그림체는 1번 이미지 그대로 — 눈, 눈썹, 머리카락, 피부를 그린 방식을 그대로 옮길 것.
눈은 심플한 검은 눈동자만 그리기.

{outfit_line}
레이아웃은 기준 시트와 같습니다 — 윗줄에 전신 정면·측면·후면과 얼굴 클로즈업,
아랫줄에 표정 5종.

size는 1536x1024입니다.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


REF_BLOCK = """
실제 인물 사진: {ref}

이 사진에서 가져올 것은 **얼굴 생김새뿐**입니다 — 얼굴형, 이마 넓이, 눈매의
각도와 크기, 눈썹, 코의 폭, 입 모양, 턱선, 헤어라인, 안경과 수염의 유무.
그리는 방식은 기준 시트를 따릅니다.
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
    ap.add_argument("--tries", type=int, default=3, help="기준 미달 시 재시도 횟수")
    ap.add_argument("--max-grain", type=float, default=22.0, help="결 상한 (기준 시트 16.1)")
    ap.add_argument("--max-edge", type=float, default=19.0, help="경계 흐림 상한 (기준 시트 14.6)")
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

        ref = (args.roster.parent / e["ref"]).resolve() if e.get("ref") else None
        if ref and ref.exists():
            who = f"첨부한 2번 이미지의 인물({e['name']}, {e.get('era','')} {e.get('age','')})로"
            base_line = f"1번: {base}\n2번: {ref}"
        else:
            who = f"{e.get('era','')}의 {e['name']}({e.get('age','')}) — {look}, {hair} — 로"
            base_line = f"1번: {base}"
        prompt = SHEET.format(who=who, outfit_line=f"의상: {e['outfit']}\n", out=out)
        prompt = prompt.replace("첨부한 1번 이미지는 세모지 기준 캐릭터 시트입니다.",
                                f"첨부 이미지\n{base_line}\n\n1번은 세모지 기준 캐릭터 시트입니다.")
        # 빗금·번짐은 프롬프트로 못 막는다. 뽑아 보고 기준을 넘으면 다시 뽑는다.
        best = None
        for attempt in range(1, args.tries + 1):
            if out.exists():
                out.replace(out.with_suffix(f".try{attempt - 1}.png"))
            subprocess.run(
                ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900,
            )
            if not out.exists():
                continue
            g, ed = _quality(out)
            if best is None or (g + ed) < (best[1] + best[2]):
                shutil.copy2(out, out.with_suffix(".best.png"))
                best = (attempt, g, ed)
            print(f"      시도 {attempt}: 결 {g:.1f} 경계 {ed:.1f}"
                  + ("  ✓ 통과" if g <= args.max_grain and ed <= args.max_edge else ""))
            if g <= args.max_grain and ed <= args.max_edge:
                break
        if best and out.with_suffix(".best.png").exists():
            shutil.move(out.with_suffix(".best.png"), out)
        got = out.exists()
        ok += got
        tail = f" (최선 시도 {best[0]}: 결 {best[1]:.1f} 경계 {best[2]:.1f})" if best else ""
        print(f"  {'✓' if got else '✗'} {e['id']:18s} {e['name']} {e.get('age','')}{tail}")

    print(f"\n완료 {ok}/{len(roster)}")
    return 0 if ok == len(roster) else 1


if __name__ == "__main__":
    sys.exit(main())
