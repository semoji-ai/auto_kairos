#!/usr/bin/env python3
"""세모지 문체 검증 게이트 — 코퍼스 실측 밴드로 채점한다.

`check_manuscript.py`가 **편집 사고**(중복 문단·챕터 번호·마커)를 잡는다면
이쪽은 **문체**를 본다. 둘은 다른 층이라 함께 돌려야 한다.

adobe(auto_kairos_adobe/backend/verify_voice.py)에서 이식했다. 원고는 v3에서
만드는데 검증이 하류에만 있었다 — 순서가 거꾸로였다.

기준은 감이 아니라 세모지 47편을 분석한 분포다
(`auto_agent/data/artstyle/semoji-voice-bands.json`).

**하한선이 있다는 것이 핵심이다.** AI가 쓴 글은 문장 길이가 고르게 나오고
사람 글은 들쭉날쭉하다. 「잘 쓴 것처럼 보이지만 사람 같지 않은」 원고 —
너무 매끈한 원고도 떨어뜨린다.

위반 문구는 그대로 재작성 지시문으로 쓸 수 있게 **다음 행동**으로 적는다.

    python3 scripts/verify_voice.py <원고.md> [원고2.md ...]
    python3 scripts/verify_voice.py --dir output/.../manuscripts_13ep
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

BANDS_FILE = (Path(__file__).resolve().parent.parent
              / "auto_agent" / "data" / "artstyle" / "semoji-voice-bands.json")

POLITE = re.compile(r"(습니다|입니다|합니다|됩니다|집니다|겁니다)[.?!…\"”』)]*\s*$")
COLLOQ = re.compile(r"(거죠|이죠|었죠|았죠|잖아요|거든요|는데요|인데요|네요|까요)[.?!…\"”』)]*\s*$")
PLAIN = re.compile(r"(했다|됐다|되었다|였다|이다)[.]?\s*$")
HANGUL_NUM = re.compile(
    r"(일|이|삼|사|오|육|칠|팔|구|십|백|천)(천|백|십)?(구백|팔십)?[일이삼사오육칠팔구십백천]*년"
    r"|[일이삼사오육칠팔구]십[일이삼사오육칠팔구]?\s*(골|년|살|개)")
META = re.compile(r"^\s*([\[(#]|<출처>|>)")

# 실측 낭독 속도 — ElevenLabs semoji 보이스로 412자/분. 여유를 둬 밴드로 쓴다.
CHARS_PER_MIN = (350, 412)
LEN_TOLERANCE = 0.3          # 목표 대비 ±30% 이탈이면 탈락 (adobe 게이트와 같은 기준)


def bands() -> dict:
    try:
        return json.loads(BANDS_FILE.read_text(encoding="utf-8")).get("bands", {})
    except Exception:
        return {}


def narration_lines(text: str) -> list[str]:
    """나레이션 줄만 남긴다 — 메타라인·헤딩·인용부호는 문체 표본이 아니다."""
    return [l.strip() for l in text.splitlines()
            if l.strip() and not META.match(l.strip())]


def check(text: str, target_min: float | None = None) -> dict:
    b = bands()
    lines = narration_lines(text)
    enders = [l for l in lines if re.search(r"[.?!…\"”]\s*$", l)
              or POLITE.search(l) or COLLOQ.search(l) or PLAIN.search(l)]
    ne = max(1, len(enders))
    polite = sum(1 for l in enders if POLITE.search(l)) / ne
    colloq = sum(1 for l in enders if COLLOQ.search(l)) / ne
    plain = sum(1 for l in enders if PLAIN.search(l)) / ne
    lens = [len(l) for l in lines]
    len_std = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    joined = "\n".join(lines)

    plain_hi = b.get("plain_of_enders", {}).get("p90", 0.023)
    polite_lo = b.get("polite_of_enders", {}).get("p10", 0.447)
    std_lo = b.get("line_len_std", {}).get("p10", 6.927)

    v: list[str] = []
    if plain > max(plain_hi, 0.05):
        bad = [l for l in enders if PLAIN.search(l)][:3]
        v.append(f"평서체 종결(~했다/됐다/이다)이 {plain:.0%} — 세모지는 존댓말이 기본입니다. "
                 f"전부 '~습니다/~죠'로 바꾸세요. 예: {bad}")
    if polite + colloq < max(polite_lo + 0.05, 0.5):
        v.append(f"존댓말+구어체 종결이 {polite+colloq:.0%}뿐 — 실측 밴드(합계 61~93%)에 못 미칩니다. "
                 f"'~습니다'를 기본으로 두고 공감 지점에 '~거죠/~거든요'를 섞으세요.")
    if len(lines) >= 10 and len_std < std_lo * 0.6:
        v.append(f"줄 길이 표준편차 {len_std:.1f} — 실측 하한({std_lo:.1f})보다 균일합니다. "
                 f"짧은 문장 연타와 긴 호흡을 섞어 리듬을 만드세요(너무 매끈한 원고 금지).")
    if HANGUL_NUM.search(text):
        v.append("숫자를 한글로 풀어썼습니다 — 세모지는 아라비아 숫자로 적습니다(예: 2022년, 672골). "
                 "발음용 변환은 TTS 전처리기가 따로 합니다.")
    colloq_all = len(re.findall(r"(거죠|이죠|잖아요|거든요|는데요|인데요|네요|까요)", joined))
    report_all = len(re.findall(r"다고 (합니다|해요|했습니다|하는데요|전해집니다)", joined))
    if len(lines) >= 10 and colloq_all + report_all == 0:
        v.append("구어체(~거죠/잖아요/거든요)와 전달체(~다고 합니다)가 전무합니다 — "
                 "코퍼스 47편 모두 최소 1회 이상 씁니다. 공감 지점에 구어체를, "
                 "간접 사실에 전달체를 섞으세요.")

    m = {"polite": round(polite, 3), "colloq": round(colloq, 3),
         "plain": round(plain, 3), "line_len_std": round(len_std, 2),
         "enders": ne, "lines": len(lines)}

    # 분량 — 목표가 주어졌을 때만 본다. 길이는 문체와 무관해 보이지만,
    # 길면 늘어지고 짧으면 설명이 빠져 결국 전달이 무너진다.
    if target_min:
        chars = len(re.findall(r"[가-힣]", joined))
        lo = int(target_min * CHARS_PER_MIN[0] * (1 - LEN_TOLERANCE))
        hi = int(target_min * CHARS_PER_MIN[1] * (1 + LEN_TOLERANCE))
        m["nar_chars"] = chars
        m["target_range"] = [lo, hi]
        if chars < lo or chars > hi:
            v.append(f"분량 이탈 — 나레이션 한글 {chars:,}자, 목표 {lo:,}~{hi:,}자"
                     f"({target_min:g}분 기준). "
                     f"{'문장을 쳐내 압축하세요' if chars > hi else '내용을 보강하세요'}.")

    return {"ok": not v, "violations": v, "metrics": m}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--dir", type=Path, help="폴더 내 *.md 전체 검사")
    ap.add_argument("--minutes", type=float, help="목표 분량(분) — 주면 분량 이탈도 탈락 사유")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    paths = list(a.files)
    if a.dir:
        paths += sorted(p for p in a.dir.glob("*.md"))
    if not paths:
        print("검사할 원고가 없습니다")
        return 1

    out, bad = [], 0
    for p in paths:
        r = check(p.read_text(encoding="utf-8"), target_min=a.minutes)
        r["file"] = p.name
        out.append(r)
        m = r["metrics"]
        head = (f"{p.name}  존댓말 {m['polite']:.0%} / 구어체 {m['colloq']:.0%} / "
                f"평서체 {m['plain']:.0%} / 리듬 {m['line_len_std']:.1f}")
        if r["ok"]:
            print(f"✓ {head}")
        else:
            bad += 1
            print(f"✗ {head}")
            for x in r["violations"]:
                print(f"    · {x}")
    if a.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n{len(paths)}편 중 {bad}편 미달")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
