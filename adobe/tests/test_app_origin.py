"""교차 출처 차단(CSRF 방어) — 패널 백엔드는 웹페이지가 부를 수 있는 자리다.

백엔드는 `127.0.0.1:8765` 에 뜨고 라우트가 70여 개다. 그중에는 파일을 덮어쓰고
(`/api/projects/file/save`) 씬을 지우고(`/api/scenes/delete`) 프로세스를 띄우는
(`/api/skills/run`) 것이 있다.

「내 컴퓨터 안에서만 도니 안전하다」가 아니다. AE 패널이 떠 있는 동안 사용자가
연 웹페이지의 자바스크립트가 그대로 부를 수 있다. 원래는 브라우저가 「다른
출처니 답을 읽지 마라」로 막아 주는데, 서버가 `Access-Control-Allow-Origin: *`
를 내보내면 그 방어를 스스로 해제하는 셈이 된다.

가르는 기준은 `Origin` 헤더다. 브라우저가 직접 붙이므로 웹페이지가 위조할 수
없다. CEP 패널은 `file://` 출신이라 헤더가 없거나 `null` 이고, 웹페이지는 반드시
`https://…` 가 붙는다.
"""
from __future__ import annotations

import pytest

from backend.app import Handler, origin_allowed


# ── 판정 함수 ────────────────────────────────────────────────────────────

def test_origin_none_allowed():
    """CEP 패널은 Origin 헤더를 안 보낸다."""
    assert origin_allowed(None) is True


def test_origin_null_allowed():
    """file:// 문서의 요청은 Origin 이 문자열 "null" 로 온다."""
    assert origin_allowed("null") is True


def test_origin_file_allowed():
    assert origin_allowed("file:///Users/x/panel") is True


def test_origin_http_blocked():
    assert origin_allowed("http://evil.example") is False


def test_origin_https_blocked():
    assert origin_allowed("https://attacker.test") is False


def test_origin_localhost_page_blocked():
    """제 컴퓨터에서 뜬 웹페이지도 웹페이지다 — 출처가 있으면 막는다."""
    assert origin_allowed("http://127.0.0.1:8765") is False
    assert origin_allowed("http://localhost:3000") is False


# ── 실제 요청 경로 ───────────────────────────────────────────────────────

class _Wire:
    """소켓 대신 쓰는 기록장 — 무엇을 내보냈는지만 본다."""

    def __init__(self, origin: str | None, path: str):
        self.headers = {} if origin is None else {"Origin": origin}
        self.path = path
        self.status: int | None = None
        self.sent_headers: list[tuple[str, str]] = []
        self.body = b""
        self.routed = False
        self.streamed = False


def _handler(origin: str | None, path: str) -> tuple[Handler, _Wire]:
    """소켓을 열지 않고 Handler 를 만든다.

    BaseHTTPRequestHandler 는 __init__ 이 곧 요청 처리라 그대로는 못 쓴다.
    __new__ 로 껍데기만 만들고 필요한 것만 끼워 넣는다.
    """
    h = Handler.__new__(Handler)
    w = _Wire(origin, path)

    class _Body:
        def write(self, b): w.body += b
        def flush(self): pass

    h.headers = w.headers
    h.path = w.path
    h.wfile = _Body()
    h.send_response = lambda code, *a: setattr(w, "status", code)
    h.send_header = lambda k, v: w.sent_headers.append((k, v))
    h.end_headers = lambda: None
    h._route = lambda method: setattr(w, "routed", True)
    h._sse = lambda: setattr(w, "streamed", True)
    return h, w


def test_get_from_panel_is_routed():
    h, w = _handler(None, "/api/projects/files")
    Handler.do_GET(h)
    assert w.routed is True
    assert w.status is None            # 막지 않았다


def test_get_from_webpage_is_denied():
    h, w = _handler("https://evil.example", "/api/projects/files")
    Handler.do_GET(h)
    assert w.routed is False
    assert w.status == 403


def test_post_from_webpage_is_denied():
    """쓰기가 특히 위험하다 — 파일 저장·씬 삭제·스킬 실행이 전부 POST 다."""
    h, w = _handler("https://evil.example", "/api/projects/file/save")
    Handler.do_POST(h)
    assert w.routed is False
    assert w.status == 403


def test_sse_from_webpage_is_denied():
    """`/api/events` 는 do_GET 에서 _route 를 우회한다 — 여기가 뚫려 있었다.

    폐기된 auto_kairos_adobe 브랜치의 원래 수정은 `_route` 만 막았다. 그 브랜치에도
    이 우회 분기가 있었으므로 SSE 는 무방비였다. 그대로 베끼면 구멍이 남는다.
    """
    h, w = _handler("https://evil.example", "/api/events")
    Handler.do_GET(h)
    assert w.streamed is False
    assert w.status == 403


def test_sse_from_panel_streams():
    h, w = _handler(None, "/api/events")
    Handler.do_GET(h)
    assert w.streamed is True


def test_preflight_from_webpage_is_denied():
    """사전확인(preflight)에서 막으면 본 요청이 아예 뜨지 않는다."""
    h, w = _handler("https://evil.example", "/api/scenes/delete")
    Handler.do_OPTIONS(h)
    assert w.status == 403
    assert not any(k == "Access-Control-Allow-Origin" for k, _ in w.sent_headers)


def test_preflight_from_panel_allowed():
    h, w = _handler(None, "/api/scenes/delete")
    Handler.do_OPTIONS(h)
    assert w.status == 204


@pytest.mark.parametrize("origin", ["https://evil.example", "http://localhost:3000"])
def test_denied_response_does_not_leak_cors(origin):
    """막을 때 ACAO 를 붙이면 막은 의미가 없다 — 응답을 읽게 해 준다."""
    h, w = _handler(origin, "/api/projects/files")
    Handler.do_GET(h)
    assert w.status == 403
    assert not any(k == "Access-Control-Allow-Origin" for k, _ in w.sent_headers)
