"""씬을 무엇으로 보여줄지 정한다 — 파이프라인 단계.

`docs/rules/scene-visual-decision.md`를 파이프라인 안으로 들여온 것이다.
그동안 이 판단은 script-director가 원고를 쓰면서 `visual_kind` 한 줄로 끝냈다.
글로만 정하고 **그려서 견주지 않아서**, EP01에서 35씬이 인포그래픽으로 잘못
넘어갔다(실제로는 5씬이 맞았다).

여기서 하는 일은 넷이다.

  ① 시각화 방식 재분석      재연·인포그래픽·실물·콜라주·지도
  ② 인포그래픽 씬 화면 설계   요소는 아직 없다 — 화면을 먼저 짠다
  ③ 그려서 본다             좌표만 보면 겹침도 묻힘도 모른다
  ④ 씬 그림과 견준다         둘 다 이길 때만 인포그래픽

③④는 씬 그림이 이미 있을 때만 할 수 있다. 그림이 없는 첫 실행에서는 ①②까지
하고 멈춘다 — 그림이 나온 뒤 다시 부르면 나머지를 잇는다. 억지로 다 하려다
빈 화면끼리 견주는 일이 없게 한다.

**script-director의 `visual_kind`는 초안이다.** 여기서 뒤집는 것이 정상이다.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from auto_agent.paths import episode_label, get_package_dir


def _run(cmd: list[str], root: Path, log) -> int:
    log.write("$ " + " ".join(cmd[1:]) + "\n")
    log.flush()
    r = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT,
                       stdin=subprocess.DEVNULL)
    return r.returncode


def _has_images(proj: Path) -> int:
    """씬 그림이 몇 장이나 확정돼 있나."""
    f = proj / "images" / "image_assets.json"
    if not f.exists():
        return 0
    try:
        db = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return 0
    return sum(1 for e in db.get("scenes", [])
               if any(i.get("selected") for i in e.get("images") or []))


def run(project: dict, budget_sec: int = 1500, **kwargs) -> dict:
    """파이프라인 진입점.

    러너가 모듈을 30분에 끊는다. 편이 길면 설계·비교가 그 안에 안 끝나므로
    예산을 두고 넘으면 멈춘다. 결과가 파일로 남아 다음 실행이 이어서 한다
    (설계·비교 모두 이미 있는 씬은 건너뛴다).
    """
    import time

    started = time.time()

    def left() -> float:
        return budget_sec - (time.time() - started)

    root = get_package_dir().parent
    proj = Path(project.get("output_dir") or "")
    slug = project.get("slug") or ""
    ep = episode_label(slug)

    if not ep:
        # 편 지도에 없는 프로젝트 — 이 단계는 편 번호로 파일을 잡는다
        return {"status": "skipped", "reason": f"편 번호를 찾을 수 없습니다: {slug}"}

    py = str(root / ".venv/bin/python")
    log_f = root / "_imggen" / f"{ep}_visual_decision.log"
    log_f.parent.mkdir(parents=True, exist_ok=True)
    done = []

    with log_f.open("a", encoding="utf-8") as log:
        # ① 방식 재분석 — 이미 있으면 건너뛴다(사람이 손본 것을 덮지 않는다)
        mode_f = root / "_imggen" / f"{ep}_mode.json"
        if not mode_f.exists():
            _run([py, "scripts/build_mode_input.py", ep, "--slug", slug], root, log)
            _run([py, "scripts/run_visual_mode.py", ep], root, log)
            done.append("방식 재분석")

        if not mode_f.exists():
            return {"status": "failed", "reason": f"재분석 결과가 없습니다 — {log_f}"}

        # ①b 글만 보고 먼저 거른다.
        #
        # 그림이 없는 씬은 견줄 수가 없어 그대로 인포로 남았다. EP02에서
        # 판정은 8씬인데 32씬이 인포로 조립된 것이 그 탓이다.
        # EP01 정답지(그려서 견준 30씬)와 맞춰 보니 글 판단이 93% 일치했고,
        # 틀리는 방향이 한쪽뿐이었다 — 인포를 조금 더 집을 뿐 놓치지는 않는다.
        # 그러니 글로 먼저 좁히고, 그림이 나오면 견주기가 그 둘을 걸러 준다.
        if left() > 300:
            _run([py, "scripts/judge_visual_by_text.py", ep], root, log)
            done.append("글 판단")

        # ② 화면 설계 (인포그래픽으로 정한 씬만)
        if left() < 120:
            return {"status": "completed", "done": done, "note": "시간이 모자라 설계는 다음에"}
        _run([py, "scripts/plan_infographic_layout.py", ep], root, log)
        done.append("화면 설계")

        # 그림이 없으면 여기까지. 없는 그림과 견줄 수는 없다.
        made = _has_images(proj)
        if made < 3:
            log.write(f"씬 그림이 {made}장뿐이라 비교는 다음에 합니다\n")
            return {"status": "completed", "done": done,
                    "note": "씬 그림이 나온 뒤 이 단계를 다시 부르면 비교까지 잇는다"}

        if left() < 240:
            return {"status": "completed", "done": done, "note": "시간이 모자라 비교는 다음에"}

        # ③ 조립 → 그려서 본다
        _run([py, "scripts/compose_infographics.py", ep, "--apply"], root, log)
        _run([py, "scripts/render_infographic.py", ep], root, log)
        done.append("그려서 봄")

        # ④ 씬 그림과 견주고, 그 판정대로 다시 조립
        _run([py, "scripts/compare_scene_vs_info.py", ep], root, log)
        _run([py, "scripts/compose_infographics.py", ep, "--apply"], root, log)
        done.append("견주고 반영")

        # 검수는 결과만 남긴다 — 고치는 것은 사람이 보고 정한다
        if left() > 180:
            _run([py, "scripts/check_infographic.py", ep], root, log)
            done.append("검수")

    picks: dict = {}
    pick_dir = root / "_imggen" / f"{ep.lower()}_pick"
    for f in pick_dir.glob("s*.json") if pick_dir.exists() else []:
        try:
            picks[int(f.stem[1:])] = json.loads(f.read_text(encoding="utf-8")).get("pick")
        except Exception:
            continue

    info = [n for n, p in picks.items() if p == "info"]
    return {
        "status": "completed",
        "done": done,
        "infographic_scenes": sorted(info),
        "scene_image_scenes": sum(1 for p in picks.values() if p == "scene"),
        "log": str(log_f),
    }


if __name__ == "__main__":
    import os

    sys.path.insert(0, str(get_package_dir().parent))
    from auto_agent.db.project_manager import ProjectManager

    # 러너는 인자 없이 부르고 프로젝트를 환경변수로 준다
    slug = (sys.argv[1] if len(sys.argv) > 1 else "") or os.environ.get("PROJECT_NAME", "")
    p = ProjectManager().get_project(slug=slug)
    if not p:
        raise SystemExit(f"프로젝트 없음: {slug}")
    out = run(p)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(0 if out.get("status") in ("completed", "skipped") else 1)
