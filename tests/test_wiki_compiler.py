"""wiki_compiler 단위 테스트 — LLM은 mock invoker로 대체."""
from __future__ import annotations

import json
from pathlib import Path

from auto_agent.research.wiki_compiler import (
    _parse_synthesis_response,
    _read_raw_excerpts,
    compile_topic,
    render_claims_md,
    render_index_md,
)


# ─────────────────────────────────────────────
# render_claims_md
# ─────────────────────────────────────────────

def test_render_claims_md_empty():
    out = render_claims_md([], "pepsi")
    assert "doc_type:" in out
    assert "page_type: claims" in out
    assert "기록된 claim이 없습니다" in out


def test_render_claims_md_with_claims():
    claims = [
        {
            "claim_id": "claim_1933",
            "claim": "안티푸라민 1933 출시",
            "kind": "fact",
            "tier": "A",
            "confidence": "high",
            "source_ids": ["src_yuhan_official", "src_wikipedia_ko"],
            "evidence": "공식 연혁 기록",
        }
    ]
    out = render_claims_md(claims, "유한양행")
    assert "## claim_1933" in out
    assert "안티푸라민 1933 출시" in out
    assert "tier: `A`" in out
    assert "src_yuhan_official, src_wikipedia_ko" in out


# ─────────────────────────────────────────────
# render_index_md
# ─────────────────────────────────────────────

def test_render_index_md_groups_by_tier():
    sources = [
        {"source_id": "s1", "title": "위키 자료", "url": "https://ko.wikipedia.org/x", "lane": "wikipedia", "tier_hint": "A", "publisher": "Wikipedia"},
        {"source_id": "s2", "title": "학술 논문", "url": "https://doi.org/10.x", "lane": "crossref", "tier_hint": "B"},
        {"source_id": "s3", "title": "블로그", "url": "https://blog.example.com", "lane": "google_news_rss", "tier_hint": "unknown"},
    ]
    out = render_index_md(sources, "pepsi")
    assert "## Tier A (1건)" in out
    assert "## Tier B (1건)" in out
    assert "## Tier unknown (1건)" in out
    assert "위키 자료" in out
    assert "_Wikipedia_" in out  # publisher italic
    assert "https://doi.org/10.x" in out


def test_render_index_md_empty():
    out = render_index_md([], "pepsi")
    assert "수집된 소스가 없습니다" in out


# ─────────────────────────────────────────────
# synthesis 응답 파싱
# ─────────────────────────────────────────────

def test_parse_synthesis_response_valid():
    raw = """
{
  "overview": "# Overview\\n\\n펩시는...",
  "entities": "# Entities\\n\\n## Caleb Bradham",
  "timeline": "# Timeline\\n\\n**1898** — Pepsi 창업"
}
"""
    out = _parse_synthesis_response(raw)
    assert "Overview" in out["overview"]
    assert "Caleb Bradham" in out["entities"]
    assert "1898" in out["timeline"]


def test_parse_synthesis_response_partial():
    """3개 중 2개만 있어도 받음."""
    raw = json.dumps({"overview": "# A", "entities": ""})
    # entities 비어있으니 drop. 그래도 overview 1개 있으면 ok.
    raw_with_text = '{"overview": "충분히 긴 본문 내용"}'
    out = _parse_synthesis_response(raw_with_text)
    assert "overview" in out
    assert "entities" not in out


def test_parse_synthesis_response_no_json():
    try:
        _parse_synthesis_response("그냥 텍스트")
        assert False
    except ValueError:
        pass


def test_parse_synthesis_response_all_empty():
    try:
        _parse_synthesis_response('{"overview": "", "entities": "", "timeline": ""}')
        assert False
    except ValueError:
        pass


# ─────────────────────────────────────────────
# raw excerpts 읽기
# ─────────────────────────────────────────────

