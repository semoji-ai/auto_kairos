"""dedup 모듈 테스트 — 워터마크, 해시 DB, upsert 판단."""
import json
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.dedup import (
    DedupManager,
    UpsertAction,
)


@pytest.fixture
def dedup(tmp_path):
    return DedupManager(collector_dir=tmp_path)


class TestWatermark:
    def test_get_returns_none_when_missing(self, dedup):
        assert dedup.get_watermark("youtube_analytics", "이로미즘") is None

    def test_set_and_get(self, dedup):
        dedup.set_watermark("youtube_analytics", "이로미즘", {"last_date": "2026-03-24"})
        result = dedup.get_watermark("youtube_analytics", "이로미즘")
        assert result["last_date"] == "2026-03-24"

    def test_persistence(self, dedup):
        dedup.set_watermark("trends", "global", {"last_fetch": "2026-03-25"})
        dedup2 = DedupManager(collector_dir=dedup._collector_dir)
        assert dedup2.get_watermark("trends", "global")["last_fetch"] == "2026-03-25"


class TestHashDB:
    def test_check_new_content(self, dedup):
        action = dedup.check("youtube_video", "abc123", "hello world")
        assert action == UpsertAction.CREATE

    def test_check_same_content(self, dedup):
        dedup.record("youtube_video", "abc123", "hello world", "videos/test.md")
        action = dedup.check("youtube_video", "abc123", "hello world")
        assert action == UpsertAction.SKIP

    def test_check_changed_content(self, dedup):
        dedup.record("youtube_video", "abc123", "hello world", "videos/test.md")
        action = dedup.check("youtube_video", "abc123", "hello world updated")
        assert action == UpsertAction.UPDATE

    def test_get_note_path(self, dedup):
        dedup.record("youtube_video", "abc123", "hello", "videos/test.md")
        assert dedup.get_note_path("youtube_video", "abc123") == "videos/test.md"
