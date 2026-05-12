"""
build_art_style.py — artstyle JSON 로더 + PD override 적용.

기존 auto_agent/data/artstyle/styles/<style_id>.json을 로드하고,
theme과 voice_id 오버라이드를 적용하는 thin wrapper.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


# ─── Public API ───────────────────────────────────────────────────────────────

def build_art_style(
    style_id: str = "quirky_cartoon",
    theme: str | None = None,
    voice_id: str | None = None,
    *,
    artstyle_dir: Path | None = None,
) -> dict[str, Any]:
    """
    art_style.json 빌더 — 기존 artstyle/styles/<id>.json 로드 + PD override 적용.

    Args:
        style_id: 스타일 ID (예: "quirky_cartoon", "semoji")
        theme: 테마 오버라이드 ("dark" 또는 "light", 기본값: None = 기존 값 유지)
        voice_id: 음성 ID 오버라이드 (기본값: None = 기존 값 유지)
        artstyle_dir: artstyle/styles/ 디렉토리 경로 (기본값: 모듈 위치 기반 계산)

    Returns:
        완전한 art_style dict (design_tokens, voice, creative 등 포함)

    Raises:
        FileNotFoundError: style_id.json 파일이 없으면 발생
    """
    # 디폴트 디렉토리 경로 계산 (모듈 위치 기반)
    if artstyle_dir is None:
        # 이 파일: auto_agent/modules/v4_bridge/build_art_style.py
        # 목표: auto_agent/data/artstyle/styles/
        module_dir = Path(__file__).parent  # .../v4_bridge
        artstyle_dir = module_dir.parent.parent / "data" / "artstyle" / "styles"

    style_path = artstyle_dir / f"{style_id}.json"

    if not style_path.exists():
        raise FileNotFoundError(
            f"Art style not found: {style_path}\n"
            f"Available styles should be in: {artstyle_dir}"
        )

    # JSON 로드
    with open(style_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    # PD override: theme
    if theme is not None:
        if "design_tokens" in result:
            result["design_tokens"]["baseTheme"] = theme

    # PD override: voice_id
    if voice_id is not None:
        if "voice" in result:
            result["voice"]["voice_id"] = voice_id

    return result
