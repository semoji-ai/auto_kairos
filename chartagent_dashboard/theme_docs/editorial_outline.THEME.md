# Editorial Outline

Updated: 2026-04-07

## 1. Theme Identity

- Theme id: `editorial_outline`
- Short label: `Editorial Outline`
- One-line summary: 종이감과 설명성을 살리면서도 chart/table의 경계를 또렷하게 유지하는 warm editorial theme
- Artwork signature: warm paper surface, outline-led bars and slices, airy editorial rhythm
- Best-fit contexts:
  - 기사/리포트형 차트
  - 설명형 표와 차트 혼합
  - 교육적/에세이형 데이터 표현
- Avoid when:
  - 속보형 방송 insert
  - 지나치게 기술적/시장형 시각화

## 2. Source References

- `notion`
- `claude`

Reference intent:

- `notion`의 whisper border와 warm neutral rhythm
- `claude`의 paper-like surface와 calm editorial pacing

## 3. Visual Theme & Atmosphere

- Mood:
  - 따뜻함
  - 설명적
  - 읽기 좋음
- Density:
  - `balanced`
- Contrast strategy:
  - warm surface + dark text + one earthy accent
- Surface language:
  - 종이 위 outline drawing 같은 느낌
- Motion expectation:
  - 정적, 낮은 긴장감, 단계적 reveal

## 4. Color Roles

- Background:
  - `#f8efe3`
- Panel:
  - `#fff8f0`
- Panel alt:
  - `#f2e6d4`
- Plot background:
  - `#fffaf3`
- Primary text:
  - `#241c16`
- Secondary text:
  - `#5a483c`
- Muted text:
  - `#8a7464`
- Primary accent:
  - `#b45309`
- Secondary accent:
  - `#7c2d12`
- Header fill:
  - `#eadcc8`

### Color usage rules

- earthy accent만 사용
- surface는 항상 warm neutral을 유지
- grid/divider는 눈에 띄지 않게

## 5. Typography Rules

- Title role:
  - family: `Space Grotesk / Pretendard`
  - weight: `650~700`
  - tone: editorial but clear
- Label role:
  - family: `IBM Plex Sans KR / Pretendard`
  - weight: `600~650`
- Value role:
  - family: `Space Grotesk / Pretendard`
  - weight: `700`
- Source role:
  - family: `IBM Plex Sans KR / Pretendard`
  - weight: `500`

### Text hierarchy rules

- title은 기사 소제목처럼
- label은 차분하게
- value는 강조하되 과장하지 않음
- source는 footnote처럼 내려줌

## 6. Geometry & Shape

- Corner radius:
  - card `18`
  - chip `10`
- Bar style:
  - outline-led, 덜 둥글게
- Outline width:
  - 분명하지만 무겁지 않게
- Gap language:
  - airy

## 7. Pattern & Texture

- Pattern mode:
  - `outline_plus_hatch`
- Pattern density:
  - `medium`
- Pattern spacing:
  - `16`
- Pattern opacity:
  - `0.56`

### Pattern rules

- filled surface보다 outline과 hatch가 더 어울림
- pattern은 정보 보조 역할이어야 함

## 8. Chart Family Defaults

### bar / bar_horizontal

- Best fit: `good`
- Rules:
  - filled bar보다 outline bar가 어울림

### line

- Best fit: `strong`
- Rules:
  - 추세/연표/설명형에 적합

### donut / pie

- Best fit: `okay`
- Rules:
  - slice보다 label/footnote 설명이 중요

### comparison_table / fact_table

- Best fit: `strong`
- Rules:
  - 표에 특히 잘 맞음
  - divider/padding을 믿는 스타일

## 9. Annotation, Source, and Caption Rules

- Annotation style:
  - soft note / quiet chip
- Source style:
  - `bottom_left`
- Source opacity:
  - `0.82`

## 10. Do

- 설명성과 따뜻한 읽기감을 유지한다
- 표와 차트의 경계를 outline으로 정리한다

## 11. Don't

- neon signal이나 방송형 rail을 넣지 말 것
- dark panel urgency를 얹지 말 것

## 12. Agent Prompt Guide

- Good prompt:
  - `Use Editorial Outline for a warm explanatory table with calm footnote treatment and gentle outline-led structure.`

