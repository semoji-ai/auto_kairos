---
name: creative-direction-patterns
description: Reference for creative patterns, field separation rules, scene continuity, and color semantics
invocation: agent-only
---

## 6. Creative 패턴 레퍼런스

렌더러는 creative 필드(reveal, emphasis, mood, headline)만으로 렌더링을 결정한다.
아래는 자주 쓰이는 creative 패턴 조합 예시:

| 패턴 | 용도 | reveal | emphasis | 핵심 효과 |
|------|------|--------|----------|----------|
| 항목 누적 → 총수 | 여러 항목 → 강조 숫자 | stagger_then_flash | count | 항목별 등장 → 전체 플래시 → 빅넘버 |
| 극적 숫자 공개 | 맥락 → 큰 숫자 | dramatic_pause | number | 맥락 텍스트 → 정지 → 큰 숫자 줌인 |
| 단계별 공개 | 순서 나열 | stagger / build_up | sequence | 각 단계가 하나씩 드러남 |
| 화면 분할 대비 | A vs B | split_reveal | contrast | 좌우 분할, 대비되는 정보 |
| 스포트라이트 공개 | 인물/핵심 강조 | spotlight | person / keyword | 어둠 속에서 핵심 정보만 빛남 |
| 다수 숫자 동시 카운트 | 여러 통계 | parallel | number | 여러 통계가 동시에 카운팅 |
| 인용문 | 발언/인용 | typewriter / spotlight | quote | 타이핑 효과 + 출처 표시 |
| 헤드라인 텍스트 | 임팩트 한 줄 | fade_in / zoom_in | keyword | AccentText 강조 |
| 이미지 주도 씬 | 시각 임팩트 | fade_in / spotlight | visual | fullscreen 이미지 + 최소 텍스트 |
| 인물 갤러리 | 다수 인물 소개 | stagger / cascade | person | inline 이미지 + items 1:1 매핑 |

### 배경 레이어 가이드라인

creative direction은 텍스트 연출뿐 아니라 **배경 레이어**(맵, 이미지)도 설계한다.
별도 타입 지정 없이, concept에 의도를 서술하고 관련 데이터 필드를 채운다.

#### 맵 배경 — mapScene 필드 작성

concept에 "지도 위에...", "위치가 표시되며..." 등 지리적 연출을 서술하면
visual-composer가 씬에 `mapScene` 필드를 함께 작성한다.

| mapType | 상황 |
|---------|------|
| `location_reveal` | 도시/기지 타격 위치, 특정 장소 공개 |
| `route_animation` | 군대/미사일 이동 경로, 수송 루트 |
| `territory_overlay` | 세력 범위, 점령지, 영토 변화 |
| `fly_through` | 지역 전체 조망, 광역 시각화 |

#### 이미지 — imageAsset 필드 작성 (6종 배치)

이미지는 **배경**, **에셋**, **장면의 주인공** 등 다양한 역할을 한다.
concept에 이미지 활용 의도를 서술하면 visual-composer가 `imageAsset` 필드를 작성한다.

imageAsset 스키마:
```json
{
  "source": "search" | "generate" | "wikimedia" | "character",
  "query": "검색어/프롬프트",
  "placement": "fullscreen" | "background" | "center" | "left" | "right" | "inline",
  "opacity": 0.3,
  "itemImages": true  // inline 전용: items와 1:1 매핑
}
```

**배치 유형별 가이드:**

| placement | 역할 | concept 서술 패턴 | opacity |
|-----------|------|------------------|---------|
| `fullscreen` | 이미지가 메시지 그 자체 | "이 장면이 화면을 가득 채우며..." | 0.8~1.0 |
| `background` | 분위기 보조 | "사진 배경 위에...", "분위기 이미지 위에..." | 0.10~0.50 |
| `center` | 이미지가 중앙 핵심 요소 | "중앙에 이미지를 배치하고 위아래에 텍스트..." | 0.7~1.0 |
| `left` / `right` | 한쪽에 에셋 배치 | "한쪽에 인물 이미지를 배치하고..." | 0.7~1.0 |
| `inline` | 아이템별 1:1 이미지 매핑 | "각 인물/상품 옆에 이미지를 함께..." | 1.0 |

