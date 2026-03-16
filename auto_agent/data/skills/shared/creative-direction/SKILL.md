---
name: creative-direction
description: Use when defining scene creative attributes including mood, reveal, emphasis, headline, items, and layout selection
---

# Creative Direction

씬별 창의적 연출을 설계하는 핵심 가이드라인입니다.
기본 타이포그래피 프리셋 위에서 각 장면의 **내러티브 아크, 정보 공개 방식, 감정적 강조**를 설계합니다.

**참조 에이전트**: visual-composer

---

## 1. 핵심 철학

**모든 장면은 하나의 미니 영화다.**

기존의 rigid한 19개 타입 배정이 아니라, 각 씬의 나레이션을 분석하여:
- **이 장면이 전달하려는 것이 무엇인가?** (정보, 감정, 긴장)
- **가장 임팩트 있는 표현 방식은?** (텍스트, 숫자, 시각화, 구조도)
- **정보를 어떤 순서로 공개할 것인가?** (점진적, 동시, 반전, 축적)

이 세 가지 질문에 답하여 `creative` 필드를 설계한다.

---

## 2. Creative 필드 스키마

```json
{
  "visualization": {
    "title": "동시 타격",
    "items": ["테헤란", "이스파한", ...],
    "values": [9],

    "creative": {
      "concept": "도시 이름이 하나씩 나타나고, 모두 동시에 번쩍이며, 큰 숫자 9가 화면을 채운다",
      "reveal": "stagger_then_flash",
      "emphasis": "count",
      "headline": "{{9개 도시}}\n동시 타격",
      "mood": "dramatic"
    }
  }
}
```

### creative 필드 상세

| 필드 | 타입 | 설명 |
|------|------|------|
| `concept` | string | 1-2문장으로 시각 연출 의도 서술. 렌더러가 참조하는 핵심 지시문 |
| `reveal` | enum | 정보 공개 패턴 (아래 3번 참조) |
| `emphasis` | enum | 핵심 강조 요소 (아래 4번 참조) |
| `headline` | string | 화면에 표시될 핵심 텍스트. `{{키워드}}`는 accent 색상, `\n`은 줄바꿈. 아래 2.1 규칙 필독 |
| `mood` | enum | 감정적 톤 (아래 5번 참조) |
| `layout` | enum (선택) | 의도 기반 레이아웃 직접 지정 (아래 6.1번 참조). 없으면 렌더러가 자동 추론 |

### 2.1 headline · items · itemIcons 역할 분리 (절대 규칙)

headline과 items는 **서로 다른 역할**이다. 같은 내용을 반복하면 시청자는 중복을 보게 된다.

**headline** = "시청자가 기억할 핵심 한 줄" (감정적·요약적)
**items** = "그 핵심을 뒷받침하는 구체적 세부 정보" (보조·확장)

#### 규칙 1: headline ≠ items (중복 금지)

headline에 이미 나온 단어/숫자를 items에서 반복하지 않는다.

```
❌ headline: "배당수익률 {{7.03%}} 금융지주 1위"
   items: ["우리금융", "하나금융", "신한금융", "KB금융"]  ← OK (세부 보조)

❌ headline: "주당 {{3,600원}} 수익률 {{5.92%}}"
   items: ["주당 3,600원", "수익률 5.92%"]  ← ⛔ headline과 완전 중복

✅ headline: "주당 {{3,600원}}\n수익률 {{5.92%}}"
   items: []  ← headline만으로 충분하면 items 비움

❌ headline: "{{통신}}과 {{인프라}}도 강합니다"
   items: ["통신", "인프라"]  ← ⛔ headline 단어 그대로 반복

✅ headline: "{{통신}}과 {{인프라}}도 강합니다"
   items: ["SKT 6.07%", "맥쿼리 6.88%"]  ← 구체적 세부 정보로 보완
```

**자가 점검**: items의 각 항목을 headline에서 찾을 수 있으면 → 중복. 삭제하거나 구체화하라.

