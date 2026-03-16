---
name: asset-advisory-perspectives
description: Reference for the 4 advisory perspectives (chart, symbol, image, layout) used in asset advisory deliberation
invocation: agent-only
---

## 2. Step 2 상세: 4개 관점 독립 제안

### 📊 차트 관점

이 씬의 데이터가 차트로 표현될 때 **정보 전달력이 높아지는가?** 판단한다.

**핵심: 키워드 매칭이 아니라 "이 데이터를 차트로 보여주면 시청자가 더 잘 이해하는가?" 질문**

| 차트 | 적합한 상황 | 부적합한 상황 |
|------|------------|-------------|
| **pie** | 전체 대비 비중/구성을 한눈에 보여야 할 때 | 항목별 절대값 비교가 핵심일 때 |
| **line** | 시간에 따른 변화/추세가 핵심일 때 | 단순 수치 나열일 때 |
| **bar** | 카테고리별 절대값 비교가 핵심일 때 | 비율/구성이 핵심일 때 |
| **logo_grid** | 기업 브랜드 자체가 핵심 메시지일 때 | 기업의 수치 비교가 핵심일 때 (→ bar가 나을 수 있음) |

**판단 질문:**
- "이 나레이션에서 시청자가 가장 기억해야 할 것은?" → 수치의 크기 차이? 비중? 추세? 기업 자체?
- "차트 없이 숫자만 나열하면 전달력이 떨어지는가?" → Yes면 차트 추천
- "이미 creative.emphasis가 number/count인데, 차트가 그 강조를 약화시키지 않는가?"
- "기업 7개를 나열하지만, 핵심은 '이 기업들이 전체의 30%를 차지한다'인가(→ pie), '이 기업들의 존재감'인가(→ logo_grid)?"

**제안 포맷:**
```
차트 관점: pie 추천 (적합도 높음)
근거: 섹터별 비중 데이터가 있고, 전체 대비 비율을 한눈에 보여주는 것이 핵심
chartConfig: { type: "pie", maxSlices: 6, showTotal: true }
items/values 재구성: research_report에서 정확한 수치 확보
```

### chartConfig 스키마

```json
// pie
{ "type": "pie", "maxSlices": 8, "highlightIndex": 0, "showTotal": true }

// line
{ "type": "line", "showGrid": true, "showDots": true, "showArea": true }

// bar — 기본값이므로 chartConfig 불필요 (values 있으면 자동 감지)
```

### 로고 그리드 스키마

```json
{
  "displayMode": "logo_grid",
  "logoMap": {
    "Apple": "Apple",
    "Microsoft": "Microsoft",
    "삼성전자": "Samsung"
  }
}
```

### 데이터 소스 규칙

- **필수**: research_report.json 또는 공인 출처에서 확인된 수치만 사용
- **금지**: 나레이션에 없는 데이터 임의 추가
- items/values 개수 일치 검증
- 파이: 합계 100% 근사 검증
- 라인: 시간 순서 정렬 확인

---

### 🏷️ 심볼 관점 (아이콘 / 국기 / 로고)

items의 각 항목을 **시각적 심볼**로 어떻게 표현하면 가장 효과적인지 판단한다.

**3가지 심볼 유형 중 최적 선택:**

| 심볼 | 적합한 상황 | 예시 |
|------|------------|------|
| **아이콘** (Lucide) | 추상 개념, 행동, 카테고리 | 성장→TrendingUp, 보호→Shield |
| **국기** (ISO 2자리) | 국가가 비교의 주체일 때 | 미국→US, 한국→KR |
| **로고** (Simple Icons) | 기업 브랜드 자체가 핵심일 때 | Apple→Apple |

**판단 질문:**
- "이 항목을 아이콘으로 보여주면 즉시 인식 가능한가?"
- "국가명이 있지만, 국가 비교가 핵심인가 vs 단순 언급인가?"
- "기업명이 있지만, 브랜드 인지가 핵심인가 vs 수치 비교가 핵심인가?"
- "차트 관점에서 bar chart를 제안했다면, 아이콘은 보조 역할로 공존 가능한가?"

