---
name: remotion-design-system
description: Use when referencing Remotion component APIs, layout types, BuildingBlocks, and rendering constraints
---

# Remotion Design System

SimpleVideo 기반 Remotion 영상의 시각 디자인 규칙을 정의합니다.
컬러, 아이콘, 레이아웃, 애니메이션, creative 필드 스키마, imageAsset, mapScene 규칙을 포함합니다.

**참조 에이전트**: visual-composer, qa-reviewer

---

## 1. 컬러 시스템 — SimpleVideo

```
기본 팔레트 (전체 영상 공통):
  bg:         '#0A0A0A'     ← 배경, 고정
  surface:    '#141414'     ← 카드 배경, 고정
  text:       '#FFFFFF'     ← 메인 텍스트, 고정
  textMuted:  'rgba(255,255,255,0.5)' ← 보조 텍스트
  border:     'rgba(255,255,255,0.1)' ← 테두리

씬별 accentColor (최대 2색):
  warning:    '#F59E0B'     ← 기본 accent (강조, 경고) — 가장 많이 사용
  primary:    '#3B82F6'     ← 정보, 기술, 차분
  accent:     '#10B981'     ← 성장, 긍정, 성취
  danger:     '#EF4444'     ← 위험, 하락, 긴박 — 드물게 사용
```

