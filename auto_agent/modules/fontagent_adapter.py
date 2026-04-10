"""
fontagent_adapter.py
---------------------
auto_kairos_v3 ↔ fontagent 연결 어댑터.

fontagent는 범용 typography service로 유지한다.
auto_kairos_v3 프로젝트 문맥 해석은 전부 이 adapter가 담당한다.

아키텍처:
    project_dir (art_style.json + scene_specs.json)
            ↓
    resolve_fontagent_context()  ← 프로젝트 문맥 파싱
            ↓
    infer_fontagent_use_case()   ← 스타일 → use_case + tones 결정
            ↓
    recommend_role_font()        ← role별 CLI 호출 (title / subtitle / body)
            ↓
    fonts_to_design_preset()     ← DesignPreset.fonts 형식으로 변환
            ↓
    CreativeScene / 자막 / chartagent viz 컴포넌트

사용 예:
    from auto_agent.modules.fontagent_adapter import get_project_fonts
    fonts = get_project_fonts(project_dir)   # project_dir 방식 (권장)
    fonts = get_project_fonts(mood="dramatic")  # 하위 호환
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 환경변수 우선, 없으면 ~/Projects/fontagent 기본값
FONTAGENT_ROOT = Path(os.environ.get("FONTAGENT_ROOT", Path.home() / "Projects" / "fontagent"))

# ──────────────────────────────────────────────────────────────────────────────
# V3 아트스타일 → fontagent use_case + tones 매핑 테이블
# 형식: style_id → (primary_tone, [tones list])
# ──────────────────────────────────────────────────────────────────────────────
_STYLE_TO_TONES: dict[str, tuple[str, list[str]]] = {
    # 세모지 — 심플 플랫, 교육 채널
    "semoji":          ("knowledge", ["knowledge", "clean"]),
    # 이로미즘 — 개성적, 약간 quirky
    "iromism":         ("quirky",    ["quirky", "knowledge"]),
    # 낙서 만화 — 유머러스, playful
    "quirky_cartoon":  ("quirky",    ["quirky", "playful"]),
    # 레고 — 블록 편집 스타일
    "lego":            ("playful",   ["playful", "clean"]),
    # 스틱맨 — 귀엽고 단순
    "stickman_cute":   ("quirky",    ["quirky", "playful"]),
    # 다큐 / 에디토리얼 — 클린 정보
    "documentary":     ("knowledge", ["knowledge", "clean"]),
    "editorial":       ("analytical",["editorial", "clean"]),
    "clean":           ("knowledge", ["knowledge", "clean"]),
}

# mood → tone fallback (art_style 없을 때)
_MOOD_TO_TONE: dict[str, str] = {
    "urgent":        "urgent",
    "dramatic":      "dramatic",
    "informative":   "analytical",
    "contemplative": "contemplative",
    "somber":        "somber",
    "suspense":      "mysterious",
    "triumphant":    "triumphant",
}

# role → (surface, medium)
_ROLE_SURFACE: dict[str, tuple[str, str]] = {
    "title":    ("scene_overlay", "video"),
    "subtitle": ("subtitle_track", "video"),
    "body":     ("body_copy",    "video"),
}

# ──────────────────────────────────────────────────────────────────────────────
# 핵심 공개 API
# ──────────────────────────────────────────────────────────────────────────────

def get_project_fonts(
    project_dir: "str | Path | None" = None,
    mood: str = "informative",
    language: str = "ko",
    fallback: str = "Apple SD Gothic Neo, sans-serif",
) -> dict[str, Any]:
    """
    프로젝트 폰트를 추천하여 DesignPreset.fonts 형식으로 반환합니다.

    Parameters
    ----------
    project_dir : 프로젝트 출력 디렉토리 (art_style.json + scene_specs.json 위치)
                  None이면 mood 파라미터로 폴백
    mood        : art_style 없을 때 사용하는 기본 mood
    language    : 언어 코드
    fallback    : CSS fallback 폰트

    Returns
    -------
    DesignPreset.fonts 형식:
        {"title": {"family": "...", "fallback": "...", "files": []},
         "subtitle": {...}, "body": {...}}
    빈 dict이면 fontagent 미사용 — 호출부가 기본 폰트 사용
    """
    if not FONTAGENT_ROOT.exists():
        logger.debug("fontagent 루트 없음 — 기본 폰트 사용: %s", FONTAGENT_ROOT)
        return {}

    vault_dir = FONTAGENT_ROOT / "vault"
    if not vault_dir.exists() or not any(vault_dir.iterdir()):
        logger.debug("fontagent vault 비어있음 — 폰트 추천 생략")
        return {}

    try:
        ctx = resolve_fontagent_context(project_dir, mood=mood, language=language)
        result: dict[str, Any] = {}
        for role in ("title", "subtitle", "body"):
            font = recommend_role_font(role, ctx)
            if font:
                result[role] = {
                    "family": font["family"],
                    "fallback": fallback,
                    "files": [],
                }
        return result
    except Exception as e:
        logger.warning("fontagent 폰트 추천 실패 (기본 폰트 사용): %s", e)
        return {}


def recommend_fonts_for_video(
    mood: str = "informative",
    language: str = "ko",
    title_count: int = 1,
    body_count: int = 1,
) -> dict[str, Any]:
    """
    하위 호환 API. mood 기반으로 title/body 폰트를 추천합니다.

    Returns
    -------
    {"title": {...}, "body": {...}} 또는 빈 dict
    """
    ctx = resolve_fontagent_context(None, mood=mood, language=language)
    result: dict[str, Any] = {}
    title_font = recommend_role_font("title", ctx)
    body_font = recommend_role_font("body", ctx)
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
    recommend_fonts_for_video() / recommend_role_font() 결과를
    DesignPreset.fonts 형식으로 변환합니다.
    """
    result: dict[str, Any] = {}
    for role in ("title", "subtitle", "body"):
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


