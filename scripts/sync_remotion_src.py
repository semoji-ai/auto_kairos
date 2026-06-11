#!/usr/bin/env python3
"""remotion src 단일 소스 동기화.

단일 진실 소스: auto_agent/remotion_template/src/ (git 추적)
파생물:        remotion/src/ (git 미추적 — 런타임 작업 사본)

사용법:
  python3 scripts/sync_remotion_src.py            # template → remotion 미러링
  python3 scripts/sync_remotion_src.py --check    # 드리프트 검사만 (차이 있으면 exit 1)
  python3 scripts/sync_remotion_src.py --reverse  # remotion → template 역방향 (백포트용)

규칙: remotion/src/ 를 직접 수정하지 마세요. template 수정 후 본 스크립트 실행.
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_SRC = REPO_ROOT / "auto_agent" / "remotion_template" / "src"
RUNTIME_SRC = REPO_ROOT / "remotion" / "src"

IGNORE_NAMES = {".DS_Store", "__pycache__"}


def _walk(root: Path) -> set[Path]:
    """root 하위 모든 파일의 상대 경로 집합 (무시 목록 제외)."""
    files: set[Path] = set()
    for p in root.rglob("*"):
        if p.is_file() and not (set(p.relative_to(root).parts) & IGNORE_NAMES):
            files.add(p.relative_to(root))
    return files


def find_drift(src: Path, dest: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """(src에만 있음, dest에만 있음, 내용 다름) 튜플 반환."""
    src_files = _walk(src)
    dest_files = _walk(dest)
    only_src = sorted(src_files - dest_files)
    only_dest = sorted(dest_files - src_files)
    differing = sorted(
        rel for rel in src_files & dest_files
        if not filecmp.cmp(src / rel, dest / rel, shallow=False)
    )
    return only_src, only_dest, differing


def sync(src: Path, dest: Path) -> int:
    """src → dest 미러링 (dest에만 있는 파일은 삭제). 변경 파일 수 반환."""
    only_src, only_dest, differing = find_drift(src, dest)
    for rel in only_src + differing:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)
        print(f"  COPY  {rel}")
    for rel in only_dest:
        (dest / rel).unlink()
        print(f"  DEL   {rel}")
    return len(only_src) + len(only_dest) + len(differing)


def main() -> int:
    if not TEMPLATE_SRC.is_dir() or not RUNTIME_SRC.is_dir():
        print(f"[sync_remotion_src] 경로 없음: {TEMPLATE_SRC} 또는 {RUNTIME_SRC}")
        return 2

    if "--check" in sys.argv:
        only_t, only_r, differing = find_drift(TEMPLATE_SRC, RUNTIME_SRC)
        if not (only_t or only_r or differing):
            print("[sync_remotion_src] OK — 양쪽 일치")
            return 0
        print("[sync_remotion_src] 드리프트 감지:")
        for rel in only_t:
            print(f"  template에만 있음: {rel}")
        for rel in only_r:
            print(f"  remotion에만 있음: {rel}")
        for rel in differing:
            print(f"  내용 다름:        {rel}")
        print()
        print("  remotion/src를 직접 수정했다면:  python3 scripts/sync_remotion_src.py --reverse")
        print("  template이 최신이라면:           python3 scripts/sync_remotion_src.py")
        return 1

    if "--reverse" in sys.argv:
        changed = sync(RUNTIME_SRC, TEMPLATE_SRC)
        print(f"[sync_remotion_src] remotion → template 백포트 완료 ({changed}개 파일)")
    else:
        changed = sync(TEMPLATE_SRC, RUNTIME_SRC)
        print(f"[sync_remotion_src] template → remotion 동기화 완료 ({changed}개 파일)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
