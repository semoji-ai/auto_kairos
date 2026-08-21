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


# ── 실사 유래 콜라주 ─────────────────────────────────────
# 제품 병처럼 **실물 형태가 정확해야 하는** 오브젝트는 설명만 보고 그리면
# 라벨·문양·색이 실제와 어긋난다. 조사로 확보한 실사를 붙여 그 형태대로 뽑는다.
#
# 다만 실사처럼 매끈하게 뽑으면 시청자가 진짜 사진으로 받아들인다. 그래서
# **오려 붙인 티가 나게** 만든다 — 재현임이 화면에서 스스로 드러나므로
# 배지 없이도 오도가 생기지 않는다.
#
# ⚠️ 세모지 화풍 에셋에는 쓰지 않는다. 캐릭터 시트에서 오려낸 인물,
#    도형·아이콘처럼 처음부터 그려낸 것에 흰 테두리를 두르면 화면이 지저분해진다.
COLLAGE_REF = """
## 첨부 이미지 — 실물 자료 (형태 기준)

{refs}

이 오브젝트는 **실물 형태를 그대로 따릅니다.** 병의 실루엣, 어깨와 목의 비율,
라벨의 위치와 크기, 문양과 색을 첨부한 사진에서 가져옵니다.
사진을 그대로 복사하지는 말고, 아래 콜라주 지시대로 다시 그립니다.
"""

COLLAGE_STYLE = """
## 콜라주 처리 — 오려 붙인 티가 나게

이것은 사진이 아니라 **잡지에서 오려 붙인 조각**입니다.
- 오브젝트 바깥 둘레에 **흰 종이 테두리를 3~5px 두께로** 두릅니다.
  가위로 자른 듯 미세하게 들쭉날쭉하게, 자를 대고 자른 듯 반듯하지 않게.
- 흰 테두리 바깥으로 **아주 옅은 회색 그림자**를 짧게 깔아 종이가 살짝
  들뜬 느낌을 냅니다. 길게 늘어뜨리지 않습니다.
- 오브젝트 자체는 실물의 색과 형태를 유지하되 **면을 단순하게** 정리합니다.
  반사와 하이라이트는 색면 두세 단계로 줄입니다.
- 배경 그림자, 원근 왜곡, 렌즈 흐림은 넣지 않습니다.
"""

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
    # 배경 지시 — 「투명 배경」·「배경 없음」 둘 다 온다. 배경은 크로마로 뽑는다.
    (re.compile(r"[,\s]*배경\s*(이|은)?\s*없음"), ""),
    (re.compile(r"투명 ?배경[,\s]*"), ""),
    # 「문자 없음」 계열 — 표현이 여러 갈래로 온다. 하나라도 새면 그 단어가
    # 그림에 찍힌다. 빼고 싶은 것은 PROMPT 본문이 「모든 면을 매끈한 빈
    # 색면으로 남깁니다」라고 긍정형으로 이미 말하고 있다.
    #
    # 앞의 수식(전혀·아무·일체)과 뒤에 이어 붙는 다른 명사(사진·이름·
    # 사건번호…)까지 함께 걷어낸다. EP03에서 144건이 「배경 없음」 하나로,
    # EP01·04·11에서 「실제 글자와 사진 없음」 꼴로 새고 있었다.
    (re.compile(
        r"[,\s]*(아무\s*|전혀\s*|일체\s*|실제\s*|읽을 수 있는\s*)*"
        r"(문자|글자|텍스트|숫자|로고|상표|눈금|라벨|표기)"
        r"(\s*[와과및,]\s*[가-힣A-Za-z]+)*"
        r"\s*(가|는|은|이|도)?\s*(전혀\s*|아무\s*)?(없는|없이|없음|생략)"), ""),
    (re.compile(r"세모지[^,]*화풍|세모지 평면 일러스트|단순한 세모지 아이콘"), "평면 색면"),
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
    sys.path.insert(0, str(root))
    from auto_agent.paths import resolve_project  # noqa: E402

    _proj, ep = resolve_project(args.ep)
    mode_f = root / "_imggen" / f"{ep}_mode.json"
    modes = json.loads(mode_f.read_text(encoding="utf-8")) if mode_f.exists() else {"scenes": []}

    # 설계가 있으면 **설계가 부르는 요소만** 그린다.
    # 규칙이 「그 화면이 요구하는 것만 그린다」인데, 재분석이 나열한 것을
    # 통째로 뽑고 있었다. EP01에서 157장을 뽑아 놓고 쓴 것은 40장뿐이었다.
    layout_dir = root / "_imggen" / f"{ep.lower()}_layout"
    wanted: dict = {}
    designs: dict = {}
    for f_ in layout_dir.glob("s*.json") if layout_dir.exists() else []:
        try:
            lay = json.loads(f_.read_text(encoding="utf-8"))
        except Exception:
            continue
        if lay.get("skip"):
            continue
        wanted[int(f_.stem[1:])] = {it.get("id") for it in lay.get("items") or []}
        designs[int(f_.stem[1:])] = lay
    want = {int(x) for x in args.scenes.split(",")}
    out_dir = root / "_imggen" / f"{ep.lower()}_info"
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = []
    # `collage` 도 요소를 따로 그린다 — 실사 병 옆에 수치·풍미 요소를 놓는
    # 화면이다. 모드 표에는 둘 다 있는데 여기서 infographic 만 받아, 콜라주로
    # 정한 씬은 에셋이 한 장도 안 나왔다. 디아지오편 58·92·121 이 그랬다.
    by_mode = {s["n"]: s for s in modes.get("scenes", [])
               if s.get("mode") in ("infographic", "collage")}
    for n in sorted(want):
        need = wanted.get(n)
        listed = {a.get("id"): a for a in (by_mode.get(n) or {}).get("assets") or []}
        # 재분석이 요소를 나열해 뒀으면 그것을 쓴다. 없으면 **설계가 부르는
        # 요소를 그대로 그린다** — 옛 재분석에만 기대면 원고를 다시 쓴 뒤
        # 새로 생긴 도해 씬은 그릴 것이 하나도 없다(8씬이 0장이 됐다).
        for iid in sorted(need or listed):
            a = listed.get(iid)
            if a is None:
                lay = designs.get(n) or {}
                it = next((x for x in lay.get("items") or [] if x.get("id") == iid), {})
                a = {"id": iid,
                     "prompt": it.get("asset_prompt") or it.get("label")
                     or lay.get("title") or "",
                     "role": lay.get("title", "")}
            jobs.append((n, a))

    def run(job) -> tuple[int, str, bool]:
        n, a = job
        raw = out_dir / f"s{n:03d}_{a['id']}_raw.png"
        prompt = PROMPT.format(base=args.base.resolve(), subject=clean_subject(a["prompt"]),
                               chroma=CHROMA, style=STYLE, out=raw.resolve())
        # 실사 자료가 붙은 오브젝트만 콜라주로 간다. 세모지 화풍 에셋은
        # 그대로 둔다 — 그려낸 것에 흰 테두리를 두르면 화면이 지저분해진다.
        refs = [r for r in (a.get("refAssets") or [])
                if r.get("local") and Path(r["local"]).exists()]
        if refs:
            lines = "\n".join(f"- {r.get('desc') or '실물 자료'}: {Path(r['local']).resolve()}"
                              for r in refs[:2])
            prompt = prompt.replace(
                "## 그릴 것",
                COLLAGE_REF.format(refs=lines) + COLLAGE_STYLE + "\n## 그릴 것", 1)
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
