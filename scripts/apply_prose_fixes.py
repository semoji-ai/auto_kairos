#!/usr/bin/env python3
"""비문 검토 보고서의 원문→수정 쌍을 원고에 기계 치환한다.

손으로 옮기면 원본이 남아 중복이 되거나 오타가 섞인다. 보고서를 파싱해
정확히 1회씩만 치환하고, 매칭 실패는 건너뛰되 전부 보고한다.

    python3 scripts/apply_prose_fixes.py <보고서.md> [보고서2.md ...] \
        --manuscripts <원고폴더> [--dry-run]

종료 코드: 0 = 전건 적용, 1 = 미적용 항목 있음
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ### EP01  또는  ### EP01_제목
EP_HEAD = re.compile(r"^#{2,4}\s*EP\s*(\d+)", re.MULTILINE)
# 1. **원문**: ...  **문제**: ...  **수정**: ...
ITEM = re.compile(
    r"\*\*원문\*\*\s*[:：]\s*(?P<old>.+?)\s*\n\s*\*\*문제\*\*\s*[:：].*?\n\s*\*\*수정\*\*\s*[:：]\s*(?P<new>.+?)(?=\n\s*\n|\n\s*\d+\.\s*\*\*원문\*\*|\n#{2,4}\s*EP|\Z)",
    re.DOTALL,
)


def parse_report(path: Path) -> dict[int, list[tuple[str, str]]]:
    """편 번호 → [(원문, 수정), ...]"""
    text = path.read_text(encoding="utf-8")
    sections: dict[int, list[tuple[str, str]]] = {}

    marks = [(m.start(), int(m.group(1))) for m in EP_HEAD.finditer(text)]
    if not marks:
        return sections

    for idx, (pos, ep) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(text)
        body = text[pos:end]
        pairs = []
        for m in ITEM.finditer(body):
            old = m.group("old").strip()
            new = m.group("new").strip()
            # 인용부호로 감싼 경우 벗겨낸다
            for q in ('"', "“", "”"):
                if old.startswith(q) and old.endswith(q):
                    old = old[1:-1].strip()
            if old and new and old != new:
                pairs.append((old, new))
        if pairs:
            sections.setdefault(ep, []).extend(pairs)
    return sections


def find_manuscript(folder: Path, ep: int) -> Path | None:
    hits = sorted(folder.glob(f"EP{ep:02d}_*.md"))
    return hits[0] if hits else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("reports", nargs="+", type=Path)
    ap.add_argument("--manuscripts", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    merged: dict[int, list[tuple[str, str]]] = {}
    for rep in args.reports:
        for ep, pairs in parse_report(rep).items():
            merged.setdefault(ep, []).extend(pairs)

    total = applied = missed = ambiguous = 0
    failures: list[str] = []

    for ep in sorted(merged):
        path = find_manuscript(args.manuscripts, ep)
        if path is None:
            failures.append(f"EP{ep:02d}: 원고 파일 없음")
            continue

        text = path.read_text(encoding="utf-8")
        ep_applied = ep_missed = ep_amb = 0

        for old, new in merged[ep]:
            total += 1
            count = text.count(old)
            if count == 1:
                text = text.replace(old, new, 1)
                ep_applied += 1
            elif count == 0:
                ep_missed += 1
                failures.append(f"EP{ep:02d} 미매칭: {old[:60]}")
            else:
                ep_amb += 1
                failures.append(f"EP{ep:02d} 중복매칭({count}회): {old[:60]}")

        applied += ep_applied
        missed += ep_missed
        ambiguous += ep_amb

        flag = "" if (ep_missed or ep_amb) else " ✓"
        print(
            f"EP{ep:02d} {path.name:32s} 적용 {ep_applied:3d}"
            f"  미매칭 {ep_missed:2d}  중복 {ep_amb:2d}{flag}"
        )

        if not args.dry_run and ep_applied:
            path.write_text(text, encoding="utf-8")

    print(f"\n합계 {total}건 중 적용 {applied} / 미매칭 {missed} / 중복매칭 {ambiguous}")
    if args.dry_run:
        print("(dry-run — 파일을 쓰지 않았습니다)")

    if failures:
        print("\n-- 수동 확인 필요 --")
        for f in failures:
            print(" ", f)

    return 0 if (missed == 0 and ambiguous == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