**아이콘 매핑 레퍼런스:**

| 키워드 패턴 | 아이콘 | 예시 |
|-------------|--------|------|
| 성장, 상승, 수익 | `TrendingUp` | "연 10% 성장" |
| 하락, 리스크, 위험, 폭락 | `TrendingDown` | "최대 낙폭" |
| 보안, 안전, 보호, 방어 | `Shield` | "원금 보호" |
| 돈, 투자, 자산, 달러, 원 | `DollarSign` | "1만 원 투자" |
| 시간, 기간, 년, 월 | `Clock` | "20년 장기" |
| 기업, 회사, 사업 | `Building` | "대기업 500곳" |
| 사람, 인물, 투자자 | `User` | "개인 투자자" |
| 세계, 글로벌, 국가 | `Globe` | "세계 경제" |
| 경고, 주의, 위기 | `AlertTriangle` | "버블 경고" |
| 성공, 달성, 승리 | `CheckCircle` | "목표 달성" |
| 절세, 세금, 공제 | `Receipt` | "세액공제" |
| 계좌, 저축, 은행 | `Landmark` | "연금저축 계좌" |
| 학습, 공부, 법칙 | `BookOpen` | "72의 법칙" |
| 비교, 대결, vs | `Swords` | "일시불 vs 적립식" |
| 목표, 전략, 계획 | `Target` | "투자 전략" |
| 차트, 데이터, 통계 | `BarChart3` | "수익률 데이터" |

**국기 코드 레퍼런스:**

| 국가명 패턴 | countryCode |
|-------------|-------------|
| 미국, USA | `US` |
| 한국, 대한민국 | `KR` |
| 일본, Japan | `JP` |
| 중국, China | `CN` |
| 영국, UK | `GB` |
| 독일, Germany | `DE` |
| 프랑스, France | `FR` |
| 호주, Australia | `AU` |
| 캐나다, Canada | `CA` |
| 인도, India | `IN` |

**로고 매핑 레퍼런스 (Simple Icons):**

| 기업명 | Simple Icons 키 |
|--------|----------------|
| Apple | `Apple` |
| Microsoft | `Microsoft` |
| Google, Alphabet | `Google` |
| Amazon | `Amazon` |
| Meta | `Meta` |
| NVIDIA | `Nvidia` |
| Tesla | `Tesla` |
| Samsung, 삼성 | `Samsung` |
| Netflix | `Netflix` |
| Berkshire | `Berkshirehathaway` |

**적용 규칙:**
- 한 씬 최대 6개 심볼
- 매핑 불가능한 항목은 빈 문자열 "" (CircleBadge 폴백)
- 같은 항목에 아이콘+국기 동시 → 해당 씬에서 더 효과적인 쪽 선택

**제안 포맷:**
```
심볼 관점: 국기 추천 (적합도 높음)
근거: 3개국 수익률 비교가 핵심이고, 국기가 즉각적 국가 인식을 돕는다
itemFlags: ["US", "GB", "AU"]
차트와 공존 가능: bar chart의 각 막대 위에 국기 배지로 병용 가능
```

---

### 🖼️ 이미지 관점

이 씬에 이미지를 추가하면 **시각적 임팩트가 높아지는가?** 판단하고, **이미지의 역할(배경/에셋/주인공)**을 결정한다.

**imageAsset 배치 유형 (6종):**

