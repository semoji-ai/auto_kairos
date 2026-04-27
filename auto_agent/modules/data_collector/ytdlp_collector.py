"""yt-dlp 기반 YouTube 데이터 수집 — API 할당량 무관."""
import json
import logging
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class YtdlpCollector:
    """yt-dlp로 YouTube 채널/영상 메타데이터 수집."""

    def __init__(self, vault_dir: Path):
        self._vault_dir = vault_dir

    def collect_channel_videos(self, channel_id: str, channel_name: str,
                                max_videos: int = 20) -> List[Dict]:
        """채널의 최신 영상 메타데이터 수집."""
        import yt_dlp

        url = f"https://www.youtube.com/channel/{channel_id}/videos"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": max_videos,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=False)

            if not result or "entries" not in result:
                logger.warning("채널 %s: 영상 없음", channel_name)
                return []

            videos = []
            for entry in result["entries"]:
                if entry is None:
                    continue
                videos.append({
                    "video_id": entry.get("id", ""),
                    "title": entry.get("title", ""),
                    "url": entry.get("url", ""),
                    "duration": entry.get("duration"),
                    "view_count": entry.get("view_count"),
                })

            logger.info("채널 %s: %d개 영상 수집", channel_name, len(videos))
            return videos

        except Exception as e:
            logger.error("채널 %s 수집 실패: %s", channel_name, e)
            return []

    def collect_video_detail(self, video_id: str) -> Optional[Dict]:
        """개별 영상 상세 메타데이터 수집."""
        import yt_dlp

        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            return {
                "video_id": info.get("id", ""),
                "title": info.get("title", ""),
                "description": info.get("description", "")[:500],
                "upload_date": info.get("upload_date", ""),
                "duration": info.get("duration"),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "comment_count": info.get("comment_count", 0),
                "channel": info.get("channel", ""),
                "channel_id": info.get("channel_id", ""),
                "tags": info.get("tags", [])[:10],
                "categories": info.get("categories", []),
            }
        except Exception as e:
            logger.error("영상 %s 수집 실패: %s", video_id, e)
            return None

    def collect_competitors(self, watchlist_path: Path) -> Dict:
        """watchlist의 모든 경쟁 채널 수집 → 볼트 저장."""
        from auto_agent.modules.data_collector.watchlist_parser import WatchlistParser

        parser = WatchlistParser(self._vault_dir)
        trackable = parser.get_trackable()

        if not trackable:
            logger.warning("watchlist가 비어있음")
            return {"collected": 0, "channels": []}

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        results = {"collected": 0, "channels": []}

        for ch in trackable:
            name = ch["name"]
            channel_id = ch["channel_id"]

            logger.info("수집 시작: %s (%s)", name, channel_id)
            videos = self.collect_channel_videos(channel_id, name, max_videos=10)

            if videos:
                # 볼트에 저장
                comp_dir = self._vault_dir / "channels" / "competitors" / name
                comp_dir.mkdir(parents=True, exist_ok=True)

                # 최신 영상 목록 저장
                videos_file = comp_dir / f"{today}-videos.json"
                videos_file.write_text(
                    json.dumps(videos, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

                # 마크다운 노트 생성/업데이트
                note_path = comp_dir / f"_overview.md"
                note_content = f"""---
channel: {name}
channel_id: {channel_id}
category: {ch.get('category', '')}
status: {ch.get('status', 'active')}
last_collected: {today}
---

# {name}

## 최신 영상 ({today})

"""
                for v in videos[:10]:
                    views = f"{v.get('view_count', 0):,}" if v.get('view_count') else "?"
                    note_content += f"- **{v['title']}** — 조회수: {views}\n"

                note_path.write_text(note_content, encoding="utf-8")

                results["channels"].append({"name": name, "videos": len(videos)})
                results["collected"] += len(videos)

        logger.info("경쟁 채널 수집 완료: %d개 채널, %d개 영상",
                     len(results["channels"]), results["collected"])
        return results

    def collect_trending(self, country: str = "KR", max_videos: int = 20) -> List[Dict]:
        """YouTube 트렌딩 영상 수집.

        2026-04 기준: YouTube가 공개 /feed/trending 페이지를 사실상 폐기해
        yt-dlp 단독으로는 수집 불가. YouTube Data API 키가 살아 있을 때만 의미가 있어
        지금은 빈 결과 + 안내 로그를 반환한다. (경쟁채널/뉴스/커뮤니티가 트렌드 신호를 대체)
        """
        logger.info("trending 수집 비활성화: YouTube 공개 trending 페이지 폐기됨 (Data API 필요)")
        return []

        import yt_dlp  # noqa: F401  (아래는 향후 Data API 연동 시 참고용)

        url = f"https://www.youtube.com/feed/trending?gl={country}"
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": max_videos,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(url, download=False)

            if not result or "entries" not in result:
                return []

            videos = []
            for entry in (result.get("entries") or []):
                if entry is None:
                    continue
                videos.append({
                    "video_id": entry.get("id", ""),
                    "title": entry.get("title", ""),
                    "channel": entry.get("channel", entry.get("uploader", "")),
                    "view_count": entry.get("view_count"),
                })

            # 볼트에 저장
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            trends_dir = self._vault_dir / "market" / "trends"
            trends_dir.mkdir(parents=True, exist_ok=True)

            trends_file = trends_dir / f"{today}-trending-{country}.json"
            trends_file.write_text(
                json.dumps(videos, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            logger.info("트렌딩 수집: %d개 (%s)", len(videos), country)
            return videos

        except Exception as e:
            logger.error("트렌딩 수집 실패: %s", e)
            return []
