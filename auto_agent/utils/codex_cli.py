"""codex CLI 공용 유틸 — 명령 빌드 + 출력 회수.

agent_runner(파이프라인 외부)와 orchestrator/runner(파이프라인)가 공유한다.
"""
from __future__ import annotations

import os
import re
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


# 추론 강도는 기본으로 지정하지 않는다(전역 config 를 따른다). low 로 낮춰 보았으나
# 한화편 #65 실측에서 medium 28,535 / low 37,828 토큰으로 줄지 않았다 — 토큰 대부분이
# 첨부 그림을 읽는 데 든다. 필요하면 CODEX_IMAGEGEN_EFFORT 로 지정한다.
DEFAULT_IMAGEGEN_EFFORT = ""


def imagegen_model_args() -> List[str]:
    """$imagegen 용 codex exec 에 붙일 모델·추론 강도 인자.

    CODEX_IMAGEGEN_MODEL · CODEX_IMAGEGEN_EFFORT 로 바꾼다.
    """
    model = os.environ.get("CODEX_IMAGEGEN_MODEL", "").strip() or DEFAULT_IMAGEGEN_MODEL
    effort = os.environ.get("CODEX_IMAGEGEN_EFFORT", "").strip() or DEFAULT_IMAGEGEN_EFFORT
    args = ["-m", model]
    if effort:
        args += ["-c", f'model_reasoning_effort="{effort}"']
    return args


_TOKENS_RE = re.compile(r"tokens used\s*\n?\s*([\d,]+)")


def log_codex_usage(output: str, log_path: Path, label: str) -> None:
    """codex exec 출력의 「tokens used」를 jsonl 로 남긴다 — 이미지 한 장의 토큰 비용."""
    import json
    m = _TOKENS_RE.search(output or "")
    if not m:
        return
    rec = {"label": label, "tokens": int(m.group(1).replace(",", "")),
           "model": os.environ.get("CODEX_IMAGEGEN_MODEL") or DEFAULT_IMAGEGEN_MODEL,
           "effort": os.environ.get("CODEX_IMAGEGEN_EFFORT") or DEFAULT_IMAGEGEN_EFFORT or "global"}
    with Path(log_path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_SESSION_RE = re.compile(r"session id:\s*([0-9a-fA-F-]{8,})")


def claim_session_image(output: str, out_path: Path) -> bool:
    """codex exec 출력의 세션 ID로 **그 세션이 만든** 마지막 그림을 out_path 에 놓는다.

    프롬프트로 「generated_images 의 최신 PNG 를 복사하라」고 시키면, 여러 codex 를
    병렬로 돌릴 때 서로 남의 결과를 집어 온다 — 한화편 시트 다섯 갈래 중 세 장이
    바이트까지 같은 그림이었다. 그림은 `generated_images/<세션ID>/` 에 떨어지므로
    그 폴더가 정본이다.

    이 세션이 그림을 못 만들었는데 out_path 에 파일이 있으면 남의 그림이다.
    지우지 않고 `.stray.png` 로 비켜 두고 실패로 돌려준다.
    """
    out_path = Path(out_path)
    m = _SESSION_RE.search(output or "")
    if not m:
        return out_path.exists()
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    d = home / "generated_images" / m.group(1)
    pngs = sorted(d.glob("*.png"), key=lambda p: p.stat().st_mtime) if d.exists() else []
    if not pngs:
        if out_path.exists():
            out_path.replace(out_path.with_suffix(".stray.png"))
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pngs[-1], out_path)
    return True


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
