"""fontagent CLI 어댑터.

기본 정책: v3 vault 공유(`auto_kairos_v3` root). v4 별도 vault 필요 시 환경 변수
`AUTO_KAIROS_V4_FONTAGENT_ROOT` 로 override.

CLI: `fontagent --root <ROOT> recommend-use-case --medium ... --surface ... --role ...`
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Projects" / "auto_kairos_v3"
ENV_OVERRIDE = "AUTO_KAIROS_V4_FONTAGENT_ROOT"


def fontagent_root() -> Path:
    return Path(os.environ.get(ENV_OVERRIDE, DEFAULT_ROOT))


def is_available() -> bool:
    return shutil.which("fontagent") is not None and (fontagent_root() / "fontagent.db").exists()


def catalog_status() -> dict:
    if not is_available():
        return {"available": False}
    out = subprocess.run(
        ["fontagent", "--root", str(fontagent_root()), "catalog-status"],
        capture_output=True, text=True, timeout=30,
    )
    if out.returncode != 0:
        return {"available": False, "error": out.stderr.strip()}
    try:
        return {"available": True, **json.loads(out.stdout)}
    except json.JSONDecodeError:
        return {"available": True, "raw": out.stdout}


def recommend(
    *,
    medium: str,             # video | web | print
    surface: str,            # narration | thumbnail | scene_overlay | landing_hero | ...
    role: str,               # headline | body | subtitle | value | mono | title
    tones: list[str] | None = None,
    language: str = "ko",
    count: int = 5,
    commercial_use: bool = True,
    video_use: bool = True,
    web_embedding: bool = False,
    timeout: int = 60,
) -> dict:
    """fontagent recommend-use-case 호출.

    반환: {results: [...], request: {...}, ...} 또는 {error: "..."}.
    """
    if not is_available():
        return {"error": "fontagent unavailable", "results": []}
    cmd = [
        "fontagent", "--root", str(fontagent_root()), "recommend-use-case",
        "--medium", medium,
        "--surface", surface,
        "--role", role,
        "--language", language,
        "--count", str(count),
    ]
    if tones:
        for t in tones:
            cmd += ["--tone", t]
    if commercial_use:
        cmd.append("--commercial-use")
    if video_use:
        cmd.append("--video-use")
    if web_embedding:
        cmd.append("--web-embedding")
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if out.returncode != 0:
        return {"error": out.stderr.strip(), "results": []}
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid JSON from fontagent", "raw": out.stdout, "results": []}