# ──────────────────────────────────────────────────────────────────────────────
# 컨텍스트 분석 함수
# ──────────────────────────────────────────────────────────────────────────────

def resolve_fontagent_context(
    project_dir: "str | Path | None",
    mood: str = "informative",
    language: str = "ko",
) -> dict[str, Any]:
    """
    프로젝트 디렉토리에서 art_style.json / scene_specs.json을 읽어
    fontagent 호출에 필요한 컨텍스트를 결정합니다.

    Returns
    -------
    {
      "style_id": "semoji",
      "primary_tone": "knowledge",
      "tones": ["knowledge", "clean"],
      "language": "ko",
      "medium": "video",
    }
    """
    ctx: dict[str, Any] = {
        "style_id": None,
        "primary_tone": _MOOD_TO_TONE.get(mood, "analytical"),
        "tones": [_MOOD_TO_TONE.get(mood, "analytical")],
        "language": language,
        "medium": "video",
    }

    if project_dir is None:
        return ctx

    project_dir = Path(project_dir)

    # 1. art_style.json에서 style_id 파악
    art_style_path = project_dir / "art_style.json"
    if art_style_path.exists():
        try:
            art_style = json.loads(art_style_path.read_text(encoding="utf-8"))
            style_id = art_style.get("id") or art_style.get("style_name", "")
            if style_id:
                ctx["style_id"] = style_id
        except Exception as e:
            logger.debug("art_style.json 파싱 실패: %s", e)

    # 2. scene_specs.json에서 대표 mood 파악 (art_style 없을 때 보조)
    if not ctx["style_id"]:
        scene_specs_path = project_dir / "scene_specs.json"
        if scene_specs_path.exists():
            try:
                specs = json.loads(scene_specs_path.read_text(encoding="utf-8"))
                scenes = specs.get("scenes", [])
                if scenes:
                    moods = [s.get("mood", "") for s in scenes if s.get("mood")]
                    if moods:
                        from collections import Counter
                        dominant = Counter(moods).most_common(1)[0][0]
                        ctx["primary_tone"] = _MOOD_TO_TONE.get(dominant, "analytical")
                        ctx["tones"] = [ctx["primary_tone"]]
            except Exception as e:
                logger.debug("scene_specs.json 파싱 실패: %s", e)

    # 3. style_id → use_case + tones 추론
    ctx = infer_fontagent_use_case(ctx)
    return ctx


def infer_fontagent_use_case(ctx: dict[str, Any]) -> dict[str, Any]:
    """
    컨텍스트의 style_id로 use_case + tones를 결정합니다.
    style_id가 없으면 현재 tones 유지.
    """
    style_id = ctx.get("style_id") or ""
    if style_id in _STYLE_TO_TONES:
        primary_tone, tones = _STYLE_TO_TONES[style_id]
        ctx["primary_tone"] = primary_tone
        ctx["tones"] = tones
    elif style_id:
        # 매핑에 없는 신규 스타일 — style_id 일부로 추론
        lower = style_id.lower()
        if any(k in lower for k in ("quirky", "cartoon", "cute", "playful", "fun")):
            ctx["primary_tone"] = "quirky"
            ctx["tones"] = ["quirky", "playful"]
        elif any(k in lower for k in ("docu", "news", "report", "editorial")):
            ctx["primary_tone"] = "analytical"
            ctx["tones"] = ["analytical", "clean"]
        # 그 외 → 기존 tones 유지
    return ctx


def recommend_role_font(role: str, ctx: dict[str, Any]) -> dict[str, Any] | None:
    """
    role (title / subtitle / body) 에 맞는 폰트를 fontagent CLI로 추천받습니다.

    Returns
    -------
    {"font_id": "...", "family": "...", "source_site": "...", "score": N}
    또는 None (실패 시)
    """
    surface, medium = _ROLE_SURFACE.get(role, ("body_copy", "video"))
    primary_tone = ctx.get("primary_tone", "analytical")
    language = ctx.get("language", "ko")

    results = _recommend_use_case(
        medium=medium,
        surface=surface,
        role=role,
        tone=primary_tone,
        language=language,
        count=1,
    )
    return _pick_best(results)


# ──────────────────────────────────────────────────────────────────────────────
# 내부 헬퍼
# ──────────────────────────────────────────────────────────────────────────────

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
        sys.executable, "-m", "fontagent.cli",
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
            logger.warning(
                "fontagent recommend-use-case 실패 (returncode=%d) — %s",
                result.returncode,
                result.stderr[:200] if result.stderr else "(stderr 없음)",
            )
            return []
        data = json.loads(result.stdout)
        return data.get("results", [])
    except json.JSONDecodeError as e:
        logger.warning("fontagent 응답 JSON 파싱 실패: %s", e)
        return []
    except subprocess.TimeoutExpired:
        logger.warning("fontagent CLI 타임아웃 (30s) — vault 준비 안 됐을 가능성")
        return []
    except FileNotFoundError:
        logger.warning("fontagent CLI 실행 불가 — python 환경 확인 필요: %s", cmd[0])
        return []
    except Exception as e:
        logger.warning("fontagent CLI 예외: %s", e)
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
