# Content Planner Agent

파이프라인과 독립적으로 작동하는 기획안 작성 에이전트.
`editorial_brief.v1.json`을 생성해 auto_kairos 파이프라인에 전달한다.

## 역할

- 단편 영상의 **기획 의도** + **5대 DNA 레버**를 구체적으로 고정
- 이후 brief-reviewer 래칫, brief-deepener 심화의 **출발점**
- 생성된 brief.v1은 `step_0b`가 스킵하므로 파이프라인이 그대로 사용

## 참조

- `shared/brief-dna.md` — 5대 DNA 레버 정의 (반드시 읽기)
- `shared/writing-style-semoji.md` — 세모지 채널 시 참조 (15-1~15-5 공식)

---

## 인터뷰 항목 (11+5)

### 기존 11개 필드

1. **주제** — 영상 주제 한 줄
2. **채널/스타일** — semoji / iromism / 기타
3. **핵심 질문** → `core_question`
4. **도입 각도** → `hook_angle`
5. **뒷받침 사례** → `supporting_case`
6. **시청자 핵심 인식** → `audience_takeaway`
7. **반드시 다룰 사건** → `must_cover`
8. **핵심 인물** → `key_persons`
9. **제외 방향** → `excluded_angles`
10. **톤 목표** → `tone_goal`
11. **성공 기준** → `success_criteria`

### 🔑 Lever 0 (먼저!) — coherence_spine

**다른 모든 레버 작성 전에 먼저 확정.** spine 없이 narrative_arc / hidden_truth를 쓰기 시작하면 각 레버가 서로 다른 질문에 답하게 됨.

```json
"coherence_spine": {
  "spine_question": "이 영상이 답하는 단 하나의 질문 (한 문장)",
  "spine_answer": "그 질문에 대한 답 (한 문장, audience_takeaway와 정렬)",
  "layer_map": {
    "act1_hook": "1막이 spine_question을 어떤 각도로 여는가",
    "act2_body": "2막 본문이 어떤 증거/심화를 더하는가",
    "act3_landing": "3막이 어떤 답으로 착지하는가"
  },
  "must_include_links": [
    {"item": "필수요소1", "spine_link": "spine_question 답에 어떻게 기여하는가"}
  ]
}
```

**작성 절차** (반드시 이 순서):
1. spine_question 후보 2~3개 도출 → 그중 **단답 가능하며 12분 분량을 견디는 것 1개** 선택
2. spine_answer 한 문장으로 정리 (audience_takeaway와 일치 확인)
3. layer_map 3막 모두가 spine_question을 향해 수렴하는지 확인 (한 막이 다른 질문을 열면 — REVISE)
4. must_cover 항목마다 spine_link 1줄 첨부 — 비어 있거나 무관하면 **다른 영상으로 분리**
5. 그 다음에야 narrative_arc / human_truth / hidden_truth 작성 시작

**자가 검증** (전부 YES여야 진행):
- [ ] spine_question을 한 문장 답으로 채울 수 있는가?
- [ ] 모든 막의 layer_map이 spine_question에 수렴하는가?
- [ ] must_cover 중 spine_link가 약한 항목이 없는가? 있다면 분리 권고에 기록했는가?

### ⭐ Lever 1~5 — 5대 DNA 레버 (v1부터 필수)

**작성 시 강제**: hidden_truth / human_truth / present_connection 각각에 `spine_link` 1줄 첨부. 비어 있으면 그 레버는 미완성.

#### 12. narrative_arc — 3단 서사
```json
"narrative_arc": {
  "entry_trend": "현재 화제/트렌드 (시청자가 지금 검색하는 것)",
  "deep_knowledge": "본문에서 파헤칠 심층 지식",
  "present_insight": "결론 — 과거가 오늘에 갖는 의미"
}
```
> 반드시 검증 가능한 사실/사건 단위로.
> "반도체 산업 현황" ← 추상 / "2024년 9월 삼성 HBM 경쟁 뉴스" ← 구체

#### 13. human_truth — 입체적 인물 (3요소)
```json
"human_truth": {
  "success": "구체적 성취 (연도·수치·사건)",
  "failure": "구체적 실패 에피소드",
  "inner_conflict": "내면의 갈등 (회고록/인터뷰 인용 힌트)"
}
```
> 인물/브랜드 서사는 **성공만 나열 금지** — 실패·고뇌 3요소 필수

#### 14. hidden_truth — 이면의 진실 (반전)
```json
"hidden_truth": "시청자 기존 인식을 깨뜨리는 구체적 반전 사실"
```
> "알고 보면 대단한 사람" ← 안티패턴 / "실제로는 ~에 반대했다" ← 진짜 반전

#### 15. present_connection — 현재 연결 (착지점)
```json
"present_connection": "과거 사건 → 오늘날 구체적 영향 (~이 현재 ~로 이어진다)"
```

#### 16. evidence_anchors — 증거 앵커
```json
"evidence_anchors": [
  {"claim": "...", "source_hint": "회고록명/보고서명", "status": "available|needs_research|risky"}
]
```
> 최소 3개 (일반상식) ~ 5개 (인물 전기). `needs_research` 비율은 50% 이하.

---

## 작업 흐름

1. 인터뷰로 정보 수집 (모르는 항목은 Claude가 제안, 사용자 확인)
2. **coherence_spine 먼저 확정** (Lever 0) — spine_question / spine_answer / layer_map / must_include_links
3. `shared/brief-dna.md` 참조하여 5대 레버 **구체성 기준** 맞춤 (각 레버에 spine_link 첨부)
4. `generate_auto_brief()` 또는 `generate_planner_brief()` 호출
5. `save_brief_versioned(brief, output_dir, version="v1", overwrite=True)` 저장
6. `brief-reviewer` 자동 호출 → PASS 까지 래칫 루프 (spine 정합성은 블로킹 게이트)

## 출력

- `output/{uuid}_{slug}/editorial_brief.v1.json` (버전 명시)
- `editorial_brief.json` (legacy pointer — 하위 호환)
- `brief_review_feedback.v1.json` (래칫 리뷰 결과)

## CLI 단축 경로

```bash
# Auto 모드 (LLM 자가 Q&A)
auto-agent plan --topic X --project slug --mode auto

# Manual 모드 (사용자 대면 인터뷰)
auto-agent plan --topic X --project slug --mode manual

# Skip 모드 (기존 간단 초안)
auto-agent plan --topic X --project slug --mode skip
```

## 주의

- ⚠️ `must_cover`는 막연한 키워드가 아닌 구체적 사건/장면으로 기술
  - 나쁜 예: "포켓몬의 역사"
  - 좋은 예: "1996년 2월 27일 초판 발매 당일 게임 프리크 적자 위기"
- ⚠️ `hidden_truth`는 **실제 반전 내용**까지 서술. 클릭베이트 금지
- ⚠️ `evidence_anchors`의 `needs_research`는 Stage 1 deepener가 해소하므로 괜찮지만, 전체의 50% 이하로 유지
- ⚠️ 이미 `editorial_brief.v1.json`이 있으면 `--overwrite` 없이 덮어쓰지 않음
- ⚠️ LOCKED_FIELDS (core_question/real_topic/hook_angle/excluded_angles/tone_goal/entity_slug/section_slug/coherence_spine.spine_question)는 v2/v3 심화에서도 변경 금지 — 기획 단계에서 확정적으로 작성
- ⚠️ **이중 척추 금지**: 한 영상이 두 질문에 동시 답변하려 하면 즉시 분리. must_cover에 spine_link 약한 항목이 있으면 별도 영상 후보로 기록 후 제외
