"""Stage 4: 채널 영상 데이터 수집 → 볼트 저장 (프론트매터 + 위키링크 + 태그).

yt-dlp로 메타데이터 수집 → 볼트 channels/{channel}/videos/*.md 생성.

Usage:
  python -m auto_agent.scripts.collect_channel_videos --channel semoji
  python -m auto_agent.scripts.collect_channel_videos --channel iromism
  python -m auto_agent.scripts.collect_channel_videos --all
"""
import json
import logging
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", os.path.expanduser("~/Desktop/kairos-vault")))

CHANNELS = {
    "semoji": {
        "id": "UCCsGPRmHOXhF4WTYs7ght9g",
        "name": "세모지(세상의모든지식)",
        "vault_path": "channels/semoji/videos",
        "categories": ["brand-encyclopedia", "knowledge-encyclopedia", "person-encyclopedia"],
    },
    "iromism": {
        "id": "UCOZmOXsWpJVoIBhqmVvfjhQ",
        "name": "이로미즘",
        "vault_path": "channels/iromism/videos",
        "categories": ["economy", "geopolitics", "analysis"],
    },
}

# 경쟁채널
COMPETITORS = {
    "지식한입": "@지식한입Bite-sizedKnowledge",
    "셜록현준": "@셜록현준",
    "소비더머니": "ytsearch:소비더머니",
    "슈카월드": "@syukaworld",
    "삼프로TV": "@3protv",
}


