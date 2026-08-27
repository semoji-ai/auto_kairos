"""화면을 정한 뒤 **세어 본다** — 파이프라인 단계.

규칙은 있었는데 검사가 없었다. `scene-splitting-rules.md` 6절에
「같은 프롬프트를 나눠 가진 씬 — 0」이 적혀 있었지만 LG 1편에서 한 번도
돌지 않았고, 세어 보니 16씬이 같은 프롬프트로 그려져 있었다.

여기서 두 가지를 센다.

  ① 프롬프트를 나눠 가진 씬
     원고를 다시 쓰며 씬을 쪼갤 때 조각들이 원래 씬의 `imageAsset` 을
     통째로 물려받는다. 원래 프롬프트는 합쳐진 문장 전체를 그린 것이라
     조각 하나에는 너무 많은 것이 들어 있다.

       씬20   「보통 첫 실패 뒤에는 물건을 줄이기 마련인데요」
       씬997  「구인회는 반대로 구색을 늘렸습니다」            ← 반전
       둘 다  「…두 선택 사이에서 풍성한 쪽을 고르는 구인회…」

     **질문 컷에 답이 이미 그려진다.** 반전이 나오기 전에 소진된다.

  ② 근거 없는 실물 자료
     판정문과 종류가 정반대로 저장되는 일이 있다.

       씬1023  이유 「archive 부재, 재현 필요」  →  종류 search_image

     다음 단계는 그 말을 곧이곧대로 읽고 자료를 찾으러 가고, 맞는 자료가
     없으니 **시대만 맞는 아무 사진**을 붙인다. 「그의 이름은 안희제」에
     일본어 간판이 걸린 거리 사진이 붙은 경로다.

     이유문으로 잡으면 오탐이 난다 — 이유문은 낡는다. 씬25·52는 「부재」라
     적혔지만 그 뒤 좋은 자료를 실제로 찾았다. **관련성 칸으로 가른다.**

규칙: `docs/rules/image-direction-rules.md` 2·4절.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from auto_agent.paths import get_package_dir, resolve_project


def _run(cmd: list[str], root: Path, log) -> int:
    log.write("$ " + " ".join(str(c) for c in cmd[1:]) + "\n")
    log.flush()
    r = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL)
    return r.returncode


def run(project: dict, budget_sec: int = 600, **kwargs) -> dict:
    root = get_package_dir().parent
    proj, ep = resolve_project(project.get("slug") or project.get("output_dir"))
    log_f = proj / "visual_gate.log"

    with log_f.open("w", encoding="utf-8") as log:
        # ① 나눈 뒤 세어 본다 — 보고만 한다. 프롬프트를 다시 쓰는 것은
        #    replan_direction 의 몫이라 여기서 손대지 않는다.
        _run([sys.executable, "scripts/check_split_health.py", ep], root, log)

        # ② 근거 없는 실물 자료는 재현으로 되돌린다. 되돌려 두면 다음
        #    실행에서 프롬프트가 쓰이고 그림이 그려진다. 그냥 두면 계속
        #    엉뚱한 사진이 붙은 채로 화면에 올라간다.
        _run([sys.executable, "scripts/check_kind_reason.py", ep, "--apply"], root, log)

    return {"ok": True, "log": str(log_f),
            "note": "docs/rules/image-direction-rules.md 2·4절"}
