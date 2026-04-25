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
from datetime import date
from pathlib import Path
from typing import Any


def _today_context() -> str:
    """현재 날짜를 entry_trend 시의성 확보용 컨텍스트 문자열로 반환."""
    today = date.today()
    return (
        f"\n\n⚠️ **현재 날짜: {today.isoformat()} (오늘)**\n"
        f"- `narrative_arc.entry_trend`와 `hook_angle`은 반드시 **오늘 기준으로 시의성 있는** 트렌드/뉴스여야 합니다\n"
        f"- 훈련 데이터에 있던 과거 시점(예: 2024년 뉴스)을 '현재'로 제시하지 마세요\n"
        f"- 오늘 시점 최신 트렌드를 모를 경우, 해당 필드 status를 `needs_research`로 표시하고 "
        f"Stage 1 deepener가 실제 최신 뉴스로 교체하도록 위임하세요"
    )

REQUIRED_BRIEF_FIELDS = [
    "core_question", "real_topic", "entity_slug", "section_slug",
    "hook_angle", "supporting_case", "excluded_angles", "audience_takeaway",
    "tone_goal", "success_criteria", "must_cover", "key_persons",
]

# 5대 DNA 레버 (shared/brief-dna.md 기반) — v1부터 필수 작성
DNA_LEVER_FIELDS = [
    "narrative_arc",        # 3단 서사 (entry_trend/deep_knowledge/present_insight)
    "human_truth",          # 3요소 (success/failure/inner_conflict)
    "hidden_truth",         # 반전
    "present_connection",   # 현재 연결
    "evidence_anchors",     # 증거 앵커
]

# v{N} 간 변경 금지 — 심화 단계에서도 불변
LOCKED_FIELDS = (
    "core_question", "real_topic", "hook_angle",
    "excluded_angles", "tone_goal", "entity_slug", "section_slug",
)


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

    Notes
    -----
    output_dir가 존재하지 않으면 자동으로 생성된다 (parents=True).
    프로젝트 디렉토리가 아직 없는 경우에도 안전하게 저장된다.
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

주제: {topic}{style_hint}{_today_context()}

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


