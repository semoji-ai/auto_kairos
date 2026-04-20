"""FAL AI 배치 클라이언트 - subscribe 동기식 + ThreadPoolExecutor 병렬."""
from __future__ import annotations
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    fal_client = None
    FAL_AVAILABLE = False


def _ensure_fal_key():
    """FAL_API_KEY -> FAL_KEY 자동 매핑."""
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


def _run_single(job: FalJob, max_retries: int = 2) -> FalResult:
    """단일 job을 subscribe(동기)로 실행. 실패 시 재시도."""
    for attempt in range(max_retries + 1):
        try:
            raw = fal_client.subscribe(job.endpoint, arguments=job.arguments)
            images = raw.get("images", [])
            return FalResult(idx=job.idx, success=True, images=images)
        except Exception as e:
            print(f"[fal_queue] job {job.idx} 실패 (attempt {attempt+1}/{max_retries+1}): {e}", flush=True)
            if attempt >= max_retries:
                return FalResult(idx=job.idx, success=False, error=str(e))
    return FalResult(idx=job.idx, success=False, error="max_retries 초과")


def run_batch(
    jobs: list[FalJob],
    on_done: Optional[Callable[[FalResult], None]] = None,
    max_workers: int = 10,
    max_retries: int = 2,
) -> list[FalResult]:
    """subscribe 동기식 + ThreadPoolExecutor 병렬 실행.

    Args:
        jobs: FAL 작업 목록
        on_done: 각 job 완료 시 콜백 (optional)
        max_workers: 동시 실행 수 (기본 5)
        max_retries: 실패 시 재시도 횟수 (기본 2)
    """
    if not jobs:
        return []
    if not FAL_AVAILABLE:
        raise RuntimeError("fal_client 미설치. pip install fal-client")
    _ensure_fal_key()

    print(f"[fal_queue] {len(jobs)}개 job 배치 시작 (workers={max_workers})", flush=True)
    all_results: list[FalResult] = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_single, job, max_retries): job
            for job in jobs
        }
        for future in as_completed(futures):
            job = futures[future]
            try:
                result = future.result()
            except Exception as e:
                result = FalResult(idx=job.idx, success=False, error=str(e))

            all_results.append(result)
            status = "OK" if result.success else f"FAIL: {result.error}"
            print(f"[fal_queue] job {result.idx} {status}", flush=True)

            if on_done:
                try:
                    on_done(result)
                except Exception as cb_err:
                    logger.warning("on_done 콜백 실패 (job %d): %s", result.idx, cb_err)

    success = sum(1 for r in all_results if r.success)
    print(f"[fal_queue] 배치 완료: {success}/{len(jobs)} 성공", flush=True)
    return all_results


# --- 하위 호환 ---
# image_batch_module.py에서 submit_batch + poll_all 호출하던 코드 호환
def submit_batch(jobs: list[FalJob]) -> list[str]:
    """하위 호환용. run_batch()를 사용하세요."""
    return [f"compat-{job.idx}" for job in jobs]


def poll_all(
    jobs: list[FalJob],
    request_ids: list[str],
    on_done: Callable[[FalResult], None],
    poll_interval: float = 2.0,
    timeout: float = 3600.0,
    max_retries: int = 2,
) -> list[FalResult]:
    """하위 호환용. 내부에서 run_batch()로 위임."""
    return run_batch(jobs, on_done=on_done, max_retries=max_retries)
