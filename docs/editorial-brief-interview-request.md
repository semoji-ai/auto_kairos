# Auto Kairos 파이프라인 수정 요청

## 제목
파이프라인 시작 전 `editorial_brief` 인터뷰 단계 추가 및 기획 정렬(alignment) 검증 도입 요청

## 배경
현재 Auto Kairos 파이프라인은 주제 입력 후 곧바로 Stage 1 리서치(`skeleton_research`)로 진입합니다.

이 구조에서는 자료 수집 자체는 잘 되더라도, **이 콘텐츠의 진짜 질문이 무엇인지**가 초기에 고정되지 않아서 다음 문제가 발생할 수 있습니다.

- 후킹용 사례가 본론을 집어삼킴
- 리서치 결과가 풍부해질수록 오히려 기획의 중심축이 흐려짐
- 원래 만들고 싶었던 콘텐츠와 다른 방향으로 manuscript/scene가 전개됨
- 사용자는 "내가 원한 건 이게 아닌데"를 Stage 2 이후에야 발견하게 됨

이번 테스트 케이스에서는:

- 출발점: `하이닉스 내년 성과급 10억원 예측` 기사
- 사용자의 진짜 의도: **대한민국 근로소득세/실수령 구조 설명**
- 실제 드리프트 위험: 콘텐츠가 **SK하이닉스 역사/기업 서사** 중심으로 전개됨

즉, 문제의 핵심은 리서치 품질 부족이 아니라 **초기 기획 의도 고정 장치의 부재**입니다.

---

## 현재 구조의 한계
현재 `pipeline.json`상 Stage 1은 아래처럼 시작됩니다.

- `skeleton_research`
- `flesh_research`

하지만 이 앞단에는 다음을 확정하는 스텝이 없습니다.

- 이 영상의 **핵심 질문(core question)**
- 사례와 본론 중 **무엇이 주제이고 무엇이 도입부인지**
- **절대 벗어나면 안 되는 프레이밍**
- 시청자가 최종적으로 가져가야 할 **한 줄 takeaway**

그래서 `topic`만 보고 리서치가 시작되면, 모델은 가장 자료가 풍부하고 내러티브가 강한 방향으로 자연스럽게 흘러가기 쉽습니다.

---

## 요청 사항

### 1) 파이프라인 시작 전 인터뷰 단계 추가
`phase_0` 또는 `stage_1` 시작 전에 사용자 인터뷰 기반의 **기획 확정 단계**를 추가해주세요.

가칭:
- `step_0b: editorial_interview`
- 또는 `step_1_prebrief: editorial_brief_capture`

이 단계는 짧아도 되지만, 아래 질문에 반드시 답하도록 해야 합니다.

#### 필수 수집 항목
- `core_question`
  - 이 영상이 답해야 하는 단 하나의 질문
- `real_topic`
  - 이 콘텐츠의 진짜 주제
- `hook_angle`
  - 처음 5~15초를 여는 도입 장치
- `supporting_case`
  - 본론을 설명하기 위해 끌어오는 사례/회사/인물/기사
- `excluded_angles`
  - 이 콘텐츠가 **아닌 것** / 벗어나면 안 되는 방향
- `audience_takeaway`
  - 시청자가 보고 나서 가져가야 하는 핵심 인식
- `tone_goal`
  - 정보형 / 해설형 / 충격형 / 풍자형 등 톤 목표
- `success_criteria`
  - 이 영상이 잘 됐다고 판단하는 기준

---

### 2) `project_config`와 별도로 `editorial_brief.json` 산출물 생성
현재 `project_config`는 스타일, 음성, 길이 등 실행 설정 중심이라 **편집 의도(editorial intent)**를 담기에 부족합니다.

따라서 별도 산출물로 아래 파일을 만들도록 요청합니다.

- `editorial_brief.json`

