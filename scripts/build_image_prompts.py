#!/usr/bin/env python3
"""scene_specs의 생성 대상 씬을 공냥(gongnyang) 규격 프롬프트로 변환한다.

전역 규칙(~/.claude/CLAUDE.md): gpt-image-2로 만드는 모든 이미지는 공냥 규격을 따른다.
  - 네거티브 0개 (빼고 싶은 건 전부 긍정형으로)
  - 앞머리 [AR] 브래킷 금지, 끝에 `AR x:y` 토큰 하나만
  - 장비 스펙 대신 결과 서술
  - SD 폐기어휘 금지, HEX 팔레트 컷당 3~5색
  - 1행 = 1컷 = 1 호출

레이어드 장면(scene/statement/quote)은 배경·중경·인물·전경이 분리되도록 쓴다.
정지 이미지 한 장을 뒤에서 레이어로 갈라 2.5D 모션을 넣기 때문이다.

    python3 scripts/build_image_prompts.py <project_dir> -o <out_dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# 세모지 아트스타일 — artstyle/styles/semoji.json에서 뽑은 고정 서술
# 세모지 아트스타일 — artstyle/styles/semoji_base.jpg를 직접 보고 서술
# (semoji.json의 "chubby/oversized head/dot eyes" 서술은 실제 베이스와 맞지 않아 쓰지 않는다)
# ⚠ 몸 비율은 한 글자도 쓰지 않는다. 「4등신」이라 적어도, 「머리가 크고 몸이
# 짧다」라고 풀어 써도 모델이 매번 다르게 해석한다. 실제로 이 한 줄 때문에
# EP01 씬 1·2가 7~8등신으로 나왔다(규칙 character-sheet-rules 3-2절).
# 비율은 gen_scenes.py가 붙이는 기준 시트가 정한다 — 말이 아니라 그림으로.
STYLE = (
    "벡터 플랫 일러스트, 형태는 오직 색면과 색면이 맞닿는 경계로만 만든다. "
    "사람을 그릴 때는 첨부한 그림에 있는 사람과 똑같은 몸으로 그린다. "
    "얼굴에는 코와 입선이 있고, 눈은 작고 둥근 점, 눈썹은 가늘고 짧으며, 뺨에 옅은 홍조가 있다. "
    "같은 색의 한 단계 어두운 톤으로 부드러운 면 그림자만 넣는다. "
    "색면은 명도 대비가 뚜렷해 서로 또렷하게 구분되고, 한 칸의 색면은 고르게 매끈하다"
)

PALETTE = "#A8BFB4, #8FAECF, #E8C4B0, #2F3E52, #F2F2F0"

LAYER_RE = re.compile(r"(배경|중경|인물|전경)\s*:\s*([^,]+(?:,(?!\s*(?:배경|중경|인물|전경)\s*:)[^,]+)*)")

# 공냥 철칙 위반 어휘 — 있으면 걷어낸다
BANNED = [
    "masterpiece", "best quality", "8k", "4k", "uhd", "ultra-detailed",
    "highly detailed", "sharp focus", "trending on artstation", "beautiful", "stunning",
]
NEGATIVE = re.compile(r"\b(no|without|avoid|never|free of|exclude|devoid of)\b", re.IGNORECASE)
# 한국어 부정문도 똑같이 렌더된다. 영어만 잡다가 「안개…쓰지 않고」,
# 「필름 그레인 없이」가 그대로 프롬프트에 실려 나갔다.
NEGATIVE_KO = re.compile(r"(쓰지 않|넣지 않|그리지 (말|않)|없이|않도록|금지)")
# 몸 비율을 말로 규정하면 매번 다르게 해석된다. 비율은 첨부한 시트가 정한다.
RATIO_WORDS = re.compile(r"등신|몸 ?비율|신체 ?비율|머리가 크고|비율은")


def parse_layers(prompt: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in LAYER_RE.findall(prompt or ""):
        v = v.strip().rstrip(",").strip()
        if v and v not in ("없음", "-"):
            out[k] = v
    return out


def clean(text: str) -> str:
    for w in BANNED:
        text = re.sub(rf"\b{re.escape(w)}\b\s*,?\s*", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", text).strip(" ,")


def build(scene: dict) -> str:
    ia = scene.get("imageAsset") or {}
    raw = ia.get("prompt") or ""
    layers = parse_layers(raw)
    info = scene.get("infoStructure") or "scene"

    # 레이어 서술이 없으면 원문을 Scene에 그대로 싣는다
    if layers:
        parts = []
        for key, label in (("배경", "Far background"), ("중경", "Mid ground"),
                           ("인물", "Subject"), ("전경", "Foreground")):
            if key in layers:
                parts.append(f"{label}: {layers[key]}")
        scene_txt = ". ".join(parts)
    else:
        scene_txt = clean(re.sub(r"^레이어 분리형[^,]*,\s*", "", raw))

    mood = scene.get("mood") or "informative"
    # 빛이 아니라 색면의 밝기 차로 분위기를 만든다.
    # 키라이트·앰비언트·딥섀도 같은 사진 어휘를 쓰면 회화적 렌더링이 나온다.
    tone = {
        "dramatic": "어두운 색면과 밝은 색면의 대비를 크게 벌린다",
        "suspense": "전체를 어두운 색면으로 깔고 한 곳만 밝은 색면으로 둔다",
        "contemplative": "밝기 차를 좁혀 색면들이 잔잔하게 이어진다",
        "triumphant": "밝고 따뜻한 색면을 넓게 쓰고 여백을 크게 둔다",
        "somber": "채도를 더 낮춘 색면으로 통일한다",
        "informative": "색면끼리 밝기가 또렷이 구분돼 층이 바로 읽힌다",
    }.get(mood, "색면끼리 밝기가 또렷이 구분된다")

    lines = [
        f"Scene: 한국 브랜드 다큐멘터리 일러스트 한 컷. {scene_txt}",
        "",
        "Camera: 아이레벨 와이드 구도, 원경·중경·인물·전경이 또렷한 층으로 겹쳐 각 층을 따로 "
        "들어낼 수 있게 배치, 피사체 둘레에 넉넉한 여백",
        "",
        f"Lighting: {tone}. 그림자는 같은 색의 한 단계 어두운 색면 하나로만 넣는다",
        "",
        f"Color grading: 채도를 낮춘 레트로 플랫 팔레트 {PALETTE}",
        "",
        # 「안개를 쓰지 않고」처럼 빼고 싶은 것을 이름으로 부르면 모델이 그것을
        # 그린다(공냥 철칙). 한국어 부정문도 마찬가지다 — 검사기는 영어만 잡는다.
        # 전부 긍정형으로 바꿔 그려야 할 것을 지정한다.
        f"Texture/Medium: 매끈한 플랫 질감. {STYLE}. "
        "화면 전체가 같은 밀도의 평면 색면으로 고르게 매끈하다. "
        "먼 곳도 가까운 곳과 같은 선명도의 또렷한 색면으로 그리고, "
        "빛은 색면의 밝기 차로만 나타낸다",
        "",
        # 글자는 화면에서 자막·헤드라인이 담당한다. 이미지에 구워 넣으면 고칠 수도
        # 번역할 수도 없고, 철자가 틀려도 손댈 수 없다. 41씬에서 실제로 생겼다.
        "Text-in-image: 간판·현수막·표지판·화면·책 표지·상자에 이르기까지 "
        "모든 면을 매끈한 빈 색면으로 남겨 둔다. 간판이 필요하면 색면과 도형만으로 "
        "표현하고, 제품명이나 회사명은 형태와 색으로 알아보게 한다",
        "",
        "AR 16:9",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    args = ap.parse_args()

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)
    args.out.mkdir(parents=True, exist_ok=True)

    jobs = []
    for s in scenes:
        ia = s.get("imageAsset") or {}
        if ia.get("source") != "generate":
            continue
        n = s.get("sceneNumber")
        prompt = build(s)

        # 철칙 자체검사
        issues = []
        # search에서 전환된 씬은 prompt가 비어 있다 — 그대로 넘기면 모델이 지어낸다.
        # EP01 씬 68(클리프행어 keyVisual)이 엉뚱한 현대 사무실로 나온 원인이었다.
        if not (ia.get("prompt") or "").strip():
            issues.append("프롬프트 비어 있음")
        if NEGATIVE.search(prompt):
            issues.append("네거티브 표현")
        if NEGATIVE_KO.search(prompt):
            issues.append("한국어 부정문")
        if RATIO_WORDS.search(prompt):
            issues.append("몸 비율을 말로 규정")
        if re.match(r"^\s*\[AR", prompt):
            issues.append("앞머리 AR 브래킷")
        if not prompt.rstrip().endswith("AR 16:9"):
            issues.append("끝 AR 토큰 없음")
        for w in BANNED:
            if re.search(rf"\b{re.escape(w)}\b", prompt, re.IGNORECASE):
                issues.append(f"폐기어휘 {w}")

        path = args.out / f"scene_{n:03d}.txt"
        path.write_text(prompt, encoding="utf-8")
        jobs.append({
            "sceneNumber": n,
            "sceneId": s.get("sceneId"),
            "prompt_file": str(path),
            "size": "1792x1024",
            "badge": s.get("badge"),
            "issues": issues,
        })

    (args.out / "jobs.json").write_text(
        json.dumps(jobs, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    bad = [j for j in jobs if j["issues"]]
    print(f"생성 대상 {len(jobs)}컷 → {args.out}")
    print(f"철칙 위반 {len(bad)}컷" + (f" {[j['sceneNumber'] for j in bad][:8]}" if bad else " ✓"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
