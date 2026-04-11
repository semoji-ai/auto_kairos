---
name: auto-kairos
description: 영상 제작 파이프라인 실행. 주제/분량/아트스타일을 인터뷰로 입력받고 파이프라인을 자동 실행한다.
user-invocable: true
---

# /auto-kairos — 영상 제작 파이프라인

## 실행 흐름

### 1단계: 기획안 선택 또는 주제 직접 입력

먼저 볼트에 기획안이 있는지 확인한다:
```bash
ls $KAIROS_VAULT_DIR/insights/planning/*기획안.md 2>/dev/null | tail -10
```

**기획안이 있으면:**
```
📋 오늘의 기획안:
  [1] [세모지 900점] 구다이글로벌 — 3억→10조 M&A 전략 (추천 12~15분)
  [2] [세모지 729점] 무신사 — 고3이 만든 패션 제국 (추천 10분)
  [3] [이로미즘 900점] 48시간 슈퍼위크 — WGBI+추경 (추천 13~15분)
  [0] 직접 주제 입력

기획안 번호를 선택하세요:
```

선택하면 기획안에서 자동 추출:
- 주제 (title)
- 채널 (channel → writing_style + art_style 매핑)
- 추천 분량 (duration)

**기획안이 없거나 [0] 선택 시:**
- "어떤 영상을 만들까요? (주제/제목)"

### 2단계: 분량 선택

```
분량을 선택하세요:
  1) 1분 (숏폼)
  2) 3분
  3) 5분
  4) 10분 (롱폼)
```

### 3단계: 아트스타일 프리셋 선택

아트스타일 목록을 보여주기 전에 `auto_agent/data/artstyle/styles/` 디렉토리를 Glob으로 스캔해서 사용 가능한 프리셋을 확인한다.

```
아트스타일을 선택하세요:
  1) quirky_cartoon (이로미즘) -- 낙서 카툰, cinematic, 극적 내러티브
  2) semoji (세모지) -- 2D 플랫, flat staging, 정보 전달 중심
  3) lego -- 레고 미니피규어, cinematic
  4) stickman_cute -- 스틱맨 손그림, flat
```

각 프리셋의 JSON을 읽어서 channel, image.staging, guidelines의 첫 문장을 표시한다.

### 4단계: Editorial Brief 인터뷰 (기획 의도 고정)

아트스타일 선택 후, 파이프라인 시작 전에 **기획 의도를 고정**한다.

아래 5개 항목을 순서대로 질문한다 (5개만으로도 충분):

```
📋 기획 의도를 명확히 해둘게요 (5개 질문, 빠르게):

1) 이 영상이 답해야 하는 핵심 질문 하나는?
   (예: "10억원 성과급을 받으면 실제 얼마를 손에 쥐는가?")

2) 이 콘텐츠의 진짜 주제는? (hook 사례 말고 실제 설명 대상)
   (예: "대한민국 근로소득세와 실수령 구조")

3) 어떤 사례/기사/장면으로 도입부를 열 건가요?
   (예: "하이닉스 성과급 10억 예측 기사")

4) 이 영상이 절대 이쪽으로 흘러가면 안 되는 방향은?
   (예: "SK하이닉스 기업사 / 반도체 산업 서사 중심")

5) 시청자가 다 보고 나서 가져가야 할 핵심 인식은?
   (예: "성과급은 세전 숫자와 실수령 체감이 완전히 다르다")
```

답변을 받으면 `editorial_brief.json`을 생성한다:

```python
import json
from pathlib import Path

brief = {
    "core_question": "{1번 답변}",
    "real_topic": "{2번 답변}",
    "hook_angle": "{3번 답변}",
    "supporting_case": "{3번 답변에서 추출한 사례}",
    "excluded_angles": ["{4번 답변}"],
    "audience_takeaway": "{5번 답변}",
    "tone_goal": "{아트스타일에서 자동 결정: quirky_cartoon→충격형, semoji→정보형}",
    "success_criteria": [
        "시청자가 핵심 개념을 직관적으로 이해한다",
        "사례보다 본질 설명이 중심에 남는다"
    ],
    "_generated_by": "cli_interview"
}
```

