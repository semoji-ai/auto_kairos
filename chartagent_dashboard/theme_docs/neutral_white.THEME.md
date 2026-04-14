# Neutral White

Updated: 2026-04-07

## 1. Theme Identity

- Theme id: `neutral_white`
- Short label: `Neutral White`
- One-line summary: 깨끗한 흰 캔버스 위에 분석 정보를 가장 조용하고 선명하게 올리는 기본 light theme
- Artwork signature: quiet white panel, restrained accent use, clean analytical spacing
- Best-fit contexts:
  - 범용 차트 기본값
  - 기사/리포트/영상 삽입 공용 차트
  - 설명보다 데이터가 먼저 읽혀야 하는 장면
- Avoid when:
  - 강한 방송형 신호감이 필요할 때
  - 패턴이나 개성이 큰 인포그래픽이 필요할 때

## 2. Source References

- `vercel`
- `apple`
- `notion`

Reference intent:

- `vercel`의 저노이즈 구조감
- `apple`의 깨끗한 여백과 단일 포커스
- `notion`의 whisper border와 warm-neutral 읽기감

## 3. Visual Theme & Atmosphere

- Mood:
  - 정제됨
  - 조용함
  - 분석적
- Density:
  - `sparse` to `balanced`
- Contrast strategy:
  - white-on-light surfaces with dark text and one restrained accent
- Surface language:
  - 큰 패널은 거의 백색, 경계는 얇고 조용함
- Motion expectation:
  - 정적, 미세 강조만 허용

## 4. Color Roles

- Background:
  - `#fcfdff`
- Panel:
  - `#ffffff`
- Panel alt:
  - `#f4f7fb`
- Plot background:
  - `#fbfdff`
- Primary text:
  - `#0f172a`
- Secondary text:
  - `#314155`
- Muted text:
  - `#64748b`
- Primary accent:
  - `#2563eb`
- Secondary accent:
  - `#0f766e`
- Header fill:
  - `#e8eef5`

### Color usage rules

- accent는 한 chart 안에서 1개만 강하게 쓴다
- grid와 divider는 눈에 띄지 않게 유지한다
- source note는 muted 계열만 사용한다

## 5. Typography Rules

- Title role:
  - family: `Space Grotesk / Pretendard`
  - weight: `600~700`
  - tone: compressed but clean
- Label role:
  - family: `Space Grotesk / Pretendard`
  - weight: `600`
- Value role:
  - family: `Space Grotesk / Pretendard`
  - weight: `700`
- Source role:
  - family: `Space Grotesk / Pretendard`
  - weight: `500`

### Text hierarchy rules

- title은 짧게
- label은 기능적으로
- value는 label보다 확실히 두껍게
- source는 잘 읽히되 시선 우선순위는 가장 낮게

## 6. Geometry & Shape

- Corner radius:
  - card `20`
  - chip `12`
- Bar style:
  - softly rounded
- Outline width:
  - 얇게
- Stroke width:
  - 중간 이하
- Gap language:
  - balanced, airy

## 7. Pattern & Texture

- Pattern mode:
  - `solid`
- Pattern density:
  - 낮게
- Texture purpose:
  - 거의 없음, 데이터 판독 우선

### Pattern rules

- 같은 panel 안에서 hatch를 남발하지 않는다
- 강조가 꼭 필요할 때만 보조 시리즈에 최소한으로 사용

## 8. Chart Family Defaults

### bar / bar_horizontal

- Best fit: `strong`
- Rules:
  - bar는 너무 두껍지 않게
  - label은 좌측 혹은 외부 정렬
  - grid line은 2개 내외

### line

- Best fit: `strong`
- Rules:
  - line은 선명하되 과장하지 않음
  - marker는 dot 정도만 허용

### donut / pie

- Best fit: `good`
- Rules:
  - ring thickness는 중간
  - 중앙 숫자는 짧게

### comparison_table / fact_table

- Best fit: `strong`
- Rules:
  - header는 연한 fill
  - divider는 얇고 조용하게
  - padding은 충분히 줌

## 9. Annotation, Source, and Caption Rules

- Annotation style:
  - quiet label
- Source style:
  - `bottom_right`
- Source opacity:
  - `0.78`
- Caption rule:
  - 한 줄, 기능적, muted

## 10. Recommended Overrides

- `stroke_width`
  - 소폭만 증가 허용
- `corner_radius`
  - 줄이는 건 괜찮고, 크게 늘리면 성격이 바뀜
- `pattern_density`
  - 기본은 `low`
- `source_mode`
  - `bottom_right` 또는 `bottom_left`

## 11. Do

- 여백을 믿는다
- 색보다 위계와 spacing으로 품질을 만든다
- 표/차트 둘 다 무난하게 읽히게 한다

## 12. Don't

- 방송형 neon accent를 얹지 말 것
- 패턴을 시각 주인공으로 만들지 말 것
- source를 rail처럼 강하게 키우지 말 것

## 13. Agent Prompt Guide

- Good prompt:
  - `Use Neutral White for a calm analytical chart with one blue accent and very quiet source text.`
- Good prompt:
  - `Keep the panel nearly white, use only thin dividers, and make the value hierarchy clearer than the color contrast.`

