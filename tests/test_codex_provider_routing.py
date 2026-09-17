import os
import pytest
from unittest.mock import patch

from auto_agent.orchestrator.runner import resolve_agent_provider

FLESH_DEF = {"provider": "codex"}


def test_default_codex_from_agents_json():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("AUTO_AGENT_RESEARCH_PROVIDER", None)
        assert resolve_agent_provider("flesh-researcher", FLESH_DEF, {}) == "codex"


def test_env_overrides_agents_json():
    with patch.dict(os.environ, {"AUTO_AGENT_RESEARCH_PROVIDER": "claude"}):
        assert resolve_agent_provider("targeted-researcher", FLESH_DEF, {}) == "claude"


def test_project_config_overrides_env():
    with patch.dict(os.environ, {"AUTO_AGENT_RESEARCH_PROVIDER": "claude"}):
        assert resolve_agent_provider("flesh-researcher", FLESH_DEF, {"research_provider": "codex"}) == "codex"


def test_non_research_agent_can_select_codex():
    assert resolve_agent_provider("script-director", {"provider": "codex"}, {}) == "codex"


def test_invalid_value_fails_explicitly():
    with pytest.raises(ValueError, match="Unknown provider"):
        resolve_agent_provider("flesh-researcher", {"provider": "gemini"}, {})
