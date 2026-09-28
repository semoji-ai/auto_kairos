#!/usr/bin/env python3
"""**화면에 넣을 출처 자막 문구**를 씬 번호에 붙여 낸다.

`check_manuscript_sources.py` 는 「이 문장에 근거가 있는가」를 답한다.
편집자가 필요한 것은 그다음이다 — **그래서 화면 어디에 뭐라고 찍을 것인가.**

## 자막 문구 규칙

방송 관행대로 **한 줄, 짧게**. 긴 URL 을 화면에 찍지 않는다.

    출처: 디아지오                      자사 자료·공식 제품 페이지
    출처: 스카치위스키 규정 2009        법령
    출처: IWSC / SFWSC / USC            수상 기록
    출처: 광고주 제공 자료               브리프·브랜드북·가격표
    자료: <매체명>                       그 외 2차 자료

**URL 은 더보기란으로 뺀다.** 화면에는 누구의 자료인지만 밝히고, 확인할
사람은 설명란에서 원문을 연다 — 그래야 화면이 안 지저분해진다.

    python3 scripts/make_source_captions.py <project> [-o 출처_자막.md]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlparse

# 도메인 → 화면에 찍을 이름. 없는 도메인은 호스트를 그대로 쓴다.
PUBLISHER = {
    "malts.com": "디아지오 (malts.com)",
    "shop.malts.com": "디아지오 (malts.com)",
    "diageobaracademy.com": "디아지오 바 아카데미",
    "legislation.gov.uk": "스카치위스키 규정 2009 (영국 법령)",
    "scotchwhisky.com": "Scotch Whisky",
    "marklittler.com": "Mark Littler",
    "whisky-news.com": "whisky-news.com",
    "diffordsguide.com": "Difford's Guide",
    "masterofmalt.com": "Master of Malt",
    "pasabahce.com": "파사바체",
    "en.wikipedia.org": "위키백과",
    "smwsa.com": "SMWS",
    "maltspedia.com": "Maltspedia",
    "distiller.com": "Distiller",
    "diffordsguide.com/": "Difford's Guide",
}

# ── 광고주가 준 자료 ────────────────────────────────────────────────────
# **「광고주 제공 자료」라고 찍으면 안 된다.** 시청자는 광고주가 누구인지
# 모르고, 그건 제작 내부에서 쓰는 말이다. 화면에는 **그 말을 한 주체의
# 이름**을 쓴다 — 브랜드북의 서술은 그 브랜드가 한 말이다.
MATERIAL = {
    "src_material_광고주_브리프": "디아지오",
    "src_material_CLYx_DesignManual_2020": "클라이넬리쉬 디자인 매뉴얼",
    "src_material_Lagavulin_BrandWorld_2023": "라가불린 브랜드북",
    "src_material_Talisker_BTL_2024": "탈리스커 브랜드 툴킷",
    "src_material_Singleton_Toolkit_v11": "싱글톤 브랜드 툴킷",
    # 판매가는 디아지오의 주장이 아니라 매장의 사실이다 — 시청자가 확인할
    # 곳을 적는다. 값 자체는 광고주 가격표에서 왔고 광고주가 확인한다.
    "src_material_가격표_png": "이마트 · 트레이더스 (2026 추석 행사가)",
}


# ── 화면에 찍어도 되는 출처 ──────────────────────────────────────────────
# **판매처를 출처로 찍으면 안 된다.** 브랜드 다큐에서 「이 사실의 근거는 술
# 파는 가게」가 되어 버린다. 실제로 Master of Malt(영국 위스키 판매점),
# dailyshot.co(한국 주류 커머스), Mark Littler(위스키 경매 중개사)가 자막에
# 들어가 있었다.
#
# 발행 주체를 댈 수 없는 것도 뺀다. scotchwhisky.com 은 내용은 믿을 만하나
# 사이트 어디에도 발행인이 없고 about 페이지가 404다 — 시청자가 「출처:
# Scotch Whisky」를 보고 그게 무엇인지 알 방법이 없다.
#
# 남기는 것은 셋뿐이다. **법령 · 당사자 공식 · 판매 매장.**
SAFE_HOSTS = {
    "legislation.gov.uk",        # 1차 자료 — 영국 법령
    "malts.com", "shop.malts.com", "diageo.com", "diageobaracademy.com",  # 디아지오 자사
    "pasabahce.com",             # 잔 제조사 자사
}


def caption_for(url: str, src: str) -> str:
    """화면 자막 한 줄. **안전하지 않은 출처는 빈 문자열을 돌려준다.**"""
    if url:
        host = urlparse(url).netloc.lower().replace("www.", "")
        if host not in SAFE_HOSTS:
            return ""
        return "출처: " + PUBLISHER.get(host, host)
    src = str(src)
    if src in MATERIAL:
        return "출처: " + MATERIAL[src]
    if src.startswith("src_material_"):
        return "출처: 디아지오"          # 브랜드 자료인데 표에 없는 것
    return ""                            # chapter_facts·위키는 자격이 없다


# 제품 이름을 부르거나 앞말을 잇는 문장에는 출처가 필요 없다.
# 「탈리스커 10년, 클라이넬리쉬 14년…」에 출처를 달면 도입부가 지저분해진다.
NO_CAPTION = re.compile(
    r"^\s*(\d+년\s*,?\s*)+$|"                       # 「10년, 14년, 15년, 16년」
    r"^[^.?!]*년까지\s*$|"                           # 「… 라가불린 16년까지」
    r"메시지가 그래서|그래서요|말이죠|보셨죠")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def run(proj: Path, out: Path) -> dict:
    check = json.loads((proj / "source_check.json").read_text(encoding="utf-8"))
    specs = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = specs if isinstance(specs, list) else specs.get("scenes", [])

    # 문장 → 판정 (원고 문장 그대로 열쇠로 쓴다)
    verdict = {}
    for bucket in ("covered", "weak", "mismatch", "missing"):
        for x in check[bucket]:
            verdict[norm(x["sentence"])] = (bucket, x)

    rows = []
    for i, sc in enumerate(scenes, 1):
        nar = str(sc.get("narration") or "")
        hits = []
        for line in re.split(r"[\n]+", nar):
            line = line.strip()
            if not line:
                continue
            v = verdict.get(norm(line))
            if v:
                hits.append((line, *v))
        if not hits:
            continue
        # 한 씬에 여러 근거가 걸리면 가장 강한 것 하나만 찍는다 — 자막이 겹치면 못 읽는다
        best = sorted(hits, key=lambda h: {"covered": 0, "weak": 1, "mismatch": 2,
                                           "missing": 3}[h[1]])[0]
        line, bucket, x = best
        cap = caption_for(x.get("url", ""), x.get("src", ""))
        # **약하게 걸린 근거로 자막을 달면 안 된다.** 화면에 「출처: X」라고
        # 찍는 순간 그 문장을 X 가 보증한 것이 된다. 실제로 클라이넬리쉬
        # 출처가 더프타운 문장에 붙는 일이 있었다 — 점수가 낮은 것은 뺀다.
        if bucket != "covered" or float(x.get("score", 0)) < 0.35 or x.get("unverified"):
            cap = ""
        if NO_CAPTION.search(line):
            cap = ""
        rows.append({"scene": sc.get("sceneNumber") or i, "chapter": sc.get("chapter", ""),
                     "narration": line, "verdict": bucket, "caption": cap,
                     "url": x.get("url", ""), "src": x.get("src", ""),
                     "unverified": bool(x.get("unverified")),
                     "score": x.get("score", 0), "bucket": bucket})

    with_cap = [r for r in rows if r["caption"]]
    need = [r for r in rows if not r["caption"]]

    md = ["# 출처 자막 — 화면에 넣을 문구", "",
          f"근거가 확인된 씬 **{len(with_cap)}개**에 아래 문구를 넣습니다. "
          "URL 은 화면에 찍지 않고 **더보기란**으로 뺍니다.", "",
          "## 화면 자막", "",
          "| 씬 | 나레이션 | 화면 자막 |", "|---:|---|---|"]
    for r in with_cap:
        n = r["narration"].replace("|", "/")[:56]
        md.append(f"| {r['scene']} | {n} | `{r['caption']}` |")

    md += ["", "## 더보기란에 넣을 출처 목록", ""]
    seen = {}
    for r in with_cap:
        if r["url"] and r["url"] not in seen:
            seen[r["url"]] = r["caption"].replace("출처: ", "")
    for i, (u, name) in enumerate(seen.items(), 1):
        md.append(f"{i}. {name} — {u}")
    # 같은 매체가 여러 쪽이면 이름이 겹친다 — 목록에서는 쪽까지 보이므로 괜찮다
    mats = sorted({r["caption"].replace("출처: ", "") for r in with_cap if not r["url"]})
    for j, m in enumerate(mats, len(seen) + 1):
        md.append(f"{j}. {m} — 디아지오 코리아 / PMG Korea 제공 자료 "
                  "(유튜브 가이드, 브랜드북 4종, 가격표)")

    if need:
        md += ["", "## 자막을 달지 않는 씬", "",
               "아래 씬은 근거가 있어도 **화면에 출처를 찍지 않습니다.** 사유는 셋입니다.", "",
               "1. **판매처가 출처** — Master of Malt(영국 위스키 판매점), dailyshot.co"
               "(한국 주류 커머스). 브랜드 다큐에서 술 파는 가게를 근거로 댈 수 없습니다.",
               "2. **발행 주체 불명** — scotchwhisky.com 은 내용은 믿을 만하나 사이트에 "
               "발행인이 없고 about 페이지가 404입니다. 위키백과도 같은 이유입니다.",
               "3. **개인 운영** — whisky-news.com 은 2006년부터 스위스의 파트리크 브로사르가 "
               "독립적으로 운영합니다. 자료로 쓰기엔 충실하나 화면 출처로는 약합니다.", "",
               "| 씬 | 나레이션 | 현재 근거 | 사유 |", "|---:|---|---|---|"]
        for r in need:
            src = r["src"] or "없음"
            host = urlparse(r["url"]).netloc.replace("www.", "") if r["url"] else ""
            if host:
                why = ("판매처" if host in ("masterofmalt.com", "dailyshot.co", "marklittler.com")
                       else "발행 주체 불명" if host in ("scotchwhisky.com", "en.wikipedia.org")
                       else "개인 운영" if host == "whisky-news.com" else "재검토")
                src = host
            else:
                why = ("근거 약함" if r["bucket"] != "covered" else
                       "미검증 자료" if r["unverified"] else
                       "출처 불필요" if NO_CAPTION.search(r["narration"]) else f"대응 약함({r['score']})")
            md.append(f"| {r['scene']} | {r['narration'].replace('|','/')[:56]} | {src} | {why} |")

    out.write_text("\n".join(md) + "\n", encoding="utf-8")
    return {"with_caption": len(with_cap), "need": len(need), "matched_scenes": len(rows)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("-o", "--out", default="")
    a = ap.parse_args()
    proj = Path(a.project)
    out = Path(a.out) if a.out else proj / "출처_자막.md"
    r = run(proj, out)
    print(f"  근거 걸린 씬 {r['matched_scenes']}개")
    print(f"    자막 넣을 씬   {r['with_caption']}")
    print(f"    자막 못 넣는 씬 {r['need']}")
    print(f"  → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
