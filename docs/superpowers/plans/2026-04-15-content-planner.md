# Content Planner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 파이프라인과 독립적으로 작동하는 `auto-agent plan` CLI 커맨드와 `content_planner_module.py`를 구축해, 사용자가 제작 전 기획의도를 명확히 담은 `editorial_brief.json`을 생성할 수 있게 한다.

**Architecture:**
- `content_planner_module.py`는 기존 `editorial_brief_module.py`보다 풍부한 필드(`must_cover`, `key_persons`)를 포함하는 기획 전용 초안을 생성한다. 기존 `generate_brief_from_topic()`은 건드리지 않고 새 함수만 추가한다.
- `auto-agent plan` CLI는 `pm.resolve_project(slug)` → `project["output_dir"]`로 저장 경로를 결정한다. `editorial_brief.json`이 이미 있으면 `--overwrite` 없이는 덮어쓰지 않는다.
- `content-planner` 에이전트 스킬은 Claude CLI로도 인터랙티브하게 실행할 수 있다.

**Tech Stack:** Python 3.12, anthropic SDK, pathlib, existing `pm.resolve_project()` pattern from `auto_agent/cli.py`

---

## 서브시스템

두 서브시스템은 독립적으로 개발·테스트 가능하다.

- **Plan A** — `content_planner_module.py` + 테스트 (Task 1)
- **Plan B** — `content-planner` 에이전트 스킬 (Task 2)
- **Plan C** — `auto-agent plan` CLI 서브커맨드 (Task 3)

---

## File Map

| 파일 | 역할 |
|------|------|
| `auto_agent/modules/content_planner_module.py` | 기획 초안 생성·검증·저장 |
| `auto_agent/data/skills/agents/content-planner/SKILL.md` | 기획 에이전트 인터뷰 스킬 |
| `auto_agent/data/agents.json` | content-planner 에이전트 등록 |
| `auto_agent/cli.py` | `plan` 서브커맨드 추가 |
| `tests/test_content_planner.py` | 단위 테스트 |

---

## Plan A — content_planner_module.py

### Task 1: content_planner_module.py 구현

**Files:**
- Create: `auto_agent/modules/content_planner_module.py`
- Create: `tests/test_content_planner.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_content_planner.py`:

```python
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

REQUIRED_FIELDS = [
    "core_question", "real_topic", "entity_slug", "section_slug",
    "hook_angle", "excluded_angles", "tone_goal", "success_criteria",
    "must_cover", "key_persons",
]

def test_validate_brief_valid():
    from auto_agent.modules.content_planner_module import validate_brief
    brief = {f: "x" if isinstance("x", str) else [] for f in REQUIRED_FIELDS}
    brief["excluded_angles"] = ["a"]
    brief["success_criteria"] = ["b"]
    brief["must_cover"] = ["c"]
    brief["key_persons"] = ["d"]
    errors = validate_brief(brief)
    assert errors == []

def test_validate_brief_missing_field():
    from auto_agent.modules.content_planner_module import validate_brief
    brief = {"core_question": "Q"}  # 나머지 필드 없음
    errors = validate_brief(brief)
    assert any("real_topic" in e for e in errors)
    assert any("must_cover" in e for e in errors)

def test_save_brief_creates_file(tmp_path):
    from auto_agent.modules.content_planner_module import save_brief
    brief = {"core_question": "Q", "real_topic": "T"}
    path = save_brief(brief, tmp_path)
    assert path.exists()
    import json
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["core_question"] == "Q"

def test_save_brief_no_overwrite(tmp_path):
    from auto_agent.modules.content_planner_module import save_brief
    brief = {"core_question": "Q"}
    save_brief(brief, tmp_path)
    with pytest.raises(FileExistsError):
        save_brief({"core_question": "Q2"}, tmp_path, overwrite=False)

def test_save_brief_overwrite(tmp_path):
    from auto_agent.modules.content_planner_module import save_brief
    import json
    save_brief({"core_question": "Q1"}, tmp_path)
    save_brief({"core_question": "Q2"}, tmp_path, overwrite=True)
    data = json.loads((tmp_path / "editorial_brief.json").read_text())
    assert data["core_question"] == "Q2"

def test_default_brief_has_must_cover():
    from auto_agent.modules.content_planner_module import _default_planner_brief
    brief = _default_planner_brief("포켓몬 30주년")
    assert "must_cover" in brief
    assert isinstance(brief["must_cover"], list)
    assert "key_persons" in brief
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
.venv/bin/python -m pytest tests/test_content_planner.py -v 2>&1 | head -15
```
Expected: `ImportError` 또는 `FAILED`

