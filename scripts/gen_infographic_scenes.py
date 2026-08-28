#!/usr/bin/env python3
"""도해를 **조각으로 조립하지 않고 한 장으로 그린다** — 글자까지 함께.

지금까지 도해는 조각 에셋을 만들고 → 좌표를 잡고 → 그려 보고 → 겹쳤는지
검사하고 → 좌표를 고치는 다섯 단계였다. LG 1편에서 그 왕복을 두 번 돌고도
검사기가 여섯 장 전부에서 같은 것을 다시 잡았다.

  겹침 · 화면밖 · 나열 · 뜻이틀림

게다가 좌표로 못 고치는 것이 있다. 씬1024 는 왼쪽 궤짝 하나가 오른쪽 다섯
개보다 크게 그려져 「다섯 배」가 거꾸로 읽혔는데, 이건 **에셋 크기가 틀린
것**이라 배치를 아무리 고쳐도 안 됐다. 그리고 조각 에셋은 스톡 일러스트라
8등신으로 나와, 앞뒤 컷의 4등신 인물과 다른 사람으로 보였다.

한 장으로 그리면 이 넷이 한꺼번에 사라지고 화풍이 저절로 맞는다.

**글자는 그림 안에 넣는다.** gpt-image-2 는 한글을 제대로 쓴다 — 씬12 의
「사농공상 / 장손이 맨 아래 칸으로 / 사·농·공·상」이 한 글자도 안 틀렸다.
고쳐야 할 일이 생기면 레이어를 갈라 애프터이펙트에서 글자를 바꾼다.

**문구는 지어내지 않는다.** 명세의 title·label·mark 에 적힌 말을 그대로
옮긴다. 도해의 말은 이미 원고와 맞춰 둔 것이라 다시 쓰면 어긋난다.

    python3 scripts/gen_infographic_scenes.py EP01 --scenes 2,1020
    python3 scripts/gen_infographic_scenes.py EP01 --scenes 2 --apply

`--apply` 는 그린 한 장을 화면 전체로 쓰도록 명세를 바꾼다. 조각과 좌표는
지우지 않고 `composed_backup` 에 남긴다 — 되돌릴 수 있어야 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

PALETTE = "#A8BFB4, #8FAECF, #E8C4B0, #2F3E52, #F2F2F0"

# scene 그림과 같은 화풍 서술을 쓴다 — 도해만 다른 그림처럼 보이면
# 그 자리에서 몰입이 끊긴다. 실제로 시청자 넷이 씬12·1074 를 두고
# 「딴 채널 같다」고 했다.
STYLE = (
    "벡터 플랫 일러스트, 형태는 오직 색면과 색면이 맞닿는 경계로만 만든다. "
    "사람을 그릴 때는 첨부한 그림에 있는 사람과 똑같은 몸으로 그린다. "
    "얼굴에는 코와 입선이 있고, 눈은 작고 둥근 점, 눈썹은 가늘고 짧다. "
    "같은 색의 한 단계 어두운 톤으로 부드러운 면 그림자만 넣는다. "
    "색면은 명도 대비가 뚜렷해 서로 또렷하게 구분되고, 한 칸의 색면은 고르게 매끈하다"
)

PROPORTION = """CHARACTER PROPORTIONS — apply to every person in the frame:
Stylized cartoon proportions, three and a half heads tall.
The head is very large relative to the body — one head height equals roughly
28 percent of the full standing figure. Shoulders sit just below the chin.
Legs are short and thick, arms are short with mitten-like hands."""

PLAN = """도해 한 컷을 **한 장의 그림**으로 그리기 위한 서술을 씁니다.

지금까지는 조각 그림을 만들어 좌표로 배치했습니다. 그 방식은 겹치고,
화면 밖으로 나가고, 크기가 어긋나 뜻이 뒤집혔습니다. 이제 한 장으로
그리므로 **배치를 말로 정확히 적어 주어야** 합니다.

## 이 도해

{spec}

## 쓸 것

**① 화면 서술** — 배경·중경·인물·전경으로 나눠 적습니다. 도해이므로
배경은 「아주 옅은 미색 바탕에 연한 회색 모눈이 고르게 깔린 평면」으로
두고, 그 위에 사물과 사람을 놓습니다.

**② 글자** — 화면에 들어갈 한글을 적습니다.

## 반드시 지킬 것