프로젝트 생성 후 `{output_dir}/editorial_brief.json`에 저장한다.

### 6단계: 설정 확인 (기존 4단계)

선택한 프리셋 JSON에서 자동으로 가져올 값:
- `writing_style`: 프리셋의 channel로 매핑 (이로미즘→iromism, 세모지→semoji, 없으면 직접 질문)
- `voice_id`: 프리셋의 voice.voice_id
- `voice_settings`: 프리셋의 voice.voice_settings
- `art_style`: 프리셋 파일의 상대경로 (예: `artstyle/styles/quirky_cartoon.json`)

설정 요약을 보여주고 확인:
```
설정 확인:
  주제: {topic}
  핵심 질문: {core_question}
  진짜 주제: {real_topic}
  분량: {duration}분
  아트스타일: {preset_name}
  문체: {writing_style}
  음성: {voice_id[:12]}...

  시작할까요? (Y/n)
```

### 7단계: 프로젝트 생성 (기존 5단계)

Bash로 실행:
```bash
.venv/bin/python -c "
from auto_agent.db.project_manager import ProjectManager
pm = ProjectManager()
config = {
    'art_style': '{art_style_path}',
    'writing_style': '{writing_style}',
    'duration_minutes': {duration},
    'voice_id': '{voice_id}',
    'voice_settings': {voice_settings_json},
}
pid = pm.create_project(
    name='{project_name}',
    slug='{slug}',
    topic='{topic}',
    config=config,
    channel='{channel}',
)
p = pm.get_project(pid)
print(f'id={pid} slug={p[\"slug\"]} uuid={p.get(\"uuid\",\"\")}')
"
```

**CLAUDE.md 규칙 준수**: config에 art_style, writing_style, duration_minutes 반드시 포함.

### 8단계: editorial_brief.json 저장 (기존 6단계 전)

프로젝트 생성 후, 4단계에서 받은 brief 답변을 파일로 저장한다:

```bash
.venv/bin/python -c "
import json
from pathlib import Path
output_dir = Path('{output_dir}')
output_dir.mkdir(parents=True, exist_ok=True)
brief = {
    'core_question': '{core_question}',
    'real_topic': '{real_topic}',
    'hook_angle': '{hook_angle}',
    'supporting_case': '{supporting_case}',
    'excluded_angles': {excluded_angles_json},
    'audience_takeaway': '{audience_takeaway}',
    'tone_goal': '{tone_goal}',
    'success_criteria': ['시청자가 핵심 개념을 직관적으로 이해한다', '사례보다 본질 설명이 중심에 남는다'],
    '_generated_by': 'cli_interview'
}
(output_dir / 'editorial_brief.json').write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding='utf-8')
print('editorial_brief.json 저장 완료')
"
```

output_dir은 `pm.get_project(pid)['output_dir']`에서 가져온다.

### 9단계: 파이프라인 백그라운드 실행 (기존 6단계)

```bash
export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"
set -a && source .env && set +a
.venv/bin/python -m auto_agent.cli bg start --project {slug}
```

### 10단계: 진행 상황 안내 (기존 7단계)

사용자에게 알려줄 것:
- 대시보드 URL: `http://localhost:8000`
- 상태 확인: `auto-agent bg status --project {slug}`
- 로그 확인: `auto-agent bg logs --project {slug}`

## 주의사항

- 프로젝트 생성 시 config에 필수값(art_style, writing_style, duration_minutes)이 누락되면 파이프라인이 실패한다
- slug는 영문+숫자+언더스코어만 허용 (한글은 자동 변환)
- voice_id와 voice_settings는 프리셋에서 자동으로 가져온다 — 사용자에게 묻지 않는다
- channel은 프리셋의 channel 값을 사용한다 (null이면 None)
- 이전 버전이 있으면 v2, v3 등 버전 번호를 slug에 추가한다
- 대시보드가 꺼져있으면 시작 전에 재시작한다 (--reload 없이)
