"""AutoResearch 반복 실행 스크립트 — Discord 스레드 기반 알림."""
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
            Path(__file__).resolve().parent.parent.parent / "logs" / "autoresearch.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

# 프로젝트 루트를 PYTHONPATH에 추가
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Discord 알림 채널 ID (Stage 0/4 결과용)
DISCORD_NOTIFY_CHANNEL = os.getenv("DISCORD_STAGE0_CHANNEL_ID", "1486738313468706987")

# 알림 인스턴스 (전역)
_notifier = None


def get_notifier():
    """Discord 봇 알림 인스턴스 (스레드 지원). 실패 시 웹훅 폴백."""
    global _notifier
    if _notifier is not None:
        return _notifier

    try:
        from auto_agent.modules.discord_bot_notify import DiscordBotNotify
        _notifier = DiscordBotNotify(channel_id=DISCORD_NOTIFY_CHANNEL)
        return _notifier
    except Exception as e:
        logger.warning("Discord 봇 초기화 실패: %s — 웹훅 폴백", e)
        return None


def notify_discord(message: str, to_thread: bool = True):
    """Discord로 알림. 스레드가 있으면 스레드에, 없으면 채널에 전송."""
    notifier = get_notifier()
    if notifier:
        if to_thread and notifier.thread_id:
            notifier.send_to_thread(message)
        else:
            notifier.send_to_channel(message)
        return

    # 웹훅 폴백
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook:
        return
    try:
        import requests
        chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
        for chunk in chunks:
            requests.post(webhook, json={"content": chunk}, timeout=10)
    except Exception as e:
        logger.warning("Discord 알림 실패: %s", e)