#### 규칙 2: `{{}}` accent는 씬당 최대 2개

`{{}}`는 "시청자의 눈이 가장 먼저 가야 할 곳"이다. 3개 이상이면 강조가 분산되어 아무것도 강조되지 않는다.

```
❌ headline: "{{높은 배당률}} vs {{높은 성장률}}"  ← 2개 OK
❌ headline: "{{단리}} vs {{복리}} 차이가 {{엄청나요}}"  ← ⛔ 3개
✅ headline: "{{단리}} vs {{복리}}\n차이가 엄청나요"  ← 2개로 제한

❌ headline: "소비재 {{27%}} · 에너지 {{24%}} 방어적 구성"  ← ⛔ 숫자마다 accent
✅ headline: "소비재 27% · 에너지 24%\n{{방어적}} 구성"  ← 핵심만 accent
```

**자가 점검**: `{{}}`가 3개 이상이면 → "진짜 핵심은 무엇인가?" 다시 판단하라.

#### 규칙 3: `{{}}`에 넣을 것과 넣지 말 것

| accent에 넣어야 할 것 | accent에 넣지 말 것 |
|---------------------|---------------------|
| 핵심 숫자 1개 (수익률, 금액, 기간) | 모든 숫자를 다 |
| 핵심 키워드 (결론, 반전) | 단순 라벨 (챕터 번호, 서수) |
| 감정 키워드 (함정, 마법, 위험) | 일반 동사/형용사 |

```
❌ headline: "핵심 {{5가지}} 정리합니다"  ← "5가지"는 라벨일 뿐
✅ headline: "핵심 5가지\n{{정리}}합니다"  ← 또는 accent 없이 깔끔하게

❌ headline: "CHAPTER {{3}} {{해외 배당 ETF}} 4대장"  ← 챕터 번호에 accent
✅ headline: "CHAPTER 3\n{{해외 배당 ETF}} 4대장"
```

#### 규칙 4: items가 있으면 itemIcons도 있어야 한다

items가 2개 이상이면 itemIcons를 **반드시** 함께 제공한다. 아이콘 없는 아이템 리스트는 시각적으로 밋밋하다.

```
❌ items: ["SCHD", "JEPI", "JEPQ"]
   itemIcons: []  ← ⛔ 아이콘 없음

✅ items: ["SCHD", "JEPI", "JEPQ"]
   itemIcons: ["TrendingUp", "DollarSign", "Zap"]
```

유일한 예외: items가 연도(`["2016", "2018", "2020"]`)나 순수 수치 데이터일 때는 아이콘 생략 가능.

#### 규칙 5: items가 1개뿐이면 items를 쓰지 않는다

항목이 1개뿐이면 headline에 통합하라. 단일 items는 화면에서 외롭다.

```
❌ items: ["배당 재투자 필수"]  ← 1개 → headline에 넣기
✅ headline: "{{배당 재투자}} 필수"
   items: []

예외: items[0]이 출처·각주 역할이면 허용 (예: items: ["2024년 기준"])
```

#### 규칙 6: emphasis="quote" 씬의 데이터 배치 (절대 규칙)

인용문 씬에서 `items[0]`은 **인용문 본문**이다. 화자 이름은 `source`에 넣는다.
렌더러는 `items[0]`을 인용문으로 표시하므로, 화자 이름만 넣으면 이름만 화면에 표시된다.

```
❌ emphasis: "quote"
   headline: "비용과 세금을 줄이는 것이 장기 수익률을 높이는 가장 확실한 방법"
   items: ["존 보글"]  ← ⛔ 화자 이름이 인용문 본문 위치에 들어감
   source: ""

✅ emphasis: "quote"
   headline: "비용과 세금을 줄이는 것이\n{{장기 수익률}}을 높이는 가장 확실한 방법"
   items: ["비용과 세금을 줄이는 것이 장기 수익률을 높이는 가장 확실한 방법"]
   source: "존 보글"

✅ emphasis: "quote" (items 생략 시 headline이 인용문으로 사용됨)
   headline: "세금은 투자 수익의\n{{가장 큰 적}}이다"
   items: []
   source: "워런 버핏"
```

