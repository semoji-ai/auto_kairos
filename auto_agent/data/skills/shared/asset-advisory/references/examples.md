---
name: asset-advisory-examples
description: Reference examples showing multi-perspective asset advisory decisions for various scene types
invocation: agent-only
---

## 6. 적용 예시

### 예시 1: 섹터별 비중 씬

```
나레이션: "정보기술이 32%로 가장 크고, 금융 13%, 헬스케어 12%..."
```

**심의 과정:**
- 📊 차트: pie 추천 — 비중/구성 데이터, 전체 대비 파악이 핵심
- 🏷️ 심볼: 아이콘 가능하나, pie 슬라이스에 레이블로 충분
- 🖼️ 이미지: 차트가 주 요소, 배경이미지 보조 가능 (opacity 0.15)
- 📐 레이아웃: pie + 배경(0.15) 공존 가능

**최종:**
```json
{
  "creative": {
    "chartConfig": { "type": "pie", "maxSlices": 6, "showTotal": true }
  },
  "items": ["정보기술", "금융", "헬스케어", "임의소비재", "통신", "기타"],
  "values": [32, 13, 12, 10, 9, 24],
  "unit": "%",
  "imageAsset": {
    "source": "search",
    "query": "stock market data visualization",
    "placement": "background",
    "opacity": 0.15
  }
}
```

### 예시 2: Magnificent 7 기업 — "이 기업들이 누구인가"가 핵심

```
나레이션: "Apple, Microsoft, NVIDIA, Amazon, Meta, Alphabet, Tesla — 이 7개 기업을 기억하세요"
```

**심의 과정:**
- 📊 차트: 수치 비교가 아니므로 차트 부적합
- 🏷️ 심볼: 로고가 핵심 — 기업 브랜드 인지가 목적
- 🖼️ 이미지: 로고가 시각 요소 충분, 배경으로 실리콘밸리 이미지 가능
- 📐 레이아웃: logo_grid + 배경(0.12) 공존 가능

**최종:**
```json
{
  "creative": {
    "displayMode": "logo_grid",
    "logoMap": {
      "Apple": "Apple", "Microsoft": "Microsoft", "NVIDIA": "Nvidia",
      "Amazon": "Amazon", "Meta": "Meta", "Alphabet": "Google", "Tesla": "Tesla"
    }
  },
  "imageAsset": {
    "source": "search",
    "query": "silicon valley tech campus aerial view",
    "placement": "background",
    "opacity": 0.12
  }
}
```

### 예시 3: 기업별 수익률 비교 — "수치 차이"가 핵심

```
나레이션: "Apple 340%, Microsoft 280%, NVIDIA 1,100% — 수익률 차이가 엄청납니다"
```

**심의 과정:**
- 📊 차트: bar chart — 수치 비교가 핵심, 로고보다 막대 높이 차이가 임팩트
- 🏷️ 심볼: 로고를 bar 레이블에 배지로 병용 가능
- 🖼️ 이미지: 차트가 주 요소, 이미지 불필요
- 📐 레이아웃: bar + 로고배지 공존 최적

**최종:**
```json
{
  "creative": {
    "chartConfig": { "type": "bar" },
    "logoMap": {
      "Apple": "Apple", "Microsoft": "Microsoft", "NVIDIA": "Nvidia"
    }
  },
  "items": ["Apple", "Microsoft", "NVIDIA"],
  "values": [340, 280, 1100],
  "unit": "%"
}
```

> 같은 기업 데이터라도 **씬의 핵심 메시지**에 따라 logo_grid vs bar chart가 달라진다.

### 예시 4: 3국 비교 + 국기 + 차트

```
나레이션: "미국 10.7%, 영국 5.4%, 호주 6.8% — 미국이 압도적입니다"
```

**심의 과정:**
- 📊 차트: bar — 수치 비교
- 🏷️ 심볼: 국기 — 즉각적 국가 인식
- 🖼️ 이미지: 세계지도 배경 가능 (opacity 0.12)
- 📐 레이아웃: bar + 국기 + 배경 모두 공존 가능

**최종:**
```json
{
  "items": ["미국", "영국", "호주"],
  "values": [10.7, 5.4, 6.8],
  "unit": "%",
  "itemFlags": ["US", "GB", "AU"],
  "imageAsset": {
    "source": "generate",
    "query": "world map with highlighted countries",
    "placement": "background",
    "opacity": 0.12
  }
}
```

### 예시 5: 투자 원칙 — 개념 리스트

```
나레이션: "원화 매매, 연금저축 계좌 활용, 소액 투자 — 이 세 가지를 기억하세요"
```

**심의 과정:**
- 📊 차트: 데이터 없음, 부적합
- 🏷️ 심볼: 아이콘 — 각 개념을 직관적으로 표현
- 🖼️ 이미지: 아이콘만으로 약간 빈약, 배경이미지로 보강
- 📐 레이아웃: 아이콘 리스트 + 배경(0.30) 최적

**최종:**
```json
{
  "items": ["원화 매매", "연금저축 계좌 활용", "소액 투자"],
  "itemIcons": ["DollarSign", "Landmark", "Coins"],
  "imageAsset": {
    "source": "generate",
    "query": "quirky cartoon style, person investing on smartphone",
    "placement": "background",
    "opacity": 0.30
  }
}
```
