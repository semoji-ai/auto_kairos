"""볼트 내 경로 규칙 중앙 관리."""
from pathlib import Path
from auto_agent.paths import get_vault_dir


def vault_root() -> Path:
    return get_vault_dir()

def collector_dir() -> Path:
    return vault_root() / ".collector"

def channel_dir(channel: str) -> Path:
    return vault_root() / "channels" / channel

def videos_dir(channel: str) -> Path:
    return channel_dir(channel) / "videos"

def analytics_dir(channel: str) -> Path:
    return channel_dir(channel) / "analytics"

def competitors_dir() -> Path:
    return vault_root() / "channels" / "competitors"

def trends_dir() -> Path:
    return vault_root() / "market" / "trends"

def news_dir() -> Path:
    return vault_root() / "market" / "news"

def social_dir() -> Path:
    return vault_root() / "market" / "social"

def communities_dir() -> Path:
    return vault_root() / "market" / "communities"

def topics_dir() -> Path:
    return vault_root() / "topics"

def insights_dir() -> Path:
    return vault_root() / "insights"

def planning_dir() -> Path:
    return insights_dir() / "planning"

def feedback_dir() -> Path:
    return insights_dir() / "feedback"

def performance_dir() -> Path:
    return insights_dir() / "performance"

def templates_dir() -> Path:
    return vault_root() / "templates"

def watchlist_path() -> Path:
    return vault_root() / "channels" / "_watchlist.md"

def state_json_path() -> Path:
    return collector_dir() / "state.json"

def hashes_db_path() -> Path:
    return collector_dir() / "hashes.db"

def video_tracking_path() -> Path:
    return collector_dir() / "video_tracking.json"


def ensure_vault_structure():
    """볼트 기본 디렉토리 구조 생성. 이미 있으면 스킵."""
    dirs = [
        collector_dir(),
        channel_dir("이로미즘") / "analytics",
        channel_dir("이로미즘") / "videos",
        channel_dir("세모지") / "analytics",
        channel_dir("세모지") / "videos",
        competitors_dir(),
        trends_dir(),
        news_dir(),
        social_dir(),
        communities_dir(),
        topics_dir(),
        planning_dir(),
        feedback_dir(),
        performance_dir(),
        templates_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # .obsidianignore
    obsidianignore = vault_root() / ".obsidianignore"
    if not obsidianignore.exists():
        obsidianignore.write_text(".collector/\n.lance/\n", encoding="utf-8")

    # 템플릿 파일 생성
    video_template = templates_dir() / "video-note.md"
    if not video_template.exists():
        video_template.write_text(
            "---\n"
            'video_id: ""\n'
            "channel:\n"
            "project_slug:\n"
            "published:\n"
            'duration: ""\n'
            "---\n"
            "\n"
            "## 성과\n"
            "| 지표 | 7일 | 28일 | 현재 |\n"
            "|------|-----|------|------|\n"
            "| 조회수 | | | |\n"
            "| CTR | | | |\n"
            "| 평균 시청 지속 | | | |\n"
            "\n"
            "## 유입 경로\n"
            "\n"
            "## 연결\n",
            encoding="utf-8",
        )
