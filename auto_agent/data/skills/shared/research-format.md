# Research Format

deep-research-kit 출력을 파이프라인 표준 포맷(research_report.json)으로 변환하는 규칙을 정의합니다.

**참조 에이전트**: research-orchestrator

---

## 1. 입력 디렉토리 구조

```
RESEARCH/{topic}_{timestamp}/
├── outputs/
│   ├── 00_executive_summary.md
│   └── 01_full_report/
│       ├── 00_table_of_contents.md
│       ├── 01_introduction.md
│       ├── 02_subtopic_1.md
│       ├── ...
│       └── 99_conclusion.md
├── sources/
│   ├── sources.jsonl          (소스 메타데이터, A-E 등급)
│   └── bibliography.md       (포맷된 참고문헌)
└── state.json                 (리서치 상태)
```

---

## 2. 출력: research_report.json 스키마

```json
{
  "topic": "리서치 주제",
  "summary": "executive summary 전문 (마크다운)",
  "key_figures": [
    {
      "name": "인물/기관명",
      "role": "역할/직책",
      "relevance": "주제와의 관계",
      "quotes": ["인용문1", "인용문2"]
    }
  ],
  "timeline": [
    {
      "date": "2024-01",
      "event": "사건/이벤트",
      "significance": "중요도 설명"
    }
  ],
  "statistics": [
    {
      "metric": "지표명",
      "value": "수치",
      "unit": "단위",
      "source": "출처",
      "year": "연도",
      "context": "맥락 설명"
    }
  ],
  "episodes": [
    {
      "title": "에피소드 제목",
      "content": "핵심 내용 요약 (1-2문장)",
      "narrative_draft": "대본 수준 상세 서술 초안 (200-500자)",
      "must_include": [
        {
          "fact": "반드시 원고에 포함되어야 할 핵심 팩트",
          "source": "src_001",
          "reason": "왜 중요한지"
        }
      ],
      "subtopic": "소속 서브토픽",
      "sources": ["src_001", "src_003"],
      "visual_hints": ["chart", "quote", "timeline"]
    }
  ],
  "comparisons": [
    {
      "subject_a": "비교 대상 A",
      "subject_b": "비교 대상 B",
      "dimensions": [
        {"dimension": "차원", "a_value": "A 값", "b_value": "B 값"}
      ]
    }
  ],
  "sources": [
    {
      "id": "src_001",
      "title": "소스 제목",
      "url": "https://...",
      "author": "저자",
      "date": "발행일",
      "quality_grade": "A",
      "type": "academic | news | official | blog"
    }
  ],
  "source_grades": {
    "A": 5, "B": 12, "C": 8, "D": 2, "E": 0
  },
  "raw_content": {
    "full_report_sections": ["섹션1 마크다운", "섹션2 마크다운"],
    "total_word_count": 15000
  }
}
```

---

## 3. 변환 규칙

### 3.1 summary
- `outputs/00_executive_summary.md` 전문을 그대로 포함

### 3.2 key_figures
- full_report 전체를 스캔하여 반복 등장하는 인물/기관 추출
- 인용문이 있으면 quotes에 포함
- 최소 3명, 최대 10명

### 3.3 timeline
- 보고서 내 날짜가 포함된 사건을 시간순 정렬
- 연도만 있으면 "YYYY", 월까지 있으면 "YYYY-MM" 형식

### 3.4 statistics
- 수치 데이터를 추출하여 구조화
- **반드시 출처(source)를 명기** — sources.jsonl의 id와 매칭
- 단위가 모호하면 원문 그대로 보존

### 3.5 episodes
- full_report의 각 섹션을 에피소드 단위로 분리
- **`content`**: 핵심 내용 1-2문장 요약 (다른 에이전트의 빠른 참조용)
- **`narrative_draft`** (핵심):
  - 리서치 원문의 핵심 논점, 수치, 인용문을 **대본 수준의 자연스러운 문장**으로 풀어쓴다
  - **요약이 아니라 서술**. "시장 규모 150억 달러" → "2025년 AI 에이전트 시장은 150억 달러를 돌파했습니다. 불과 3년 전인 2022년 대비 10배 이상 성장한 수치입니다."
  - 200-500자 범위. 원문의 뉘앙스, 맥락, 인과관계를 보존한다
  - "A 때문에 B가 발생했다"를 "B가 발생했다"로 축소하지 않는다
  - 완성도보다 **정보 보존**이 우선
- **`must_include`**:
  - 에피소드 내에서 특히 중요한 팩트, 수치, 인용문을 별도 표기
  - 에피소드당 최소 1개
  - 각 항목에 source id와 중요 이유를 명기
- **`visual_hints`**: 해당 에피소드를 시각화할 때 적합한 타입 제안
  - "chart", "quote", "timeline", "comparison", "list", "image"

### 3.6 comparisons
- 보고서 내 비교 구도(vs, 대비, 차이)를 추출
- 비교 차원(dimension)별로 구조화

### 3.7 sources
- sources.jsonl을 파싱하여 배열로 변환
- E등급 소스는 제외
- quality_grade 포함

---

## 주의사항

- 원본 데이터를 왜곡하지 않는다. 수치/인용문은 원문 그대로
- sources.jsonl이 없으면 bibliography.md에서 소스 정보 추출
- full_report이 없으면 executive_summary만으로 최소 포맷 생성
- JSON은 UTF-8 인코딩, 한국어 그대로 저장 (ASCII 이스케이프 금지)
