"""
UserPromptSubmit hook — 프로젝트 생성/시작 의도 감지 시 사전 인터뷰 체크리스트 주입.

감지 패턴:
  - "만들어", "영상 만들", "프로젝트 시작", "파이프라인 시작"
  - "auto-kairos", "새 프로젝트", "project create"
  - 주제 단독 입력 + "만들어 / 시작해 / 해줘 / 해보자 / 가자"
  - "이로미즘/세모지 스타일로" 같은 채널 언급 + 주제

인터뷰 완료 판정(둘 중 하나):
  1. 사용자가 명시적으로 인터뷰 종료를 선언 (INTERVIEW_DONE_MARKERS)
  2. 직전 messages에 editorial_brief.json이 이미 만들어진 프로젝트 경로가 등장

⚠️ 단순 키워드(writing_style, art_style, voice_id 등)는 슬래시 커맨드 본문에도
   포함되므로 DONE 판정 기준으로 사용 금지. 명시적 마커만 사용한다.
"""
import json
import sys
import re
from pathlib import Path

CREATION_PATTERNS = [
    r"새\s*프로젝트",
    r"project\s*create",
    r"영상\s*만들",
    r"파이프라인\s*(시작|실행|돌려|돌릴)",
    r"auto[-_.]?kairos",
    r"카이로스\s*전체",
    r"(시작|만들어|해줘|시작해줘|해보자|가자|진행).{0,20}(영상|프로젝트|콘텐츠)",
    r"(영상|프로젝트|콘텐츠).{0,20}(시작|만들어|해줘|해보자|가자|진행)",
    r"주제.{0,30}(만들|시작|영상|해보자|가자)",
    r"(이로미즘|세모지|레고|스틱맨)\s*(스타일|채널|로|으로).{0,30}(해보|시작|가자|만들|진행)",
    r"--project.{1,60}(create|start|run)",
    r"bg\s+start",
    r"run\s+--project",
]

# ⚠️ 매우 보수적으로 유지 — 슬래시 커맨드/문서/스킬 본문에 우연히 박힌 단어로
# 통과되지 않도록 "사용자의 명시적 의도 표현"만 마커로 인정.
INTERVIEW_DONE_MARKERS = [
    "인터뷰 완료",
    "인터뷰는 끝",
    "인터뷰 건너뛰",
    "인터뷰 스킵",
    "interview done",
    "skip interview",
    "brief 확정",
    "brief 작성 완료",
    "editorial_brief 확정",
    "_interview_complete",
]


def _editorial_brief_already_exists(prompt: str) -> bool:
    """프롬프트에 등장한 프로젝트 슬러그/경로의 editorial_brief.json이 실제 존재하면 True."""
    # output/<uuid>_<slug> 또는 --project <slug> 패턴에서 슬러그 추출
    candidates: list[str] = []
    for m in re.finditer(r"output/([0-9a-f]{8}_[^\s/'\"]+)", prompt):
        candidates.append(m.group(1))
    for m in re.finditer(r"--project\s+([^\s'\"]+)", prompt):
        candidates.append(m.group(1))
    if not candidates:
        return False
    kairos_home = Path(__file__).resolve().parents[3]
    output_dir = kairos_home / "output"
    if not output_dir.exists():
        return False
    for cand in candidates:
        # 정확 매칭 + 슬러그만 주어진 경우 prefix 매칭
        for d in output_dir.iterdir():
            if not d.is_dir():
                continue
            if d.name == cand or d.name.endswith("_" + cand) or cand in d.name:
                if (d / "editorial_brief.json").exists() or (d / "editorial_brief.v1.json").exists():
                    return True
    return False

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

    # 명시적 DONE 마커가 있으면 통과 (사용자가 의도적으로 선언한 경우만)
    for marker in INTERVIEW_DONE_MARKERS:
        if marker.lower() in prompt_lower:
            sys.exit(0)

    # 기존 프로젝트의 editorial_brief.json이 이미 존재하면 통과
    if _editorial_brief_already_exists(prompt):
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
