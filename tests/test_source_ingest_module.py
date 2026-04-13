from pathlib import Path

import pytest

from auto_agent.modules.source_ingest_module import (
    _resolve_research_agent_paths,
    _validate_ingest_completion,
)


def _make_agent_dir(base: Path) -> Path:
    scripts = base / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "research_launcher.py").write_text("# launcher\n", encoding="utf-8")
    (scripts / "research_vault.py").write_text("# vault\n", encoding="utf-8")
    return base


def test_resolve_research_agent_paths_accepts_capitalized_dir(tmp_path):
    capitalized = _make_agent_dir(tmp_path / "ResearchAgent")
    _, launcher, vault_script = _resolve_research_agent_paths(candidate_dirs=[capitalized, tmp_path / "researchagent"])
    assert launcher == (capitalized / "scripts" / "research_launcher.py").resolve()
    assert vault_script == (capitalized / "scripts" / "research_vault.py").resolve()


def test_resolve_research_agent_paths_accepts_lowercase_dir(tmp_path):
    lowercase = _make_agent_dir(tmp_path / "researchagent")
    research_agent_dir, launcher, vault_script = _resolve_research_agent_paths(candidate_dirs=[tmp_path / "missing-research-agent", lowercase])
    assert research_agent_dir == lowercase.resolve()
    assert launcher == (lowercase / "scripts" / "research_launcher.py").resolve()
    assert vault_script == (lowercase / "scripts" / "research_vault.py").resolve()


def test_resolve_research_agent_paths_reports_checked_candidates(tmp_path):
    with pytest.raises(FileNotFoundError) as excinfo:
        _resolve_research_agent_paths(candidate_dirs=[tmp_path / "ResearchAgent", tmp_path / "researchagent"])
    message = str(excinfo.value)
    assert "ResearchAgent launcher를 찾지 못했습니다" in message
    assert str(tmp_path / "ResearchAgent" / "scripts" / "research_launcher.py") in message
    assert str(tmp_path / "researchagent" / "scripts" / "research_launcher.py") in message


def test_validate_ingest_completion_fails_when_claims_missing(tmp_path):
    research_root = tmp_path / "02-research"
    wiki_dir = research_root / "wiki" / "바세린"
    manifest_dir = research_root / "manifests" / "바세린"
    wiki_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    (wiki_dir / "overview.md").write_text("# overview\n" + ("x" * 600), encoding="utf-8")
    (manifest_dir / "claims.jsonl").write_text("", encoding="utf-8")

    result = _validate_ingest_completion(
        research_root=research_root,
        topic_slug="바세린의_역사",
        entity_slug="바세린",
        section_slug="역사",
        finalize_payload={
            "run_state": {"stage": "quality-assurance", "status": "blocked"},
            "snapshot": {"specialist_readiness": "seed_only"},
            "status": {"recommended_next_step": "strengthen-claim-set"},
        },
    )

    assert result["success"] is False
    assert result["claim_count"] == 0
    assert any("claim_count=0 < 3" in issue for issue in result["issues"])
    assert any("finalize-session not completed" in issue for issue in result["issues"])


def test_validate_ingest_completion_succeeds_with_packaged_run(tmp_path):
    research_root = tmp_path / "02-research"
    wiki_dir = research_root / "wiki" / "바세린"
    manifest_dir = research_root / "manifests" / "바세린"
    wiki_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    (wiki_dir / "역사.md").write_text("# 역사\n" + ("x" * 400), encoding="utf-8")
    (manifest_dir / "claims.jsonl").write_text("{}\n{}\n{}\n", encoding="utf-8")
    (manifest_dir / "sources.jsonl").write_text("{}\n{}\n", encoding="utf-8")

    result = _validate_ingest_completion(
        research_root=research_root,
        topic_slug="바세린의_역사",
        entity_slug="바세린",
        section_slug="역사",
        finalize_payload={
            "run_state": {"stage": "packaging", "status": "completed"},
            "snapshot": {"specialist_readiness": "usable"},
            "status": {"recommended_next_step": "complete"},
        },
    )

    assert result["success"] is True
    assert result["claim_count"] == 3
    assert result["source_count"] == 2