**① fullscreen — 이미지 주도 씬** (텍스트 최소 또는 없음):
concept에 "화면 전체를 채우는...", "이 장면을 보세요" 등 시각 묘사를 서술.

| 상황 | source | 예시 |
|------|--------|------|
| 역사적 순간 | search | "1987 black monday wall street" |
| 감정 전환점 | generate | "dark storm clouds clearing, hope" |
| 챕터 브릿지 | generate / search | 분위기 전환 이미지 |

fullscreen 씬은 `headline_only` layout과 함께 사용. headline은 짧은 한 줄 또는 생략.

**② background — 배경 분위기**:

| 상황 | source | 예시 query |
|------|--------|-----------|
| 실제 사건 장면 | search | "Iran aerial strike night" |
| 역사 사진 | search | "Iranian revolution 1979" |
| 추상적/개념 배경 | generate | "dark military command center, cinematic" |
| 감정/분위기 연출 | generate | "hopeful sunrise over city, warm tones" |

**③ center — 중앙 에셋**:

| 상황 | source | 예시 |
|------|--------|------|
| 제품/오브젝트 쇼케이스 | search / generate | ETF 상품, 핵심 아이템 |
| 상징물 강조 | generate | 금괴, 트로피, 방패 |

**④ left / right — 사이드 에셋**:

| 상황 | source | placement | 예시 |
|------|--------|-----------|------|
| 실존 인물 초상 | wikimedia / search | left/right | 워런 버핏, 잭 보글 |
| 핵심 오브젝트 | generate / search | left/right | 금괴, 주식 증서, 건물 |
| 캐릭터 일러스트 | character | left/right | 스타일 맞춤 캐릭터 |
| 상징적 사물 | generate | left/right | 저금통, 로켓, 방패 |

**⑤ inline — 아이템별 이미지**:

| 상황 | source | 예시 |
|------|--------|------|
| 인물 다수 나열 | wikimedia | 투자 대가 3인 (각각 초상) |
| 제품/상품 비교 | search | ETF 3종 (각각 로고) |
| 국가 대표 이미지 | search | 3개국 도시 사진 |

inline 사용 시 `itemImages: true` 설정. items 배열과 이미지가 1:1 매핑.

**적극 활용 원칙:**
- 텍스트만 있는 씬은 시각적으로 빈약 → 이미지를 넣어 시각적 풍성함 확보
- 나레이션이 시각적 대상을 **직접 묘사**하면 → `fullscreen` (이미지가 주인공)
- 나레이션에 구체적 대상(인물, 사물, 장소)이 언급되면 에셋(`left`/`right`/`center`)으로 배치
- 아이템마다 고유한 시각 대상이 있으면 → `inline` (itemImages: true)
- 추상적 분위기만 필요하면 배경(`background`)으로 깔기
- **전체 씬의 70% 이상에 시각 에셋(이미지/차트/아이콘/로고) 존재 목표**

### 차트 레이아웃 자동 추론

렌더러는 creative 필드와 데이터 구조를 조합하여 차트 타입을 자동 결정한다.
별도 타입 지정 없이 아래 패턴이 작동:

| 의도 | creative 필드 | 필요 데이터 | 결과 |
|------|-------------|-----------|------|
| 시간 흐름 | emphasis="sequence" | descriptions[] | Timeline |
| A vs B | emphasis="contrast" 또는 reveal="split_reveal" | left + right | Compare |
| 데이터 테이블 | — | items에 파이프(\|) 구분 | Table |
| 프로세스도 | — | items + relations[] | Diagram |
| 수치 비교 | emphasis="number" | items + values (2+) | Bar chart |
| 그 외 | — | — | CreativeScene 자동 레이아웃 |

creative direction 작성 시 emphasis/reveal만 맞게 설정하고 데이터를 적절히 구조화하면
렌더러가 적절한 차트 컴포넌트를 자동 선택한다.

---

## 8. 필드 역할 분리 — 중복 방지 원칙

**핵심**: 화면에 표시되는 텍스트는 `headline` 하나에서만 관리한다.

### 필드별 역할

