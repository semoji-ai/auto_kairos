# Asset Advisory 스킬

## 목적
씬의 나레이션, 데이터 구조, research_report.json을 분석하여 **텍스트 외 시각 에셋**(차트, 아이콘, 국기, 로고, 이미지, 배치)을 자동으로 추천하고 scene_specs.json에 반영하는 규칙.

> 이 스킬은 visual-composer의 **Phase 2.5**에서 실행된다.
> Phase 2 (Creative Direction)에서 설계된 creative 필드를 **보강**하는 역할이며, 기존 creative 필드를 덮어쓰지 않는다.

---

## 1. 실행 순서

```
Phase 2 출력 (scene_specs.json)
    ↓
[1단계] 씬 스캔 — 모든 씬을 순회하며 에셋 후보 식별
[2단계] 차트 추천 — 데이터 패턴 분석 → chartConfig/displayMode
[3단계] 아이콘 추천 — items 키워드 → itemIcons 매핑
[4단계] 국기 추천 — 국가명 감지 → itemFlags 매핑
[5단계] 로고 추천 — 기업명 감지 → logoMap 매핑
[6단계] 이미지 추천 — 씬 내용 → imageAsset 생성/보강
[7단계] 배치 결정 — 데이터 밀도에 따른 placement 최적화
[8단계] 검증 — 에셋 과잉/충돌 검사
    ↓
Phase 3 입력 (scene_specs.json 업데이트)
```

---

## 2. 차트 추천

### 판단 기준

| 차트 | 키워드 | 데이터 패턴 | 조건 |
|------|--------|-------------|------|
| **pie** | 비중, 비율, 구성, 차지, 점유율, % | 항목별 비율 → 합계 ~100% | items 3~8개 + values가 % |
| **line** | 추이, 변화, 성장, 기간, 년간, 수익률, 역사, 시뮬레이션 | 시간축 + 수치 변화 | items가 시간 레이블 |
| **bar** | 비교, 순위, top, 대비, 확률 | 카테고리별 절대값 | items 3개+ |
| **logo_grid** | 기업, 브랜드, 회사, 종목 | 기업명 + 수치 | items가 알려진 기업명 |

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
- **필수**: research_report.json 또는 공인 출처(S&P Global, IMF 등)에서 확인된 수치만 사용
- **금지**: 나레이션에 없는 데이터 임의 추가
- items/values 개수 일치 검증
- 파이: 합계 100% 근사 검증
- 라인: 시간 순서 정렬 확인

---

## 3. 아이콘 추천

### 매핑 규칙

items의 각 항목 텍스트를 분석하여 적합한 Lucide 아이콘을 `itemIcons` 배열로 설정한다.

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

### 적용 규칙

- **items 3개 이상**일 때만 아이콘 추천 (2개 이하는 시각적 효과 미미)
- **한 씬 최대 6개** 아이콘 (초과 시 시각적 소음)
- **차트 씬**(pie/line/bar)에는 아이콘 추가하지 않음 (차트가 주 시각 요소)
- **logo_grid 씬**에는 아이콘 대신 로고 사용
- 매핑 불가능한 항목은 아이콘 없이 남겨둠 (빈 문자열 "")

### scene_specs 반영

```json
{
  "visualization": {
    "items": ["원화 매매", "연금저축 계좌 활용", "소액 투자"],
    "itemIcons": ["DollarSign", "Landmark", "Coins"]
  }
}
```

---

## 4. 국기 추천

### 감지 규칙

나레이션 또는 items에 국가명이 포함되면 해당 항목에 `itemFlags`를 설정한다.

| 국가명 패턴 | countryCode |
|-------------|-------------|
| 미국, 미합중국, USA, US | `US` |
| 한국, 대한민국, Korea | `KR` |
| 일본, Japan | `JP` |
| 중국, China | `CN` |
| 영국, UK, Britain | `GB` |
| 독일, Germany | `DE` |
| 프랑스, France | `FR` |
| 호주, Australia | `AU` |
| 캐나다, Canada | `CA` |
| 인도, India | `IN` |
| 브라질, Brazil | `BR` |
| 러시아, Russia | `RU` |
| 대만, Taiwan | `TW` |

