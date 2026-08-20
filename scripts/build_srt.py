#!/usr/bin/env python3
"""씬 오디오 길이를 재서 자막(SRT)을 만든다.

씬마다 음성 파일이 있고 그 길이가 곧 그 문장이 화면에 머무는 시간이다.
낱말 단위 타이밍이 필요하면 ElevenLabs 글자 타임스탬프를 써야 하지만,
편집·검수용으로는 씬 단위로 충분하다.

    python3 scripts/build_srt.py EP05
    python3 scripts/build_srt.py EP05 --split 45   # 45자 넘으면 문장 단위로 쪼갠다
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402


def audio_len(p: Path) -> float:
    """오디오 길이(초). ffprobe가 없으면 0."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
            capture_output=True, text=True, timeout=30)
        return float((r.stdout or "0").strip() or 0)
    except Exception:
        return 0.0


def fmt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def clean(text: str) -> str:
    """화면에 뜨는 말만 남긴다 — 강조 표시는 자막에 그대로 찍히면 안 된다."""
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", text or "")
    t = re.sub(r"\{\{(.+?)\}\}", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def chunks(text: str, limit: int) -> list[str]:
    """긴 문장은 문장 부호에서 끊는다. 한 줄이 너무 길면 읽히지 않는다."""
    if len(text) <= limit:
        return [text]
    parts, cur = [], ""
    for piece in re.split(r"(?<=[.!?。…])\s+", text):
        if not cur:
            cur = piece
        elif len(cur) + len(piece) + 1 <= limit:
            cur += " " + piece
        else:
            parts.append(cur)
            cur = piece
    if cur:
        parts.append(cur)
    return parts or [text]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--split", type=int, default=48, help="한 자막의 최대 글자 수")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 편 라벨이든 프로젝트 slug 든 받는다 — 시리즈가 아닌 프로젝트도 돌아야 한다
    proj, ep = resolve_project(args.ep)
    specs = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))
    audio = proj / "audio"

    out, idx, t = [], 1, 0.0
    missing = []
    for s in specs.get("scenes", []):
        n = s.get("sceneNumber")
        f = audio / f"{s.get('sceneId')}.mp3"
        if not f.exists():
            f = audio / f"scene_{n:03d}.mp3"
        if not f.exists():
            missing.append(n)
            continue
        dur = audio_len(f)
        if dur <= 0:
            missing.append(n)
            continue
        text = clean(s.get("narration") or "")
        if not text:
            t += dur
            continue
        parts = chunks(text, args.split)
        share = dur / len(parts)
        for i, part in enumerate(parts):
            start = t + share * i
            out.append(f"{idx}\n{fmt(start)} --> {fmt(start + share)}\n{part}\n")
            idx += 1
        t += dur

    dst = proj / f"{proj.name}.srt"
    dst.write_text("\n".join(out), encoding="utf-8")
    print(f"{dst}")
    print(f"  자막 {idx - 1}개 · 총 {t / 60:.1f}분")
    if missing:
        print(f"  음성이 없어 건너뛴 씬 {len(missing)}개: {missing[:15]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
