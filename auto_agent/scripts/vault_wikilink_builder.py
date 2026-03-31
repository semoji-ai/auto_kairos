"""볼트 위키링크 크로스 연동 — 기존 노트 간 누락된 위키링크 자동 발견 + 추가.

주 1회 실행. 볼트 전체를 스캔하여:
1. 제목/키워드 기반으로 관련 노트 발견
2. 아직 위키링크가 없는 관계를 찾아 "관련 노트" 섹션에 추가
3. 인덱스 파일 카운트 업데이트

Usage:
  python -m auto_agent.scripts.vault_wikilink_builder
  python -m auto_agent.scripts.vault_wikilink_builder --dry-run
"""
import json
import logging
import os
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

VAULT_DIR = Path(os.environ.get(
    "KAIROS_VAULT_DIR",
    "/Volumes/kairos/kairos_vault/kairos-vault",
))

# 스캔 대상 디렉토리
SCAN_DIRS = [
    "02-research/topics",
    "03-analysis/videos",
    "channels/semoji/videos",
    "channels/iromism/videos",
    "insights/performance",
    "insights/feedback",
    "insights/planning",
    "09-memory/sessions",
    "09-memory/decisions",
    "09-memory/patterns",
    "solutioner/daily",
]

# 키워드 추출용 — 2글자 이상 한글 명사
MIN_KEYWORD_LEN = 2
# 위키링크 연결 최소 키워드 겹침
MIN_OVERLAP = 3


def main():
    dry_run = "--dry-run" in sys.argv
    logger.info(f"=== 위키링크 크로스 연동 시작 {'(dry-run)' if dry_run else ''} ===")

    # 1. 전체 노트 수집 + 키워드 추출
    notes = _collect_notes()
    logger.info(f"스캔 완료: {len(notes)}개 노트")

    # 2. 키워드 인버트 인덱스 구축
    keyword_index = _build_keyword_index(notes)
    logger.info(f"키워드 인덱스: {len(keyword_index)}개 키워드")

    # 3. 관련 노트 쌍 발견
    pairs = _find_related_pairs(notes, keyword_index)
    logger.info(f"관련 노트 쌍: {len(pairs)}개 발견")

    # 4. 기존 위키링크 확인 → 누락된 것만 추가
    new_links = _filter_existing_links(pairs, notes)
    logger.info(f"새 위키링크: {len(new_links)}개")

    if dry_run:
        for src, targets in list(new_links.items())[:10]:
            print(f"  {Path(src).stem} → {[Path(t).stem for t in targets]}")
        return

    # 5. 위키링크 추가
    added = _add_wikilinks(new_links, notes)
    logger.info(f"위키링크 {added}개 추가 완료")


def _collect_notes() -> Dict[str, dict]:
    """볼트 노트 수집 + 메타데이터."""
    notes = {}
    for scan_dir in SCAN_DIRS:
        dir_path = VAULT_DIR / scan_dir
        if not dir_path.exists():
            continue
        for md in dir_path.glob("*.md"):
            if md.name.startswith("_"):
                continue
            text = md.read_text(encoding="utf-8")
            nfc = unicodedata.normalize("NFC", text)

            # 프론트매터 파싱
            title = md.stem
            tags = []
            if nfc.startswith("---"):
                end = nfc.find("---", 3)
                if end > 0:
                    fm = nfc[3:end]
                    for line in fm.split("\n"):
                        if line.strip().startswith("title:"):
                            title = line.split(":", 1)[1].strip().strip('"')
                        if line.strip().startswith("- "):
                            tags.append(line.strip()[2:])

            # 키워드 추출
            keywords = set(re.findall(r'[가-힣]{2,}', nfc))
            # 영문 키워드도 (3글자 이상)
            keywords.update(w.lower() for w in re.findall(r'[A-Za-z]{3,}', nfc))

            # 기존 위키링크 수집
            existing_links = set(re.findall(r'\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]', nfc))

            notes[str(md)] = {
                "path": str(md),
                "stem": md.stem,
                "title": title,
                "tags": tags,
                "keywords": keywords,
                "existing_links": existing_links,
                "dir": scan_dir,
            }
    return notes


def _build_keyword_index(notes: dict) -> Dict[str, Set[str]]:
    """키워드 → 노트 경로 인버트 인덱스."""
    index = defaultdict(set)
    for path, meta in notes.items():
        for kw in meta["keywords"]:
            if len(kw) >= MIN_KEYWORD_LEN:
                index[kw].add(path)
    return index


def _find_related_pairs(notes: dict, keyword_index: dict) -> List[Tuple[str, str, int]]:
    """관련 노트 쌍 발견 (키워드 겹침 기반)."""
    pairs = []
    paths = list(notes.keys())

    for i, p1 in enumerate(paths):
        kw1 = notes[p1]["keywords"]
        candidates = defaultdict(int)
        for kw in kw1:
            if kw in keyword_index:
                for p2 in keyword_index[kw]:
                    if p2 != p1:
                        candidates[p2] += 1

        for p2, overlap in candidates.items():
            if overlap >= MIN_OVERLAP:
                # 같은 디렉토리 내 연결은 스킵 (이미 있을 가능성 높음)
                if notes[p1]["dir"] == notes[p2]["dir"]:
                    continue
                pairs.append((p1, p2, overlap))

    return pairs


def _filter_existing_links(pairs: list, notes: dict) -> Dict[str, List[str]]:
    """기존 위키링크가 없는 쌍만 필터."""
    new_links = defaultdict(list)
    for p1, p2, overlap in pairs:
        stem2 = notes[p2]["stem"]
        if stem2 not in notes[p1]["existing_links"]:
            new_links[p1].append(p2)

    # 각 노트당 최대 5개 새 링크
    return {k: v[:5] for k, v in new_links.items()}


def _add_wikilinks(new_links: dict, notes: dict) -> int:
    """노트에 "관련 노트" 섹션 추가/업데이트."""
    added = 0
    for src_path, targets in new_links.items():
        src = Path(src_path)
        content = src.read_text(encoding="utf-8")

        # "## 크로스 연동" 섹션이 있으면 거기에 추가, 없으면 끝에 추가
        links_text = "\n## 크로스 연동\n\n"
        for t in targets:
            stem = notes[t]["stem"]
            title = notes[t]["title"][:40]
            links_text += f"- [[{stem}]] — {title}\n"

        if "## 크로스 연동" in content:
            # 기존 섹션에 추가
            for t in targets:
                stem = notes[t]["stem"]
                if f"[[{stem}]]" not in content:
                    title = notes[t]["title"][:40]
                    # 섹션 끝에 추가
                    content = content.replace("## 크로스 연동\n", f"## 크로스 연동\n- [[{stem}]] — {title}\n", 1)
                    added += 1
        else:
            content += links_text
            added += len(targets)

        src.write_text(content, encoding="utf-8")

    return added


if __name__ == "__main__":
    main()
