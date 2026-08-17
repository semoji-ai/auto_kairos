#!/usr/bin/env python3
"""시각화 방식 재분석을 돌린다 — `{EP}_mode.json`.

「자료를 구할 수 있나」가 아니라 **「이 내용을 어떻게 보여줘야 알아듣나」**를
먼저 묻는다. EP01에서 이 순서를 뒤집자 68씬 중 55씬이 몰려 있던 「그림 한 장」이
재연·인포그래픽·실물·콜라주로 갈라졌다.

판단 기준과 출력 양식은 `_imggen/visual_mode_prompt.txt`에 있다. 여기서는
그 문서에 입출력 경로만 끼워 코덱스에 넘긴다 — 지시를 두 곳에 두지 않는다.

    python3 scripts/run_visual_mode.py EP02
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--effort", default="xhigh")
    ap.add_argument("--timeout", type=int, default=5400)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    src = root / "_imggen" / f"{args.ep}_mode_in.json"
    dst = root / "_imggen" / f"{args.ep}_mode.json"
    if not src.exists():
        raise SystemExit(f"입력이 없습니다: {src}  (build_mode_input.py 를 먼저 돌리세요)")
    if dst.exists():
        print(f"이미 있습니다: {dst}")
        return 0

    prompt = (root / "_imggen" / "visual_mode_prompt.txt").read_text(encoding="utf-8")
    prompt = prompt.replace("__INPUT__", str(src.relative_to(root)))
    prompt = prompt.replace("__OUTPUT__", str(dst.relative_to(root)))

    log = root / "_imggen" / f"{args.ep}_mode.log"
    with log.open("w", encoding="utf-8") as f:
        subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--sandbox", "workspace-write",
             "-c", f"model_reasoning_effort={args.effort}", prompt],
            cwd=root, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT,
            timeout=args.timeout,
        )

    if not dst.exists():
        print(f"결과 파일이 없습니다 — {log} 를 보세요")
        return 1

    data = json.loads(dst.read_text(encoding="utf-8"))
    modes: dict[str, int] = {}
    for s in data.get("scenes", []):
        modes[s.get("mode", "?")] = modes.get(s.get("mode", "?"), 0) + 1
    changed = sum(1 for s in data.get("scenes", []) if s.get("keep_or_change") == "changed")
    print(f"{dst}")
    print(f"  방식별: {modes}")
    print(f"  바뀐 씬: {changed}  /  쪼갬 {len(data.get('splits') or [])}  합침 {len(data.get('merges') or [])}")
    print(f"  요약: {data.get('summary', '')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
