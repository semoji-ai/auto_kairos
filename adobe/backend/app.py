"""auto_kairos Adobe PD Assistant — HTTP 서버 (M2).
순수 라우팅은 backend.router.handle_request 가 담당. 이 파일은 소켓/JSON 입출력만."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from backend import projects
from backend.jobs import JobRegistry
from backend.router import handle_request

PORT = int(os.environ.get("AK_BACKEND_PORT", "8765"))
CTX = {"root": projects.projects_root(), "jobs": JobRegistry()}


class Handler(BaseHTTPRequestHandler):
    def _read_body(self) -> dict | None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            return None

    def _route(self, method: str) -> None:
        u = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(u.query).items()}
        body = self._read_body() if method == "POST" else None
        code, payload = handle_request(method, u.path, query, body, CTX)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):   # noqa: N802
        if urlparse(self.path).path == "/api/events":
            self._sse()
            return
        self._route("GET")

    def do_POST(self):  self._route("POST")   # noqa: E704,N802

    def _sse(self) -> None:
        """SSE 스트림 — 잡 로그/완료를 푸시(패널은 폴링 대신 이벤트 수신). 15s 핑으로 연결 유지."""
        import queue as _q
        q = CTX["jobs"].subscribe()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            while True:
                try:
                    ev = q.get(timeout=15)
                    self.wfile.write(("data: " + json.dumps(ev, ensure_ascii=False) + "\n\n").encode("utf-8"))
                except _q.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass                                # 패널 닫힘/재연결 — 정상 종료
        finally:
            CTX["jobs"].unsubscribe(q)

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, fmt, *args):
        pass


def main() -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"[auto_kairos backend M2] http://127.0.0.1:{PORT}  root={CTX['root']}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