- [ ] **Step 3: content_planner_module.py 작성**

`auto_agent/modules/content_planner_module.py`:

```python
"""
content_planner_module.py
--------------------------
파이프라인 외부에서 독립 실행하는 기획안 생성 모듈.

기존 editorial_brief_module.py의 generate_brief_from_topic()보다
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


# ---------------------------------------------------------------------------
# 검증
# ---------------------------------------------------------------------------

def validate_brief(brief: dict[str, Any]) -> list[str]:
    """editorial_brief dict 검증. 오류 메시지 리스트 반환 (비어 있으면 유효)."""
    errors: list[str] = []
    for field in REQUIRED_BRIEF_FIELDS:
        if field not in brief:
            errors.append(f"필수 필드 누락: {field}")
    return errors


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------

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
    output_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Claude API 초안 생성
# ---------------------------------------------------------------------------

def generate_planner_brief(
    topic: str,
    writing_style: str = "",
    channel: str = "",
) -> dict[str, Any]:
    """Claude API로 topic → 풍부한 editorial_brief 초안 생성.

    기존 editorial_brief_module.generate_brief_from_topic()보다
    must_cover, key_persons 필드를 추가로 포함한다.
    API 키 없거나 실패하면 기본 뼈대 반환.
    """
    try:
        import anthropic
    except ImportError:
        return _default_planner_brief(topic)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
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
- real_topic: 후킹 사례가 아닌 실제 설명 대상 (예: "SK하이닉스 성과급 논란" → real_topic은 "한국 대기업 연봉 구조")
- entity_slug: 핵심 엔티티 한글 slug, 공백 없음 언더스코어 허용 (예: "포켓몬스터")
- section_slug: 이 콘텐츠의 각도 (예: "30주년_생존전략")
- must_cover: 이 영상에서 반드시 다뤄야 할 사건/인물/장면 목록 (구체적으로)
- key_persons: 핵심 등장 인물 목록
- excluded_angles: 이 영상이 빠져들면 안 되는 방향 (주제 이탈 방지)

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
        if "```" in raw:
            import re
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if m:
                raw = m.group(1)
        return json.loads(raw)
    except Exception as e:
        print(f"[content_planner] Claude API 오류: {e} — 기본 초안 반환", flush=True)
        return _default_planner_brief(topic)


def _default_planner_brief(topic: str) -> dict[str, Any]:
    """API 없을 때 최소 뼈대 초안."""
    import re
    entity = re.sub(r"(의|을|를|이|가|은|는|와|과|에서|에|로|으로)\s.*$", "", topic).strip()
    entity_slug = re.sub(r"\s+", "_", entity.lower())
    parts = topic.split()
    section_slug = parts[-1].lower() if len(parts) > 1 else "overview"
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
.venv/bin/python -m pytest tests/test_content_planner.py -v
```
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/content_planner_module.py tests/test_content_planner.py
git commit -m "feat(planner): add content_planner_module with must_cover/key_persons fields"
```

---

## Plan B — content-planner 에이전트 스킬

### Task 2: content-planner 에이전트 스킬 + agents.json

**Files:**
- Create: `auto_agent/data/skills/agents/content-planner/SKILL.md`
- Modify: `auto_agent/data/agents.json`