**체크리스트**:
- `items[0]`에 인명만 있으면 → ⛔ 반드시 `source`로 이동
- `items[0]`에 인용문 본문이 있으면 → ✅
- `items`가 비어있으면 → headline이 인용문으로 폴백 → ✅

---

## 3. reveal — 정보 공개 패턴 (12종)

| reveal | 설명 | 적합한 상황 |
|--------|------|------------|
| `fade_in` | 전체가 한 번에 페이드인 | 단일 메시지, 인용문 |
| `stagger` | 항목이 순차적으로 등장 | 리스트, 타임라인, 비교 |
| `stagger_then_flash` | 순차 등장 → 전체 동시 강조 | 누적 효과 (9개 도시 등) |
| `cascade` | 위에서 아래로 폭포처럼 | 순위, 우선순위 |
| `count_up` | 숫자가 카운팅되며 증가 | 통계, 수치 강조 |
| `typewriter` | 글자가 하나씩 타이핑 | 핵심 문장, 결론 |
| `spotlight` | 어두운 화면에서 핵심만 밝아짐 | 인물, 핵심 개념 |
| `split_reveal` | 화면이 분할되며 양쪽 동시 공개 | A vs B, 대비 |
| `zoom_in` | 작은 것에서 크게 확대 | 핵심 수치, 디테일 |
| `build_up` | 요소가 쌓여가며 최종 형태 완성 | 프로세스, 구조 |
| `dramatic_pause` | 잠시 멈춤 후 핵심 공개 | 반전, 놀라운 사실 |
| `parallel` | 두 가지가 동시에 진행 | 대비, 동시 사건 |

---

## 4. emphasis — 핵심 강조 요소 (8종)

| emphasis | 설명 | 렌더링 효과 |
|----------|------|------------|
| `number` | 큰 숫자 강조 | 카운트업 + 스케일 확대 + accent 색상 |
| `keyword` | 핵심 단어 강조 | accent 색상 + 약간의 스케일 |
| `count` | 항목 수 강조 | 항목 등장 후 총 개수 빅넘버 |
| `contrast` | 대비/차이 강조 | 분할 레이아웃 + 색상 대비 |
| `sequence` | 순서/과정 강조 | 화살표/연결선 + 순차 등장 |
| `person` | 인물 강조 | 서클 이미지/배지 + 이름 |
| `quote` | 발언 강조 | 큰따옴표 + 발화자 |
| `none` | 특별한 강조 없음 | 균등한 정보 전달 |

---

## 5. mood — 감정적 톤 (7종)

| mood | 설명 | 시각적 표현 |
|------|------|------------|
| `dramatic` | 극적, 긴장 | 빠른 등장, 강한 accent, 큰 스케일 |
| `contemplative` | 사색적, 차분 | 느린 페이드, 낮은 대비, 여백 |
| `urgent` | 긴박, 위급 | 빠른 스태거, 경고색(danger), 타이트 |
| `triumphant` | 승리, 성취 | 스케일 확대, 밝은 accent, 카운트업 |
| `somber` | 엄숙, 슬픔 | 느린 페이드, 뮤트 색상, 여백 |
| `informative` | 정보 전달 | 균등 스태거, 중립 색상, 깔끔 |
| `suspense` | 서스펜스 | 느린 공개, 어두운 톤, 극적 일시정지 |

---

## 6.1 layout — 의도 기반 레이아웃 (24종)

**핵심 질문: "이 씬에서 시청자가 가장 기억해야 할 것이 무엇인가?"**

이 질문의 답이 레이아웃을 결정한다. 같은 데이터도 의도에 따라 다른 레이아웃이 선택된다.