**개수와 크기가 곧 뜻입니다.** 「다섯 배」면 같은 물건을 같은 크기로
하나와 다섯 놓습니다. 크기가 다르면 정확히 반대로 읽힙니다 — 실제로
그렇게 나온 적이 있습니다. 비교하는 두 덩어리는 **같은 물건, 같은 각도,
같은 크기**여야 합니다.

**문구를 지어내지 마세요.** 위 명세의 제목·라벨·기호에 적힌 말을 글자
그대로 옮깁니다. 원고와 맞춰 둔 말이라 새로 쓰면 어긋납니다.

**부정문을 쓰지 마세요.** 「무엇을 넣지 않는다」가 아니라 무엇이 있는지로
적습니다. 빼고 싶은 것은 있는 것으로 바꿔 씁니다.

**강조는 색으로 합니다.** 강조할 것만 따뜻한 색으로 칠하고 나머지는
채도를 낮춘 회색조로 물러나게 합니다.

**흐름은 화살표로 보입니다.** 순서나 이동이 있으면 굵은 짙은 남색 화살표
하나로 어디서 어디로 가는지 보입니다.

## 낼 것 — JSON만

{{"scene": "배경/중경/인물/전경으로 나눈 화면 서술 한 문단",
  "text": "화면에 들어갈 한글을 자리와 함께 — 제목은 어디에 무엇, 라벨은 어디에 무엇",
  "count_check": "이 그림에서 개수나 크기로 뜻을 지는 것이 있으면 무엇인지 한 줄"}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=1200, env=env)
    except Exception:
        return None
    out = r.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(out[i:j + 1])
    except json.JSONDecodeError:
        return None


def check_text(root: Path, ep: str, n: int) -> str:
    """지난 검수에서 나온 지적 — 다시 그릴 때 물려준다.

    안 물려주면 같은 것을 또 그린다. 씬2 는 「잃었다」인데 기둥이 멀쩡히
    서 있고 가운데 `+` 가 합산으로 읽혀, 화면이 나레이션과 반대로 말했다.
    """
    f = root / "_imggen" / f"{ep.lower()}_check" / (
        f"s{n:03d}.json" if n < 1000 else f"s{n}.json")
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if d.get("verdict") != "fix":
        return ""
    L = ["  지난번에 그렸다가 이렇게 지적받았습니다 — 이번엔 이걸 고쳐야 합니다:"]
    for x in d.get("problems") or []:
        L.append(f"    [{x.get('kind')}] {x.get('detail','')}")
        if x.get("fix"):
            L.append(f"      고칠 방향: {x['fix']}")
    return "\n".join(L)


def spec_text(s: dict) -> str:
    g = s.get("infographic") or {}
    L = [f"  말: {(s.get('narration') or '').strip()}",
         f"  제목: {g.get('title','')}"]
    if g.get("note"):
        L.append(f"  왜 이렇게 짰나: {g['note']}")
    for it in g.get("items") or []:
        L.append(f"  요소: {it.get('id','')}"
                 + (f" — 라벨 「{it['label']}」" if it.get("label") else "")
                 + (f" (강조: {it['emphasis']})" if it.get("emphasis") else ""))
    for m in g.get("marks") or []:
        L.append(f"  기호: 「{m.get('text','')}」")
    return "\n".join(L)


