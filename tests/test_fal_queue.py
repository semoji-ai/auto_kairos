import pytest
from unittest.mock import MagicMock, patch
from auto_agent.tools.fal_queue import FalJob, FalResult, submit_batch, poll_all


def test_submit_batch_returns_request_ids():
    """submit_batch가 job당 request_id를 반환한다."""
    mock_handle = MagicMock()
    mock_handle.request_id = "req-abc123"

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.submit.return_value = mock_handle
        jobs = [
            FalJob(idx=0, endpoint="fal-ai/nano-banana-2", arguments={"prompt": "test"}),
            FalJob(idx=1, endpoint="fal-ai/nano-banana-2", arguments={"prompt": "test2"}),
        ]
        ids = submit_batch(jobs)

    assert len(ids) == 2
    assert ids[0] == "req-abc123"
    assert mock_fal.submit.call_count == 2


def test_submit_batch_empty():
    """빈 job 목록이면 빈 리스트 반환."""
    with patch("auto_agent.tools.fal_queue.fal_client"):
        result = submit_batch([])
    assert result == []


def _make_jobs(n: int) -> list:
    return [FalJob(idx=i, endpoint="ep", arguments={}) for i in range(n)]


def test_poll_all_completes_all():
    """모든 job이 COMPLETED로 완료되면 on_done이 각각 호출된다."""
    jobs = _make_jobs(2)
    request_ids = ["req-0", "req-1"]
    done_results = []

    fake_status = MagicMock()
    fake_status.status = "COMPLETED"
    fake_result = {"images": [{"url": "http://x.com/img.png", "width": 512, "height": 512}]}

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.return_value = fake_status
        mock_fal.result.return_value = fake_result
        poll_all(jobs, request_ids, on_done=done_results.append)

    assert len(done_results) == 2
    assert all(r.success for r in done_results)


def test_poll_all_retries_on_failure():
    """FAILED 시 max_retries만큼 재제출하고 그래도 실패하면 success=False."""
    jobs = _make_jobs(1)
    request_ids = ["req-0"]
    done_results = []

    new_handle = MagicMock()
    new_handle.request_id = "req-retry"

    def fake_status(req_id):
        s = MagicMock()
        s.status = "FAILED"
        return s

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.side_effect = fake_status
        mock_fal.submit.return_value = new_handle
        poll_all(jobs, request_ids, on_done=done_results.append, max_retries=1)

    assert len(done_results) == 1
    assert not done_results[0].success
    assert mock_fal.submit.call_count == 1  # 1번 재제출


def test_poll_all_timeout():
    """timeout 초과 시 미완료 job이 success=False로 처리된다."""
    jobs = _make_jobs(1)
    request_ids = ["req-0"]
    done_results = []

    fake_status = MagicMock()
    fake_status.status = "IN_QUEUE"

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.return_value = fake_status
        with patch("auto_agent.tools.fal_queue.time") as mock_time:
            mock_time.time.side_effect = [0, 0, 9999]  # 즉시 timeout
            mock_time.sleep = MagicMock()
            poll_all(jobs, request_ids, on_done=done_results.append, timeout=1.0)

    assert len(done_results) == 1
    assert not done_results[0].success
    assert "timeout" in (done_results[0].error or "")


def test_poll_all_callback_exception_continues():
    """on_done 콜백에서 예외 발생해도 폴링 루프가 계속된다."""
    jobs = _make_jobs(2)
    request_ids = ["req-0", "req-1"]
    success_count = {"n": 0}

    fake_status = MagicMock()
    fake_status.status = "COMPLETED"
    fake_result = {"images": [{"url": "http://x.com/img.png", "width": 512, "height": 512}]}

    def on_done(r):
        if r.idx == 0:
            raise ValueError("저장 실패")
        success_count["n"] += 1

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.return_value = fake_status
        mock_fal.result.return_value = fake_result
        poll_all(jobs, request_ids, on_done=on_done)

    assert success_count["n"] == 1  # idx=1은 정상 처리됨
