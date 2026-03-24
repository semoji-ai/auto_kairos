#!/usr/bin/env python3
"""기존 프로젝트 캐릭터 이미지를 글로벌 라이브러리로 마이그레이션.

사용법:
  python3 auto_agent/scripts/migrate_characters.py [--dry-run] [--output-root OUTPUT_DIR]

기본 output 디렉토리: WORKSPACE_DIR/output/
"""
import argparse
import json
import sys
from pathlib import Path

from auto_agent.paths import get_workspace_dir
from auto_agent.tools.character_library import CharacterLibrary, read_png_metadata


def migrate(output_root: Path, dry_run: bool = False) -> None:
    lib = CharacterLibrary()
    total, skipped, registered = 0, 0, 0

    for char_png in sorted(output_root.glob("*/characters/*.png")):
        total += 1
        meta = read_png_metadata(char_png)

        # PNG tEXt 없으면 건너뜀 (이전 방식으로 생성된 캐릭터)
        if not meta.get("character_name"):
            print(f"  [SKIP] tEXt 없음: {char_png}")
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] {meta['character_name']} / {meta.get('art_style')} -- {char_png.name}")
        else:
            record = lib.register(char_png, meta)
            print(f"  [REG] id={record.id} {record.name} / {record.art_style}")
            registered += 1

    print(f"\n총 {total}개 중 등록 {registered}개, 스킵 {skipped}개 (dry_run={dry_run})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    output_root = Path(args.output_root) if args.output_root else get_workspace_dir() / "output"
    if not output_root.exists():
        print(f"output 디렉토리 없음: {output_root}", file=sys.stderr)
        sys.exit(1)

    migrate(output_root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
