"""세모지 콘텐츠 심층 분석 — 원고 × 성과 × 시간순 변화."""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).resolve().parent.parent.parent / "logs" / "semoji-analysis.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_NOTIFY_CHANNEL = "1486738313468706987"


def get_drive_service():
    """Google Drive 서비스 생성."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    tokens = json.load(open(os.path.expanduser("~/.config/google-drive-mcp/tokens.json")))
    keys = json.load(open(os.path.expanduser("~/.config/google-drive-mcp/gcp-oauth.keys.json")))
    installed = keys.get("installed", keys.get("web", {}))

    creds = Credentials(
        token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=installed["client_id"],
        client_secret=installed["client_secret"],
    )
    if creds.expired:
        creds.refresh(Request())
    return build("drive", "v3", credentials=creds)


def fetch_all_scripts(service, prefix: str, max_docs: int = 100) -> list:
    """Drive에서 prefix로 시작하는 모든 Google Docs 가져오기."""
    all_docs = []
    page_token = None

    while len(all_docs) < max_docs:
        results = service.files().list(
            q=f"name contains '{prefix}' and mimeType='application/vnd.google-apps.document'",
            fields="files(id, name, modifiedTime), nextPageToken",
            pageSize=50,
            pageToken=page_token,
            orderBy="name",
        ).execute()

        all_docs.extend(results.get("files", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break

    logger.info("'%s' Docs: %d개 발견", prefix, len(all_docs))
    return all_docs


def read_doc_content(service, doc_id: str) -> str:
    """Google Docs 내용 읽기 (텍스트 추출)."""
    try:
        content = service.files().export(
            fileId=doc_id,
            mimeType="text/plain",
        ).execute()
        return content.decode("utf-8") if isinstance(content, bytes) else content
    except Exception as e:
        logger.warning("Doc 읽기 실패 (%s): %s", doc_id, e)
        return ""


def analyze_script(content: str, title: str) -> dict:
    """원고 기본 분석."""
    lines = content.split("\n")
    non_empty = [l for l in lines if l.strip()]

    return {
        "title": title,
        "total_chars": len(content),
        "total_lines": len(lines),
        "non_empty_lines": len(non_empty),
        "avg_line_length": sum(len(l) for l in non_empty) / max(len(non_empty), 1),
        "first_line": non_empty[0][:100] if non_empty else "",
        "has_chapters": any("챕터" in l or "Chapter" in l or "##" in l for l in lines),
    }


def build_analysis_prompt(scripts_summary: str, youtube_data: str) -> str:
    """Claude 에이전트에게 전달할 분석 프롬프트."""
    vault_dir = os.getenv("KAIROS_VAULT_DIR", "")

    return f"""# 세모지 콘텐츠 심층 분석

당신은 YouTube 콘텐츠 분석 전문가입니다. 세모지 채널의 원고와 성과 데이터를 교차 분석하세요.

## ⚠️ 중요 주의사항
- **한글 원고가 오리지널**입니다. 영어 원고는 별도 번역 프로젝트의 번역본이므로 분석에서 제외하세요.
- "영어→한글 전환"이 아닙니다. 처음부터 한글로 작성됨.
- 영어 원고와 한글 원고가 같은 Drive에 섞여 있으니 혼동하지 마세요.

## 원고 데이터 (Google Drive에서 추출)
{scripts_summary}

## YouTube 성과 데이터
{youtube_data}

## 분석 과제

### 1. 시간순 원고 진화 분석
- 초기(B001~B050) vs 중기(B050~B150) vs 최근(B150~B215) 원고 비교
- 문장 길이, 분량, 구성 방식의 변화
- 오프닝 훅 스타일의 변화 (첫 문장/첫 단락)
- 언제 가장 큰 변화가 있었는지

### 2. 성과 상관관계
- 조회수 상위 20% 영상의 원고 특징
- 조회수 하위 20% 영상의 원고 특징
- 구성 패턴(챕터 수, 분량)과 성과의 상관관계
- 장편 시리즈 vs 단편의 성과 차이

### 3. 문체/스토리텔링 패턴
- 세모지만의 고유 문체 특징 (어투, 용어, 문장 구조)
- 오프닝 훅 유형 분류 (질문형, 반전형, 숫자형 등)
- 스토리 아크 구조 (기승전결, 연대기, 미스터리 등)
- 감정 곡선 패턴

### 4. 개선 방향 제시
- 성과 좋았던 패턴 → 강화 권고
- 아쉬웠던 패턴 → 구체적 개선 방향
- 향후 콘텐츠 제작에 적용할 가이드라인

## 출력

분석 결과를 아래 파일들로 저장하세요:

1. `{vault_dir}/channels/세모지/analysis/script-evolution.md` — 시간순 진화 분석
2. `{vault_dir}/channels/세모지/analysis/performance-correlation.md` — 성과 상관관계
3. `{vault_dir}/channels/세모지/analysis/storytelling-patterns.md` — 문체/스토리텔링 패턴
4. `{vault_dir}/channels/세모지/analysis/improvement-guide.md` — 개선 가이드

