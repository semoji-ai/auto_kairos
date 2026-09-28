#!/usr/bin/env python3
"""실물 자료를 찾아볼 씬을 고른다 — 전 씬에서, source와 무관하게.

**source가 search인 씬만 조사하면 실물 우선이 봉쇄된다.** 에이전트는 기본적으로
generate로 기울고, 한 번 generate로 찍힌 씬은 조사 대상에서 빠져 실물이 있어도
영영 안 쓰인다. EP02는 65씬 중 search가 5개뿐이었다(EP01은 68씬 중 29개).

그래서 판단 순서를 뒤집는다.
    (X) source가 search인 씬을 조사한다
    (O) 실물이 있을 법한 씬을 조사하고, 있으면 search로 올린다

전 씬을 다 조사하면 편당 한 시간이 넘고, 은유·심리 장면은 조사해도 빈손이다.
그래서 **사료가 있을 자리만 골라낸다.**

    python3 scripts/select_asset_candidates.py <project_dir> -o <out.json> [--judge]

**--judge (권장).** 아래 SIGNALS 는 LG편 고유명사 사전이라 소재가 바뀌면 거의 걸리지 않는다
(디아지오편 142씬 중 7씬). --judge 는 전 씬을 한 번에 모델에게 보여 주고 「이 씬의 말과
직접 이어지는 실물이 남아 있을 법한가, 있다면 무엇인가」를 판정받는다. 정규식 신호는
판정의 힌트로만 넘긴다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# 실물이 남아 있을 법한 신호 — 나레이션·헤드라인·프롬프트에서 찾는다
SIGNALS = [
    # 고유명사·조직
    (r"[가-힣]{2,}(전자|화학|산업|그룹|반도체|텔레콤|디스플레이|이노텍|생활건강)", "기업"),
    (r"(금성사|락희|럭키|LG|GS|삼성|현대|대우|소니|애플|구글|모토로라|노키아)", "브랜드"),
    # 제품
    (r"(라디오|텔레비전|냉장고|세탁기|에어컨|휴대폰|스마트폰|배터리|반도체|크림|치약)", "제품"),
    (r"(초콜릿폰|프라다폰|샤인폰|옵티머스|롤러블|트롬|디오스|휘센|싸이언)", "제품명"),
    # 인물
    (r"(구인회|구자경|구본무|구광모|허만정|허준구|허창수|이병철|정주영)", "인물"),
    (r"(회장|사장|창업자|대표이사|연구원|기술자)", "직함"),
    # 사건·시점
    (r"\b(19|20)\d{2}년", "연도"),
    (r"(출시|발표|준공|창업|설립|합병|인수|파업|화재|소송|상장|철수|매각)", "사건"),
    # 문서·기록
    (r"(광고|신문|기사|보도|사사|연혁|특허|주권|계약서|약관|보고서|사진)", "기록"),
    # 장소
    (r"(공장|본사|사옥|매장|연구소|단지|박람회|전시회)", "장소"),
    # 한국 현대사 — LG는 이 나라 역사와 겹쳐 흐른다. 기록 사진이 가장 풍부한 자리다.
    (r"(전쟁|피난|수복|해방|광복|군정|개발|산업화|새마을|올림픽|월드컵|외환위기|IMF|"
     r"民主|민주화|고도성장|수출)", "현대사"),
    (r"(거리|시장|골목|가정집|안방|다방|극장|학교|역전|정류장|버스|전차|기차|"
     r"아파트|판자촌|상점가|백화점)", "생활상"),
    (r"(라디오 듣|텔레비전 보|흑백|컬러 방송|전기가 들어|수돗물|연탄|보릿고개)", "시대풍경"),
]

# 강한 신호 라벨 — 이게 없으면 검색어를 만들 수 없다. 편별 어휘로 늘어난다.
STRONG_LABELS = {"인물", "브랜드", "제품명", "기업"}

# 실물이 없는 자리 — 조사해도 빈손이다
SKIP = [
    (r"(마음|생각|믿음|불안|두려움|자존심|각오|의지)", "심리"),
    (r"(상징|은유|비유|처럼|같이 보이는|떠올리)", "은유"),
    (r"^\s*\*\*[^*]+\*\*\s*$", "명제"),  # 강조만 있는 한 줄 = 메시지 씬
]

# 이 레이아웃은 화면에 실물 이미지가 필요하다
IMAGE_LAYOUTS = {"cinematic", "quote_portrait", "images_grid", "before_after", "split"}


def classify(scene: dict) -> tuple[bool, list[str], str]:
    text = " ".join(str(scene.get(f) or "") for f in ("narration", "headline"))
    ia = scene.get("imageAsset") or {}
    text += " " + str(ia.get("prompt") or "") + " " + str(ia.get("query") or "")

    hits = sorted({label for pat, label in SIGNALS if re.search(pat, text)})
    skips = sorted({label for pat, label in SKIP if re.search(pat, text, re.M)})

    layout = scene.get("layout") or ""
    needs_image = layout in IMAGE_LAYOUTS

    # 실물을 특정할 수 있는 강한 신호 — 이게 없으면 검색어를 만들 수 없다
    strong = STRONG_LABELS & set(hits)

    # 시대 장면은 브랜드가 없어도 기록 사진이 넘친다.
    # 1950년대 서울 거리, 산업화 시절 공장, 라디오 앞에 모인 가족 —
    # 국가기록원과 e영상역사관에 다 있고, 이런 자료가 공감대를 만든다.
    era = {"현대사", "생활상", "시대풍경"} & set(hits)

    # 강한 신호 + 뒷받침 신호
    worth = bool(strong) and len(hits) >= 2
    # 이미지가 필요한 레이아웃이면 신호 하나로도 찾아본다
    if strong and needs_image:
        worth = True
    # 시대 신호 + 연도(또는 다른 신호)면 시대 기록 사진을 찾아볼 값어치가 있다
    if era and len(hits) >= 2:
        worth = True
    # 은유·심리 장면은 사료가 없다
    if skips and len(hits) < 3:
        worth = False
    reason = ("+".join(hits) or "신호없음") + (f" / 제외:{'+'.join(skips)}" if skips else "")
    return worth, hits, reason


JUDGE_PROMPT = """브랜드·기업사 다큐멘터리의 씬 목록입니다. 실물 자료(보도사진, 제품 사진, 광고·신문 지면,
공문서, 인물 초상, 기록 영상 캡처)를 찾아볼 값어치가 있는 씬을 고르세요.

