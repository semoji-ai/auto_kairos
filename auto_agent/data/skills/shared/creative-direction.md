# Creative Direction

씬별 창의적 연출을 설계하는 핵심 가이드라인입니다.
기본 타이포그래피 프리셋 위에서 각 장면의 **내러티브 아크, 정보 공개 방식, 감정적 강조**를 설계합니다.

**참조 에이전트**: visual-composer

---

## 1. 핵심 철학

**모든 장면은 하나의 미니 영화다.**

기존의 rigid한 19개 타입 배정이 아니라, 각 씬의 나레이션을 분석하여:
- **이 장면이 전달하려는 것이 무엇인가?** (정보, 감정, 긴장)
- **가장 임팩트 있는 표현 방식은?** (텍스트, 숫자, 시각화, 구조도)
- **정보를 어떤 순서로 공개할 것인가?** (점진적, 동시, 반전, 축적)

이 세 가지 질문에 답하여 `creative` 필드를 설계한다.

---

## 2. Creative 필드 스키마

```json
{
  "visualization": {
    "title": "동시 타격",
    "items": ["테헤란", "이스파한", ...],
    "values": [9],

    "creative": {
      "concept": "도시 이름이 하나씩 나타나고, 모두 동시에 번쩍이며, 큰 숫자 9가 화면을 채운다",
      "reveal": "stagger_then_flash",
      "emphasis": "count",
      "headline": "{{9개 도시}}\n동시 타격",
      "mood": "dramatic"
    }
  }
}
```

### creative 필드 상세

| 필드 | 타입 | 설명 |
|------|------|------|
| `concept` | string | 1-2문장으로 시각 연출 의도 서술. 렌더러가 참조하는 핵심 지시문 |
| `reveal` | enum | 정보 공개 패턴 (아래 3번 참조) |
| `emphasis` | enum | 핵심 강조 요소 (아래 4번 참조) |
| `headline` | string | 화면에 표시될 핵심 텍스트. `{{키워드}}`는 accent 색상, `\n`은 줄바꿈 |
| `mood` | enum | 감정적 톤 (아래 5번 참조) |

---

## 3. reveal — 정보 공개 패턴 (12종)

| reveal | 설명 | 적합한 상황 |
|--------|------|------------|
| `fade_in` | 전체가 한 번에 페이드인 | 단일 메시지, 인용문 |
| `stagger` | 항목이 순차적으로 등장 | 리스트, 타임라인, 비교 |
| `stagger_then_flash` | 순차 등장 → 전체 동시 강조 | 누적 효과 (9개 도시 등) |
| `cascade` | 위에서 아래로 폭포처럼 | 순위, 우선순위 |
| `count_up` | 숫자가 카운팅되며 증가 | 통계, 수치 강조 |
| `typewriter` | 글자가 하나씩 타이핑 | 핵심 문장, 결론 |
| `spotlight` | 어두운 화면에서 핵심만 밝아짐 | 인물, 핵심 개념 |
| `split_reveal` | 화면이 분할되며 양쪽 동시 공개 | A vs B, 대비 |
| `zoom_in` | 작은 것에서 크게 확대 | 핵심 수치, 디테일 |
| `build_up` | 요소가 쌓여가며 최종 형태 완성 | 프로세스, 구조 |
| `dramatic_pause` | 잠시 멈춤 후 핵심 공개 | 반전, 놀라운 사실 |
| `parallel` | 두 가지가 동시에 진행 | 대비, 동시 사건 |

---

## 4. emphasis — 핵심 강조 요소 (8종)

| emphasis | 설명 | 렌더링 효과 |
|----------|------|------------|
| `number` | 큰 숫자 강조 | 카운트업 + 스케일 확대 + accent 색상 |
| `keyword` | 핵심 단어 강조 | accent 색상 + 약간의 스케일 |
| `count` | 항목 수 강조 | 항목 등장 후 총 개수 빅넘버 |
| `contrast` | 대비/차이 강조 | 분할 레이아웃 + 색상 대비 |
| `sequence` | 순서/과정 강조 | 화살표/연결선 + 순차 등장 |
| `person` | 인물 강조 | 서클 이미지/배지 + 이름 |
| `quote` | 발언 강조 | 큰따옴표 + 발화자 |
| `none` | 특별한 강조 없음 | 균등한 정보 전달 |

---

## 5. mood — 감정적 톤 (7종)

| mood | 설명 | 시각적 표현 |
|------|------|------------|
| `dramatic` | 극적, 긴장 | 빠른 등장, 강한 accent, 큰 스케일 |
| `contemplative` | 사색적, 차분 | 느린 페이드, 낮은 대비, 여백 |
| `urgent` | 긴박, 위급 | 빠른 스태거, 경고색(danger), 타이트 |
| `triumphant` | 승리, 성취 | 스케일 확대, 밝은 accent, 카운트업 |
| `somber` | 엄숙, 슬픔 | 느린 페이드, 뮤트 색상, 여백 |
| `informative` | 정보 전달 | 균등 스태거, 중립 색상, 깔끔 |
| `suspense` | 서스펜스 | 느린 공개, 어두운 톤, 극적 일시정지 |

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

