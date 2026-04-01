"""Ollama → Anthropic Messages API 호환 프록시 서버.

Qwen3.5 로컬 모델을 Claude API처럼 사용할 수 있게 해주는 프록시.
runner.py에서 ANTHROPIC_API_KEY 대신 이 프록시를 가리키면 $0 에이전트 실행 가능.

Usage:
  python -m auto_agent.scripts.ollama_proxy                    # 기본 (port 8090)
  python -m auto_agent.scripts.ollama_proxy --port 8090        # 포트 지정
  python -m auto_agent.scripts.ollama_proxy --model qwen3.5:latest

테스트:
  curl http://localhost:8090/v1/messages -X POST -H "Content-Type: application/json" \\
    -d '{"model":"claude-sonnet-4-6","messages":[{"role":"user","content":"안녕"}],"max_tokens":100}'
"""
import argparse
import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:latest"


class AnthropicProxyHandler(BaseHTTPRequestHandler):
    """Anthropic Messages API → Ollama chat API 변환."""

    def do_POST(self):
        if self.path not in ("/v1/messages", "/v1/chat/completions"):
            self.send_error(404)
            return

        content_len = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_len)) if content_len else {}

        messages = body.get("messages", [])
        max_tokens = body.get("max_tokens", 2000)
        system = body.get("system", "")

        # system 메시지 처리
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        for m in messages:
            ollama_messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "") if isinstance(m.get("content"), str)
                else " ".join(b.get("text", "") for b in m.get("content", []) if b.get("type") == "text"),
            })

        # Ollama 호출
        import requests
        try:
            start = time.time()
            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": self.server.ollama_model,
                    "messages": ollama_messages,
                    "stream": False,
                    "think": False,
                    "options": {"num_predict": max_tokens},
                },
                timeout=600,
            )
            elapsed = time.time() - start
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            eval_count = data.get("eval_count", len(content) // 4)

            logger.info(f"[{elapsed:.1f}s] {eval_count}tok → {len(content)}자")

            # Anthropic Messages API 형식으로 응답
            response = {
                "id": f"msg_{int(time.time()*1000)}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": content}],
                "model": self.server.ollama_model,
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": data.get("prompt_eval_count", 0),
                    "output_tokens": eval_count,
                },
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"Ollama 호출 실패: {e}")
            self.send_error(502, str(e))

    def do_GET(self):
        """헬스체크."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "model": self.server.ollama_model,
            "ollama_url": OLLAMA_URL,
        }).encode())

    def log_message(self, format, *args):
        pass  # 기본 로그 억제


def main():
    parser = argparse.ArgumentParser(prog="ollama-proxy")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), AnthropicProxyHandler)
    server.ollama_model = args.model

    logger.info(f"Anthropic 호환 프록시 시작: http://localhost:{args.port}")
    logger.info(f"모델: {args.model} → Ollama ({OLLAMA_URL})")
    logger.info(f"사용법: ANTHROPIC_BASE_URL=http://localhost:{args.port} claude ...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("프록시 종료")


if __name__ == "__main__":
    main()
