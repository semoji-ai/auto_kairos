#!/usr/bin/env python3
"""최종 원고의 **사실 주장**마다 출처가 붙어 있는지 대조한다.

광고주가 「내용의 출처를 확인해 달라」고 하면 필요한 것은 원장이 아니라
**원고 문장 옆에 붙은 출처**다. 원장은 우리가 조사한 순서로 쌓여 있고
원고는 이야기 순서로 쓰여 있어, 둘을 눈으로 맞추면 반드시 빠진다.

## 무엇을 「사실 주장」으로 보는가

말투가 아니라 **틀릴 수 있는가**로 가른다.

    ✅  숫자(연도·도수·용량·시간·가격·거리)
    ✅  고유명사(증류소·인명·지명·브랜드·법령)
    ✅  유일성·최초·최대 같은 단정
    ✅  인과 서술(「~때문에 ~하다」)
    ✗   질문·감탄·전환·요약 (「그런데 말이죠」)

## 어떻게 맞추는가

원장의 `claim` 과 원고 문장을 **토큰 겹침 + 숫자 일치**로 점수 내어 가장
높은 것을 후보로 붙인다. 숫자가 어긋나면 겹침이 높아도 **불일치**로 따로
뺀다 — 출처는 있는데 수치가 다른 것이 가장 위험하다.

    python3 scripts/check_manuscript_sources.py <project_dir> [-o out.md]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# ── 사실 주장 판정 ──────────────────────────────────────────────────────
NUM = re.compile(r"\d")
YEAR = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\s*년")
UNIT = re.compile(r"\d[\d,.]*\s*(%|도|년|시간|일|개|mL|ml|L|리터|원|만|천|배|km|미터|명|톤|ppm)")
PROPER = re.compile(
    r"클라이넬리쉬|싱글톤|탈리스커|라가불린|브로라|더프타운|스카이|아일라|스페이사이드|"
    r"조니\s*워커|디아지오|스카치|하이랜드|포트\s*엘런|말트밀|피트|셰리|버번|올로로소|PX|"
    r"스코틀랜드|잉글랜드|영국|파사바체|슈톨츠|레만|이마트|트레이더스")
ASSERT = re.compile(r"유일|최초|처음|가장|모든|전부|반드시|법으로|규정|규제|의무|금지|공식")
CAUSE = re.compile(r"때문|덕분|그래서|따라서|이유는|결과|영향")

STOP = re.compile(r"^(그런데|그래서요|자|근데|여기까지|다음|정리하면|보셨죠|보시죠)")


def is_claim(s: str) -> tuple[bool, str]:
    """사실 주장인가. (판정, 이유)"""
    t = s.strip()
    if len(t) < 6:
        return False, ""
    if t.endswith("?") and not (UNIT.search(t) or YEAR.search(t)):
        return False, "질문"
    why = []
    if YEAR.search(t):
        why.append("연도")
    if UNIT.search(t):
        why.append("수치")
    if PROPER.search(t):
        why.append("고유명사")
    if ASSERT.search(t):
        why.append("단정")
    if CAUSE.search(t) and (NUM.search(t) or PROPER.search(t)):
        why.append("인과")
    # 고유명사만으로는 약하다 — 이름만 부르는 전환 문장이 걸린다
    strong = {"연도", "수치", "단정", "인과"} & set(why)
    return (bool(strong or len(why) >= 2), "·".join(why))


# ── 대조 ────────────────────────────────────────────────────────────────
TOKEN = re.compile(r"[가-힣A-Za-z]{2,}|\d[\d,.]*")


def toks(s: str) -> set:
    return {t for t in TOKEN.findall(s) if len(t) >= 2}


KNUM = re.compile(r"(\d+)\s*만(?:\s*(\d+)\s*천)?(?:\s*(\d+)\s*백)?(?:\s*(\d+)\s*십)?")


def nums(s: str) -> set:
    """비교 가능한 수.

    **한글 수 표기를 풀어야 한다.** 원고는 「8만 7천8백 원」이라 읽기 좋게 쓰고
    원장은 「87,800」이라 적는다. 그대로 견주면 같은 값이 서로 다른 수로 잡혀
    「출처는 있는데 수치가 다르다」는 거짓 경보가 난다 — 실제로 그랬다.
    """
    out = {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", s)}
    for m in KNUM.finditer(s):
        man, chon, baek, sip = (int(g) if g else 0 for g in m.groups())
        v = man * 10000 + chon * 1000 + baek * 100 + sip * 10
        if v:
            out.add(str(v))
    return out


def key_nums(s: str) -> set:
    """**견줄 값어치가 있는 수만** 고른다 — 연도와 1,000 이상의 값.

    「1차 증류」의 1, 「두 개」의 2 같은 수까지 견주면 어느 문장도 통과하지
    못한다. 틀리면 사고가 나는 것은 연도와 금액이다.
    """
    out = set()
    for n in nums(s):
        try:
            v = float(n)
        except ValueError:
            continue
        if 1700 <= v <= 2100 or v >= 1000:
            out.add(n)
    return out


# 같은 문장 안에서만 견준다 — 브랜드가 다르면 애초에 남남이다
BRANDS = {
    "클라이넬리쉬": ("클라이넬리쉬", "브로라", "clynelish", "brora"),
    "싱글톤": ("싱글톤", "더프타운", "singleton", "dufftown"),
    "탈리스커": ("탈리스커", "스카이", "카보스트", "talisker", "skye"),
    "라가불린": ("라가불린", "아일라", "포트 엘런", "포트엘런", "말트밀", "lagavulin", "islay"),
}


def brands(s: str) -> set:
    low = s.lower()
    return {b for b, keys in BRANDS.items() if any(k.lower() in low for k in keys)}


def score(sent: str, claim: str) -> float:
    """토큰 겹침. **브랜드가 서로 어긋나면 0으로 떨군다.**

    이걸 안 걸면 「1896년 클라이넬리쉬…」 문장에 「1862년 라가불린…」 원장이
    붙는다. 연도 자리와 문장 뼈대가 닮아 점수가 오르기 때문이다.
    """
    bs, bc = brands(sent), brands(claim)
    if bs and bc and not (bs & bc):
        return 0.0
    a, b = toks(sent), toks(claim)
    if not a or not b:
        return 0.0
    base = len(a & b) / len(a | b) ** 0.5
    if bs & bc:
        base *= 1.35            # 같은 브랜드를 말하고 있으면 힘을 싣는다
    return base


def load_claims(proj: Path) -> list:
    out = []
    led = proj / "research/claims_ledger.jsonl"
    if led.is_file():
        for line in led.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            out.append({"text": d.get("claim", ""), "url": d.get("source_url", ""),
                        "src": d.get("source_id", ""), "tier": d.get("tier", ""),
                        "span": d.get("evidence_span", ""), "from": "claims_ledger"})
    tc = proj / "targeted_claims.json"
    if tc.is_file():
        for c in json.loads(tc.read_text(encoding="utf-8")).get("claims", []):
            srcs = c.get("sources") or []
            url = ""
            if srcs:
                s0 = srcs[0]
                url = s0.get("url", "") if isinstance(s0, dict) else str(s0)
            out.append({"text": (c.get("answer") or "")[:600], "url": url,
                        "src": c.get("question_id", ""), "tier": c.get("confidence", ""),
                        "span": (c.get("evidence") or "")[:300] if isinstance(c.get("evidence"), str) else "",
                        "from": "targeted_claims"})

    # chapter_facts — 원고를 쓸 때 실제로 앞에 놓였던 자료다. 원장에 안 올라간
    # 사실이 여기 있다. **「미검증」 표시를 함께 끌어온다** — 근거가 있는 것과
    # 「일반지식으로 적었다」고 스스로 밝힌 것은 전혀 다른 것이다.
    for fp in sorted((proj / "chapter_facts").glob("chapter_*.json")):
        try:
            d = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue
        ch = d.get("chapter", fp.stem)
        for kf in d.get("key_facts", []) or []:
            text = f"{kf.get('fact','')} {kf.get('detail','')}".strip()
            if not text:
                continue
            unver = ("미검증" in text) or not (kf.get("claim_ids") or kf.get("source_ids"))
            out.append({"text": text[:800], "url": "", "src": f"chapter_facts ch{ch}",
                        "tier": "미검증" if unver else "검증",
                        "span": "", "from": "chapter_facts", "unverified": unver})
        for ta in d.get("timeline_anchors", []) or []:
            text = ta if isinstance(ta, str) else json.dumps(ta, ensure_ascii=False)
            out.append({"text": text[:400], "url": "", "src": f"chapter_facts ch{ch} timeline",
                        "tier": "", "span": "", "from": "chapter_facts", "unverified": True})

    # 위키 — 조사 단계에서 모은 서술. 문단 단위로 쪼개 후보로 쓴다.
    for page in sorted((proj / "research/wiki").glob("*/*.md")):
        if page.name == "claims.md":
            continue
        body = page.read_text(encoding="utf-8")
        body = re.sub(r"^---.*?^---", "", body, flags=re.S | re.M)   # 앞머리 메타 제거
        for para in re.split(r"\n\s*\n", body):
            p = para.strip()
            if len(p) < 40 or p.startswith("#"):
                continue
            out.append({"text": p[:600], "url": "", "src": f"wiki/{page.parent.name}/{page.stem}",
                        "tier": "", "span": "", "from": "wiki", "unverified": True})

    for c in out:
        c.setdefault("unverified", False)
    return [c for c in out if c["text"]]


def split_manuscript(md: str) -> list:
    """(챕터, 문장) 목록. 주석과 구분선을 걷어낸다."""
    chapter = "도입"
    rows = []
    for block in md.split("---"):
        b = re.sub(r"<!--.*?-->", "", block, flags=re.S).strip()
        if not b:
            continue
        for line in b.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                chapter = line.lstrip("# ").strip()
                continue
            rows.append((chapter, line))
    return rows


def run(proj: Path, out_path: Path) -> dict:
    md = (proj / "final_manuscript.md").read_text(encoding="utf-8")
    rows = split_manuscript(md)
    claims = load_claims(proj)

    covered, weak, missing, mismatch = [], [], [], []
    for ch, sent in rows:
        ok, why = is_claim(sent)
        if not ok:
            continue
        best, bs = None, 0.0
        for c in claims:
            s = score(sent, c["text"])
            if s > bs:
                best, bs = c, s
        sn = key_nums(sent)
        cn = key_nums(best["text"]) if best else set()
        rec = {"chapter": ch, "sentence": sent, "why": why,
               "score": round(bs, 3), "claim": best["text"] if best else "",
               "url": best["url"] if best else "", "src": best["src"] if best else "",
               "tier": best["tier"] if best else "", "from": best["from"] if best else "",
               "span": (best["span"] if best else "")[:220],
               "unverified": bool(best.get("unverified")) if best else True}
        if sn:
            rec["sent_nums"], rec["claim_nums"] = sorted(sn), sorted(cn)

        # **연도·금액이 안 맞으면 그 문장은 출처가 없는 것이다.**
        # 닮은 원장이 붙었다고 출처가 된 것이 아니다 — 1896년 문장에 1862년
        # 원장을 붙여 놓고 「출처 있음」이라 하면 그게 더 위험하다.
        num_ok = (not sn) or bool(sn & cn)
        if bs >= 0.25 and num_ok:
            covered.append(rec)
        elif bs >= 0.45 and sn and not num_ok:
            mismatch.append(rec)      # 같은 얘기인데 수치가 어긋난다 — 사람이 봐야 한다
        elif bs >= 0.18 and num_ok:
            weak.append(rec)
        else:
            missing.append(rec)

    res = {"_order": [s for _, s in rows],
           "total_sentences": len(rows),
           "claim_sentences": len(covered) + len(weak) + len(missing) + len(mismatch),
           "covered": covered, "weak": weak, "mismatch": mismatch, "missing": missing,
           "claims_pool": len(claims)}
    out_path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("-o", "--out", default="")
    ap.add_argument("--md", default="", help="광고주용 대조표 마크다운 경로")
    a = ap.parse_args()
    proj = Path(a.project)
    out = Path(a.out) if a.out else proj / "source_check.json"
    r = run(proj, out)
    n = r["claim_sentences"]
    print(f"  문장 {r['total_sentences']}개 중 사실 주장 {n}개 · 원장 {r['claims_pool']}건")
    print(f"    출처 붙음   {len(r['covered']):>3}")
    print(f"    약한 대응   {len(r['weak']):>3}")
    print(f"    수치 불일치 {len(r['mismatch']):>3}")
    print(f"    출처 없음   {len(r['missing']):>3}")
    print(f"  → {out}")
    if a.md:
        md = Path(a.md)
        md.write_text(to_markdown(r, "최종 원고 출처 대조표 — 디아지오 싱글몰트 브랜드백과사전"),
                      encoding="utf-8")
        print(f"  → {md}")
    return 0



# ── 광고주에게 보낼 표 ──────────────────────────────────────────────────
LABEL = {"covered": "출처 확인", "weak": "출처 추정", "mismatch": "수치 불일치", "missing": "근거 미확인"}


def to_markdown(r: dict, title: str) -> str:
    """원고 순서 그대로 한 줄씩. **원고 순서가 아니면 광고주가 못 읽는다.**"""
    rows = []
    for bucket in ("covered", "weak", "mismatch", "missing"):
        for x in r[bucket]:
            rows.append((bucket, x))
    # 원고에 나온 순서로 되돌린다
    order = {s: i for i, s in enumerate(r.get("_order", []))}
    rows.sort(key=lambda kv: order.get(kv[1]["sentence"], 10**6))

    n = len(rows)
    out = [f"# {title}", "",
           f"최종 원고(`final_manuscript.md`) 314문장 가운데 **틀릴 수 있는 문장 {n}개**를 "
           "골라 근거 자료와 하나씩 대조했습니다.", "",
           "| 판정 | 건수 | 뜻 |", "|---|---:|---|",
           f"| 출처 확인 | {len(r['covered'])} | 근거 자료에 같은 내용이 있습니다 |",
           f"| 출처 추정 | {len(r['weak'])} | 비슷한 내용은 있으나 문장과 정확히 맞지 않습니다 |",
           f"| **수치 불일치** | {len(r['mismatch'])} | **원고의 수와 자료의 수가 다릅니다 — 확인 필요** |",
           f"| **근거 미확인** | {len(r['missing'])} | **자료에서 근거를 찾지 못했습니다 — 확인 필요** |",
           ""]

    for bucket, head in (("mismatch", "수치 불일치 — 먼저 확인 부탁드립니다"),
                         ("missing", "근거 미확인 — 출처 회신 또는 문장 수정이 필요합니다")):
        if not r[bucket]:
            continue
        out += [f"## {head}", ""]
        ch_now = None
        for x in r[bucket]:
            if x["chapter"] != ch_now:
                ch_now = x["chapter"]
                out += ["", f"### {ch_now}", ""]
            out.append(f"- {x['sentence']}")
            if bucket == "mismatch":
                out.append(f"  - 원고 `{', '.join(x.get('sent_nums', []))}` ↔ "
                           f"자료 `{', '.join(x.get('claim_nums', [])) or '해당 수치 없음'}`")
                out.append(f"  - 자료: {x['claim'][:150]}")
        out.append("")

    out += ["## 전체 대조표", "",
            "| # | 챕터 | 원고 문장 | 판정 | 근거 | 출처 |", "|---:|---|---|---|---|---|"]
    for i, (bucket, x) in enumerate(rows, 1):
        ch = x["chapter"].split(".")[0]
        sent = x["sentence"].replace("|", "/")[:70]
        claim = (x["claim"] or "").replace("|", "/")[:70]
        url = x["url"] or x["src"] or "—"
        mark = LABEL[bucket]
        if x.get("unverified") and bucket in ("covered", "weak"):
            mark += " ⚠️미검증"
        out.append(f"| {i} | {ch} | {sent} | {mark} | {claim} | {url} |")
    out.append("")
    return "\n".join(out)

if __name__ == "__main__":
    raise SystemExit(main())
