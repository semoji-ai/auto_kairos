"""
build_outline.py — v4 plan.md → v3 outline.json 변환기 (결정론적, 순수 함수).

v4 plan.md 구조 (실제 프로젝트 파일 기반):
  - YAML frontmatter: project_id, title, status
  - ## 한 줄 요약   → core_question
  - ## 분량 목표    → target_duration_minutes (숫자 파싱)
  - ### 구조 가설   → chapters[] (bullet list 파싱)

추론 기본값:
  - act: 챕터 위치에서 추론 (첫 챕터 → 1, 마지막 챕터 → 3, 나머지 → 2)
  - duration_ratio: 1/N 균등 분배 (구조 가설에 ~N분 힌트 있으면 비율 조정)
  - research_focus / key_points: 미해결 질문 섹션에서 추출 (없으면 [])
"""
from __future__ import annotations

import re
from typing import Any


# ─── Public API ───────────────────────────────────────────────────────────────

def build_outline(plan_md: str) -> dict[str, Any]:
    """Convert v4 plan.md text to v3 outline.json-compatible dict."""
    if not plan_md.strip():
        return {
            "title": "",
            "core_question": "",
            "target_duration_minutes": 0,
            "chapters": [],
        }

    title = _parse_title(plan_md)
    core_question = _parse_core_question(plan_md)
    target_duration_minutes = _parse_duration_minutes(plan_md)
    chapters = _parse_chapters(plan_md)

    return {
        "title": title,
        "core_question": core_question,
        "target_duration_minutes": target_duration_minutes,
        "chapters": chapters,
    }


# ─── Private helpers ──────────────────────────────────────────────────────────

