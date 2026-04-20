"""Discord 알림 테스트 — 웹훅 호출 모킹."""
from unittest.mock import patch, MagicMock

import pytest

from auto_agent.modules.data_collector.discord_notifier import DiscordNotifier


@pytest.fixture
def notifier():
    return DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test/test")


class TestFormatting:
    def test_format_planning_message(self, notifier):
        msg = notifier.format_planning(
            channel="이로미즘",
            date="03-25",
            topics=[
                {"title": "희토류 전쟁", "reason": "검색량 +180%", "estimate": "50~90K"},
            ],
        )
        assert "이로미즘" in msg
        assert "희토류 전쟁" in msg

    def test_format_video_performance(self, notifier):
        msg = notifier.format_video_performance(
            title="미국-이란 전쟁",
            days=7,
            views=42000,
            ctr=7.1,
            avg_watch="5:48",
            duration="12:34",
        )
        assert "7일" in msg
        assert "42,000" in msg

    def test_format_weekly_review(self, notifier):
        msg = notifier.format_weekly_review(
            channel="이로미즘",
            week="W12",
            total_views=125000,
            views_change="+12%",
            top_video="미국-이란 전쟁",
            approvals_needed=["trial→정규: 어쩌다어른"],
        )
        assert "W12" in msg
        assert "125,000" in msg
        assert "승인" in msg

    def test_format_error(self, notifier):
        msg = notifier.format_error("youtube", "API 할당량 초과")
        assert "youtube" in msg
        assert "할당량" in msg


class TestSend:
    @patch("auto_agent.modules.data_collector.discord_notifier.requests")
    def test_send_calls_webhook(self, mock_requests, notifier):
        mock_requests.post.return_value = MagicMock(status_code=204)
        result = notifier.send("테스트 메시지")
        assert result is True
        mock_requests.post.assert_called_once()

    @patch("auto_agent.modules.data_collector.discord_notifier.requests")
    def test_send_failure(self, mock_requests, notifier):
        mock_requests.post.return_value = MagicMock(status_code=500, text="error")
        result = notifier.send("테스트")
        assert result is False

    def test_send_no_url(self):
        notifier = DiscordNotifier(webhook_url="")
        result = notifier.send("테스트")
        assert result is False
