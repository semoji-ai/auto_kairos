# Chart Mapping 스킬

> **상위 스킬**: `shared/asset-advisory` — 차트뿐 아니라 아이콘/국기/로고/이미지까지 포괄하는 에셋 추천 규칙.
> 이 문서는 차트 관련 세부 매핑 규칙에 집중합니다.

## 목적
씬의 나레이션과 데이터를 분석하여 차트(파이/라인/바) 적용이 적합한 씬을 식별하고, 정확한 데이터를 매핑하는 규칙.

---

## 1. 차트 후보 씬 식별 기준

### Pie Chart (원형 그래프)
- **키워드**: "비중", "비율", "구성", "차지", "점유율", "%"
- **데이터 패턴**: 항목별 비율/퍼센트 → 합계 100% 또는 전체 대비 비중
- **적합 조건**: items 3~8개 + values가 비율(%) 데이터
- **예시**: "섹터별 비중", "기업별 점유율", "자산 배분 비율"

### Line Chart (꺾은선 그래프)
- **키워드**: "추이", "변화", "성장", "기간", "년간", "수익률", "역사"
- **데이터 패턴**: 시간 순서 데이터 (연도, 기간) + 수치 변화
- **적합 조건**: items가 시간축 레이블 + values가 시계열 수치
- **예시**: "97년간 수익률", "연도별 성장", "투자 시뮬레이션"

### Bar Chart (막대 그래프) — 기존 기본값
- **키워드**: "비교", "순위", "top", "대비"
- **데이터 패턴**: 카테고리별 절대값 비교
- **적합 조건**: items 3개 이상 + values가 절대값
- **예시**: "자산별 수익률 비교", "국가별 GDP"

### Logo Grid (로고 그리드)
- **키워드**: "기업", "브랜드", "회사"
- **데이터 패턴**: 기업명 + 비율/수치
- **적합 조건**: items가 알려진 기업명이고 로고 표시가 의미있는 경우
- **예시**: "Magnificent 7 기업", "FAANG 기업"

---

## 2. research_report.json 데이터 매핑 규칙

### 데이터 검색 순서
1. research_report.json의 관련 섹션에서 정확한 수치 검색
2. 나레이션에 언급된 수치 추출
3. 공인 출처(IMF, World Bank, S&P Global 등)의 데이터 우선

### 매핑 검증
- 항목(items)과 값(values) 개수 일치 확인
- 파이 차트: 합계가 논리적으로 맞는지 검증 (100%에 근사하거나 부분합)
- 라인 차트: 시간 순서 정렬 확인
- 값의 단위(unit) 명시 필수

---

## 3. chartConfig 스키마

```json
{
  "chartConfig": {
    "type": "pie" | "line" | "bar",

    // pie 전용
    "maxSlices": 8,         // 최대 슬라이스 수 (기본 8)
    "highlightIndex": 0,    // 강조할 슬라이스 인덱스
    "showTotal": true,      // 중앙에 합계 표시

    // line 전용
    "showGrid": true,       // 그리드 라인 표시
    "showDots": true,       // 데이터 포인트 도트
    "showArea": true        // 면적 그라데이션
  }
}
```

### displayMode 스키마
```json
{
  "displayMode": "logo_grid" | "pie_chart" | "line_chart",
  "logoMap": {              // logo_grid 전용
    "Apple": "Apple",       // item명 → Simple Icons 키
    "Microsoft": "Microsoft"
  }
}
```

---

## 4. 차트 추천 판단 프로세스

1. **나레이션 분석**: 키워드 매칭으로 차트 후보 식별
2. **데이터 구조 확인**: items/values 쌍이 차트 요건 충족하는지 검증
3. **데이터 검색**: research_report.json에서 정확한 수치 확보
4. **차트 타입 결정**: 데이터 특성에 맞는 차트 선택
5. **chartConfig 생성**: 해당 차트에 맞는 설정 작성
6. **creative 필드에 반영**: `displayMode` 또는 `chartConfig.type` 설정

### 적용 예시

```json
// Scene 9: 섹터별 비중 → pie_chart
{
  "creative": {
    "chartConfig": { "type": "pie", "maxSlices": 6, "showTotal": true },
    ...
  },
  "items": ["정보기술", "금융", "헬스케어", "임의소비재", "통신", "기타"],
  "values": [32, 13, 12, 10, 9, 24],
  "unit": "%"
}

// Scene 14: 97년간 수익률 → line_chart
{
  "creative": {
    "chartConfig": { "type": "line", "showGrid": true, "showDots": true, "showArea": true },
    ...
  },
  "items": ["1926", "1950", "1970", "1990", "2000", "2010", "2023"],
  "values": [100, 1200, 3500, 15000, 35000, 45000, 120000],
  "unit": "$"
}
```
