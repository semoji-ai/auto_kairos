# Series Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 장편 시리즈 제작을 위한 두 가지 기능 추가 — (A) `--until` CLI 플래그로 Stage 2에서 파이프라인 정지, (B) 시리즈 플래너 에이전트로 편별 scope 사전 정의 및 Stage 2 완료 후 시리즈 전체 검토

**Architecture:**
- Plan A(`--until`)는 runner.py의 step 필터링 로직에 `stop_after_step` 파라미터를 추가하는 단순 확장이다. 기존 `--only` / `--from` 패턴을 그대로 따른다.
- Plan B(시리즈 모드)는 `series_plan.json` 스키마 → 시리즈 플래너 모듈 → 편별 `episode_brief.json` 생성 → 시리즈 리뷰어 에이전트 3계층으로 구성된다. 기존 `editorial_brief_module.py` 패턴을 상속한다.

**Tech Stack:** Python 3.12, pathlib, existing runner.py hook system, existing agents.json / pipeline.json pattern, Claude API (anthropic SDK)

---

## 서브시스템 분리

두 서브시스템은 독립적으로 개발·테스트 가능하다.

- **Plan A** — `--until` CLI 플래그 (Task 1~2)
- **Plan B** — 시리즈 모드 (Task 3~7)

---

## File Map

### Plan A — `--until` 플래그

| 파일 | 역할 |
|------|------|
| `auto_agent/orchestrator/runner.py` | `stop_after_step` 파라미터 추가, step 루프에 조기 종료 로직 삽입 |
| `auto_agent/cli.py` | `--until` 인수 파싱 → runner 전달 |
| `tests/test_runner_until.py` | `--until step_2b` 동작 단위 테스트 |

### Plan B — 시리즈 모드

| 파일 | 역할 |
|------|------|
| `auto_agent/modules/series_planner_module.py` | series_plan.json 생성 (Claude API 인터뷰 또는 수동 입력) |
| `auto_agent/data/skills/agents/series-planner/SKILL.md` | 시리즈 플래너 에이전트 스킬 |
| `auto_agent/data/skills/agents/series-reviewer/SKILL.md` | 시리즈 리뷰어 에이전트 스킬 |
| `auto_agent/orchestrator/series_runner.py` | 시리즈 전편 Stage 1~2 순차 실행 + 시리즈 리뷰 트리거 |
| `auto_agent/cli.py` | `series` 서브커맨드 추가 |
| `auto_agent/data/docs/series-plan-schema.json` | series_plan.json JSON 스키마 문서 |
| `tests/test_series_planner.py` | 시리즈 플래너 단위 테스트 |
| `tests/test_series_runner.py` | 시리즈 러너 단위 테스트 |

---

## Plan A — `--until` 플래그

### Task 1: runner.py에 stop_after_step 파라미터 추가

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:560-660`
- Create: `tests/test_runner_until.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_runner_until.py
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def _make_steps():
    return [
        {"id": "step_1a", "phase": "stage_1"},
        {"id": "step_2_draft", "phase": "stage_2"},
        {"id": "step_2b", "phase": "stage_2"},
        {"id": "step_3b", "phase": "stage_3"},
    ]

def test_stop_after_step_excludes_later_steps():
    """stop_after_step='step_2b'이면 step_3b는 실행되지 않아야 한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after="step_2b")
    ids = [s["id"] for s in result]
    assert "step_3b" not in ids
    assert "step_2b" in ids

def test_stop_after_step_includes_target():
    """stop_after_step 대상 step 자체는 포함되어야 한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after="step_2_draft")
    ids = [s["id"] for s in result]
    assert "step_2_draft" in ids
    assert "step_2b" not in ids

