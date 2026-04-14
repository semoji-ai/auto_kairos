# Research Strategist — SKILL

## 역할
editorial_brief + skeleton.json을 읽고 세 가지를 결정한다:
1. **outline.json** — 챕터 구조 + research_focus 질문
2. **research_queries.json** — 챕터별 검색 쿼리 + 메인 쿼리
3. **hook_strategy.json** — 훅 전략 + 오프닝 방향

## 입력
- `editorial_brief.json` — 주제, core_question, hook_angle, tone, excluded_angles
- `skeleton.json` — timeline, key_figures, key_episodes, summary_bullets

## 출력

### outline.json
```json
{
  "title": "주제명",
  "core_question": "핵심 질문",
  "target_duration_minutes": 5,
  "chapters": [
    {
      "chapter_number": 1,
      "title": "챕터 제목 (20자 이내, 구체적)",
      "act": 1,
      "purpose": "이 챕터가 전체 서사에서 하는 역할 (1~2문장)",
      "duration_ratio": 0.20,
      "research_focus": [
        "전환점/사건 질문",
        "날짜·수치·규모 질문",
        "인물·기관·WHY/HOW 질문"
      ],
      "key_points": []
    }
  ]
}
```

### research_queries.json
```json
{
  "main_query": "리서치 에이전트가 메인으로 사용할 검색 쿼리",
  "chapter_queries": [
    {
      "chapter_number": 1,
      "title": "챕터 제목",
      "queries": ["검색 쿼리 1", "검색 쿼리 2"]
    }
  ]
}
```

### hook_strategy.json
```json
{
  "hook_type": "shocking_fact | question | contrast | story",
  "opening_line": "영상 첫 문장 또는 훅 방향",
  "tension": "시청자가 끝까지 보게 만드는 긴장감/궁금증",
  "payoff": "마지막에 해소되는 것"
}
```

## 챕터 설계 원칙

### 서사 흐름
- Act 1 (도입): 훅 → 전제 설정. 시청자가 "왜 봐야 하는가"를 느끼게
- Act 2 (전개): 핵심 전환점·사건·수치 중심. 각 챕터가 다음 챕터로 이어지는 인과 구조
- Act 3 (결론): 현재적 의미 + takeaway. 단순 요약이 아닌 관점 제시

### 챕터 제목 규칙
- 구체적이어야 한다 — "성장" 대신 "유압 혁명이 스팀을 죽인 순간"
- 질문형 또는 사건 중심 — "왜 굴착기는 노란색인가?"
- editorial_brief의 core_question/hook_angle을 챕터 제목으로 쓰지 않는다

### research_focus 질문 규칙
- 챕터 제목 키워드만 짧게 (챕터 제목 전체를 앞에 반복하지 않는다)
- 반드시 사실 확인 가능한 질문 (연도, 수치, 인물명 등)
- 예시: "유압 실린더 특허 최초 출원 연도와 발명가는?"

### 검색 쿼리 원칙
- Wikipedia/학술/뉴스에서 실제로 검색할 수 있는 형태
- 한국어 or 영어 중 결과가 더 풍부한 언어 선택
- 너무 포괄적이지 않게 — 챕터별로 좁혀서 구체적인 사실을 찾을 수 있도록

### 훅 전략 원칙
- editorial_brief의 hook_angle을 구체적인 오프닝 방향으로 변환
- 시청자가 끝까지 보게 만드는 긴장감(tension)을 명시
- "충격적 사실 → 전개 → 해소" 구조 권장

## 작업 순서
1. `editorial_brief.json` 읽기
2. `skeleton.json` 읽기
3. outline.json 작성 → 저장
4. research_queries.json 작성 → 저장
5. hook_strategy.json 작성 → 저장
6. 완료 출력: "STRATEGY_COMPLETE"
