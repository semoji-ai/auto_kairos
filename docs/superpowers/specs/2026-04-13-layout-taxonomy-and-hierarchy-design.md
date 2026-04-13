# Layout Taxonomy and Hierarchy Design

## 목표
Auto Kairos의 Remotion 레이아웃 시스템을 `기본형(base layout) + 옵션(variant)` 구조로 재정리하고, 텍스트 정보 계층을 `headline/title/items/value`의 실제 역할에 맞게 다시 정의합니다. 이번 개편은 특히 quote 계열 중복 제거, pie/donut 및 bar 방향 옵션화, items/value 중심 레이아웃에서 잘못된 타이포 비중 수정, logo/flag 표시 복구를 함께 해결하는 것을 목표로 합니다.

## 현재 문제

### 1. 레이아웃 taxonomy가 표현 차이를 별도 layout 이름으로 들고 있음
- `quote` / `quote_portrait`는 실질적으로 같은 개념인데 분리되어 있음
- `pie` / `donut`, `bar` / `bar_horizontal`은 표현 옵션 차이에 가까운데 별도 layout으로 노출됨
- SceneEditor 레이아웃 목록과 CreativeScene 내부 분기가 taxonomy/표현 옵션을 혼합하고 있음

### 2. 정보 계층이 실제 의미와 반대로 렌더링됨
현재 렌더러는 많은 레이아웃에서 상단 headline 텍스트를 공통 주연처럼 취급합니다. 하지만 실제 사용 규칙은 다음과 다릅니다.

- `headline`은 사실상 `headline_only` 계열 전용
- 대부분의 레이아웃은 `title`이 보조 제목/차트 제목/섹션명 역할
- 핵심 정보는 `items` 또는 `value`
- 같은 의미를 title/headline과 item/value에서 중복 강조하면 안 됨

현재 문제 사례:
- `before_after`에서 "열효율 비교"가 크게 보이고 `증기 엔진`, `내연기관`, 수치가 작음
- `items_list` 계열에서 제목이 지나치게 크고 실제 이유/포인트가 작음
- `metric_spotlight`에서 headline이 주연처럼 보이고 실제 수치/대상이 약함

### 3. logo / flag가 데이터가 있어도 충분히 노출되지 않음
- 일부 레이아웃에서만 제한적으로 사용됨
- 데이터가 있어도 자동 선택/렌더링 흐름에서 묻히거나 사라짐
- logo/flag가 장식이 아니라 정보 전달 요소로 쓰여야 할 장면에서 존재감이 약함

## 설계 원칙

### 1. 기본형과 옵션을 분리한다
레이아웃 이름은 "콘텐츠 구조"를 나타내고, 시각적 파생은 옵션으로 표현합니다.

예시:
- `pie` + `chartStyle: "pie" | "donut"`
- `bar` + `orientation: "vertical" | "horizontal"`
- `quote` + `withPortrait: true | false`
- `quote` + `portraitPlacement: "left" | "right"`

### 2. `headline`은 공통 주연 슬롯이 아니다
- `headline_only`만 headline을 주연으로 사용
- 나머지 레이아웃은 `title`이 작은 보조 제목
- 실제 주연은 `items`, `value`, 비교 대상, 핵심 수치

### 3. 주연 슬롯(primary content slot)을 레이아웃별로 명시한다
각 레이아웃은 무엇이 가장 크게 보여야 하는지 규칙을 가져야 합니다.

예시:
- `items_list`, `items_grid`, `before_after`, `comparison_table`, `metric_wall` → items/value가 주연
- `metric_spotlight`, `icon_stat`, `counter` → value + 대상 텍스트가 주연
- `quote` → quote text가 주연
- `headline_only` → headline이 주연
- `cinematic` → 이미지/나레이션이 주연, 텍스트 최소화

