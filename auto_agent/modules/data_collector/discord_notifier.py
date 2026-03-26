"""Discord 웹훅 알림."""
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord 웹훅으로 알림 발송."""

    MAX_LENGTH = 2000

    def __init__(self, webhook_url: str):
        self._url = webhook_url

    def send(self, message: str) -> bool:
        if not self._url:
            logger.warning("Discord 웹훅 URL이 설정되지 않음 — 알림 스킵")
            return False
        try:
            resp = requests.post(
                self._url,
                json={"content": message[:self.MAX_LENGTH]},
                timeout=10,
            )
            if resp.status_code in (200, 204):
                return True
            logger.error("Discord 알림 실패: %d %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.error("Discord 알림 에러: %s", e)
            return False

    def format_planning(self, channel: str, date: str, topics: List[Dict]) -> str:
        lines = [f"📋 **{channel} 일일 기획안** ({date})", ""]
        for i, t in enumerate(topics, 1):
            lines.append(f"{i}. **{t['title']}**")
            lines.append(f"   {t.get('reason', '')} · 예상 {t.get('estimate', '?')}")
            lines.append("")
        return "\n".join(lines)

    def format_video_performance(
        self, title: str, days: int, views: int, ctr: float,
        avg_watch: str, duration: str,
    ) -> str:
        return "\n".join([
            f"📊 **{title}** {days}일 성과",
            "",
            f"조회수: {views:,}",
            f"CTR: {ctr}%",
            f"평균 시청: {avg_watch} / {duration}",
        ])

    def format_weekly_review(
        self, channel: str, week: str, total_views: int,
        views_change: str, top_video: str,
        approvals_needed: Optional[List[str]] = None,
    ) -> str:
        lines = [
            f"📈 **{channel} 주간 리뷰** ({week})",
            "",
            f"총 조회수: {total_views:,} ({views_change})",
            f"최고 성과: {top_video}",
        ]
        if approvals_needed:
            lines += ["", "⚡ **승인 필요**"]
            for item in approvals_needed:
                lines.append(f"• {item}")
        return "\n".join(lines)

    def format_error(self, source: str, error: str) -> str:
        return f"⚠️ **수집 오류** [{source}]\n{error}"
