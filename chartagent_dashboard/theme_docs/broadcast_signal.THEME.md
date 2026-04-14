# Broadcast Signal

Updated: 2026-04-07

## 1. Theme Identity

- Theme id: `broadcast_signal`
- Short label: `Broadcast Signal`
- One-line summary: dark panel 위에서 정보 신호를 강하게 띄우는 방송형 고대비 chart theme
- Artwork signature: high-contrast dark panel, crisp signal outlines, urgent broadcast accent cadence
- Best-fit contexts:
  - 영상형 explainer 차트
  - 비교/속보형 수치 전달
  - source rail과 annotation tag가 필요한 장면
- Avoid when:
  - 차분한 리포트/문서 삽입용
  - warm editorial 톤이 필요한 상황

## 2. Source References

- `clickhouse`
- `vercel`

Reference intent:

- `clickhouse`의 dark + signal accent 긴장감
- `vercel`의 구조적 정밀함과 workflow-like color discipline

## 3. Visual Theme & Atmosphere

- Mood:
  - 긴급함
  - 신호감
  - 방송형
- Density:
  - `balanced` to `balanced_dense`
- Contrast strategy:
  - dark panel + bright accent + pale cool text
- Surface language:
  - 카드보다 panel, 칩보다 signal tag
- Motion expectation:
  - 빠른 reveal, crisp emphasis

## 4. Color Roles

- Background:
  - `#07101c`
- Panel:
  - `#0c1730`
- Panel alt:
  - `#12203a`
- Plot background:
  - `#0a152b`
- Primary text:
  - `#f8fafc`
- Secondary text:
  - `#dbeafe`
- Muted text:
  - `#93c5fd`
- Grid:
  - `#314159`
- Grid strong:
  - `#4b5d78`
- Primary accent:
  - `#f97316`
- Secondary accent:
  - `#22d3ee`
- Series palette:
  - `#f97316`, `#22d3ee`, `#4ade80`, `#facc15`, `#a78bfa`, `#fb7185`

### Color usage rules

- accent는 signal처럼 써야지 surface fill처럼 남발하면 안 된다
- 주 시리즈 1개, 보조 시리즈 1개 정도가 이상적
- 텍스트는 항상 명확히 밝아야 한다

## 5. Typography Rules

- Title role:
  - family: `Space Grotesk / Pretendard`
  - weight: `700`
  - tone: sharp, compressed, high-attention
- Label role:
  - family: `IBM Plex Sans KR / Pretendard`
  - weight: `700`
- Value role:
  - family: `Space Grotesk / Pretendard`
  - weight: `700+`
- Source role:
  - family: `IBM Plex Sans KR / Pretendard`
  - weight: `600`

### Text hierarchy rules

- title보다 label이 더 기능적으로 읽혀야 한다
- value는 밝고 굵게
- source는 rail로 보내되, 너무 약하지 않게 유지한다

## 6. Geometry & Shape

- Corner radius:
  - card `14`
  - chip `8`
- Bar style:
  - sharper, tighter
- Outline width:
  - 중간 이상
- Stroke width:
  - 강하게
- Gap language:
  - tight but organized

## 7. Pattern & Texture

- Pattern mode:
  - `outline_plus_hatch`
- Pattern density:
  - 중간 이상
- Pattern spacing:
  - `8`
- Pattern opacity:
  - `0.42`
- Texture purpose:
  - 시리즈 구분과 방송형 리듬 부여

### Pattern rules

- hatch는 주 시리즈 전체가 아니라 일부 강조 시리즈에 쓴다
- pattern은 signal을 강화하는 용도여야 한다

## 8. Chart Family Defaults

### bar / bar_horizontal

- Best fit: `strong`
- Rules:
  - 막대 대비를 강하게
  - annotation tag를 붙이기 좋음

### line

- Best fit: `strong`
- Rules:
  - line weight는 강하게
  - marker는 ring이나 강한 dot 허용

### donut / pie

- Best fit: `good`
- Rules:
  - dark panel 안에서도 ring 구분이 명확해야 함

### comparison_table

- Best fit: `strong`
- Rules:
  - center comparison보다 panel strip 느낌
  - header와 key metric을 강하게 살림

## 9. Annotation, Source, and Caption Rules

- Annotation style:
  - signal tag / news tag
- Source style:
  - `edge_rail`
- Source opacity:
  - `0.9`
- Caption rule:
  - rail-based, 짧고 확실하게

## 10. Recommended Overrides

- `stroke_width`
  - 늘려도 잘 버팀
- `outline_width`
  - 중간 이상 유지 추천
- `pattern_density`
  - `medium` 또는 `high`
- `source_mode`
  - `edge_rail` 강력 추천

## 11. Do

- 차트를 signal source처럼 보이게 한다
- rail, tag, crisp outline을 적극 활용한다
- 비교/지표판을 빠르게 읽히게 만든다

## 12. Don't

- pastel infographic처럼 만들지 말 것
- panel을 너무 둥글고 부드럽게 만들지 말 것
- source를 바닥 미세 글씨처럼 죽이지 말 것

## 13. Agent Prompt Guide

- Good prompt:
  - `Use Broadcast Signal for a dark comparison chart with an edge source rail and strong orange/cyan emphasis.`
- Good prompt:
  - `Make the line chart feel like a broadcast explainer insert rather than a dashboard widget.`

