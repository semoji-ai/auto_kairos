"""v4 PD 워크플로 산출물을 대시보드용으로 로드하는 헬퍼.

frontmatter 파싱 + 디렉토리별 .md 파일 lister + 통합 로더를 제공합니다.
모든 함수는 누락 파일·디렉토리에 대해 빈 값을 반환합니다 (조건부 노출 패턴).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """YAML frontmatter 블록을 dict로. 블록 없으면 빈 dict."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def strip_frontmatter(text: str) -> str:
    """frontmatter 블록을 제거한 본문 반환."""
    return _FRONTMATTER_RE.sub("", text, count=1)


def read_or_empty(path: Path) -> str:
    """파일 존재 시 본문, 아니면 빈 문자열."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


_DRAFT_RE = re.compile(r"^v(\d+)\.md$")
_REVIEW_RE = re.compile(r"^review-draft-v(\d+)-")


def list_md_files(directory: Path) -> list[dict[str, Any]]:
    """디렉토리 내 .md 파일을 frontmatter+본문으로 분리해 반환.

    파일은 슬러그(파일명 stem) 알파벳 순. 디렉토리 부재 시 빈 리스트.
    """
    if not directory.exists() or not directory.is_dir():
        return []
    out = []
    for f in sorted(directory.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        out.append({
            "slug": f.stem,
            "frontmatter": parse_frontmatter(text),
            "content": strip_frontmatter(text),
        })
    return out


def list_drafts(directory: Path) -> list[dict[str, Any]]:
    """drafts/v{n}.md 파일을 버전 번호 순으로 반환."""
    if not directory.exists() or not directory.is_dir():
        return []
    drafts = []
    for f in directory.glob("v*.md"):
        m = _DRAFT_RE.match(f.name)
        if not m:
            continue
        text = f.read_text(encoding="utf-8")
        drafts.append({
            "version": int(m.group(1)),
            "frontmatter": parse_frontmatter(text),
            "content": strip_frontmatter(text),
        })
    drafts.sort(key=lambda d: d["version"])
    return drafts


def parse_review_scores(review_dir: Path) -> list[dict[str, Any]]:
    """review/review-draft-v{n}-*.md 의 frontmatter에서 점수 추출."""
    if not review_dir.exists() or not review_dir.is_dir():
        return []
    scores = []
    for f in sorted(review_dir.glob("review-draft-v*.md")):
        m = _REVIEW_RE.match(f.name)
        if not m:
            continue
        fm = parse_frontmatter(f.read_text(encoding="utf-8"))
        scores.append({
            "version": int(m.group(1)),
            "viewer_score": fm.get("viewer_score"),
            "expert_verdict": fm.get("expert_verdict"),
        })
    scores.sort(key=lambda s: s["version"])
    return scores


def load_research_v4(project_dir: Path) -> dict[str, Any]:
    """v4 리서치 산출물 통합 로드. 키 모두 항상 존재 (없으면 빈 값)."""
    return {
        "plan_md": read_or_empty(project_dir / "plan.md"),
        "fresh_reports": list_md_files(project_dir / "research_reports"),
        "targeted": list_md_files(project_dir / "research_targeted"),
    }


def load_manuscript_v4(project_dir: Path) -> dict[str, Any]:
    """v4 원고 산출물 통합 로드."""
    return {
        "drafts": list_drafts(project_dir / "drafts"),
        "review_scores": parse_review_scores(project_dir / "review"),
        "final_manuscript": read_or_empty(project_dir / "final_manuscript.md"),
        "final_marked": read_or_empty(project_dir / "final_manuscript_marked.md"),
    }