### 적용 규칙

- **국가 비교 씬**에서만 적용 (국가가 items의 주체일 때)
- 단순 언급("미국 시장")은 국기 불필요
- items에 국가명이 직접 포함된 경우만 적용
- 아이콘과 국기가 동시에 필요한 경우 **국기 우선** (itemFlags가 있으면 해당 항목의 itemIcons는 무시됨)

### scene_specs 반영

```json
{
  "visualization": {
    "items": ["미국", "영국", "호주"],
    "itemFlags": ["US", "GB", "AU"]
  }
}
```

---

## 5. 로고 추천

### 감지 규칙

items에 알려진 기업/브랜드명이 포함되면 `logoMap`을 설정하고 `displayMode: "logo_grid"`를 적용한다.

### Simple Icons 매핑 (자주 사용)

| 기업명 | Simple Icons 키 |
|--------|----------------|
| Apple | `Apple` |
| Microsoft | `Microsoft` |
| Google, Alphabet | `Google` |
| Amazon | `Amazon` |
| Meta, Facebook | `Meta` |
| NVIDIA | `Nvidia` |
| Tesla | `Tesla` |
| Samsung, 삼성 | `Samsung` |
| Netflix | `Netflix` |
| Berkshire | `Berkshirehathaway` |
| Vanguard | `Vanguard` |

### 적용 규칙

- items의 **과반수 이상**이 기업명일 때만 logo_grid 적용
- 기업명이 1~2개만 있으면 로고 추천 안 함 (아이콘으로 대체)
- logoMap에 매핑 불가능한 기업은 빈 값 → CircleBadge 폴백
- `creative.displayMode = "logo_grid"` + `creative.logoMap = {...}` 설정

---

## 6. 이미지 추천

### imageAsset 판단 기준

| 조건 | source | 예시 |
|------|--------|------|
| **실존 인물** 언급 (워런 버핏, 잭 보글 등) | `wikimedia` | 인물 초상화 |
| **캐릭터** 등장 예정 (character_plan 참조) | `character` | 캐릭터 일러스트 |
| **추상 개념** 시각화 필요 | `generate` | 교실, 저금통, 주식 차트 |
| **실물 사진** 필요 (건물, 도시, 제품) | `search` | NYSE 빌딩, 월스트리트 |

### 추천 안 하는 경우

- **차트 씬** (pie/line/bar) — 차트가 주 시각 요소, 이미지가 방해
- **데이터 밀도 높은 씬** (items 5개+, values 있음) — 텍스트+이미지 동시 표시 시 가독성 저하
- **split_reveal 씬** — 좌우 분할 자체가 시각 요소
- **이미 mapScene이 있는 씬** — 지도와 이미지 중복

### 이미지가 필요한 씬 (적극 추천)

- **인물 중심 씬** — 나레이션에 특정 인물의 말/행동 언급
- **텍스트만 있는 씬** (items 없음, values 없음) — 시각적 빈약 방지
- **감정적 씬** (mood: dramatic, triumphant) — 분위기 강화

### placement 결정

| 데이터 밀도 | placement | opacity |
|-------------|-----------|---------|
| items 0~2개, values 없음 | `background` | 0.3~0.5 |
| items 3~4개 | `background` | 0.25~0.35 |
| items 5개+ | **이미지 추천 안 함** | — |
| 인물 초상 | `left` 또는 `right` | 0.8~1.0 |

### scene_specs 반영

```json
{
  "imageAsset": {
    "source": "generate",
    "query": "quirky cartoon style, cute piggy bank with coins, savings concept",
    "placement": "background",
    "opacity": 0.35
  }
}
```

---

## 7. 배치 최적화

### 기존 imageAsset의 placement 검증

Phase 2에서 이미 imageAsset이 설정된 씬의 placement를 데이터 밀도에 맞게 재검증한다.

| 상황 | 조정 |
|------|------|
| items 5개+ + placement="background" | opacity를 0.2~0.25로 하향 또는 이미지 제거 |
| items 0~1개 + placement="background" | 적절 (유지) |
| 인물 이미지 + items 3개+ | placement를 `left`/`right`로 변경 (텍스트 공간 확보) |
| 차트 씬 + imageAsset 존재 | imageAsset 제거 추천 |

