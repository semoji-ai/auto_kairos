"""Solutioner 초기 학습 — 기반 지식 10라운드 집중 구축."""
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
            Path(__file__).resolve().parent.parent.parent / "logs" / "solutioner-initial.log",
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
        "topic": "Claude Code 핵심 기능 딥다이브",
        "prompt": """Claude Code의 전체 기능을 체계적으로 정리하세요.

검색 키워드: "Claude Code features", "Claude Code MCP", "Claude Code skills", "Claude Code hooks", "Claude Code agent SDK"

정리할 내용:
- MCP (Model Context Protocol): 개념, 서버 연결 방식, 사용 가능한 도구
- 스킬 시스템: 슬래시 커맨드, SKILL.md 작성법, 트리거 조건
- 훅 시스템: pre/post 훅, 자동화 동작 설정
- 에이전트 SDK: 서브에이전트, 병렬 실행, worktree 격리
- 권한 시스템: allow/deny, auto-mode, 도구별 제어
- 플러그인: 마켓플레이스, 설치/업데이트
- CLI 옵션: --print, --output-format, --model, --max-turns

출력: solutioner/models/claude-code.md""",
    },
    {
        "round": 2,
        "topic": "MCP 생태계 카탈로그 (상위 50개)",
        "prompt": """MCP (Model Context Protocol) 생태계의 주요 서버를 카탈로그화하세요.

검색: "awesome MCP servers", "MCP server list", "modelcontextprotocol servers github"

카테고리별로 정리:
- 데이터베이스: PostgreSQL, SQLite, MongoDB MCP
- 클라우드: AWS, GCP, Azure MCP
- 개발도구: GitHub, GitLab, Docker MCP
- 커뮤니케이션: Slack, Discord, Email MCP
- 생산성: Notion, Google Drive, Calendar MCP
- AI/ML: 이미지생성, TTS, STT MCP
- 파일시스템: 로컬, S3, NAS MCP
- 웹: 브라우저, 스크래핑, 검색 MCP

각 서버: 이름, GitHub URL, 설명, 설치법, 활용 시나리오

출력: solutioner/tools/mcp-catalog.md""",
    },
    {
        "round": 3,
        "topic": "에이전트 프레임워크 비교",
        "prompt": """주요 AI 에이전트 프레임워크를 비교 분석하세요.

검색: "AI agent framework comparison 2026", "LangChain vs CrewAI vs AutoGen"

분석 대상:
- LangChain / LangGraph — 체인 기반, 그래프 워크플로우
- CrewAI — 역할 기반 멀티에이전트
- AutoGen (Microsoft) — 대화 기반 에이전트
- Dify — 로우코드 AI 앱 빌더
- Claude Agent SDK — Anthropic 공식
- OpenAI Agents — GPT 기반 에이전트
- Mastra — TypeScript 에이전트 프레임워크

각 프레임워크: 아키텍처, 강점, 약점, 적합한 사용 사례, 비용, 커뮤니티 규모

출력: solutioner/tools/agent-frameworks.md""",
    },
    {
        "round": 4,
        "topic": "프롬프트 엔지니어링 검증된 패턴",
        "prompt": """실전에서 검증된 프롬프트 엔지니어링 패턴을 정리하세요.

검색: "prompt engineering patterns 2026", "advanced prompting techniques", "chain of thought examples"

패턴 분류:
- 구조화: System/User/Assistant 역할 분리, XML 태그 구조
- 추론: Chain-of-Thought, Tree-of-Thought, Self-Consistency
- 분해: Task Decomposition, Step-by-Step
- 검증: Self-Verification, Chain-of-Verification
- 제어: Output Format Control, Few-Shot, Constrained Generation
- 멀티턴: Memory Management, Context Compression
- 에이전트: ReAct, Plan-and-Execute, Reflection

각 패턴: 설명, 예시, 적합한 모델, 효과

출력: solutioner/patterns/prompt-engineering.md""",
    },
    {
        "round": 5,
        "topic": "RAG/벡터DB 실전 패턴",
        "prompt": """RAG (Retrieval-Augmented Generation)과 벡터DB 실전 활용 패턴을 정리하세요.

검색: "RAG best practices 2026", "vector database comparison", "ChromaDB vs Pinecone vs Weaviate"

정리 내용:
- RAG 아키텍처: 기본 RAG, Advanced RAG, Modular RAG
- 청킹 전략: Fixed, Semantic, Recursive, Agentic Chunking
- 임베딩 모델: OpenAI, Cohere, BGE, sentence-transformers 비교
- 벡터DB: ChromaDB, Pinecone, Weaviate, Qdrant, Milvus 비교
- 검색 전략: Dense, Sparse, Hybrid, Reranking
- 평가: Faithfulness, Relevance, Context Recall 메트릭
- 실전 패턴: Multi-Query, HyDE, Parent Document Retriever
- Obsidian 볼트 RAG 구현 패턴

출력: solutioner/patterns/rag-patterns.md""",
    },
    {
        "round": 6,
        "topic": "노코드/자동화 도구 카탈로그",
        "prompt": """노코드/로우코드 자동화 도구를 카탈로그화하세요.

검색: "no code automation tools 2026", "n8n vs Zapier vs Make", "AI automation platforms"

분석 대상:
- 워크플로우: n8n, Zapier, Make (Integromat), Pipedream
- AI 앱 빌더: Dify, FlowiseAI, Langflow, Google Opal
- 데이터: Airtable, Notion, Google Sheets 자동화
- 웹사이트: Webflow, Framer, v0.dev
- 챗봇: Botpress, Voiceflow, Chatbase
- 비용 구간: 무료 / $10↓ / $50↓ / 엔터프라이즈

각 도구: 핵심 기능, 가격, AI 통합 방식, 적합한 사용 사례

출력: solutioner/tools/no-code-automation.md""",
    },
    {
        "round": 7,
        "topic": "Claude/GPT/Gemini 모델 상세 비교",
        "prompt": """현재 주요 AI 모델의 기능과 제한을 상세 비교하세요.

검색: "Claude vs GPT vs Gemini 2026 comparison", "Claude Opus 4.6 features", "GPT-5.4 capabilities", "Gemini 3 features"

비교 항목:
- 모델별 라인업 (tier별 가격/성능)
- 컨텍스트 윈도우 크기
- 멀티모달 지원 범위 (텍스트/이미지/오디오/비디오)
- 코딩 능력 벤치마크
- 추론 능력
- 도구 사용 (Function Calling, MCP)
- API 가격 비교 (input/output/cache)
- 고유 기능 (Claude: Artifacts, MCP / GPT: DALL-E, Actions / Gemini: 긴 컨텍스트, NotebookLM)
- 약점과 한계

기존 solutioner/models/ 의 claude.md, gpt.md, gemini.md 업데이트

출력: solutioner/models/ 각 파일 업데이트""",
    },
    {
        "round": 8,
        "topic": "Discord 봇 + AI 통합 패턴",
        "prompt": """Discord 봇과 AI를 통합하는 실전 패턴을 정리하세요.

검색: "Discord bot AI integration", "Discord Claude bot", "Discord automation patterns"

정리 내용:
- Discord Bot API 핵심 (메시지, 스레드, 리액션, 임베드, 파일)
- Discord + Claude Code 연동 (현재 플러그인 방식)
- Discord + LLM 자동응답 패턴
- 피드백 수집 → 자동 반영 루프
- 팀 협업 봇 패턴 (작업 할당, 리뷰 요청, 알림)
- 웹훅 vs 봇 토큰 사용 분기
- Rate Limit 관리
- 오픈소스 Discord AI 봇 프로젝트 (GitHub)

출력: solutioner/patterns/discord-ai-integration.md""",
    },
    {
        "round": 9,
        "topic": "YouTube 자동화 + 콘텐츠 AI 파이프라인",
        "prompt": """YouTube 콘텐츠 제작 자동화 도구와 AI 파이프라인을 정리하세요.

검색: "YouTube automation AI 2026", "AI video production pipeline", "YouTube analytics API", "Remotion video generation"

정리 내용:
- YouTube Data API v3: 검색, 채널 분석, 댓글 수집
- YouTube Analytics API: CTR, 시청 지속, 유입 경로
- AI 영상 제작: Remotion, Revideo, Shotstack, Runway
- AI 음성: ElevenLabs, Google TTS, OpenAI TTS, Fish Audio
- AI 이미지: Midjourney, DALL-E, Stable Diffusion, FAL.ai, Flux
- AI 자막: WhisperX, AssemblyAI, Deepgram
- AI 리서치: Perplexity, Tavily, deep-research
- 트렌드 분석: Google Trends API, VidIQ, TubeBuddy
- 경쟁 분석: Social Blade, Playboard

출력: solutioner/patterns/youtube-ai-pipeline.md""",
    },
    {
        "round": 10,
        "topic": "오픈소스 Claude Code 스킬/플러그인 에코시스템",
        "prompt": """Claude Code 생태계의 오픈소스 스킬과 플러그인을 조사하세요.

검색: "Claude Code skills github", "Claude Code plugins marketplace", "awesome claude code", "superpowers claude code"

정리 내용:
- 공식 마켓플레이스 플러그인 목록
- obra/superpowers: 스킬 전체 분석 (brainstorming, TDD, subagent 등)
- fivetaku/deep-research-kit: 딥리서치 파이프라인
- 커뮤니티 스킬 모음 (GitHub 검색)
- MCP 서버 중 Claude Code 특화
- 스킬 작성 가이드 (writing-skills 패턴)
- CLAUDE.md 작성 베스트 프랙티스
- 훅(hooks) 활용 사례

기존 solutioner/tools/claude-skills.md가 없으면 생성

출력: solutioner/tools/claude-code-ecosystem.md""",
    },
]


