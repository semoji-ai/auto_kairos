import pytest, json
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SAMPLE_PLAN = {
    "series_id": "lg_brand_encyclopedia",
    "title": "당신이 몰랐던 LG의 역사",
    "channel": "세모지",
    "writing_style": "semoji",
    "total_episodes": 8,
    "series_angle": "창업~분리는 인물 중심, 구광모 이후는 산업 전환 중심",
    "series_hook": "왜 삼성과 함께 시작했지만 다른 길을 걸었는가",
    "key_entities": ["구인회", "구자경", "구본무", "구광모", "LG전자", "LG화학"],
    "episodes": [
        {
            "episode_number": 1,
            "title": "포마드 장사꾼이 그룹을 만들다",
            "scope_start": "구인회 출생 (1907년)",
            "scope_end": "락희화학 설립 (1947년)",
            "core_question": "LG는 어떻게 시작됐는가",
            "key_events": ["구인회 포목점", "락희화학 설립", "플라스틱 빗"],
            "key_persons": ["구인회", "허만정"],
            "handoff_to_next": "금성사 설립로 가전 진출 시작",
            "do_not_cover": ["금성사 이후 가전 사업"]
        }
    ]
}

def test_validate_series_plan_valid():
    from auto_agent.modules.series_planner_module import validate_series_plan
    errors = validate_series_plan(SAMPLE_PLAN)
    assert errors == []

def test_validate_series_plan_missing_required():
    from auto_agent.modules.series_planner_module import validate_series_plan
    bad = {k: v for k, v in SAMPLE_PLAN.items() if k != "series_angle"}
    errors = validate_series_plan(bad)
    assert any("series_angle" in e for e in errors)

def test_generate_episode_brief():
    from auto_agent.modules.series_planner_module import episode_to_editorial_brief
    ep = SAMPLE_PLAN["episodes"][0]
    brief = episode_to_editorial_brief(ep, SAMPLE_PLAN)
    assert brief["core_question"] == ep["core_question"]
    assert brief["entity_slug"] == "lg"
    assert brief["section_slug"] == "역사_1편"
    assert brief["tone_goal"] in ("정보형", "해설형", "인물중심형")

def test_episode_brief_do_not_cover_reflected():
    from auto_agent.modules.series_planner_module import episode_to_editorial_brief
    ep = SAMPLE_PLAN["episodes"][0]
    brief = episode_to_editorial_brief(ep, SAMPLE_PLAN)
    assert any("금성사" in a for a in brief["excluded_angles"])