def _parse_title(text: str) -> str:
    """Extract title from YAML frontmatter 'title:' or from first H1 heading.

    Frontmatter is scanned first, confined to the leading ---...--- block so that
    a 'title:' key appearing elsewhere in the document is not mistaken for metadata.
    Falls back to the first H1 heading when no frontmatter block is present.
    """
    # YAML frontmatter block (leading ---\n...\n---)
    fm = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if fm:
        m = re.search(r"^title:\s*(.+)$", fm.group(1), re.MULTILINE)
        if m:
            return m.group(1).strip()

    # Fallback: first H1 heading (e.g. # 기획안 — 주제)
    h1_match = re.search(r'^#\s+기획안\s*[—–-]\s*(.+)$', text, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    h1_plain = re.search(r'^#\s+(.+)$', text, re.MULTILINE)
    if h1_plain:
        return h1_plain.group(1).strip()

    return ""


def _parse_core_question(text: str) -> str:
    """Extract core_question from '## 한 줄 요약' section."""
    # Section after '## 한 줄 요약'
    match = re.search(
        r'##\s*한\s*줄\s*요약\s*\n+(.*?)(?=\n##|\Z)',
        text,
        re.DOTALL,
    )
    if match:
        content = match.group(1).strip()
        # Take first non-empty line
        for line in content.splitlines():
            line = line.strip()
            if line:
                return line
    return ""


def _parse_duration_minutes(text: str) -> float:
    """Extract target_duration_minutes from '## 분량 목표' section.

    Handles patterns like:
      "5-10분", "10-15분", "약 5분", "5분"
    Returns the midpoint when a range is given.
    """
    section_match = re.search(
        r'##\s*분량\s*목표\s*\n+(.*?)(?=\n##|\Z)',
        text,
        re.DOTALL,
    )
    if not section_match:
        return 0.0

    content = section_match.group(1)

    # Range: "5-10분" or "10~15분"
    # A section may contain multiple ranges (e.g. total "5-10분" AND per-chapter "2-4분").
    # We pick the range with the LARGEST midpoint, because total duration is always
    # >= per-chapter duration, so the largest midpoint corresponds to the total.
    range_matches = list(re.finditer(r'(\d+)\s*[-~]\s*(\d+)\s*분', content))
    if range_matches:
        best = max(range_matches, key=lambda m: (float(m.group(1)) + float(m.group(2))) / 2)
        lo = float(best.group(1))
        hi = float(best.group(2))
        return (lo + hi) / 2.0

    # Single value: "약 5분" or "5분"
    single_match = re.search(r'(\d+)\s*분', content)
    if single_match:
        return float(single_match.group(1))

    return 0.0


def _parse_chapters(text: str) -> list[dict[str, Any]]:
    """Extract chapters from '### 구조 가설' bullet list.

    Each bullet like:
      - 1막 (제목): 설명. ~N분
    yields a chapter dict.
    """
    section_match = re.search(
        r'###\s*구조\s*가설\s*\n+(.*?)(?=\n###|\n##|\Z)',
        text,
        re.DOTALL,
    )
    if not section_match:
        return []

    section = section_match.group(1)

    # Collect research_focus lines from '## 미해결 질문' for injection
    research_questions = _parse_research_questions(text)

    # Parse bullet lines (- 1막 ... or - N막 ...)
    bullet_pattern = re.compile(
        r'^[-*]\s*(\d+막)\s*(?:\(([^)]+)\))?\s*[:：]?\s*(.*)$',
        re.MULTILINE,
    )

    raw_chapters: list[dict] = []
    for m in bullet_pattern.finditer(section):
        act_str = m.group(1)      # e.g. "1막"
        title_paren = m.group(2)  # e.g. "약사 펨버턴의 실험실"
        description = m.group(3).strip()

        act_num = _act_number(act_str)

        # Title: prefer parenthesised label; fall back to first phrase of description
        if title_paren:
            chapter_title = title_paren.strip()
        else:
            chapter_title = description.split('.')[0].strip()

        raw_chapters.append({
            "act_num": act_num,
            "title": chapter_title,
            "purpose": description,
        })

    if not raw_chapters:
        return []

    n = len(raw_chapters)
    chapters = []
    for i, raw in enumerate(raw_chapters):
        chapter_number = i + 1

        # act inference: first → 1, last → 3 (if n≥3), middle → 2
        # Use explicit act_num from 막 label; only fall back if ambiguous
        act = raw["act_num"] if raw["act_num"] else _infer_act(i, n)

        # duration_ratio: equal split by default
        duration_ratio = round(1.0 / n, 4)

        # research_focus: round-robin distribution — chapter i gets questions[i::n].
        # This ensures even distribution regardless of len(questions) % n, unlike
        # integer-floor slicing which dumps all remainders onto the last chapter.
        research_focus = research_questions[i::n] if n else []

        chapters.append({
            "chapter_number": chapter_number,
            "title": raw["title"],
            "act": act,
            "purpose": raw["purpose"],
            "duration_ratio": duration_ratio,
            "research_focus": research_focus,
            "key_points": [],
        })

    # Normalise duration_ratio so it sums to exactly 1.0
    chapters = _normalise_duration_ratio(chapters)

    return chapters


def _parse_research_questions(text: str) -> list[str]:
    """Extract bullet questions from '## 미해결 질문' section."""
    match = re.search(
        r'##\s*미해결\s*질문.*?\n+(.*?)(?=\n##|\Z)',
        text,
        re.DOTALL,
    )
    if not match:
        return []

    questions = []
    for line in match.group(1).splitlines():
        line = line.strip()
        # Remove leading bullet markers
        line = re.sub(r'^[-*]\s*', '', line)
        if line and not line.startswith('#'):
            questions.append(line)
    return questions


def _act_number(막_str: str) -> int:
    """Convert '1막'/'2막'/'3막' to integer 1/2/3. Unknown → 0 (caller infers)."""
    digit_match = re.search(r'(\d+)', 막_str)
    if digit_match:
        n = int(digit_match.group(1))
        if 1 <= n <= 3:
            return n
    return 0


def _infer_act(index: int, total: int) -> int:
    """Infer act number from chapter position when 막 label is absent/ambiguous."""
    if total <= 1:
        return 1
    if index == 0:
        return 1
    if index == total - 1:
        return 3
    return 2


def _normalise_duration_ratio(chapters: list[dict]) -> list[dict]:
    """Adjust duration_ratio so the list sums to exactly 1.0."""
    if not chapters:
        return chapters
    total = sum(ch["duration_ratio"] for ch in chapters)
    if total == 0:
        equal = round(1.0 / len(chapters), 4)
        for ch in chapters:
            ch["duration_ratio"] = equal
        return chapters
    for ch in chapters:
        ch["duration_ratio"] = round(ch["duration_ratio"] / total, 4)
    # Fix floating-point rounding: adjust last chapter
    diff = round(1.0 - sum(ch["duration_ratio"] for ch in chapters), 4)
    if diff:
        chapters[-1]["duration_ratio"] = round(chapters[-1]["duration_ratio"] + diff, 4)
    return chapters
