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
    prompt = f"""당신은 세모지 Threads 콘텐츠 작성 에이전트입니다.

아래 오늘의 작업 로그를 바탕으로 Threads 포스트 5-6개를 작성하세요.

## 오늘의 작업 로그:
{session_context}

## Qwen 인턴 학습 결과:
{qwen_context}

## 파이프라인 실행 로그:
{pipeline_context}

## 카테고리별 작성:
1. 빌딩 로그 2개 — 실제 작업 과정, 수치 포함
2. 툴/기술 팁 2개 — 따라할 수 있는 실전 팁
3. 속보/반응 1개 — 최신 AI 뉴스에 대한 의견
4. 비하인드/데이터 1개 — 비용, 시간, 성과 수치

## 규칙:
- 각 포스트 200자 이내
- 수치 필수 (시간, 비용, 점수)
- 겸손한 실험자 톤 ("해봤더니 이랬다")
- 해시태그 3-4개
- 이모지 최소

## 출력 형식 (JSON):
{{
  "date": "{today}",
  "posts": [
    {{
      "category": "building_log|tool_tip|breaking|behind_data",
      "text": "포스트 본문",
      "hashtags": ["#태그1", "#태그2"],
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
    """디스코드 웹훅으로 포스트 미리보기 전송."""
    import requests

    webhook_url = os.environ.get("KAIROS_DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return

    posts = posts_data.get("posts", [])
    preview = f"## 📱 오늘의 Threads 포스트 ({len(posts)}개)\n\n"
    for i, p in enumerate(posts, 1):
        preview += f"**{i}. [{p.get('category', '')}] {p.get('scheduled_time', '')}**\n"
        preview += f"{p.get('text', '')[:150]}\n"
        preview += f"{' '.join(p.get('hashtags', []))}\n\n"

    try:
        requests.post(webhook_url, json={"content": preview[:2000]}, timeout=10)
        logger.info("디스코드 웹훅 전송 완료")
    except Exception as e:
        logger.warning(f"웹훅 전송 실패: {e}")


if __name__ == "__main__":
    main()
