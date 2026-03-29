"""Solutioner 심화 학습 — Auto Kairos 정리 + 해외 사례 + 발전 방향."""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).resolve().parent.parent.parent / "logs" / "solutioner-deep.log",
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

STUDY_ROUNDS = [
    {
        "round": 1,
        "topic": "Auto Kairos 실제 파이프라인 정리",
        "prompt": """Auto Kairos v3의 실제 파이프라인을 정리하세요.

먼저 프로젝트 파일을 읽어서 실제 구조를 파악하세요:
- auto_agent/data/agents.json (에이전트 정의)
- auto_agent/data/pipeline.json (파이프라인 설정, 있으면)
- CLAUDE.md (프로젝트 규칙)
- auto_agent/modules/ 디렉토리 구조

정리할 내용:
### 파이프라인 구조
- Stage 0: trend-analyst (AutoResearch, 카파시 루프)
- Stage 1: research-orchestrator (심층 리서치)
- Stage 2: script-director (원고+연출) + data-mapper + fact-verifier
- Stage 3: assembly-director (TTS+이미지+자막+렌더링)
- Stage 4: performance-analyst (성과 분석)

### 기술 스택
- 에이전트: Claude CLI (Sonnet/Opus)
- TTS: ElevenLabs (primary) / Gemini TTS (fallback)
- 이미지: FAL.ai (생성) / Serper (검색)
- 자막: WhisperX
- 렌더링: Remotion
- 데이터: Obsidian 볼트 + Supabase
- 알림: Discord Bot API (스레드 기반)

### 특수 기법
- 카파시 AutoResearch 루프 (래칫, 점수 체계)
- scene_specs 플랫 스키마
- SceneRenderer 단일 소스
- 디자인 토큰 시스템

출력: solutioner/patterns/auto-kairos-pipeline.md""",
    },
    {
        "round": 2,
        "topic": "해외 AI 영상 자동화 사례 (미국/유럽/일본/중국)",
        "prompt": """해외에서 AI를 활용한 YouTube/영상 콘텐츠 자동화 사례를 심층 조사하세요.

검색 키워드:
- "AI video production automation"
- "automated YouTube channel AI"
- "AI content creation pipeline"
- "faceless YouTube channel automation"
- "AI video generation startup"
- "中国 AI 视频制作" (중국)
- "AI動画制作 自動化" (일본)

조사 대상:
### 미국/유럽
- Synthesia (AI 아바타 영상)
- HeyGen (AI 영상 번역/더빙)
- Runway ML (AI 영상 생성)
- Pika Labs
- Eleven Labs 풀 파이프라인 사례
- 'Faceless Channel' 자동화 트렌드

### 중국
- 快影/剪映 (CapCut AI 자동 편집)
- 小红书 AI 콘텐츠 자동화
- Bilibili AI 크리에이터 도구
- 즈후(知乎) AI 지식 콘텐츠

### 일본
- VTuber AI 자동화
- NHK/민방 AI 뉴스 자동화
- 일본 교육 콘텐츠 AI

### 공통 분석
- 각 사례의 파이프라인 구조 (리서치→원고→제작 과정)
- Auto Kairos 대비 차이점 (뭘 더 잘하고, 뭘 못하는지)
- 우리가 배울 수 있는 기법
- 비용 구조 비교

출력: solutioner/patterns/global-ai-video-cases.md""",
    },
    {
        "round": 3,
        "topic": "Auto Kairos 발전 방향 + 시나리오 시뮬레이션",
        "prompt": """Auto Kairos의 발전 방향을 제시하고 가상 시나리오를 시뮬레이션하세요.

먼저 solutioner/ 에 축적된 기술 지식과 auto-kairos-pipeline.md를 읽으세요.

### 발전 방향 제시 (3-5개)
각 방향에 대해:
- 현재 상태 vs 목표 상태
- 필요한 기술/도구
- 구현 난이도 / 비용 / 기간
- 기대 효과

예시 방향:
1. 완전 자율 운영 (사람 개입 0 → 기획부터 업로드까지)
2. 멀티채널 동시 운영 (이로미즘+세모지+신규 채널 N개)
3. 실시간 트렌드 반응 (트렌드 감지 → 24시간 내 영상 자동 제작)
4. 다국어 확장 (한국어 → 영어/일본어/중국어 자동 번역+더빙)
5. AI 아바타/가상 진행자 도입

### 시나리오 시뮬레이션 (3개)

**시나리오 1: "6개월 후 최적 상태"**
- 매일 자동 기획 → 주 3회 자동 업로드
- 성과 피드백 루프 완성
- 예상 구독자/조회수 성장

**시나리오 2: "1년 후 최대 확장"**
- 5개 채널 동시 운영
- 다국어 콘텐츠
- AI 아바타 도입
- 월 비용 vs 수익 시뮬레이션

**시나리오 3: "기술 한계 돌파"**
- 현재 기술로 불가능한 것 (감정 표현, 창의적 연출 등)
- 1-2년 내 해결 가능성 (모델 발전 속도 기준)
- 돌파 시 어떤 변화가 오는지

출력: solutioner/solutions/auto-kairos-roadmap.md""",
    },
]


