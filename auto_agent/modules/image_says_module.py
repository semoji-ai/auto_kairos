"""그린 그림을 **열어 보고** 이 말을 하는지 묻는다 — 파이프라인 단계.

빠져 있던 고리다. 검사가 둘 있었는데 둘 다 그림을 안 봤다.

  check_prompt_match.py      나레이션 ↔ 프롬프트     글과 글
  check_asset_relevance.py   실물 자료 ↔ 나레이션    생성 이미지는 대상 밖

그래서 프롬프트가 맞으면 검사는 전부 통과했고, **그림이 배신한 것은
화면에 올라갈 때까지 아무도 몰랐다.**

  씬993   말 「원하는 색·두께·무늬를 못 내놓았다」  (실패)
          그림 선반 가득한 가게에서 웃으며 천을 펼치는 주인  (성공)
  씬1004  말 「누가 비단을 사겠느냐」  (두려움)
          그림 맑은 하늘, 물건 가득한 좌판, 웃으며 걷는 사람들

둘 다 프롬프트는 정확했다. 원인은 프롬프트의 80%가 화풍 지시였고 그중
인물 비율 블록이 스스로 「이 그림에서 가장 중요한 요구」라고 선언한 데
있다 — 모델은 시킨 대로 화풍을 지키고 이야기를 흘렸다.

화풍을 덜면 그림체가 흩어지므로 덜지 않는다. `build_image_prompts.py` 가
순위만 바꾼다(Priority 를 맨 앞에, Must be visible 을 맨 끝에). 그렇게
고친 뒤 13컷을 다시 그려 11컷이 회복됐다.

**고쳐도 또 생긴다.** 그래서 그릴 때마다 묻는 고리를 여기 둔다.

  ok    그림이 그 말을 한다
  weak  어긋나지는 않지만 그 말의 핵심이 화면에 없다
  wrong 그림이 말과 반대이거나 딴 이야기를 한다   ← 다시 그린다

LG 1편 첫 검사: ok 63 · weak 35 · wrong 10.

규칙: `docs/rules/image-direction-rules.md` 1·3절.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from auto_agent.paths import get_package_dir, resolve_project


def run(project: dict, budget_sec: int = 2400, **kwargs) -> dict:
    root = get_package_dir().parent
    proj, ep = resolve_project(project.get("slug") or project.get("output_dir"))
    log_f = proj / "image_says.log"

    with log_f.open("w", encoding="utf-8") as log:
        log.write(f"$ check_image_says.py {ep}\n")
        log.flush()
        subprocess.run([sys.executable, "scripts/check_image_says.py", ep],
                       cwd=root, stdout=log, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL)

    # 결과를 스텝의 산출로 돌려준다. 막지는 않는다 — 그림 한 장 때문에
    # 편 전체가 멈추면 아무도 이 검사를 켜 두지 않는다. 대신 숫자를 남겨
    # 다음 사람이 무엇부터 볼지 알게 한다.
    out = root / "_imggen" / f"{ep}_image_says.json"
    wrong = weak = ok = 0
    if out.exists():
        try:
            rows = json.loads(out.read_text(encoding="utf-8")).get("scenes", [])
            for r in rows:
                v = r.get("verdict")
                wrong += v == "wrong"
                weak += v == "weak"
                ok += v == "ok"
        except Exception:
            pass
    return {"ok": True, "log": str(log_f), "report": str(out),
            "verdicts": {"ok": ok, "weak": weak, "wrong": wrong},
            "note": ("wrong 은 replan_direction → build_image_prompts → gen_scenes 로 "
                     "다시 그린다. docs/rules/image-direction-rules.md 3절")}
