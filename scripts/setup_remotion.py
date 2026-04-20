#!/usr/bin/env python3
"""
setup_remotion.py — remotion/ 폴더 초기화 및 동기화

git clone 후 remotion/ 폴더가 없는 팀원이 실행하거나,
auto_agent/remotion_template/src 변경 후 remotion/src에 반영할 때 사용.

사용법:
    python scripts/setup_remotion.py            # 전체 초기화 (최초 1회)
    python scripts/setup_remotion.py --src-only # src/ 만 동기화
    python scripts/setup_remotion.py --fonts    # fonts 만 동기화
    python scripts/setup_remotion.py --no-install  # npm install 건너뜀
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ── 경로 계산 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent                               # auto_kairos_v3/
TEMPLATE_DIR = PROJECT_ROOT / "auto_agent" / "remotion_template"
REMOTION_DIR = PROJECT_ROOT / "remotion"

# ── 동기화 대상 정의 ──────────────────────────────────────────────────────────
# (템플릿 상대경로, 복사 모드: "dir"|"file")
SYNC_TARGETS = [
    ("src",                 "dir"),
    ("public/fonts",        "dir"),
    ("public/assets",       "dir"),
    ("tsconfig.json",       "file"),
    ("remotion.config.ts",  "file"),
    ("vite.editor.config.ts",  "file"),
    ("vite.thumb.config.ts",   "file"),
    ("vite.preview.config.ts", "file"),
    ("tailwind.config.ts",  "file"),
    ("postcss.config.js",   "file"),
]

# package.json은 별도 처리 (remotion/ 에 이미 있으면 덮어쓰지 않음)
PACKAGE_JSON_SRC = TEMPLATE_DIR / "package.json"


def sync_dir(src: Path, dst: Path, label: str) -> None:
    """디렉토리를 dst로 복사 (기존 삭제 후 재복사)."""
    if not src.exists():
        print(f"  [SKIP] {label} — 소스 없음: {src}")
        return
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  [OK]   {label} → {dst.relative_to(PROJECT_ROOT)}")


def sync_file(src: Path, dst: Path, label: str) -> None:
    """단일 파일 복사."""
    if not src.exists():
        print(f"  [SKIP] {label} — 소스 없음: {src}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  [OK]   {label} → {dst.relative_to(PROJECT_ROOT)}")


def sync_fonts_only() -> None:
    print("▶ fonts 동기화")
    src = TEMPLATE_DIR / "public" / "fonts"
    dst = REMOTION_DIR / "public" / "fonts"
    sync_dir(src, dst, "public/fonts")


def sync_src_only() -> None:
    print("▶ src/ 동기화")
    src = TEMPLATE_DIR / "src"
    dst = REMOTION_DIR / "src"
    sync_dir(src, dst, "src")


def full_setup(no_install: bool = False) -> None:
    print(f"▶ remotion/ 초기화: {REMOTION_DIR}")
    REMOTION_DIR.mkdir(parents=True, exist_ok=True)

    # public/ 루트 디렉토리 생성
    (REMOTION_DIR / "public").mkdir(exist_ok=True)

    for rel, mode in SYNC_TARGETS:
        src = TEMPLATE_DIR / rel
        dst = REMOTION_DIR / rel
        if mode == "dir":
            sync_dir(src, dst, rel)
        else:
            sync_file(src, dst, rel)

    # package.json: 없을 때만 복사 (로컬 수정 유지)
    pkg_dst = REMOTION_DIR / "package.json"
    if not pkg_dst.exists():
        sync_file(PACKAGE_JSON_SRC, pkg_dst, "package.json (최초)")
    else:
        print(f"  [SKIP] package.json — 이미 존재 (로컬 유지)")

    # npm install
    if no_install:
        print("  [SKIP] npm install (--no-install)")
    else:
        _run_npm_install()

    print("\n✅ remotion/ 셋업 완료")
    print("   Remotion Studio 실행: cd remotion && npx remotion studio")


def _run_npm_install() -> None:
    print("▶ npm install (remotion/)")
    node_bin = _find_node_bin()
    npm_cmd = [str(node_bin / "npm"), "install"] if node_bin else ["npm", "install"]
    try:
        subprocess.run(npm_cmd, cwd=str(REMOTION_DIR), check=True)
        print("  [OK]   npm install 완료")
    except FileNotFoundError:
        print("  [WARN] npm 을 찾을 수 없습니다. 수동으로 실행하세요:")
        print("         cd remotion && npm install")
    except subprocess.CalledProcessError as e:
        print(f"  [WARN] npm install 실패 (exit {e.returncode})")
        print("         수동으로 실행하세요: cd remotion && npm install")


def _find_node_bin() -> Path | None:
    """NODEJS_BIN_DIR 또는 NODE_DIR 환경변수에서 Node 경로 탐색."""
    for env_key in ("NODEJS_BIN_DIR", "NODE_DIR"):
        val = os.environ.get(env_key)
        if val:
            p = Path(val)
            if (p / "npm").exists() or (p / "npm.cmd").exists():
                return p
    return None


# ── CLI ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="remotion/ 폴더 초기화/동기화")
    parser.add_argument("--src-only",    action="store_true", help="src/ 만 동기화")
    parser.add_argument("--fonts",       action="store_true", help="fonts 만 동기화")
    parser.add_argument("--no-install",  action="store_true", help="npm install 건너뜀")
    args = parser.parse_args()

    if args.src_only:
        sync_src_only()
    elif args.fonts:
        sync_fonts_only()
    else:
        full_setup(no_install=args.no_install)


if __name__ == "__main__":
    main()
