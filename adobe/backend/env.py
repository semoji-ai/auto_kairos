"""auto_kairos .env에서 API 키 로드 — os.environ 우선, 없으면 .env 파일 파싱."""
from __future__ import annotations

import os
from pathlib import Path


def kairos_env_path() -> Path | None:
    """AUTO_KAIROS_ENV 환경변수 → 없으면 LocalProjects/auto_kairos_v3/.env 후보."""
    p = os.environ.get("AUTO_KAIROS_ENV")
    if p:
        pp = Path(p).expanduser()
        return pp if pp.is_file() else None
    cand = Path(__file__).resolve().parents[2] / "auto_kairos_v3" / ".env"
    return cand if cand.is_file() else None


def _file_env() -> dict:
    fp = kairos_env_path()
    if not fp:
        return {}
    out: dict[str, str] = {}
    for line in fp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def get_key(name: str) -> str:
    """name 키 값. os.environ 우선, 없으면 auto_kairos .env. 없으면 ''."""
    return os.environ.get(name) or _file_env().get(name, "")
