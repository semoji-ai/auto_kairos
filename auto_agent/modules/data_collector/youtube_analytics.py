"""YouTube Analytics API — 채널별 OAuth 토큰 관리 + 성과 데이터 수집."""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

CREDENTIALS_DIR = Path(__file__).resolve().parent.parent.parent.parent / ".credentials"


class YouTubeAnalytics:
    """채널별 YouTube Analytics 수집."""

    def __init__(self, channel_name: str):
        self._channel_name = channel_name
        self._token_path = CREDENTIALS_DIR / f"youtube_{channel_name}.json"
        self._creds = self._load_credentials()

    def _load_credentials(self) -> Optional[Credentials]:
        """토큰 파일에서 자격증명 로드."""
        if not self._token_path.exists():
            logger.warning("토큰 없음: %s", self._token_path)
            return None

        try:
            creds = Credentials.from_authorized_user_file(str(self._token_path))
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 갱신된 토큰 저장
                self._token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception as e:
            logger.error("자격증명 로드 실패 (%s): %s", self._channel_name, e)
            return None

    def get_channel_info(self) -> Optional[Dict]:
        """채널 기본 정보 (구독자, 총 조회수, 영상 수)."""
        if not self._creds:
            return None

        try:
            youtube = build("youtube", "v3", credentials=self._creds)
            response = youtube.channels().list(
                part="snippet,statistics",
                mine=True,
            ).execute()

            if not response.get("items"):
                return None

            ch = response["items"][0]
            stats = ch.get("statistics", {})
            return {
                "channel_name": ch["snippet"]["title"],
                "channel_id": ch["id"],
                "subscribers": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            }
        except Exception as e:
            logger.error("채널 정보 실패 (%s): %s", self._channel_name, e)
            return None

    def get_recent_videos(self, max_results: int = 10) -> List[Dict]:
        """최근 업로드 영상 목록 + 성과."""
        if not self._creds:
            return []

        try:
            youtube = build("youtube", "v3", credentials=self._creds)

            # 내 채널 ID 가져오기
            ch_response = youtube.channels().list(part="contentDetails", mine=True).execute()
            if not ch_response.get("items"):
                return []

            uploads_id = ch_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

            # 최근 영상 가져오기
            pl_response = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_id,
                maxResults=max_results,
            ).execute()

            video_ids = [item["snippet"]["resourceId"]["videoId"]
                         for item in pl_response.get("items", [])]

            if not video_ids:
                return []

            # 영상 상세 통계
            v_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids),
            ).execute()

            videos = []
            for v in v_response.get("items", []):
                stats = v.get("statistics", {})
                videos.append({
                    "video_id": v["id"],
                    "title": v["snippet"]["title"],
                    "published": v["snippet"]["publishedAt"],
                    "duration": v["contentDetails"]["duration"],
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                })

            return videos
        except Exception as e:
            logger.error("최근 영상 실패 (%s): %s", self._channel_name, e)
            return []

    def save_to_vault(self, vault_dir: Path):
        """채널 성과 데이터를 볼트에 저장."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 채널 정보
        info = self.get_channel_info()
        if info:
            logger.info("%s: 구독자 %s, 총 조회수 %s",
                        self._channel_name,
                        f"{info['subscribers']:,}",
                        f"{info['total_views']:,}")

        # 최근 영상
        videos = self.get_recent_videos()
        if videos:
            logger.info("%s: 최근 %d개 영상 수집", self._channel_name, len(videos))

        # 저장
        ch_dir = vault_dir / "channels" / self._channel_name / "analytics"
        ch_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "date": today,
            "channel": self._channel_name,
            "info": info,
            "recent_videos": videos,
        }

        output = ch_dir / f"{today}-analytics.json"
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        # 마크다운 요약
        summary_path = ch_dir / f"{today}-summary.md"
        lines = [f"# {self._channel_name} Analytics — {today}\n"]

        if info:
            lines.append(f"- 구독자: {info['subscribers']:,}")
            lines.append(f"- 총 조회수: {info['total_views']:,}")
            lines.append(f"- 영상 수: {info['video_count']:,}\n")

        if videos:
            lines.append("## 최근 영상 성과\n")
            lines.append("| 제목 | 조회수 | 좋아요 | 댓글 |")
            lines.append("|------|--------|--------|------|")
            for v in videos:
                lines.append(f"| {v['title'][:40]} | {v['views']:,} | {v['likes']:,} | {v['comments']:,} |")

        summary_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("%s: 볼트 저장 완료 → %s", self._channel_name, ch_dir)

        return data