### 4. 같은 의미를 두 번 크게 보여주지 않는다
예를 들어:
- `before_after`에서는 `title="열효율 비교"`는 작아야 하고
- `증기 엔진`, `내연기관`, 수치가 커야 함

즉 title은 분류/설명, items/value는 정보 본문 역할을 지켜야 합니다.

## 목표 taxonomy

### 유지할 기본 layout
- `headline_only`
- `items_grid`
- `items_list`
- `person_card`
- `counter`
- `quote`
- `split`
- `bar`
- `logo_grid`
- `pie`
- `line`
- `flow`
- `timeline`
- `metric_spotlight`
- `metric_wall`
- `rank_list`
- `comparison_table`
- `before_after`
- `icon_stat`
- `stacked_progress`
- `card_carousel`
- `hero_with_context`
- `annotated_chart`
- `cinematic`

### 기본 layout의 옵션/variant로 흡수할 것
- `donut` → `pie.chartStyle = "donut"`
- `bar_horizontal` → `bar.orientation = "horizontal"`
- `quote_portrait` → `quote.withPortrait = true`

### 유지 이유
- `metric_spotlight`와 `icon_stat`은 모두 단일 포인트 계열이지만 사용 의도가 다름
- `metric_wall`과 `comparison_table`은 카드 형태가 비슷해도 의미 구조가 다름
- `bar`와 `bar_horizontal`, `pie`와 `donut`은 사용자 취향/맥락 선택이 필요하므로 옵션화가 적절

## 데이터/타입 구조 변경

### VisualizationData / creative 확장
현재 구조를 크게 깨지 않으면서 옵션을 수용합니다.

추가할 필드 예시:
- `chartStyle?: "pie" | "donut"`
- `orientation?: "vertical" | "horizontal"`
- `withPortrait?: boolean`
- `portraitPlacement?: "left" | "right"`
- `hierarchyRole?: "headline_only" | "title_supports_items" | "value_primary" | "quote_primary"`

또는 `creative.layoutOptions` 같은 중첩 블록으로 묶어도 되지만, 현재 코드베이스는 플랫 스키마를 선호하므로 첫 단계에서는 플랫 필드가 더 안전합니다.

## 렌더링 규칙

### 1. Layout resolution
`resolveLayout()`는 다음 규칙으로 변경합니다.

- 입력 layout이 `quote_portrait`면 내부적으로 `quote`로 정규화 + `withPortrait=true`
- 입력 layout이 `donut`면 내부적으로 `pie`로 정규화 + `chartStyle="donut"`
- 입력 layout이 `bar_horizontal`면 내부적으로 `bar`로 정규화 + `orientation="horizontal"`
- SceneEditor와 manifest에서는 기존 값도 읽을 수 있게 하위호환 유지

### 2. Title/Items hierarchy
공통 헤드라인 렌더링을 그대로 모든 layout에 적용하지 않고, layout별 규칙을 둡니다.

#### headline_only
- headline만 크게 렌더링
- title/items/value는 보조 또는 없음

#### items 중심 layout
대상:
- `items_list`
- `items_grid`
- `before_after`
- `comparison_table`
- `metric_wall`
- `rank_list`
- `card_carousel`
- `hero_with_context`
- `timeline`
- `flow`

규칙:
- title은 작은 섹션 제목/차트 제목
- items 또는 비교 대상 텍스트가 가장 큼
- value가 있으면 item과 동급 또는 더 크게
- 공통 headline block은 숨기거나 title용 작은 스타일로 축소

#### value 중심 layout
대상:
- `counter`
- `metric_spotlight`
- `icon_stat`

규칙:
- value가 최우선
- item 또는 label은 value를 설명하는 수준
- title은 작은 맥락 텍스트
- headline이 value보다 커지면 안 됨

#### quote
- quote text가 주연
- title은 있더라도 매우 작게
- withPortrait=true면 좌/우 portrait 레이아웃 사용

