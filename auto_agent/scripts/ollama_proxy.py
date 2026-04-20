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

        # Anthropic tools → Ollama tools 변환
        anthropic_tools = body.get("tools", [])
        ollama_tools = []
        for t in anthropic_tools:
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": t.get("name", ""),
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            })

        # system 메시지 처리
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")

            if role == "assistant" and isinstance(content, list):
                # Anthropic 형식: content 배열에 text + tool_use 블록
                text_parts = []
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        # tool_use → Ollama tool_calls로 변환
                        ollama_messages.append({
                            "role": "assistant",
                            "content": " ".join(text_parts) if text_parts else "",
                            "tool_calls": [{
                                "id": block.get("id", ""),
                                "function": {
                                    "name": block.get("name", ""),
                                    "arguments": block.get("input", {}),
                                },
                            }],
                        })
                        text_parts = []
                if text_parts:
                    ollama_messages.append({"role": "assistant", "content": " ".join(text_parts)})
            elif role == "user" and isinstance(content, list):
                # tool_result 블록 처리
                for block in content:
                    if block.get("type") == "tool_result":
                        ollama_messages.append({
                            "role": "tool",
                            "content": block.get("content", "") if isinstance(block.get("content"), str)
                            else json.dumps(block.get("content", "")),
                        })
                    elif block.get("type") == "text":
                        ollama_messages.append({"role": "user", "content": block.get("text", "")})
            else:
                ollama_messages.append({
                    "role": role,
                    "content": content if isinstance(content, str)
                    else " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"),
                })

        # Ollama 호출
        import requests
        try:
            start = time.time()
            ollama_payload = {
                "model": self.server.ollama_model,
                "messages": ollama_messages,
                "stream": False,
                "think": False,
                "options": {"num_predict": max_tokens},
            }
            if ollama_tools:
                ollama_payload["tools"] = ollama_tools

            resp = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json=ollama_payload,
                timeout=600,
            )
            elapsed = time.time() - start
            data = resp.json()
            msg = data.get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
            eval_count = data.get("eval_count", max(len(content) // 4, 1))

            # Anthropic Messages API 형식으로 응답 빌드
            response_content = []
            stop_reason = "end_turn"

            if content:
                response_content.append({"type": "text", "text": content})

            if tool_calls:
                stop_reason = "tool_use"
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_id = tc.get("id", f"toolu_{int(time.time()*1000)}")
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {"raw": args}
                    response_content.append({
                        "type": "tool_use",
                        "id": tool_id,
                        "name": func.get("name", ""),
                        "input": args,
                    })

            if not response_content:
                response_content.append({"type": "text", "text": ""})

            tool_info = f", tools={len(tool_calls)}" if tool_calls else ""
            logger.info(f"[{elapsed:.1f}s] {eval_count}tok → {len(content)}자{tool_info}")

            response = {
                "id": f"msg_{int(time.time()*1000)}",
                "type": "message",
                "role": "assistant",
                "content": response_content,
                "model": self.server.ollama_model,
                "stop_reason": stop_reason,
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
