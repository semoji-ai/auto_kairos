"""auto_kairos Adobe PD Assistant — HTTP 서버 (M2).
순수 라우팅은 backend.router.handle_request 가 담당. 이 파일은 소켓/JSON 입출력만."""
from __future__ import annotations

import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from backend import projects
from backend.jobs import JobRegistry
from backend.router import handle_request

PORT = int(os.environ.get("AK_BACKEND_PORT", "8765"))
CTX = {"root": projects.projects_root(), "jobs": JobRegistry()}

# 파이썬을 고치면 이 프로세스를 다시 띄워야 반영된다. 그걸 사람이 기억해야
# 했고, 하루에 네 번 잊었다 — 영상이 안 실리고, 레이어가 안 실리고, 매니페스트
# 배율이 옛것이고. 매번 「고쳤는데 왜 그대로냐」로 돌아왔다. 파일이 바뀌면
# 스스로 다시 뜬다. AK_BACKEND_RELOAD=0 으로 끈다.
RELOAD = os.environ.get("AK_BACKEND_RELOAD", "1") != "0"


def _watch_sources() -> None:
    """`backend/*.py` 가 바뀌면 프로세스를 다시 띄운다.

    ⚠️ **작업이 도는 중에는 안 건드린다.** 이미지 생성·레이어 분리·비디오는
    몇 분씩 걸리는데, 그 사이에 다시 뜨면 하던 일이 통째로 날아간다. 조용해질
    때까지 기다린다 — 늦게 반영되는 것과 작업을 잃는 것은 무게가 다르다.
    """
    import threading, time, sys
    d = Path(__file__).resolve().parent

    def _stamp():
        out = {}
        for p in sorted(d.glob("*.py")):
            try:
                out[p.name] = p.stat().st_mtime
            except OSError:
                pass
        return out

    def _loop():
        base = _stamp()
        while True:
            time.sleep(1.0)
            now = _stamp()
            if now == base:
                continue
            changed = sorted(k for k in set(base) | set(now) if base.get(k) != now.get(k))
            # 저장이 끝날 때까지 한 박자 쉰다 — 쓰는 중에 읽으면 반쪽을 읽는다
            time.sleep(0.6)
            if CTX["jobs"].running_jobs():
                base = _stamp()
                print("[reload] 작업 중이라 미룹니다: " + ", ".join(changed), flush=True)
                continue
            print("[reload] 바뀐 파일: " + ", ".join(changed) + " — 다시 뜹니다", flush=True)
            try:
                os.execv(sys.executable, [sys.executable, "-m", "backend.app"])
            except Exception as e:                      # 실패해도 서버는 살아 있어야 한다
                print(f"[reload] 실패(그대로 둡니다): {e}", flush=True)
                base = _stamp()

    threading.Thread(target=_loop, name="reload-watch", daemon=True).start()


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
    if RELOAD:
        _watch_sources()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    srv.allow_reuse_address = True          # 다시 뜰 때 포트가 바로 잡혀야 한다
    print(f"[auto_kairos backend M2] http://127.0.0.1:{PORT}  root={CTX['root']}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
