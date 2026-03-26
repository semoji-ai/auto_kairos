"""vault_writer 테스트 — 마크다운 생성, 프론트매터, 위키링크."""
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.vault_writer import VaultWriter
from auto_agent.modules.data_collector.dedup import DedupManager


@pytest.fixture
def vault_env(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    collector_dir = vault_dir / ".collector"
    collector_dir.mkdir()
    dedup = DedupManager(collector_dir=collector_dir)
    writer = VaultWriter(vault_dir=vault_dir, dedup=dedup)
    return writer, vault_dir


class TestVideoNote:
    def test_creates_video_note(self, vault_env):
        writer, vault_dir = vault_env
        videos_dir = vault_dir / "channels" / "이로미즘" / "videos"
        videos_dir.mkdir(parents=True)

        result = writer.write_video_note(
            channel="이로미즘",
            video_id="abc123",
            title="미국-이란 전쟁",
            published="2026-03-20",
            duration="12:34",
            views=58300,
            likes=1200,
            project_slug="us-iran-war",
        )

        assert result == "created"
        note_path = videos_dir / "미국-이란 전쟁.md"
        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert 'video_id: "abc123"' in content
        assert "channel: 이로미즘" in content
        assert "58,300" in content

    def test_skips_duplicate(self, vault_env):
        writer, vault_dir = vault_env
        videos_dir = vault_dir / "channels" / "이로미즘" / "videos"
        videos_dir.mkdir(parents=True)

        kwargs = dict(
            channel="이로미즘", video_id="abc123", title="테스트",
            published="2026-03-20", duration="5:00", views=100, likes=10,
        )
        result1 = writer.write_video_note(**kwargs)
        result2 = writer.write_video_note(**kwargs)
        assert result1 == "created"
        assert result2 == "skipped"

    def test_updates_changed(self, vault_env):
        writer, vault_dir = vault_env
        videos_dir = vault_dir / "channels" / "이로미즘" / "videos"
        videos_dir.mkdir(parents=True)

        writer.write_video_note(
            channel="이로미즘", video_id="abc123", title="테스트",
            published="2026-03-20", duration="5:00", views=100, likes=10,
        )
        result = writer.write_video_note(
            channel="이로미즘", video_id="abc123", title="테스트",
            published="2026-03-20", duration="5:00", views=500, likes=50,
        )
        assert result == "updated"


class TestTrendNote:
    def test_creates_daily_trend(self, vault_env):
        writer, vault_dir = vault_env
        trends_dir = vault_dir / "market" / "trends"
        trends_dir.mkdir(parents=True)

        result = writer.write_trend_note(
            date="2026-03-25",
            trends=[
                {"keyword": "희토류", "volume_change": "+180%", "region": "KR"},
                {"keyword": "AI 규제", "volume_change": "+50%", "region": "KR"},
            ],
        )

        assert result == "created"
        note_path = trends_dir / "2026-03-25-daily.md"
        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert "희토류" in content
        assert "+180%" in content


class TestCompetitorNote:
    def test_creates_competitor_note(self, vault_env):
        writer, vault_dir = vault_env
        comp_dir = vault_dir / "channels" / "competitors"
        comp_dir.mkdir(parents=True)

        result = writer.write_competitor_note(
            channel_id="UCxyz",
            name="슈카월드",
            category="경제/시사",
            subscribers=1500000,
            recent_videos=[
                {"title": "AI 버블론", "views": 120000, "published": "2026-03-22"},
            ],
        )

        assert result == "created"
        note_path = comp_dir / "슈카월드.md"
        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert "슈카월드" in content
        assert "1,500,000" in content


class TestAnalyticsNote:
    def test_creates_analytics_note(self, vault_env):
        writer, vault_dir = vault_env
        analytics_dir = vault_dir / "channels" / "이로미즘" / "analytics"
        analytics_dir.mkdir(parents=True)

        result = writer.write_analytics_note(
            channel="이로미즘",
            date="2026-03-25",
            metrics={"views": 5200, "subscribers_gained": 15, "avg_view_duration": "4:32"},
        )

        assert result == "created"
        note_path = analytics_dir / "2026-03-25.md"
        assert note_path.exists()
