"""
content_planner_module.py
--------------------------
파이프라인과 독립적으로 작동하는 기획안 생성 모듈.

기존 editorial_brief_module.generate_brief_from_topic()보다
must_cover, key_persons 필드를 포함한 풍부한 초안을 생성한다.

출력: editorial_brief.json (step_0b가 존재 시 스킵하는 파일과 동일)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REQUIRED_BRIEF_FIELDS = [
    "core_question", "real_topic", "entity_slug", "section_slug",
    "hook_angle", "excluded_angles", "tone_goal", "success_criteria",
    "must_cover", "key_persons",
]


def validate_brief(brief: dict[str, Any]) -> list[str]:
    """editorial_brief dict 검증. 오류 메시지 리스트 반환 (비어 있으면 유효)."""
    errors: list[str] = []
    for field in REQUIRED_BRIEF_FIELDS:
        if field not in brief:
            errors.append(f"필수 필드 누락: {field}")
    return errors


def save_brief(
    brief: dict[str, Any],
    output_dir: Path,
    overwrite: bool = False,
) -> Path:
    """editorial_brief.json 저장.

    Parameters
    ----------
    brief       : editorial_brief dict
    output_dir  : 저장할 디렉토리 (프로젝트 output_dir)
    overwrite   : True면 기존 파일 덮어쓰기. False(기본)면 FileExistsError

    Returns
    -------
    저장된 파일 Path
    """
    output_dir = Path(output_dir)
    path = output_dir / "editorial_brief.json"
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"editorial_brief.json 이미 존재: {path}\n"
            "--overwrite 플래그를 사용하면 덮어씁니다."
        )
    # 검증 경고 (차단하지 않음 — 수동 편집용 부분 저장 허용)
    errors = validate_brief(brief)
    if errors:
        print(f"[content_planner] 경고: 불완전한 brief 저장 — {errors}", flush=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate_planner_brief(
    topic: str,
    writing_style: str = "",
    channel: str = "",
) -> dict[str, Any]:
    """Claude API로 topic → 풍부한 editorial_brief 초안 생성.

    API 키 없거나 실패하면 기본 뼈대 반환.
    """
    try:
        import anthropic
    except ImportError:
        print("[content_planner] anthropic 패키지 없음 — 기본 초안 반환", flush=True)
        return _default_planner_brief(topic)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[content_planner] ANTHROPIC_API_KEY 없음 — 기본 초안 반환", flush=True)
        return _default_planner_brief(topic)

    style_hint = ""
    if writing_style == "semoji" or channel in ("세모지", "세상의모든지식"):
        style_hint = "\n채널 특성: 세모지 — 친근한 정보 전달, 명확한 구조, 데이터 시각화 적극 활용"
    elif writing_style == "iromism":
        style_hint = "\n채널 특성: 이로미즘 — 충격적 후킹, 날카로운 해설, 드라마틱 전개"

    prompt = f"""다음 유튜브 영상의 기획안을 작성하세요.

주제: {topic}{style_hint}

아래 원칙을 지켜서 JSON으로만 응답하세요 (설명 없이 JSON만):

원칙:
- real_topic: 후킹 사례가 아닌 실제 설명 대상
- entity_slug: 핵심 엔티티 한글 slug, 공백 없음 언더스코어 허용
- section_slug: 이 콘텐츠의 각도
- must_cover: 반드시 다뤄야 할 구체적 사건/인물/장면 목록
- key_persons: 핵심 등장 인물 목록
- excluded_angles: 이 영상이 빠져들면 안 되는 방향

{{
  "core_question": "시청자가 이 영상을 보고 나서 답을 얻었다고 느껴야 할 핵심 질문",
  "real_topic": "진짜 설명 대상",
  "entity_slug": "핵심엔티티_슬러그",
  "section_slug": "각도_슬러그",
  "hook_angle": "처음 5~15초를 여는 도입 장치 (구체적 사례/사실)",
  "supporting_case": "본론을 뒷받침하는 사례/대조점",
  "excluded_angles": ["이 영상이 빠져들면 안 되는 방향1", "방향2"],
  "audience_takeaway": "시청자가 보고 나서 가져가야 할 핵심 인식 (한 문장)",
  "tone_goal": "정보형|향수형|인물중심형|해설형|충격형 중 하나",
  "must_cover": ["반드시 다뤄야 할 사건/장면1", "사건2", "사건3"],
  "key_persons": ["핵심 인물1", "인물2"],
  "success_criteria": ["성공 기준1", "성공 기준2"]
}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # 마크다운 코드 블록 제거
        if "```" in raw:
            lines = raw.split("\n")
            # 첫 줄(```json 또는 ```) 과 마지막 줄(```) 제거
            start = 1 if lines[0].strip().startswith("```") else 0
            end = -1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[start:end]).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[content_planner] Claude API 오류: {e} — 기본 초안 반환", flush=True)
        return _default_planner_brief(topic)


def _default_planner_brief(topic: str) -> dict[str, Any]:
    """API 없을 때 최소 뼈대 초안."""
    import re
    topic = topic.strip()
    if not topic:
        topic = "미지정주제"
    entity = re.sub(r"(의|을|를|이|가|은|는|와|과|에서|에|로|으로)\s.*$", "", topic).strip() or topic
    # 특수문자 제거 후 슬러그 생성
    entity_slug = re.sub(r"[^\w가-힣]", "_", entity.lower()).strip("_") or "unknown"
    entity_slug = re.sub(r"_+", "_", entity_slug)
    parts = topic.split()
    raw_section = parts[-1].lower() if len(parts) > 1 else "overview"
    section_slug = re.sub(r"[^\w가-힣]", "_", raw_section).strip("_") or "overview"
    return {
        "core_question": f"{topic}의 핵심 질문 (수동 입력 필요)",
        "real_topic": topic,
        "entity_slug": entity_slug,
        "section_slug": section_slug,
        "hook_angle": "(수동 입력 필요)",
        "supporting_case": "(수동 입력 필요)",
        "excluded_angles": ["(수동 입력 필요)"],
        "audience_takeaway": "(수동 입력 필요)",
        "tone_goal": "정보형",
        "must_cover": ["(수동 입력 필요)"],
        "key_persons": [],
        "success_criteria": ["시청자가 핵심 개념을 이해한다"],
    }