def run_study_round(round_info: dict, notifier) -> dict:
    """단일 스터디 라운드 실행."""
    from auto_agent.modules.agent_runner import AgentRunner

    round_num = round_info["round"]
    topic = round_info["topic"]
    vault_dir = os.getenv("KAIROS_VAULT_DIR", "")
    sol_dir = f"{vault_dir}/solutioner"

    logger.info("=== 라운드 %d/10: %s ===", round_num, topic)
    notifier.send_to_thread(f"🔍 **라운드 {round_num}/10** 시작: {topic}")

    base_prompt = f"""# Solutioner 초기 학습 — 라운드 {round_num}: {topic}

당신은 AI 기술 리서치 에이전트입니다. 아래 주제를 깊이 조사하고 볼트에 정리하세요.

볼트 경로: {sol_dir}/

{round_info["prompt"]}

## 규칙
- WebSearch로 최신 정보 검색 필수
- 모든 노트에 [[위키링크]]로 관련 노트 연결
- 출처 URL 필수
- 기존 파일이 있으면 업데이트 (덮어쓰기 아님, 내용 추가)
- "활용 가능성"은 구체적으로 기술
"""

    runner = AgentRunner()
    config = {"model": "sonnet", "max_turns": 40, "max_duration_minutes": 20}

    result = runner._run_agent(
        base_prompt, config,
        extra_tools=["WebSearch", "WebFetch"],
    )

    usage = result.get("usage", {})
    cost = usage.get("total_cost_usd", 0)
    duration = usage.get("duration_ms", 0) / 1000

    if result["status"] == "success":
        logger.info("라운드 %d 완료 — $%.4f, %.0fs", round_num, cost, duration)
        notifier.send_to_thread(
            f"✅ **라운드 {round_num}/10 완료**: {topic}\n"
            f"💰 ${cost:.4f} | ⏱️ {duration:.0f}s"
        )
    elif result["status"] == "timeout":
        logger.warning("라운드 %d 타임아웃", round_num)
        notifier.send_to_thread(f"⏱️ **라운드 {round_num}/10 타임아웃**: {topic}")
    else:
        logger.error("라운드 %d 실패", round_num)
        notifier.send_to_thread(f"❌ **라운드 {round_num}/10 실패**: {topic}")

    return result


