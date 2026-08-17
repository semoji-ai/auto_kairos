"""프로젝트별 codex 세션 id 저장/로드 (.codex_session 사이드카)."""
from __future__ import annotations

from pathlib import Path

_FILE = ".codex_session"


def load_session(proj_dir: Path) -> str | None:
    fp = proj_dir / _FILE
    if not fp.exists():
        return None
    val = fp.read_text(encoding="utf-8").strip()
    return val or None


def save_session(proj_dir: Path, session_id: str) -> None:
    (proj_dir / _FILE).write_text(session_id, encoding="utf-8")
