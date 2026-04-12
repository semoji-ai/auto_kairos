"""
Editorial Brief Module — 기획 의도 고정 모듈

파이프라인 step_0b에서 실행:
1. editorial_brief.json이 이미 존재하면 스킵 (resume 지원)
2. 없으면 Claude API로 topic 분석 → 초안 생성 후 저장

/auto-kairos 스킬에서 CLI 인터랙티브 인터뷰 후 직접 생성된 경우도 스킵됨.
"""
import json
import os
import sys
from pathlib import Path


BRIEF_SCHEMA = {
    "core_question": "이 영상이 답해야 하는 단 하나의 질문",
    "real_topic": "이 콘텐츠의 진짜 주제 (후킹용 사례가 아닌 실제 설명 대상)",
    "entity_slug": "핵심 엔티티 slug — vault wiki 최상위 폴더명 (예: '바세린의 역사' → '바세린'). 한글 소문자, 공백 없음, 언더스코어 허용",
    "section_slug": "이 콘텐츠의 각도/섹션 slug (예: '역사', '효능', '제조'). 한글 소문자, 공백 없음",
    "hook_angle": "처음 5~15초를 여는 도입 장치 (어떤 사례/기사/장면으로 시작하는가)",
    "supporting_case": "본론을 설명하기 위해 끌어오는 사례/회사/인물/기사",
    "excluded_angles": ["절대 벗어나면 안 되는 방향 1", "절대 벗어나면 안 되는 방향 2"],
    "audience_takeaway": "시청자가 보고 나서 가져가야 하는 핵심 인식 (한 문장)",
    "tone_goal": "정보형 / 해설형 / 충격형 / 풍자형 등",
    "success_criteria": ["이 영상이 잘 됐다고 판단하는 기준 1", "기준 2"],
}


def generate_brief_from_topic(topic: str, writing_style: str = "") -> dict:
    """Claude API로 topic → editorial_brief 초안 생성."""
    try:
        import anthropic
    except ImportError:
        print("[editorial_brief] anthropic 패키지 없음 — 기본 brief 생성", flush=True)
        return _default_brief(topic)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("[editorial_brief] ANTHROPIC_API_KEY 없음 — 기본 brief 생성", flush=True)
        return _default_brief(topic)

    style_hint = ""
    if writing_style == "iromism":
        style_hint = "\n채널 특성: 이로미즘 — 충격적 후킹, 날카로운 해설, 드라마틱 전개"
    elif writing_style == "semoji":
        style_hint = "\n채널 특성: 세모지 — 친근한 정보 전달, 명확한 구조"

    prompt = f"""다음 영상 제작 주제를 분석해서 editorial_brief JSON을 생성하세요.

주제: {topic}{style_hint}

핵심 원칙:
- real_topic: 후킹용 사례가 아닌 '진짜 설명하려는 주제'. 예) "SK하이닉스 성과급" → 진짜 주제는 "대한민국 근로소득세 구조"일 수 있음
- entity_slug: 핵심 엔티티의 vault 저장 slug. Wikipedia처럼 최상위 엔티티명. 예) "바세린의 역사" → "바세린", "SK하이닉스 성과급 논란" → "SK하이닉스". 한글 소문자, 공백 대신 언더스코어, 특수문자 없음
- section_slug: 이 콘텐츠의 각도/섹션. 예) "바세린의 역사" → "역사", "바세린 효능" → "효능". 한글 소문자, 공백 없음
- hook_angle: 시청자를 끌어들이는 도입 장치 (사례/기사/충격적 사실)
- excluded_angles: 이 콘텐츠가 빠지면 안 되는 방향 — 사례가 본론을 잡아먹는 현상 방지
- core_question: 시청자가 이 영상을 다 보고 나서 "아, 이 질문의 답을 얻었다"고 느껴야 할 질문

반드시 아래 JSON 형식으로만 응답하세요 (설명 없이 JSON만):
{{
  "core_question": "...",
  "real_topic": "...",
  "entity_slug": "...",
  "section_slug": "...",
  "hook_angle": "...",
  "supporting_case": "...",
  "excluded_angles": ["...", "..."],
  "audience_takeaway": "...",
  "tone_goal": "...",
  "success_criteria": ["...", "..."]
}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # JSON 블록 추출
        if "```" in text:
            import re
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if m:
                text = m.group(1)
        return json.loads(text)
    except Exception as e:
        print(f"[editorial_brief] Claude API 호출 실패: {e}", flush=True)
        return _default_brief(topic)


def _default_brief(topic: str) -> dict:
    """API 실패 시 기본 brief (topic 기반 최소 구조)."""
    import re
    # 간단한 entity_slug 추출: 첫 명사구 (조사/어미 제거)
    entity = re.sub(r"(의|을|를|이|가|은|는|와|과|에서|에|로|으로)\s.*$", "", topic).strip()
    entity_slug = re.sub(r"\s+", "_", entity.lower())
    # section_slug: 마지막 단어
    parts = topic.split()
    section_slug = parts[-1].lower() if len(parts) > 1 else "overview"
    return {
        "core_question": f"{topic}에 대해 시청자가 가장 궁금해하는 핵심 질문은?",
        "real_topic": topic,
        "entity_slug": entity_slug,
        "section_slug": section_slug,
        "hook_angle": f"{topic} 관련 충격적이거나 흥미로운 사실로 시작",
        "supporting_case": f"{topic} 관련 대표 사례",
        "excluded_angles": ["주제와 직접 관련 없는 기업/인물 서사 중심 전개"],
        "audience_takeaway": f"{topic}의 핵심 구조와 의미를 이해한다",
        "tone_goal": "해설형",
        "success_criteria": [
            "시청자가 핵심 개념을 직관적으로 이해한다",
            "사례보다 본질 설명이 중심에 남는다",
        ],
    }


def main():
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    brief_path = project_dir / "editorial_brief.json"

    # resume: 이미 존재하면 스킵
    if brief_path.exists():
        print(f"[editorial_brief] 이미 존재 — 스킵: {brief_path}", flush=True)
        sys.exit(0)

    # project_config에서 topic 읽기
    config_path = project_dir / "project_config.json"
    topic = ""
    writing_style = ""
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            topic = cfg.get("topic", "")
            writing_style = cfg.get("writing_style", "")
        except Exception:
            pass

    if not topic:
        # DB에서 읽기 시도
        topic = os.environ.get("PROJECT_NAME", "알 수 없는 주제")

    print(f"[editorial_brief] 주제: {topic}", flush=True)
    print("[editorial_brief] AI 초안 생성 중...", flush=True)

    brief = generate_brief_from_topic(topic, writing_style)
    brief["_generated_by"] = "auto"
    brief["_topic"] = topic

    brief_path.write_text(
        json.dumps(brief, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[editorial_brief] 저장 완료: {brief_path}", flush=True)
    print(f"  core_question: {brief.get('core_question', '')}", flush=True)
    print(f"  real_topic: {brief.get('real_topic', '')}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
