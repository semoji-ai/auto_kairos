# tests/test_vault_rag_path.py
import os
from pathlib import Path
from unittest.mock import patch
import pytest


def test_env_var_overrides_all(tmp_path):
    """KAIROS_VAULT_DIR 환경변수가 설정되면 해당 경로를 반환한다."""
    custom = str(tmp_path / "my-vault")
    with patch.dict(os.environ, {"KAIROS_VAULT_DIR": custom}):
        import auto_agent.orchestrator.vault_rag as vr
        result = vr._resolve_vault_dir()
    assert str(result) == custom


def test_prefers_projects_when_exists(tmp_path):
    """Projects/kairos-vault가 존재하면 Desktop보다 우선한다."""
    projects_vault = tmp_path / "Projects" / "kairos-vault"
    projects_vault.mkdir(parents=True)
    desktop_vault = tmp_path / "Desktop" / "kairos-vault"
    desktop_vault.mkdir(parents=True)

    env = {k: v for k, v in os.environ.items() if k != "KAIROS_VAULT_DIR"}
    with patch.dict(os.environ, env, clear=True):
        with patch("auto_agent.orchestrator.vault_rag.Path.home", return_value=tmp_path):
            from importlib import reload
            import auto_agent.orchestrator.vault_rag as vr
            result = vr._resolve_vault_dir()
    assert result == projects_vault


def test_falls_back_to_desktop(tmp_path, capsys):
    """Projects가 없고 Desktop이 있으면 Desktop을 반환한다."""
    desktop_vault = tmp_path / "Desktop" / "kairos-vault"
    desktop_vault.mkdir(parents=True)

    env = {k: v for k, v in os.environ.items() if k != "KAIROS_VAULT_DIR"}
    with patch.dict(os.environ, env, clear=True):
        with patch("auto_agent.orchestrator.vault_rag.Path.home", return_value=tmp_path):
            import auto_agent.orchestrator.vault_rag as vr
            result = vr._resolve_vault_dir()
    assert result == desktop_vault
    captured = capsys.readouterr()
    assert "Desktop" in captured.out or "Desktop" in captured.err


def test_defaults_to_projects_when_neither_exists(tmp_path):
    """둘 다 없으면 Projects 경로를 기본값으로 반환한다."""
    env = {k: v for k, v in os.environ.items() if k != "KAIROS_VAULT_DIR"}
    with patch.dict(os.environ, env, clear=True):
        with patch("auto_agent.orchestrator.vault_rag.Path.home", return_value=tmp_path):
            import auto_agent.orchestrator.vault_rag as vr
            result = vr._resolve_vault_dir()
    assert result == tmp_path / "Projects" / "kairos-vault"
