#!/usr/bin/env python3
"""인포그래픽 씬의 요소를 **하나씩 따로** 그린다.

재연 씬은 한 장을 그린 뒤 레이어로 가르지만, 인포그래픽은 처음부터 요소별로
만든다. 분리 단계가 없어 그만큼 안정적이고, 배치와 등장 순서를 자유롭게 정할 수 있다.

**글자는 그리지 않는다.** 라벨은 AE 텍스트 레이어가 얹는다 — 이미지에 글자를
구우면 고칠 수도 번역할 수도 없다.

gpt-image-2는 투명 배경을 내지 못한다. 그래서 균일한 크로마 배경으로 뽑고
`remove_chroma_key.py`로 알파를 만든다(코덱스 스킬이 권하는 방식).

    python3 scripts/gen_info_assets.py EP01 --scenes 14,43,57
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CHROMA = "#12FF6A"          # 세모지 팔레트에 없는 색이라 잔상이 남지 않는다

# 화풍 서술은 씬 이미지와 같은 문법을 쓴다. 배경 없는 오브젝트도 같은 세계여야 한다.
STYLE = (
    "벡터 플랫 일러스트, 형태는 오직 색면과 색면이 맞닿는 경계로만 만든다. "
    "같은 색의 한 단계 어두운 톤으로 부드러운 면 그림자만 넣는다. "
    "색면은 명도 대비가 뚜렷해 서로 또렷하게 구분되고, 한 칸의 색면은 고르게 매끈하다. "
    "채도를 낮춘 레트로 플랫 팔레트 #A8BFB4, #8FAECF, #E8C4B0, #2F3E52, #F2F2F0"
)

PROMPT = """$imagegen

**첨부한 그림을 먼저 view_image 도구로 불러와 대화 맥락에 넣으세요.**
경로를 읽고 말로 옮기지 마세요 — 그림 자체가 맥락에 있어야 합니다.

## 첨부 이미지 — 그림체 기준 (세모지 공식 캐릭터 시트)

{base}

이 그림의 그리는 방식으로 아래 **오브젝트 하나만** 그립니다.
사람을 그릴 때는 첨부한 그림에 있는 사람과 똑같은 몸으로 그립니다.

## 그릴 것

{subject}

## 지켜야 할 것

- 화면에 이 오브젝트 하나만 있습니다. 주변은 전부 균일한 단색 {chroma} 배경입니다.
- 오브젝트는 화면 가운데에 크게 놓고 가장자리에 여백을 남깁니다.
- 그림자는 오브젝트 자체의 면 그림자만. 바닥 그림자는 생략합니다.
- 모든 면을 매끈한 빈 색면으로 남깁니다 — 글자는 나중에 영상에서 얹습니다.

Texture/Medium: {style}

AR 1:1

size는 1024x1024입니다.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


# 씬 분석이 내는 요소 문구에는 「투명 배경」·「문자 없음」·「세모지 3D 화풍」이
# 섞여 온다. 셋 다 여기서는 해롭다 — 배경은 크로마로 뽑고, 부정문은 그 단어를
# 오히려 렌더하며, 화풍을 이름으로 부르면 첨부한 그림을 제쳐 두고 재해석한다.
CLEAN = [
    (re.compile(r"투명 ?배경[,\s]*"), ""),
    # 「문자 없음」 계열 — 표현이 여러 갈래로 온다. 하나라도 새면 그 단어가
    # 그림에 찍힌다. 빼고 싶은 것은 PROMPT 본문이 「모든 면을 매끈한 빈
    # 색면으로 남깁니다」라고 긍정형으로 이미 말하고 있다.
    (re.compile(
        r"[,\s]*(읽을 수 있는 )?(실제 )?"
        r"(문자|글자|텍스트|숫자|로고|상표|눈금|라벨|표기)"
        r"(\s*[와과및,]\s*(문자|글자|텍스트|숫자|로고|상표|눈금|라벨|표기))*"
        r"\s*(가|는|은|이)?\s*(없는|없이|없음|생략)"), ""),
    (re.compile(r"세모지[^,]*화풍"), "평면 색면"),
    (re.compile(r"단일 오브젝트"), "오브젝트 하나"),
]


def clean_subject(t: str) -> str:
    for rx, rep in CLEAN:
        t = rx.sub(rep, t)
    return re.sub(r"\s{2,}", " ", t).strip(" ,")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--scenes", required=True, help="쉼표로 구분한 씬 번호")
    ap.add_argument("--base", type=Path,
                    default=Path("auto_agent/data/artstyle/styles/semoji_character_sheet.png"))
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    modes = json.loads((root / "_imggen" / f"{args.ep}_mode.json").read_text(encoding="utf-8"))
    want = {int(x) for x in args.scenes.split(",")}
    out_dir = root / "_imggen" / f"{args.ep.lower()}_info"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    for s in modes["scenes"]:
        if s["n"] not in want or s["mode"] != "infographic":
            continue
        for a in s.get("assets") or []:
            jobs.append((s["n"], a))

    def run(job) -> tuple[int, str, bool]:
        n, a = job
        raw = out_dir / f"s{n:03d}_{a['id']}_raw.png"
        prompt = PROMPT.format(base=args.base.resolve(), subject=clean_subject(a["prompt"]),
                               chroma=CHROMA, style=STYLE, out=raw.resolve())
        subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900)
        if not raw.exists():
            return n, a["id"], False
        cut = out_dir / f"s{n:03d}_{a['id']}.png"
        subprocess.run([sys.executable,
                        str(Path.home() / ".codex/skills/.system/imagegen/scripts/remove_chroma_key.py"),
                        "--input", str(raw), "--out", str(cut),
                        "--key-color", CHROMA, "--tolerance", "70",
                        "--soft-matte", "--despill", "--spill-cleanup", "--force"],
                       capture_output=True, text=True)
        return n, a["id"], cut.exists()

    ok = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, aid, got in ex.map(run, jobs):
            ok += got
            print(f"  {'✓' if got else '✗'} 씬{n:>3} {aid}", flush=True)

    print(f"\n완료 {ok}/{len(jobs)} — {out_dir}")
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
