"""codex 내장 image_gen 병렬 러너 (codex-fleet 패턴).

codex_generate가 세션 안에서 out_path로 직접 복사하므로(2차 회수는 세션ID 기반)
워커 간 파일 회수 레이스가 없다 — mtime 전역 스캔 방식을 쓰지 않는 이유.
계정 한도(250 IPM)·RAM이 실질 병목 → 병렬 수는 여유 RAM 기반 auto.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional

from auto_agent.tools.codex_image import codex_generate

HARD_CAP = 32
RAM_PER_PROC_GB = 0.4


@dataclass
class CodexImageJob:
    idx: int
    prompt: str
    size: str
    out_path: Path
    ref_images: Optional[list] = None


@dataclass
class CodexImageResult:
    idx: int
    success: bool
    error: str = ""


def _free_ram_gb() -> float:
    try:
        import psutil  # 선택 의존성
        return psutil.virtual_memory().available / (1024 ** 3)
    except Exception:
        return 4.0  # 보수적 기본값 → 워커 ~10


def _auto_parallel(n_jobs: int) -> int:
    env = os.getenv("CODEX_IMG_PARALLEL", "").strip()
    if env.isdigit() and int(env) > 0:
        return int(env)
    cap = int(_free_ram_gb() / RAM_PER_PROC_GB)
    return max(1, min(n_jobs, cap, HARD_CAP))


def run_codex_batch(
    jobs: List[CodexImageJob],
    *,
    on_done: Optional[Callable[[CodexImageResult], None]] = None,
    timeout: int = 240,
) -> List[CodexImageResult]:
    if not jobs:
        return []
    workers = _auto_parallel(len(jobs))
    results: List[CodexImageResult] = []

    def _one(job: CodexImageJob) -> CodexImageResult:
        ok, err = codex_generate(
            job.prompt, job.out_path,
            ref_images=job.ref_images, size=job.size, timeout=timeout,
        )
        return CodexImageResult(idx=job.idx, success=ok, error=err)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_one, j): j for j in jobs}
        for fut in as_completed(futures):
            res = fut.result()
            results.append(res)
            if on_done:
                on_done(res)
    return results
