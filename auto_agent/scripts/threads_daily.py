"""세모지 Threads 일일 콘텐츠 생성 — 에이전트 기반.

매일 KST 07:00 (UTC 22:00) 실행.
볼트에서 어제 작업 로그 → 5-6개 포스트 생성 → threads_posts.json 저장.

Usage:
  python -m auto_agent.scripts.threads_daily
"""
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass


def main():
    logger.info("=== Threads Daily 시작 ===")

    vault_dir = Path(os.environ.get(
        "KAIROS_VAULT_DIR",
        os.path.expanduser("~/Desktop/kairos-vault"),
    ))
    workspace = Path(__file__).resolve().parent.parent.parent
    output_dir = workspace / "output" / "threads"
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 볼트에서 최근 세션 로그 수집
    session_context = _load_recent_sessions(vault_dir)

    # 2. Qwen 래칫 결과 수집
    qwen_context = _load_qwen_results(vault_dir)

    # 3. 파이프라인 실행 로그 수집
    pipeline_context = _load_pipeline_logs(workspace)

    # 4. Claude 에이전트로 포스트 생성
    prompt = f"""당신은 세모지 채널의 Threads 콘텐츠 작성 에이전트입니다.
AI를 활용한 유튜브 교양 영상 제작 과정을 공유하는 계정입니다.

아래 오늘의 작업 로그를 바탕으로 Threads 포스트 5-6개를 작성하세요.

## 오늘의 작업 로그:
{session_context}

## Qwen 인턴 학습 결과:
{qwen_context}

## 파이프라인 실행 로그:
{pipeline_context}

## 카테고리별 작성 (5-6개):
1. 영상 공개형 또는 AI 쉬운 활용법 — 2개
2. 인사이트/효과적 방법론 — 2개
3. 새 기술 적용 또는 비하인드 — 2개

## 훅(첫 줄) 공식 — 반드시 아래 5가지 중 하나:
A. 속보형: "🎬 [주제] — [충격적 사실]" (이모지 1개로 시선 확보)
B. 숫자형: "[구체적 수치]로 시작" (예: "290원으로 영상 한 편을 만들었습니다")
C. 문제 제기형: "[논쟁적 명제]" (예: "AI가 만든 영상은 진짜 콘텐츠일까요?")
D. 리스트형: "[N가지] [카테고리]" (예: "AI 영상 제작에서 가장 많이 실수하는 3가지")
E. 경험 스토리형: "[내가 직접 해본 결과]" (예: "원고를 5번 고쳐봤더니 달라진 것")

## 체인 구조:
- 메인 글(Hook): 멈추게 하는 1-2줄. 구체적 수치나 고유명사 필수.
- 답글 1 (본론): 구체적 방법이나 과정 설명 3-5줄. 경험 기반.
- 답글 2 (증거): 수치, 비교, before/after. "~했더니 ~됐습니다" 형태.
- 답글 3 (심화 정보): 팔로우 요청 금지. 대신:
  - 본문 주제와 관련된 추가 정보/팁/참고 자료 제공
  - 관련 GitHub 레포, 도구, 논문, 영상 링크가 있으면 포함
  - "더 알고 싶으시면 이쪽을 참고해보세요" 형태
  - 독자가 "이 체인을 읽어서 유익했다"고 느끼게 마무리

## 톤 & 스타일 규칙:
- **존댓말 필수** ("~입니다", "~했습니다", "~거든요", "~인 것 같습니다")
- 전문용어 → 쉬운 말 변환 (래칫→"AI가 AI를 채점", pipeline→"자동 제작 과정")
- 이모지 **1-2개만** (🎬, 😊 정도). 과다 사용 금지.
- 토픽 태그 **1개만** (2개 이상은 스팸 판정)
- 링크가 있으면 본문이 아닌 답글에 배치한다고 언급
- 같은 수치/에피소드를 2개 이상 포스트에서 반복하지 말 것

## 출력 형식 (JSON):
{{
  "date": "{today}",
  "posts": [
    {{
      "category": "easy_method|effective_method|new_tech|behind_data|video_release|insight",
      "hook_type": "A|B|C|D|E",
      "main_text": "메인 글 (Hook — 300자 이내)",
      "replies": [
        "답글 1: 본론 (3-5줄)",
        "답글 2: 수치/증거",
        "답글 3: CTA"
      ],
      "hashtags": ["#AI영상제작"],
      "scheduled_time": "HH:MM"
    }}
  ]
}}

JSON만 출력하세요.
"""

    try:
        result = subprocess.run(
            ["claude", "--print", "--model", "claude-sonnet-4-6",
             "--max-turns", "1", "-p", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=str(workspace),
        )
        response = result.stdout.strip()

        # JSON 추출
        import re
        json_match = re.search(r'\{[\s\S]*"posts"[\s\S]*\}', response)
        if json_match:
            posts_data = json.loads(json_match.group())
            output_path = output_dir / f"{today}-threads.json"
            output_path.write_text(
                json.dumps(posts_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info(f"포스트 {len(posts_data.get('posts', []))}개 생성 → {output_path}")

            # 웹훅 전송
            _send_webhook(posts_data)
        else:
            logger.error(f"JSON 파싱 실패: {response[:500]}")

    except Exception as e:
        logger.error(f"포스트 생성 실패: {e}")

    logger.info("=== Threads Daily 종료 ===")


def _load_recent_sessions(vault_dir: Path) -> str:
    """볼트에서 최근 세션 요약 로드."""
    sessions_dir = vault_dir / "09-memory" / "sessions"
    if not sessions_dir.exists():
        return "세션 로그 없음"

    files = sorted(sessions_dir.glob("*.md"), reverse=True)[:2]
    context = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        context.append(f"### {f.stem}\n{content[:1000]}")
    return "\n\n".join(context) if context else "세션 로그 없음"


def _load_qwen_results(vault_dir: Path) -> str:
    """Qwen 래칫 결과 로드."""
    ratchet_path = vault_dir / "qwen_memory" / "ratchet_state.json"
    if not ratchet_path.exists():
        return "Qwen 결과 없음"
    data = json.loads(ratchet_path.read_text(encoding="utf-8"))
    return json.dumps(data, ensure_ascii=False, indent=2)


def _load_pipeline_logs(workspace: Path) -> str:
    """최근 파이프라인 실행 로그 수집."""
    output_dir = workspace / "output"
    if not output_dir.exists():
        return "파이프라인 로그 없음"

    # 최근 프로젝트의 pipeline_state.json
    states = sorted(output_dir.glob("*/pipeline_state.json"), reverse=True)[:2]
    context = []
    for s in states:
        data = json.loads(s.read_text(encoding="utf-8"))
        project = s.parent.name
        context.append(f"프로젝트: {project}\n{json.dumps(data, ensure_ascii=False)[:500]}")
    return "\n\n".join(context) if context else "파이프라인 로그 없음"


def _send_webhook(posts_data: dict):
    """디스코드에 포스트별 스레드로 전송 — 체인 구조 미리보기."""
    import time as _time

    # 봇 토큰 기반 스레드 전송 시도
    threads_channel = os.environ.get("THREADS_DISCORD_CHANNEL_ID", "")
    if threads_channel:
        try:
            from auto_agent.modules.discord_bot_notify import DiscordBotNotify
            bot = DiscordBotNotify(channel_id=threads_channel)

            posts = posts_data.get("posts", [])
            today = posts_data.get("date", datetime.now().strftime("%Y-%m-%d"))

            # 요약 메시지
            bot.send_to_channel(f"## 📱 Threads 포스트 ({today}) — {len(posts)}개")
            _time.sleep(0.5)

            for i, p in enumerate(posts, 1):
                category = p.get("category", "")
                scheduled = p.get("scheduled_time", "")
                main_text = p.get("main_text", "")
                replies = p.get("replies", [])
                hashtags = " ".join(p.get("hashtags", []))

                # 메인 포스트 → 디스코드 스레드 생성
                thread_name = f"#{i} [{category}] {scheduled}"
                thread_id = bot.create_thread(thread_name)

                if thread_id:
                    # 메인 글
                    bot.send_to_thread(f"**메인 글:**\n{main_text}\n{hashtags}")
                    _time.sleep(0.3)

                    # 답글 체인
                    for j, reply in enumerate(replies, 1):
                        bot.send_to_thread(f"**답글 {j}:**\n{reply}")
                        _time.sleep(0.3)
                else:
                    # 스레드 생성 실패 → 채널에 직접
                    bot.send_to_channel(
                        f"**#{i} [{category}] {scheduled}**\n"
                        f"{main_text[:300]}\n{hashtags}"
                    )

                _time.sleep(0.5)  # rate limit 방지

            logger.info("디스코드 스레드 전송 완료")
            return
        except Exception as e:
            logger.warning(f"스레드 전송 실패, 웹훅 fallback: {e}")

    # fallback: 웹훅 (단일 메시지)
    import requests as _req
    webhook_url = os.environ.get("THREADS_DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return

    posts = posts_data.get("posts", [])
    preview = f"## 📱 오늘의 Threads 포스트 ({len(posts)}개)\n\n"
    for i, p in enumerate(posts, 1):
        preview += f"**{i}. [{p.get('category', '')}] {p.get('scheduled_time', '')}**\n"
        preview += f"{p.get('main_text', '')[:150]}\n"
        preview += f"{' '.join(p.get('hashtags', []))}\n\n"

    try:
        _req.post(webhook_url, json={"content": preview[:2000]}, timeout=10)
        logger.info("디스코드 웹훅 전송 완료")
    except Exception as e:
        logger.warning(f"웹훅 전송 실패: {e}")


if __name__ == "__main__":
    main()