def save_brief_versioned(
    brief: dict[str, Any],
    output_dir: Path,
    version: str = "v1",
    overwrite: bool = False,
) -> Path:
    """editorial_brief.v{N}.json 저장 (버전 관리).

    editorial_brief.json도 latest pointer로 함께 저장 (하위 호환).
    """
    output_dir = Path(output_dir)
    path = output_dir / f"editorial_brief.{version}.json"
    legacy_path = output_dir / "editorial_brief.json"

    if path.exists() and not overwrite:
        raise FileExistsError(
            f"editorial_brief.{version}.json 이미 존재: {path}\n"
            "overwrite=True로 덮어쓸 수 있습니다."
        )
    errors = validate_brief(brief)
    if errors:
        print(f"[content_planner] 경고: 불완전한 brief 저장 — {errors}", flush=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    brief.setdefault("_version", version)
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")

    # legacy editorial_brief.json 도 동시 기록 (하위 호환 + runner의 기본 로더)
    legacy_path.write_text(
        json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    return path


def generate_auto_brief(
    topic: str,
    writing_style: str = "",
    channel: str = "",
) -> dict[str, Any]:
    """Auto 모드: 각 DNA 레버에 후보 3개 생성 → 자가 평가 → 최고점 선택.

    Claude API 사용 가능할 때만 진짜 auto 동작, 없으면 _default_auto_brief.
    """
    try:
        import anthropic
    except ImportError:
        return _default_auto_brief(topic)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _default_auto_brief(topic)

    style_hint = ""
    if writing_style == "semoji" or channel in ("세모지", "세상의모든지식"):
        style_hint = (
            "\n채널 특성: 세모지 — writing-style-semoji 15-1~15-5 공식 준수 "
            "(입체적 인물, 현재와의 연결, 이면의 진실, 데이터 기반, 3단 서사)"
        )
    elif writing_style == "iromism":
        style_hint = "\n채널 특성: 이로미즘 — 충격적 후킹, 날카로운 해설, 드라마틱"

    prompt = f"""다음 유튜브 영상 주제에 대해 editorial_brief.v1.json을 생성하세요.

주제: {topic}{style_hint}{_today_context()}

## 단계

### Step 1: 주제 분석
- 표면 주제 vs 잠재 주제(real_topic) 분리
- 드리프트 위험 방향(excluded_angles) 파악

### Step 2: 각 필드에 대해 **후보 3개** 생성 후 자가 평가
- hook_angle: 서로 다른 관점 3개 (뉴스/일화/수치)
- hidden_truth: 서로 다른 반전 포인트 3개
- narrative_arc.entry_trend / deep_knowledge / present_insight: 각 3개
각 후보에 (구체성/반전성/DNA부합도) 3축 평가 후 최고점 선택.

### Step 3: 다음 JSON 형식으로 **최종 brief만 반환** (후보는 내부 검토만):

{{
  "core_question": "...",
  "real_topic": "...",
  "entity_slug": "...",
  "section_slug": "...",
  "hook_angle": "...",
  "supporting_case": "...",
  "excluded_angles": ["...", "..."],
  "audience_takeaway": "...",
  "tone_goal": "정보형|향수형|인물중심형|해설형|충격형",
  "must_cover": ["YYYY년 X사건", "..."],
  "key_persons": ["...", "..."],
  "success_criteria": ["...", "..."],
  "narrative_arc": {{
    "entry_trend": "현재 화제/트렌드 (구체적)",
    "deep_knowledge": "본문에서 파헤칠 심층 지식",
    "present_insight": "결론 — 과거가 오늘에 갖는 의미"
  }},
  "human_truth": {{
    "success": "구체적 성취",
    "failure": "구체적 실패 에피소드",
    "inner_conflict": "내면의 고뇌/갈등"
  }},
  "hidden_truth": "시청자 기존 인식을 깨뜨리는 반전 포인트 (구체 사실)",
  "present_connection": "과거→오늘 구체 연결",
  "evidence_anchors": [
    {{"claim": "...", "source_hint": "...", "status": "available|needs_research|risky"}}
  ]
}}

JSON만 반환. 설명/주석 없이.
"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        if "```" in raw:
            lines = raw.split("\n")
            start = 1 if lines[0].strip().startswith("```") else 0
            end = -1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[start:end]).strip()
        brief = json.loads(raw)
        brief["_generated_by"] = "auto"
        return brief
    except Exception as e:
        print(f"[content_planner auto] Claude API 오류: {e}", flush=True)
        return _default_auto_brief(topic)


def _default_auto_brief(topic: str) -> dict[str, Any]:
    """API 없을 때 5개 레버 포함된 최소 뼈대."""
    base = _default_planner_brief(topic)
    base.update({
        "narrative_arc": {
            "entry_trend": "(수동 입력 필요 — 현재 트렌드/화제)",
            "deep_knowledge": "(수동 입력 필요 — 심층 지식)",
            "present_insight": "(수동 입력 필요 — 현재 의미)",
        },
        "human_truth": {
            "success": "(수동 입력 필요)",
            "failure": "(수동 입력 필요)",
            "inner_conflict": "(수동 입력 필요)",
        },
        "hidden_truth": "(수동 입력 필요 — 반전 포인트)",
        "present_connection": "(수동 입력 필요 — 과거→오늘 연결)",
        "evidence_anchors": [],
        "_generated_by": "auto_fallback",
    })
    return base


def ratchet_brief_v1(
    project_dir: Path,
    topic: str,
    mode: str = "auto",
    writing_style: str = "",
    channel: str = "",
    max_rounds: int = 3,
    pass_threshold: int = 85,
) -> dict[str, Any]:
    """v1 brief 래칫 루프 — 생성 → 리뷰 → 재작성을 pass_threshold까지 반복.

    Parameters
    ----------
    project_dir    : 프로젝트 output_dir
    topic          : 주제
    mode           : "auto" | "manual" | "skip"
    writing_style  : 문체
    channel        : 채널
    max_rounds     : 최대 재작성 라운드
    pass_threshold : PASS 판정 점수 (기본 85, brief-reviewer 기본값과 일치)

    Returns
    -------
    최종 feedback dict (score_total, verdict, brief_path 등)
    """
    from auto_agent.modules.brief_review_module import review_brief  # lazy import

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    final: dict[str, Any] = {"round": 0, "score_total": 0, "verdict": "FAIL"}

    for round_num in range(1, max_rounds + 1):
        # 라운드별 brief 생성
        if mode == "auto":
            brief = generate_auto_brief(topic, writing_style, channel)
        else:
            # manual/skip: 기존 planner 사용 (사용자가 별도 인터뷰 수행 가정)
            brief = generate_planner_brief(topic, writing_style, channel)

        # v1 저장 (overwrite)
        save_brief_versioned(brief, project_dir, version="v1", overwrite=True)

        # 리뷰
        try:
            feedback = review_brief(project_dir, version="v1")
        except Exception as e:
            print(f"[ratchet_brief_v1] 리뷰 실패 round {round_num}: {e}", flush=True)
            feedback = {"score_total": 0, "verdict": "FAIL"}

        feedback["round"] = round_num
        final = feedback

        score = feedback.get("score_total", 0)
        verdict = feedback.get("verdict", "FAIL")
        print(f"[ratchet_brief_v1] round {round_num}: {score}점 ({verdict})",
              flush=True)

        if verdict == "PASS" or score >= pass_threshold:
            break

        # 마지막 라운드면 중단
        if round_num >= max_rounds:
            print(f"[ratchet_brief_v1] 최대 라운드 {max_rounds} 도달 — "
                  f"최종 {score}점, 사용자 개입 권장", flush=True)
            break

    return final


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
