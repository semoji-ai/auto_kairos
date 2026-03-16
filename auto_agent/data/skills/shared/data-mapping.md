---
name: data-mapping
description: Use when extracting structured data (items, values, units) from narration text for visualization
---

# Data Mapping

시각화 씬에 리서치 기반 정확한 수치/통계를 보강하는 규칙을 정의합니다.
research_report.json에서 scene_specs.json으로의 데이터 매핑 규칙을 포함합니다.

**참조 에이전트**: visual-composer, qa-reviewer

---

## 1. 보강 대상 씬 타입

| 씬 타입 | 보강 항목 |
|---------|----------|
| bar_chart | items, values, unit, source 정확도 검증/보정 |
| line_chart | items, values, unit 정밀도 확인 |
| pie_chart | values 합계 100% 검증, 반올림 보정 |
| timeline | 날짜/사건 정확도 교차 검증 |
| table_view | 셀 데이터 정확도 |
| icon_stat | value, trend 수치 검증 |
| text_highlight | variant=countup일 때 수치 검증 |

---

## 2. 수치 정확도

```
research_report.json의 statistics에서 매칭:
  ├─ metric명이 일치하는 데이터 찾기
  ├─ value, unit 검증
  ├─ source(출처) 명기
  └─ year(연도) 확인

매칭 실패 시:
  ├─ notes에 "DATA_UNVERIFIED" 태그 추가
  └─ 가용한 유사 데이터로 대체 제안
```

---

## 3. 단위 표준화

```
큰 수치:
  1,000,000,000 → "10억" (한국어 단위)
  $15B → "150억$" 또는 "150억 달러"

백분율:
  0.142857... → "14.3%" (소수점 1자리)

연도:
  "2024-Q3" → "2024년 3분기"
```

---

## 4. 출처(source) 필수화

모든 데이터 시각화 씬에 source 필드가 없으면 추가:
```json
"source": "출처명 (연도)"
```

research_report.json의 sources 배열에서 매칭.

---

## 5. 파이 차트 특별 규칙

```
values 합계 검증:
  합계 == 100 → OK
  합계 != 100 → 반올림 조정 (가장 큰 항목에서 보정)

항목 수 제한:
  최대 6개. 초과 시 하위 항목 "기타"로 통합
```

---

## 6. 보강 결과 기록

각 보강된 씬에 `enrichment` 필드 추가:

```json
{
  "enrichment": {
    "status": "verified | adjusted | unverified",
    "original_values": [20, 45, 90],
    "corrected_values": [22, 47, 95],
    "source_matched": "src_003",
    "notes": "2024 연도 기준으로 보정"
  }
}
```

---

## 주의사항

- 원본 나레이션 텍스트는 절대 수정하지 않는다
- 수치를 찾을 수 없으면 원본 값 유지 + unverified 표기
- research_report.json에 없는 수치를 임의로 만들지 않는다
- 보강 작업은 데이터 씬에만 적용 (title_card, quote_card 등은 건드리지 않음)
