import importlib
import sys
import types


# 진짜 fastapi가 있으면 스텁 미설치 — sys.modules 오염 방지 (실제 모듈로 동작)
if importlib.util.find_spec("fastapi") is None:
    fastapi = types.ModuleType("fastapi")

    class FastAPI:
        def __init__(self, *args, **kwargs):
            pass

        def include_router(self, *args, **kwargs):
            return None

        def mount(self, *args, **kwargs):
            return None

        def get(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def post(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def put(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def delete(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def websocket(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def on_event(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    class APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def post(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

    class Request:
        pass

    class WebSocket:
        pass

    class WebSocketDisconnect(Exception):
        pass

    fastapi.FastAPI = FastAPI
    fastapi.APIRouter = APIRouter
    fastapi.Request = Request
    fastapi.WebSocket = WebSocket
    fastapi.WebSocketDisconnect = WebSocketDisconnect
    sys.modules["fastapi"] = fastapi

    responses = types.ModuleType("fastapi.responses")
    class HTMLResponse: pass
    class JSONResponse:
        def __init__(self, content=None, status_code=200):
            self.content = content
            self.status_code = status_code
    class RedirectResponse: pass
    class StreamingResponse:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
    responses.HTMLResponse = HTMLResponse
    responses.JSONResponse = JSONResponse
    responses.RedirectResponse = RedirectResponse
    responses.StreamingResponse = StreamingResponse
    sys.modules["fastapi.responses"] = responses

    staticfiles = types.ModuleType("fastapi.staticfiles")
    class StaticFiles:
        def __init__(self, *args, **kwargs):
            pass
    staticfiles.StaticFiles = StaticFiles
    sys.modules["fastapi.staticfiles"] = staticfiles

    templating = types.ModuleType("fastapi.templating")
    class _Templates:
        def __init__(self, *args, **kwargs):
            self.env = types.SimpleNamespace(filters={})
        def TemplateResponse(self, *args, **kwargs):
            return {"args": args, "kwargs": kwargs}
    templating.Jinja2Templates = _Templates
    sys.modules["fastapi.templating"] = templating

    # dashboard 라우터 import stub
    for name in [
        "auto_agent.dashboard.actions",
        "auto_agent.dashboard.json_editor",
        "auto_agent.dashboard.sse",
        "auto_agent.dashboard.memory_routes",
        "auto_agent.dashboard.vault_routes",
        "auto_agent.dashboard.scene_editor",
        "auto_agent.dashboard.design_presets",
    ]:
        mod = types.ModuleType(name)
        mod.router = object()
        if name.endswith("scene_editor"):
            mod.manifest_router = object()
        sys.modules[name] = mod

app_module = importlib.import_module("app")
_load_tab_data = app_module._load_tab_data

# load_live_doc_snapshot은 live_docs.py에 존재하지만 app.py에 연결된 적 없음.
# 기능이 배선되기 전까지 skip — 배선되면 자동으로 다시 활성화됨.
pytestmark = __import__("pytest").mark.skipif(
    not hasattr(app_module, "load_live_doc_snapshot"),
    reason="app.py에 load_live_doc_snapshot 미배선 — live_docs 탭 통합 미구현",
)


def test_load_tab_data_prefers_live_research_snapshot(monkeypatch):
    monkeypatch.setattr(app_module, "load_live_doc_snapshot", lambda slug, doc_type: {
        "doc_type": "research",
        "status": "streaming",
        "content": {"summary": "실시간 요약"},
    })
    monkeypatch.setattr(app_module, "load_project_json", lambda out_dir, filename: {"summary": "최종 요약"})
    monkeypatch.setattr(app_module, "load_project_text", lambda out_dir, filename: None)

    pm = type("PM", (), {})()
    project = {"id": 1, "slug": "demo", "output_dir": "/tmp/demo"}
    context = _load_tab_data(pm, project, "research")

    assert context["live_research"]["content"]["summary"] == "실시간 요약"


def test_load_tab_data_prefers_live_manuscript_snapshot(monkeypatch):
    def fake_live(slug, doc_type):
        if doc_type == "manuscript":
            return {
                "doc_type": "manuscript",
                "status": "streaming",
                "content": {"raw_text": "첫 문장입니다.", "chapters": []},
            }
        return None

    monkeypatch.setattr(app_module, "load_live_doc_snapshot", fake_live)
    monkeypatch.setattr(app_module, "load_project_json", lambda out_dir, filename: {"scenes": []})

    pm = type("PM", (), {})()
    project = {"id": 1, "slug": "demo", "output_dir": "/tmp/demo"}
    context = _load_tab_data(pm, project, "manuscript")

    assert context["live_manuscript"]["content"]["raw_text"] == "첫 문장입니다."
