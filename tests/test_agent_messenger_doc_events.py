import importlib
import sys
import types
from pathlib import Path


def _install_fastapi_stub():
    fastapi = types.ModuleType("fastapi")

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

    fastapi.APIRouter = APIRouter
    fastapi.Request = Request

    responses = types.ModuleType("fastapi.responses")

    class StreamingResponse:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class JSONResponse:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    responses.StreamingResponse = StreamingResponse
    responses.JSONResponse = JSONResponse

    sys.modules["fastapi"] = fastapi
    sys.modules["fastapi.responses"] = responses


_install_fastapi_stub()

agent_messenger = importlib.import_module("auto_agent.dashboard.agent_messenger")
post_message = agent_messenger.post_message

from auto_agent.orchestrator.runner import ProgressFileMonitor


def test_post_message_preserves_kind_for_doc_updates(tmp_path, monkeypatch):
    persist_path = tmp_path / "agent_messages.jsonl"
    monkeypatch.setattr(agent_messenger, "_PERSIST_FILE", persist_path)
    monkeypatch.setattr(agent_messenger, "_messages", [])
    monkeypatch.setattr(agent_messenger, "_initialized", True)
    monkeypatch.setattr(agent_messenger, "_msg_id", 0)
    monkeypatch.setattr(agent_messenger, "_subscribers", [])

    post_message(
        agent="홍탐정",
        text="리서치 문서 초기화",
        project_slug="demo",
        data={"doc_type": "research", "op": "snapshot"},
        kind="doc_update",
        skip_persist=False,
    )

    history = persist_path.read_text(encoding="utf-8")
    assert '"kind": "doc_update"' in history


def test_progress_monitor_forwards_doc_update(monkeypatch, tmp_path: Path):
    sent = []
    monkeypatch.setattr("auto_agent.orchestrator.runner._notify", lambda **kwargs: sent.append(kwargs))

    progress_path = tmp_path / ".progress.jsonl"
    progress_path.write_text(
        '{"kind":"doc_update","agent":"홍탐정","text":"초기화","level":"info","phase":"stage_1","data":{"doc_type":"research","op":"snapshot"}}\n',
        encoding="utf-8",
    )

    mon = ProgressFileMonitor(progress_path, project_slug="demo", phase="stage_1")
    mon._flush_remaining()

    assert sent[0]["kind"] == "doc_update"
    assert sent[0]["data"]["doc_type"] == "research"
    assert sent[0]["data"]["op"] == "snapshot"
