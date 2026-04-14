"""
UserPromptSubmit hook — 프로젝트 생성/시작 의도 감지 시 사전 인터뷰 체크리스트 주입.

감지 패턴:
  - "만들어", "영상 만들", "프로젝트 시작", "파이프라인 시작"
  - "auto-kairos", "새 프로젝트", "project create"
  - 주제 단독 입력 + "만들어 / 시작해 / 해줘"

이미 인터뷰가 완료된 신호가 있으면 주입하지 않음:
  - "editorial_brief", "art_style", "voice_id", "아트스타일 선택", "인터뷰 완료"
"""
import json
import sys
import re

CREATION_PATTERNS = [
    r"새\s*프로젝트",
    r"project\s*create",
    r"영상\s*만들",
    r"파이프라인\s*(시작|실행|돌려|돌릴)",
    r"auto.kairos\s*(시작|실행)",
    r"(시작|만들어|해줘|시작해줘).{0,20}(영상|프로젝트|콘텐츠)",
    r"(영상|프로젝트|콘텐츠).{0,20}(시작|만들어|해줘)",
    r"주제.{0,30}(만들|시작|영상)",
    r"--project.{1,60}(create|start|run)",
    r"bg\s+start",
    r"run\s+--project",
]

INTERVIEW_DONE_SIGNALS = [
    "editorial_brief",
    "art_style",
    "voice_id",
    "아트스타일",
    "인터뷰",
    "real_topic",
    "hook_angle",
    "기획 의도",
    "core_question",
    "writing_style",
    "artstyle",
]

INTERVIEW_CONTEXT = """
⚠️ **프로젝트 사전 인터뷰 필수** ⚠️

새 영상 프로젝트를 시작하기 전에 반드시 아래 항목을 먼저 확인해야 합니다.
`/auto-kairos` 스킬을 실행하거나, 아래 인터뷰를 직접 진행하세요.

---

## 🎬 사전 인터뷰 체크리스트

### A. 채널 & 스타일 설정
- [ ] **채널/아트스타일**: quirky_cartoon(이로미즘) / semoji(세모지) / lego / stickman_cute 중 선택
- [ ] **문체(writing_style)**: iromism / semoji / neutral 중 선택
- [ ] **보이스 ID(voice_id)**: 아트스타일 프리셋에서 자동 결정 (수동 지정 시 명시)
- [ ] **테마(video_theme)**: dark / light 중 선택 (기본: dark)
- [ ] **분량**: 1분 / 3분 / 5분 / 10분 중 선택

### B. 기획 인터뷰 (5개 질문)
1. 이 영상이 답해야 하는 **핵심 질문** 하나는?
2. **진짜 주제**는? (hook 사례 말고 실제 설명 대상)
3. 도입부에 쓸 **사례/기사/장면**은?
4. 절대 이쪽으로 흘러가면 안 되는 **방향**은?
5. 시청자가 가져가야 할 **핵심 인식**은?

---

이 항목들이 확인되지 않으면 파이프라인을 시작하지 마세요.
모든 답변이 준비되면 `/auto-kairos` 스킬로 자동 저장+실행하세요.
"""


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    prompt = ""
    # UserPromptSubmit 형식: {"prompt": "...", "session_id": "..."}
    if isinstance(data, dict):
        prompt = data.get("prompt", "") or data.get("message", "") or ""

    prompt_lower = prompt.lower()

    # 인터뷰 완료 신호가 있으면 통과
    for signal in INTERVIEW_DONE_SIGNALS:
        if signal.lower() in prompt_lower:
            sys.exit(0)

    # 프로젝트 생성 의도 감지
    matched = any(re.search(p, prompt, re.IGNORECASE) for p in CREATION_PATTERNS)
    if not matched:
        sys.exit(0)

    # 인터뷰 체크리스트 주입
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": INTERVIEW_CONTEXT,
        }
    }
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
