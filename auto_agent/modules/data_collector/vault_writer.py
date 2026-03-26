"""수집 데이터를 Obsidian 볼트 마크다운 노트로 변환."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dedup import DedupManager, UpsertAction


class VaultWriter:
    """수집 데이터 → 볼트 마크다운 노트 변환 + 중복 방지."""

    def __init__(self, vault_dir: Path, dedup: DedupManager):
        self._vault = vault_dir
        self._dedup = dedup

    def write_video_note(
        self,
        channel: str,
        video_id: str,
        title: str,
        published: str,
        duration: str,
        views: int,
        likes: int,
        project_slug: Optional[str] = None,
    ) -> str:
        content = self._render_video_note(
            channel, video_id, title, published, duration, views, likes, project_slug
        )
        note_path = self._vault / "channels" / channel / "videos" / f"{title}.md"
        return self._upsert("youtube_video", video_id, content, note_path)

    def write_trend_note(self, date: str, trends: List[Dict]) -> str:
        content = self._render_trend_note(date, trends)
        note_path = self._vault / "market" / "trends" / f"{date}-daily.md"
        return self._upsert("trend", date, content, note_path)

    def write_competitor_note(
        self,
        channel_id: str,
        name: str,
        category: str,
        subscribers: int,
        recent_videos: List[Dict],
    ) -> str:
        content = self._render_competitor_note(
            channel_id, name, category, subscribers, recent_videos
        )
        note_path = self._vault / "channels" / "competitors" / f"{name}.md"
        return self._upsert("competitor", channel_id, content, note_path)

    def write_analytics_note(
        self,
        channel: str,
        date: str,
        metrics: Dict[str, Any],
    ) -> str:
        content = self._render_analytics_note(channel, date, metrics)
        note_path = self._vault / "channels" / channel / "analytics" / f"{date}.md"
        return self._upsert("analytics", f"{channel}:{date}", content, note_path)

    # ── 내부: upsert ──

    def _upsert(self, source: str, source_id: str, content: str, note_path: Path) -> str:
        action = self._dedup.check(source, source_id, content)
        if action == UpsertAction.CREATE:
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(content, encoding="utf-8")
            self._dedup.record(source, source_id, content, str(note_path.relative_to(self._vault)))
            return "created"
        elif action == UpsertAction.UPDATE:
            existing_rel = self._dedup.get_note_path(source, source_id)
            target = self._vault / existing_rel if existing_rel else note_path
            target.write_text(content, encoding="utf-8")
            self._dedup.record(source, source_id, content, str(target.relative_to(self._vault)))
            return "updated"
        return "skipped"

    # ── 내부: 렌더링 ──

    def _render_video_note(self, channel, video_id, title, published, duration, views, likes, project_slug) -> str:
        lines = [
            "---",
            f'video_id: "{video_id}"',
            f"channel: {channel}",
        ]
        if project_slug:
            lines.append(f"project_slug: {project_slug}")
        lines += [
            f"published: {published}",
            f'duration: "{duration}"',
            f"last_updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {title}",
            "",
            "## 성과",
            f"- 조회수: {views:,}",
            f"- 좋아요: {likes:,}",
            "",
        ]
        return "\n".join(lines)

    def _render_trend_note(self, date: str, trends: List[Dict]) -> str:
        lines = [
            "---",
            "type: trend-daily",
            f"date: {date}",
            "---",
            "",
            f"# 트렌드 스냅샷 ({date})",
            "",
            "| 키워드 | 변화 | 지역 |",
            "|--------|------|------|",
        ]
        for t in trends:
            lines.append(f"| {t['keyword']} | {t.get('volume_change', '-')} | {t.get('region', '-')} |")
        lines.append("")
        return "\n".join(lines)

    def _render_competitor_note(self, channel_id, name, category, subscribers, recent_videos) -> str:
        lines = [
            "---",
            f'channel_id: "{channel_id}"',
            f"name: {name}",
            f"category: {category}",
            f"subscribers: {subscribers:,}",
            f"last_updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {name}",
            "",
            "## 최근 영상",
            "| 제목 | 조회수 | 게시일 |",
            "|------|--------|--------|",
        ]
        for v in recent_videos:
            lines.append(f"| {v['title']} | {v.get('views', 0):,} | {v.get('published', '-')} |")
        lines.append("")
        return "\n".join(lines)

    def _render_analytics_note(self, channel: str, date: str, metrics: Dict) -> str:
        lines = [
            "---",
            "type: analytics-daily",
            f"channel: {channel}",
            f"date: {date}",
            "---",
            "",
            f"# {channel} Analytics ({date})",
            "",
        ]
        for key, value in metrics.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
        return "\n".join(lines)