#### 이미지 배경 — imageAsset 필드 작성

concept에 "사진 배경 위에...", "실제 장면 이미지 위에..." 등 서술하면
visual-composer가 씬에 `imageAsset` 필드를 함께 작성한다.

| 상황 | source | 예시 query |
|------|--------|-----------|
| 실제 사건 장면 | search | "Iran aerial strike night" |
| 역사 사진 | search | "Iranian revolution 1979" |
| 인물 | search | "Ali Khamenei portrait" |
| 추상적/개념 배경 | generate | "dark military command center, cinematic" |

imageAsset 스키마: `{ "source": "search"|"generate", "query": "검색어/프롬프트" }`

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

## 7. Creative Direction 설계 프로세스

Visual Composer가 각 씬의 creative 필드를 설계할 때 따르는 3단계:

### Step 1: 내러티브 분석

나레이션 텍스트를 읽고 핵심 요소를 식별:

```
질문:
- 이 씬의 핵심 전달 내용은? (숫자, 사건, 인물, 감정, 비교)
- 시청자가 느껴야 할 감정은? (긴장, 놀라움, 슬픔, 이해)
- 이전/이후 씬과의 관계는? (강화, 대비, 전환)
```

### Step 2: 시각 컨셉 설계

핵심 요소에 맞는 시각적 접근법 결정:

```
숫자가 핵심 → emphasis: "number", reveal: "count_up" 또는 "dramatic_pause"
항목 나열이 핵심 → reveal: "stagger" 또는 "stagger_then_flash"
대비가 핵심 → reveal: "split_reveal", emphasis: "contrast"
인물이 핵심 → emphasis: "person", reveal: "spotlight"
사건이 핵심 → reveal: "dramatic_pause", mood: "dramatic"
과정이 핵심 → reveal: "build_up", emphasis: "sequence"
```

### Step 3: headline 작성

나레이션 텍스트를 화면용 핵심 헤드라인으로 변환:

```
규칙:
1. 나레이션 문장을 그대로 쓰지 않는다
2. 임팩트 있는 짧은 구문으로 변환
3. 핵심 단어에 {{}} 마크업 적용
4. \n으로 적절한 줄바꿈
5. 2-3줄 이내

예시:
나레이션: "미국은 2026년 2월 28일 새벽, 이란의 9개 주요 도시를 동시에 타격했습니다."
headline: "{{9개 도시}}\n동시 타격"

나레이션: "이 작전으로 민간인 사망자가 2,400명에 달했습니다."
headline: "민간인 사망자\n{{2,400명}}"
```

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

---

## 11. Creative Direction 예시

### 예시 1: 숫자 임팩트

```
나레이션: "이 폭격으로 2,400명의 민간인이 사망했습니다."

creative:
  concept: "어두운 화면에 '민간인 사망자' 텍스트가 먼저 나타나고,
            잠시 정적 후 '2,400' 숫자가 카운팅되며 크게 나타난다"
  reveal: "dramatic_pause"
  emphasis: "number"
  headline: "민간인 사망자\n{{2,400명}}"
  mood: "somber"
```

### 예시 2: 항목 누적

```
나레이션: "미국은 테헤란, 이스파한, 반다르아바스 등 9개 도시를 동시에 타격했습니다."

creative:
  concept: "도시 이름이 하나씩 그리드에 나타나고,
            모두 표시되면 동시에 번쩍이며,
            큰 숫자 '9'가 화면 중앙에 나타난다"
  reveal: "stagger_then_flash"
  emphasis: "count"
  headline: "{{9개 도시}}\n동시 타격"
  mood: "dramatic"
```

### 예시 3: 인물 소개

```
나레이션: "수양대군은 어린 조카의 왕위를 빼앗기로 결심합니다."

creative:
  concept: "어두운 배경에서 수양대군의 실루엣이 스포트라이트처럼
            드러나고, '왕위 찬탈'이라는 텍스트가 accent로 강조된다"
  reveal: "spotlight"
  emphasis: "person"
  headline: "수양대군\n{{왕위 찬탈}}의 결심"
  mood: "suspense"
```

### 예시 4: 대비

```
나레이션: "세조실록에는 자살로 기록되어 있으나,
          숙종실록에는 사약을 받은 것으로 기록되어 있습니다."

creative:
  concept: "화면이 좌우로 분할되어,
            왼쪽에 '세조실록: 자살', 오른쪽에 '숙종실록: 사약'이
            동시에 나타나며 대비를 보여준다"
  reveal: "split_reveal"
  emphasis: "contrast"
  headline: "세조실록 {{자살}}\nvs\n숙종실록 {{사약}}"
  mood: "suspense"
```

