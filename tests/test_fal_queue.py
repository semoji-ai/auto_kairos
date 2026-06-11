"""fal_queue 테스트 — subscribe 동기식 + ThreadPoolExecutor 구조 (run_batch가 주 API).

옛 큐 제출/폴링(submit→request_id→poll) 구조는 제거되었고,
submit_batch/poll_all은 run_batch로 위임하는 하위 호환 껍데기만 남아 있다.
"""
from unittest.mock import patch

from auto_agent.tools.fal_queue import FalJob, FalResult, run_batch, submit_batch, poll_all


def _make_jobs(n: int) -> list:
    return [FalJob(idx=i, endpoint="fal-ai/nano-banana-2", arguments={"prompt": f"p{i}"}) for i in range(n)]


def test_run_batch_empty():
    """빈 job 목록이면 빈 리스트 반환 (fal_client 호출 없음)."""
    assert run_batch([]) == []


def test_run_batch_executes_all_jobs():
    """모든 job이 성공하면 결과 수 = job 수, on_done이 각각 호출된다."""
    jobs = _make_jobs(2)
    done_results = []

    fake_result = {"images": [{"url": "http://x.com/img.png", "width": 512, "height": 512}]}

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal, \
         patch("auto_agent.tools.fal_queue.FAL_AVAILABLE", True):
        mock_fal.subscribe.return_value = fake_result
        results = run_batch(jobs, on_done=done_results.append)

    assert len(results) == 2
    assert all(r.success for r in results)
    assert len(done_results) == 2
    assert mock_fal.subscribe.call_count == 2


def test_run_batch_retries_then_fails():
    """subscribe가 계속 실패하면 max_retries+1회 시도 후 success=False."""
    jobs = _make_jobs(1)

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal, \
         patch("auto_agent.tools.fal_queue.FAL_AVAILABLE", True):
        mock_fal.subscribe.side_effect = RuntimeError("FAL down")
        results = run_batch(jobs, max_retries=1)

    assert len(results) == 1
    assert not results[0].success
    assert "FAL down" in (results[0].error or "")
    assert mock_fal.subscribe.call_count == 2  # 최초 1회 + 재시도 1회


def test_run_batch_retry_recovers():
    """첫 시도 실패 후 재시도에서 성공하면 success=True."""
    jobs = _make_jobs(1)
    fake_result = {"images": [{"url": "http://x.com/img.png"}]}

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal, \
         patch("auto_agent.tools.fal_queue.FAL_AVAILABLE", True):
        mock_fal.subscribe.side_effect = [RuntimeError("일시 오류"), fake_result]
        results = run_batch(jobs, max_retries=2)

    assert results[0].success
    assert results[0].images == fake_result["images"]


def test_run_batch_callback_exception_continues():
    """on_done 콜백에서 예외가 발생해도 나머지 job 처리가 계속된다."""
    jobs = _make_jobs(2)
    success_count = {"n": 0}

    fake_result = {"images": [{"url": "http://x.com/img.png"}]}

    def on_done(r: FalResult):
        if r.idx == 0:
            raise ValueError("저장 실패")
        success_count["n"] += 1

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal, \
         patch("auto_agent.tools.fal_queue.FAL_AVAILABLE", True):
        mock_fal.subscribe.return_value = fake_result
        results = run_batch(jobs, on_done=on_done)

    assert len(results) == 2
    assert success_count["n"] == 1  # idx=1은 정상 처리됨


def test_compat_shims_delegate_to_run_batch():
    """submit_batch는 placeholder id, poll_all은 run_batch 위임 — 하위 호환 계약."""
    jobs = _make_jobs(2)
    ids = submit_batch(jobs)
    assert ids == ["compat-0", "compat-1"]

    done_results = []
    fake_result = {"images": [{"url": "http://x.com/img.png"}]}
    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal, \
         patch("auto_agent.tools.fal_queue.FAL_AVAILABLE", True):
        mock_fal.subscribe.return_value = fake_result
        results = poll_all(jobs, ids, on_done=done_results.append)

    assert len(results) == 2
    assert len(done_results) == 2
