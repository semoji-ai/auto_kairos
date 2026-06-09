"""codex_image — 오케스트레이터가 codex CLI 내장 image_gen 툴로 이미지 생성.

codex 세션을 열어 생성 → 산출물 회수 → 세션 종료(ephemeral)하는 방식.
codex 구독 인증을 사용하므로 **OPENAI_API_KEY 불필요** (의도적으로 env에서 제거).

Fallback CLI(`~/.codex/.../scripts/image_gen.py`)와는 무관하다 — 그건 OPENAI_API_KEY가
필요한 OpenAI SDK 직접 경로다. 여기서는 codex 에이전트의 내장 `image_gen` 툴만 쓴다.

검증된 동작 (스모크 테스트):
  env -u OPENAI_API_KEY codex exec --cd <dir> -s workspace-write --ephemeral \
    --color never "<프롬프트>"
  → 산출물은 $CODEX_HOME/generated_images/<session_id>/ig_<hash>.png 에 떨어진다.
  → codex 시작 시 'session id: <uuid>' 를 출력하므로 세션ID로 회수 가능.
  → 내장 툴은 크기 비결정적(1024 요청→1254 생성) → 회수 후 PIL로 강제 리사이즈.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# CODEX_HOME 기본값은 ~/.codex (codex CLI 규약). 절대경로 하드코딩 금지.
CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))

_SESSION_RE = re.compile(r"session id:\s*([0-9a-fA-F-]{8,})")
_RESULT_RE = re.compile(r"RESULT_PATH=(\S+)")


def codex_available() -> bool:
    """이 머신에서 codex CLI를 쓸 수 있는지."""
    return shutil.which("codex") is not None


def _build_instruction(prompt: str, out_path: Path, has_refs: bool) -> str:
    task = "Edit the attached reference image(s)" if has_refs else "Generate a new image"
    return (
        "Use ONLY your built-in image_gen tool — never the fallback CLI "
        "(scripts/image_gen.py), never any OPENAI_API_KEY/OpenAI-SDK path.\n\n"
        f"{task} per this description:\n\n{prompt}\n\n"
        f"After it is generated, copy the final image to: {out_path}\n"
        f"On the LAST line of your response print exactly: RESULT_PATH={out_path}\n"
        "Do not modify, create, or delete any other files. Do not run git."
    )


def _resize_to(out_path: Path, size: str) -> None:
    """내장 툴 크기 비결정성 보정 — size('WxH')로 강제 리사이즈."""
    try:
        from PIL import Image  # 지연 임포트 (PIL 미설치 환경 보호)

        w, h = (int(x) for x in size.lower().split("x"))
        im = Image.open(out_path)
        if im.size != (w, h):
            im.resize((w, h)).save(out_path)
    except Exception:
        # 리사이즈 실패는 치명적 아님 — 원본 유지
        pass


def codex_generate(
    prompt: str,
    out_path,
    *,
    ref_images: Optional[list] = None,
    size: Optional[str] = None,
    cd: Optional[Path] = None,
    timeout: int = 420,
) -> tuple[bool, str]:
    """codex 내장 image_gen 툴로 이미지를 생성/편집해 out_path로 회수.

    Args:
        prompt: 이미지 묘사 프롬프트 (호출부에서 레이어별로 구성).
        out_path: 최종 PNG 저장 경로.
        ref_images: 편집/참조용 이미지 경로 리스트 (있으면 edit 모드).
        size: 'WxH' (예: '1024x1024'). 주면 회수 후 강제 리사이즈.
        cd: codex 작업 루트 (기본: out_path.parent). workspace-write 대상.
        timeout: codex exec 타임아웃(초).

    Returns:
        (ok, err). ok=True면 out_path에 PNG 존재 보장.
    """
    codex = shutil.which("codex")
    if not codex:
        return (False, "codex CLI not found (PATH)")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    work = str(cd or out_path.parent)

    refs = [Path(r) for r in (ref_images or []) if r and Path(r).exists()]
    instr = _build_instruction(prompt, out_path, has_refs=bool(refs))

    cmd = [
        codex, "exec",
        "--cd", work,
        "--skip-git-repo-check",
        "-s", "workspace-write",
        "--ephemeral",
        "--color", "never",
    ]
    for r in refs:
        cmd += ["-i", str(r)]
    cmd.append(instr)

    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)  # 무키 경로 강제 — codex 구독 인증만 사용

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return (False, f"codex exec timeout ({timeout}s)")

    stdout = res.stdout or ""

    # 1차 회수: codex가 out_path로 직접 복사했는가
    if not out_path.exists():
        # 2차 회수: 세션ID로 generated_images에서 최신 PNG 가져오기
        m = _SESSION_RE.search(stdout)
        if m:
            gen_dir = CODEX_HOME / "generated_images" / m.group(1)
            pngs = sorted(gen_dir.glob("*.png")) if gen_dir.exists() else []
            if pngs:
                shutil.copy(pngs[-1], out_path)

    if not out_path.exists():
        tail = (res.stderr or stdout)[-400:]
        return (False, f"no output produced. {tail}")

    if size:
        _resize_to(out_path, size)

    return (True, "")