| 활용 방식 | placement | 설명 | opacity |
|-----------|-----------|------|---------|
| **이미지가 메시지 그 자체** | `fullscreen` | 텍스트 최소/없음, 이미지로만 전달 | 0.8~1.0 |
| **배경 분위기** | `background` | 텍스트/차트 뒤에 분위기를 깔아줌 | 0.10~0.50 |
| **중앙 에셋** | `center` | 이미지가 화면 중앙, 텍스트는 상/하단 | 0.7~1.0 |
| **좌측 에셋** | `left` | 인물/오브젝트를 왼쪽에 배치, 텍스트 오른쪽 | 0.7~1.0 |
| **우측 에셋** | `right` | 인물/오브젝트를 오른쪽에 배치, 텍스트 왼쪽 | 0.7~1.0 |
| **아이템별 인라인** | `inline` | items와 1:1 매핑 (itemImages: true) | 1.0 |

**fullscreen 판단 기준 — 언제 이미지가 주인공인가?**

| 조건 | fullscreen 적합 | 예시 |
|------|----------------|------|
| 나레이션이 시각적 대상을 묘사 ("이 장면을 보세요") | ✅ 높음 | 전쟁 현장, 역사적 순간 |
| 감정 전달이 핵심 (공포, 희망, 경외) | ✅ 높음 | 폭락 장면, 일출, 눈물 |
| 전환/브릿지 씬 (챕터 전환점) | ✅ 높음 | 분위기 전환 |
| 수치/데이터가 핵심 | ❌ 낮음 | → background/left/right |
| items가 3개 이상 | ❌ 낮음 | → background + items |
| 차트가 이미 있음 | ❌ 낮음 | → background(낮은 opacity) |

**inline 판단 기준 — 아이템마다 이미지가 필요한가?**

| 조건 | inline 적합 | 예시 |
|------|------------|------|
| 각 아이템이 고유한 시각적 대상 | ✅ 높음 | ETF 상품 3종 비교 (각각 로고) |
| 인물 카드 나열 | ✅ 높음 | 투자 대가 3인 (각각 초상) |
| 아이템이 추상 개념 | ❌ 낮음 | → 아이콘으로 대체 |

**소스 판단:**

| 조건 | source | 예시 |
|------|--------|------|
| 실존 인물 | `wikimedia` | 워런 버핏 초상화 |
| 캐릭터 (character_plan 참조) | `character` | 캐릭터 일러스트 |
| 추상 개념, 분위기 | `generate` | 복리 성장 이미지 |
| 실물 사진 (건물, 제품) | `search` | NYSE 빌딩 |

**판단 질문:**
- "이 씬이 텍스트만으로 충분한가, 이미지가 있으면 몰입감이 올라가는가?"
- "이미지가 **메시지 그 자체**인가(→ fullscreen), **분위기 보조**인가(→ background), **핵심 에셋**인가(→ left/right/center)?"
- "나레이션이 시각적 대상을 직접 묘사하는가? → fullscreen 고려"
- "각 아이템마다 고유 이미지가 필요한가? → inline (itemImages: true)"
- "차트 관점에서 pie를 제안했는데, 배경이미지가 차트의 가독성을 해치는가? → opacity를 낮추면 공존 가능한가?"
- "인물이 언급되는데, 인물 사진이 감정적 연결을 강화하는가?"
- "이미 아이콘이 충분한 시각 요소를 제공하는 씬인가?"

**핵심 원칙: 이미지 없는 씬은 시각적으로 지루하다. 다른 에셋과 공존 가능하면 적극 추가하라. 이미지가 메시지의 핵심이면 fullscreen으로 과감하게.**

**제안 포맷:**
```
이미지 관점: fullscreen 이미지 추천 (적합도 높음)
근거: 나레이션이 "이 역사적 순간을 보세요"로 시각 대상을 직접 묘사. 텍스트 최소화, 이미지로 감정 전달.
source: "search", query: "1987 black monday stock exchange panic"
placement: "fullscreen", opacity: 0.9
layout 제안: headline_only (최소 텍스트 오버레이)
```

```
이미지 관점: background 이미지 추천 (적합도 중간)
근거: 차트가 주 요소이지만, 주식시장 분위기 이미지가 배경에 깔리면 몰입감 상승
source: "search", query: "stock market trading floor"
placement: "background", opacity: 0.15
차트와 공존 시: opacity 0.12~0.18 권장
```