판정 기준:
- 그 씬의 나레이션을 들은 사람이 자료를 보고 「이게 방금 그 이야기구나」 하고 알 수 있는
  **특정한** 실물이 세상에 남아 있을 법한가. 「같은 시대라서」「분위기가 맞아서」는 이유가 아니다
- 특정할 수 있어야 검색어를 만들 수 있다 — 인물·제품·사건·장소·문서가 구체적인가
- 은유·심리·가정·명제 씬, 「어느 공장」처럼 특정할 수 없는 씬은 제외
- 개수보다 정확도. 애매하면 제외

signals 는 키워드 기반 참고 힌트일 뿐 판단 근거가 아닙니다.

씬 목록(JSON):
__SCENES__

JSON 한 덩어리로만 답하세요:
{"items":[{"n":씬번호,"worth":true|false,"expected_asset":"찾을 실물을 한 문장으로","query":"검색어","reason":"판정 이유 한 줄"}]}
모든 씬에 대해 한 항목씩 답합니다."""


def judge_with_model(scenes: list[dict]) -> dict[int, dict]:
    """전 씬을 한 번에 판정받는다. claude CLI 는 stdin 으로 부른다(-p 인자 없이)."""
    rows = []
    for s in scenes:
        ia = s.get("imageAsset") or {}
        _, hits, _ = classify(s)
        rows.append({"n": s.get("sceneNumber"), "layout": s.get("layout"),
                     "narration": (s.get("narration") or "")[:300],
                     "hint": (ia.get("query") or ia.get("prompt") or "")[:120],
                     "signals": hits})
    prompt = JUDGE_PROMPT.replace("__SCENES__", json.dumps(rows, ensure_ascii=False))
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)
    cli = os.getenv("CLAUDE_CLI") or "claude"
    proc = subprocess.run([cli, "--print", "--output-format", "json", "--model", "opus",
                           "--max-turns", "1", "--tools", ""],
                          input=prompt, capture_output=True, text=True, timeout=1800, env=env)
    text = json.loads(proc.stdout).get("result", "") if proc.stdout.strip().startswith("{") else proc.stdout
    m = re.search(r"\{[\s\S]*\}", text)
    if proc.returncode != 0 or not m:
        raise RuntimeError(f"판정 실패: {proc.stderr[:300] or text[:300]}")
    items = json.loads(m.group(0)).get("items", [])
    return {it.get("n"): it for it in items}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--judge", action="store_true",
                    help="모델이 전 씬을 보고 판정한다(정규식 신호는 힌트로만)")
    ap.add_argument("--signals", type=Path,
                    help="편별 어휘 JSON. 기본 SIGNALS 는 LG편 어휘라 다른 소재에서는 "
                         "거의 걸리지 않는다(디아지오편 142씬 중 7씬). "
                         '형식: {"강한": {"브랜드": "정규식", ...}, "뒷받침": {...}}')
    args = ap.parse_args()

    # 편별 어휘 주입 — 기본 목록은 LG 전용 고유명사라 소재가 바뀌면 무력해진다.
    if args.signals:
        extra = json.loads(args.signals.read_text(encoding="utf-8"))
        for label, pat in (extra.get("강한") or {}).items():
            SIGNALS.append((pat, label))
            STRONG_LABELS.add(label)
        for label, pat in (extra.get("뒷받침") or {}).items():
            SIGNALS.append((pat, label))

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)

    judged = judge_with_model(scenes) if args.judge else {}

    picked = []
    for s in scenes:
        worth, hits, reason = classify(s)
        j = judged.get(s.get("sceneNumber"))
        if args.judge:
            worth = bool(j and j.get("worth"))
            reason = (j or {}).get("reason") or "판정 없음"
        if not worth:
            if args.verbose:
                print(f"    - {s.get('sceneNumber'):>3} 제외  {reason}")
            continue
        picked.append({
            "n": s.get("sceneNumber"),
            "layout": s.get("layout"),
            "currentSource": (s.get("imageAsset") or {}).get("source"),
            "signals": hits,
            "narration": (s.get("narration") or "")[:200],
            "headline": s.get("headline"),
            "hint": (j or {}).get("query") or (s.get("imageAsset") or {}).get("query")
                    or (s.get("imageAsset") or {}).get("prompt", "")[:120],
            **({"expected_asset": j.get("expected_asset", ""), "reason": reason} if j else {}),
        })

    args.out.write_text(json.dumps({"scenes": picked}, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    gen = sum(1 for p in picked if p["currentSource"] == "generate")
    print(f"  {args.project.name}: 전체 {len(scenes)}씬 → 조사 대상 {len(picked)}씬 "
          f"(그중 지금 generate로 잡힌 것 {gen}씬)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
