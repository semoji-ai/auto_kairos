#!/usr/bin/env python3
"""연속 씬(±2) 같은 카메라 무빙·같은 연출 보고 — 생성 결과는 고치지 않는다(보고만).

세모지 통합보고 §0-1 #4 · §4 "연속 씬 같은 무빙 금지". 규칙: auto_agent/tools/repetition_check.py

    python3 scripts/check_repetition.py <project_dir> [-w 2] [--json out.json]
종료 코드: 되풀이가 있으면 1, 없으면 0.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.tools.repetition_check import find_repetitions, load_plan  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-w", "--window", type=int, default=2)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    plan = load_plan(a.project)
    reps = find_repetitions(plan, a.window)
    n_cam = sum(1 for p in plan if p["camera"])
    n_mot = sum(1 for p in plan if p["motion"])
    print(f"씬 {len(plan)} · 카메라 무빙 계획 {n_cam} · 연출 계획 {n_mot} · ±{a.window}씬 되풀이 {len(reps)}")
    for r in reps:
        kind = "카메라" if r["field"] == "camera" else "연출"
        print(f"  ! #{r['a']} ↔ #{r['b']} 같은 {kind}: {r['value']}")
    if not n_cam and not n_mot:
        print("  (비교할 카메라·연출 계획이 없다 — motion_<sceneId>.json 이나 씬 motion/camera 필드)")
    if a.json:
        a.json.write_text(json.dumps({"window": a.window, "plan": plan, "repetitions": reps},
                                     ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if reps else 0


if __name__ == "__main__":
    sys.exit(main())
