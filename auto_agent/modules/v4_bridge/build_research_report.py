"""v4 research artifacts → v3 research_report.json 변환기.

v4 research 결과물:
  - <project>/research_reports/*.md  (fresh-research / deep-research 산출물)
  - <project>/research_targeted/*.md (target-research 산출물)

v3 schema (schema_samples/research_report.example.json 기준):
  topic, summary, sections[], agent_results[], sources[], source_grades{}, agents_deployed, search_mode

품질 등급(quality_grade) 추론 정책:
  - v4 reports는 v3처럼 A/B/C 등급 체계를 사용하지 않는다.
  - frontmatter status=partial → "C", status=verified → "A", 나머지 default → "B"
  - Wikipedia URL 패턴이면 "A" (공개 백과사전, 위키피디아 자체 신뢰도 아님, runner.py 기존 관행)
  - target-research 산출물(질문 답변) → "B" (신뢰도 불명이지만 검증된 질문에 대한 답)

search_mode:
  - "v4-mixed" 고정값. v4는 fresh/deep/target을 자유롭게 조합하므로 단일 모드로 표현 불가.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")
_SECTION_SPLIT_RE = re.compile(r"^##\s+", re.MULTILINE)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """YAML-lite frontmatter 파싱 (PyYAML 의존성 없이 단순 key: value 처리)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def _strip_frontmatter(text: str) -> str:
    """본문에서 frontmatter 제거."""
    return _FRONTMATTER_RE.sub("", text, count=1)


def _infer_quality_grade(url: str, frontmatter_status: str) -> str:
    """URL 패턴과 frontmatter status로 품질 등급 추론."""
    if frontmatter_status == "verified":
        return "A"
    if frontmatter_status == "partial":
        return "C"
    if "wikipedia.org" in url:
        return "A"
    return "B"


def _extract_sections(body: str) -> list[dict[str, str]]:
    """마크다운 ## 헤딩 기준으로 섹션 분리.

    Returns list of {"title": str, "content": str}
    """
    parts = _SECTION_SPLIT_RE.split(body)
    sections: list[dict[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        title = lines[0].strip() if lines else ""
        content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        if title:
            sections.append({"title": title, "content": content})
    return sections


def _extract_sources(body: str, default_grade: str = "B", status: str = "") -> list[dict[str, str]]:
    """본문 마크다운 링크에서 출처 추출."""
    seen_urls: set[str] = set()
    sources: list[dict[str, str]] = []
    for m in _LINK_RE.finditer(body):
        title, url = m.group(1), m.group(2)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        grade = _infer_quality_grade(url, status)
        sources.append({"title": title, "url": url, "quality_grade": grade})
    return sources


def _build_source_grades(sources: list[dict[str, str]]) -> dict[str, int]:
    grades: dict[str, int] = {}
    for s in sources:
        g = s.get("quality_grade", "?")
        grades[g] = grades.get(g, 0) + 1
    return grades


def build_research_report(
    reports_dir: Path,
    targeted_dir: Path,
    *,
    topic: str = "",
) -> dict[str, Any]:
    """v4 research 결과물 → v3 research_report.json 스키마 dict 변환.

    Args:
        reports_dir: research_reports/ 디렉토리 (없어도 OK → 빈 처리)
        targeted_dir: research_targeted/ 디렉토리 (없어도 OK → 빈 처리)
        topic: 영상 주제 (plan.md 타이틀 등 caller가 주입)

    Returns:
        v3 research_report.json 스키마와 호환되는 dict
    """
    sections: list[dict[str, str]] = []
    agent_results: list[dict[str, str]] = []
    all_sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    agents_used: list[str] = []
    resolved_topic = topic

    # === research_reports/ 처리 ===
    reports_files: list[Path] = []
    if reports_dir and reports_dir.exists():
        reports_files = sorted(reports_dir.glob("*.md"))

    if reports_files:
        agents_used.append("fresh-research")
        for md_path in reports_files:
            raw = md_path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(raw)
            body = _strip_frontmatter(raw)

            # topic 추론 (첫 번째 파일에서)
            if not resolved_topic and fm.get("topic"):
                resolved_topic = fm["topic"]

            # 섹션 분리
            file_sections = _extract_sections(body)
            sections.extend(file_sections)

            # 출처 추출
            status = fm.get("status", "")
            for src in _extract_sources(body, status=status):
                if src["url"] not in seen_urls:
                    seen_urls.add(src["url"])
                    all_sources.append(src)

    # === research_targeted/ 처리 ===
    targeted_files: list[Path] = []
    if targeted_dir and targeted_dir.exists():
        targeted_files = sorted(targeted_dir.glob("*.md"))

    if targeted_files:
        agents_used.append("target-research")
        for md_path in targeted_files:
            raw = md_path.read_text(encoding="utf-8")
            fm = _parse_frontmatter(raw)
            body = _strip_frontmatter(raw)

            # targeted 파일은 agent_results로 분류 (질문-답변 형식)
            question = fm.get("question", md_path.stem)
            content_lines = [ln for ln in body.splitlines() if ln.strip()]
            content_preview = "\n".join(content_lines[:30])
            agent_results.append({"title": question, "content": content_preview})

            # 출처 추출 (targeted도 "B" 등급 기본)
            status = fm.get("status", "")
            for src in _extract_sources(body, status=status):
                if src["url"] not in seen_urls:
                    seen_urls.add(src["url"])
                    all_sources.append(src)

    # === summary: 첫 섹션 content 또는 빈 문자열 ===
    summary = sections[0]["content"] if sections else ""

    # === 조립 ===
    report: dict[str, Any] = {
        "topic": resolved_topic,
        "summary": summary,
        "sections": sections,
        "agent_results": agent_results,
        "sources": all_sources,
        "source_grades": _build_source_grades(all_sources),
        "agents_deployed": len(agents_used),
        "search_mode": "v4-mixed",
    }
    return report
