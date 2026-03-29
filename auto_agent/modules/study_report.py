"""스터디 결과 요약 + 스레드 보고 헬퍼."""
import os
import re
from pathlib import Path
from typing import Optional


def summarize_vault_file(file_path: str, max_chars: int = 1800) -> str:
    """볼트 마크다운 파일의 핵심 내용을 요약 추출."""
    p = Path(file_path)
    if not p.exists():
        return ""

    content = p.read_text(encoding="utf-8")
    lines = content.split("\n")

    # 제목 추출
    title = p.stem
    for l in lines:
        if l.startswith("# "):
            title = l.replace("# ", "")
            break

    # 섹션 헤더 + 첫 줄 추출
    sections = []
    for i, l in enumerate(lines):
        if l.startswith("## "):
            header = l.replace("## ", "")
            # 다음 비어있지 않은 줄 찾기
            preview = ""
            for j in range(i + 1, min(i + 5, len(lines))):
                stripped = lines[j].strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("|---"):
                    preview = stripped[:120]
                    break
            sections.append(f"**{header}**" + (f"\n  {preview}" if preview else ""))

    # 위키링크 추출
    wikilinks = list(set(re.findall(r'\[\[(.*?)\]\]', content)))

    # 파일 통계
    stats = f"📄 {p.name} ({len(content):,}자, {len(sections)}섹션)"

    # 조립
    result = f"**{title}**\n{stats}\n\n"

    if sections:
        result += "\n".join(sections[:15])  # 최대 15섹션

    if wikilinks:
        result += f"\n\n🔗 연결: {', '.join(f'[[{w}]]' for w in wikilinks[:10])}"

    return result[:max_chars]


def find_new_or_updated_files(vault_dir: str, category: str, since_minutes: int = 30) -> list:
    """최근 N분 내 생성/수정된 파일 찾기."""
    import time
    cutoff = time.time() - since_minutes * 60
    target = Path(vault_dir) / "solutioner" / category

    if not target.exists():
        return []

    result = []
    for f in target.rglob("*.md"):
        if f.stat().st_mtime >= cutoff:
            result.append(str(f))
    return sorted(result)


def report_study_results(notifier, vault_dir: str, round_topic: str, round_num: int, total: int):
    """라운드 완료 후 생성/수정된 파일 내용을 스레드에 보고."""
    # 최근 30분 내 변경된 파일 찾기
    all_files = []
    for cat in ["models", "tools", "patterns", "solutions", "daily"]:
        all_files.extend(find_new_or_updated_files(vault_dir, cat, since_minutes=30))

    if not all_files:
        notifier.send_to_thread(f"📝 **라운드 {round_num}/{total} 결과**: 파일 변경 없음")
        return

    notifier.send_to_thread(
        f"📝 **라운드 {round_num}/{total} 상세 결과** — {round_topic}\n"
        f"변경된 파일: {len(all_files)}개"
    )

    for fp in all_files:
        summary = summarize_vault_file(fp)
        if summary:
            notifier.send_to_thread(summary)


def report_index_update(notifier, vault_dir: str):
    """볼트 solutioner/ 전체 인덱스 현황 보고."""
    base = Path(vault_dir) / "solutioner"
    index = {}
    total_chars = 0
    total_links = 0

    for cat in ["models", "tools", "patterns", "solutions"]:
        cat_dir = base / cat
        if not cat_dir.exists():
            continue
        files = list(cat_dir.glob("*.md"))
        cat_chars = 0
        cat_links = 0
        for f in files:
            content = f.read_text(encoding="utf-8")
            cat_chars += len(content)
            cat_links += len(re.findall(r'\[\[.*?\]\]', content))
        index[cat] = {"files": len(files), "chars": cat_chars, "links": cat_links}
        total_chars += cat_chars
        total_links += cat_links

    lines = ["📊 **Solutioner 지식 베이스 현황**\n"]
    for cat, stats in index.items():
        lines.append(f"  `{cat}/` — {stats['files']}파일, {stats['chars']:,}자, {stats['links']}링크")
    lines.append(f"\n  **총합:** {sum(s['files'] for s in index.values())}파일, {total_chars:,}자, {total_links}위키링크")

    notifier.send_to_thread("\n".join(lines))
