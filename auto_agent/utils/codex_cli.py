"""codex CLI 공용 유틸 — 명령 빌드 + 출력 회수.

agent_runner(파이프라인 외부)와 orchestrator/runner(파이프라인)가 공유한다.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional


def find_codex_cli() -> str:
    """Codex CLI 바이너리 경로. 없으면 FileNotFoundError."""
    path = shutil.which("codex")
    if path:
        return path
    raise FileNotFoundError("Codex CLI를 찾을 수 없습니다. 'codex'가 PATH에 있는지 확인하세요.")


def codex_available() -> bool:
    return shutil.which("codex") is not None


# $imagegen 배치를 지휘하는 모델. 그림을 그리는 것은 codex 내장 image_gen 이고,
# 이 모델은 프롬프트를 읽고 view_image·image_gen 을 부르는 역할이다.
# 전역 ~/.codex/config.toml 이 바뀌어도 이미지 작업은 흔들리지 않게 여기서 고정한다.
DEFAULT_IMAGEGEN_MODEL = "gpt-6.1-sol"


def imagegen_model_args() -> List[str]:
    """$imagegen 용 codex exec 에 붙일 모델 인자. CODEX_IMAGEGEN_MODEL 로 바꾼다."""
    model = os.environ.get("CODEX_IMAGEGEN_MODEL", "").strip() or DEFAULT_IMAGEGEN_MODEL
    return ["-m", model]


def build_codex_exec_cmd(
    *,
    workdir: Path,
    output_last_message: str,
    model: Optional[str] = None,
    reasoning_effort: str = "medium",
    search: bool = False,
    sandbox: str = "workspace-write",
) -> List[str]:
    """codex exec 명령 빌드. 프롬프트는 stdin으로 전달한다."""
    cmd = [find_codex_cli()]

    # --search는 최상위 플래그 (exec 앞에 위치)
    if search:
        cmd.append("--search")

    cmd += [
        "exec",
        "-C", str(workdir),
        "--skip-git-repo-check",
        "--ephemeral",
        "--sandbox", sandbox,
        "-c", f'model_reasoning_effort="{reasoning_effort}"',
        "--json",
        "--output-last-message", output_last_message,
    ]

    if model:
        cmd += ["-m", model]

    return cmd


def read_output_last_message(path: Optional[str], fallback: str = "") -> str:
    if not path:
        return fallback
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
        return text or fallback
    except Exception:
        return fallback