def format_results_summary(channel: str) -> str:
    """최신 autoresearch 결과를 요약 메시지로 포맷."""
    import unicodedata
    from auto_agent.paths import get_vault_dir
    vault = get_vault_dir()
    planning_dir = vault / "insights" / "planning"

    # NAS NFD 인코딩 대응 — 모든 파일을 NFC로 비교
    channel_nfc = unicodedata.normalize("NFC", channel)
    files = sorted(
        [f for f in planning_dir.glob("*-autoresearch.json")
         if channel_nfc in unicodedata.normalize("NFC", f.name)],
        reverse=True,
    )
    if not files:
        return ""

    try:
        data = json.loads(files[0].read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ""

    candidates = data.get("candidates", [])
    if not candidates:
        return ""

    ratchet = data.get("ratchet_score", 0)
    lines = [f"📊 **래칫 점수: {ratchet}**\n"]

    for c in candidates[:5]:
        score = c.get("topic_score", 0)
        title = c.get("title", "")
        hook = c.get("hook", "")
        urgent = c.get("urgent_flag", "")
        urgent_tag = f" 🚨 {urgent}" if urgent else ""
        lines.append(f"**{c.get('rank', '?')}. [{score}점] {title}**{urgent_tag}")
        if hook:
            lines.append(f"  > {hook}")
        lines.append("")

    urgents = data.get("urgent_flags", [])
    if urgents:
        lines.append("**⚠️ 긴급 플래그:**")
        for u in urgents:
            lines.append(f"- {u.get('topic', '')} (D-{u.get('days_remaining', '?')}): {u.get('action', '')}")

    return "\n".join(lines)


def run_single_round(channel: str, round_num: int, total: int):
    """단일 autoresearch 라운드 실행."""
    from auto_agent.modules.agent_runner import AgentRunner

    logger.info("=== 라운드 %d/%d 시작 (채널: %s) ===", round_num, total, channel)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    notify_discord(f"🔍 **라운드 {round_num}/{total}** 시작 ({now})")

    runner = AgentRunner()
    result = runner.run_trend_analyst(
        channel=channel,
        autoresearch=True,
        max_rounds=1,
    )

    if result["status"] == "success":
        usage = result.get("usage", {})
        cost = usage.get("total_cost_usd", 0)
        input_tok = usage.get("input_tokens", 0)
        output_tok = usage.get("output_tokens", 0)
        cache_read = usage.get("cache_read_tokens", 0)
        duration = usage.get("duration_ms", 0) / 1000
        turns = usage.get("num_turns", 0)

        logger.info(
            "라운드 %d 완료 (성공) — $%.4f, %d턴, %.0fs, in:%d out:%d cache:%d",
            round_num, cost, turns, duration, input_tok, output_tok, cache_read,
        )

        summary = format_results_summary(channel)
        usage_line = (
            f"\n💰 **비용:** ${cost:.4f} | **턴:** {turns} | **시간:** {duration:.0f}s\n"
            f"📊 **토큰:** input {input_tok:,} / output {output_tok:,} / cache {cache_read:,}"
        ) if cost > 0 else ""

        notify_discord(
            f"✅ **라운드 {round_num}/{total} 완료**"
            f"{usage_line}\n\n{summary}"
        )
    elif result["status"] == "timeout":
        logger.warning("라운드 %d 타임아웃", round_num)
        notify_discord(f"⏱️ **라운드 {round_num}/{total}** 타임아웃")
    else:
        stderr_preview = result.get("stderr", "")[:200]
        logger.error("라운드 %d 실패: %s", round_num, stderr_preview)
        notify_discord(f"❌ **라운드 {round_num}/{total}** 실패: {stderr_preview[:100]}")

    return result


def main():
    channel = sys.argv[1] if len(sys.argv) > 1 else "이로미즘"
    total_rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    interval_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 3600

    # 로그 디렉토리 생성
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    logger.info("AutoResearch 시작 — 채널: %s, 라운드: %d, 간격: %ds",
                channel, total_rounds, interval_sec)

    # 스레드 생성 — 크론 실행마다 1개
    notifier = get_notifier()
    if notifier:
        thread_name = f"[{today}] {channel} AutoResearch"
        thread_id = notifier.create_thread(thread_name)
        if thread_id:
            logger.info("Discord 스레드 생성: %s", thread_id)

    notify_discord(
        f"🚀 **AutoResearch 시작!**\n"
        f"채널: {channel}\n"
        f"라운드: {total_rounds}회\n"
        f"날짜: {today}"
    )

    no_improvement_count = 0
    prev_top5 = set()
    actual_rounds = 0

    for i in range(1, total_rounds + 1):
        run_single_round(channel, i, total_rounds)
        actual_rounds = i

        # Early stopping: Top 5 변화 감지
        current_summary = format_results_summary(channel)
        current_top5 = set()
        for line in current_summary.split("\n"):
            if line.startswith("**") and "점]" in line:
                current_top5.add(line.strip())

        if current_top5 == prev_top5 and i > 1:
            no_improvement_count += 1
            logger.info("라운드 %d: Top 5 변화 없음 (%d회 연속)", i, no_improvement_count)
        else:
            no_improvement_count = 0
        prev_top5 = current_top5

        if no_improvement_count >= 2:
            logger.info("=== Early Stopping: 2라운드 연속 Top 5 변화 없음 → 종료 ===")
            notify_discord(
                f"⏹️ **Early Stopping** — 2라운드 연속 Top 5 변화 없음\n"
                f"라운드 {i}/{total_rounds}에서 조기 종료"
            )
            break

        if i < total_rounds:
            logger.info("다음 라운드까지 %d분 대기...", interval_sec // 60)
            time.sleep(interval_sec)

    logger.info("=== AutoResearch 전체 완료 (%d라운드) ===", actual_rounds)
    final_summary = format_results_summary(channel)

    # 최종 결과는 스레드 + 채널 양쪽에 전송
    completion_msg = (
        f"🎉 **AutoResearch 전체 완료!**\n"
        f"채널: {channel}, {total_rounds}라운드 완료\n\n"
        f"{final_summary}\n"
        f"→ 볼트 insights/planning/ 확인"
    )
    notify_discord(completion_msg)

    # 채널에도 완료 알림 (스레드 밖)
    if notifier and notifier.thread_id:
        notifier.send_to_channel(
            f"✅ **[{today}] {channel} AutoResearch 완료** — "
            f"스레드에서 상세 결과 확인"
        )

    # 팀 서버 웹훅으로 기획안 전송
    send_to_team_webhook(channel, final_summary)


def send_to_team_webhook(channel: str, summary: str):
    """팀 서버 Discord에 기획안을 주제별 스레드로 전송."""
    import time as _time

    # 1. 봇 토큰 기반 스레드 전송 시도
    team_channel = os.getenv("TEAM_DISCORD_CHANNEL_ID", "")
    if team_channel:
        try:
            from auto_agent.modules.discord_bot_notify import DiscordBotNotify
            bot = DiscordBotNotify(channel_id=team_channel)

            today = datetime.now().strftime("%Y-%m-%d")

            # 볼트에서 기획안 .md 파일 읽기
            vault_dir = Path(os.environ.get("KAIROS_VAULT_DIR", ""))
            planning_file = vault_dir / "insights" / "planning" / f"{today}-{channel}-기획안.md"

            if not planning_file.exists():
                # fallback: 요약만 전송
                bot.send_to_channel(f"📋 **[{today}] {channel} AutoResearch 기획안**\n\n{summary}")
                logger.info("팀 채널 전송 완료 (요약)")
                return

            content = planning_file.read_text(encoding="utf-8")

            # 주제별로 분할 (## 1위, ## 2위 등)
            import re
            topics = re.split(r'\n(?=## \d+위)', content)

            # 요약 메시지
            bot.send_to_channel(f"📋 **[{today}] {channel} AutoResearch 기획안** — {len(topics)-1}개 주제")
            _time.sleep(0.5)

            for topic_block in topics[1:]:  # 첫 번째는 프론트매터
                # 제목 추출
                title_match = re.match(r'## \d+위\.\s*(.+)', topic_block.strip())
                title = title_match.group(1)[:80] if title_match else "기획안"

                # 스레드 생성
                thread_id = bot.create_thread(f"[{channel}] {title}")
                if thread_id:
                    # 본문을 1900자 청크로 분할하여 스레드에 전송
                    chunks = [topic_block[i:i+1800] for i in range(0, len(topic_block), 1800)]
                    for chunk in chunks:
                        bot.send_to_thread(chunk)
                        _time.sleep(0.3)
                else:
                    bot.send_to_channel(f"**{title}**\n{topic_block[:500]}")

                _time.sleep(0.5)

            logger.info("팀 채널 스레드 전송 완료")
            return
        except Exception as e:
            logger.warning("스레드 전송 실패, 웹훅 fallback: %s", e)

    # 2. fallback: 웹훅 (주제별 브리프 포함)
    webhook = os.getenv("TEAM_DISCORD_WEBHOOK_URL", "")
    if not webhook:
        return

    today = datetime.now().strftime("%Y-%m-%d")

    # 볼트 기획안에서 주제별 전체 브리프 읽기
    vault_dir = Path(os.environ.get("KAIROS_VAULT_DIR", ""))
    planning_file = vault_dir / "insights" / "planning" / f"{today}-{channel}-기획안.md"

    if planning_file.exists():
        import re
        content = planning_file.read_text(encoding="utf-8")
        # 프론트매터 제거
        body = re.sub(r'^---[\s\S]*?---\s*', '', content).strip()
        # 주제별 분할
        topics = re.split(r'\n(?=## \d+위)', body)

        try:
            import requests as _req
            import time as _time

            # 요약 메시지
            _req.post(webhook, json={"content":
                f"📋 **[{today}] {channel} AutoResearch 기획안** — {len(topics)}개 주제\n"
                f"복사해서 `/auto-kairos`에 붙여넣기 가능합니다."
            }, timeout=10)
            _time.sleep(0.3)

            for topic_block in topics:
                if not topic_block.strip():
                    continue

                # 핵심만 추출: 제목 + 왜 지금 + 핵심 앵글 + 필수 에피소드 + 추천
                lines = topic_block.strip().split("\n")
                brief_lines = []
                in_section = False
                for line in lines:
                    # 제목 (## N위)
                    if line.startswith("## "):
                        brief_lines.append(f"**{line.lstrip('#').strip()}**")
                        continue
                    # 점수 줄
                    if "topic_score" in line:
                        brief_lines.append(line.strip())
                        continue
                    # 핵심 섹션 감지
                    lower = line.lower()
                    if any(k in lower for k in ["왜 지금", "왜 이 주제", "핵심 앵글", "핵심앵글",
                                                  "필수 에피소드", "반드시 다뤄", "이야기 포인트",
                                                  "추천 길이", "추천 구성", "긴급도"]):
                        in_section = True
                        brief_lines.append(line.strip())
                        continue
                    if in_section:
                        if line.startswith("### ") and not any(k in line.lower() for k in
                                ["앵글", "에피소드", "포인트", "추천", "긴급"]):
                            in_section = False
                            continue
                        if line.strip():
                            brief_lines.append(line.strip())

                brief = "\n".join(brief_lines)
                if brief:
                    chunks = [brief[i:i+1800] for i in range(0, len(brief), 1800)]
                    for chunk in chunks:
                        _req.post(webhook, json={"content": chunk}, timeout=10)
                        _time.sleep(0.3)
                    _req.post(webhook, json={"content": "━━━━━━━━━━━━━━━━━━━━"}, timeout=10)
                    _time.sleep(0.3)

            logger.info("팀 웹훅 전송 완료 (핵심 브리프)")
        except Exception as e:
            logger.warning("팀 웹훅 전송 실패: %s", e)
    else:
        # 기획안 파일 없으면 요약만
        msg = f"📋 **[{today}] {channel} AutoResearch 기획안**\n\n{summary}"
        try:
            import requests as _req
            chunks = [msg[i:i+1900] for i in range(0, len(msg), 1900)]
            for chunk in chunks:
                _req.post(webhook, json={"content": chunk}, timeout=10)
            logger.info("팀 웹훅 전송 완료 (요약)")
        except Exception as e:
            logger.warning("팀 웹훅 전송 실패: %s", e)


if __name__ == "__main__":
    main()
