#!/usr/bin/env python3
"""두 저장소가 함께 쓰는 파일을 어긋나지 않게 유지한다.

**소유자는 v3다.** 고치는 곳은 여기 한 곳이고 adobe는 받아 쓴다.
사본을 각자 고치기 시작하면 어느 쪽이 맞는지 알 수 없게 된다 —
실제로 `verify_voice.py`가 양쪽에서 따로 자라 문턱값이 갈릴 뻔했다.

목록은 `auto_agent/data/spec/shared.json`에 있다.

    python3 scripts/spec_sync.py --check    어긋난 것이 있는지만 본다 (종료코드 1)
    python3 scripts/spec_sync.py --push     소유자 사본을 소비자에게 밀어 넣는다
    python3 scripts/spec_sync.py --lock     현재 해시를 잠금 파일에 굳힌다
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "auto_agent" / "data" / "spec" / "shared.json"
LOCK = ROOT / "auto_agent" / "data" / "spec" / "shared.lock.json"

def consumer_root(name: str) -> Path:
    env = os.environ.get(name.upper() + "_ROOT")
    return Path(env) if env else Path.home() / "LocalProjects" / name

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.is_file() else ""

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--lock", action="store_true")
    a = ap.parse_args()

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    lock: dict = {}
    drift = 0

    for f in spec["files"]:
        src = ROOT / f["source"]
        if not src.is_file():
            print(f"  ✗ {f['id']}: 소유자 사본 없음 — {f['source']}")
            drift += 1
            continue
        h = sha(src)
        lock[f["id"]] = h
        for repo, rel in f["consumers"].items():
            dst = consumer_root(repo) / rel
            dh = sha(dst)
            if dh == h:
                print(f"  ✓ {f['id']} → {repo}")
                continue
            drift += 1
            if a.push:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                print(f"  ↻ {f['id']} → {repo}  ({dh or '없음'} → {h})")
            else:
                print(f"  ✗ {f['id']} → {repo} 어긋남  소유자 {h} / 사본 {dh or '없음'}")

    if a.lock or a.push:
        LOCK.write_text(json.dumps({"version": spec["version"], "sha": lock},
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  잠금 갱신 — {LOCK.name}")

    if a.check and drift:
        print(f"\n{drift}건 어긋남. `spec_sync.py --push` 로 맞추세요.")
        return 1
    print("\n어긋남 없음" if not drift else f"\n{drift}건 처리")
    return 0

if __name__ == "__main__":
    sys.exit(main())