- [ ] **Step 1: SKILL.md 작성**

`auto_agent/data/skills/agents/content-planner/SKILL.md`:

```markdown
# Content Planner Agent

파이프라인과 독립적으로 작동하는 기획안 작성 에이전트.
`editorial_brief.json`을 생성해 auto_kairos 파이프라인에 전달한다.

## 역할

- 단편 영상의 기획 의도를 명확히 정의
- must_cover(반드시 다룰 사건), key_persons(핵심 인물), excluded_angles(제외 방향) 명시
- 생성된 brief는 `step_0b`가 스킵하므로 파이프라인이 그대로 사용

## 인터뷰 항목

1. **주제** — 영상 주제 한 줄 (예: 포켓몬스터 30주년 생존 전략)
2. **채널/스타일** — semoji / iromism / 기타
3. **핵심 질문** — "시청자가 이 영상을 보고 나서 답을 얻어야 할 질문"
4. **도입 각도** — 처음 15초를 어떤 사실/사례로 여는가
5. **반드시 다룰 사건** — must_cover 목록 (구체적으로 3~5개)
6. **핵심 인물** — key_persons 목록
7. **제외 방향** — excluded_angles (이 영상이 빠져들면 안 되는 방향)
8. **톤 목표** — 정보형 / 향수형 / 인물중심형 / 해설형
9. **성공 기준** — 이 영상이 잘 됐다고 판단하는 기준 2가지

## 작업 흐름

1. 인터뷰로 정보 수집 (모르는 항목은 Claude가 제안, 사용자 확인)
2. `content_planner_module.generate_planner_brief()` 호출로 초안 생성
3. 초안을 사용자에게 보여주고 수정 확인
4. `validate_brief()` 검증
5. `save_brief(brief, project_output_dir)` 저장

## 출력

프로젝트 output_dir의 `editorial_brief.json`

## 주의

- 이미 `editorial_brief.json`이 있으면 `--overwrite` 없이 덮어쓰지 않음
- `must_cover`는 막연한 키워드가 아닌 구체적 사건/장면으로 기술
  - 나쁜 예: "포켓몬의 역사"
  - 좋은 예: "1996년 2월 27일 초판 발매 당일 게임 프리크 적자 위기"
- `excluded_angles`는 "이 영상이 게임 공략 영상이 되는 것을 막는다" 수준으로 명확히
```

- [ ] **Step 2: agents.json에 content-planner 등록**

`auto_agent/data/agents.json`을 읽고, 기존 에이전트 배열에 추가:

```json
{
  "id": "content-planner",
  "description": "파이프라인 외부에서 기획안(editorial_brief.json)을 작성하는 에이전트",
  "model": "opus",
  "max_turns": 25,
  "skills": ["agents/content-planner"],
  "allowed_tools": ["Read", "Write", "Edit", "Bash"]
}
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/skills/agents/content-planner/SKILL.md \
        auto_agent/data/agents.json
git commit -m "feat(planner): add content-planner agent skill"
```

---

## Plan C — CLI `plan` 서브커맨드

### Task 3: `auto-agent plan` CLI 서브커맨드

**Files:**
- Modify: `auto_agent/cli.py`

- [ ] **Step 1: cli.py 읽기**

`auto_agent/cli.py`를 읽어서 확인:
1. `COMMANDS` dict 또는 subparser 등록 위치
2. `pm.resolve_project(slug)` 호출 패턴 (줄 ~235, ~1689 참고)
3. `project["output_dir"]`로 경로 추출하는 패턴

- [ ] **Step 2: `cmd_plan` 함수 작성**

`cli.py`에 `cmd_series` 함수 근처에 추가:

