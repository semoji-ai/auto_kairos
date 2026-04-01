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

    def __init__(self, model_name: str = "qwen3.5:latest"):
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

    def generate(self, prompt: str, max_tokens: int = 8192) -> str:
        """Qwen으로 텍스트 생성 (chat API + think=false)."""
        import requests
        try:
            resp = requests.post(
                f"{self._ollama_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=600,
            )
            data = resp.json()
            result = data.get("message", {}).get("content", "")
            # fallback: thinking 필드에만 응답이 있는 경우
            if not result.strip():
                thinking = data.get("message", {}).get("thinking", "")
                if thinking:
                    result = self._extract_final_answer(thinking)
            return result
        except Exception as e:
            logger.error("Qwen 생성 실패: %s", e)
            return ""

    def generate_vision(self, prompt: str, image_path: str, max_tokens: int = 2000) -> str:
        """Qwen 비전으로 이미지 분석 (chat API + think=false)."""
        import base64
        import requests
        from pathlib import Path

        img_path = Path(image_path)
        if not img_path.exists():
            logger.error("이미지 파일 없음: %s", image_path)
            return ""

        # 이미지를 base64로 인코딩
        img_b64 = base64.b64encode(img_path.read_bytes()).decode("utf-8")
        ext = img_path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")

        try:
            resp = requests.post(
                f"{self._ollama_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": [{
                        "role": "user",
                        "content": prompt,
                        "images": [img_b64],
                    }],
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=600,
            )
            data = resp.json()
            result = data.get("message", {}).get("content", "")
            if not result.strip():
                thinking = data.get("message", {}).get("thinking", "")
                if thinking:
                    result = self._extract_final_answer(thinking)
            return result
        except Exception as e:
            logger.error("Qwen 비전 실패: %s", e)
            return ""

    @staticmethod
    def _extract_final_answer(thinking: str) -> str:
        """Qwen thinking 출력에서 최종 답변 추출.

        Qwen 3.5는 thinking 안에 'Final Answer:' 또는 마지막 코드블록/리스트를 포함.
        최종 답변 패턴을 찾아 반환, 없으면 마지막 50%를 반환.
        """
        import re
        # 패턴 1: "Final Answer:" 이후
        for marker in ["Final Answer:", "**Final Answer", "최종 답변:", "**최종 답변"]:
            idx = thinking.find(marker)
            if idx != -1:
                return thinking[idx + len(marker):].strip().lstrip(":").lstrip("*").strip()

        # 패턴 2: 번호 매기기 리스트 (1. 2. 3.) — 마지막 리스트 블록
        lines = thinking.split("\n")
        last_list_start = -1
        for i, line in enumerate(lines):
            if re.match(r"^\s*1[\.\)]\s", line):
                last_list_start = i
        if last_list_start >= 0:
            return "\n".join(lines[last_list_start:]).strip()

        # 패턴 3: 후반부 반환 (thinking의 앞부분은 분석, 뒷부분이 답변)
        half = len(thinking) // 2
        return thinking[half:].strip()

    def run_ab_test(self, task_name: str, prompt: str,
                    claude_result: Optional[str] = None) -> Optional[Dict]:
        """A/B 테스트 실행 + 자동 평가."""
        logger.info("A/B 테스트 시작: %s", task_name)

        # B안: Qwen 생성
        start = time.time()
        qwen_result = self.generate(prompt)
        qwen_time = time.time() - start

        if not qwen_result or len(qwen_result.strip()) < 10:
            return None

        # A안: Claude 생성 (없으면 직접 생성)
        if not claude_result:
            try:
                import subprocess
                cli_result = subprocess.run(
                    ["claude", "--print", "--model", "claude-sonnet-4-6",
                     "--max-turns", "1", "-p", prompt],
                    capture_output=True, text=True, timeout=120,
                )
                claude_result = cli_result.stdout.strip() if cli_result.returncode == 0 else ""
            except Exception as e:
                logger.warning("Claude 생성 실패: %s", e)
                claude_result = ""

        if not claude_result:
            # Claude 없이 Qwen만 평가
            return {
                "task": task_name,
                "status": "qwen_only",
                "qwen_time_sec": qwen_time,
                "qwen_result": qwen_result[:1000],
                "evaluation": {"scores_b": {}, "winner": "B_only", "feedback_for_b": ""},
            }

        # 자동 평가: Claude가 양쪽을 채점
        eval_prompt = f"""두 AI 모델의 결과를 비교 평가하세요. 반드시 JSON만 출력하세요.

## 과제: {task_name}

## A안 (Claude):
{claude_result[:2000]}

## B안 (Qwen):
{qwen_result[:2000]}

## 평가 기준 (각 1~10점):
1. accuracy — 사실이 맞는지
2. depth — 분석이 얼마나 깊은지
3. creativity — 새로운 관점이 있는지
4. practicality — 바로 활용 가능한지
5. korean — 자연스러운 한국어인지

다음 JSON만 출력하세요 (설명 없이):
{{"scores_a": {{"accuracy": 0, "depth": 0, "creativity": 0, "practicality": 0, "korean": 0}}, "scores_b": {{"accuracy": 0, "depth": 0, "creativity": 0, "practicality": 0, "korean": 0}}, "winner": "A", "feedback_for_b": ""}}
"""
        try:
            import subprocess
            eval_run = subprocess.run(
                ["claude", "--print", "--model", "claude-haiku-4-5-20251001",
                 "--max-turns", "1", "-p", eval_prompt],
                capture_output=True, text=True, timeout=60,
            )
            eval_text = eval_run.stdout.strip() if eval_run.returncode == 0 else ""

            # JSON 파싱
            eval_data = {}
            if eval_text:
                # JSON 블록 추출
                import re
                json_match = re.search(r'\{[^{}]*"scores_a"[^{}]*\{[^{}]*\}[^{}]*"scores_b"[^{}]*\{[^{}]*\}[^{}]*\}', eval_text, re.DOTALL)
                if json_match:
                    eval_data = json.loads(json_match.group())
                else:
                    # 전체가 JSON일 수 있음
                    try:
                        eval_data = json.loads(eval_text)
                    except json.JSONDecodeError:
                        eval_data = {"raw": eval_text[:500]}

        except Exception as e:
            logger.error("평가 실패: %s", e)
            eval_data = {"error": str(e)}

        return {
            "task": task_name,
            "status": "completed",
            "qwen_time_sec": round(qwen_time, 1),
            "qwen_result": qwen_result[:1000],
            "claude_result": claude_result[:1000],
            "evaluation": eval_data,
        }

    def save_result(self, result: Dict, vault_dir: Path):
        """A/B 테스트 결과를 볼트에 저장."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out_dir = vault_dir / "solutioner" / "evaluations"
        out_dir.mkdir(parents=True, exist_ok=True)

        out = out_dir / f"{today}-{result['task']}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("결과 저장: %s", out)


def setup_ollama_model(model: str = "qwen3.5:latest"):
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