### 예시 5: 타임라인

```
나레이션: "계유정난, 단종 양위, 사육신 사건...
          불과 3년 사이에 벌어진 일입니다."

creative:
  concept: "타임라인 항목이 빠르게 쌓이며,
            마지막에 '3년' 숫자가 크게 나타나
            짧은 기간에 많은 일이 있었음을 강조"
  reveal: "build_up"
  emphasis: "count"
  headline: "불과 {{3년}}"
  mood: "dramatic"
```

---

## 12. 렌더러 연동

렌더러(CreativeScene)는 creative 필드만으로 렌더링을 결정한다:

1. **reveal로 등장 애니메이션 결정** (stagger, zoom_in, dramatic_pause 등)
2. **emphasis로 강조 효과 적용** (number→카운트업, quote→인용문, sequence→번호배지)
3. **headline으로 AccentText 렌더링** (`{{}}` 파싱 → accent 색상)
4. **mood로 전체 톤 조절** (색상, 속도, 글로우)
5. **items/values 데이터로 레이아웃 자동 감지** (그리드, 리스트, 바차트 등)

렌더링은 creative 필드만으로 결정된다.
concept은 creative 필드 설계의 근거가 되는 자연어 의도 서술이다.

---

## 13. 연출 팔레트

렌더러가 사용할 수 있는 재료 목록이다.
concept에 의도를 서술하면 렌더러가 이 팔레트에서 적절한 조합을 선택한다.
**기계적 1:1 매핑이 아니라, 씬의 내러티브에 맞게 자유롭게 조합한다.**

### 모션 효과

| 효과 | 느낌 |
|------|------|
| fadeRise | 부드러운 등장. 가장 기본 |
| fadeSlide | 옆에서 밀려오는 등장 |
| scale | 작아졌다 커지는 등장 |
| overshootScale | 목표 크기를 살짝 넘겼다 돌아오는 등장. 탄력감 |
| bounceIn | 통통 튀는 등장. 에너지 |
| shake | 좌우 진동. 불안정함, 충격 |
| pulse | 계속 미세하게 커졌다 작아지는 반복. 살아 있는 느낌 |
| glitch | 위치와 색이 흔들리는 노이즈. 디지털, 오류 |
| typewriter | 글자가 한 자씩 타이핑. 메시지 전달감 |
| fadeOut | 사라지는 퇴장 |
| spring | 물리적으로 자연스러운 모션 |
| countUp | 숫자가 올라가는 카운팅 |
| lineExpand | 선이 늘어나는 효과 |
| staggerDelay | 여러 항목의 시차 등장 간격 계산 |

### 시각 요소

| 요소 | 역할 |
|------|------|
| AccentText | `{{키워드}}` 강조 텍스트 |
| Card | 정보를 담는 카드 컨테이너 |
| CircleBadge | 텍스트를 원 안에 (번호, 이니셜) |
| ImageBadge | 이미지를 원 안에 (인물, 사물) |
| IconBadge | Lucide 아이콘을 원 안에 (개념, 카테고리) |
| FlagBadge | 국기를 원 안에 (국가) |
| LogoBadge | 브랜드 로고를 원 안에 (기업, 조직) |
| Icon | 아이콘 단독 사용 |
| ProgressBar | 비율/진행도 시각화 |
| Tag | 키워드 태그 칩 |
| Divider | 구분선 |
| StatusDot | 상태 표시 (긍정/부정/중립/경고) |
| Pill | 선택 항목 필 |

### 아이콘 (Lucide)

개념을 시각적으로 빠르게 인지시키는 도구.
Shield, Brain, TrendingUp, Swords, Crown, Globe, DollarSign, Users, AlertTriangle, Zap, Flame, Target 등.
**장식이 아니라 정보 인식을 돕는 용도로만 사용.**

### 배지 선택 기준

이미지가 있다 → ImageBadge
기업/조직이다 → LogoBadge
국가가 중요하다 → FlagBadge
개념을 표현한다 → IconBadge
텍스트/숫자로 충분하다 → CircleBadge

---

## 주의사항

- 나레이션 텍스트 자체는 절대 수정하지 않는다 (headline은 별도 필드)
- headline은 나레이션을 **시각화용으로 재구성**한 것 (표시용)
- 같은 creative 조합(reveal + emphasis + mood)이 3회 연속 금지
- concept은 렌더러 개발자/디버깅용 참조 문서. 실제 렌더링 로직에 직접 사용되지 않음
- 모든 creative 타입은 SimpleScene.tsx의 기존 디자인 토큰(C.bg, C.text, C.accent) 위에서 동작
