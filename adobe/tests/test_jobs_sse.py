import queue
import time
from backend.jobs import JobRegistry, run_async


def test_subscribe_receives_log_and_status_events():
    j = JobRegistry()
    q = j.subscribe()
    jid = j.create("x", "p")
    j.append_log(jid, "진행 1")
    j.set_status(jid, "completed", result={"ok": True})
    ev1 = q.get_nowait()
    assert ev1 == {"type": "log", "job_id": jid, "line": "진행 1"}
    ev2 = q.get_nowait()
    assert ev2["type"] == "status" and ev2["status"] == "completed" and ev2["job_id"] == jid


def test_unsubscribe_stops_events():
    j = JobRegistry()
    q = j.subscribe()
    j.unsubscribe(q)
    jid = j.create("x", "p")
    j.append_log(jid, "x")
    try:
        q.get_nowait()
        assert False, "구독 해제 후 이벤트 수신"
    except queue.Empty:
        pass


def test_running_status_not_emitted():
    j = JobRegistry()
    q = j.subscribe()
    jid = j.create("x", "p")
    j.set_status(jid, "running")
    try:
        q.get_nowait()
        assert False
    except queue.Empty:
        pass


def test_run_async_emits_completion():
    j = JobRegistry()
    q = j.subscribe()
    jid = j.create("x", "p")
    run_async(j, jid, lambda: {"n": 1})
    ev = q.get(timeout=2)
    assert ev["type"] == "status" and ev["status"] == "completed"