### 3. Logo / flag 표시 규칙
logo/flag는 데이터가 있을 때 가급적 항상 정보 슬롯으로 소비합니다.

#### 우선 적용 layout
- `items_list`
- `items_grid`
- `logo_grid`
- `rank_list`
- `comparison_table`
- `before_after`
- `card_carousel`

#### 규칙
- `itemFlags`가 있으면 우선 국기 배지/플래그 카드 표시
- `logoMap` 또는 logo 식별자가 있으면 로고 표시
- 아이콘/플래그/로고가 모두 없을 때만 일반 badge fallback
- `before_after`는 before/after 카드 각각에 대표 visual 슬롯을 둘 수 있게 확장
- `comparison_table` / `metric_wall`은 cell/card 선행 시각 요소를 허용

## 타이포그래피 재조정 방향
`design/defaults.ts`의 typography 기본값과 실제 layout별 사용 크기를 함께 손봅니다.

핵심 방향:
- `itemText`, `comparisonValue`, `metricValue`를 지금보다 더 강하게 사용
- `chartTitle`, `labelText`, `sourceText`는 보조적 역할에 맞게 유지 또는 축소
- 공통 headline accent font size override를 items 존재 여부만으로 결정하지 않음
- layout별 max font cap / min font cap을 둬서 title이 items를 압도하지 못하게 함

## SceneEditor 방향
SceneEditor는 사용자가 여전히 직관적으로 고를 수 있어야 합니다.

### 변경 방향
- layout 선택 목록에는 기본형만 노출
- 별도 옵션 UI 추가
  - pie: `pie` / `donut`
  - bar: `vertical` / `horizontal`
  - quote: portrait on/off, portrait 위치
- 기존 scene가 `donut`, `bar_horizontal`, `quote_portrait`를 가지고 있어도 에디터에서 읽어서 옵션으로 매핑
- 씬에디터에서 수정한 값이 저장/재로드 후에도 동일 스키마로 유지되도록 manifest/visualization/creative 경로를 함께 동기화
- 즉 렌더러만 바꾸는 것이 아니라, 씬에디터가 수정된 taxonomy와 옵션 구조를 직접 편집할 수 있어야 함

## 구현 범위

### 필수
- taxonomy 정리 및 하위호환 정규화
- quote 통합
- pie/donut, bar orientation 옵션화
- title/items/value hierarchy 룰 도입
- logo/flag 렌더 우선순위 개선
- SceneEditor 옵션 반영

### 이번 단계에서 제외
- 완전 새로운 layout 추가
- scene_specs 생성 로직 전면 개편
- 모든 기존 scene 데이터 일괄 마이그레이션 스크립트
- 디자인 프리셋 시스템의 전면 재작성

## 검증 기준
- `headline_only` 외 레이아웃에서 headline이 주연처럼 보이지 않음
- `before_after`에서 비교 대상과 수치가 title보다 큼
- `metric_spotlight`에서 value와 대상이 가장 잘 보임
- `quote_portrait` 없이도 `quote + withPortrait`로 같은 표현 가능
- `pie`와 `donut`, `bar` 세로/가로를 SceneEditor에서 옵션으로 선택 가능
- logo/flag 데이터가 있는 씬에서 시각 요소가 실제로 보임

## 대상 파일
- `auto_agent/remotion_template/src/simple/CreativeScene.tsx`
- `auto_agent/remotion_template/src/components/SceneRenderer.tsx`
- `auto_agent/remotion_template/src/types/manifest.ts`
- `auto_agent/remotion_template/src/editor/SceneEditorPanel.tsx`
- `auto_agent/remotion_template/src/design/defaults.ts`
- `remotion/src/...` 동기화 대상 전체

## 비고
Remotion 규칙상 `remotion/src/`와 `auto_agent/remotion_template/src/`는 반드시 동기화해야 하므로, 실제 구현은 양쪽에 동일 반영되어야 합니다.
