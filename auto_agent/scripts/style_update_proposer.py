"""제안→승인→적용 시스템 — Stage 0/4 분석 → 문체/연출 업데이트 제안.

주 1회 실행. 볼트 성과 데이터를 분석하여 writing-style/SKILL.md 업데이트를 제안.
사용자가 승인하면 적용, 거부하면 기록만.

Usage:
  python -m auto_agent.scripts.style_update_proposer
  python -m auto_agent.scripts.style_update_proposer --apply <proposal_id>
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

VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", ""))
WORKSPACE = Path(__file__).resolve().parent.parent.parent


def main():
    args = sys.argv[1:]

    if "--apply" in args:
        idx = args.index("--apply")
        if idx + 1 < len(args):
            apply_proposal(args[idx + 1])
        return

    generate_proposals()


def generate_proposals():
    """성과 데이터 분석 → 업데이트 제안 생성."""
    logger.info("=== 문체/연출 업데이트 제안 생성 ===")

    # 1. 최근 성과 데이터 수집
    performance_data = _collect_performance_data()
    # 2. 최근 래칫 리뷰 피드백 수집
    review_data = _collect_review_feedback()
    # 3. 경쟁 분석 데이터
    competitor_data = _collect_competitor_insights()

    if not any([performance_data, review_data, competitor_data]):
        logger.info("분석할 데이터 없음")
        return

    # 4. Claude에게 제안 생성 요청
    prompt = f"""당신은 YouTube 콘텐츠 전략 컨설턴트입니다.
아래 데이터를 분석하여 세모지/이로미즘 채널의 writing-style과 연출 규칙 업데이트를 제안하세요.

## 최근 성과 데이터:
{performance_data}

## 래칫 리뷰 반복 피드백:
{review_data}

## 경쟁 채널 동향:
{competitor_data}

## 현재 writing-style 규칙 위치:
- 세모지: auto_agent/data/skills/shared/writing-style-semoji.md
- 이로미즘: auto_agent/data/skills/shared/writing-style-iromism.md
- 리뷰어: auto_agent/data/skills/agents/script-reviewer/SKILL.md

## 출력 형식 (JSON):
{{
  "proposals": [
    {{
      "id": "prop_001",
      "channel": "세모지|이로미즘",
      "target_file": "파일 경로",
      "category": "writing_style|review_criteria|art_direction",
      "title": "제안 제목",
      "reason": "왜 이 변경이 필요한지 (데이터 근거)",
      "current": "현재 규칙",
      "proposed": "제안 규칙",
      "expected_impact": "예상 효과",
      "priority": "high|medium|low"
    }}
  ]
}}

제안은 3~5개. 데이터 근거가 명확한 것만. JSON만 출력.
"""

    try:
        result = subprocess.run(
            ["claude", "--print", "--model", "claude-sonnet-4-6",
             "--max-turns", "1", "-p", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=str(WORKSPACE),
        )
        response = result.stdout.strip()

        # JSON 파싱
        import re
        json_match = re.search(r'\{[\s\S]*"proposals"[\s\S]*\}', response)
        if json_match:
            proposals = json.loads(json_match.group())

            # 볼트에 저장
            today = datetime.now().strftime("%Y-%m-%d")
            out_dir = VAULT_DIR / "insights" / "proposals"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{today}-style-proposals.json"
            out_path.write_text(json.dumps(proposals, ensure_ascii=False, indent=2), encoding="utf-8")

            # 디스코드 웹훅으로 제안 전송
            _send_proposals_webhook(proposals)

            logger.info(f"제안 {len(proposals.get('proposals', []))}개 생성 → {out_path}")
        else:
            logger.error(f"JSON 파싱 실패: {response[:300]}")

    except Exception as e:
        logger.error(f"제안 생성 실패: {e}")


def apply_proposal(proposal_id: str):
    """승인된 제안을 실제 파일에 적용."""
    logger.info(f"제안 적용: {proposal_id}")

    # 최신 제안 파일 찾기
    proposals_dir = VAULT_DIR / "insights" / "proposals"
    if not proposals_dir.exists():
        logger.error("제안 파일 없음")
        return

    latest = sorted(proposals_dir.glob("*-style-proposals.json"), reverse=True)
    if not latest:
        logger.error("제안 파일 없음")
        return

    proposals = json.loads(latest[0].read_text(encoding="utf-8"))

    for prop in proposals.get("proposals", []):
        if prop.get("id") == proposal_id:
            target = WORKSPACE / prop["target_file"]
            if not target.exists():
                logger.error(f"대상 파일 없음: {target}")
                return

            content = target.read_text(encoding="utf-8")
            current = prop.get("current", "")
            proposed = prop.get("proposed", "")

            if current and proposed and current in content:
                content = content.replace(current, proposed, 1)
                target.write_text(content, encoding="utf-8")
                logger.info(f"적용 완료: {prop['title']}")

                # 적용 기록
                prop["status"] = "applied"
                prop["applied_at"] = datetime.now().isoformat()
                latest[0].write_text(
                    json.dumps(proposals, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            else:
                logger.warning(f"current 텍스트 매칭 실패 — 수동 적용 필요")
            return

    logger.error(f"제안 ID '{proposal_id}' 없음")


def _collect_performance_data() -> str:
    """최근 성과 데이터 수집."""
    insights_dir = VAULT_DIR / "insights" / "performance"
    if not insights_dir.exists():
        return ""
    files = sorted(insights_dir.glob("*.md"), reverse=True)[:3]
    data = []
    for f in files:
        content = f.read_text(encoding="utf-8")
        data.append(f"### {f.stem}\n{content[:500]}")
    return "\n\n".join(data)


def _collect_review_feedback() -> str:
    """최근 래칫 리뷰 반복 피드백 수집."""
    # 최근 프로젝트의 review_feedback 수집
    output_dir = WORKSPACE / "output"
    if not output_dir.exists():
        return ""

    feedbacks = []
    for state_file in sorted(output_dir.glob("*/review_feedback.json"), reverse=True)[:3]:
        fb = json.loads(state_file.read_text(encoding="utf-8"))
        issues = []
        for sr in fb.get("scene_reviews", []):
            for issue in sr.get("issues", []):
                issues.append(f"씬{sr.get('sceneNumber','?')} [{issue.get('severity','')}] {issue.get('description','')[:80]}")
        if issues:
            feedbacks.append(f"프로젝트: {state_file.parent.name}\n" + "\n".join(issues[:5]))

    return "\n\n".join(feedbacks)


def _collect_competitor_insights() -> str:
    """경쟁 분석 인사이트."""
    insights_dir = VAULT_DIR / "insights" / "performance"
    if not insights_dir.exists():
        return ""
    competitors = [f for f in insights_dir.glob("*competitor*")]
    if not competitors:
        return ""
    return competitors[0].read_text(encoding="utf-8")[:500]


def _send_proposals_webhook(proposals: dict):
    """디스코드로 제안 전송."""
    import requests
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not webhook_url:
        return

    posts = proposals.get("proposals", [])
    msg = f"## 📝 문체/연출 업데이트 제안 ({len(posts)}건)\n\n"
    for p in posts:
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p.get("priority", ""), "⚪")
        msg += f"{priority_emoji} **[{p['id']}] {p['title']}**\n"
        msg += f"채널: {p.get('channel', '')} | 근거: {p.get('reason', '')[:80]}\n"
        msg += f"적용: `python -m auto_agent.scripts.style_update_proposer --apply {p['id']}`\n\n"

    try:
        requests.post(webhook_url, json={"content": msg[:2000]}, timeout=10)
    except Exception:
        pass


if __name__ == "__main__":
    main()
