"""codex exec 래퍼 — 커맨드 빌드(순수) + 스킬 실행(subprocess, stdin 프롬프트 + 스트리밍)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def codex_exe() -> str:
    """codex 실행 파일의 **전체 경로**.

    윈도우에서 `subprocess.run(["codex", ...])` 가 `[WinError 2] 지정된 파일을
    찾을 수 없습니다` 로 죽는다. 파일이 없다는 뜻이 아니라 **윈도우가 실행 파일을
    못 찾았다**는 뜻이다 — `CreateProcess` 는 `PATHEXT` 를 뒤지지 않으므로,
    확장자 없이 넘긴 이름으로는 `codex.CMD` 를 찾지 못한다.

        codex   →  ...\\npm\\codex.CMD    ← 이름만으로는 못 찾는다
        claude  →  ...\\bin\\claude.EXE   ← .EXE 라서 찾힌다

    그래서 `claude` 를 쓰는 경로는 멀쩡하고 codex 를 쓰는 경로만 죽었다. 패널의
    레이어 분석이 정확히 여기를 탄다(analyze-layers → run_orchestrator →
    run_skill → build_codex_cmd).

    PATH 에 없으면 종전대로 이름만 돌려준다 — 못 찾는 것과 없는 것은 다르다.
    """
    return shutil.which("codex") or "codex"


def build_codex_cmd(
    *,
    session_id: str | None = None,
    output_schema: str | None = None,
    output_last: str | None = None,
    json_events: bool = True,
    skip_git: bool = True,
    sandbox: str | None = None,
    images: list | None = None,
) -> list[str]:
    """codex exec 커맨드 리스트. 프롬프트는 stdin으로 넘기므로 positional은 '-'.
    session_id 있으면 resume."""
    cmd = [codex_exe(), "exec"]
    if session_id:
        cmd += ["resume", session_id]
    if sandbox:
        cmd += ["-s", sandbox]
    if images:
        for img in images:
            cmd += ["-i", img]
    if skip_git:
        cmd += ["--skip-git-repo-check"]
    if json_events:
        cmd += ["--json"]
    if output_schema:
        cmd += ["--output-schema", output_schema]
    if output_last:
        cmd += ["-o", output_last]
    cmd += ["-"]  # 프롬프트는 stdin (긴/'--'로 시작하는 프롬프트 안전)
    return cmd


def _extract_session_id(json_line: str) -> str | None:
    try:
        evt = json.loads(json_line)
    except ValueError:
        return None
    if isinstance(evt, dict):
        for key in ("session_id", "sessionId", "conversation_id", "thread_id"):
            if evt.get(key):
                return str(evt[key])
    return None


def run_skill(
    prompt: str,
    cwd: Path,
    *,
    session_id: str | None = None,
    output_schema: str | None = None,
    output_last: str | None = None,
    sandbox: str | None = None,
    images: list | None = None,
    on_line=None,
) -> dict:
    """codex exec 실행. 프롬프트는 stdin으로 전달. 각 stdout 라인을 on_line(line)으로 흘림.
    반환: {returncode, session_id, output_last}."""
    cmd = build_codex_cmd(
        session_id=session_id, output_schema=output_schema,
        output_last=output_last, sandbox=sandbox, images=images,
    )
    proc = subprocess.Popen(
        cmd, cwd=str(cwd),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", bufsize=1,
    )
    try:
        if proc.stdin is not None:
            proc.stdin.write(prompt)
            proc.stdin.close()
    except BrokenPipeError:
        pass
    found_session = session_id
    if proc.stdout is not None:
        for line in proc.stdout:
            line = line.rstrip("\n")
            if on_line:
                on_line(line)
            if found_session is None:
                sid = _extract_session_id(line)
                if sid:
                    found_session = sid
    proc.wait()
    return {
        "returncode": proc.returncode,
        "session_id": found_session,
        "output_last": output_last,
    }
