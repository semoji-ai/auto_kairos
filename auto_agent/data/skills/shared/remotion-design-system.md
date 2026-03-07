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

### UI 컴포넌트 (13개)

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

모든 시각화는 **creative 필드 + 데이터 구조**로 자동 결정된다.

### 자동 레이아웃 감지 (CreativeScene)

렌더러가 아래 순서로 레이아웃을 자동 결정:

1. **displayMode 명시** → logo_grid, pie_chart, line_chart
2. **emphasis/reveal 조합** → quote, split, person_card, counter
3. **데이터 구조** → items/values 수, chartConfig 존재, descriptions 유무
4. **기본값** → headline_only

| 데이터 패턴 | 자동 감지 레이아웃 | 조건 |
|------------|------------------|------|
| displayMode="logo_grid" | 로고 그리드 | items가 기업명 |
| chartConfig.type="pie" | 파이 차트 | items + values (%) |
| chartConfig.type="line" | 라인 차트 | items(시간축) + values |
| emphasis="quote" | 인용문 | items[0]이 인용문 |
| emphasis="contrast" + items 2개 | VS 분할 | 좌/우 비교 |
| emphasis="person" + items 2개+ | 인물 카드 | 이미지/실루엣 |
| emphasis="number"/"count" | 큰 숫자 카운터 | headline에 {{숫자}} |
| emphasis="sequence" + descriptions | 타임라인 | 시간순 이벤트 |
| items 3개+ + values 3개+ | 바 차트 | 카테고리별 비교 |
| items 6개+ | 아이콘 그리드 | 개념 나열 |
| items 3~5개 | 리스트 | 순서/목록 |
| 그 외 | headline_only | 텍스트 강조 |

### 보완 메커니즘 (normalizeCreative)

creative 필드가 불완전할 때 렌더러가 자동 보정:
- **headline 없음** → title에서 생성
- **emphasis 없음** → 데이터 패턴에서 추론 (values 있으면 number, 아니면 none)
- **reveal 없음** → items 3개+ 이면 stagger, 아니면 fade_in
- **mood 없음** → informative 기본값

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
    "placement": "background | center | left | right | inline",
    "opacity": 0.8,
    "overlay": true,
    "usage": "asset | background",
    "characters": ["characters/variant_id.png"],
    "license": null
  }
}
```

**source 유형:**
- `wikimedia` — Wikimedia Commons 검색 (CC 라이선스)
- `search` — 웹 이미지 검색 (Serper/Pixabay)
- `generate` — FAL.ai로 AI 이미지 생성
- `character` — character_casting.json의 캐릭터 이미지 활용

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
