"""썸네일/제목 학습 시스템 — yt-dlp로 썸네일 수집 + 패턴 분석."""
import json
import logging
import os
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def collect_thumbnails(channel_name: str, channel_id: str, vault_dir: Path,
                        max_videos: int = 20) -> List[Dict]:
    """채널의 최신 영상 썸네일 다운로드 + 메타데이터 수집."""
    import yt_dlp

    thumb_dir = vault_dir / "channels" / "thumbnails" / channel_name
    thumb_dir.mkdir(parents=True, exist_ok=True)

    url = f"https://www.youtube.com/channel/{channel_id}/videos"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "playlistend": max_videos,
        "writethumbnail": True,
        "outtmpl": str(thumb_dir / "%(id)s"),
        "skip_download": True,
    }

    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)

        for entry in (result.get("entries") or []):
            if entry is None:
                continue
            videos.append({
                "video_id": entry.get("id", ""),
                "title": entry.get("title", ""),
                "view_count": entry.get("view_count", 0),
                "like_count": entry.get("like_count", 0),
                "channel_follower_count": entry.get("channel_follower_count", 0),
                "thumbnail_path": str(thumb_dir / f"{entry.get('id', '')}.webp"),
            })
    except Exception as e:
        logger.error("썸네일 수집 실패 (%s): %s", channel_name, e)

    logger.info("%s: %d개 썸네일 수집", channel_name, len(videos))
    return videos


def calculate_ctr_proxy(videos: List[Dict]) -> List[Dict]:
    """구독자 대비 조회수 비율로 CTR 추정치 계산."""
    for v in videos:
        subs = v.get("channel_follower_count", 1) or 1
        views = v.get("view_count", 0)
        v["view_sub_ratio"] = views / subs
    return sorted(videos, key=lambda x: x["view_sub_ratio"], reverse=True)


def analyze_title_patterns(videos: List[Dict]) -> Dict:
    """제목 패턴 분석."""
    import re

    patterns = {
        "has_number": 0,
        "has_question": 0,
        "has_exclamation": 0,
        "has_bracket": 0,
        "avg_length": 0,
        "top_keywords": {},
    }

    for v in videos:
        title = v.get("title", "")
        if re.search(r"\d", title):
            patterns["has_number"] += 1
        if "?" in title:
            patterns["has_question"] += 1
        if "!" in title:
            patterns["has_exclamation"] += 1
        if "[" in title or "(" in title:
            patterns["has_bracket"] += 1
        patterns["avg_length"] += len(title)

    n = max(len(videos), 1)
    patterns["avg_length"] /= n
    patterns["total_videos"] = len(videos)

    return patterns


def main():
    vault = Path(os.getenv("KAIROS_VAULT_DIR", ""))

    # watchlist에서 채널 목록 가져오기
    from auto_agent.modules.data_collector.watchlist_parser import WatchlistParser
    parser = WatchlistParser(vault)
    trackable = parser.get_trackable()

    all_results = {}
    for ch in trackable[:6]:
        name = ch["name"]
        channel_id = ch["channel_id"]
        videos = collect_thumbnails(name, channel_id, vault, max_videos=10)
        if videos:
            ranked = calculate_ctr_proxy(videos)
            title_patterns = analyze_title_patterns(videos)
            all_results[name] = {
                "top_videos": ranked[:5],
                "title_patterns": title_patterns,
            }

    # 결과 저장
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = vault / "channels" / "thumbnails" / f"{today}-study.json"
    out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("썸네일 학습 결과 저장: %s", out)


if __name__ == "__main__":
    main()
