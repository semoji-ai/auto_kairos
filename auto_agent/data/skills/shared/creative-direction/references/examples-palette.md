---
name: creative-direction-examples
description: Reference examples and motion/visual palette for creative direction decisions
invocation: agent-only
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

### 아이템 블록 에셋

items 각각에 이미지를 매핑하여 아이콘/번호 대신 **실제 이미지를 아이템 에셋으로 활용**할 수 있다.
`visualization.images` 배열(items와 1:1 대응)로 설정하면 렌더러가 `ImageBadge`로 표시한다.

```
적합한 상황:
- items가 인물 목록 → 각각의 초상화를 ImageBadge로
- items가 건물/장소 → 각각의 실물 사진을 ImageBadge로
- emphasis="person" + items 2개+ → 인물 카드 형태
```

imageAsset에 `"itemImages": true`를 설정하면 이미지 생성 스크립트가 items별 개별 이미지를 생성한다.

---

## 주의사항

- 나레이션 텍스트 자체는 절대 수정하지 않는다 (headline은 별도 필드)
- headline은 나레이션을 **시각화용으로 재구성**한 것 (표시용)
- 같은 creative 조합(reveal + emphasis + mood)이 3회 연속 금지
- concept은 렌더러 개발자/디버깅용 참조 문서. 실제 렌더링 로직에 직접 사용되지 않음
- 모든 creative 타입은 SimpleScene.tsx의 기존 디자인 토큰(C.bg, C.text, C.accent) 위에서 동작
