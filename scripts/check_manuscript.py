#!/usr/bin/env python3
"""원고 정합성 검사기 — 편집 사고를 사람 눈 대신 기계가 잡는다.

문자열 교체로 원고를 고칠 때 원본을 안 지워 같은 내용이 두 번 남는 사고가
반복돼 만들었다. 평가에 넘기기 전, 녹음에 넘기기 전 반드시 통과시킬 것.

    python3 scripts/check_manuscript.py <원고.md> [원고2.md ...]
    python3 scripts/check_manuscript.py --dir output/.../manuscripts_13ep

종료 코드: 0 = 이상 없음, 1 = 문제 발견
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

# 나레이션 한 블록 = '---' 로 구분되는 한 덩어리
BLOCK_SEP = re.compile(r"^-{3,}\s*$", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
CHAPTER = re.compile(r"^#\s+(.*)$", re.MULTILINE)

# 유사도 이 값 이상이면 중복 의심. 0.90은 조사·어미만 바뀐 재작성까지 잡는다.
NEAR_DUP_RATIO = 0.90
# 이 글자 수 미만은 비교 대상에서 뺀다 ("그런데", "---" 같은 연결어)
MIN_LEN = 12
# 근접 중복만 본다. 멀리 떨어진 의도적 반복(후렴)은 사고가 아니다.
NEAR_WINDOW = 12


def normalize(text: str) -> str:
    """비교용 정규화 — 강조 기호, 공백, 문장부호 차이를 무시."""
    text = COMMENT.sub("", text)
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[*_`#]", "", text)
    text = re.sub(r"[\s]+", "", text)
    text = re.sub(r"[.,!?~…·\"'“”‘’]", "", text)
    return text


def split_blocks(text: str) -> list[tuple[int, str]]:
    """(줄번호, 블록원문) 목록. 챕터 제목 줄은 블록에서 제외."""
    blocks: list[tuple[int, str]] = []
    line_no = 1
    for chunk in BLOCK_SEP.split(text):
        body = "\n".join(
            ln for ln in chunk.split("\n") if not ln.startswith("#")
        ).strip()
        if body:
            blocks.append((line_no, body))
        line_no += chunk.count("\n") + 1
    return blocks


def find_duplicates(blocks: list[tuple[int, str]]) -> list[str]:
    """근접 구간의 동일·유사 블록을 찾는다."""
    issues: list[str] = []
    norms = [(ln, raw, normalize(raw)) for ln, raw in blocks]

    for i, (ln_a, raw_a, norm_a) in enumerate(norms):
        if len(norm_a) < MIN_LEN:
            continue
        for ln_b, raw_b, norm_b in norms[i + 1 : i + 1 + NEAR_WINDOW]:
            if len(norm_b) < MIN_LEN:
                continue
            if norm_a == norm_b:
                issues.append(
                    f"  L{ln_a}/L{ln_b} 완전 중복: {raw_a[:60]}…"
                )
                continue
            ratio = SequenceMatcher(None, norm_a, norm_b).ratio()
            if ratio >= NEAR_DUP_RATIO:
                issues.append(
                    f"  L{ln_a}/L{ln_b} 유사 {ratio:.0%}:\n"
                    f"      A: {raw_a[:70]}\n"
                    f"      B: {raw_b[:70]}"
                )
    return issues


def check_chapters(text: str) -> list[str]:
    """챕터 번호가 건너뛰거나 중복되지 않는지."""
    issues: list[str] = []
    titles = CHAPTER.findall(text)
    nums: list[int] = []
    for t in titles:
        m = re.match(r"Ch(\d+)\.", t.strip())
        if m:
            nums.append(int(m.group(1)))
    for idx, n in enumerate(nums, start=1):
        if n != idx:
            issues.append(
                f"  챕터 번호 불연속: {idx}번째 챕터가 Ch{n} (Ch{idx} 이어야 함)"
            )
            break
    if len(set(nums)) != len(nums):
        issues.append("  챕터 번호 중복")
    return issues


def check_markers(text: str) -> list[str]:
    """주석 마커 문법 검사."""
    issues: list[str] = []
    for m in COMMENT.finditer(text):
        body = m.group(0)[4:-3].strip()
        # caption = 화면 자막, chars = 인물 식별, source = 출처 주석(비렌더)
        if not re.match(r"(caption|chars|source):", body):
            issues.append(f"  알 수 없는 마커: {body[:50]}")
    # 닫히지 않은 주석
    if text.count("<!--") != text.count("-->"):
        issues.append("  주석이 닫히지 않음 (<!-- 와 --> 개수 불일치)")
    return issues


def narration_chars(text: str) -> int:
    stripped = COMMENT.sub("", text)
    return len(re.sub(r"[#\-*\n\s]", "", stripped))


def check_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    blocks = split_blocks(text)

    issues: list[str] = []
    issues += find_duplicates(blocks)
    issues += check_chapters(text)
    issues += check_markers(text)

    n = narration_chars(text)
    head = f"{path.name}  {n:,}자 / 약 {n/350:.1f}분 / {len(blocks)}블록"

    if issues:
        print(f"✗ {head}")
        for line in issues:
            print(line)
        return False

    print(f"✓ {head}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--dir", type=Path, help="폴더 내 EP*.md 전체 검사")
    args = ap.parse_args()

    targets = list(args.files)
    if args.dir:
        targets += sorted(p for p in args.dir.glob("*.md") if "backup" not in p.name)

    if not targets:
        ap.error("검사할 원고를 지정하세요 (파일 또는 --dir)")

    ok = all(check_file(p) for p in targets)
    if not ok:
        print("\n중복이 발견되면 교체 편집 중 원본을 안 지운 것입니다. 해당 줄을 확인하세요.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
