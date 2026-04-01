"""Stage 4 주간 데이터 수집 + 볼트 업데이트 + 위키링크 연동.

매주 월요일 KST 06:30 (UTC 21:30) 실행.

1. yt-dlp로 채널 영상 데이터 수집 → 볼트 md 업데이트
2. YouTube Analytics 성과 데이터 → 볼트 md에 추가
3. 위키링크 크로스 연동 → 누락된 링크 추가
4. 벡터 인덱스 리빌드

Usage:
  python -m auto_agent.scripts.stage4_weekly
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

WORKSPACE = Path(__file__).resolve().parent.parent.parent
VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", ""))


def main():
    logger.info("=== Stage 4 주간 수집 시작 ===")

    if not VAULT_DIR.exists():
        logger.error("볼트 미연결: %s", VAULT_DIR)
        sys.exit(1)

    python = sys.executable

    # 1. yt-dlp 채널 데이터 수집
    logger.info("[1/4] 채널 영상 데이터 수집...")
    for channel in ["semoji", "iromism"]:
        try:
            result = subprocess.run(
                [python, "-m", "auto_agent.scripts.collect_channel_videos",
                 "--channel", channel],
                capture_output=True, text=True, timeout=300,
                cwd=str(WORKSPACE),
            )
            if result.returncode == 0:
                logger.info("  %s 수집 완료", channel)
            else:
                logger.error("  %s 수집 실패: %s", channel, result.stderr[:200])
        except Exception as e:
            logger.error("  %s 수집 에러: %s", channel, e)

    # 2. YouTube Analytics 성과 데이터
    logger.info("[2/4] YouTube Analytics 수집...")
    try:
        from auto_agent.modules.data_collector.youtube_analytics import YouTubeAnalytics

        for channel_name in ["semoji", "iromism"]:
            try:
                yt = YouTubeAnalytics(channel_name)
                videos = yt.get_recent_videos(max_results=20)
                if videos:
                    _update_vault_with_analytics(channel_name, videos)
                    logger.info("  %s: %d개 영상 성과 업데이트", channel_name, len(videos))
                else:
                    logger.warning("  %s: Analytics 데이터 없음 (토큰 확인)", channel_name)
            except Exception as e:
                logger.error("  %s Analytics 실패: %s", channel_name, e)
    except ImportError:
        logger.warning("  YouTube Analytics 모듈 불가 (google-api-python-client 필요)")

    # 3. 위키링크 크로스 연동
    logger.info("[3/4] 위키링크 크로스 연동...")
    try:
        result = subprocess.run(
            [python, "-m", "auto_agent.scripts.vault_wikilink_builder"],
            capture_output=True, text=True, timeout=120,
            cwd=str(WORKSPACE),
        )
        logger.info("  위키링크 연동 완료")
    except Exception as e:
        logger.error("  위키링크 연동 실패: %s", e)

    # 4. 벡터 인덱스 리빌드
    logger.info("[4/4] 벡터 인덱스 리빌드...")
    try:
        result = subprocess.run(
            [python, "-m", "auto_agent.modules.memory_index", "build"],
            capture_output=True, text=True, timeout=120,
            cwd=str(WORKSPACE),
        )
        logger.info("  인덱스 리빌드 완료")
    except Exception as e:
        logger.error("  인덱스 리빌드 실패: %s", e)

    # 웹훅 보고
    _send_report()

    logger.info("=== Stage 4 주간 수집 종료 ===")


def _update_vault_with_analytics(channel_name: str, videos: list):
    """YouTube Analytics 데이터를 볼트 md에 추가."""
    vault_map = {
        "semoji": "channels/semoji/videos",
        "iromism": "channels/iromism/videos",
    }
    vault_path = VAULT_DIR / vault_map.get(channel_name, "")
    if not vault_path.exists():
        return

    for v in videos:
        vid = v.get("video_id", "")
        views = v.get("views", 0)
        likes = v.get("likes", 0)
        comments = v.get("comments", 0)

        # 해당 영상 md 찾기 (video_id로 grep)
        for md in vault_path.glob("*.md"):
            if md.name.startswith("_"):
                continue
            content = md.read_text(encoding="utf-8")
            if f'video_id: "{vid}"' in content:
                # Analytics 섹션 업데이트
                analytics_block = (
                    f"\n## YouTube Analytics (업데이트: {datetime.now().strftime('%Y-%m-%d')})\n\n"
                    f"- 조회수: **{views:,}**\n"
                    f"- 좋아요: {likes:,}\n"
                    f"- 댓글: {comments:,}\n"
                    f"- 좋아요율: {likes/max(views,1)*100:.1f}%\n"
                )

                if "## YouTube Analytics" in content:
                    # 기존 섹션 교체
                    import re
                    content = re.sub(
                        r'## YouTube Analytics.*?(?=\n## |\Z)',
                        analytics_block.strip() + "\n",
                        content,
                        flags=re.DOTALL,
                    )
                else:
                    content += analytics_block

                # views 프론트매터도 업데이트
                content = re.sub(r'views: \d+', f'views: {views}', content)

                md.write_text(content, encoding="utf-8")
                break


def _send_report():
    """디스코드 웹훅으로 주간 보고."""
    import requests
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return

    report = (
        f"## 📊 Stage 4 주간 수집 완료\n\n"
        f"날짜: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"1. 채널 데이터 수집 (yt-dlp)\n"
        f"2. YouTube Analytics 업데이트\n"
        f"3. 위키링크 크로스 연동\n"
        f"4. 벡터 인덱스 리빌드"
    )

    try:
        requests.post(webhook_url, json={"content": report}, timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    main()
