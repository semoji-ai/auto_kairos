"""codex CLI 공용 유틸 — 명령 빌드 + 출력 회수.

agent_runner(파이프라인 외부)와 orchestrator/runner(파이프라인)가 공유한다.
"""
from __future__ import annotations

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


def build_codex_exec_cmd(
    *,
    workdir: Path,
    output_last_message: str,
    model: Optional[str] = None,
    reasoning_effort: str = "medium",
    search: bool = False,
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
        "--sandbox", "workspace-write",
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
