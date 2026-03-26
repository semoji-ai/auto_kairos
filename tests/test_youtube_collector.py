"""YouTube 수집기 테스트 — API 응답 모킹."""
import re
from unittest.mock import MagicMock, patch

import pytest

from auto_agent.modules.data_collector.youtube_collector import YouTubeCollector


@pytest.fixture
def collector():
    with patch(
        "auto_agent.modules.data_collector.youtube_collector.YouTubeCollector._build_youtube_service"
    ) as mock_yt, patch(
        "auto_agent.modules.data_collector.youtube_collector.YouTubeCollector._build_analytics_service"
    ) as mock_analytics:
        mock_yt.return_value = MagicMock()
        mock_analytics.return_value = MagicMock()
        c = YouTubeCollector(
            client_id="test", client_secret="test", refresh_token="test"
        )
        yield c


class TestParseDuration:
    def test_minutes_and_seconds(self):
        assert YouTubeCollector._parse_duration("PT12M34S") == "12:34"

    def test_hours(self):
        assert YouTubeCollector._parse_duration("PT1H5M30S") == "65:30"

    def test_seconds_only(self):
        assert YouTubeCollector._parse_duration("PT45S") == "0:45"

    def test_empty(self):
        assert YouTubeCollector._parse_duration("") == "0:00"

    def test_invalid(self):
        assert YouTubeCollector._parse_duration("invalid") == "0:00"


class TestChannelVideos:
    def test_fetch_new_videos(self, collector):
        # Mock search().list().execute()
        search_mock = MagicMock()
        search_mock.execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid1"},
                    "snippet": {
                        "title": "테스트 영상",
                        "publishedAt": "2026-03-20T10:00:00Z",
                    },
                }
            ]
        }
        collector._youtube.search.return_value.list.return_value = search_mock

        # Mock videos().list().execute()
        videos_mock = MagicMock()
        videos_mock.execute.return_value = {
            "items": [
                {
                    "id": "vid1",
                    "snippet": {"title": "테스트 영상", "publishedAt": "2026-03-20T10:00:00Z"},
                    "contentDetails": {"duration": "PT12M34S"},
                    "statistics": {"viewCount": "1000", "likeCount": "50"},
                }
            ]
        }
        collector._youtube.videos.return_value.list.return_value = videos_mock

        videos = collector.fetch_channel_videos("UCxxxxxx", after="2026-03-19")
        assert len(videos) == 1
        assert videos[0]["video_id"] == "vid1"
        assert videos[0]["views"] == 1000
        assert videos[0]["duration"] == "12:34"

    def test_empty_results(self, collector):
        search_mock = MagicMock()
        search_mock.execute.return_value = {"items": []}
        collector._youtube.search.return_value.list.return_value = search_mock

        videos = collector.fetch_channel_videos("UCxxxxxx")
        assert len(videos) == 0


class TestCompetitorData:
    def test_fetch_competitor_info(self, collector):
        # Mock channels().list()
        ch_mock = MagicMock()
        ch_mock.execute.return_value = {
            "items": [
                {
                    "id": "UCxyz",
                    "snippet": {"title": "슈카월드", "description": "경제 채널"},
                    "statistics": {"subscriberCount": "1500000"},
                }
            ]
        }
        collector._youtube.channels.return_value.list.return_value = ch_mock

        # Mock search for recent videos
        search_mock = MagicMock()
        search_mock.execute.return_value = {"items": []}
        collector._youtube.search.return_value.list.return_value = search_mock

        info = collector.fetch_competitor_info("UCxyz")
        assert info["name"] == "슈카월드"
        assert info["subscribers"] == 1500000
