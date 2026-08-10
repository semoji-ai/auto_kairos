#!/usr/bin/env python3
"""상황 씬을 생성한다 — 등장 인물의 캐릭터 시트를 첨부해 얼굴을 고정한다.

씬마다 얼굴이 달라지는 것을 막는 유일한 방법은 시트를 첨부하는 것이다.
텍스트로 인상을 아무리 자세히 써도 매번 재해석된다(인물 시트에서 확인된 사실).

시트는 얼굴·머리·옷의 근거이고, 포즈와 구도는 씬 프롬프트가 정한다.
기존 파일은 지우지 않고 `_v2`, `_v3`로 버전을 올린다(프로젝트 규칙).

    python3 scripts/gen_scenes.py <project_dir> <prompt_dir> -o <out_dir>
    python3 scripts/gen_scenes.py ... --only 7,8,10
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 첨부 조합에 따라 지시가 달라진다 (kairos-ai 실증 구조).
# 사람 그림이 둘이면 섞인다 — 캐릭터 시트가 있으면 화풍 기준 시트를 붙이지 않는다.

STYLE_ONLY = """
## 첨부 이미지 — 그림체 기준 (세모지 공식 캐릭터 시트)

{base}

**[STYLE ONLY] 이 그림은 그림체만 참고합니다.**
- 가져올 것: 색감, 질감, 선 처리, 그림자 방식, 인물의 몸 비율, 분위기
- **가져오지 말 것: 이 그림에 있는 사람의 얼굴, 머리 모양, 옷, 성별, 자세**
- 이 그림 속 인물이 결과물에 나타나서는 안 됩니다
- 아래 장면 설명에 맞는 **새로운 인물**을 그리세요

**[STYLE ONLY] The attached image is for art style reference only.**
- COPY: color palette, texture, line treatment, shading, body proportions, mood
- NEVER COPY: the face, hairstyle, clothing, gender, or pose of any person in it
- The reference image character must NOT appear in the generated image
"""

CAST_ONLY = """
## 첨부 이미지 — 등장 인물

{sheets}

**얼굴과 옷차림만 참고합니다.**
- 인물의 생김새, 머리 모양, 옷은 첨부한 시트 그대로입니다
- **자세는 복사하지 마세요.** 시트의 정면으로 선 자세를 그대로 쓰면 안 됩니다
- 자세와 동작은 아래 장면 설명을 따릅니다
- 그림체와 몸 비율도 시트 그대로입니다
"""

PEOPLE_BLOCK = """
**등장 인물 (이대로 그릴 것)**
{people}
"""
SCENE = """$imagegen

{prompt}
{ref_block}
size는 {size}입니다.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


def next_version(out_dir: Path, n: int) -> Path:
    """기존 파일을 덮어쓰지 않는다 — 이미지 삭제·덮어쓰기 금지 규칙."""
    base = out_dir / f"scene_{n:03d}.png"
    if not base.exists():
        return base
    v = 2
    while (out_dir / f"scene_{n:03d}_v{v}.png").exists():
        v += 1
    return out_dir / f"scene_{n:03d}_v{v}.png"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("prompt_dir", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--sheets", type=Path, default=Path("_imggen/characters/final3"))
    ap.add_argument("--base", type=Path,
                    default=Path("auto_agent/data/artstyle/styles/semoji_character_sheet.png"),
                    help="화풍 기준 시트 — 인물이 없는 씬에도 붙인다")
    ap.add_argument("--roster", type=Path, default=Path("_imggen/characters/roster.json"))
    ap.add_argument("--only", help="쉼표로 구분한 씬 번호")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--allow-empty", action="store_true",
                    help="빈 프롬프트도 생성 (장면이 날조되므로 쓰지 말 것)")
    args = ap.parse_args()

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data.get("scenes", data)}
    names = {e["id"]: e["name"] for e in json.loads(args.roster.read_text(encoding="utf-8"))}
    jobs = json.loads((args.prompt_dir / "jobs.json").read_text(encoding="utf-8"))

    # 프롬프트가 빈 씬을 생성에 넘기면 모델이 장면을 지어낸다.
    # EP01 씬 68(클리프행어)이 현대 사무실로 나온 원인이다. 경고가 아니라 막는다.
    empty = [j["sceneNumber"] for j in jobs if "프롬프트 비어 있음" in (j.get("issues") or [])]
    if empty:
        print(f"  ✗ 프롬프트가 빈 씬 {len(empty)}개: {empty}")
        print("    나레이션을 읽고 imageAsset.prompt를 쓴 뒤 다시 실행하세요.")
        print("    (--allow-empty 로 강제할 수 있으나 장면이 날조됩니다)")
        if not args.allow_empty:
            return 2
    if args.only:
        want = {int(x) for x in args.only.split(",")}
        jobs = [j for j in jobs if j["sceneNumber"] in want]
    args.out.mkdir(parents=True, exist_ok=True)

    def run(job: dict) -> tuple[int, bool, str]:
        n = job["sceneNumber"]
        cast = scenes.get(n, {}).get("cast") or []
        lines = []
        for cid in cast:
            p = (args.sheets / f"{cid}_sheet.png").resolve()
            if p.exists():
                lines.append(f"- {names.get(cid, cid)}: {p}")
        scene = scenes.get(n, {})
        if lines:
            # 캐릭터 시트가 있으면 그것만 붙인다. 화풍 기준 시트를 함께 주면
            # 두 사람 그림이 섞여 정체성이 깨진다.
            ref = CAST_ONLY.format(sheets="\n".join(lines))
        else:
            ref = STYLE_ONLY.format(base=args.base.resolve())
            # 베끼지 말라고만 하면 대신 그릴 것이 없다. 무명 인물이라도
            # 누가 나오는지 적어 주면 시트를 베낄 이유가 사라진다.
            people = scene.get("people") or []
            if people:
                ref += PEOPLE_BLOCK.format(
                    people="\n".join(f"- {d}" for d in people))
        out = next_version(args.out, n)
        prompt = SCENE.format(prompt=Path(job["prompt_file"]).read_text(encoding="utf-8"),
                              ref_block=ref, size=job.get("size", "1792x1024"), out=out)
        subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1200,
        )
        return n, out.exists(), out.name

    ok = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, got, name in ex.map(run, jobs):
            ok += got
            print(f"  {'✓' if got else '✗'} scene {n:>3}  {name}", flush=True)

    print(f"\n완료 {ok}/{len(jobs)}")
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
