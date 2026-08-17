#!/usr/bin/env python3
"""공유 규격 파일이 소유자(v3) 판과 같은지 본다.

소유자는 auto_kairos_v3다. 여기 있는 것은 **사본**이므로 고치지 않는다 —
고쳐야 하면 v3에서 고치고 `spec_sync.py --push`로 내려받는다.

v3가 없는 환경에서도 잠금 파일(data/spec/shared.lock.json)의 해시로 판정한다.

    python3 scripts/spec_check.py
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "data" / "spec" / "shared.lock.json"
# 잠금 파일의 id → 이 저장소에서의 위치
PATHS = {
    "semoji-voice-bands": "data/artstyle/semoji-voice-bands.json",
    "semoji-drawing-style": "data/artstyle/semoji_drawing_style.json",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else ""


def main() -> int:
    if not LOCK.is_file():
        print("잠금 파일 없음 — v3에서 spec_sync.py --push 를 돌리세요")
        return 1
    want = json.loads(LOCK.read_text(encoding="utf-8"))["sha"]
    bad = 0
    for key, rel in PATHS.items():
        p = ROOT / rel
        got, exp = sha(p), want.get(key, "")
        if got == exp:
            print(f"  ✓ {key}")
        else:
            bad += 1
            print(f"  ✗ {key} — 잠금 {exp or '없음'} / 사본 {got or '없음'}")
    if bad:
        print(f"\n{bad}건 어긋남. v3에서 `python3 scripts/spec_sync.py --push`")
        return 1
    print("\n공유 규격 일치")
    return 0


if __name__ == "__main__":
    sys.exit(main())
