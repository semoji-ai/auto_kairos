#!/usr/bin/env python3
"""기준 캐릭터 이미지를 편집해 인물 시트를 만든다.

**그림체를 말로 묘사하지 않는다.** 텍스트로 "외곽선 없음, 4등신, 면 그림자"를
아무리 정확히 써도 등신과 대비가 어긋난다(실제로 두 번 실패). 기준 이미지를
**편집**하라고 지시하면 비율·크기·배경·화풍이 구조적으로 보존된다.

바꾸는 것은 얼굴·머리·옷 세 가지뿐이다.

    python3 scripts/gen_character_sheets.py <roster.json> --base <base.jpg> -o <out_dir>
    python3 scripts/gen_character_sheets.py <roster.json> --base <base.jpg> -o <out_dir> --only koo_inhoe_20s
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROMPT = """$imagegen

첨부한 이미지를 **편집**하세요. 새로 그리지 말고, 이 이미지를 고치는 겁니다.

원본: {base}

이 캐릭터를 **{era}의 {name}({age})**로 바꿔 주세요.

바꿀 것은 세 가지뿐입니다.
- 얼굴: {look}
- 머리: {hair}
- 옷: {outfit}

**나머지는 원본 그대로 두세요.** 몸의 비율과 크기, 서 있는 자세, 팔다리 길이,
화면 안에서의 위치와 크기, 캔버스 비율, 배경색, 그림체를 전혀 건드리지 마세요.
원본 위에 옷과 얼굴만 갈아입힌 결과여야 합니다.

눈은 원본과 똑같이 그리세요. 작고 **완전한 원형**의 검은 점입니다.
찌그러지거나 눌린 타원이 되지 않게, 좌우 모두 또렷한 동그라미로 유지하세요.

얼굴 각도도 원본 그대로 두세요. 원본은 얼굴이 아주 살짝 비스듬합니다.
그 각도라야 코가 옆선으로 또렷하게 읽힙니다. 얼굴을 정면으로 돌리면
코가 애매해지니, 원본의 기울기를 그대로 유지하세요.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


def run(entry: dict, base: Path, out_dir: Path) -> bool:
    out = out_dir / f"{entry['id']}.png"
    look = entry["look"]
    # look 안에 머리 서술이 섞여 있으면 분리, 없으면 통째로
    hair = entry.get("hair") or ""
    if not hair:
        parts = [p.strip() for p in look.split(",")]
        hair = next((p for p in parts if "머리" in p), "원본과 같은 머리")
        look = ", ".join(p for p in parts if p != hair)

    prompt = PROMPT.format(
        base=base, era=entry.get("era", ""), name=entry["name"],
        age=entry.get("age", ""), look=look, hair=hair,
        outfit=entry["outfit"], out=out,
    )
    proc = subprocess.run(
        ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900,
    )
    ok = out.exists()
    print(f"  {'✓' if ok else '✗'} {entry['id']:18s} {entry['name']} {entry.get('age','')}")
    if not ok:
        print(f"      {proc.stderr[-160:] or proc.stdout[-160:]}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roster", type=Path)
    ap.add_argument("--base", required=True, type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--only", help="특정 id만")
    args = ap.parse_args()

    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    if args.only:
        roster = [r for r in roster if r["id"] == args.only]
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"인물 시트 {len(roster)}종 생성 — 기준 {args.base.name} 편집")
    ok = sum(run(r, args.base.resolve(), args.out.resolve()) for r in roster)
    print(f"\n완료 {ok}/{len(roster)}")
    return 0 if ok == len(roster) else 1


if __name__ == "__main__":
    sys.exit(main())
