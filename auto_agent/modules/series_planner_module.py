"""
series_planner_module.py
------------------------
장편 시리즈 사전 기획 모듈.

주요 기능:
1. validate_series_plan()   — series_plan.json 스키마 검증
2. episode_to_editorial_brief() — 편별 episode_brief.json 생성
3. generate_series_plan_from_topic() — Claude API로 시리즈 기획안 초안 생성
4. save_series_plan() / load_series_plan() — 파일 I/O
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


REQUIRED_SERIES_FIELDS = [
    "series_id", "title", "channel", "writing_style",
    "total_episodes", "series_angle", "episodes",
]
REQUIRED_EPISODE_FIELDS = [
    "episode_number", "title", "scope_start", "scope_end",
    "core_question", "key_events", "key_persons",
]


def validate_series_plan(plan: dict[str, Any]) -> list[str]:
    """series_plan dict 검증. 오류 메시지 리스트 반환 (비어 있으면 유효)."""
    errors: list[str] = []
    for field in REQUIRED_SERIES_FIELDS:
        if field not in plan:
            errors.append(f"필수 필드 누락: {field}")

    episodes = plan.get("episodes", [])
    if not isinstance(episodes, list) or len(episodes) == 0:
        errors.append("episodes 배열이 비어 있거나 잘못된 형식입니다.")
        return errors

    for i, ep in enumerate(episodes):
        for field in REQUIRED_EPISODE_FIELDS:
            if field not in ep:
                errors.append(f"episodes[{i}] 필수 필드 누락: {field}")

    return errors


def episode_to_editorial_brief(
    episode: dict[str, Any],
    series_plan: dict[str, Any],
) -> dict[str, Any]:
    """편 정보 + 시리즈 컨텍스트 → editorial_brief.json 형식 dict 변환."""
    ep_num = episode.get("episode_number", 1)
    series_id = series_plan.get("series_id", "series")

    # entity_slug: 시리즈 id에서 파생. lg_brand_encyclopedia → lg
    entity_slug = series_id.split("_")[0].lower()

    # section_slug: 역사_N편
    section_slug = f"역사_{ep_num}편"

    do_not_cover = episode.get("do_not_cover", [])
    excluded = list(do_not_cover)

    series_hook = series_plan.get("series_hook", "")

    brief: dict[str, Any] = {
        "core_question": episode["core_question"],
        "real_topic": episode["title"],
        "entity_slug": entity_slug,
        "section_slug": section_slug,
        "hook_angle": f"{episode['scope_start']}에서 {episode['scope_end']}까지",
        "supporting_case": series_hook,
        "excluded_angles": excluded,
        "audience_takeaway": episode["core_question"],
        "tone_goal": "인물중심형" if ep_num <= 4 else "정보형",
        "success_criteria": [
            f"시청자가 {episode['scope_start']} ~ {episode['scope_end']} 흐름을 이해한다",
            "다음 편이 궁금해진다",
        ],
        "_series": {
            "series_id": series_plan.get("series_id"),
            "episode_number": ep_num,
            "total_episodes": series_plan.get("total_episodes"),
            "scope_start": episode["scope_start"],
            "scope_end": episode["scope_end"],
            "key_events": episode.get("key_events", []),
            "key_persons": episode.get("key_persons", []),
            "handoff_to_next": episode.get("handoff_to_next", ""),
            "do_not_cover": do_not_cover,
        },
    }
    return brief


def generate_series_plan_from_topic(
    topic: str,
    channel: str = "세모지",
    writing_style: str = "semoji",
    total_episodes: int = 8,
) -> dict[str, Any]:
    """Claude API로 topic → series_plan 초안 생성.

    API 키 없거나 실패하면 최소 뼈대 dict 반환.
    """
    try:
        import anthropic
    except ImportError:
        return _default_series_plan(topic, channel, writing_style, total_episodes)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _default_series_plan(topic, channel, writing_style, total_episodes)

    prompt = f"""다음 유튜브 채널의 장편 브랜드백과 시리즈를 기획하세요.

채널: {channel}
주제: {topic}
총 편수: {total_episodes}편
문체 스타일: {writing_style}

요구사항:
- 창업/초기 역사는 인물 중심 서사로
- 현재 사업 구조는 산업 전환 중심으로
- 각 편은 10~15분 분량 (씬 12~20개)
- 편 간 중복 없이 scope_start/scope_end를 명확히 구분
- handoff_to_next로 다음 편으로 자연스럽게 연결

반드시 아래 JSON 형식으로만 응답 (설명 없이 JSON만):
{{
  "series_id": "slug_형식",
  "title": "시리즈 전체 제목",
  "channel": "{channel}",
  "writing_style": "{writing_style}",
  "total_episodes": {total_episodes},
  "series_angle": "전체 서사 방향 한 줄",
  "series_hook": "시리즈 전체를 관통하는 핵심 긴장감",
  "key_entities": ["핵심 인물/기업 목록"],
  "episodes": [
    {{
      "episode_number": 1,
      "title": "편 제목",
      "scope_start": "시작 시점",
      "scope_end": "끝 시점",
      "core_question": "이 편의 핵심 질문",
      "key_events": ["핵심 사건1", "핵심 사건2"],
      "key_persons": ["인물1"],
      "handoff_to_next": "다음 편 브릿지",
      "do_not_cover": ["다른 편에서 다룰 내용"]
    }}
  ]
}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"[series_planner] Claude API 오류: {e} — 기본 플랜 반환", flush=True)
        return _default_series_plan(topic, channel, writing_style, total_episodes)


def _default_series_plan(
    topic: str,
    channel: str,
    writing_style: str,
    total_episodes: int,
) -> dict[str, Any]:
    """API 없을 때 최소 뼈대 플랜."""
    return {
        "series_id": topic.lower().replace(" ", "_"),
        "title": topic,
        "channel": channel,
        "writing_style": writing_style,
        "total_episodes": total_episodes,
        "series_angle": "(수동 입력 필요)",
        "series_hook": "(수동 입력 필요)",
        "key_entities": [],
        "episodes": [],
    }


def save_series_plan(plan: dict[str, Any], path: Path) -> None:
    """series_plan.json 저장."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def load_series_plan(path: Path) -> dict[str, Any]:
    """series_plan.json 로드."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
