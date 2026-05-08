"""Test build_art_style module."""
import pytest
from pathlib import Path
from auto_agent.modules.v4_bridge.build_art_style import build_art_style


class TestBuildArtStyle:
    """Tests for build_art_style function."""

    def test_build_art_style_loads_quirky_cartoon(self):
        """Test loading quirky_cartoon style with required keys."""
        result = build_art_style("quirky_cartoon")
        assert isinstance(result, dict)
        assert result.get("id") == "quirky_cartoon"
        assert "name" in result
        assert "design_tokens" in result
        assert "voice" in result

    def test_build_art_style_loads_semoji(self):
        """Test loading semoji style."""
        result = build_art_style("semoji")
        assert isinstance(result, dict)
        assert result.get("id") == "semoji"
        assert "design_tokens" in result

    def test_build_art_style_loads_lego(self):
        """Test loading lego style."""
        result = build_art_style("lego")
        assert isinstance(result, dict)
        assert result.get("id") == "lego"
        assert "design_tokens" in result

    def test_build_art_style_loads_stickman_cute(self):
        """Test loading stickman_cute style."""
        result = build_art_style("stickman_cute")
        assert isinstance(result, dict)
        assert result.get("id") == "stickman_cute"
        assert "design_tokens" in result

    def test_build_art_style_theme_override(self):
        """Test theme override."""
        result = build_art_style("quirky_cartoon", theme="light")
        assert result.get("design_tokens", {}).get("baseTheme") == "light"

    def test_build_art_style_voice_override(self):
        """Test voice_id override."""
        result = build_art_style("quirky_cartoon", voice_id="custom_voice_id")
        assert result.get("voice", {}).get("voice_id") == "custom_voice_id"

    def test_build_art_style_all_styles_loadable(self):
        """Test that all 4 known styles load without errors."""
        styles = ["quirky_cartoon", "semoji", "lego", "stickman_cute"]
        for style_id in styles:
            result = build_art_style(style_id)
            assert result.get("id") == style_id
            assert "design_tokens" in result

    def test_build_art_style_unknown_style_raises(self):
        """Test that unknown style_id raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            build_art_style("unknown_style_xyz")

    def test_build_art_style_both_overrides(self):
        """Test both theme and voice override together."""
        result = build_art_style(
            "semoji",
            theme="dark",
            voice_id="test_voice"
        )
        assert result.get("design_tokens", {}).get("baseTheme") == "dark"
        assert result.get("voice", {}).get("voice_id") == "test_voice"

    def test_build_art_style_default_artstyle_dir(self):
        """Test that default artstyle_dir resolves correctly."""
        # This should not raise an error about path resolution
        result = build_art_style("quirky_cartoon")
        assert result.get("id") == "quirky_cartoon"
