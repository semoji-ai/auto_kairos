---
name: creative-direction-process
description: Reference for the 3-step creative direction design process (narrative analysis, visual concept, headline writing)
invocation: agent-only
---

## 7. Creative Direction 설계 프로세스

Visual Composer가 각 씬의 creative 필드를 설계할 때 따르는 3단계:

### Step 1: 내러티브 분석

나레이션 텍스트를 읽고 핵심 요소를 식별:

```
질문:
- 이 씬의 핵심 전달 내용은? (숫자, 사건, 인물, 감정, 비교)
- 시청자가 느껴야 할 감정은? (긴장, 놀라움, 슬픔, 이해)
- 이전/이후 씬과의 관계는? (강화, 대비, 전환)
```

### Step 2: 시각 컨셉 설계

핵심 요소에 맞는 시각적 접근법 결정:

```
숫자가 핵심 → emphasis: "number", reveal: "count_up" 또는 "dramatic_pause"
항목 나열이 핵심 → reveal: "stagger" 또는 "stagger_then_flash"
대비가 핵심 → reveal: "split_reveal", emphasis: "contrast"
인물이 핵심 → emphasis: "person", reveal: "spotlight"
사건이 핵심 → reveal: "dramatic_pause", mood: "dramatic"
과정이 핵심 → reveal: "build_up", emphasis: "sequence"
```

### Step 3: headline 작성

나레이션 텍스트를 화면용 핵심 헤드라인으로 변환:

```
규칙:
1. 나레이션 문장을 그대로 쓰지 않는다
2. 임팩트 있는 짧은 구문으로 변환
3. 핵심 단어에 {{}} 마크업 적용
4. \n으로 적절한 줄바꿈
5. 2-3줄 이내

예시:
나레이션: "미국은 2026년 2월 28일 새벽, 이란의 9개 주요 도시를 동시에 타격했습니다."
headline: "{{9개 도시}}\n동시 타격"

나레이션: "이 작전으로 민간인 사망자가 2,400명에 달했습니다."
headline: "민간인 사망자\n{{2,400명}}"
```