def run_study_round(round_info: dict, notifier) -> dict:
    from auto_agent.modules.agent_runner import AgentRunner

    round_num = round_info["round"]
    topic = round_info["topic"]
    vault_dir = os.getenv("KAIROS_VAULT_DIR", "")
    sol_dir = f"{vault_dir}/solutioner"

    logger.info("=== 라운드 %d/3: %s ===", round_num, topic)
    notifier.send_to_thread(f"🔍 **라운드 {round_num}/3** 시작: {topic}")

    base_prompt = f"""# Solutioner 심화 학습 — 라운드 {round_num}: {topic}

볼트 경로: {sol_dir}/
프로젝트 루트: {PROJECT_ROOT}/

{round_info["prompt"]}

## 규칙
- WebSearch로 최신 해외 정보 검색 필수
- 프로젝트 파일을 직접 읽어서 실제 구조 파악
- 기존 solutioner/ 노트와 [[위키링크]] 연결
- 출처 URL 필수
- 구체적 수치와 비교 데이터 포함
"""

    runner = AgentRunner()
    config = {"model": "sonnet", "max_turns": 50, "max_duration_minutes": 25}

    result = runner._run_agent(
        base_prompt, config,
        extra_tools=["WebSearch", "WebFetch"],
    )

    usage = result.get("usage", {})
    cost = usage.get("total_cost_usd", 0)
    duration = usage.get("duration_ms", 0) / 1000

    if result["status"] == "success":
        logger.info("라운드 %d 완료 — $%.4f, %.0fs", round_num, cost, duration)
        notifier.send_to_thread(f"✅ **라운드 {round_num}/3 완료**: {topic}\n💰 ${cost:.4f} | ⏱️ {duration:.0f}s")
    elif result["status"] == "timeout":
        logger.warning("라운드 %d 타임아웃", round_num)
        notifier.send_to_thread(f"⏱️ **라운드 {round_num}/3 타임아웃**: {topic}")
    else:
        logger.error("라운드 %d 실패", round_num)
        notifier.send_to_thread(f"❌ **라운드 {round_num}/3 실패**: {topic}")

    return result


def main():
    from auto_agent.modules.discord_bot_notify import DiscordBotNotify

    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("=== Solutioner 심화 학습 시작 (3라운드) ===")

    bot = DiscordBotNotify(channel_id=DISCORD_NOTIFY_CHANNEL)
    thread_id = bot.create_thread(f"[{today}] Solutioner 심화 학습")

    if thread_id:
        bot.send_to_thread(
            "🧠 **심화 학습 시작!**\n\n"
            "1. Auto Kairos 실제 파이프라인 정리\n"
            "2. 해외 AI 영상 자동화 사례 (미국/유럽/일본/중국)\n"
            "3. 발전 방향 + 시나리오 시뮬레이션"
        )

    total_cost = 0
    success = 0
    for round_info in STUDY_ROUNDS:
        result = run_study_round(round_info, bot)
        cost = result.get("usage", {}).get("total_cost_usd", 0)
        total_cost += cost
        if result["status"] == "success":
            success += 1
        time.sleep(10)

    logger.info("=== 심화 학습 완료 (%d/3 성공, $%.4f) ===", success, total_cost)

    bot.send_to_thread(
        f"🎉 **심화 학습 완료!**\n\n"
        f"성공: {success}/3 라운드\n"
        f"총 비용: ${total_cost:.4f}\n\n"
        f"생성된 파일:\n"
        f"- `patterns/auto-kairos-pipeline.md`\n"
        f"- `patterns/global-ai-video-cases.md`\n"
        f"- `solutions/auto-kairos-roadmap.md`"
    )

    bot.send_to_channel(
        f"✅ **[{today}] Solutioner 심화 학습 완료** — "
        f"{success}/3 성공, ${total_cost:.4f} → 스레드에서 확인"
    )


if __name__ == "__main__":
    main()
