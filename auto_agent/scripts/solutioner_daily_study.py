"""Solutioner Daily Study — AI 기술 지식 자동 축적."""
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
            Path(__file__).resolve().parent.parent.parent / "logs" / "solutioner-study.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_NOTIFY_CHANNEL = os.getenv("DISCORD_SOLUTIONER_CHANNEL_ID", "1486738313468706987")


def build_study_prompt() -> str:
    """Daily Study 프롬프트 생성."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    vault_path = os.getenv("KAIROS_VAULT_DIR", "")
    sol_dir = f"{vault_path}/solutioner" if vault_path else "solutioner"

    return f"""# Solutioner Daily Study — {today}

당신은 AI 기술 리서치 에이전트입니다. 아래 소스에서 최신 AI 기술/도구/패턴을 스캔하고 정리하세요.

## 스캔 소스

### 1. Threads/X 크리에이터 (WebSearch)
- open.choi — AI 활용 인사이트
- aicoffeechat — AI 트렌드/팁
- unclejobs.ai — AI 실무 활용
- gptaku (fivetaku) — 스킬 개발, deep-research 등

각 크리에이터의 최근 게시물을 검색하세요:
- "open.choi threads AI" / "aicoffeechat threads" 등으로 WebSearch
- 최근 1주일 내 게시물 중 유용한 것 요약

### 2. GitHub Trending (WebSearch)
- "github trending AI" 또는 "github trending machine learning"
- 상위 10개 저장소 중 실용적인 것 선별
- 특히 MCP 서버, Claude 스킬, 에이전트 프레임워크에 주목

### 3. 공식 블로그 (WebSearch)
- "Anthropic blog latest" — Claude 신기능
- "OpenAI blog latest" — GPT 업데이트
- "Google AI blog latest" — Gemini 업데이트

## 출력

### 1. 일일 로그 파일
**⚠️ 기존 파일이 있으면 먼저 읽고, 기존 내용 아래에 새 발견을 추가(append)하세요. 덮어쓰지 마세요.**
`{sol_dir}/daily/{today}.md` 에 저장 (누적):

```markdown
---
date: {today}
new_discoveries: N
combination_ideas: N
---

# Daily Study — {today}

## 🆕 새 발견

### [카테고리: model/tool/pattern/insight] 제목
- **출처**: URL 또는 소스
- **요약**: 한 줄 요약
- **활용 가능성**: Auto Kairos 또는 일반 프로젝트에서 어떻게 쓸 수 있는지
- **관련 노트**: [[기존 노트]] 위키링크

(발견마다 반복)

## 💡 조합 아이디어

기존 solutioner/ 지식과 오늘 발견을 교차하여 새로운 조합 가능성을 기록:
- [아이디어 제목]: 기존 [[A]] + 새 발견 B = 새로운 가능성 C

## 📊 요약
- 스캔한 소스: N개
- 새 발견: N개 (model: N, tool: N, pattern: N, insight: N)
- 조합 아이디어: N개
```

### 2. 카탈로그 업데이트
새로운 도구/모델을 발견하면 해당 카탈로그 파일도 업데이트:
- 새 도구 → `{sol_dir}/tools/` 에 추가 또는 기존 파일 업데이트
- 새 모델 기능 → `{sol_dir}/models/` 업데이트
- 새 패턴 → `{sol_dir}/patterns/` 에 노트 생성

### 3. 기존 지식 확인
먼저 `{sol_dir}/` 디렉토리를 읽어서 현재 축적된 지식 수준을 파악하세요.
이미 있는 내용은 중복 기록하지 않고, 새로운 정보만 추가합니다.

## 규칙
- 모든 노트에 [[위키링크]]로 관련 노트 연결
- 출처 URL 필수
- "활용 가능성"은 구체적으로 (단순 "유용할 수 있다" 금지)
- 검증되지 않은 정보는 "미검증" 태그 추가
"""


def run_study():
    """Claude CLI로 Daily Study 실행."""
    from auto_agent.modules.agent_runner import AgentRunner

    logger.info("=== Solutioner Daily Study 시작 ===")

    prompt = build_study_prompt()

    runner = AgentRunner()
    config = {"model": "sonnet", "max_turns": 30, "max_duration_minutes": 15}

    result = runner._run_agent(
        prompt, config,
        extra_tools=["WebSearch", "WebFetch"],
    )

    if result["status"] == "success":
        usage = result.get("usage", {})
        cost = usage.get("total_cost_usd", 0)
        logger.info("Daily Study 완료 — $%.4f", cost)
    else:
        logger.error("Daily Study 실패: %s", result.get("stderr", "")[:200])

    return result


def send_digest():
    """디스코드에 스레드 단위로 일일 요약 전송."""
    from auto_agent.modules.discord_bot_notify import DiscordBotNotify

    vault_dir = os.getenv("KAIROS_VAULT_DIR", "")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_file = Path(vault_dir) / "solutioner" / "daily" / f"{today}.md"

    if not daily_file.exists():
        logger.warning("오늘 스터디 결과 없음: %s", daily_file)
        return

    content = daily_file.read_text(encoding="utf-8")

    # 섹션별 추출
    discoveries = []
    combos = []
    summary_text = ""

    current_section = None
    current_item = []

    for line in content.split("\n"):
        if "## 🆕 새 발견" in line:
            current_section = "discovery"
        elif "## 💡 조합 아이디어" in line:
            current_section = "combo"
        elif "## 📊 요약" in line:
            current_section = "summary"
        elif current_section == "discovery" and line.startswith("### ["):
            discoveries.append(line.replace("### ", ""))
        elif current_section == "combo" and line.startswith("- **["):
            combos.append(line)
        elif current_section == "summary" and not line.startswith("##"):
            summary_text += line + "\n"

    bot = DiscordBotNotify(channel_id=DISCORD_NOTIFY_CHANNEL)

    # 스레드 생성
    thread_name = f"[{today}] Solutioner Daily Study"
    thread_id = bot.create_thread(thread_name)

    if thread_id:
        # 새 발견
        if discoveries:
            disc_text = "\n".join(discoveries[:12])
            bot.send_to_thread(f"🆕 **새 발견 ({len(discoveries)}개)**\n\n{disc_text}")

        # 조합 아이디어
        if combos:
            combo_text = "\n".join(combos)
            bot.send_to_thread(f"💡 **조합 아이디어 ({len(combos)}개)**\n\n{combo_text}")

        # 요약
        bot.send_to_thread(f"📊 **요약**\n{summary_text[:1500]}\n→ 상세: solutioner/daily/{today}.md")

        # 채널에도 완료 알림
        bot.send_to_channel(
            f"📚 **[{today}] Solutioner Daily Study 완료** — "
            f"발견 {len(discoveries)}개, 조합 {len(combos)}개 "
            f"→ 스레드에서 확인"
        )
    else:
        # 스레드 생성 실패 시 채널에 직접
        bot.send_to_channel(
            f"📚 **Solutioner Daily Digest** ({today})\n\n"
            f"🆕 새 발견: {len(discoveries)}개\n"
            f"💡 조합 아이디어: {len(combos)}개\n\n"
            f"{summary_text[:1500]}\n"
            f"→ 상세: solutioner/daily/{today}.md"
        )


def main():
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    result = run_study()

    if result["status"] == "success":
        send_digest()

    logger.info("=== Solutioner Daily Study 종료 ===")


if __name__ == "__main__":
    main()