def collect_channel(channel_key: str, max_videos: int = 100):
    """채널 영상 메타데이터 수집 → 볼트 md 생성."""
    config = CHANNELS.get(channel_key)
    if not config:
        logger.error(f"알 수 없는 채널: {channel_key}")
        return

    channel_id = config["id"]
    vault_path = VAULT_DIR / config["vault_path"]
    vault_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"=== {config['name']} 영상 수집 시작 (최대 {max_videos}개) ===")

    # yt-dlp로 메타데이터 수집
    cmd = [
        "yt-dlp", "--flat-playlist", "-j",
        f"https://www.youtube.com/channel/{channel_id}/videos",
        "--playlist-items", f"1:{max_videos}",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        videos = [json.loads(line) for line in result.stdout.strip().split("\n") if line.strip()]
    except Exception as e:
        logger.error(f"yt-dlp 실패: {e}")
        return

    logger.info(f"{len(videos)}개 영상 수집")

    # 기존 파일 목록
    existing = {f.stem for f in vault_path.glob("*.md") if not f.name.startswith("_")}
    created = 0
    updated = 0

    for v in videos:
        vid = v.get("id", "")
        title = v.get("title", "")
        views = v.get("view_count", 0)
        duration = v.get("duration", 0)
        slug = _slugify(title, vid)

        md_path = vault_path / f"{slug}.md"

        # 카테고리 자동 분류
        category = _classify_category(title, config["categories"])
        tags = _generate_tags(title, views, category, channel_key)

        # 관련 영상 위키링크
        wikilinks = _find_related(title, videos, vid)

        # 조회수 등급
        view_tier = _view_tier(views)

        frontmatter = {
            "title": title,
            "type": "video",
            "channel": config["name"],
            "video_id": vid,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "views": views,
            "duration_sec": duration,
            "duration_min": round(duration / 60, 1) if duration else 0,
            "category": category,
            "view_tier": view_tier,
            "tags": tags,
            "url": f"https://www.youtube.com/watch?v={vid}",
        }

        body = f"# {title}\n\n"
        body += f"조회수: **{views:,}** ({view_tier})\n"
        body += f"길이: {round(duration/60, 1)}분\n\n"

        if wikilinks:
            body += "## 관련 영상\n"
            for wl in wikilinks:
                body += f"- [[{wl}]]\n"
            body += "\n"

        body += "## 분석\n\n"
        body += "_NotebookLM 분석 추가 예정_\n\n"
        body += "## YouTube Analytics\n\n"
        body += "_CTR, 시청지속율 데이터 추가 예정_\n"

        # 프론트매터 YAML
        fm_yaml = "---\n"
        for k, val in frontmatter.items():
            if isinstance(val, list):
                fm_yaml += f"{k}: [{', '.join(val)}]\n"
            elif isinstance(val, (int, float)):
                fm_yaml += f"{k}: {val}\n"
            else:
                fm_yaml += f'{k}: "{val}"\n'
        fm_yaml += "---\n\n"

        content = fm_yaml + body

        if slug in existing:
            # 기존 파일 업데이트 (views만)
            old = md_path.read_text(encoding="utf-8")
            if f"views: {views}" not in old:
                md_path.write_text(content, encoding="utf-8")
                updated += 1
        else:
            md_path.write_text(content, encoding="utf-8")
            created += 1

    # 인덱스 업데이트
    _update_index(vault_path, config["name"], videos)

    logger.info(f"완료: {created}개 생성, {updated}개 업데이트")


def _slugify(title: str, vid: str) -> str:
    """제목 → 파일명 슬러그."""
    # 한글, 영문, 숫자만 유지
    slug = re.sub(r'[^\w가-힣\s-]', '', title)
    slug = re.sub(r'\s+', '-', slug.strip())
    slug = slug[:60]  # 최대 60자
    if not slug:
        slug = vid
    return unicodedata.normalize("NFC", slug)


def _classify_category(title: str, categories: list) -> str:
    """제목에서 카테고리 자동 분류."""
    title_lower = title.lower()
    if any(k in title for k in ["브랜드", "brand", "역사", "history"]):
        return "brand-encyclopedia"
    if any(k in title for k in ["인물", "person", "인생"]):
        return "person-encyclopedia"
    if any(k in title for k in ["상식", "knowledge", "백과"]):
        return "knowledge-encyclopedia"
    if any(k in title_lower for k in ["경제", "economy", "금리", "환율"]):
        return "economy"
    if any(k in title_lower for k in ["전쟁", "war", "지정학"]):
        return "geopolitics"
    return categories[0] if categories else "general"


def _generate_tags(title: str, views: int, category: str, channel: str) -> list:
    """태그 자동 생성."""
    tags = ["video", channel, category]

    if views >= 10_000_000:
        tags.append("10M-club")
    elif views >= 1_000_000:
        tags.append("1M-club")
    elif views >= 500_000:
        tags.append("500K-club")
    elif views >= 100_000:
        tags.append("100K-club")

    # 시리즈 감지
    if any(k in title for k in ["통합편", "통합본", "Part", "편"]):
        tags.append("series")

    return tags


def _view_tier(views: int) -> str:
    if views >= 10_000_000: return "mega-hit"
    if views >= 1_000_000: return "million"
    if views >= 500_000: return "viral"
    if views >= 100_000: return "hit"
    if views >= 50_000: return "good"
    if views >= 10_000: return "normal"
    return "low"


def _find_related(title: str, videos: list, current_id: str) -> list:
    """제목 키워드로 관련 영상 찾기."""
    keywords = set(re.findall(r'[가-힣]{2,}', title))
    related = []
    for v in videos:
        if v.get("id") == current_id:
            continue
        other_title = v.get("title", "")
        other_keywords = set(re.findall(r'[가-힣]{2,}', other_title))
        overlap = keywords & other_keywords
        if len(overlap) >= 2:
            slug = _slugify(other_title, v.get("id", ""))
            related.append(slug)
    return related[:5]


def _update_index(vault_path: Path, channel_name: str, videos: list):
    """_index.md 업데이트."""
    total = len(videos)
    total_views = sum(v.get("view_count", 0) for v in videos)
    top_video = max(videos, key=lambda x: x.get("view_count", 0)) if videos else {}

    index_content = f"""---
title: "{channel_name} 영상 인덱스"
type: index
channel: "{channel_name}"
updated: "{datetime.now().strftime('%Y-%m-%d')}"
total_videos: {total}
total_views: {total_views}
tags: [index, video, {channel_name.split('(')[0].strip().lower()}]
---

# {channel_name} 영상 ({total}개)

총 조회수: **{total_views:,}**
최고 조회수: **{top_video.get('title', '')[:50]}** ({top_video.get('view_count', 0):,})

## 조회수별 분포
- 10M+: {sum(1 for v in videos if v.get('view_count', 0) >= 10_000_000)}개
- 1M+: {sum(1 for v in videos if v.get('view_count', 0) >= 1_000_000)}개
- 500K+: {sum(1 for v in videos if v.get('view_count', 0) >= 500_000)}개
- 100K+: {sum(1 for v in videos if v.get('view_count', 0) >= 100_000)}개
"""
    (vault_path / "_index.md").write_text(index_content, encoding="utf-8")


def main():
    args = sys.argv[1:]

    if "--all" in args:
        for ch in CHANNELS:
            collect_channel(ch, max_videos=500)
    elif "--channel" in args:
        idx = args.index("--channel")
        if idx + 1 < len(args):
            ch = args[idx + 1]
            max_v = 500 if ch in ("semoji", "iromism") else 100
            collect_channel(ch, max_videos=max_v)
    else:
        print("Usage: --channel semoji|iromism | --all")


if __name__ == "__main__":
    main()
