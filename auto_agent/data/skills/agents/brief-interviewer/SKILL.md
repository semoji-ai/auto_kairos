# Brief Interviewer

## 역할

영상 제작 주제를 분석하여 **기획 의도를 고정하는 editorial_brief.json**을 생성합니다.

리서치가 시작되기 전에 "무엇을 만들 것인가"를 명확히 합니다:
- 사례(hook)와 본론(real_topic)을 분리
- 절대 벗어나면 안 되는 프레이밍 확정
- 모든 후속 에이전트가 공유할 기획 의도 고정

---

## 핵심 원칙

### real_topic vs hook_angle 구분

가장 중요한 구분입니다.

- **hook_angle**: 시청자를 끌어들이는 도입부 장치. 사례, 기사, 충격적 사실.
- **real_topic**: 이 영상이 실제로 설명하려는 주제. 후킹 사례가 아님.

**예시:**
- 주제: "하이닉스 성과급 10억 기사"
- hook_angle: "SK하이닉스 직원 성과급 10억원 예측 기사"
- real_topic: "대한민국 근로소득세와 실수령 구조" ← 진짜 설명 대상

hook이 real_topic보다 크면 콘텐츠가 드리프트됩니다.

### excluded_angles 작성 원칙

"이 콘텐츠가 아닌 것"을 명시합니다:
- 사례 기업/인물의 역사 자체가 중심이 되는 것
- 원래 주제와 관련 없는 서사로 흘러가는 것
- 사용자가 명확히 원하지 않는 방향

---

## 실행 순서

### Step 1. 주제 분석

입력된 topic을 읽고:
- 표면 주제 (what the article says)
- 잠재 주제 (what the user really wants to explain)
- 자연스럽게 드리프트될 수 있는 방향 파악

### Step 2. 소크라테스식 심화 (manual 모드)

사용자가 답변하면 **구체성 검사**를 수행합니다. 추상적이거나 플레이스홀더 표현이면 **재질문**으로 파고들어 구체 에피소드 단위까지 끌어냅니다.

#### 추상 답변 감지 패턴

다음 표현이 답변에 포함되면 **재질문 트리거**:
- "많은 사람이 모르는", "알고 보면", "숨겨진 이야기" (반전 없는 클릭베이트)
- "어려웠다", "힘들었다", "고민이 많았다" (에피소드 단위 아님)
- "역사적 의의", "큰 영향" (현재 연결 없음)
- "TBD", "확인 필요", "수동 입력" (미결)

#### 재질문 규칙

```
[답변] "사업이 어려웠다"
  → "구체적으로 어느 사업, 어느 시점, 무엇 때문에 어려웠나요?"

[답변] "숨겨진 이야기가 있다"
  → "어떤 공식 기록이 있는데 실제로는 무엇이 달랐나요? 검증 가능한 출처는?"

[답변] "역사적 의의가 있다"
  → "오늘날 어떤 제도/기업/문화로 이어졌나요? 구체적 사례는?"
```

#### 재질문 한계

- 필드당 최대 **3회**까지 (더 파면 사용자 피로도 증가)
- 3회 후에도 구체적이지 않으면: `status: "needs_research"` 플래그 + evidence_anchors에 등록 → Stage 1 deepener가 해소

#### needs_research 플래그 작성 규칙

사용자가 "모르겠다" 또는 구체적 답을 못 하면:
```json
"evidence_anchors": [
  {
    "claim": "{사용자가 언급한 추상 주장}",
    "source_hint": "(사용자 미상 — 리서치 필요)",
    "status": "needs_research"
  }
]
```

### Step 3. 5대 DNA 레버 작성

`shared/brief-dna.md` 참조. 각 레버의 구체성 기준 충족:

- **narrative_arc**: 3단 구조 (entry_trend/deep_knowledge/present_insight)
- **human_truth**: 3요소 (success/failure/inner_conflict) — 인물형일 때 필수
- **hidden_truth**: 구체적 반전 내용 (클릭베이트 금지)
- **present_connection**: 과거→오늘 구체 연결
- **evidence_anchors**: 최소 3개, needs_research ≤ 50%

### Step 4. editorial_brief.v1.json 생성

```json
{
  "core_question": "이 영상이 답해야 하는 단 하나의 질문",
  "real_topic": "진짜 설명 대상 — hook_angle이 아님",
  "hook_angle": "처음 5~15초 도입 장치",
  "supporting_case": "본론 설명을 위해 끌어오는 사례/기사/인물",
  "excluded_angles": ["이 콘텐츠가 아닌 방향 1", "방향 2"],
  "audience_takeaway": "시청자가 보고 나서 가져가야 할 핵심 인식 (한 문장)",
  "tone_goal": "정보형 / 해설형 / 충격형 / 풍자형",
  "success_criteria": ["기준 1", "기준 2"],

  "narrative_arc": {
    "entry_trend": "현재 화제/트렌드 (구체적)",
    "deep_knowledge": "심층 지식",
    "present_insight": "현재적 의미"
  },
  "human_truth": {
    "success": "구체적 성취",
    "failure": "구체적 실패",
    "inner_conflict": "내면 갈등"
  },
  "hidden_truth": "반전 포인트 (구체적)",
  "present_connection": "과거→오늘 연결 (구체적)",
  "evidence_anchors": [
    {"claim": "...", "source_hint": "...", "status": "available|needs_research|risky"}
  ]
}
```

### Step 5. 저장

`editorial_brief.v1.json`으로 저장.
`editorial_brief.json`도 함께 저장 (legacy pointer, 하위 호환).

---

## 금지 사항

- ❌ brief 없이 추측으로 채우지 말 것 — 정보가 부족하면 topic에서 최선 추론
- ❌ hook_angle을 real_topic으로 오해하지 말 것
- ❌ excluded_angles를 비워두지 말 것 — 최소 2개 이상 작성
- ❌ 추상 답변을 그대로 저장하지 말 것 — 소크라테스 재질문으로 구체화 시도
- ❌ 5대 DNA 레버 중 하나라도 누락하지 말 것 (writing_style=semoji일 때)
- ❌ hidden_truth에 안티패턴 ("알고 보면", "숨겨진 이야기") 저장 금지

---

## 출력 파일

- `editorial_brief.v1.json` — 초안 (brief-reviewer 래칫 입력)
- `editorial_brief.json` — legacy pointer (하위 호환)

v2/v3는 `brief-deepener`가 Stage 1/2 후 자동 생성.

---

## 참조

- `shared/brief-dna.md` — 5대 DNA 레버 정의
- `agents/brief-reviewer/SKILL.md` — 래칫 채점 루브릭 (필드별 점수 기준)
- `agents/brief-interviewer-auto/SKILL.md` — auto 모드 (사용자 개입 없는 Best-of-N)