def main():
    from auto_agent.modules.discord_bot_notify import DiscordBotNotify

    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("=== Solutioner 초기 학습 시작 (10라운드) ===")

    bot = DiscordBotNotify(channel_id=DISCORD_NOTIFY_CHANNEL)
    thread_id = bot.create_thread(f"[{today}] Solutioner 초기 학습 (10라운드)")

    if thread_id:
        bot.send_to_thread(
            "🧠 **Solutioner 초기 학습 시작!**\n\n"
            "10개 주제를 순차 학습합니다:\n"
            + "\n".join(f"{r['round']}. {r['topic']}" for r in STUDY_ROUNDS)
        )

    total_cost = 0
    success = 0
    for round_info in STUDY_ROUNDS:
        result = run_study_round(round_info, bot)
        cost = result.get("usage", {}).get("total_cost_usd", 0)
        total_cost += cost
        if result["status"] == "success":
            success += 1
        time.sleep(10)  # 라운드 간 짧은 대기

    logger.info("=== 초기 학습 완료 (%d/10 성공, $%.4f) ===", success, total_cost)

    # 스레드에 최종 결과
    bot.send_to_thread(
        f"🎉 **Solutioner 초기 학습 완료!**\n\n"
        f"성공: {success}/10 라운드\n"
        f"총 비용: ${total_cost:.4f}\n"
        f"→ 볼트 solutioner/ 확인"
    )

    # 채널에도 알림
    bot.send_to_channel(
        f"✅ **[{today}] Solutioner 초기 학습 완료** — "
        f"{success}/10 성공, ${total_cost:.4f} → 스레드에서 확인"
    )


if __name__ == "__main__":
    main()
