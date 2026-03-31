"""Qwen 인턴 A/B 테스트 — Claude(A안) vs Qwen(B안) 동시 실행 + 자동 평가."""
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).resolve().parent.parent.parent / "logs" / "qwen-intern.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


class QwenIntern:
    """Qwen 3.5 로컬 모델 A/B 테스트."""

    def __init__(self, model_name: str = "qwen3.5:8b"):
        self._model = model_name
        self._ollama_url = "http://localhost:11434"

    def is_available(self) -> bool:
        """ollama가 실행 중이고 모델이 있는지 확인."""
        try:
            import requests
            resp = requests.get(f"{self._ollama_url}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False
            models = [m["name"] for m in resp.json().get("models", [])]
            return self._model in models or any(self._model.split(":")[0] in m for m in models)
        except Exception:
            return False

    def generate(self, prompt: str, max_tokens: int = 4096) -> str:
        """Qwen으로 텍스트 생성."""
        import requests
        try:
            resp = requests.post(
                f"{self._ollama_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=300,
            )
            return resp.json().get("response", "")
        except Exception as e:
            logger.error("Qwen 생성 실패: %s", e)
            return ""

    def run_ab_test(self, task_name: str, prompt: str,
                    claude_result: str) -> Dict:
        """A/B 테스트 실행 + 자동 평가."""
        logger.info("A/B 테스트 시작: %s", task_name)

        # B안: Qwen 생성
        start = time.time()
        qwen_result = self.generate(prompt)
        qwen_time = time.time() - start

        if not qwen_result:
            return {
                "task": task_name,
                "status": "qwen_failed",
                "claude_result": claude_result[:500],
            }

        # 자동 평가: Claude가 양쪽을 채점
        eval_prompt = f"""두 AI 모델의 결과를 비교 평가하세요.

## 과제: {task_name}

## A안 (Claude):
{claude_result[:3000]}

## B안 (Qwen):
{qwen_result[:3000]}

## 평가 기준 (각 1~10점):
1. 정확성 — 사실이 맞는지
2. 깊이 — 분석이 얼마나 깊은지
3. 창의성 — 새로운 관점이 있는지
4. 실용성 — 바로 활용 가능한지
5. 한국어 품질 — 자연스러운 한국어인지

## 출력 형식 (JSON):
{{
  "scores_a": {{"accuracy": N, "depth": N, "creativity": N, "practicality": N, "korean": N}},
  "scores_b": {{"accuracy": N, "depth": N, "creativity": N, "practicality": N, "korean": N}},
  "total_a": N,
  "total_b": N,
  "winner": "A" 또는 "B",
  "percentage_b": N (B가 A의 몇 %인지),
  "feedback_for_b": "B안 개선 포인트"
}}
"""
        # Claude로 평가
        from auto_agent.modules.agent_runner import AgentRunner
        runner = AgentRunner()
        eval_config = {"model": "sonnet", "max_turns": 5, "max_duration_minutes": 5}
        eval_result = runner._run_agent(eval_prompt, eval_config)

        return {
            "task": task_name,
            "status": "completed",
            "qwen_time_sec": qwen_time,
            "qwen_result_preview": qwen_result[:500],
            "claude_result_preview": claude_result[:500],
            "evaluation": eval_result.get("stdout", "")[:2000],
        }

    def save_result(self, result: Dict, vault_dir: Path):
        """A/B 테스트 결과를 볼트에 저장."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_dir = vault_dir / "solutioner" / "evaluations"
        out_dir.mkdir(parents=True, exist_ok=True)

        out = out_dir / f"{today}-{result['task']}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("결과 저장: %s", out)


def setup_ollama_model(model: str = "qwen3.5:8b"):
    """ollama에서 Qwen 모델 다운로드."""
    logger.info("Qwen 모델 다운로드: %s", model)
    proc = subprocess.run(
        ["ollama", "pull", model],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode == 0:
        logger.info("모델 다운로드 완료: %s", model)
    else:
        logger.error("모델 다운로드 실패: %s", proc.stderr[:200])


if __name__ == "__main__":
    intern = QwenIntern()
    if not intern.is_available():
        print("Qwen 모델이 없습니다. 먼저 설치하세요:")
        print("  ollama serve &")
        print("  ollama pull qwen3:8b")
    else:
        print("Qwen 인턴 준비 완료!")
