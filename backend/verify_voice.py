"""세모지 문체 검증 게이트 — 코퍼스 실측 밴드(semoji-voice-bands.json) 기반 규칙 채점.

나레이션 라인만 평가한다(메타라인 `[...]`, `(...)`, 헤딩 제외).
gn-voice verify_style 방법론: 하한선 포함 — '너무 매끈한'(균일 리듬) 원고도 탈락.
"""
from __future__ import annotations

import json
import re
import statistics
from pathlib import Path

BANDS_FILE = Path(__file__).resolve().parents[1] / "data" / "artstyle" / "semoji-voice-bands.json"


def bands() -> dict:
    """문턱을 코드가 아니라 밴드 파일에서 읽는다.

    전에는 0.05·0.5·4.0을 하드코딩했는데, 코퍼스를 갱신하면 파일과 코드가
    어긋난다. p90/p10을 읽으면 밴드를 다시 뽑는 것만으로 기준이 따라 움직인다.
    (v3 이식본에서 역이식)"""
    try:
        return json.loads(BANDS_FILE.read_text(encoding="utf-8")).get("bands", {})
    except Exception:
        return {}

POLITE = re.compile(r"(습니다|입니다|합니다|됩니다|집니다|겁니다)[.?!…\"”』)]*\s*$")
COLLOQ = re.compile(r"(거죠|이죠|었죠|았죠|잖아요|거든요|는데요|인데요|네요|까요)[.?!…\"”』)]*\s*$")
PLAIN = re.compile(r"(했다|됐다|되었다|였다|이다)[.]?\s*$")
HANGUL_NUM = re.compile(r"(일|이|삼|사|오|육|칠|팔|구|십|백|천)(천|백|십)?(구백|팔십)?[일이삼사오육칠팔구십백천]*년|[일이삼사오육칠팔구]십[일이삼사오육칠팔구]?\s*(골|년|살|개)")
META = re.compile(r"^\s*([\[(#]|<출처>|>)")


def narration_lines(text: str) -> list[str]:
    return [l.strip() for l in text.splitlines()
            if l.strip() and not META.match(l.strip())]


def check(text: str) -> dict:
    """{ok, violations[], metrics{}} — 위반 문구는 재작성 지시문에 그대로 쓸 수 있게 서술형."""
    b = bands()
    plain_hi = b.get("plain_of_enders", {}).get("p90", 0.023)
    polite_lo = b.get("polite_of_enders", {}).get("p10", 0.447)
    std_lo = b.get("line_len_std", {}).get("p10", 6.927)
    lines = narration_lines(text)
    enders = [l for l in lines if re.search(r"[.?!…\"”]\s*$", l)
              or POLITE.search(l) or COLLOQ.search(l) or PLAIN.search(l)]
    ne = max(1, len(enders))
    polite = sum(1 for l in enders if POLITE.search(l)) / ne
    colloq = sum(1 for l in enders if COLLOQ.search(l)) / ne
    plain = sum(1 for l in enders if PLAIN.search(l)) / ne
    lens = [len(l) for l in lines]
    len_std = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    hangul_years = HANGUL_NUM.findall(text)

    v = []
    if plain > max(plain_hi, 0.05):
        bad = [l for l in enders if PLAIN.search(l)][:3]
        v.append(f"평서체 종결(~했다/됐다/이다)이 {plain:.0%} — 세모지는 존댓말 기본, 전부 '~습니다/~죠'로 바꿀 것. 예: {bad}")
    if polite + colloq < max(polite_lo + 0.05, 0.5):
        v.append(f"존댓말+구어체 종결이 {polite+colloq:.0%}뿐 — 실측 밴드(합계 61~93%)에 못 미침. '~습니다' 기본, 공감 지점 '~거죠/~거든요' 혼용.")
    if len(lines) >= 10 and len_std < std_lo * 0.6:
        v.append(f"줄 길이 표준편차 {len_std:.1f} — 실측 하한({std_lo:.1f})보다 균일. 짧은 문장 연타와 긴 호흡을 섞어 리듬을 만들 것(너무 매끈한 원고 금지).")
    if hangul_years:
        v.append("숫자를 한글로 풀어씀 — 세모지는 아라비아 숫자 표기(예: 2022년, 672골).")
    colloq_all = len(re.findall(r"(거죠|이죠|잖아요|거든요|는데요|인데요|네요|까요)", "\n".join(lines)))
    report_all = len(re.findall(r"다고 (합니다|해요|했습니다|하는데요|전해집니다)", "\n".join(lines)))
    if len(lines) >= 10 and colloq_all + report_all == 0:
        v.append("구어체(~거죠/잖아요/거든요)와 전달체(~다고 합니다)가 전무 — 코퍼스 전 문서에 최소 1회 이상 존재. "
                 "공감 지점에 구어체를, 간접 사실에 전달체를 섞을 것.")
    return {"ok": not v, "violations": v,
            "metrics": {"polite": round(polite, 3), "colloq": round(colloq, 3),
                        "plain": round(plain, 3), "line_len_std": round(len_std, 2),
                        "enders": ne}}


def check_project(proj_dir: Path) -> dict:
    fp = proj_dir / "final_manuscript.md"
    if not fp.exists():
        return {"ok": False, "violations": ["final_manuscript.md 없음"], "metrics": {}}
    text = fp.read_text(encoding="utf-8")
    r = check(text)
    # 분량 검사 — plan.md 분량 목표 대비 ±30% 이탈 시 위반
    from backend import skills_cfg
    m = re.search(r"(\d+(?:\.\d+)?)", skills_cfg.parse_plan_fields(proj_dir).get("분량", ""))
    if m:
        lo = int(float(m.group(1)) * skills_cfg.CHARS_PER_MIN[0])
        hi = int(float(m.group(1)) * skills_cfg.CHARS_PER_MIN[1])
        nar = "\n".join(narration_lines(text))
        chars = len(re.findall(r"[가-힣]", nar))
        if chars < lo * 0.7 or chars > hi * 1.3:
            r["violations"].append(
                f"분량 이탈 — 나레이션 한글 {chars:,}자, 목표 {lo:,}~{hi:,}자. "
                f"{'문장을 쳐내 압축' if chars > hi else '내용을 보강'}할 것.")
            r["ok"] = False
        r["metrics"]["nar_chars"] = chars
    return r
