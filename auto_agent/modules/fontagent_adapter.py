"""
fontagent_adapter.py
---------------------
auto_kairos_v3 ↔ fontagent 연결 어댑터.

fontagent는 auto_kairos_v3 전체 디자인 토큰의 폰트 종류 위임을 받습니다.
CreativeScene, 자막, chartagent viz 컴포넌트 모두 이 어댑터를 통해 폰트를 받습니다.

아키텍처:
    design_tokens (색상 + 크기) ← artstyle 단일 소스
    fontagent (폰트 선택 + 설치) → DesignPreset.fonts 흡수
                    ↓
            DesignPreset (마스터)
                    ↓
    CreativeScene / 자막 / chartagent viz 컴포넌트

사용 예:
    from auto_agent.modules.fontagent_adapter import (
        recommend_fonts_for_video,
        fonts_to_design_preset,
    )
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

# fontagent 프로젝트 루트
FONTAGENT_ROOT = Path("/Users/jleavens_macmini/Projects/fontagent")

# mood → fontagent tone 매핑
_MOOD_TO_TONE: dict[str, str] = {
    "urgent":        "urgent",
    "dramatic":      "dramatic",
    "informative":   "analytical",
    "contemplative": "contemplative",
    "somber":        "somber",
    "suspense":      "mysterious",
    "triumphant":    "triumphant",
}

# 기본 폰트 fallback (fontagent 없을 때)
_DEFAULT_FONTS = {
    "title": {
        "family": "Pretendard",
        "fallback": "Apple SD Gothic Neo, sans-serif",
        "files": [],
    },
    "body": {
        "family": "Pretendard",
        "fallback": "Apple SD Gothic Neo, sans-serif",
        "files": [],
    },
}


# ---------------------------------------------------------------------------
# 핵심 함수: 무드 기반 폰트 추천
# ---------------------------------------------------------------------------

def recommend_fonts_for_video(
    mood: str = "informative",
    language: str = "ko",
    title_count: int = 1,
    body_count: int = 1,
) -> dict[str, Any]:
    """
    fontagent CLI `recommend-use-case`를 호출하여 영상용 폰트를 추천받습니다.

    Parameters
    ----------
    mood         : scene mood (urgent, dramatic, informative, ...)
    language     : 언어 코드 (기본: ko)
    title_count  : 제목 후보 수
    body_count   : 본문 후보 수

    Returns
    -------
    {
      "title": {"font_id": "...", "family": "...", "source_site": "..."},
      "body":  {"font_id": "...", "family": "...", "source_site": "..."},
    }
    또는 fontagent 실패 시 None 반환
    """
    tone = _MOOD_TO_TONE.get(mood, "analytical")

    title_result = _recommend_use_case(
        medium="video",
        surface="headline",
        role="title",
        tone=tone,
        language=language,
        count=title_count,
    )
    body_result = _recommend_use_case(
        medium="video",
        surface="body",
        role="body",
        tone=tone,
        language=language,
        count=body_count,
    )

    title_font = _pick_best(title_result)
    body_font = _pick_best(body_result)

    if not title_font and not body_font:
        return {}

    result: dict[str, Any] = {}
    if title_font:
        result["title"] = title_font
    if body_font:
        result["body"] = body_font

    return result


def fonts_to_design_preset(
    font_recommendation: dict[str, Any],
    fallback: str = "Apple SD Gothic Neo, sans-serif",
) -> dict[str, Any]:
    """
    recommend_fonts_for_video() 결과를 DesignPreset.fonts 형식으로 변환합니다.

    Parameters
    ----------
    font_recommendation : recommend_fonts_for_video() 반환값
    fallback            : CSS fallback 폰트 문자열

    Returns
    -------
    DesignPreset.fonts 형식 dict:
        {
          "body":  {"family": "Pretendard", "fallback": "...", "files": []},
          "title": {"family": "카페24 슈퍼매직", "fallback": "...", "files": []},
        }
    """
    result: dict[str, Any] = {}

    for role in ("title", "body"):
        entry = font_recommendation.get(role)
        if entry:
            family = entry.get("family", "")
            if family:
                result[role] = {
                    "family": family,
                    "fallback": fallback,
                    "files": [],
                }

    return result


def get_project_fonts(
    mood: str = "informative",
    language: str = "ko",
    fallback: str = "Apple SD Gothic Neo, sans-serif",
) -> dict[str, Any]:
    """
    mood 기반 폰트 추천 → DesignPreset.fonts 형식까지 한 번에 반환합니다.

    build_manifest.py에서 호출하는 메인 진입점입니다.

    Parameters
    ----------
    mood     : 프로젝트 대표 mood
    language : 언어 코드
    fallback : CSS fallback

    Returns
    -------
    DesignPreset.fonts 형식 dict (비어 있으면 fontagent 실패)
    """
    if not FONTAGENT_ROOT.exists():
        return {}

    try:
        rec = recommend_fonts_for_video(mood=mood, language=language)
        if not rec:
            return {}
        return fonts_to_design_preset(rec, fallback=fallback)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _recommend_use_case(
    medium: str,
    surface: str,
    role: str,
    tone: str,
    language: str,
    count: int,
) -> list[dict[str, Any]]:
    """fontagent CLI recommend-use-case 호출 → results 반환."""
    cmd = [
        "python3", "-m", "fontagent.cli",
        "--root", str(FONTAGENT_ROOT),
        "recommend-use-case",
        "--medium", medium,
        "--surface", surface,
        "--role", role,
        "--tone", tone,
        "--language", language,
        "--count", str(count),
        "--commercial-use",
        "--video-use",
        "--detail", "compact",
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(FONTAGENT_ROOT),
            timeout=30,
        )
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        return data.get("results", [])
    except Exception:
        return []


def _pick_best(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """
    추천 결과에서 최적 폰트를 선택합니다.

    우선 조건:
    1. verification_status == "installed"
    2. automation_profile.status == "ready"
    3. score 내림차순
    """
    installed = [
        r for r in results
        if r.get("verification_status") == "installed"
        and (r.get("automation_profile") or {}).get("status") == "ready"
    ]
    if not installed:
        installed = results

    if not installed:
        return None

    best = max(installed, key=lambda r: r.get("score", 0))
    return {
        "font_id": best.get("font_id", ""),
        "family": best.get("family", ""),
        "source_site": best.get("source_site", ""),
        "score": best.get("score", 0),
    }
