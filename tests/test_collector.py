"""수집 오케스트레이터 테스트."""
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest

from auto_agent.modules.data_collector.collector import DataCollector


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / ".collector").mkdir()
    # 볼트 구조 생성
    for d in [
        "channels/이로미즘/videos", "channels/이로미즘/analytics",
        "channels/세모지/videos", "channels/세모지/analytics",
        "channels/competitors", "market/trends", "market/social",
        "topics", "insights/planning", "insights/feedback", "insights/performance",
        "templates",
    ]:
        (vault_dir / d).mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_IROMISM", "UC_iromism")
    monkeypatch.setenv("YOUTUBE_CHANNEL_ID_SEMOJI", "UC_semoji")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/test")
    return vault_dir


class TestCollectorInit:
    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_creates_collector(self, mock_yt, mock_env):
        collector = DataCollector()
        assert collector._vault_dir == mock_env


class TestVideoTracking:
    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_register_video(self, mock_yt, mock_env):
        collector = DataCollector()
        collector.register_video_tracking("vid1", "test-project", "이로미즘")

        tracking = collector._load_video_tracking()
        assert len(tracking["tracking"]) == 1
        assert tracking["tracking"][0]["video_id"] == "vid1"
        assert "1d" in tracking["tracking"][0]["checkpoints"]
        assert "28d" in tracking["tracking"][0]["checkpoints"]

    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_get_due_checkpoints_none_today(self, mock_yt, mock_env):
        collector = DataCollector()
        collector.register_video_tracking("vid1", "test-project", "이로미즘")
        # 등록 직후에는 모든 체크포인트가 미래
        due = collector.get_due_checkpoints()
        assert len(due) == 0

    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_get_due_checkpoints_with_past_due(self, mock_yt, mock_env):
        collector = DataCollector()
        # 수동으로 과거 due date 주입
        tracking = {
            "tracking": [{
                "video_id": "vid1",
                "project_slug": "test",
                "channel": "이로미즘",
                "linked_at": "2026-03-20T00:00:00",
                "checkpoints": {
                    "1d": {"due": "2026-03-21", "status": "done"},
                    "3d": {"due": "2026-03-23", "status": "pending"},
                    "7d": {"due": "2026-03-27", "status": "pending"},
                    "28d": {"due": "2026-04-17", "status": "pending"},
                },
            }]
        }
        path = mock_env / ".collector" / "video_tracking.json"
        path.write_text(json.dumps(tracking), encoding="utf-8")

        due = collector.get_due_checkpoints()
        # 3d (03-23) should be due (today is 2026-03-26)
        assert any(d["checkpoint"] == "3d" for d in due)


class TestCollectAll:
    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_collect_all_handles_errors(self, mock_yt_cls, mock_env):
        mock_yt = MagicMock()
        mock_yt.fetch_channel_videos.side_effect = Exception("API error")
        mock_yt_cls.return_value = mock_yt

        collector = DataCollector()
        # Should not raise, should handle gracefully
        collector.collect_all()