```
이미지 관점: inline 이미지 추천 (적합도 높음)
근거: 투자 대가 3인을 각각 인물 사진과 함께 보여주면 인물 인식 극대화
source: "wikimedia", queries: ["워런 버핏", "잭 보글", "찰리 멍거"]
placement: "inline", itemImages: true
```

---

### 📐 레이아웃 관점

다른 관점들의 제안을 종합하여 **화면 공간 배분과 가독성**을 검증하고, **최종 `creative.layout` 값을 확정**한다.

**핵심 역할**: 📐 레이아웃 관점이 `creative.layout` 필드를 결정한다. 다른 3개 관점(차트/심볼/이미지)의 제안을 종합하여, 씬의 의도에 가장 부합하는 레이아웃 타입을 선택한다.

**layout 결정 질문:**
- **"이 씬에서 시청자가 가장 기억해야 할 것은 무엇인가?"**
- "순위가 핵심인가(→ rank_list), 비중이 핵심인가(→ pie), 존재감이 핵심인가(→ logo_grid)?"
- "프로세스/순서가 핵심인가(→ flow/timeline), 변화가 핵심인가(→ before_after)?"
- "데이터 밀도가 높은가(→ metric_wall/comparison_table), 단일 핵심인가(→ metric_spotlight/icon_stat)?"
- "제안된 에셋들을 모두 넣으면 화면이 과밀한가?"
- "텍스트(headline, items)가 이미지/차트에 가려지지 않는가?"

**사용 가능한 layout 타입 (24종):**
- 기본 11: `headline_only`, `items_grid`, `items_list`, `person_card`, `counter`, `quote`, `split`, `bar`, `logo_grid`, `pie`, `line`
- 확장 13: `flow`, `timeline`, `metric_spotlight`, `metric_wall`, `rank_list`, `comparison_table`, `before_after`, `icon_stat`, `stacked_progress`, `card_carousel`, `hero_with_context`, `quote_portrait`, `annotated_chart`

**기본 11개**는 `layout` 생략 가능 (렌더러가 자동 추론). **확장 13개**는 반드시 `layout` 직접 지정.

**제안 포맷:**
```
레이아웃 관점: layout="rank_list" 확정
근거: 시청자가 기억해야 할 것은 "순위 차이"이지 절대값이 아님.
      bar chart도 가능하지만, 순위를 시각적으로 강조하는 rank_list가 더 효과적.
      RankBadge의 금/은/동 색상이 순위 인식을 극대화.
opacity: 배경이미지 0.12 (차트가 주 요소)
공존 가능: rank_list + background image(0.12)
```

**opacity 가이드라인 (에셋 공존 시):**

| 조합 | 배경 이미지 opacity |
|------|-------------------|
| 차트(주) + 배경이미지(보조) | 0.10~0.18 |
| 로고그리드(주) + 배경이미지(보조) | 0.10~0.18 |
| 아이콘 리스트(주) + 배경이미지(보조) | 0.25~0.40 |
| 텍스트만(주) + 배경이미지(보조) | 0.30~0.50 |
| 사이드 이미지 + 텍스트 | opacity 0.7~1.0, 반대쪽에 텍스트 |

**items 밀도별 공간 배분:**

| items 수 | 텍스트 공간 | 이미지 공간 |
|----------|-----------|-----------|
| 0개 (텍스트 없음) | 없음 → 이미지가 주인공 | **fullscreen** (opacity 0.8~1.0) |
| 0~2개 | 적음 → 이미지에 여유 공간 | left/right/center 또는 background(높은 opacity) |
| 3~4개 (각각 고유 대상) | 중간 | **inline** (itemImages) 또는 background |
| 3~4개 (추상 개념) | 중간 | background(중간 opacity) 또는 사이드 |
| 5~6개 | 많음 → 이미지는 보조 | background(낮은 opacity)만 |
| 7개+ | 매우 많음 | background(최소 opacity) 또는 생략 |
