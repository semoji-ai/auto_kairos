# Dashboard Analytical

Updated: 2026-04-07

## 1. Theme Identity

- Theme id: `dashboard_analytical`
- Short label: `Dashboard Analytical`
- One-line summary: 패널형 분석 화면에서 수치와 비교를 가장 안정적으로 전달하는 운영형 chart theme
- Artwork signature: dense information grid, balanced KPI panels, clean operational signal language
- Best-fit contexts:
  - KPI 대시보드
  - 분석 보고용 패널
  - 비교표, metric wall, line/bar 복합 구성
- Avoid when:
  - 장식적 인포그래픽이 필요한 경우
  - 극도로 cinematic한 장면

## 2. Source References

- `coinbase`
- `clickhouse`

Reference intent:

- `coinbase`의 제도권/신뢰형 panel rhythm
- `clickhouse`의 성능 중심 수치 강조

## 3. Visual Theme & Atmosphere

- Mood:
  - 차분함
  - 운영적
  - 구조적
- Density:
  - `balanced_dense`
- Contrast strategy:
  - white panel + cool analytical accent
- Surface language:
  - panel system, tidy KPI blocks, readable grid
- Motion expectation:
  - 과장 없이, 정보 reveal 위주

## 4. Color Roles

- Background:
  - `#eef6f7`
- Panel:
  - `#ffffff`
- Panel alt:
  - `#e3f0f2`
- Plot background:
  - `#f7fbfc`
- Primary text:
  - `#0f172a`
- Secondary text:
  - `#0f4c5c`
- Muted text:
  - `#5a6c78`
- Primary accent:
  - `#0f766e`
- Secondary accent:
  - `#0284c7`
- Header fill:
  - `#dceff0`
- Series palette:
  - `#0f766e`, `#0284c7`, `#2563eb`, `#d97706`, `#14b8a6`, `#7c3aed`

### Color usage rules

- accent는 operational emphasis에만 사용
- grid는 읽히되 배경처럼 남아야 함
- panel 간 구분은 surface tone으로 만든다

## 5. Typography Rules

- Title role:
  - family: `Space Grotesk / Pretendard`
  - weight: `650~700`
  - tone: structured analytical heading
- Label role:
  - family: `IBM Plex Sans KR / Pretendard`
  - weight: `650`
- Value role:
  - family: `Space Grotesk / Pretendard`
  - weight: `700`
- Source role:
  - family: `IBM Plex Sans KR / Pretendard`
  - weight: `500~600`

### Text hierarchy rules

- title은 panel title처럼 작동
- label은 grid/axis/table에서 일관되게 유지
- value는 가장 또렷하게
- source는 footnote 수준

## 6. Geometry & Shape

- Corner radius:
  - card `18`
  - chip `10`
- Bar style:
  - 정돈된 rounded
- Outline width:
  - 얇거나 중간
- Stroke width:
  - 중간
- Gap language:
  - tight but breathable

## 7. Pattern & Texture

- Pattern mode:
  - `solid`
- Pattern density:
  - 낮음
- Pattern spacing:
  - `10`
- Texture purpose:
  - 데이터 구분 보조 정도

### Pattern rules

- panel형 차트에선 solid 우선
- hatch는 꼭 필요한 비교군에만 약하게 적용

## 8. Chart Family Defaults

### bar / bar_horizontal

- Best fit: `strong`
- Rules:
  - KPI/랭킹용으로 안정적
  - label/value 정렬을 분명히

### line

- Best fit: `strong`
- Rules:
  - 추세를 읽기 좋게
  - guide line은 3개 정도 유지

### donut / pie

- Best fit: `good`
- Rules:
  - share 설명용 정도로만
  - 너무 decorative하게 가지 않음

### comparison_table / fact_table

- Best fit: `strong`
- Rules:
  - 가장 강한 family 중 하나
  - padding과 divider rhythm이 중요

### metric_wall / single_stat

- Best fit: `strong`
- Rules:
  - panel grouping이 핵심
  - value hierarchy가 명확해야 함

## 9. Annotation, Source, and Caption Rules

- Annotation style:
  - compact chip
- Source style:
  - `bottom_right`
- Source opacity:
  - `0.8`
- Caption rule:
  - 짧고 분석적

## 10. Recommended Overrides

- `table_cell_padding`
  - 줄이거나 늘려도 잘 버팀
- `bar_gap`
  - family에 따라 조절 가능
- `label_weight`
  - 약간 높여도 안정적
- `source_mode`
  - `bottom_right` 기본, 필요시 `bottom_left`

## 11. Do

- panel 단위로 질서를 만든다
- value / label / source를 안정적으로 분리한다
- 비교표와 metric wall을 강점으로 쓴다

## 12. Don't

- 장식 패턴으로 시선을 뺏지 말 것
- 방송형 강한 rail/tag를 무리하게 넣지 말 것
- 정보 밀도를 낮추는 대신 의미 없는 여백만 늘리지 말 것

## 13. Agent Prompt Guide

- Good prompt:
  - `Use Dashboard Analytical for a KPI-heavy operational chart with clear value hierarchy and clean cool panels.`
- Good prompt:
  - `Make the comparison table feel trustworthy and institutional rather than decorative.`

