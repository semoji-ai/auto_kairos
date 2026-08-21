"""auto_kairos .env에서 API 키 로드 — os.environ 우선, 없으면 .env 파일 파싱."""
from __future__ import annotations

import os
from pathlib import Path


def kairos_env_path() -> Path | None:
    """AUTO_KAIROS_ENV 환경변수 → 없으면 저장소의 `.env`.

    **통합 전 경로가 남아 있었다.** adobe 가 별도 저장소로 `auto_kairos_v3/`
    **옆에** 있던 시절에는 `parents[2]/auto_kairos_v3/.env` 가 맞았다. 지금은
    `adobe/` 가 저장소 **안으로** 들어와 `parents[2]` 자체가 저장소 루트다 —
    그 뒤에 이름을 한 번 더 붙이면 `auto_kairos_v3/auto_kairos_v3/.env` 라는
    없는 경로가 된다.

    그래서 키를 못 찾았고, `_engine()` 이 일레븐랩스 대신 맥 `say` 로
    떨어졌다. 재생성한 음성이 전부 기본 한국어 여성(Yuna)으로 나오던 원인이다 —
    목소리를 골라도 소용이 없었다. 고른 값은 일레븐랩스에만 쓰인다.

    두 배치를 다 본다. 예전 배치로 쓰는 곳이 남아 있을 수 있다.
    """
    p = os.environ.get("AUTO_KAIROS_ENV")
    if p:
        pp = Path(p).expanduser()
        return pp if pp.is_file() else None
    root = Path(__file__).resolve().parents[2]
    for cand in (root / ".env",                          # 통합본 — adobe/ 가 저장소 안
                 root / "auto_kairos_v3" / ".env"):      # 통합 전 — 저장소가 옆에
        if cand.is_file():
            return cand
    return None


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
