"""vault_sync wiki 페이지 통합(머지) 테스트."""
from __future__ import annotations

import json
from pathlib import Path

from auto_agent.research.vault_sync import (
    _merge_entities_md,
    _merge_log_md,
    _merge_overview_md,
    _merge_timeline_md,
    _merge_wiki_page,
)


# ─────────────────────────────────────────────
# entities 머지 — 헤더 단위 dedup
# ─────────────────────────────────────────────

def test_merge_entities_dedup_header():
    old = """---
title: x
---

# Entities

### Robert Chesebrough
- 역할: 바세린 발명가

### Indra Nooyi
- 역할: PepsiCo CEO
"""
    new = """---
title: y
updated_at: 2026-04-29
---

# Entities

### Robert Chesebrough
- 역할: 바세린 발명가
- 추가 정보: 1859년 펜실베이니아에서 발견

### John Sculley
- 역할: 펩시 마케팅 임원
"""
    out = _merge_entities_md(old, new)
    assert "Robert Chesebrough" in out
    assert "Indra Nooyi" in out  # 옛에만 있던 것 보존
    assert "John Sculley" in out  # 새에서 온 것
    assert out.count("### Robert Chesebrough") == 1  # dedup
    # 더 긴 본문(새 버전) 채택
    assert "1859년 펜실베이니아" in out
    # 새 frontmatter 우선
    assert "2026-04-29" in out


def test_merge_entities_empty_old():
    new = "# Entities\n\n### A\n- info"
    out = _merge_entities_md("", new)
    assert "### A" in out


def test_merge_entities_empty_new():
    old = "# Entities\n\n### A\n- info"
    out = _merge_entities_md(old, "")
    assert "### A" in out


# ─────────────────────────────────────────────
# timeline 머지 — 연도 dedup + 정렬
# ─────────────────────────────────────────────

def test_merge_timeline_dedup_and_sort():
    old = """# Timeline

- **1898** — Pepsi 창업
- **1923** — 1차 파산
"""
    new = """# Timeline

- **1898** — Pepsi 창업 (Caleb Bradham)
- **1934** — 12온스 5센트 전략
- **1985** — New Coke 사고
"""
    out = _merge_timeline_md(old, new)
    # 모든 연도 포함
    for year in ("1898", "1923", "1934", "1985"):
        assert f"**{year}" in out
    # 1898은 1번만 (dedup)
    assert out.count("**1898") == 1
    # 정렬 — 1898이 1923보다 먼저, 1985가 마지막
    pos_1898 = out.find("**1898")
    pos_1985 = out.find("**1985")
    assert pos_1898 < pos_1985


def test_merge_timeline_preserves_headers():
    old = "# Timeline\n\n## Section A\n\n- **1900** — event"
    new = "## Section A\n\n- **2000** — event"
    out = _merge_timeline_md(old, new)
    assert "# Timeline" in out


# ─────────────────────────────────────────────
# log 머지 — append
# ─────────────────────────────────────────────

def test_merge_log_appends_entry():
    old = "# Log\n\n## Sync Events\n- [2026-04-01] sync from project_a\n"
    new = "# Log\n"
    out = _merge_log_md(old, new, "project_b")
    assert "project_a" in out  # 옛 항목 유지
    assert "project_b" in out  # 새 항목 추가


def test_merge_log_creates_when_empty():
    out = _merge_log_md("", "", "test_project")
    assert "test_project" in out
    assert "Sync Events" in out


# ─────────────────────────────────────────────
# overview LLM 머지 (mock invoker)
# ─────────────────────────────────────────────

def test_merge_overview_with_mock_invoker():
    old = "---\ntitle: x\n---\n\n# Overview\n\n옛 자료의 핵심 사실 5건."
    new = "---\ntitle: x\nupdated_at: 2026-04-29\n---\n\n# Overview\n\n새 자료의 핵심 사실 7건."

    def mock_llm(prompt: str) -> str:
        assert "old_overview" in prompt
        assert "new_overview" in prompt
        return "# Overview\n\n옛 자료 5건 + 새 자료 7건 통합 12건."

    out = _merge_overview_md(old, new, invoker=mock_llm)
    assert "통합 12건" in out
    # frontmatter는 새 것 우선
    assert "2026-04-29" in out


def test_merge_overview_fallback_on_llm_error():
    old = "옛 본문 5건"
    new = "새 본문 7건"

    def boom(prompt: str) -> str:
        raise RuntimeError("CLI 실패")

    out = _merge_overview_md(old, new, invoker=boom)
    # fallback 동작: 새 본문 + 옛 본문 보존 섹션
    assert "새 본문 7건" in out
    assert "옛 본문 5건" in out
    assert "통합 실패" in out


def test_merge_overview_empty_old_returns_new():
    out = _merge_overview_md("", "new content", invoker=lambda p: "should not be called")
    assert out == "new content"


def test_merge_overview_empty_new_returns_old():
    out = _merge_overview_md("old content", "", invoker=lambda p: "should not be called")
    assert out == "old content"


# ─────────────────────────────────────────────
# 디스패처
# ─────────────────────────────────────────────

def test_merge_wiki_page_dispatches(tmp_path: Path):
    old = tmp_path / "old.md"
    new = tmp_path / "new.md"
    old.write_text("- **1900** — old", encoding="utf-8")
    new.write_text("- **2000** — new", encoding="utf-8")

    out = _merge_wiki_page("timeline.md", old, new)
    assert "1900" in out and "2000" in out


def test_merge_wiki_page_claims_replaces(tmp_path: Path):
    old = tmp_path / "old.md"
    new = tmp_path / "new.md"
    old.write_text("OLD CLAIMS", encoding="utf-8")
    new.write_text("NEW CLAIMS", encoding="utf-8")
    out = _merge_wiki_page("claims.md", old, new)
    # claims는 새 버전으로 교체 (manifests에서 이미 dedup됨)
    assert out == "NEW CLAIMS"
