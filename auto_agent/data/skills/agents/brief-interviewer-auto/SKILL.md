# Brief Interviewer (Auto Mode)

## 역할

사용자 개입 없이 **LLM 자가 Q&A**로 editorial_brief.v1.json을 생성한다.
각 필드에 대해 후보를 여럿 만들고, 세모지 DNA 부합도로 자가 채점하여 최고점을 선택한다.

`auto-agent plan --mode auto` 또는 `brief_mode: "auto"` 설정 시 사용.

---

## 핵심 원칙

### 1. Best-of-N 선택

각 필드에 대해 **후보 3~5개** 생성 → 자가 평가 → 최고점 선택.
기계적 템플릿 채움이 아닌, 다양한 앵글을 고려한 후 선택.

### 2. DNA 레버 우선 고려

`shared/brief-dna.md`의 5대 레버를 **기획 단계에서 강제**:
- narrative_arc (3단 서사)
- human_truth (3요소)
- hidden_truth (반전)
- present_connection (착지)
- evidence_anchors (출처)

### 3. excluded_angles로 드리프트 방지

후보 생성 시 `excluded_angles`에 해당하는 방향이면 **즉시 폐기**.

---

## 입력

- topic (문자열) — 주제 한 줄
- writing_style (선택) — "semoji" | "iromism" | ""
- channel (선택)
- vault 맥락 (선택) — vault wiki에 해당 엔티티가 있으면 참조

## 출력

- `editorial_brief.v1.json` (메인)
- `editorial_brief.json` (legacy 포인터, v1과 동일 내용)

**두 파일 모두 동일한 내용으로 Write 도구로 저장해야 함.** 다운스트림(stage_1, stage_2)이 둘 다 사용함.

---

## 실행 순서

### Step 1. 주제 분석

topic을 읽고:
- **표면 주제** (what it says)
- **잠재 주제** (what the user really wants to explain) → `real_topic`
- **드리프트 위험 방향** → `excluded_angles`

### Step 2. 후보 생성 (병렬 5개 앵글)

각 DNA 레버에 대해 서로 다른 앵글의 후보 여러 개를 **한 번의 LLM 호출**로 생성:

```
후보 생성 프롬프트 (하나의 LLM call에 통합):

주제 "{topic}"에 대해:
1. hook_angle 후보 3개 (서로 다른 관점 — 뉴스 / 일화 / 수치)
2. hidden_truth 후보 3개 (서로 다른 반전 지점)
3. narrative_arc.entry_trend 후보 3개
4. narrative_arc.deep_knowledge 후보 3개
5. human_truth.failure 후보 3개 (인물형일 때만)
```

### Step 3. 자가 채점

각 후보 세트에 대해 3축 평가 (각 10점 만점):
- **구체성**: 검증 가능한 사실/수치/연도 포함 여부
- **반전 강도**: 시청자 기존 인식을 얼마나 깨는가
- **세모지 DNA 부합**: writing-style-semoji 공식 부합도

총점 최고 후보 선택.

### Step 4. 통합 및 일관성 검증

선택된 후보들을 합쳐 하나의 brief로 조립.
필드 간 정합성 검사:
- `hidden_truth`가 `core_question` 답변에 기여하는가
- `narrative_arc.present_insight`가 `audience_takeaway`와 일치하는가
- `must_cover`가 `excluded_angles`를 침범하지 않는가

### Step 5. evidence_anchors 초안 작성

기획 단계에서 확보된 주장은 `available`, 나머지는 `needs_research`로 표시.
(Stage 1 deepener가 확인하면 `available`로 승격)

### Step 6. Write

`editorial_brief.v1.json`과 `editorial_brief.json` **둘 다** 동일 내용으로 저장. `_generated_by: "auto"`, `_topic: "{topic}"`, `_version: "v1"` 메타 추가.

**필수 출력 스키마** (모든 필드 채워야 함, 플레이스홀더 금지):
```json
{
  "core_question": "시청자가 답을 얻어야 할 핵심 질문 (구체)",
  "real_topic": "진짜 설명 대상",
  "entity_slug": "엔티티 slug (한글 소문자, 공백→언더스코어)",
  "section_slug": "각도 slug (예: 역사, 효능)",
  "hook_angle": "처음 5~15초 도입 장치 (구체 사실/사건)",
  "supporting_case": "본론 뒷받침 사례",
  "excluded_angles": ["드리프트 방지 방향1", "방향2"],
  "audience_takeaway": "한 문장 핵심 인식",
  "tone_goal": "정보형|향수형|인물중심형|해설형|충격형",
  "must_cover": ["YYYY년 구체사건1", "사건2", "사건3"],
  "key_persons": ["인물1", "인물2"],
  "success_criteria": ["성공 기준1", "기준2"],
  "narrative_arc": {
    "entry_trend": "현재 트렌드 (구체)",
    "deep_knowledge": "심층 지식",
    "present_insight": "과거→오늘 의미"
  },
  "human_truth": {
    "success": "구체 성취",
    "failure": "구체 실패 에피소드",
    "inner_conflict": "내면 갈등"
  },
  "hidden_truth": "기존 인식을 깨는 반전 (구체)",
  "present_connection": "과거→오늘 인과 연결",
  "evidence_anchors": [
    {"claim": "주장", "source_hint": "출처 힌트", "status": "available|needs_research"}
  ],
  "_generated_by": "auto",
  "_topic": "{원본 topic}",
  "_version": "v1"
}
```

---

## 후보 생성 프롬프트 템플릿

```
주제: {topic}
채널: {channel}
문체: {writing_style}
제외 방향: {excluded_angles}

아래 각 필드에 대해 **서로 다른 앵글의 후보 3개**를 생성하고,
각 후보마다 (구체성/반전성/DNA부합도) 3축 자가 평가하세요.

- hook_angle: 처음 5~15초 도입 장치
- hidden_truth: 시청자 기존 인식을 깨뜨리는 반전 포인트
- narrative_arc.entry_trend: 현재 화제/트렌드
- narrative_arc.deep_knowledge: 본문에서 파헤칠 심층 지식
- human_truth.failure: (인물형일 때) 구체적 실패 에피소드

JSON으로 반환:
{
  "candidates": {
    "hook_angle": [
      {"content": "...", "scores": {"구체성": 8, "반전성": 6, "DNA부합도": 7}},
      ...
    ],
    ...
  }
}
```

---

## 금지 사항

- ❌ 후보 1개만 생성하고 그대로 사용 — **반드시 다중 후보 + 선택**
- ❌ excluded_angles에 해당하는 후보를 폐기하지 않고 선택
- ❌ hidden_truth에 안티패턴("알고 보면 대단한", "숨겨진 이야기") 허용
- ❌ 구체성 없는 플레이스홀더("TBD", "확인 필요") 출력

---

## 한계 및 대응

### 한계
- 사용자 고유의 창작 방향을 반영할 수 없음 → excluded_angles로만 제한
- vault 맥락이 없으면 근거 빈약 가능 → evidence_anchors의 needs_research 비율 허용

### 대응
- brief-reviewer가 후속 평가에서 재질문 형태로 약점 포착
- Stage 1 deepener가 리서치로 v2에서 구체화
- 사용자가 언제든 brief.v1.json을 직접 편집 가능