```python
def cmd_plan(args):
    """auto-agent plan — 파이프라인 외부 기획안 생성"""
    import argparse
    parser = argparse.ArgumentParser(prog="auto-agent plan")
    parser.add_argument("--topic", required=True, help="영상 주제")
    parser.add_argument("--project", required=True, help="프로젝트 slug")
    parser.add_argument("--style", default="", dest="writing_style", help="문체 스타일 (예: semoji)")
    parser.add_argument("--channel", default="", help="채널명")
    parser.add_argument("--overwrite", action="store_true", help="기존 editorial_brief.json 덮어쓰기")
    parsed = parser.parse_args(args)

    from auto_agent.modules.content_planner_module import (
        generate_planner_brief,
        validate_brief,
        save_brief,
    )

    # 프로젝트 output_dir 조회
    project = pm.resolve_project(parsed.project)
    if not project:
        console.print(f"[red]프로젝트를 찾을 수 없습니다: {parsed.project}[/red]")
        return

    project_dir = Path(project["output_dir"])

    console.print(f"[blue]기획안 생성 중...[/blue] 주제: {parsed.topic}")
    brief = generate_planner_brief(
        topic=parsed.topic,
        writing_style=parsed.writing_style,
        channel=parsed.channel,
    )

    errors = validate_brief(brief)
    if errors:
        console.print(f"[yellow]검증 경고:[/yellow] {errors}")

    # 저장
    try:
        path = save_brief(brief, project_dir, overwrite=parsed.overwrite)
        console.print(f"[green]기획안 저장 완료:[/green] {path}")
        console.print(f"  core_question: {brief.get('core_question', '')}")
        console.print(f"  tone_goal: {brief.get('tone_goal', '')}")
        must_cover = brief.get("must_cover", [])
        if must_cover:
            console.print(f"  must_cover ({len(must_cover)}개):")
            for item in must_cover:
                console.print(f"    - {item}")
        console.print()
        console.print(f"[dim]다음 단계: auto-agent run --project {parsed.project}[/dim]")
    except FileExistsError as e:
        console.print(f"[red]{e}[/red]")
```

- [ ] **Step 3: COMMANDS dict에 `plan` 등록**

`COMMANDS` dict(또는 subparser add 영역)에 추가:

```python
"plan": cmd_plan,
```

- [ ] **Step 4: 동작 확인**

```bash
cd /Users/jleavens_macmini/Projects/auto_kairos_v3
.venv/bin/python -m auto_agent.cli plan --help
```
Expected: `--topic`, `--project`, `--style`, `--channel`, `--overwrite` 옵션 출력

```bash
.venv/bin/python -c "import auto_agent.cli; print('ok')"
```
Expected: `ok`

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat(cli): add 'plan' subcommand for standalone editorial brief generation"
```

---

## Self-Review

### Spec coverage

| 요구사항 | 담당 Task |
|---------|-----------|
| 파이프라인과 독립 실행 | Task 1 (모듈), Task 3 (CLI) ✅ |
| must_cover, key_persons 필드 | Task 1 ✅ |
| editorial_brief.json 생성 → step_0b 스킵 | Task 1 save_brief() ✅ |
| 기존 파일 덮어쓰기 방지 | Task 1 FileExistsError ✅ |
| 에이전트 인터뷰 모드 | Task 2 SKILL.md ✅ |
| `auto-agent plan` CLI | Task 3 ✅ |
| 기존 `auto-agent run`과 연결 | step_0b 스킵 메커니즘 (기존 코드 이미 지원) ✅ |

### 미연결 항목

- **시리즈와 통합 CLI 진입점**: 현재 시리즈 기획은 `auto-agent series plan`, 단편은 `auto-agent plan`으로 분리. 추후 `auto-agent plan series`로 통합 가능하지만 지금은 YAGNI.
- **인터랙티브 수정 루프**: CLI에서 초안을 보여주고 사용자가 필드를 수정하는 인터랙티브 편집은 이번 범위 밖. 생성 후 `editorial_brief.json`을 텍스트 에디터에서 직접 수정하는 것으로 대체.