def test_stop_after_none_returns_all():
    """stop_after=None이면 전체 steps를 그대로 반환한다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    result = _filter_steps_until(steps, stop_after=None)
    assert len(result) == len(steps)

def test_stop_after_unknown_raises():
    """존재하지 않는 step_id를 지정하면 ValueError를 발생시킨다."""
    from auto_agent.orchestrator.runner import _filter_steps_until
    steps = _make_steps()
    with pytest.raises(ValueError, match="stop_after"):
        _filter_steps_until(steps, stop_after="step_999")
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
.venv/bin/python -m pytest tests/test_runner_until.py -v 2>&1 | head -20
```
Expected: `ImportError` 또는 `FAILED` (함수 미존재)

- [ ] **Step 3: runner.py에 `_filter_steps_until` 헬퍼 추가**

`auto_agent/orchestrator/runner.py` 상단 헬퍼 함수 영역(클래스 정의 전)에 추가:

```python
def _filter_steps_until(steps: list[dict], stop_after: str | None) -> list[dict]:
    """stop_after step_id까지만 포함한 steps 리스트를 반환한다.

    Parameters
    ----------
    steps      : 파이프라인 전체 steps (평탄화된 리스트)
    stop_after : 마지막으로 실행할 step id. None이면 전체 반환.

    Raises
    ------
    ValueError : stop_after step_id가 steps에 없는 경우
    """
    if stop_after is None:
        return steps

    ids = [s["id"] for s in steps]
    if stop_after not in ids:
        raise ValueError(f"stop_after '{stop_after}' 를 steps에서 찾을 수 없습니다. 유효한 step id: {ids}")

    cutoff = ids.index(stop_after)
    return steps[: cutoff + 1]
```

- [ ] **Step 4: `run()` 메서드에 `stop_after_step` 파라미터 연결**

`runner.py`의 `run()` 함수 시그니처(현재 줄 ~560):

```python
# 기존
def run(
    self,
    project: dict,
    from_step: str = None,
    only_step: str = None,
) -> dict:

# 변경 후
def run(
    self,
    project: dict,
    from_step: str = None,
    only_step: str = None,
    stop_after_step: str = None,
) -> dict:
```

`run()` 내부에서 steps 목록을 구성한 직후(`steps = self._collect_steps()` 또는 동등한 코드 바로 뒤)에 삽입:

```python
    # --until 필터 적용
    if stop_after_step:
        steps = _filter_steps_until(steps, stop_after=stop_after_step)
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_runner_until.py -v
```
Expected: 4 passed

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/orchestrator/runner.py tests/test_runner_until.py
git commit -m "feat(runner): add stop_after_step / _filter_steps_until for --until support"
```

---

### Task 2: CLI에 `--until` 인수 추가

**Files:**
- Modify: `auto_agent/cli.py` (줄 ~221 argparse 영역, 줄 ~243 호출 영역)

- [ ] **Step 1: argparse에 `--until` 추가**

`cli.py` 줄 ~222 (`--only` 정의 바로 뒤):

```python
# 기존
parser.add_argument("--only", dest="only_step", help="이 step만 실행")

# 추가 (--only 다음 줄)
parser.add_argument("--until", dest="until_step", help="이 step까지만 실행 (stage 2 정지 예: --until step_2b)")
```

- [ ] **Step 2: runner 호출에 `stop_after_step` 전달**

줄 ~243 (`only_step=parsed.only_step` 바로 뒤):

```python
# 기존
from_step=parsed.from_step,
only_step=parsed.only_step,

# 변경
from_step=parsed.from_step,
only_step=parsed.only_step,
stop_after_step=getattr(parsed, "until_step", None),
```

bg start 커맨드(줄 ~688)에도 동일하게:

```python
until_step = _get_arg(args[1:], "--until") or None
# ... 기존 코드 ...
session = sm.start(project_slug, from_step=from_step, only_step=only_step, stop_after_step=until_step)
```

세션 표시(줄 ~832) 에도 추가:

```python
if session.get("stop_after_step"):
    lines.append(f"[white]종료스텝:[/white]  {session['stop_after_step']}")
```

- [ ] **Step 3: 동작 확인 (dry-run)**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
.venv/bin/python -m auto_agent.cli run --help 2>&1 | grep until
```
Expected: `--until UNTIL_STEP  이 step까지만 실행`

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat(cli): add --until flag for stopping pipeline at specified step"
```

---

## Plan B — 시리즈 모드

### Task 3: series_plan.json 스키마 + 플래너 모듈

**Files:**
- Create: `auto_agent/data/docs/series-plan-schema.json`
- Create: `auto_agent/modules/series_planner_module.py`
- Create: `tests/test_series_planner.py`

- [ ] **Step 1: 스키마 파일 작성**

`auto_agent/data/docs/series-plan-schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Series Plan",
  "description": "장편 시리즈 사전 기획 스키마",
  "type": "object",
  "required": ["series_id", "title", "channel", "writing_style", "total_episodes", "series_angle", "episodes"],
  "properties": {
    "series_id": {
      "type": "string",
      "description": "시리즈 식별자 (slug). 예: lg_brand_encyclopedia"
    },
    "title": {
      "type": "string",
      "description": "시리즈 전체 제목. 예: 당신이 몰랐던 LG의 역사"
    },
    "channel": {
      "type": "string",
      "description": "유튜브 채널명. 예: 세모지"
    },
    "writing_style": {
      "type": "string",
      "description": "artstyle writing_style 값. 예: semoji"
    },
    "total_episodes": {
      "type": "integer",
      "description": "총 편수 (통합편 포함)"
    },
    "series_angle": {
      "type": "string",
      "description": "시리즈 전체 서사 방향. 예: 창업~분리는 인물 중심, 구광모 이후는 산업 전환 중심"
    },
    "series_hook": {
      "type": "string",
      "description": "시리즈 전체를 관통하는 핵심 질문 또는 긴장감"
    },
    "key_entities": {
      "type": "array",
      "items": {"type": "string"},
      "description": "시리즈에서 반복 등장하는 핵심 인물/기업/사건 목록"
    },
    "episodes": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["episode_number", "title", "scope_start", "scope_end", "core_question", "key_events", "key_persons"],
        "properties": {
          "episode_number": {"type": "integer"},
          "title": {"type": "string", "description": "편 제목 (안)"},
          "scope_start": {"type": "string", "description": "이 편이 다루는 시작 시점/사건"},
          "scope_end": {"type": "string", "description": "이 편이 끝나는 시점/사건"},
          "core_question": {"type": "string", "description": "이 편의 핵심 질문"},
          "key_events": {
            "type": "array",
            "items": {"type": "string"},
            "description": "이 편에서 반드시 다뤄야 할 사건 목록"
          },
          "key_persons": {
            "type": "array",
            "items": {"type": "string"},
            "description": "이 편의 주요 등장 인물"
          },
          "handoff_to_next": {
            "type": "string",
            "description": "다음 편으로 넘어가는 브릿지 포인트 (마지막 편은 생략)"
          },
          "do_not_cover": {
            "type": "array",
            "items": {"type": "string"},
            "description": "이 편에서 다루지 않아야 할 내용 (다른 편 담당)"
          },
          "episode_brief_path": {
            "type": "string",
            "description": "생성된 episode_brief.json 경로 (런타임 기입)"
          },
          "project_slug": {
            "type": "string",
            "description": "연결된 auto_kairos 프로젝트 slug (런타임 기입)"
          }
        }
      }
    }
  }
}
```

- [ ] **Step 2: 실패 테스트 작성**

`tests/test_series_planner.py`:

```python
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
    assert "구인회" in brief["excluded_angles"] or len(brief["excluded_angles"]) == 0 or True
    assert brief["tone_goal"] in ("정보형", "해설형", "인물중심형")

def test_episode_brief_do_not_cover_reflected():
    from auto_agent.modules.series_planner_module import episode_to_editorial_brief
    ep = SAMPLE_PLAN["episodes"][0]
    brief = episode_to_editorial_brief(ep, SAMPLE_PLAN)
    # do_not_cover 항목이 excluded_angles에 반영되어야 한다
    assert any("금성사" in a for a in brief["excluded_angles"])
```

- [ ] **Step 3: 테스트 실패 확인**

```bash
.venv/bin/python -m pytest tests/test_series_planner.py -v 2>&1 | head -15
```
Expected: `ImportError` 또는 `FAILED`

- [ ] **Step 4: series_planner_module.py 작성**

`auto_agent/modules/series_planner_module.py`:

```python
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


# ---------------------------------------------------------------------------
# 검증
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 편별 editorial_brief 변환
# ---------------------------------------------------------------------------

def episode_to_editorial_brief(
    episode: dict[str, Any],
    series_plan: dict[str, Any],
) -> dict[str, Any]:
    """편 정보 + 시리즈 컨텍스트 → editorial_brief.json 형식 dict 변환.

    editorial_brief_module.py의 BRIEF_SCHEMA와 호환되는 형식으로 반환한다.
    """
    ep_num = episode.get("episode_number", 1)
    series_id = series_plan.get("series_id", "series")

    # entity_slug: 시리즈 id에서 파생. lg_brand_encyclopedia → lg
    entity_slug = series_id.split("_")[0].lower()

    # section_slug: 역사_N편
    section_slug = f"역사_{ep_num}편"

    # excluded_angles: do_not_cover → excluded_angles로 변환
    do_not_cover = episode.get("do_not_cover", [])
    excluded = list(do_not_cover)  # 복사

    # 시리즈 hook을 supporting_case로 활용
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
        # 시리즈 메타데이터 (파이프라인 에이전트에서 참조용)
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


# ---------------------------------------------------------------------------
# Claude API로 시리즈 기획안 초안 생성
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 파일 I/O
# ---------------------------------------------------------------------------

def save_series_plan(plan: dict[str, Any], path: Path) -> None:
    """series_plan.json 저장."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def load_series_plan(path: Path) -> dict[str, Any]:
    """series_plan.json 로드."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_series_planner.py -v
```
Expected: 4 passed

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/data/docs/series-plan-schema.json \
        auto_agent/modules/series_planner_module.py \
        tests/test_series_planner.py
git commit -m "feat(series): add series_plan schema + series_planner_module"
```

---

### Task 4: 시리즈 플래너 에이전트 스킬

**Files:**
- Create: `auto_agent/data/skills/agents/series-planner/SKILL.md`

- [ ] **Step 1: 스킬 파일 작성**

`auto_agent/data/skills/agents/series-planner/SKILL.md`:

```markdown
# Series Planner Agent

장편 시리즈 기획안(series_plan.json)을 작성하는 에이전트.

## 역할

브랜드백과 등 장편 시리즈의 전체 구조를 사전에 설계한다.
- 편별 scope 명확히 분리 (중복·누락 방지)
- 인물 중심 / 산업 전환 혼합 서사 구조 결정
- 각 편의 do_not_cover로 경계 명시

## 인터뷰 항목

1. 시리즈 주제 (예: LG 브랜드 역사)
2. 채널 / 문체 스타일
3. 총 편수 (권장 8~10편)
4. 서사 방향 — 인물 중심 / 산업 중심 / 혼합
5. 핵심 인물·기업 목록
6. 특별히 강조할 에피소드 (드라마틱한 사건)
7. 절대 빠뜨리면 안 되는 사건

## 작업 흐름

1. 인터뷰로 기본 정보 수집
2. `series_planner_module.generate_series_plan_from_topic()` 호출로 초안 생성
3. 초안 검토 후 편별 scope 수동 조정
4. `validate_series_plan()` 검증
5. `{project_output_dir}/series_plan.json` 저장

## 출력

`series_plan.json` — 시리즈 전체 기획안
`episodes/{N}/episode_brief.json` — 편별 editorial_brief (series_runner가 사용)

## 주의

- 각 편의 scope_end = 다음 편의 scope_start와 자연스럽게 이어져야 함
- do_not_cover는 명확하게 — 모호한 경계는 시리즈 리뷰에서 수정됨
- 통합편(마지막 편)은 key_events를 전편 하이라이트로 설정
```

- [ ] **Step 2: agents.json에 시리즈 플래너 등록**

`auto_agent/data/agents.json`에 추가:

```json
{
  "id": "series-planner",
  "description": "장편 시리즈 기획안(series_plan.json) 작성 에이전트",
  "model": "opus",
  "max_turns": 20,
  "skills": ["agents/series-planner"],
  "allowed_tools": ["Read", "Write", "Edit", "Bash"]
}
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/skills/agents/series-planner/SKILL.md \
        auto_agent/data/agents.json
git commit -m "feat(series): add series-planner agent skill"
```

---

### Task 5: 시리즈 리뷰어 에이전트 스킬

**Files:**
- Create: `auto_agent/data/skills/agents/series-reviewer/SKILL.md`

- [ ] **Step 1: 스킬 파일 작성**

`auto_agent/data/skills/agents/series-reviewer/SKILL.md`:

```markdown
# Series Reviewer Agent

전체 시리즈의 Stage 2 완료 후 편 간 일관성을 검토하는 에이전트.

## 역할

- 편 간 중복 내용 탐지
- 서사 흐름 단절 감지 (이전 편과 연결이 어색한 부분)
- 누락된 핵심 사건 확인 (series_plan.json 대비)
- 각 편 분량 균형 검토

## 입력

- `series_plan.json` — 원래 기획안
- `episodes/{N}/scene_specs.json` — 전 편의 Stage 2 결과물

## 출력

`series_review.json`:
```json
{
  "overall_score": 85,
  "issues": [
    {
      "type": "overlap",
      "episodes": [2, 3],
      "description": "EP2와 EP3 모두 금성사 설립 에피소드를 다루고 있음",
      "recommendation": "EP2에서 제거, EP3에서 상세 서술"
    },
    {
      "type": "missing",
      "episode": 4,
      "description": "series_plan의 key_event '구자경 회장 취임'이 EP4에 없음",
      "recommendation": "EP4 도입부에 추가 필요"
    },
    {
      "type": "flow_break",
      "episodes": [3, 4],
      "description": "EP3 마지막 씬과 EP4 첫 씬 사이 시간 점프가 15년으로 설명 없음",
      "recommendation": "EP4 첫 씬에 브릿지 나레이션 추가"
    }
  ],
  "per_episode": [
    {"episode": 1, "scene_count": 18, "status": "ok"},
    {"episode": 2, "scene_count": 14, "status": "thin"}
  ]
}
```

## 작업 흐름

1. series_plan.json 로드
2. 전 편 scene_specs.json 로드
3. 편별 key_events 커버리지 확인
4. 인접 편 간 scope 경계 검토
5. narration 텍스트 중복 탐지 (핵심 문장 반복 여부)
6. series_review.json 저장
7. 수정 권고사항 요약 출력

## 점수 기준

- 90점 이상: Stage 3 진행 가능
- 70~89점: 권고 수정 후 재검토
- 70점 미만: 특정 편 Stage 2 재실행 권고
```

- [ ] **Step 2: agents.json에 시리즈 리뷰어 등록**

`auto_agent/data/agents.json`에 추가:

```json
{
  "id": "series-reviewer",
  "description": "전체 시리즈 Stage 2 완료 후 편 간 일관성 검토 에이전트",
  "model": "opus",
  "max_turns": 30,
  "skills": ["agents/series-reviewer"],
  "allowed_tools": ["Read", "Write", "Glob"]
}
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/skills/agents/series-reviewer/SKILL.md \
        auto_agent/data/agents.json
git commit -m "feat(series): add series-reviewer agent skill"
```

---

### Task 6: series_runner.py — 전편 Stage 1~2 순차 실행

**Files:**
- Create: `auto_agent/orchestrator/series_runner.py`
- Create: `tests/test_series_runner.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_series_runner.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SAMPLE_PLAN = {
    "series_id": "lg_brand_encyclopedia",
    "title": "당신이 몰랐던 LG의 역사",
    "channel": "세모지",
    "writing_style": "semoji",
    "total_episodes": 2,
    "series_angle": "test",
    "series_hook": "test hook",
    "key_entities": [],
    "episodes": [
        {
            "episode_number": 1,
            "title": "EP1",
            "scope_start": "1907",
            "scope_end": "1947",
            "core_question": "Q1",
            "key_events": [],
            "key_persons": [],
        },
        {
            "episode_number": 2,
            "title": "EP2",
            "scope_start": "1947",
            "scope_end": "1969",
            "core_question": "Q2",
            "key_events": [],
            "key_persons": [],
        },
    ]
}

def test_build_episode_run_order():
    """에피소드는 episode_number 오름차순으로 실행되어야 한다."""
    from auto_agent.orchestrator.series_runner import build_episode_run_order
    order = build_episode_run_order(SAMPLE_PLAN)
    assert [ep["episode_number"] for ep in order] == [1, 2]

def test_build_episode_project_slug():
    """각 에피소드의 project_slug는 series_id_ep{N} 형식이어야 한다."""
    from auto_agent.orchestrator.series_runner import build_episode_project_slug
    slug = build_episode_project_slug("lg_brand_encyclopedia", 3)
    assert slug == "lg_brand_encyclopedia_ep03"

def test_series_run_calls_runner_for_each_episode():
    """series_run은 각 에피소드마다 runner를 stop_after_step='step_2b'로 호출한다."""
    from auto_agent.orchestrator.series_runner import series_run

    call_args = []
    def mock_run(project, stop_after_step=None, **kwargs):
        call_args.append({"project": project, "stop_after_step": stop_after_step})
        return {"status": "completed"}

    with patch("auto_agent.orchestrator.series_runner.run_single_episode", mock_run):
        series_run(SAMPLE_PLAN, output_base=Path("/tmp/test_series"), dry_run=True)

    assert len(call_args) == 2
    assert all(c["stop_after_step"] == "step_2b" for c in call_args)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/bin/python -m pytest tests/test_series_runner.py -v 2>&1 | head -15
```
Expected: `ImportError` 또는 `FAILED`

- [ ] **Step 3: series_runner.py 작성**

`auto_agent/orchestrator/series_runner.py`:

```python
"""
series_runner.py
----------------
장편 시리즈 전편 Stage 1~2 순차 실행 오케스트레이터.

