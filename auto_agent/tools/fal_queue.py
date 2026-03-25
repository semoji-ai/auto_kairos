"""FAL AI queue 비동기 클라이언트 — submit_batch / poll_all."""
from __future__ import annotations
import os
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    fal_client = None
    FAL_AVAILABLE = False


def _ensure_fal_key():
    """FAL_API_KEY → FAL_KEY 자동 매핑."""
    if not os.environ.get("FAL_KEY") and os.environ.get("FAL_API_KEY"):
        os.environ["FAL_KEY"] = os.environ["FAL_API_KEY"]


@dataclass
class FalJob:
    idx: int
    endpoint: str
    arguments: dict


@dataclass
class FalResult:
    idx: int
    success: bool
    images: list = field(default_factory=list)  # [{"url":..,"width":..,"height":..}]
    error: str | None = None


def submit_batch(jobs: list[FalJob]) -> list[str]:
    """모든 job을 FAL queue에 제출. request_id 목록 반환."""
    if not jobs:
        return []
    if not FAL_AVAILABLE:
        raise RuntimeError("fal_client 미설치. pip install fal-client")
    _ensure_fal_key()

    request_ids: list[str] = []
    for job in jobs:
        handle = fal_client.submit(job.endpoint, arguments=job.arguments)
        request_ids.append(handle.request_id)
        logger.debug("submitted job %d → %s", job.idx, handle.request_id)
    return request_ids


def poll_all(
    jobs: list[FalJob],
    request_ids: list[str],
    on_done: Callable[[FalResult], None],
    poll_interval: float = 2.0,
    timeout: float = 3600.0,
    max_retries: int = 2,
) -> list[FalResult]:
    """모든 request_id 폴링. 완료마다 on_done 콜백 호출."""
    if not jobs:
        return []
    if not FAL_AVAILABLE:
        raise RuntimeError("fal_client 미설치. pip install fal-client")
    _ensure_fal_key()

    # pending: {request_id: (job, retry_count, endpoint)}
    pending: dict[str, tuple[FalJob, int, str]] = {
        rid: (job, 0, job.endpoint) for rid, job in zip(request_ids, jobs)
    }
    all_results: list[FalResult] = []
    start = time.time()

    while pending and (time.time() - start) < timeout:
        time.sleep(poll_interval)
        for req_id in list(pending):
            job, retry_count, endpoint = pending[req_id]
            try:
                status_obj = fal_client.status(endpoint, req_id)
                status = status_obj.status
            except Exception as e:
                logger.warning("status 조회 실패 (req=%s): %s", req_id, e)
                continue

            if status == "COMPLETED":
                try:
                    raw = fal_client.result(endpoint, req_id)
                    result = FalResult(
                        idx=job.idx,
                        success=True,
                        images=raw.get("images", []),
                    )
                    try:
                        on_done(result)
                    except Exception as cb_err:
                        logger.warning("on_done 콜백 실패 (job %d): %s", job.idx, cb_err)
                    all_results.append(result)
                except Exception as e:
                    result = FalResult(idx=job.idx, success=False, error=str(e))
                    try:
                        on_done(result)
                    except Exception:
                        pass
                    all_results.append(result)
                del pending[req_id]

            elif status == "FAILED":
                if retry_count < max_retries:
                    try:
                        new_handle = fal_client.submit(job.endpoint, arguments=job.arguments)
                        del pending[req_id]
                        pending[new_handle.request_id] = (job, retry_count + 1, endpoint)
                        logger.info("job %d 재제출 (retry %d): %s", job.idx, retry_count + 1, new_handle.request_id)
                    except Exception as e:
                        logger.warning("재제출 실패 (job %d): %s", job.idx, e)
                        del pending[req_id]
                        result = FalResult(idx=job.idx, success=False, error=f"재제출 실패: {e}")
                        try:
                            on_done(result)
                        except Exception:
                            pass
                        all_results.append(result)
                else:
                    del pending[req_id]
                    result = FalResult(idx=job.idx, success=False, error="max_retries 초과")
                    try:
                        on_done(result)
                    except Exception:
                        pass
                    all_results.append(result)

    # timeout 초과 잔여
    for req_id, (job, _, _ep) in pending.items():
        result = FalResult(idx=job.idx, success=False, error="timeout")
        try:
            on_done(result)
        except Exception:
            pass
        all_results.append(result)

    return all_results
