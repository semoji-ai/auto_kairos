#!/usr/bin/env python3
"""오디오 파일을 나레이션에 다시 잇는다.

scene_specs를 재생성하면 `sceneId`가 새로 발급되는데 오디오 파일명은 옛 ID
그대로다. 그러면 씬과 소리가 끊긴다 — EP05·EP09·EP11·EP12가 그랬고,
매니페스트의 `audioPath`도 0건이었다. 렌더해도 소리가 안 난다.

**파일명이 아니라 내용으로 잇는다.** ElevenLabs가 남긴 `.timestamps.json`에
실제로 읽은 글자가 들어 있어, 그것을 씬 나레이션과 대조하면 짝을 찾을 수 있다.

붙지 않은 씬은 TTS를 다시 돌려야 한다 — `--report`로 목록을 낸다.

    python3 scripts/relink_audio.py EP05
    python3 scripts/relink_audio.py EP05 --apply
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

WS = re.compile(r"\s+")


def norm(t: str) -> str:
    """맞춤법 전처리·문장부호 차이를 무시하고 비교한다."""
    t = re.sub(r"[^\w가-힣]", "", t or "")
    return WS.sub("", t)


def spoken(p: Path) -> str:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return "".join(d.get("characters") or [])
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--apply", action="store_true", help="scene_specs의 sceneId를 갱신")
    ap.add_argument("--min", type=float, default=0.72, help="이 이상 닮아야 같은 문장으로 본다")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    key = next((k for k in emap if k.startswith(args.ep)), None)
    D = Path(emap[key]["dir"])

    sp = D / "scene_specs.json"
    data = json.loads(sp.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    pool = []
    for ts in sorted((D / "audio").glob("*.timestamps.json")):
        stem = ts.name.replace(".timestamps.json", "")
        if (D / "audio" / f"{stem}.mp3").exists():
            pool.append((stem, norm(spoken(ts))))

    hit, miss, used = 0, [], set()
    for s in scenes:
        n = s["sceneNumber"]
        want = norm(s.get("narration_tts") or s.get("narration") or "")
        if not want:
            continue
        best, score = None, 0.0
        for stem, said in pool:
            if stem in used or not said:
                continue
            r = SequenceMatcher(None, want[:220], said[:220]).ratio()
            if r > score:
                best, score = stem, r
        if best and score >= args.min:
            used.add(best)
            hit += 1
            if args.apply:
                s["sceneId"] = best
        else:
            miss.append((n, round(score, 2)))

    if args.apply and hit:
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.ep}: 씬 {len(scenes)} / 오디오 {len(pool)} → 연결 {hit}"
          f" / 미연결 {len(miss)}" + ("  [apply]" if args.apply else "  [dry-run]"))
    if miss:
        print(f"      TTS 재생성 필요: {[m[0] for m in miss][:20]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
