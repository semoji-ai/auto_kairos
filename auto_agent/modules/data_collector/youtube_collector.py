"""YouTube Data API + Analytics API 수집."""
import re
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class YouTubeCollector:
    """YouTube 채널/영상/Analytics 데이터 수집."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=self.SCOPES,
        )
        self._youtube = self._build_youtube_service()
        self._analytics = self._build_analytics_service()

    def _build_youtube_service(self):
        return build("youtube", "v3", credentials=self._credentials)

    def _build_analytics_service(self):
        return build("youtubeAnalytics", "v2", credentials=self._credentials)

    def fetch_channel_videos(
        self, channel_id: str, after: Optional[str] = None, max_results: int = 10
    ) -> List[Dict]:
        """채널의 최근 영상 목록 + 통계."""
        params = {
            "channelId": channel_id,
            "part": "id,snippet",
            "order": "date",
            "maxResults": max_results,
            "type": "video",
        }
        if after:
            params["publishedAfter"] = f"{after}T00:00:00Z"

        search_result = self._youtube.search().list(**params).execute()
        video_ids = [item["id"]["videoId"] for item in search_result.get("items", [])]

        if not video_ids:
            return []

        details = (
            self._youtube.videos()
            .list(part="snippet,contentDetails,statistics", id=",".join(video_ids))
            .execute()
        )

        videos = []
        for item in details.get("items", []):
            videos.append({
                "video_id": item["id"],
                "title": item["snippet"]["title"],
                "published": item["snippet"].get("publishedAt", ""),
                "duration": self._parse_duration(item["contentDetails"].get("duration", "")),
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
            })
        return videos

    def fetch_competitor_info(self, channel_id: str) -> Dict:
        """경쟁 채널 기본 정보 + 최근 영상."""
        ch = self._youtube.channels().list(part="snippet,statistics", id=channel_id).execute()
        if not ch.get("items"):
            return {}
        item = ch["items"][0]
        info = {
            "channel_id": channel_id,
            "name": item["snippet"]["title"],
            "subscribers": int(item["statistics"].get("subscriberCount", 0)),
            "category": item["snippet"].get("description", "")[:100],
        }
        info["recent_videos"] = self.fetch_channel_videos(channel_id, max_results=5)
        return info

    def fetch_analytics(self, channel_id: str, start_date: str, end_date: str) -> Dict:
        """내 채널 Analytics."""
        return self._analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained",
            dimensions="day",
        ).execute()

    def fetch_video_analytics(self, video_id: str, channel_id: str) -> Dict:
        """개별 영상 Analytics."""
        return self._analytics.reports().query(
            ids=f"channel=={channel_id}",
            startDate="2020-01-01",
            endDate="2030-12-31",
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
            filters=f"video=={video_id}",
        ).execute()

    @staticmethod
    def _parse_duration(iso_duration: str) -> str:
        """ISO 8601 duration → "MM:SS" 형식."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
        if not match:
            return "0:00"
        h, m, s = (int(x or 0) for x in match.groups())
        total_min = h * 60 + m
        return f"{total_min}:{s:02d}"
