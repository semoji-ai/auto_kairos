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
STYLE = (
    "벡터 플랫 일러스트, 외곽선을 전혀 쓰지 않고 색면만으로 형태를 만든다. "
    "인물은 4등신 비율로 머리가 크고 몸이 짧다. "
    "얼굴에는 코와 입선이 있고, 눈은 작고 둥근 점, 눈썹은 가늘고 짧으며, 뺨에 옅은 홍조가 있다. "
    "같은 색의 한 단계 어두운 톤으로 부드러운 면 그림자만 넣는다. "
    "색면은 명도 대비가 뚜렷해 서로 또렷하게 구분되고, 질감과 그러데이션 없이 매끈하다"
)

PALETTE = "#A8BFB4, #8FAECF, #E8C4B0, #2F3E52, #F2F2F0"

LAYER_RE = re.compile(r"(배경|중경|인물|전경)\s*:\s*([^,]+(?:,(?!\s*(?:배경|중경|인물|전경)\s*:)[^,]+)*)")

# 공냥 철칙 위반 어휘 — 있으면 걷어낸다
BANNED = [
    "masterpiece", "best quality", "8k", "4k", "uhd", "ultra-detailed",
    "highly detailed", "sharp focus", "trending on artstation", "beautiful", "stunning",
]
NEGATIVE = re.compile(r"\b(no|without|avoid|never|free of|exclude|devoid of)\b", re.IGNORECASE)


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
    tone = {
        "dramatic": "high contrast, deep shadows anchoring the subject",
        "suspense": "cool dim ambience, single warm light source",
        "contemplative": "soft even light, calm spacing",
        "triumphant": "bright warm key, open airy composition",
        "somber": "muted low-saturation field, heavy sky",
        "informative": "clear neutral daylight, legible separation between planes",
    }.get(mood, "clear neutral daylight")

    lines = [
        f"Scene: 한국 브랜드 다큐멘터리 일러스트 한 컷. {scene_txt}",
        "",
        "Camera: 아이레벨 와이드 구도, 원경·중경·인물·전경이 또렷한 층으로 겹쳐 각 층을 따로 "
        "들어낼 수 있게 배치, 피사체 둘레에 넉넉한 여백",
        "",
        f"Lighting: {tone}, 따뜻한 키라이트와 차가운 앰비언트 필, 가장자리가 부드러운 그림자",
        "",
        f"Color grading: 채도를 낮춘 레트로 플랫 팔레트 {PALETTE}",
        "",
        f"Texture/Medium: 매끈한 플랫 질감. {STYLE}",
        "",
        "Text-in-image: 형태와 색만 담은 깨끗한 면",
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