**규칙**: 각 씬에서 accentColor는 creative.mood에 따라 결정.
대부분의 씬은 warning(#F59E0B) 1색만으로 충분합니다.

---

## 2. 아이콘 매핑 — 개념 → Lucide

| 개념 카테고리 | Lucide 아이콘 예시 |
|-------------|-------------------|
| AI/기술 | Brain, Cpu, Code, Database, Terminal |
| 성장/트렌드 | TrendingUp, Rocket, ArrowUpRight |
| 보안/안전 | Shield, Lock, ShieldCheck |
| 통신/소통 | MessageSquare, Mail, Globe |
| 비즈니스 | DollarSign, BarChart3, Target |
| 사람/조직 | Users, User, Building |
| 시간 | Clock, Calendar, History |
| 도구 | Wrench, Settings, Hammer |
| 검색/탐구 | Search, Eye, Compass |
| 성공/달성 | CheckCircle, Award, Star |
| 경고/주의 | AlertTriangle, AlertCircle |
| 학습/지식 | BookOpen, GraduationCap, Lightbulb |
| 데이터 | Database, HardDrive, Layers |
| 연결/네트워크 | Network, Link, GitBranch |
| 전쟁/군사 | Swords, Shield, Target, Crosshair |
| 왕관/권력 | Crown, Castle, Landmark |

**반드시 Lucide React에 존재하는 아이콘명만 사용합니다.**

---

## 2.1 Building Blocks 레퍼런스

공유 코드는 `BuildingBlocks.tsx`에 위치. SimpleScene/CreativeScene 양쪽에서 import.

### UI 컴포넌트 — 기본 13개

| 컴포넌트 | 용도 | 사용 시점 |
|----------|------|----------|
| AccentText | {{}} 마크업 | 모든 헤드라인 |
| Card | 카드 컨테이너 | 데이터 묶음 |
| CircleBadge | 텍스트 원형 뱃지 | 번호, 이니셜 |
| ImageBadge | 이미지 원형 뱃지 | 실제 이미지가 있을 때만 |
| Icon | Lucide 아이콘 | 개념 표시 |
| IconBadge | 아이콘 원형 뱃지 | 아이콘이 있는 카테고리 |
| FlagBadge | 국기 원형 뱃지 | 국가 비교/지정학 |
| LogoBadge | 브랜드 로고 뱃지 | 기업/조직 표시 (NATO, Boeing 등) |
| ProgressBar | 진행 바 | 비율, 달성도 |
| Tag | 키워드 태그 | 카테고리, 키워드 |
| Divider | 구분선 | 섹션 분리 |
| StatusDot | 상태 도트 | 긍정/부정/중립 표시 |
| Pill | 필 버튼 | 선택 항목 |

### UI 컴포넌트 — 확장 12개 (의도 기반 컴포지션용)

| 컴포넌트 | 용도 | 사용 시점 |
|----------|------|----------|
| Connector | 노드 간 화살표/연결선 | 프로세스 흐름, 인과관계 (flow 레이아웃) |
| TimelineDot | 타임라인 이벤트 마커 | 연대기, 역사 사건 (timeline 레이아웃) |
| MetricCard | KPI 카드 (라벨+큰숫자+변화율) | 핵심 통계 강조 (metric_spotlight, metric_wall) |
| Sparkline | 인라인 미니 차트 (SVG) | 트렌드를 컴팩트하게 (metric_spotlight 보조) |
| Callout | 말풍선/주석 박스 | 부연 설명, 인용 강조 |
| StepBadge | 번호 스텝 배지 | 프로세스 단계 표시 (flow 레이아웃) |
| ComparisonCell | 비교 항목 셀 (before/after) | 변화 전후 대비 (before_after, comparison_table) |
| RankBadge | 순위 배지 (1st/2nd/3rd 색상) | 랭킹 (rank_list 레이아웃) |
| QuoteMark | 독립 인용부호 장식 | 인용문 연출 강화 (quote_portrait) |
| GlowDot | 발광 효과 점 (펄스) | 주의 환기, 라이브 표시 |
| AnnotationLine | 지시선 + 주석 | 차트 주석 (annotated_chart 레이아웃) |
| MiniBar | 인라인 소형 막대 | 카드 내 비교 수치 (rank_list 보조) |

### 애니메이션 훅 (15개)

| 훅 | 용도 | 사용 시점 |
|----|------|----------|
| useFadeRise | 기본 등장 | 대부분의 요소 |
| useFadeSlide | 수평 등장 | 좌우 슬라이드 레이아웃 |
| useFade | 투명도만 | 배경, 오버레이 |
| useScale | 스케일 등장 | 카드, 뱃지 |
| useOvershootScale | 오버슈트 등장 | 숫자 공개, 핵심 뱃지 |
| useBounceIn | 바운스 등장 | 성취/축하 (mood: triumphant) |
| useShake | 진동 | 경고/위험 (mood: urgent) |
| usePulse | 펄스 | 라이브 카운터, 경고 지속 |
| useGlitch | 글리치 | 해킹/기술 장애 |
| useTypewriter | 타자기 | 인용구, 메시지 |
| useFadeOut | 퇴장 | 씬 전환 전 |
| useSpringValue | 물리 기반 | 자연스러운 모션 |
| useCountUp | 카운팅 | 숫자 데이터 |
| useLineExpand | 라인 확장 | 구분선 애니메이션 |
| staggerDelay | 딜레이 계산 | 리스트/그리드 항목 |

### 아이콘 해석 유틸

- `resolveIcon(name)` — 문자열 → Lucide 컴포넌트 (예: `"Shield"` → Shield)
- `resolveLogo(name)` — 문자열 → Simple Icons 컴포넌트 (예: `"Nato"` → SiNato)

### 아이콘 사용 원칙

- **의미 있는 아이콘만** — 장식용 금지, 정보 인식 보조 용도
- **일관된 매핑** — 같은 개념엔 같은 아이콘 (영상 전체)
- **한 씬 최대 6개** — 초과 시 시각적 소음
- **우선순위**: 실제 이미지 → ImageBadge, 브랜드 → LogoBadge, 개념 → IconBadge, 국가 → FlagBadge, 텍스트 → CircleBadge
- **국기**: 국가 비교, 지정학 씬에서만 FlagBadge 사용
- **로고**: 기업/조직이 주체일 때만 LogoBadge 사용 (NATO, Boeing, UN 등)

---

## 3. 레이아웃 파라미터

```
padding: 48px          ← 최소, 넉넉한 여백
gap: 24px              ← 요소 간격
cardRadius: 16px       ← 둥근 카드
maxContentWidth: 1400px ← 콘텐츠 최대 폭
```

---

## 4. 애니메이션 파라미터

```
fadeIn: 10-15 프레임    ← 등장
stagger: 4-8 프레임     ← 항목 간 지연
hold: 60-120 프레임     ← 정보 체류 시간 (30fps 기준)
translate: 16-24px      ← 이동 거리
spring: { damping: 200, stiffness: 100 }  ← 바운스 없음
```

**바운스 금지**: damping은 최소 150. 부드럽고 자연스럽게.

---

## 5. 배경 패턴

```
dots:  미묘한 도트 패턴 (opacity: 0.02)  ← 기본
grid:  격자 패턴 (opacity: 0.02)         ← 기술/데이터 씬
lines: 수평선 패턴 (opacity: 0.01)       ← 텍스트 씬
none:  배경 없음                          ← 이미지 씬
```

---

## 6. 전환 효과

| 전환 | 용도 |
|------|------|
| fade | 기본. 자연스러운 전환 |
| slide | 새로운 정보 등장. 방향: left, right |
| wipe | 에너지. 데이터 씬 전환 |

**같은 전환 3회 연속 사용 금지**. 반드시 교차.

---

## 7. durationFrames 계산

```
base = narration_char_count / 5 * 30   (한국어: 초당 5자, 30fps)
padding = 60                           (앞뒤 여백 1초씩)
durationFrames = base + padding

최소: 120 프레임 (4초)
최대: 600 프레임 (20초)
```

---

## 8. creative 필드 기반 렌더링

모든 시각화는 **creative 필드 + 데이터 구조**로 결정된다.

### 레이아웃 결정 (resolveLayout) — 의도 기반

렌더러가 아래 **우선순위**로 레이아웃을 결정:

1. **`creative.layout` 직접 지정** (1순위, 의도 기반) — asset-advisory가 다중 관점 심의 결과로 설정
2. **displayMode / chartConfig** (2순위, 하위호환) — logo_grid, pie, line
3. **데이터 구조 기반 추론** (3순위, fallback) — emphasis/reveal + items/values 패턴

**핵심 원칙**: 같은 데이터도 씬의 의도에 따라 다른 레이아웃이 결정된다.
- "이 기업들의 존재감" → `logo_grid`
- "이 기업들의 비중 차이" → `pie`
- "이 기업들의 순위" → `rank_list`

### 레이아웃 타입 (24개)

**기본 11개** (기존):

| layout | 용도 | 필요 데이터 |
|--------|------|-----------|
| `headline_only` | 텍스트 임팩트 | headline만 |
| `items_grid` | 6+ 항목 그리드 | items 6개+ |
| `items_list` | 3-5 항목 리스트 | items 3-5개 |
| `person_card` | 인물 카드 | emphasis=person, items 2+ |
| `counter` | 빅넘버 카운팅 | emphasis=number/count, {{숫자}} |
| `quote` | 인용문 | emphasis=quote |
| `split` | 좌우 VS 비교 | emphasis=contrast / reveal=split_reveal |
| `bar` | 바 차트 | items + values 3+쌍 |
| `logo_grid` | 로고 그리드 | displayMode=logo_grid, logoMap |
| `pie` | 파이 차트 | chartConfig.type=pie |
| `line` | 라인 차트 | chartConfig.type=line |

**확장 13개** (의도 기반 컴포지션):

| layout | 용도 | 필요 데이터 |
|--------|------|-----------|
| `flow` | 프로세스/인과 흐름 | items (단계명), StepBadge+Connector |
| `timeline` | 시간순 사건 나열 | items (시점), descriptions (설명) |
| `metric_spotlight` | 단일 KPI 극적 강조 | items[0] (라벨), values[0] (수치) |
| `metric_wall` | 여러 KPI 동시 비교 | items + values (2-4쌍) |
| `rank_list` | 순위 시각화 | items + values (이미 순위 정렬) |
| `comparison_table` | 다차원 비교 | items + values (각 항목별 수치) |
| `before_after` | 변화 전후 대비 | items[0]=before, items[1]=after |
| `icon_stat` | 단일 통계 + 아이콘 | itemIcons[0], values[0] |
| `stacked_progress` | 점유율/진행률 비교 | items + values (ProgressBar 스택) |
| `card_carousel` | 정보 카드 나열 | items + descriptions, itemIcons |
| `hero_with_context` | 큰 헤드라인 + 부연 카드 | headline + items (보조 정보) |
| `quote_portrait` | 인물 사진 + 인용문 | images[0], items[0] (인용문) |
| `annotated_chart` | 차트 + 주석 | items + values + annotations[] |

### layout 필드 스키마

```json
{
  "creative": {
    "concept": "...",
    "reveal": "stagger",
    "emphasis": "number",
    "mood": "informative",
    "headline": "...",
    "layout": "rank_list"   // ← 의도 기반 직접 지정
  }
}
```

`layout`이 없으면 렌더러가 emphasis/reveal/데이터 구조로 자동 추론한다 (하위호환).

### 보완 메커니즘 (normalizeCreative)

creative 필드가 불완전할 때 렌더러가 자동 보정:
- **headline 없음** → title에서 생성
- **emphasis 없음** → 데이터 패턴에서 추론 (values 있으면 number, 아니면 none)
- **reveal 없음** → items 3개+ 이면 stagger, 아니면 fade_in
- **mood 없음** → informative 기본값
- **layout 없음** → resolveLayout fallback (데이터 구조 기반 추론)

### creative 필드 (필수)

```json
{
  "creative": {
    "concept": "string — 시각 연출 의도 서술",
    "reveal": "string — 정보 공개 패턴 (creative-direction 3번)",
    "emphasis": "string — 핵심 강조 요소 (creative-direction 4번)",
    "headline": "string — 화면 표시 텍스트. {{키워드}}는 accent 색상, \\n은 줄바꿈",
    "mood": "string — 감정적 톤 (creative-direction 5번)"
  }
}
```

### 차트/그래프 확장 필드 (선택)

```json
{
  "creative": {
    "chartConfig": {
      "type": "pie | line | bar",
      "maxSlices": 8,
      "highlightIndex": 0,
      "showTotal": true,
      "showGrid": true,
      "showDots": true,
      "showArea": true
    },
    "displayMode": "logo_grid | pie_chart | line_chart",
    "logoMap": { "항목명": "SimpleIcons키" }
  }
}
```

- `chartConfig.type`: pie/line 지정 시 해당 차트 컴포넌트 렌더
- `displayMode`: 특수 레이아웃 (logo_grid 등) 강제 지정
- `logoMap`: logo_grid에서 기업 로고 매핑 (`@icons-pack/react-simple-icons` 키 사용)
- 상세 규칙: `shared/chart-mapping.md` 참조

### 필드 역할 분리 (중복 방지)

```
headline = 화면에 보이는 유일한 텍스트 (AccentText)
title    = 차트 타입에서만 헤더 표시 / 크리에이티브 타입에서는 메타 라벨 (비표시)
values   = 애니메이션 데이터 (count-up 타겟), 별도 화면 표시 안 함
items    = 보조 맥락 라벨

⚠ title과 headline에 동일 텍스트 금지
⚠ dramatic_number에 values 2개 이상 금지 (핵심 숫자 1개만)
⚠ items에 values와 동일한 숫자 문자열 금지

→ 상세 규칙: creative-direction.md 8번 참조
```

---

## 9. imageAsset 스키마

```json
{
  "imageAsset": {
    "source": "wikimedia | search | generate | character",
    "query": "검색어/프롬프트",
    "subject": "대상 설명",
    "placement": "fullscreen | background | center | left | right | inline",
    "opacity": 0.8,
    "overlay": true,
    "usage": "asset | background",
    "characters": ["characters/variant_id.png"],
    "itemImages": false,
    "license": null
  }
}
```

**source 유형:**
- `wikimedia` — Wikimedia Commons 검색 (CC 라이선스)
- `search` — 웹 이미지 검색 (Serper/Pixabay)
- `generate` — FAL.ai로 AI 이미지 생성
- `character` — character_casting.json의 캐릭터 이미지 활용

**placement 유형:**

| placement | 이미지 역할 | 텍스트 위치 | opacity 기본값 | 적합한 상황 |
|-----------|-----------|-----------|-------------|-----------|
| `fullscreen` | **주체** — 이미지가 화면 전체 | 하단 자막만 또는 최소 오버레이 | 0.9~1.0 | 감성적 전환, 시네마틱 순간, 사건 장면 |
| `background` | **보조** — 분위기 깔아줌 | 중앙에 텍스트/차트 | 0.10~0.50 (에셋 밀도에 따라) | 데이터+분위기 조합 |
| `center` | **공동 주체** — 중앙 큰 이미지 | 상하에 텍스트 | 0.8~1.0 | 제품, 건물, 핵심 오브젝트 |
| `left` / `right` | **에셋** — 한쪽에 배치 | 반대쪽에 텍스트 | 0.7~1.0 | 인물 초상, 실물 사진 |
| `inline` | **아이템별** — items와 1:1 매칭 | 각 아이템 옆/위에 | 1.0 | 인물 카드, 아이템별 사진 |

**fullscreen 이미지 씬 (텍스트 없는 이미지 단독 연출):**

이미지 자체가 메시지인 씬. headline은 최소화하거나 생략 가능.
```json
{
  "creative": {
    "concept": "1929년 대공황 당시 월스트리트 사진이 화면을 가득 채운다",
    "layout": "headline_only",
    "reveal": "fade_in",
    "emphasis": "none",
    "headline": "{{1929}}",
    "mood": "somber"
  },
  "imageAsset": {
    "source": "search",
    "query": "1929 wall street crash historic photo",
    "placement": "fullscreen",
    "opacity": 0.9
  }
}
```

**inline 이미지 (아이템별 개별 이미지):**

`itemImages: true`이면 이미지 생성 스크립트가 items 각각에 대해 개별 이미지를 확보하고 `visualization.images` 배열을 채운다.
```json
{
  "items": ["워런 버핏", "피터 린치", "잭 보글"],
  "images": [null, null, null],
  "imageAsset": {
    "source": "wikimedia",
    "query": "Warren Buffett, Peter Lynch, Jack Bogle portraits",
    "placement": "inline",
    "itemImages": true
  }
}
```

---

## 10. 아트스타일 연동

`art_style.json`이 있으면 씬 설계 시 참조:
- 아트스타일의 color_palette와 씬별 accentColor 조화
- historical_period가 있으면 시대 고증 참고

---

## 11. AccentText 마크업

creative.headline에 사용하는 텍스트 마크업:

```
{{텍스트}}  → accent 색상으로 표시
\n          → 줄바꿈

예시:
"{{9개 도시}}\n동시 타격"
→ "9개 도시"는 주황색(accent), "동시 타격"은 흰색(text)
→ 두 줄로 표시
```

---

## 12. mapScene 스키마 (map_scene 전용)

`map_scene` 타입은 visualization 대신 `mapScene` 필드를 사용합니다.
Remotion의 `remotion/src/map/` 컴포넌트가 렌더링합니다.

### mapType (4종)

| mapType | 용도 | 예시 |
|---------|------|------|
| `location_reveal` | 광역→타겟 위치 줌인 | 한반도 → 영월 청령포 |
| `route_animation` | 경로 순차 그리기 | 유배 경로, 진격 경로 |
| `territory_overlay` | GeoJSON 영역 페이드인 | 세력 범위, 행정구역 |
| `fly_through` | 키프레임 카메라 이동 | 여러 장소 순차 소개 |

### mapStyle (4종)

| mapStyle | 용도 |
|----------|------|
| `modern_clean` | 현대 콘텐츠, 밝고 깔끔 |
| `historical` | 역사 콘텐츠, 세피아 톤 |
| `dark_cyber` | 기술/미래 콘텐츠, 어두운 톤 |
| `satellite` | 실제 위성 이미지 (드물게) |

### mapScene 필드 스키마

```json
{
  "mapScene": {
    "mapType": "location_reveal",
    "mapStyle": "historical",
    "title": "청령포 — 단종 유배지",
    "source": "강원도 영월군",
    "camera": {
      "keyframes": [
        { "frame": 0, "center": [127.5, 37.4], "zoom": 7 },
        { "frame": 60, "center": [128.456, 37.172], "zoom": 13 }
      ],
      "easing": "easeInOutCubic"
    },
    "markers": [],
    "route": {},
    "territories": [],
    "labels": []
  }
}
```

### 주의사항

- `map_scene`은 `visualization` 대신 `mapScene` 필드 사용
- `has_image_asset`는 항상 `false` (지도 자체가 시각화)
- 카메라 키프레임의 `center`는 `[경도, 위도]` 순서 (GeoJSON 표준)
- 같은 지역의 연속 맵 씬은 피한다 (대신 `fly_through`로 통합)