### 전체 영상 밸런스 검증

- 연속 3개 이상 이미지 없는 씬 → 중간에 이미지 추가 추천
- 연속 3개 이상 이미지 있는 씬 → 시각적 피로, 일부 제거 검토
- 전체 씬의 40~60%에 이미지/차트/로고 등 시각 에셋이 있는 것이 이상적

---

## 8. 에셋 충돌 검사

### 우선순위 (한 씬에 복수 에셋 충돌 시)

```
1. 차트 (pie/line/bar) — 최우선, 다른 에셋과 공존 불가
2. logo_grid — 차트 다음, 이미지 배경과 공존 불가
3. 이미지 배경 (background) — 텍스트/아이콘과 공존 가능
4. 이미지 사이드 (left/right) — 텍스트와 공존 가능
5. 아이콘 (itemIcons) — 모든 레이아웃과 공존 가능
6. 국기 (itemFlags) — 아이콘 대신 사용, 공존 불가
```

### 금지 조합

- ❌ 차트 + imageAsset (background)
- ❌ logo_grid + imageAsset (background)
- ❌ itemIcons[i] + itemFlags[i] (같은 항목에 양쪽 불가)
- ❌ mapScene + imageAsset

### 허용 조합

- ✅ 차트 + itemIcons (차트 외 영역에 아이콘)
- ✅ 이미지 배경 + itemIcons
- ✅ 이미지 사이드 + itemIcons
- ✅ split_reveal + itemIcons

---

## 9. 적용 예시

### 예시 1: 섹터별 비중 씬
```
나레이션: "정보기술이 32%로 가장 크고, 금융 13%, 헬스케어 12%..."
```
→ **pie_chart** 추천 + imageAsset 제거
```json
{
  "creative": {
    "chartConfig": { "type": "pie", "maxSlices": 6, "showTotal": true }
  },
  "items": ["정보기술", "금융", "헬스케어", "임의소비재", "통신", "기타"],
  "values": [32, 13, 12, 10, 9, 24],
  "unit": "%",
  "imageAsset": null
}
```

### 예시 2: Magnificent 7 기업 씬
```
나레이션: "Apple, Microsoft, NVIDIA, Amazon, Meta, Alphabet, Tesla"
```
→ **logo_grid** 추천
```json
{
  "creative": {
    "displayMode": "logo_grid",
    "logoMap": {
      "Apple": "Apple", "Microsoft": "Microsoft", "NVIDIA": "Nvidia",
      "Amazon": "Amazon", "Meta": "Meta", "Alphabet": "Google", "Tesla": "Tesla"
    }
  },
  "imageAsset": null
}
```

### 예시 3: 국내 ETF 장점 씬
```
나레이션: "원화로 매매, 연금저축 계좌, 1만 원 소액 투자"
```
→ **itemIcons** 추천 + 배경 이미지 유지
```json
{
  "items": ["원화 매매", "연금저축 계좌 활용", "소액 투자"],
  "itemIcons": ["DollarSign", "Landmark", "Coins"],
  "imageAsset": {
    "source": "generate",
    "query": "quirky cartoon style, person investing on smartphone",
    "placement": "background",
    "opacity": 0.3
  }
}
```

### 예시 4: 미국/영국/호주 비교 씬
```
나레이션: "미국, 영국, 호주 세 나라 전부..."
```
→ **itemFlags** 추천
```json
{
  "items": ["미국", "영국", "호주"],
  "itemFlags": ["US", "GB", "AU"]
}
```

### 예시 5: 연 10% 복리 성장 씬
```
나레이션: "$10,000이 30년 후 $174,494가 됩니다"
```
→ **line_chart** 추천 + imageAsset 제거
```json
{
  "creative": {
    "chartConfig": { "type": "line", "showGrid": true, "showDots": true, "showArea": true }
  },
  "items": ["시작", "5년", "10년", "15년", "20년", "25년", "30년"],
  "values": [10000, 16105, 25937, 41772, 67275, 108347, 174494],
  "unit": "$",
  "imageAsset": null
}
```
