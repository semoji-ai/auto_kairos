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

CAST_BLOCK = """
등장 인물의 캐릭터 시트를 첨부합니다.
{sheets}

각 인물의 **얼굴, 머리 모양, 옷**은 시트 그대로입니다. 시트의 화풍과 4등신 비율도
그대로 유지하세요. 시트에 없는 것은 이 씬에서 정합니다 — 포즈, 각도, 표정의 세기,
화면에서의 크기와 위치.

인물은 화면에서 **또렷하게 보이는 크기**로 그립니다. 얼굴 생김새와 옷 색이
읽히지 않으면 인물을 넣은 의미가 없습니다.
"""

SCENE = """$imagegen

{prompt}
{cast_block}
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
    ap.add_argument("--roster", type=Path, default=Path("_imggen/characters/roster.json"))
    ap.add_argument("--only", help="쉼표로 구분한 씬 번호")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data.get("scenes", data)}
    names = {e["id"]: e["name"] for e in json.loads(args.roster.read_text(encoding="utf-8"))}
    jobs = json.loads((args.prompt_dir / "jobs.json").read_text(encoding="utf-8"))
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
        block = CAST_BLOCK.format(sheets="\n".join(lines)) if lines else ""
        out = next_version(args.out, n)
        prompt = SCENE.format(prompt=Path(job["prompt_file"]).read_text(encoding="utf-8"),
                              cast_block=block, size=job.get("size", "1792x1024"), out=out)
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
