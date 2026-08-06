#!/usr/bin/env python3
"""확정 원고를 구글 문서로 올린다.

문서에는 **성우가 읽을 나레이션만** 남긴다. `<!-- caption/chars/source -->`
같은 제작용 주석은 화면에서 빼고 댓글로 붙인다 (사용자 요청 방식).

    python3 scripts/push_to_gdocs.py --map <map.tsv> --dir <원고폴더> [--dry-run]
    python3 scripts/push_to_gdocs.py --map <map.tsv> --dir <원고폴더> --only EP01

map.tsv 형식(탭 구분): 문서ID<TAB>문서제목<TAB>원고파일명
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

COMMENT = re.compile(r"<!--\s*(caption|chars|source)\s*:\s*(.*?)\s*-->", re.DOTALL)
SEP = re.compile(r"^-{3,}\s*$", re.MULTILINE)


def build_paragraphs(md: str) -> tuple[list[str], list[tuple[int, str]], set[int]]:
    """원고 마크다운 → (문단 목록, [(문단 인덱스, 댓글내용), ...], 제목 문단 인덱스)

    Drive API의 comments.create는 앵커를 못 만들어 문서에 표시되지 않는다.
    그래서 .docx로 만들어 올린다 — docx는 댓글과 앵커를 포맷 자체에 담고,
    구글 드라이브가 변환할 때 그대로 가져온다.

    챕터 제목(`# Ch1. ...`)은 반드시 **별도 문단**으로 뽑는다. 뒤 나레이션과
    한 문단에 묶이면 장 경계가 사라진다.
    """
    paragraphs: list[str] = []
    comments: list[tuple[int, str]] = []
    headings: set[int] = set()

    def push(text: str, *, heading: bool = False) -> int:
        if paragraphs:
            paragraphs.append("")
        idx = len(paragraphs)
        paragraphs.append(text)
        if heading:
            headings.add(idx)
        return idx

    for chunk in SEP.split(md):
        lines = chunk.strip("\n").split("\n")
        body_lines: list[str] = []
        pending: list[str] = []

        for ln in lines:
            if ln.startswith("#"):
                # 앞에 쌓인 본문을 먼저 내보내고 제목을 독립 문단으로
                text = "\n".join(x.replace("**", "") for x in body_lines if x.strip()).strip()
                if text:
                    idx = push(text)
                    for c in pending:
                        comments.append((idx, c))
                    pending = []
                body_lines = []
                push(ln.lstrip("# ").strip(), heading=True)
                continue

            m = COMMENT.search(ln)
            if m:
                kind, value = m.group(1), m.group(2)
                label = {"caption": "자막", "chars": "인물", "source": "출처"}[kind]
                pending.append(f"[{label}] {value}")
                rest = COMMENT.sub("", ln).strip()
                if rest:
                    body_lines.append(rest)
                continue
            body_lines.append(ln)

        text = "\n".join(x.replace("**", "") for x in body_lines if x.strip()).strip()
        if not text:
            # 제목만 있던 덩어리 — 댓글이 남았으면 제목 문단에 붙인다
            if pending and paragraphs:
                for c in pending:
                    comments.append((len(paragraphs) - 1, c))
            continue

        idx = push(text)
        for c in pending:
            comments.append((idx, c))

    return paragraphs, comments, headings


def _legacy_build_body(md: str) -> tuple[str, list[tuple[str, str]]]:
    """(구) 평문 본문 + 앵커 문장 방식 — 앵커 댓글이 안 보여 쓰지 않는다."""
    comments: list[tuple[str, str]] = []
    out_lines: list[str] = []

    for chunk in SEP.split(md):
        lines = chunk.strip("\n").split("\n")
        body_lines: list[str] = []
        pending: list[str] = []

        for ln in lines:
            m = COMMENT.search(ln)
            if m:
                kind, value = m.group(1), m.group(2)
                label = {"caption": "자막", "chars": "인물", "source": "출처"}[kind]
                pending.append(f"[{label}] {value}")
                rest = COMMENT.sub("", ln).strip()
                if rest:
                    body_lines.append(rest)
                continue
            body_lines.append(ln)

        # 강조 표시(**)와 챕터 머리(#)는 낭독 대본에 불필요 — 제거
        clean = []
        for ln in body_lines:
            if ln.startswith("#"):
                clean.append(ln.lstrip("# ").strip())
                continue
            clean.append(ln.replace("**", ""))
        text = "\n".join(x for x in clean if x.strip())

        if not text.strip():
            continue

        if pending:
            anchor = next(
                (x for x in reversed(text.split("\n")) if len(x.strip()) >= 6),
                text.strip().split("\n")[0],
            )
            comments.append((anchor.strip(), "\n".join(pending)))

        out_lines.append(text)

    return "\n\n".join(out_lines) + "\n", comments


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", required=True, type=Path)
    ap.add_argument("--dir", required=True, type=Path)
    ap.add_argument("--only", help="특정 원고 파일만 (예: EP01)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-comments", action="store_true", help="본문만 올리고 댓글은 생략")
    args = ap.parse_args()

    rows = []
    for line in args.map.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        doc_id, title, fname = line.split("\t")
        rows.append((doc_id, title, fname))

    if args.only:
        rows = [r for r in rows if r[2].startswith(args.only)]

    if not args.dry_run:
        from googleapiclient.http import MediaFileUpload

        from auto_agent.tools import gdocs
        from auto_agent.tools.docx_comments import build_docx

        _, drive = gdocs._services()

    tmp_dir = Path("/tmp/gdocs_push")
    tmp_dir.mkdir(exist_ok=True)

    total_c = 0
    for doc_id, title, fname in rows:
        path = args.dir / fname
        if not path.exists():
            print(f"✗ {fname} 없음")
            continue

        paragraphs, comments, headings = build_paragraphs(path.read_text(encoding="utf-8"))
        chars = sum(len(re.sub(r"\s", "", p)) for p in paragraphs)
        print(f"{title[:38]:40s} {chars:5,}자  댓글 {len(comments):3d}", end="")

        if args.dry_run:
            print("  (dry-run)")
            continue

        docx = build_docx(
            paragraphs,
            [] if args.no_comments else comments,
            tmp_dir / f"{fname}.docx",
            headings=headings,
        )

        # 같은 문서 ID에 docx를 덮어쓴다 — 링크와 공유 설정이 유지된다.
        # (새로 만들면 문서가 중복된다)
        media = MediaFileUpload(
            str(docx),
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            resumable=False,
        )
        drive.files().update(
            fileId=doc_id,
            body={"name": title},
            media_body=media,
        ).execute()

        total_c += 0 if args.no_comments else len(comments)
        print(f"  → 덮어쓰기 완료")
        time.sleep(0.3)

    print(f"\n총 댓글 {total_c}개 (docx 앵커 방식)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
