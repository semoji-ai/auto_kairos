from unittest.mock import patch

from auto_agent.modules.image_batch_module import _resolve_image_backend


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_default_codex(mock_av, monkeypatch):
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    assert _resolve_image_backend() == "codex"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_env_fal(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "fal")
    assert _resolve_image_backend() == "fal"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=False)
def test_degrade_to_fal_when_codex_missing(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "codex")
    assert _resolve_image_backend() == "fal"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_invalid_value_default_codex(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "midjourney")
    assert _resolve_image_backend() == "codex"
