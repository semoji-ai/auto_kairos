from pathlib import Path

import pytest

from auto_agent.modules.source_ingest_module import _resolve_research_agent_paths


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
