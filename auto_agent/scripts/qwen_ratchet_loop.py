"""Qwen 래칫 학습 자동화 — AutoResearch 방법론 적용.

매일 KST 22:00 (UTC 13:00) 실행.
Qwen 생성 → Claude 평가 → 래칫 점수 축적 → 볼트 저장.

Usage:
  python -m auto_agent.scripts.qwen_ratchet_loop
"""
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# 환경 설정
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass


def main():
    logger.info("=== Qwen 래칫 학습 시작 ===")

    from auto_agent.scripts.qwen_intern_ab_test import QwenIntern

    intern = QwenIntern()
    if not intern.is_available():
        logger.error("Qwen 사용 불가 (ollama 미실행 또는 모델 없음)")
        sys.exit(1)

    vault_dir = Path(os.environ.get(
        "KAIROS_VAULT_DIR",
        os.path.expanduser("~/Desktop/kairos-vault"),
    ))
    memory_dir = vault_dir / "qwen_memory"
    memory_dir.mkdir(parents=True, exist_ok=True)

    # 래칫 상태 로드
    ratchet_path = memory_dir / "ratchet_state.json"
    ratchet = _load_ratchet(ratchet_path)

    # 오늘의 학습 태스크
    tasks = [
        ("scene_description", "조선시대 한양의 시장 풍경을 영상 나레이션용으로 150자 이내로 묘사해줘. 시대적 디테일을 포함해서."),
        ("narration_rewrite", "다음 나레이션을 이로미즘 문체로 재작성해줘: '인공지능은 1950년대에 처음 등장했으며, 이후 여러 발전을 거쳤습니다.' 200자 이내."),
        ("title_generate", "'한국 반도체 전쟁의 숨겨진 이야기' 주제로 YouTube 영상 제목 3종을 만들어줘. 클릭률 높은 스타일로."),
        ("data_summary", "삼성전자 vs TSMC 반도체 점유율 데이터를 시각화에 적합한 형태(items, values, unit)로 정리해줘."),
        ("creative_brief", "배달의민족이 한국 음식 문화를 바꾼 방식을 일반인이 체감할 수 있는 비유 3가지 만들어줘."),
    ]

    results = []
    round_scores = []

    for task_name, prompt in tasks:
        logger.info(f"[{task_name}] 시작")
        try:
            qwen_result = intern.generate(prompt)
            if not qwen_result or len(qwen_result.strip()) < 10:
                logger.warning(f"[{task_name}] Qwen 응답 부족 ({len(qwen_result or '')}자)")
                continue

            logger.info(f"[{task_name}] Qwen 응답 ({len(qwen_result)}자)")

            # A/B 테스트 (Claude 평가)
            ab_result = intern.run_ab_test(task_name, prompt, claude_result=None)
            if ab_result:
                results.append(ab_result)
                intern.save_result(ab_result, vault_dir)

                # 점수 추출
                eval_data = ab_result.get("evaluation", {})
                scores_b = eval_data.get("scores_b", {})
                avg_score = sum(scores_b.values()) / max(len(scores_b), 1) if scores_b else 0
                round_scores.append(avg_score)

                winner = eval_data.get("winner", "?")
                logger.info(f"[{task_name}] 평가: winner={winner}, qwen_avg={avg_score:.1f}")
            else:
                logger.warning(f"[{task_name}] A/B 테스트 실패")
        except Exception as e:
            logger.error(f"[{task_name}] 에러: {e}")

    # 래칫 업데이트
    if round_scores:
        today_avg = sum(round_scores) / len(round_scores)
        prev_best = ratchet.get("best_avg_score", 0)

        if today_avg >= prev_best:
            ratchet["best_avg_score"] = today_avg
            ratchet["best_date"] = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"래칫 ↑: {prev_best:.1f} → {today_avg:.1f}")
        else:
            logger.info(f"래칫 유지: {today_avg:.1f} < {prev_best:.1f}")

        ratchet["history"].append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "avg_score": round(today_avg, 2),
            "tasks_completed": len(results),
            "tasks_total": len(tasks),
        })
        # 최근 30일만 유지
        ratchet["history"] = ratchet["history"][-30:]
        ratchet["total_rounds"] = ratchet.get("total_rounds", 0) + 1

        _save_ratchet(ratchet, ratchet_path)

    logger.info(f"=== Qwen 래칫 학습 종료: {len(results)}/{len(tasks)} 완료 ===")


def _load_ratchet(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "best_avg_score": 0,
        "best_date": "",
        "total_rounds": 0,
        "history": [],
    }


def _save_ratchet(ratchet: dict, path: Path):
    path.write_text(json.dumps(ratchet, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
