"""chapter-marker 에이전트 호출 래퍼 — narration substring 보존 보장.

runner.py의 _run_agent_step 패턴을 직접 복제:
  - claude CLI 바이너리를 subprocess.Popen으로 실행
  - 프롬프트를 stdin으로 전달 (-p 플래그 사용 안 함)
  - --dangerously-skip-permissions 플래그 사용
  - allowed_tools: Read, Write 만
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

from auto_agent.utils.platform import subprocess_kwargs


def _find_claude_cli() -> str:
    path = shutil.which("claude")
    if path:
        return path
    raise FileNotFoundError(
        "Claude CLI를 찾을 수 없습니다. 'claude'가 PATH에 있는지 확인하세요."
    )


def insert_markers(manuscript: str, outline: Dict[str, Any], project_dir: Path) -> str:
    """chapter-marker 에이전트 호출 → final_manuscript.md에 마커 삽입.

    narration 본문은 절대 변경되지 않음 (post-validation으로 검증).

    Args:
        manuscript: v4 final_manuscript.md 의 전문 텍스트
        outline: outline.json dict (chapters 배열 포함)
        project_dir: 프로젝트 디렉토리 (워킹 디렉토리로 사용)

    Returns:
        마커가 삽입된 마크다운 텍스트

    Raises:
        ValueError: 에이전트가 narration을 변경했을 경우
        RuntimeError: Claude CLI 호출 실패
    """
    workdir = project_dir / "_bridge"
    workdir.mkdir(parents=True, exist_ok=True)

    input_path = workdir / "_chapter_marker_input.json"
    output_path = workdir / "final_manuscript_marked.md"

    input_data = {
        "final_manuscript": manuscript,
        "outline": outline,
        "output_path": str(output_path),
    }
    input_path.write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 프롬프트 구성 ──
    skill_dir = Path(__file__).parent.parent.parent / "data" / "skills" / "agents" / "chapter-marker"
    skill_path = skill_dir / "SKILL.md"
    skill_text = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    prompt = (
        f"{skill_text}\n\n"
        f"## 작업 지시\n\n"
        f"입력 파일을 Read 도구로 읽으세요: `{input_path}`\n\n"
        f"파일 안의 `final_manuscript` 텍스트에 `outline.chapters`를 기준으로 "
        f"`# Ch N. <title>` 헤더와 `---` 구분선을 삽입하세요.\n\n"
        f"완성된 결과를 Write 도구로 `output_path` 경로에 저장하세요.\n"
        f"narration 본문을 한 글자도 바꾸지 마세요."
    )

    # ── Claude CLI 호출 ──
    cli_path = _find_claude_cli()
    cmd = [
        cli_path,
        "--print",
        "--output-format", "json",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "8",
        "--dangerously-skip-permissions",
        "--allowedTools", "Read",
        "--allowedTools", "Write",
    ]

    env = os.environ.copy()
    env.pop("CLAUDECODE", None)  # 중첩 세션 방지

    popen_flags = subprocess_kwargs()
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(workdir),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            **popen_flags,
        )
        stdout, stderr = proc.communicate(input=prompt, timeout=300)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        raise RuntimeError("chapter-marker 에이전트 타임아웃 (300s)")

    if proc.returncode != 0:
        raise RuntimeError(
            f"chapter-marker 에이전트 실패 (exit={proc.returncode})\n{stderr[:500]}"
        )

    if not output_path.exists():
        raise RuntimeError(
            f"chapter-marker가 출력 파일을 생성하지 않았습니다: {output_path}"
        )

    marked = output_path.read_text(encoding="utf-8")
    _validate_substring(manuscript, marked)
    return marked


def _validate_substring(original: str, marked: str) -> None:
    """마커/주석/공백을 제거한 후 원본 narration이 그대로 들어 있는지 확인.

    실패 시 ValueError (에이전트가 narration을 변경했음).
    """
    stripped_lines = [
        line for line in marked.splitlines()
        if not line.startswith("#")
        and line.strip() != "---"
        and not (line.strip().startswith("<!--") and line.strip().endswith("-->"))
    ]
    stripped = "\n".join(stripped_lines)

    norm = lambda s: " ".join(s.split())
    if norm(original) not in norm(stripped):
        raise ValueError(
            "chapter-marker가 narration을 변경했습니다. "
            "marked.md의 본문이 원본 manuscript의 substring이 아닙니다.\n"
            f"원본(norm) 앞 100자: {norm(original)[:100]}\n"
            f"결과(norm) 앞 200자: {norm(stripped)[:200]}"
        )
