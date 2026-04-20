"""볼트 기억 중요도 이동 시스템 — 활성 → 비활성 → 아카이브.

주 1회 실행 (일요일).
삭제 없음 — 벡터 인덱스에 영구 보존, 중요도만 이동.

Usage:
  python -m auto_agent.scripts.memory_maintenance
  python -m auto_agent.scripts.memory_maintenance --dry-run
"""
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", ""))
MEMORY_DIR = VAULT_DIR / "09-memory"

# 중요도 이동 기준
COMPRESS_AFTER_DAYS = 7     # 7일 후 압축
ARCHIVE_AFTER_DAYS = 90     # 90일 후 아카이브


def main():
    dry_run = "--dry-run" in sys.argv
    logger.info(f"=== 기억 중요도 이동 {'(dry-run)' if dry_run else ''} ===")

    if not MEMORY_DIR.exists():
        logger.error("볼트 미연결: %s", MEMORY_DIR)
        return

    now = datetime.now()

    # 1. 세션 기억 — 7일+ 압축, 90일+ 아카이브
    compressed, archived = _process_sessions(now, dry_run)
    logger.info(f"세션: {compressed}개 압축, {archived}개 아카이브")

    # 2. 결정 기억 — superseded 체크
    superseded = _process_decisions(now, dry_run)
    logger.info(f"결정: {superseded}개 superseded 표시")

    # 3. 패턴 기억 — confidence 체크
    demoted = _process_patterns(now, dry_run)
    logger.info(f"패턴: {demoted}개 중요도 하향")

    # 4. 벡터 인덱스 리빌드 (아카이브 포함)
    if not dry_run and (compressed + archived + superseded + demoted) > 0:
        _rebuild_index()

    logger.info("=== 기억 유지보수 완료 ===")


def _process_sessions(now: datetime, dry_run: bool) -> tuple:
    """세션 기억 중요도 이동."""
    sessions_dir = MEMORY_DIR / "sessions"
    archive_dir = MEMORY_DIR / "archive" / "sessions"
    if not sessions_dir.exists():
        return 0, 0

    compressed = 0
    archived = 0

    for md in sorted(sessions_dir.glob("*.md")):
        if md.name.startswith("_"):
            continue

        # 날짜 추출 (파일명: 2026-03-31-topic.md)
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', md.name)
        if not date_match:
            continue
        file_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
        age_days = (now - file_date).days

        content = md.read_text(encoding="utf-8")

        if age_days >= ARCHIVE_AFTER_DAYS:
            # 90일+ → 아카이브 이동
            if dry_run:
                logger.info(f"  [아카이브 예정] {md.name} ({age_days}일)")
            else:
                archive_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(md), str(archive_dir / md.name))
                logger.info(f"  [아카이브] {md.name} ({age_days}일)")
            archived += 1

        elif age_days >= COMPRESS_AFTER_DAYS:
            # 7일+ → 압축 (이미 압축됐으면 스킵)
            if "## 압축본" in content:
                continue  # 이미 압축됨

            summary = _compress_session(content)
            if dry_run:
                logger.info(f"  [압축 예정] {md.name} ({age_days}일) → {len(summary)}자")
            else:
                # 원본 보존 + 압축본 추가
                compressed_content = content + f"\n\n---\n## 압축본 ({now.strftime('%Y-%m-%d')})\n\n{summary}\n"
                md.write_text(compressed_content, encoding="utf-8")
                logger.info(f"  [압축] {md.name} ({age_days}일)")
            compressed += 1

    return compressed, archived


def _compress_session(content: str) -> str:
    """세션 내용을 핵심 3줄 + 미해결 항목으로 압축."""
    lines = content.split("\n")

    # 완료 항목 카운트
    completed = sum(1 for l in lines if "[x]" in l or "✅" in l)

    # 미해결 항목 추출
    unresolved = []
    in_unresolved = False
    for line in lines:
        lower = line.lower()
        if "미해결" in lower or "todo" in lower or "다음" in lower:
            in_unresolved = True
        elif in_unresolved and line.strip().startswith("- "):
            unresolved.append(line.strip()[:80])
        elif in_unresolved and line.startswith("##"):
            in_unresolved = False

    # 핵심 요약 (제목에서 추출)
    title = ""
    for line in lines:
        if line.startswith("# ") and not line.startswith("##"):
            title = line.replace("# ", "").strip()
            break

    summary = f"**{title}**\n"
    summary += f"완료: {completed}개\n"
    if unresolved:
        summary += "미해결:\n" + "\n".join(f"  {u}" for u in unresolved[:5])

    return summary


def _process_decisions(now: datetime, dry_run: bool) -> int:
    """결정 기억 — 같은 주제의 새 결정이 있으면 이전 것을 superseded 표시."""
    decisions_dir = MEMORY_DIR / "decisions"
    if not decisions_dir.exists():
        return 0

    # 주제별 최신 결정 찾기
    topic_latest = {}
    for md in decisions_dir.glob("*.md"):
        if md.name.startswith("_"):
            continue
        content = md.read_text(encoding="utf-8")
        # 제목에서 주제 추출
        title_match = re.search(r'title:\s*"([^"]+)"', content)
        if title_match:
            topic = title_match.group(1)
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})', md.name)
            file_date = date_match.group(1) if date_match else "0000-00-00"

            if topic not in topic_latest or file_date > topic_latest[topic]["date"]:
                topic_latest[topic] = {"date": file_date, "path": md}

    # 이전 결정에 superseded 표시
    superseded = 0
    for md in decisions_dir.glob("*.md"):
        if md.name.startswith("_"):
            continue
        content = md.read_text(encoding="utf-8")
        if "status: superseded" in content:
            continue

        title_match = re.search(r'title:\s*"([^"]+)"', content)
        if not title_match:
            continue
        topic = title_match.group(1)

        if topic in topic_latest and str(topic_latest[topic]["path"]) != str(md):
            if dry_run:
                logger.info(f"  [superseded 예정] {md.name}")
            else:
                content = content.replace("status: active", "status: superseded", 1)
                if "status: superseded" not in content:
                    content = content.replace("---\n\n", "status: superseded\n---\n\n", 1)
                md.write_text(content, encoding="utf-8")
            superseded += 1

    return superseded


def _process_patterns(now: datetime, dry_run: bool) -> int:
    """패턴 기억 — 오래된 패턴의 중요도 하향 (반증이 있으면)."""
    # 현재는 패턴이 적어서 수동 관리. 향후 자동화.
    return 0


def _rebuild_index():
    """벡터 인덱스 리빌드."""
    try:
        import subprocess
        workspace = Path(__file__).resolve().parent.parent.parent
        subprocess.run(
            [sys.executable, "-m", "auto_agent.modules.memory_index", "build"],
            cwd=str(workspace), timeout=120,
            capture_output=True,
        )
        logger.info("벡터 인덱스 리빌드 완료")
    except Exception as e:
        logger.warning(f"인덱스 리빌드 실패: {e}")


if __name__ == "__main__":
    main()
