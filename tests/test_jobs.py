from backend.jobs import JobRegistry


def test_create_and_get():
    reg = JobRegistry()
    jid = reg.create("scene-decompose", "demo01")
    assert jid.startswith("job_")
    j = reg.get(jid)
    assert j["status"] == "running"
    assert j["skill_name"] == "scene-decompose"
    assert j["project_id"] == "demo01"
    assert j["logs"] == []


def test_append_log_and_complete():
    reg = JobRegistry()
    jid = reg.create("scene-decompose", "demo01")
    reg.append_log(jid, "line1")
    reg.append_log(jid, "line2")
    reg.set_status(jid, "completed", artifact_paths=["projects/demo01/scenes.json"])
    j = reg.get(jid)
    assert j["logs"] == ["line1", "line2"]
    assert j["status"] == "completed"
    assert j["artifact_paths"] == ["projects/demo01/scenes.json"]


def test_get_unknown_returns_none():
    assert JobRegistry().get("job_999") is None


def test_set_status_stores_result():
    import time
    j = JobRegistry(); jid = j.create("x", "p")
    j.set_status(jid, "completed", result={"n": 3})
    assert j.get(jid)["result"] == {"n": 3}


def test_run_async_success():
    import time
    from backend.jobs import run_async
    j = JobRegistry(); jid = j.create("x", "p")
    run_async(j, jid, lambda: {"ok": True})
    for _ in range(50):
        if j.get(jid)["status"] != "running":
            break
        time.sleep(0.02)
    g = j.get(jid)
    assert g["status"] == "completed" and g["result"] == {"ok": True}


def test_run_async_failure_sets_failed():
    import time
    from backend.jobs import run_async
    j = JobRegistry(); jid = j.create("x", "p")
    def boom(): raise RuntimeError("터짐")
    run_async(j, jid, boom)
    for _ in range(50):
        if j.get(jid)["status"] != "running":
            break
        time.sleep(0.02)
    g = j.get(jid)
    assert g["status"] == "failed" and "터짐" in (g["error"] or "")


def test_request_cancel_and_flag():
    from backend.jobs import JobRegistry
    r = JobRegistry()
    jid = r.create("assistant", "p1")
    assert r.is_cancelled(jid) is False
    assert r.request_cancel(jid) is True
    assert r.is_cancelled(jid) is True
    assert [j["job_id"] for j in r.running_jobs("p1")] == [jid]
    r.set_status(jid, "cancelled")
    assert r.request_cancel(jid) is False       # 이미 끝난 잡은 취소 대상 아님
    assert r.running_jobs("p1") == []
    assert r.request_cancel("job_없음") is False


def test_run_async_marks_cancelled():
    import time
    from backend.jobs import JobRegistry, JobCancelled, run_async
    r = JobRegistry()
    jid = r.create("assistant", "p1")

    def _fn():
        raise JobCancelled("3개 처리 후 취소")

    run_async(r, jid, _fn)
    for _ in range(100):
        if r.get(jid)["status"] != "running":
            break
        time.sleep(0.01)
    j = r.get(jid)
    assert j["status"] == "cancelled" and j["error"] is None