| 필드 | 역할 | 화면 표시 | 예시 |
|------|------|----------|------|
| `headline` | **유일한 화면 표시 텍스트** (AccentText) | ✅ 항상 | `"{{36}}년간의 지배\n이란의 신정 권력"` |
| `title` | 데이터 차트 헤더 (차트 타입만) / 크리에이티브 타입에서는 메타 라벨 | 차트만 ✅ | 차트: `"국제유가 급등"`, 크리에이티브: `"알리 하메네이"` |
| `values` | 애니메이션 데이터 (count-up 타겟) | ❌ 별도 표시 안 함 | `[36]` |
| `items` | 보조 맥락 라벨, 데이터 포인트 | 타입별 상이 | `["1989~2026, 최고지도자"]` |

### 타입별 표시 규칙

```
데이터 시각화 타입 (bar_chart, timeline, table, compare 등):
  → title = 차트 헤더로 표시 ✅
  → headline = 오버레이 강조 텍스트 ✅
  → title ≠ headline (다른 표현이어야 함)
  → 예: title="국제유가 급등", headline="{{$67 → $79}}\n하룻밤 사이 급등"

크리에이티브 타입 (dramatic_number, impact_count, spotlight_reveal 등):
  → title = 메타데이터 (화면에 직접 표시 안 됨)
  → headline = 유일한 화면 텍스트 ✅
  → values = 애니메이션 엔진에만 전달 (count-up 등)
  → 예: title="알리 하메네이", headline="{{36}}년간의 지배", values=[36]

title_card 타입:
  → title = 메타 라벨 ("Ch.3 도입" 등, 표시 안 됨)
  → headline = "CHAPTER 3\n{{45년의 적대}}" (유일한 표시)
```

### 금지 패턴 (Anti-patterns)

```
❌ title과 headline이 같은 텍스트
   title: "하루 만에 궤멸된 이란 군부"
   headline: "하루 만에 {{궤멸된}} 이란 군부"
   → 화면에 동일 문구가 상하로 중복

❌ values의 숫자가 items에도 중복
   items: ["1", "궤멸 소요 시간"]
   values: [1]
   → "1"이 라벨과 데이터에 모두 존재

❌ dramatic_number에 values 2개 이상
   values: [36, 2]
   → 어떤 숫자를 극적으로 보여줄지 불명확
   → 핵심 숫자 1개만, 나머지는 subtitle이나 items로

❌ items가 headline과 동일
   headline: "거의 {{모든 무기}}가\n이란을 향했다"
   items: ["거의 {{모든 무기}}가\n이란을 향했다"]
   → 대부분 컴포넌트가 headline + items 둘 다 렌더링하므로 같은 텍스트가 위아래 중복
   → headline만으로 충분하면 items: [] (빈 배열)

✅ 올바른 예시
   title: "알리 하메네이"         ← 메타 라벨
   headline: "{{36}}년간의 지배"   ← 화면 표시 (유일)
   values: [36]                  ← count-up 애니메이션 데이터
   items: ["1989~2026"]          ← 보조 맥락 (headline과 다른 정보)
   subtitle: "겨우 2번째 최고지도자" ← 보조 정보
```

---

## 9. 씬 연속성 규칙

### 같은 reveal 3회 연속 금지

```
나쁜 예: stagger → stagger → stagger → stagger
좋은 예: stagger → dramatic_pause → count_up → stagger_then_flash
```

### mood 흐름 설계

전체 영상에서 mood가 자연스러운 감정 곡선을 그리도록:

```
Act 1 (도입):    informative → suspense
Act 2 (전개):    dramatic ↔ informative (교차)
                 → urgent (클라이맥스)
Act 3 (결말):    somber → contemplative
```

### 시각적 다양성

연속 3씬 이상 같은 reveal + emphasis 조합 금지.
reveal과 emphasis 조합이 다르면 시각적으로 다르게 느껴진다.

---

## 10. 컬러 시맨틱

creative의 mood에 따라 씬별 accent 색상 결정:

| mood | 권장 accentColor | 의미 |
|------|-----------------|------|
| dramatic | `#F59E0B` (warning) | 긴장, 경고 |
| triumphant | `#10B981` (accent) | 성장, 성취 |
| urgent | `#EF4444` (danger) | 위험, 긴박 |
| informative | `#3B82F6` (primary) | 정보, 신뢰 |
| somber | `#71717A` (muted) | 엄숙, 절제 |
| contemplative | `#3B82F6` (primary) | 사색, 깊이 |
| suspense | `#F59E0B` (warning) | 긴장, 미스터리 |
