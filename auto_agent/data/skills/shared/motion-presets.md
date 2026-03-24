---
name: motion-presets
description: 씬별 모션 그래픽 프리셋 정의. script-director가 원고 작성 시 선택하고, Remotion 렌더러가 해석
---

# Motion Presets

나레이션의 의미와 모션을 직접 연결하는 프리셋 시스템입니다.
script-director가 씬 작성 시 `motion` 필드에 프리셋 이름 하나를 지정하면,
Remotion 렌더러가 구체적인 애니메이션 조합으로 변환합니다.

---

## 프리셋 목록 (15종)

### 1. 기본 등장 계열

#### `fade_rise`
**가장 기본적인 등장.** 아래에서 위로 부드럽게 올라오며 나타남.
- 용도: 일반 정보 전달, 특별한 연출이 필요 없는 씬
- 조합: opacity 0→1 + translateY 25→0 + easeOut
- 주의: 전체의 30% 이하로 사용. 너무 많으면 단조로움

#### `stagger_wave`
**항목이 파도처럼 순차 등장.** 리스트/그리드의 기본 연출.
- 용도: items가 2개 이상인 정보 씬
- 조합: 각 item에 fade_rise + staggerDelay(index × 8프레임)
- 변형: items가 5개 이상이면 stagger gap을 6프레임으로 좁힘

#### `cascade_rank`
**위에서 아래로 폭포처럼 떨어지며 등장.** 순위/우선순위 강조.
- 용도: rank_list, 순위 데이터, 중요도 순서
- 조합: 각 item이 overshootScale + translateY(-20→0) + stagger
- 1위 항목은 약간 더 큰 scale(1.05)로 강조

### 2. 숫자/데이터 강조 계열

#### `count_and_grow`
**숫자가 카운팅되면서 바/차트가 동시에 성장.**
- 용도: bar, line 차트 씬, 수치 비교
- 조합: countUp(0→target) + bar height interpolate + easeOutCubic
- 핵심: 숫자와 시각화가 동시에 움직여야 임팩트

#### `number_spotlight`
**화면 중앙에 큰 숫자가 스프링으로 튕기며 등장.**
- 용도: metric_spotlight, counter, 핵심 수치 하나
- 조합: spring(damping:150, stiffness:100) + scale(0.5→1) + glow textShadow
- 배경: 어두운 spotlight gradient

#### `pie_spin`
**파이 차트가 시계방향으로 채워지며 라벨이 순차 등장.**
- 용도: pie, donut 차트 씬
- 조합: arc sweep(0°→360°) + label stagger fade(slice 완성 후)

### 3. 감정/드라마 계열

#### `dramatic_shake`
**화면이 짧게 흔들리며 경고/충격을 표현.**
- 용도: 위기, 사건, 충격적 수치
- 조합: shake(sin함수, amplitude:4px, 0.5초) + 항목 빠른 stagger(gap:4)
- mood: dramatic 또는 urgent와 함께 사용
- 주의: 전체의 10% 이하. 남용하면 피로감

#### `glitch_alert`
**디지털 글리치 효과 + 색상 왜곡.** 기술/해킹/위험 테마.
- 용도: 사이버 보안, 해킹, 시스템 오류 관련 씬
- 조합: glitch(sin+cos 왜곡) + 색 채널 분리(2px) + 0.3초 후 안정
- 주의: 매우 강한 효과. 전체의 5% 이하

#### `bounce_celebrate`
**탄성 있게 튕기며 등장.** 성취/결과/긍정적 순간.
- 용도: 성과 발표, 달성, 축하, triumphant mood
- 조합: bounceIn(easeOutBounce) + scale(0→1.1→1) + items stagger
- 분위기: 밝은 accent 색상과 함께

#### `calm_float`
**느리게 떠다니듯 등장.** 여운, 성찰, 마무리.
- 용도: 엔딩, 브리딩 포인트, 감성적 인용문
- 조합: slow fade(30프레임) + pulse(breathing, amplitude:0.02) + 넓은 여백
- mood: contemplative 또는 somber와 함께

### 4. 특수 효과 계열

#### `type_and_draw`
**글자가 타이핑되면서 SVG 선이 함께 그려짐.** 설명/정의 강조.
- 용도: 핵심 문장, 정의, 결론, headline_only
- 조합: typewriter(charPerFrame:2) + SVG underline evolvePath
- headline에 특히 효과적

#### `split_compare`
**화면이 좌우로 분할되며 양쪽이 동시에 슬라이드 인.**
- 용도: before_after, split, A vs B 비교
- 조합: left(slideX: -100→0) + right(slideX: 100→0) + 중앙 구분선 fade
- 양쪽 동시에 움직여야 대비 효과

#### `map_reveal`
**지도가 줌인되며 마커가 순차 등장.**
- 용도: mapScene이 있는 씬
- 조합: zoom(wide→target, bezier ease) + marker stagger(fade+scale)
- 마커 완성 후 라벨 페이드인

