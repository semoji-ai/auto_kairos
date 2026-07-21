"""gpt-image-2 프롬프트 빌더 테스트 — 공냥 규격 준수 확인."""
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from auto_agent.tools.codex_prompt import SIZE_LOCK, build_codex_image_prompt, validate_prompt


def test_size_lock_table():
    assert SIZE_LOCK["16:9"] == "1792x1024"
    assert SIZE_LOCK["9:16"] == "1024x1792"
    assert SIZE_LOCK["1:1"] == "1024x1024"
    assert SIZE_LOCK["2:3"] == "1024x1536"


@patch("auto_agent.tools.codex_prompt._translate", side_effect=lambda t: t)
def test_prompt_ends_with_ar_token(mock_tr):
    prompt, size = build_codex_image_prompt("a lighthouse on a cliff", "warm watercolor", ar="16:9")
    assert prompt.rstrip().endswith("AR 16:9")
    assert size == "1792x1024"
    assert not prompt.startswith("[")  # 앞머리 브래킷 금지


@patch("auto_agent.tools.codex_prompt._translate", side_effect=lambda t: t)
def test_prompt_contains_style(mock_tr):
    prompt, _ = build_codex_image_prompt("a cat", "bold flat colors", ar="1:1")
    assert "bold flat colors" in prompt


def test_validate_prompt_absent_validator(tmp_path, monkeypatch):
    monkeypatch.setattr("auto_agent.tools.codex_prompt.VALIDATOR_PATH", tmp_path / "none.mjs")
    ok, msg = validate_prompt("hello AR 1:1")
    assert ok is True


@patch("auto_agent.tools.codex_prompt._translate", side_effect=lambda t: t)
def test_prompt_no_negatives_and_has_sections(mock_tr):
    prompt, _ = build_codex_image_prompt("a lighthouse on a cliff", "warm watercolor, #2A4D69 #F2E9DC", ar="4:3")
    assert "Scene:" in prompt
    assert "Camera:" in prompt
    assert "Lighting:" in prompt
    assert "Texture/Medium:" in prompt
    assert " no " not in prompt.lower()
    assert " without " not in prompt.lower()


def test_builder_output_passes_real_validator():
    """실제 check_prompt.mjs 검증기를 통과하는지 확인하는 통합 테스트.

    node/검증기가 없는 환경에서는 skip.
    """
    validator = Path.home() / ".claude/skills/image-prompt/scripts/check_prompt.mjs"
    node = shutil.which("node")
    if not node or not validator.exists():
        pytest.skip("node 또는 check_prompt.mjs 부재")

    with patch("auto_agent.tools.codex_prompt._translate", side_effect=lambda t: t):
        prompt, _size = build_codex_image_prompt(
            "a lighthouse on a rocky cliff at dawn, single figure standing near the railing",
            "warm watercolor illustration, soft paper texture, HEX #2A4D69 #F2E9DC #C97B4A",
            ar="4:3",
        )

    ok, msg = validate_prompt(prompt)
    assert ok is True, f"검증기 실패: {msg}"