#### 권장 스키마 예시
```json
{
  "core_question": "10억원 성과급을 받으면 실제 얼마를 손에 쥐는가?",
  "real_topic": "대한민국 근로소득세와 실수령 구조",
  "hook_angle": "하이닉스 성과급 10억원 예측 기사",
  "supporting_case": "SK하이닉스 성과급 사례",
  "excluded_angles": [
    "하이닉스 기업사 자체",
    "반도체 산업사 중심 서사",
    "최태원 개인 서사"
  ],
  "audience_takeaway": "성과급은 세전 숫자와 실수령 체감이 완전히 다르다는 점을 이해한다",
  "tone_goal": "이로미즘식 훅 강한 설명형",
  "success_criteria": [
    "시청자가 세전/세후 차이를 직관적으로 이해한다",
    "사례보다 세금 구조 설명이 중심에 남는다"
  ]
}
```

---

### 3) `editorial_brief.json`을 Stage 1~2 공통 입력으로 주입
아래 에이전트들이 모두 이 brief를 입력으로 받도록 해주세요.

- `skeleton-researcher`
- `flesh-researcher`
- `draft-writer`
- `targeted-researcher`
- `script-director`
- 필요시 `data-mapper`, `fact-verifier`

핵심은, 이 brief가 단순 참고가 아니라 **우선순위와 프레이밍을 규정하는 상위 컨텍스트**가 되어야 한다는 점입니다.

예를 들어:
- `skeleton-researcher`는 outline을 만들 때 `real_topic` 중심으로 챕터를 설계해야 함
- `draft-writer`는 사례 서사가 아니라 `core_question` 답변을 중심으로 초고를 써야 함
- `script-director`는 scene 분할 시 `audience_takeaway`가 흐려지지 않도록 연출해야 함

---

### 4) Stage 1 checkpoint에 `brief alignment` 검증 추가
현재 Stage 1 checkpoint는 리서치 결과 검토 수준입니다.

여기에 아래 검증을 추가해주세요.

#### 검증 질문
- outline의 각 chapter가 `core_question`에 직접 기여하는가?
- `supporting_case`가 `real_topic`보다 더 큰 비중을 차지하고 있지 않은가?
- `excluded_angles`로 빠진 챕터/문단이 있는가?
- chapter 제목만 봐도 사용자의 원래 의도가 드러나는가?
- 초반 훅 이후 본론 전환이 충분히 빠른가?

#### 권장 결과
- 정렬되면 통과
- 어긋나면 Stage 2로 가지 않고 brief 기반 재설계

즉, "자료가 많다"가 아니라 **"지금 만든 구조가 원래 기획 질문을 향하고 있는가"**를 체크해야 합니다.

---

## 권장 파이프라인 흐름(개정안)

### 기존
1. Preflight
2. skeleton_research
3. flesh_research
4. draft_writing
5. targeted_research
6. manuscript_writing
7. script_split_and_direct

### 제안
1. Preflight
2. **editorial_interview**
3. **editorial_brief.json 생성**
4. skeleton_research
5. flesh_research
6. **brief alignment checkpoint**
7. draft_writing
8. targeted_research
9. manuscript_writing
10. script_split_and_direct

---

## 기대 효과
- 사례와 본론이 뒤바뀌는 기획 드리프트 감소
- 사용자 의도와 다른 방향으로 길게 써버리는 비용 절감
- Stage 1에서 실패를 조기 발견 가능
- Stage 2 이후 대수정 빈도 감소
- 같은 주제라도 **어떤 콘텐츠를 만들고 싶은지**를 더 정확히 반영 가능

---

## 최소 구현안(MVP)
풀 인터뷰 UX가 부담된다면, 최소한 아래 5개만 받아도 효과가 큽니다.

1. `core_question`
2. `real_topic`
3. `hook_angle`
4. `excluded_angles`
5. `audience_takeaway`

이 다섯 개만 있어도 모델이 "무엇을 중심에 두고, 무엇을 배경으로 밀어야 하는지"를 훨씬 잘 판단할 수 있습니다.

---

## 한 줄 요약
지금 필요한 건 리서치 강화가 아니라, **리서치 이전에 기획 의도를 고정하는 인터뷰형 editorial brief 단계**입니다. 이 brief를 Stage 1~2 전 과정의 상위 컨텍스트로 주입하고, Stage 1 끝에서 alignment 검증을 추가해야 사례가 본론을 잡아먹는 문제를 막을 수 있습니다.