#### `cinematic_fade`
**느린 크로스페이드. 텍스트 없이 이미지만.**
- 용도: cinematic 레이아웃 전용
- 조합: slow crossfade(45프레임) + vignette + optional grain
- imageAsset.placement: "fullscreen" 필수

#### `build_sequence`
**요소가 하나씩 쌓여가며 최종 구조를 완성.**
- 용도: flow, timeline, 프로세스/과정
- 조합: item별 fadeRise + 연결선/화살표 lineExpand + stagger
- 완성 후 전체가 잠시 함께 pulse

---

## 선택 가이드

### layout × motion 추천 조합

| layout | 1순위 motion | 2순위 | 피할 것 |
|--------|-------------|-------|---------|
| headline_only | type_and_draw | fade_rise | stagger_wave |
| items_grid | stagger_wave | bounce_celebrate | type_and_draw |
| items_list | stagger_wave | cascade_rank | split_compare |
| counter | number_spotlight | count_and_grow | stagger_wave |
| bar / bar_horizontal | count_and_grow | stagger_wave | calm_float |
| pie / donut | pie_spin | fade_rise | dramatic_shake |
| line | count_and_grow | fade_rise | bounce_celebrate |
| rank_list | cascade_rank | stagger_wave | calm_float |
| split / before_after | split_compare | fade_rise | cascade_rank |
| flow / timeline | build_sequence | stagger_wave | number_spotlight |
| metric_spotlight | number_spotlight | dramatic_shake | stagger_wave |
| metric_wall | stagger_wave | count_and_grow | type_and_draw |
| quote / quote_portrait | calm_float | type_and_draw | dramatic_shake |
| person_card | fade_rise | bounce_celebrate | glitch_alert |
| logo_grid | stagger_wave | fade_rise | dramatic_shake |
| cinematic | cinematic_fade | (유일) | 다른 모든 것 |
| card_carousel | stagger_wave | build_sequence | number_spotlight |
| hero_with_context | fade_rise | type_and_draw | split_compare |
| comparison_table | stagger_wave | split_compare | cinematic_fade |
| icon_stat | number_spotlight | fade_rise | glitch_alert |
| stacked_progress | count_and_grow | stagger_wave | type_and_draw |
| annotated_chart | count_and_grow | build_sequence | calm_float |

### mood × motion 궁합

| mood | 잘 맞는 motion | 어울리지 않는 motion |
|------|---------------|-------------------|
| dramatic | dramatic_shake, number_spotlight, split_compare | calm_float |
| contemplative | calm_float, type_and_draw, fade_rise | dramatic_shake, glitch_alert |
| urgent | dramatic_shake, stagger_wave(빠른), count_and_grow | calm_float, cinematic_fade |
| triumphant | bounce_celebrate, number_spotlight, cascade_rank | calm_float, glitch_alert |
| somber | calm_float, fade_rise, cinematic_fade | bounce_celebrate, dramatic_shake |
| informative | stagger_wave, count_and_grow, fade_rise | dramatic_shake, glitch_alert |
| suspense | type_and_draw, fade_rise(느린), number_spotlight | bounce_celebrate |

---

## 연속 규칙

1. **같은 motion 3회 연속 금지** — 시각적 단조로움 방지
2. **fade_rise 비율 30% 이하** — 기본이지만 남용 금지
3. **dramatic_shake + glitch_alert 합산 10% 이하** — 강한 효과는 희소해야
4. **cinematic_fade는 전체의 10~15% 이내** — 정보 전달력 유지
5. **calm_float는 3-5씬마다 1회** — 브리딩 포인트 역할

---

## Remotion 렌더러 매핑

각 프리셋은 `resolveMotion(preset)` 함수로 구체적 애니메이션 파라미터로 변환됩니다.
렌더러는 다음 정보를 반환받습니다:

```typescript
interface MotionConfig {
  // 진입 애니메이션
  entrance: {
    type: 'fade' | 'slide' | 'scale' | 'spring' | 'typewriter';
    duration: number;      // 프레임
    easing: string;        // easingMap 키
    direction?: 'up' | 'down' | 'left' | 'right';
    springConfig?: { damping: number; stiffness: number };
  };
  // 스태거 설정
  stagger?: {
    gap: number;           // 프레임
    pattern: 'sequential' | 'wave' | 'cascade';
  };
  // 강조 효과
  emphasis?: {
    type: 'countUp' | 'shake' | 'glitch' | 'pulse' | 'glow' | 'bounce';
    delay: number;         // entrance 완료 후 딜레이
    duration: number;
  };
  // SVG 효과
  svg?: {
    type: 'line_draw' | 'path_morph';
    duration: number;
  };
  // 배경 효과
  background?: {
    spotlight: boolean;
    vignette: boolean;
    grain: boolean;
  };
}
```

---

## 확장 가이드

새 프리셋 추가 시:
1. 이 파일에 프리셋 정의 추가
2. Remotion의 `resolveMotion.ts`에 매핑 구현
3. 기존 BuildingBlocks 훅 조합으로 구현 가능한지 먼저 확인
4. 불가능하면 새 훅 추가 (BuildingBlocks.tsx)