### 기본 레이아웃 (11종, layout 미지정 시 자동 추론)
`headline_only`, `items_grid`, `items_list`, `person_card`, `counter`, `quote`, `split`, `bar`, `logo_grid`, `pie`, `line`

### 확장 레이아웃 (13종, layout 직접 지정 권장)

| layout | 의도 (언제 선택하나) | 필요 데이터 |
|--------|---------------------|-----------|
| `flow` | "A가 B를 거쳐 C가 된다" 인과/프로세스를 보여줄 때 | items (단계명) |
| `timeline` | "이 사건들이 순서대로 일어났다"를 보여줄 때 | items (시점) + descriptions (설명) |
| `metric_spotlight` | "이 숫자 하나가 핵심이다"를 극적으로 보여줄 때 | items[0] (라벨) + values[0] (수치) |
| `metric_wall` | "이 통계들을 한눈에 비교하라"를 보여줄 때 | items + values (2-4쌍) |
| `rank_list` | "누가 1등인가, 순위가 핵심이다"를 보여줄 때 | items + values (순위 정렬) |
| `comparison_table` | "여러 차원에서 비교하라"를 보여줄 때 | items + values |
| `before_after` | "전과 후가 이렇게 달라졌다"를 보여줄 때 | items[0]=before, items[1]=after |
| `icon_stat` | "이 아이콘이 대표하는 수치가 핵심이다" | itemIcons[0] + values[0] |
| `stacked_progress` | "각 항목의 점유율/진행도를 비교하라" | items + values |
| `card_carousel` | "이 정보 카드들을 하나씩 보여주고 싶다" | items + descriptions + itemIcons |
| `hero_with_context` | "핵심 메시지가 크고, 부연이 작게 따라온다" | headline + items (보조 정보) |
| `quote_portrait` | "인물 사진과 함께 인용문을 보여줄 때" | images[0] + items[0] (인용문) |
| `annotated_chart` | "차트에 주석을 달아 특정 부분을 설명할 때" | items + values + annotations[] |

### layout 사용 예시

```json
// "기업 7개의 순위가 핵심" → rank_list
{
  "creative": {
    "concept": "7대 기업을 시가총액 순으로 순위 매겨 보여준다",
    "layout": "rank_list",
    "reveal": "cascade",
    "emphasis": "number",
    "headline": "시가총액 {{TOP 7}}",
    "mood": "informative"
  },
  "items": ["Apple", "Microsoft", "NVIDIA", "Amazon", "Meta", "Alphabet", "Tesla"],
  "values": [3200, 2800, 2600, 2100, 1500, 1400, 800],
  "unit": "B$"
}

// "3단계 투자 프로세스를 보여주고 싶다" → flow
{
  "creative": {
    "concept": "계좌 개설 → 종목 선택 → 적립식 투자의 3단계를 순서대로",
    "layout": "flow",
    "reveal": "build_up",
    "emphasis": "sequence",
    "headline": "{{3단계}}\n투자 시작",
    "mood": "informative"
  },
  "items": ["계좌 개설", "ETF 종목 선택", "적립식 투자 시작"]
}

// "변화 전후를 극적으로 대비" → before_after
{
  "creative": {
    "concept": "10년 전과 지금의 S&P500 수준을 극적으로 비교",
    "layout": "before_after",
    "reveal": "split_reveal",
    "emphasis": "contrast",
    "headline": "{{10년 전}} vs {{지금}}",
    "mood": "dramatic"
  },
  "items": ["2,000", "5,800"],
  "values": [2000, 5800],
  "unit": "pt"
}
```

### layout 미지정 시

`layout` 필드가 없으면 렌더러가 emphasis/reveal/데이터 구조로 자동 추론한다.
기본 11개 레이아웃은 자동 추론이 잘 작동하므로 `layout` 생략 가능.
확장 13개 레이아웃은 자동 추론이 불가능하므로 **반드시 `layout`을 직접 지정**해야 한다.