모든 파일에 [[위키링크]]로 상호 연결하세요.
"""


def main():
    from auto_agent.modules.discord_bot_notify import DiscordBotNotify
    from auto_agent.modules.agent_runner import AgentRunner

    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    vault_dir = os.getenv("KAIROS_VAULT_DIR", "")

    logger.info("=== 세모지 콘텐츠 분석 시작 ===")

    bot = DiscordBotNotify(channel_id=DISCORD_NOTIFY_CHANNEL)
    thread_id = bot.create_thread(f"[{today}] 세모지 콘텐츠 심층 분석")
    bot.send_to_thread("🔍 **세모지 콘텐츠 심층 분석 시작!**\n\n단계:\n1. Google Drive 원고 수집\n2. YouTube 성과 데이터 수집\n3. Claude 에이전트 교차 분석")

    # 1. Drive에서 원고 수집
    logger.info("Drive 원고 수집 시작...")
    bot.send_to_thread("📄 Step 1: Google Drive 원고 수집 중...")
    service = get_drive_service()

    all_scripts = []
    for prefix in ["B0", "B1", "B2", "C0", "P0"]:
        docs = fetch_all_scripts(service, prefix, max_docs=50)
        all_scripts.extend(docs)

    bot.send_to_thread(f"📄 원고 {len(all_scripts)}개 발견. 내용 읽는 중...")

    # 샘플 원고 읽기 (전체 읽으면 너무 오래 걸림)
    scripts_data = []
    sample_indices = list(range(0, len(all_scripts), max(1, len(all_scripts) // 30)))  # 30개 샘플
    for i in sample_indices:
        doc = all_scripts[i]
        content = read_doc_content(service, doc["id"])
        if content:
            analysis = analyze_script(content, doc["name"])
            analysis["content_preview"] = content[:2000]
            analysis["modified"] = doc.get("modifiedTime", "")
            scripts_data.append(analysis)

    logger.info("원고 %d개 읽기 완료 (샘플 %d개)", len(all_scripts), len(scripts_data))
    bot.send_to_thread(f"📄 원고 {len(scripts_data)}개 샘플 읽기 완료")

    # 2. YouTube 성과 데이터
    logger.info("YouTube 성과 데이터 수집...")
    bot.send_to_thread("📊 Step 2: YouTube 성과 데이터 수집 중...")

    from auto_agent.modules.data_collector.youtube_analytics import YouTubeAnalytics
    yt = YouTubeAnalytics("semoji")
    yt_info = yt.get_channel_info()
    yt_videos = yt.get_recent_videos(max_results=50)

    youtube_summary = f"채널: {yt_info['channel_name'] if yt_info else '세모지'}\n"
    youtube_summary += f"구독자: {yt_info['subscribers']:,}\n\n" if yt_info else ""
    youtube_summary += "최근 영상 성과:\n"
    for v in yt_videos:
        youtube_summary += f"- {v['title'][:50]} | 조회수: {v['views']:,} | 좋아요: {v['likes']:,}\n"

    bot.send_to_thread(f"📊 YouTube 영상 {len(yt_videos)}개 성과 수집 완료")

    # 3. 원고 요약 생성
    scripts_summary = f"총 원고 수: {len(all_scripts)}개 (브랜드백과 B*, 상식백과 C*, 인물백과 P*)\n"
    scripts_summary += f"샘플 분석: {len(scripts_data)}개\n\n"

    for s in scripts_data:
        scripts_summary += f"### {s['title']}\n"
        scripts_summary += f"- 분량: {s['total_chars']:,}자, {s['non_empty_lines']}줄\n"
        scripts_summary += f"- 평균 줄 길이: {s['avg_line_length']:.0f}자\n"
        scripts_summary += f"- 첫 줄: {s['first_line']}\n"
        scripts_summary += f"- 내용 미리보기:\n{s['content_preview'][:500]}\n\n"

    # 4. Claude 에이전트 분석
    logger.info("Claude 에이전트 분석 시작...")
    bot.send_to_thread("🧠 Step 3: Claude 에이전트 교차 분석 중... (10~15분 소요)")

    prompt = build_analysis_prompt(scripts_summary, youtube_summary)

    # 분석 디렉토리 생성
    analysis_dir = Path(vault_dir) / "channels" / "세모지" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    runner = AgentRunner()
    config = {"model": "opus", "max_turns": 50, "max_duration_minutes": 30}
    result = runner._run_agent(prompt, config, extra_tools=["WebSearch", "WebFetch"])

    usage = result.get("usage", {})
    cost = usage.get("total_cost_usd", 0)

    if result["status"] == "success":
        logger.info("분석 완료 — $%.4f", cost)
        bot.send_to_thread(
            f"✅ **분석 완료!** (${cost:.4f})\n\n"
            f"생성된 파일:\n"
            f"- `channels/세모지/analysis/script-evolution.md`\n"
            f"- `channels/세모지/analysis/performance-correlation.md`\n"
            f"- `channels/세모지/analysis/storytelling-patterns.md`\n"
            f"- `channels/세모지/analysis/improvement-guide.md`"
        )
        bot.send_to_channel(f"✅ **[{today}] 세모지 콘텐츠 심층 분석 완료** — 스레드에서 확인")
    else:
        logger.error("분석 실패: %s", result.get("stderr", "")[:200])
        bot.send_to_thread(f"❌ 분석 실패: {result.get('stderr', '')[:200]}")

    logger.info("=== 세모지 콘텐츠 분석 종료 ===")


if __name__ == "__main__":
    main()
