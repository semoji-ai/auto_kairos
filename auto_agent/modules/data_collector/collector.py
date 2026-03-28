"""데이터 수집 메인 오케스트레이터."""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

from auto_agent.paths import get_vault_dir
from .dedup import DedupManager
from .discord_notifier import DiscordNotifier
from .vault_paths import ensure_vault_structure
from .vault_writer import VaultWriter
from .youtube_collector import YouTubeCollector

logger = logging.getLogger(__name__)

CHECKPOINT_DAYS = {"1d": 1, "3d": 3, "7d": 7, "28d": 28}


class DataCollector:
    """데이터 수집 오케스트레이터 — YouTube 중심."""

    def __init__(self):
        self._vault_dir = get_vault_dir()
        self._collector_dir = self._vault_dir / ".collector"
        self._collector_dir.mkdir(parents=True, exist_ok=True)

        self._dedup = DedupManager(collector_dir=self._collector_dir)
        self._writer = VaultWriter(vault_dir=self._vault_dir, dedup=self._dedup)

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self._notifier = DiscordNotifier(webhook_url=webhook_url)

        # 채널 ID는 __init__에서 로드 (.env 로드 이후 보장)
        self._channel_ids = {
            "이로미즘": os.getenv("YOUTUBE_CHANNEL_ID_IROMISM", ""),
            "세모지": os.getenv("YOUTUBE_CHANNEL_ID_SEMOJI", ""),
        }

        self._youtube = YouTubeCollector(
            client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
            client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
            refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
        )

        # 볼트 기본 구조 + 템플릿 자동 생성
        ensure_vault_structure()

    # ── 전체 수집 ──

    def collect_all(self):
        """전체 수집 실행 (cron 05:30)."""
        errors = []
        for source, fn in [
            ("youtube", self._collect_youtube),
            ("video_tracking", self._collect_video_tracking),
        ]:
            try:
                fn()
            except Exception as e:
                logger.error("수집 실패 [%s]: %s", source, e)
                errors.append((source, str(e)))

        if errors:
            for source, err in errors:
                self._notifier.send(self._notifier.format_error(source, err))

    def collect_youtube(self):
        """YouTube 수집만 (CLI용)."""
        self._collect_youtube()

    # ── YouTube 수집 ──

    def _collect_youtube(self):
        for channel_name, channel_id in self._channel_ids.items():
            if not channel_id:
                continue
            wm = self._dedup.get_watermark("youtube_videos", channel_name)
            after = wm.get("last_published") if wm else None

            videos = self._youtube.fetch_channel_videos(channel_id, after=after)
            for v in videos:
                self._writer.write_video_note(
                    channel=channel_name,
                    video_id=v["video_id"],
                    title=v["title"],
                    published=v["published"],
                    duration=v["duration"],
                    views=v["views"],
                    likes=v["likes"],
                )

            if videos:
                self._dedup.set_watermark(
                    "youtube_videos",
                    channel_name,
                    {
                        "last_video_id": videos[0]["video_id"],
                        "last_published": videos[0]["published"][:10],
                        "last_fetch": datetime.now(timezone.utc).isoformat(),
                    },
                )

        self._collect_competitors()

    def _collect_competitors(self):
        """경쟁 채널 공개 데이터 수집 (주 1회)."""
        wm = self._dedup.get_watermark("competitors", "global")
        if wm:
            last = datetime.fromisoformat(wm["last_fetch"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - last).days < 7:
                return

        watchlist = self._load_watchlist()
        for ch in watchlist:
            try:
                info = self._youtube.fetch_competitor_info(ch["channel_id"])
                if info:
                    self._writer.write_competitor_note(
                        channel_id=info["channel_id"],
                        name=info["name"],
                        category=info.get("category", ""),
                        subscribers=info["subscribers"],
                        recent_videos=[
                            {"title": v["title"], "views": v["views"], "published": v["published"][:10]}
                            for v in info.get("recent_videos", [])
                        ],
                    )
            except Exception as e:
                logger.error("경쟁 채널 수집 실패 [%s]: %s", ch.get("name"), e)

        self._dedup.set_watermark(
            "competitors", "global", {"last_fetch": datetime.now(timezone.utc).isoformat()}
        )

    # ── 영상 추적 ──

    def register_video_tracking(self, video_id: str, project_slug: str, channel: str):
        """영상 성과 추적 등록 — 1d/3d/7d/28d 체크포인트 생성."""
        tracking = self._load_video_tracking()
        now = datetime.now(timezone.utc)

        entry = {
            "video_id": video_id,
            "project_slug": project_slug,
            "channel": channel,
            "linked_at": now.isoformat(),
            "checkpoints": {},
        }
        for key, days in CHECKPOINT_DAYS.items():
            due = (now + timedelta(days=days)).strftime("%Y-%m-%d")
            entry["checkpoints"][key] = {"due": due, "status": "pending"}

        tracking["tracking"].append(entry)
        self._save_video_tracking(tracking)

    def get_due_checkpoints(self) -> List[Dict]:
        """오늘 이전 due date이면서 pending 상태인 체크포인트 목록 반환."""
        tracking = self._load_video_tracking()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        due = []
        for entry in tracking["tracking"]:
            for cp_key, cp in entry["checkpoints"].items():
                if cp["due"] <= today and cp["status"] == "pending":
                    due.append({
                        "video_id": entry["video_id"],
                        "project_slug": entry["project_slug"],
                        "channel": entry["channel"],
                        "checkpoint": cp_key,
                    })
        return due

    def _collect_video_tracking(self):
        """만기 체크포인트 분석 데이터 수집."""
        due = self.get_due_checkpoints()
        for item in due:
            try:
                channel_id = self._channel_ids.get(item["channel"], "")
                if not channel_id:
                    continue
                self._youtube.fetch_video_analytics(item["video_id"], channel_id)
                self._mark_checkpoint(item["video_id"], item["checkpoint"], "done")
            except Exception as e:
                logger.error("영상 추적 실패 [%s/%s]: %s", item["video_id"], item["checkpoint"], e)
                self._mark_checkpoint(item["video_id"], item["checkpoint"], "retry")

    def _mark_checkpoint(self, video_id: str, checkpoint: str, status: str):
        """체크포인트 상태 업데이트."""
        tracking = self._load_video_tracking()
        for entry in tracking["tracking"]:
            if entry["video_id"] == video_id:
                entry["checkpoints"][checkpoint]["status"] = status
                if status == "done":
                    entry["checkpoints"][checkpoint]["collected_at"] = datetime.now(timezone.utc).isoformat()
                break
        self._save_video_tracking(tracking)

    # ── 파일 I/O ──

    def _load_video_tracking(self) -> Dict:
        path = self._collector_dir / "video_tracking.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"tracking": []}

    def _save_video_tracking(self, data: Dict):
        path = self._collector_dir / "video_tracking.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_watchlist(self) -> List[Dict]:
        """_watchlist.md에서 active + trial 채널 목록 추출."""
        from .watchlist_parser import WatchlistParser
        parser = WatchlistParser(self._vault_dir)
        return parser.get_trackable()
