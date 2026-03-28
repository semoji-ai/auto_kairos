"""에이전트 실행 래퍼 테스트."""
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from auto_agent.modules.agent_runner import AgentRunner


@pytest.fixture
def runner(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / "insights" / "planning").mkdir(parents=True)
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
    return AgentRunner()


class TestBuildPrompt:
    def test_trend_analyst_autonomous(self, runner):
        prompt = runner.build_trend_analyst_prompt(channel="이로미즘", seed=None)
        assert "이로미즘" in prompt
        assert "자율 모드" in prompt
        assert "기획안" in prompt

    def test_trend_analyst_seeded(self, runner):
        prompt = runner.build_trend_analyst_prompt(channel="이로미즘", seed="희토류 전쟁")
        assert "희토류 전쟁" in prompt
        assert "시드 모드" in prompt

    def test_performance_analyst_video(self, runner):
        prompt = runner.build_performance_analyst_prompt(
            mode="video", channel="이로미즘", video_id="abc123"
        )
        assert "abc123" in prompt
        assert "영상 성과" in prompt

    def test_performance_analyst_weekly(self, runner):
        prompt = runner.build_performance_analyst_prompt(
            mode="weekly", channel="이로미즘"
        )
        assert "주간 리뷰" in prompt


class TestBuildCommand:
    def test_build_claude_cmd(self, runner):
        cmd = runner._build_claude_cmd(model="sonnet", max_turns=40)
        assert "--model" in cmd
        assert "sonnet" in cmd
