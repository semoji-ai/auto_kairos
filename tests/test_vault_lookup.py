"""vault_lookup 단위 테스트 — NAS와 LLM 모두 mock."""
from __future__ import annotations

import json
from pathlib import Path

from auto_agent.research.vault_lookup import (
    _build_matcher_prompt,
    _parse_matcher_response,
    absorb_topic,
    match_vault_topics,
)


# ─────────────────────────────────────────────
# Matcher response 파싱
# ─────────────────────────────────────────────

def test_parse_matcher_response_valid():
    raw = """텍스트도 있어요
{
  "matches": [
    {"vault_slug": "유한양행", "confidence": 0.95, "rationale": "정확 일치"},
    {"vault_slug": "유일한", "confidence": 0.85, "rationale": "창업자 인물"}
  ]
}
"""
    out = _parse_matcher_response(raw)
    assert len(out) == 2
    assert out[0]["vault_slug"] == "유한양행"
    assert out[0]["confidence"] == 0.95


def test_parse_matcher_response_filters_low_confidence():
    raw = json.dumps({"matches": [
        {"vault_slug": "high", "confidence": 0.9},
        {"vault_slug": "mid", "confidence": 0.65},  # < 0.7 → drop
        {"vault_slug": "low", "confidence": 0.3},
    ]})
    out = _parse_matcher_response(raw)
    assert [m["vault_slug"] for m in out] == ["high"]


def test_parse_matcher_response_dedupes():
    raw = json.dumps({"matches": [
        {"vault_slug": "x", "confidence": 0.9},
        {"vault_slug": "x", "confidence": 0.85},  # dup → drop
    ]})
    out = _parse_matcher_response(raw)
    assert len(out) == 1


def test_parse_matcher_response_empty_array():
    out = _parse_matcher_response('{"matches": []}')
    assert out == []


def test_parse_matcher_response_no_json_raises():
    try:
        _parse_matcher_response("그냥 텍스트")
        assert False
    except ValueError:
        pass


# ─────────────────────────────────────────────
# match_vault_topics
# ─────────────────────────────────────────────

def test_match_topics_with_mock_invoker():
    def mock(prompt: str) -> str:
        # input에 queries/vault_topics 둘 다 들어가는지 가볍게 검증
        assert "queries" in prompt
        assert "vault_topics" in prompt
        return json.dumps({"matches": [
            {"vault_slug": "pepsi", "confidence": 0.95, "rationale": "정확"},
        ]})

    out = match_vault_topics(
        queries=["펩시", "Caleb Bradham"],
        vault_slugs=["pepsi", "coca_cola", "yuhan"],
        invoker=mock,
    )
    assert len(out) == 1
    assert out[0]["vault_slug"] == "pepsi"


def test_match_topics_returns_empty_on_invoker_error():
    def boom(prompt: str) -> str:
        raise RuntimeError("CLI not found")
    out = match_vault_topics(
        queries=["x"], vault_slugs=["y"], invoker=boom,
    )
    assert out == []


def test_match_topics_returns_empty_when_no_input():
    assert match_vault_topics([], ["pepsi"]) == []
    assert match_vault_topics(["펩시"], []) == []


# ─────────────────────────────────────────────
# absorb_topic
# ─────────────────────────────────────────────

def test_absorb_topic_copies_pages_when_vault_exists(tmp_path: Path, monkeypatch):
    # mock vault 구조
    fake_vault = tmp_path / "fake_vault" / "02-research"
    (fake_vault / "wiki" / "pepsi").mkdir(parents=True)
    (fake_vault / "wiki" / "pepsi" / "overview.md").write_text("# Overview\n", encoding="utf-8")
    (fake_vault / "wiki" / "pepsi" / "claims.md").write_text("# Claims\n", encoding="utf-8")
    (fake_vault / "manifests" / "pepsi").mkdir(parents=True)
    (fake_vault / "manifests" / "pepsi" / "claims.jsonl").write_text(
        '{"claim_id": "c1", "claim": "test"}\n', encoding="utf-8"
    )

    monkeypatch.setenv("KAIROS_VAULT_DIR", str(fake_vault))
    # cache invalidate
    from auto_agent.research import vault_lookup
    vault_lookup.get_vault_root.__wrapped__ if hasattr(vault_lookup.get_vault_root, "__wrapped__") else None

    project_research = tmp_path / "project" / "research"
    result = absorb_topic("pepsi", project_research)

    assert result["absorbed"] is True
    assert result["vault_slug"] == "pepsi"
    assert "overview.md" in result["files"]
    assert "claims.md" in result["files"]
    assert "claims.jsonl" in result["files"]

    # 실제 파일 복사 확인
    assert (project_research / "wiki" / "pepsi" / "overview.md").exists()
    assert (project_research / "manifests" / "pepsi" / "claims.jsonl").exists()


def test_absorb_topic_returns_false_when_vault_missing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("KAIROS_VAULT_DIR", "/nonexistent/path")
    result = absorb_topic("pepsi", tmp_path / "project" / "research")
    assert result["absorbed"] is False


def test_absorb_topic_handles_existing_target_with_vault_suffix(tmp_path: Path, monkeypatch):
    # vault에 overview.md 있고
    fake_vault = tmp_path / "fake_vault" / "02-research"
    (fake_vault / "wiki" / "pepsi").mkdir(parents=True)
    (fake_vault / "wiki" / "pepsi" / "overview.md").write_text("vault content", encoding="utf-8")
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(fake_vault))

    # 프로젝트에 이미 같은 이름 파일이 있을 때
    proj = tmp_path / "project" / "research"
    proj_wiki = proj / "wiki" / "pepsi"
    proj_wiki.mkdir(parents=True)
    (proj_wiki / "overview.md").write_text("project local content", encoding="utf-8")

    result = absorb_topic("pepsi", proj)
    assert result["absorbed"]
    # 원본은 보존되고 .vault.md로 따로 저장
    assert (proj_wiki / "overview.md").read_text(encoding="utf-8") == "project local content"
    assert (proj_wiki / "overview.vault.md").exists()
    assert "overview.vault.md" in result["files"]


# ─────────────────────────────────────────────
# Prompt 빌드
# ─────────────────────────────────────────────

def test_build_matcher_prompt_includes_inputs():
    p = _build_matcher_prompt(["펩시", "코카콜라"], ["pepsi", "yuhan"])
    assert "펩시" in p
    assert "pepsi" in p
    assert "yuhan" in p
    assert "<input>" in p