def test_read_raw_excerpts_skips_frontmatter(tmp_path: Path):
    run_dir = tmp_path / "raw_topic" / "20260429"
    notes_dir = run_dir / "source_notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "src_a.md").write_text(
        "---\nsource_id: src_a\ntitle: foo\n---\n\n본문 내용입니다. 짧지만 충분.",
        encoding="utf-8",
    )
    excerpts = _read_raw_excerpts(tmp_path / "raw_topic")
    assert len(excerpts) == 1
    assert "본문 내용입니다" in excerpts[0]
    assert "source_id" not in excerpts[0]  # frontmatter 제거됨


def test_read_raw_excerpts_missing_dir(tmp_path: Path):
    excerpts = _read_raw_excerpts(tmp_path / "nonexistent")
    assert excerpts == []


# ─────────────────────────────────────────────
# compile_topic — 통합
# ─────────────────────────────────────────────

def test_compile_topic_skip_synthesis(tmp_path: Path):
    """skip_synthesis=True — claims.md / index.md만 생성, LLM 안 부름."""
    research = tmp_path / "research"
    (research / "manifests" / "pepsi").mkdir(parents=True)
    (research / "manifests" / "pepsi" / "sources.jsonl").write_text(
        json.dumps({"source_id": "s1", "title": "Pepsi wiki", "tier_hint": "A", "url": "https://x"}) + "\n",
        encoding="utf-8",
    )
    (research / "manifests" / "pepsi" / "claims.jsonl").write_text(
        json.dumps({"claim_id": "c1", "claim": "Pepsi est. 1898", "tier": "A"}) + "\n",
        encoding="utf-8",
    )

    result = compile_topic("pepsi", research, skip_synthesis=True)
    assert "claims.md" in result["written"]
    assert "index.md" in result["written"]
    assert len(result["skipped"]) == 3  # overview/entities/timeline
    assert (research / "wiki" / "pepsi" / "claims.md").exists()
    assert (research / "wiki" / "pepsi" / "index.md").exists()


def test_compile_topic_with_mock_synthesis(tmp_path: Path):
    research = tmp_path / "research"
    (research / "manifests" / "pepsi").mkdir(parents=True)
    (research / "manifests" / "pepsi" / "sources.jsonl").write_text(
        json.dumps({"source_id": "s1", "title": "Pepsi wiki", "tier_hint": "A"}) + "\n",
        encoding="utf-8",
    )

    def mock_invoker(prompt: str) -> str:
        assert "topic_slug" in prompt
        return json.dumps({
            "overview": "# Pepsi Overview\n\n전체 요약",
            "entities": "# Entities\n\n## Caleb Bradham",
            "timeline": "# Timeline\n\n**1898** — 창업",
        })

    result = compile_topic("pepsi", research, invoker=mock_invoker)
    assert "overview.md" in result["written"]
    assert "entities.md" in result["written"]
    assert "timeline.md" in result["written"]
    assert (research / "wiki" / "pepsi" / "overview.md").read_text(encoding="utf-8").startswith("---\n")


def test_compile_topic_synthesis_failure_logged(tmp_path: Path):
    research = tmp_path / "research"
    (research / "manifests" / "pepsi").mkdir(parents=True)
    (research / "manifests" / "pepsi" / "sources.jsonl").write_text(
        json.dumps({"source_id": "s1", "title": "x", "tier_hint": "A"}) + "\n",
        encoding="utf-8",
    )

    def boom(prompt: str) -> str:
        raise RuntimeError("CLI not found")

    result = compile_topic("pepsi", research, invoker=boom)
    # claims/index는 항상 생성, 합성만 실패
    assert "claims.md" in result["written"]
    assert "index.md" in result["written"]
    assert len(result["errors"]) == 1
    assert result["errors"][0]["phase"] == "synthesis"


def test_compile_topic_no_data_skips_synthesis(tmp_path: Path):
    """sources + claims 둘 다 비어있으면 synthesis 호출 자체 안 함."""
    research = tmp_path / "research"
    (research / "manifests" / "pepsi").mkdir(parents=True)

    def fail(prompt: str) -> str:
        raise AssertionError("호출되면 안 됨")

    result = compile_topic("pepsi", research, invoker=fail)
    assert "claims.md" in result["written"]
    assert len(result["errors"]) == 1
    assert "비어있어" in result["errors"][0]["reason"]
