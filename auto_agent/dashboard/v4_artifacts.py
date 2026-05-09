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
