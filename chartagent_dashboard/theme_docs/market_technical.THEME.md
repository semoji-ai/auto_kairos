# Market Technical

Updated: 2026-04-07

## 1. Theme Identity

- Theme id: `market_technical`
- Short label: `Market Technical`
- One-line summary: 장식보다 정확성과 밀도를 우선하는 기술/시장형 chart theme
- Artwork signature: terminal density, thin technical lines, compressed market signal layout
- Best-fit contexts:
  - candlestick / histogram / dense line chart
  - 정량 분석
  - 기술 리포트
- Avoid when:
  - 감성적 인포그래픽
  - warm explanatory graphic

## 2. Source References

- `clickhouse`
- `coinbase`
- `vercel`

Reference intent:

- `clickhouse`의 performance-first 긴장감
- `coinbase`의 금융형 안정감
- `vercel`의 precise minimalism

## 3. Visual Theme & Atmosphere

- Mood:
  - 정밀함
  - 압축됨
  - 기술적
- Density:
  - `dense`
- Contrast strategy:
  - 기능적 대비, 장식 최소
- Surface language:
  - panelized technical sheet
- Motion expectation:
  - 최소, 값과 축 중심

## 4. Color Roles

- Background:
  - `#eff4f7`
- Panel:
  - `#f9fbfd`
- Panel alt:
  - `#ebf1f5`
- Plot background:
  - `#eef4f8`
- Primary text:
  - `#111827`
- Secondary text:
  - `#243243`
- Muted text:
  - `#526070`
- Grid:
  - `#c4d2de`
- Grid strong:
  - `#90a3b8`
- Primary accent:
  - `#2563eb`
- Secondary accent:
  - `#0ea5e9`

### Color usage rules

- color는 기능적으로만 사용
- positive/negative 또는 series 구분 외에는 과장 금지
- grid는 읽기용으로 적극 사용 가능

## 5. Typography Rules

- Title role:
  - family: `Space Grotesk / Pretendard`
  - weight: `600`
- Label role:
  - family: `IBM Plex Mono / JetBrains Mono`
  - weight: `500~600`
- Value role:
  - family: `IBM Plex Mono / JetBrains Mono`
  - weight: `700`
- Source role:
  - family: `IBM Plex Mono / JetBrains Mono`
  - weight: `500`

### Text hierarchy rules

- 모노 label을 적극 허용
- value는 compact하지만 또렷해야 함
- 불필요한 annotation은 줄인다

## 6. Geometry & Shape

- Corner radius:
  - card `12`
  - chip `8~10`
- Bar style:
  - tighter, more exact
- Stroke width:
  - 얇거나 중간
- Gap language:
  - compact

## 7. Pattern & Texture

- Pattern mode:
  - `solid`
- Pattern density:
  - `low`
- Texture purpose:
  - 거의 없음

## 8. Chart Family Defaults

### line

- Best fit: `strong`
- Rules:
  - dense guides 허용
  - marker는 최소화

### bar / bar_horizontal

- Best fit: `strong`
- Rules:
  - 정렬과 숫자 가독성이 중요

### candlestick / histogram

- Best fit: `strong`
- Rules:
  - 가장 잘 맞는 family
  - grid, axis, wick, body 구분을 명확히

### comparison_table / fact_table

- Best fit: `strong`
- Rules:
  - dense but readable
  - padding은 줄여도 됨

## 9. Annotation, Source, and Caption Rules

- Annotation style:
  - minimal signal
- Source style:
  - `bottom_right` or technical rail
- Source opacity:
  - `0.72`

## 10. Do

- 장식보다 판독성을 우선한다
- 모노/기술형 label을 활용한다
- dense guide 구조를 허용한다

## 11. Don't

- round/friendly infographic처럼 만들지 말 것
- pattern으로 시선을 빼앗지 말 것
- warm editorial surface를 섞지 말 것

## 12. Agent Prompt Guide

- Good prompt:
  - `Use Market Technical for a dense line chart with compact labels, strong grid discipline, and minimal decorative surface treatment.`