def build(plan: dict) -> str:
    return "\n\n".join([
        "Priority: 아래 Scene 이 말하는 것을 한눈에 세어 읽을 수 있게 만드는 것이 "
        "이 그림의 목적입니다. 그 뒤의 규격은 어떤 화풍으로 그릴지를 정합니다.",
        f"Scene: 한국 브랜드 다큐멘터리의 설명 화면 한 컷. {plan['scene']}",
        "Camera: 정면에서 곧게 본 평면 구도, 요소 둘레에 넉넉한 여백",
        "Lighting: 색면끼리 밝기가 또렷이 구분돼 층이 바로 읽힌다. "
        "그림자는 같은 색의 한 단계 어두운 색면 하나로만",
        f"Color grading: 채도를 낮춘 레트로 플랫 팔레트 {PALETTE}",
        PROPORTION,
        f"Texture/Medium: 매끈한 플랫 질감. {STYLE}",
        f"Text-in-image: {plan['text']} 글자는 획이 또렷한 한글이며 "
        "여기 적은 말만 넣습니다.",
        "AR 16:9",
    ])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--use-check", action="store_true",
                    help="지난 검수의 지적을 물려준다 (check_infographic.py 결과)")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    by_n = {s.get("sceneNumber"): s for s in data["scenes"]}

    want = [int(x) for x in args.scenes.split(",")]
    todo = [n for n in want
            if by_n.get(n, {}).get("visual_kind") == "infographic"]
    skipped = [n for n in want if n not in todo]
    if skipped:
        print(f"  도해가 아니라 건너뜁니다: {skipped}")
    if not todo:
        raise SystemExit("그릴 도해가 없습니다")

    out_dir = root / "_imggen" / f"{ep.lower()}_infoscene"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{ep}  도해 {len(todo)}장을 한 장씩 그립니다")

    def plan_one(n):
        sp = spec_text(by_n[n])
        if args.use_check:
            fb = check_text(root, ep, n)
            if fb:
                sp += "\n\n" + fb
        d = ask(PLAN.format(spec=sp))
        if not d or not (d.get("scene") or "").strip():
            return n, None
        p = build(d)
        (out_dir / f"scene_{n:04d}.txt").write_text(p, encoding="utf-8")
        return n, d

    plans = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, d in ex.map(plan_one, todo):
            if d:
                plans[n] = d
                print(f"  씬{n:>5}  서술 완료 — {d.get('count_check','')[:56]}")
            else:
                print(f"  씬{n:>5}  서술 실패")

    # 전역 규칙: 생성 전 공냥 검증기를 반드시 통과해야 한다
    chk = Path.home() / ".claude/skills/image-prompt/scripts/check_prompt.mjs"
    ok = []
    for n in plans:
        p = out_dir / f"scene_{n:04d}.txt"
        if chk.exists():
            r = subprocess.run(["node", str(chk), str(p)],
                               capture_output=True, text=True)
            if '"errors": []' not in r.stdout:
                print(f"  씬{n} 철칙 위반 — 건너뜁니다\n{r.stdout[-400:]}")
                continue
        ok.append(n)
    print(f"  철칙 검증 통과 {len(ok)}/{len(plans)}")

    base = (root / "auto_agent/data/artstyle/styles/semoji_character_sheet.png").resolve()

    def draw(n):
        out = (out_dir / f"scene_{n:04d}.png").resolve()
        body = (out_dir / f"scene_{n:04d}.txt").read_text(encoding="utf-8")
        prompt = (
            "$imagegen\n\n"
            "**첨부한 그림을 먼저 view_image 도구로 불러와 대화 맥락에 넣으세요.**\n"
            "경로를 읽고 말로 옮기지 마세요 — 그림 자체가 맥락에 있어야 합니다.\n\n"
            f"{body}\n\n"
            f"화풍 기준 그림(사람 몸 비율과 그리는 방식만 참고): {base}\n\n"
            "size는 1792x1024입니다.\n\n"
            "생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:\n"
            f"{out}"
        )
        subprocess.run(["codex", "exec", "--skip-git-repo-check",
                        "--sandbox", "workspace-write", prompt],
                       stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       timeout=int(os.environ.get("GEN_TIMEOUT", "2400")))
        return n, out.exists()

    drawn = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, got in ex.map(draw, ok):
            print(f"  {'✓' if got else '✗'} 씬{n}")
            if got:
                drawn.append(n)

    if not args.apply:
        print(f"\n  {len(drawn)}장 그렸습니다. --apply 로 도해에 반영합니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_infoscene_{datetime.now():%Y%m%d_%H%M%S}"))
    for n in drawn:
        g = by_n[n].get("infographic") or {}
        # 조각과 좌표는 지우지 않고 남긴다 — 되돌릴 수 있어야 한다
        if "composed_backup" not in g:
            g["composed_backup"] = {k: g.get(k) for k in ("items", "marks", "title")}
        g["items"] = [{"id": "full", "src": f"{ep.lower()}_infoscene/scene_{n:04d}.png",
                       "left": 50.0, "top": 50.0, "size": 100.0,
                       "label": "", "emphasis": "normal"}]
        g["marks"] = []
        g["title"] = ""          # 제목은 그림 안에 있다
        g["background"] = "plain"
        by_n[n]["infographic"] = g
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  {len(drawn)}장을 도해에 반영했습니다.")
    print(f"  확인: python3 scripts/render_infographic.py {ep} --scenes {','.join(map(str, drawn))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