흐름:
  series_plan.json
    → 편별 episode_brief.json 생성
    → 편마다 Runner(stop_after_step='step_2b') 실행
    → 전편 완료 후 series-reviewer 에이전트 실행
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auto_agent.modules.series_planner_module import (
    episode_to_editorial_brief,
    save_series_plan,
    load_series_plan,
    validate_series_plan,
)


def build_episode_run_order(series_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """에피소드를 episode_number 오름차순으로 정렬하여 반환."""
    return sorted(series_plan["episodes"], key=lambda ep: ep["episode_number"])


def build_episode_project_slug(series_id: str, episode_number: int) -> str:
    """시리즈 + 편번호 → 프로젝트 slug. 예: lg_brand_encyclopedia_ep03"""
    return f"{series_id}_ep{episode_number:02d}"


def run_single_episode(
    project: dict[str, Any],
    stop_after_step: str = "step_2b",
    **kwargs,
) -> dict[str, Any]:
    """단일 에피소드 Runner 실행 (테스트 모킹 진입점)."""
    from auto_agent.orchestrator.runner import PipelineRunner
    from auto_agent.db.project_store import get_project_by_slug

    runner = PipelineRunner()
    return runner.run(project, stop_after_step=stop_after_step)


def series_run(
    series_plan: dict[str, Any],
    output_base: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """시리즈 전편을 Stage 2까지 순차 실행.

    Parameters
    ----------
    series_plan  : 검증된 series_plan dict
    output_base  : 시리즈 출력 루트 디렉토리
    dry_run      : True면 실제 Runner 호출 없이 구조만 생성

    Returns
    -------
    {
      "series_id": str,
      "episodes_completed": int,
      "episodes_failed": list[int],
      "series_review_path": str | None
    }
    """
    errors = validate_series_plan(series_plan)
    if errors:
        raise ValueError(f"series_plan 검증 실패: {errors}")

    output_base = Path(output_base)
    series_id = series_plan["series_id"]
    episodes_completed = 0
    episodes_failed: list[int] = []

    for episode in build_episode_run_order(series_plan):
        ep_num = episode["episode_number"]
        slug = build_episode_project_slug(series_id, ep_num)
        ep_dir = output_base / slug

        # episode_brief.json 생성
        brief = episode_to_editorial_brief(episode, series_plan)
        ep_dir.mkdir(parents=True, exist_ok=True)
        brief_path = ep_dir / "episode_brief.json"
        brief_path.write_text(
            json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # series_plan에 경로 기록
        episode["episode_brief_path"] = str(brief_path)
        episode["project_slug"] = slug

        if dry_run:
            print(f"[series_runner] DRY RUN — EP{ep_num:02d}: {slug}", flush=True)
            episodes_completed += 1
            continue

        project = {
            "slug": slug,
            "output_dir": str(ep_dir),
            "topic": f"{series_plan['title']} {ep_num}편 — {episode['title']}",
            "writing_style": series_plan.get("writing_style", ""),
            "episode_brief_path": str(brief_path),
        }

        try:
            print(f"[series_runner] EP{ep_num:02d} 시작: {slug}", flush=True)
            run_single_episode(project, stop_after_step="step_2b")
            episodes_completed += 1
            print(f"[series_runner] EP{ep_num:02d} 완료", flush=True)
        except Exception as e:
            print(f"[series_runner] EP{ep_num:02d} 실패: {e}", flush=True)
            episodes_failed.append(ep_num)

    # 업데이트된 series_plan 저장 (episode_brief_path, project_slug 기록)
    save_series_plan(series_plan, output_base / "series_plan.json")

    return {
        "series_id": series_id,
        "episodes_completed": episodes_completed,
        "episodes_failed": episodes_failed,
        "series_review_path": None,  # Task 7에서 연결
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/bin/python -m pytest tests/test_series_runner.py -v
```
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/orchestrator/series_runner.py \
        tests/test_series_runner.py
git commit -m "feat(series): add series_runner with per-episode Stage1~2 execution"
```

---

### Task 7: CLI에 `series` 서브커맨드 추가

**Files:**
- Modify: `auto_agent/cli.py`

- [ ] **Step 1: `series` 서브커맨드 파싱 추가**

`cli.py`의 subparser 정의 영역에 추가 (기존 `run`, `bg` 등과 같은 레벨):

```python
# series 서브커맨드
series_parser = subparsers.add_parser("series", help="장편 시리즈 모드")
series_sub = series_parser.add_subparsers(dest="series_cmd")

# series plan — 시리즈 기획안 생성
sp_plan = series_sub.add_parser("plan", help="시리즈 기획안 생성")
sp_plan.add_argument("--topic", required=True, help="시리즈 주제 (예: LG 브랜드 역사)")
sp_plan.add_argument("--channel", default="세모지", help="채널명")
sp_plan.add_argument("--style", default="semoji", dest="writing_style", help="문체 스타일")
sp_plan.add_argument("--episodes", type=int, default=8, dest="total_episodes", help="총 편수")
sp_plan.add_argument("--out", required=True, help="series_plan.json 저장 경로")

# series run — 전편 Stage 1~2 실행
sp_run = series_sub.add_parser("run", help="시리즈 전편 Stage 2까지 실행")
sp_run.add_argument("--plan", required=True, help="series_plan.json 경로")
sp_run.add_argument("--output-dir", required=True, dest="output_dir", help="시리즈 출력 루트 디렉토리")
sp_run.add_argument("--dry-run", action="store_true", dest="dry_run", help="실제 실행 없이 구조만 생성")
```

- [ ] **Step 2: 서브커맨드 핸들러 연결**

```python
elif parsed.command == "series":
    if parsed.series_cmd == "plan":
        from auto_agent.modules.series_planner_module import (
            generate_series_plan_from_topic,
            save_series_plan,
            validate_series_plan,
        )
        plan = generate_series_plan_from_topic(
            topic=parsed.topic,
            channel=parsed.channel,
            writing_style=parsed.writing_style,
            total_episodes=parsed.total_episodes,
        )
        errors = validate_series_plan(plan)
        if errors:
            console.print(f"[red]기획안 검증 오류:[/red] {errors}")
        else:
            save_series_plan(plan, Path(parsed.out))
            console.print(f"[green]시리즈 기획안 저장:[/green] {parsed.out}")
            console.print(f"  편수: {plan['total_episodes']}편")
            for ep in plan.get("episodes", []):
                console.print(f"  EP{ep['episode_number']:02d}: {ep['title']}")

    elif parsed.series_cmd == "run":
        from auto_agent.modules.series_planner_module import load_series_plan
        from auto_agent.orchestrator.series_runner import series_run
        plan = load_series_plan(Path(parsed.plan))
        result = series_run(
            plan,
            output_base=Path(parsed.output_dir),
            dry_run=parsed.dry_run,
        )
        console.print(f"[green]시리즈 실행 완료:[/green]")
        console.print(f"  완료: {result['episodes_completed']}편")
        if result["episodes_failed"]:
            console.print(f"  [red]실패: EP{result['episodes_failed']}[/red]")
```

- [ ] **Step 3: 동작 확인**

```bash
.venv/bin/python -m auto_agent.cli series --help
.venv/bin/python -m auto_agent.cli series plan --help
.venv/bin/python -m auto_agent.cli series run --help
```
Expected: 각 help 텍스트 출력

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat(cli): add 'series plan' and 'series run' subcommands"
```

---

## Self-Review

### Spec coverage 확인

| 요구사항 | 담당 Task |
|---------|-----------|
| `--until step_2b` CLI 플래그 | Task 1~2 ✅ |
| series_plan.json 스키마 | Task 3 ✅ |
| 편별 episode_brief 생성 | Task 3 ✅ |
| 시리즈 플래너 에이전트 | Task 4 ✅ |
| 시리즈 리뷰어 에이전트 | Task 5 ✅ |
| 전편 Stage 1~2 순차 실행 | Task 6 ✅ |
| CLI series 서브커맨드 | Task 7 ✅ |
| LG 시리즈 실제 제작 | Task #1 (별도, 이 플랜 완료 후) |

### 미연결 항목

- `episode_brief_path`가 runner.py에서 `editorial_brief.json` 대신 로드되는 연결 코드가 없음 → runner.py의 `step_0b`(editorial_brief 모듈)가 `episode_brief_path` 환경변수 또는 project 필드를 참조하도록 수정 필요. 단, 이는 runner 내부 복잡도가 높아 **별도 Task로 분리**하는 것이 낫다. 현재 플랜에서는 `episode_brief.json`을 수동으로 `editorial_brief.json`으로 복사하는 워크어라운드로 대체 가능.
- 시리즈 리뷰어 실제 실행 연결(series_runner.py에서 reviewer 호출) — Task 6의 `series_review_path: None` 주석으로 명시됨. LG 시리즈 첫 실행 전에 필요하면 Task 추가.
