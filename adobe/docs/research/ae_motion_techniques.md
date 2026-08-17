# AE 모션그래픽 실전 기법 — 리서치 학습 노트 / 검증 rubric

> 웹 리서치(School of Motion, Mt.Mograph, Motion Array, PremiumBeat, Adobe Help, Evercast, Mister Horse 등) 종합.
> 모션 라이브러리 정교화 근거이자 **gemini 분석·검증의 공통 rubric**.
> 빌더 기준: `cep/com.autokairos.pd/jsx/tylenol/build_from_json.jsx` — 현재 props: `opacity / scale / position / rotationY / trimEnd / textOffset`.
>
> **이 문서의 용도**: analyze(레퍼런스 분석)와 verify(원본↔렌더 대조) 프롬프트에 기법 어휘 rubric으로 주입한다.
> "비슷해 보임"이 아니라 "easeOut인데 overshoot가 빠졌다 / anticipation 없음 / influence 대칭이라 기계적"처럼 **명명된 원칙으로 판정**하기 위함.

---

## 0. 핵심 요약 (rubric 한 줄 정리)

- **비대칭 이징이 정석** — 등장은 도착 측 influence 75~85%(부드러운 착지), 출발 측 33~40%. 대칭 33.33%(Easy Ease 기본)는 기계적.
- **오버슈트는 3키 이상** — start→overshoot(+10~20%)→settle. 2키로는 weight가 안 생김.
- **모든 이동 요소에 모션블러** — shutter angle 180°, phase -90°. 없으면 "인위적"으로 인지.
- **Drop Shadow는 3-스택** — tight + smooth(softness 120) + ambient glow(softness ~400, opacity ~25%). 단일 하드 섀도는 싸 보임.
- **타이밍은 30fps 기준** — snappy 6~10f / standard 12~15f / heavy 18~24f. stagger 2~10f.
- **Animation Composer 교훈** — IN/OUT/TRANSITION 역할 분류 + Duration/Smoothness/Distance 3-슬라이더 추상화.

---

## 1. 이징·애니메이션 원칙 (심화)

### 1-1. 이징 곡선별 수치 (Graph Editor 관점)

| Named Curve | influence_in | influence_out | 대표 duration(30fps) | 주 적용 prop | 효과 |
|---|---|---|---|---|---|
| `easy_ease_default` | 33 | 33 | 15~18f | 범용 | 기준선, 기계적 — 이상 개선 필요 |
| `ease_out_snappy` | 80 | 35 | 8~12f | position, opacity, scale | slow start→fast→soft land (등장) |
| `ease_in_snappy` | 35 | 85 | 6~10f | position, opacity | soft start→accelerating exit (퇴장) |
| `ease_inout_dramatic` | 90 | 90 | 18~24f | scale, position, rotationY | 무게감 있는 등장, 카메라 패닝 |
| `sharp_snap` | 0 (linear) | 0 | 3~5f | opacity, textOffset, trimEnd | 즉각 전환, 비트 싱크, 타이포 팝 |

- Easy Ease 기본 incoming/outgoing influence = **33.33%**, 양끝 velocity 0 px/sec. 단축키 F9 / Shift+F9(in) / Cmd+Shift+F9(out).
- Adobe 공식 ease-out 추천: Keyframe Velocity 다이얼로그에서 Influence **75%**.
- **Value Graph**: 오버슈트·바운스(목표 초과) / 다차원 position(Separate Dimensions). **Speed Graph**: 일반 가감속 / 단일 속성.

### 1-2. 오버슈트 / 바운스

**키프레임 수동 오버슈트(3~4키, scale 기준 30fps):**

| 키프레임 | 값 | 타이밍 |
|---|---|---|
| K1 시작 | 0% | 0f |
| K2 오버슈트 | **110~120%** | 10~12f |
| K3 언더슈트 | **95~98%** | 14~16f |
| K4 안착 | **100%** | 18~20f |

- 오버슈트 비율 = 목표값 **+10~20%**. 언더슈트 간격은 오버슈트의 50% 이하로 점감. settle은 주 동작 완료 후 **6~10f 이내**.
- 표현식 inertial bounce 파라미터(참고): amp 0.1, freq 3.0, decay 5.0, velocity sampling 0.001s. → 빌더는 키프레임 베이크로 근사(표현식 직접 주입 불가).
- 감쇠 바운스: elasticity 0.7(매 바운스 70% 유지), 실용적으로 3~5회.

**프리셋 매핑**: `overshoot_settle` → scale `[0,115,97,100]` @ `[0,10,14,18]f` → scale/position. (현재 `pop_bounce` 3키 = 정석)

### 1-3. 12원칙의 MG 적용 (30fps 프레임 단위)

| 원칙 | 수치 |
|---|---|
| **Anticipation** | 예비동작 3~6f, 주 동작의 10~20% 반대 방향. snappy=2~3f+6~8f, heavy=6~8f+12~15f |
| **Follow-through / Overlap** | 주 동작 후 4~8f. trailing 요소 2~4f 지연. 글자별 1~2f |
| **Squash & Stretch** | squash X +15~30% / Y -10~20%, volume 보존(×≈1.0), 각 극값 2~4f. *scaleX/Y 분리 필요 — 빌더 확장* |
| **Slow In/Out** | 등장 기본값 `ease_out`(influence_in 80, out 35) |

### 1-4. 타이밍/스페이싱 표준 (30fps)

| 동작 유형 | 프레임 | 특징 |
|---|---|---|
| Ultra-snappy pop | 5~6f | 버튼 피드백, 아이콘 강조 |
| Snappy entrance | 8~10f | 타이틀, UI 카드 |
| Standard entrance | 12~15f | 일반 요소(균형) |
| Comfortable/heavy | 18~24f | 무거운 요소, 씬 전환 |
| Dramatic reveal | 24~30f | 히어로 타이틀, 로고 |
| Snappy/Standard exit | 6~10f / 10~15f | 빠른/일반 퇴장 |

**Stagger 딜레이**: 타이트 UI 2~3f / 리스트·카드 4~6f / 히어로 8~10f / 글자별 1~2f.
오버슈트 settle 여유: snappy +4~6f / standard +6~8f / heavy +8~12f.

---

## 2. 트랜지션·키네틱 타이포·셰이프·파티클 (심화)

### 2-1. 트랜지션

| 기법 | 핵심 | matchName / 값 | 길이 | 빌더 |
|---|---|---|---|---|
| **Linear Wipe** | 방향성 와이프 | `ADBE Linear Wipe` (Completion -0001, Angle -0002 기본90°, Feather -0003 20~80) | 8~15f, Easy Ease | Effect 추가 확장 필요 |
| **줌(Crash Zoom)** | scale + 모션블러 | scale 100→115~130→(다음)70→100, shutter 180°, Motion Tile 550/Mirror | 8~14f | **scale 기본 가능** + MB 토글 코드 |
| **셰이프 모핑** | path 보간 | 양쪽 정점 수 동일 필수, Bezier 변환 후, first vertex 정렬 | 12~20f | `vertices[]` 신규 prop 확장 |
| **Gradient Wipe/리퀴드** | `ADBE Gradient Wipe` + Fractal Noise | Softness 20~60% | 12~20f | Effect 확장 필요 |

### 2-2. 키네틱 타이포 (Text Animator)

Range Selector matchName: `ADBE Text Animators` > `ADBE Text Animator` > `ADBE Text Selectors` > `ADBE Text Selector`. 핵심: **Offset** `ADBE Text Percent Offset`(-100~+100), Start/End `ADBE Text Percent Start/End`, Shape `ADBE Text Range Shape`. per-char: Opacity/Position/Scale/Rotation/Blur(`ADBE Text Opacity` 등).

| 스타일 | 설정 | 길이 |
|---|---|---|
| **type-on** | Offset -100→+100, Shape=Square(1), Opacity 0→100 + Blur 10→0 | 글자수 × 2~4f (권장 3f/char) |
| **reveal** | Shape=Ramp Up, Ease High 70~100%, sweep | 18~30f |
| **pop-in word** | Units=Words, Scale 120→100 + Opacity 0→100 | 단어별 6~10f |

**빌더**: `textOffset` prop이 Range Selector Offset 제어인지 확인 후 `shape/easeHigh/staggerFrames` 추가로 확장.

### 2-3. 셰이프 빌드 / 드로잉 (Trim Paths)

matchName: `ADBE Vector Filter - Trim` > Start `ADBE Vector Trim Start` / **End** `ADBE Vector Trim End` / Offset `ADBE Vector Trim Offset`.

| 기법 | Start | End | 길이 | ease |
|---|---|---|---|---|
| draw-on | 0 고정 | 0→100 | 12~20f | Easy Ease Out |
| 역방향 지우기 | 0→100 | 100 고정 | 12~20f | Easy Ease In |
| 중앙→양쪽 | 50 고정 | 동시 확장 | 10~16f | Linear |
| 순차 다중 stroke | — | 각 6~12f, stagger 4~6f | — | — |

**빌더**: `trimEnd` 존재 → **단일 draw-on 즉시 가능**. 다중 순차는 `trimEnd[]`+stagger, 양방향은 `trimStart` 추가.

### 2-4. 파티클 (CC Particle World)

Cycore 번들 — ADBE matchName 미공개, effect 이름 문자열로 접근(영문 AE 기준). 디졸브 레시피: Birth Rate 버스트(0→25→0), Longevity 2~3s, Velocity 0.5, Gravity 0→0.2, Particle Type=Textured Quadpolygon(원본 레이어), Birth/Death Size 0.08/0.04, Opacity 100→0. **빌더**: `particlePreset: "dissolve"|"burst"|"float"` 신규 prop + preset 블록.

---

## 3. 프리미엄 폴리시 이펙트 (심화)

현재 적용 중: Drop Shadow softness 120, Add Grain 0.4.

### 3-1. Drop Shadow 3-스택 (`ADBE Drop Shadow`)

| 레이어 | Color | Distance | Softness | Opacity | 목적 |
|---|---|---|---|---|---|
| ① Tight | 검정 | 4~8px | 30~50 | 60~70% | 밀착 그림자, 입체 앵커 |
| ② Smooth | 검정 | 0 | **120** | 40~55% | 중간 확산 (현행) |
| ③ Ambient Glow | 흰색/accent | 0 | **~400** | **25%** | 빛 wrap, 공중부양 제거 |

→ applyDetail을 단일 120에서 **3-스택으로 확장** 권장. rubric: `ambientGlowOpacity <= 30` pass.

### 3-2. Glow (`ADBE Glo2`, 2-패스)

- pass1: Threshold **60~65%**, Radius **15~25px**, Intensity **1.5~2.5**.
- pass2: Threshold 동일, Radius > pass1×3 (50~80px), Intensity 0.8~1.2.
- Color Looping **"Sawtooth B>A"**(단방향 sweep), 로고 reveal 1~2 loops. **프로젝트 32-bpc 필수**(8-bpc는 클리핑).
- 네이티브 한계: radius 클수록 banding. Deep/Optical Glow(플러그인) 없으면 2-패스+Screen 블렌드로 보완.

### 3-3. Grain (`ADBE Add Grain`)

Intensity **0.3~0.5**(현행 0.4 적정), Size 1.0~1.5, Softness 0.3~0.6, **Blend Overlay/Soft Light**(Normal이면 노출 상승 WARN), Blue 채널 +20~30%(필름 에뮬), Shadows +30%/Highlights -20%.

### 3-4. Motion Blur

Comp 토글 ON + 이동 레이어별 토글 ON(정지 레이어 OFF). **Shutter Angle 180°**(24fps=1/48s 영화 표준), **Shutter Phase -90°**(=-Angle/2, blur를 오브젝트 중심 정렬), Samples 8~16. 과장 스윕 270~360°. 렌더된 레이어엔 `ADBE Force Motion Blur`.

### 3-5. Depth Blur / Vignette / Color Grade

- **Depth**: `ADBE Camera Lens Blur`(Iris Hexagon) 또는 배경 Fast Box Blur 20~40px.
- **Vignette**: Ellipse mask(Subtract), Feather 350~500px(1080p), Opacity 20~40% + Classic Color Burn 18% 조합. Lumetri Amount -1.3~-3.0.
- **Color Grade**: black lift 10~20(0이면 WARN), white ceiling 230~245(255이면 WARN), Split Toning(shadows hue 200~230 쿨 / highlights 30~50 웜), Vibrance +15~20. **32-bpc**.

### 3-6. applyDetail rubric 체크 기준선

```
DROP SHADOW(3-stack): ①soft30~50/dist4~8/op60~70  ②soft100~140/dist0/op40~55(현행✓)  ③soft350~450/dist0/white|accent/op20~30
GLOW(2-pass): p1 thr60~65/r15~25/int1.5~2.5  p2 thr동일/r>p1×3/int0.8~1.2  loop"Sawtooth B>A"  32bpc
GRAIN: int0.3~0.5(현행✓)  blend Overlay|SoftLight(Normal→WARN)  blueBoost+20~30
MOTION BLUR: comp ON  모든 animated 레이어 ON  shutter180  phase-90
VIGNETTE: feather350~500  opNormal20~40  +ClassicColorBurn18
COLOR: blackLift10~20(0→WARN)  whiteCeiling230~245(255→WARN)  splitToning 권장
```

---

## 4. Animation Composer (Mister Horse) 분석 및 도입 검토

> **주의**: AC는 AE 플러그인이고 우리 렌더러도 AE/ExtendScript이므로 매핑이 자연스럽다(v3 Remotion 아님). AC의 익스프레션 기반 Behaviors는 우리 빌더가 키프레임 기반이라 **키프레임 베이크로 근사**한다.

### 4-1. AC 구조 (5대 카테고리)

Animation Presets(키프레임) / Behaviors(익스프레션 프로시저럴: Wiggle·Overshoot·Looper·Rubber·Blink) / Transitions / Text Boxes / Sounds / Precomps. 최신 AC4, Starter Pack 150+ 무료.

**IN/OUT/TRANSITION taxonomy**: 프리셋을 레이어 inPoint(등장)/outPoint(퇴장)/연결부(전환)에 적용. 전부 비파괴.

### 4-2. 파라미터 모델 — 3-슬라이더 추상화

AC 프리셋은 Effects Controls에 **Duration / Smoothness / Distance** 3개 슬라이더만 노출(내부는 수백 줄 익스프레션). Smoothness=이징 강도(0 선형~1 부드러운 감속), Distance=변위 크기. AC4 Keyframe Wingman은 그래프 에디터 없이 패널에서 이징 조정.

### 4-3. 우리 시스템 도입 검토

현재 우리 프리셋: `{name, props, ease, params}` → 빌더가 AE 키프레임 생성.

**✅ 즉시 채용 권장**
- **`role: "in"|"out"|"transition"|"emphasis"|"loop"` 필드**: 빌더가 `out`이면 파라미터 자동 반전(opacity 1→0 등) → 한 정의로 IN/OUT 양쪽.
- **`smoothness`/`distance`/`duration` 3-파라미터 추상화**: gemini/에이전트가 의미론적으로 설정(`smoothness 0.3` 빠른 바운스 vs `0.9` 부드러움). 빌더가 influence%/키프레임으로 변환하는 테이블 보유. AE 네이티브라 Smoothness→Easy Ease influence 직매핑이 자연스럽다(0→linear, 0.5→33%, 0.8→75%, 1.0→90%).
- **`bundle: ["opacity","scale","position"]`**: 한 named preset이 다중 속성 연동.

**⚠️ 부분 채용 (키프레임 베이크 근사)**
- Overshoot → 3키 오버슈트 키프레임(§1-2). Wiggle → 사전계산 perlin 노이즈 다수 키프레임 베이크. Looper → 모듈러 키프레임. *표현식 직접 주입은 AE에선 가능하나, 우리 데이터 주도 원칙상 키프레임 베이크 우선.*

**❌ 채용 불필요**
- .ffx/pack.info 패키지 포맷(우리는 JSON+jsx 직접). AE 마커 기반 타이밍(우리는 t0/dur 기준).

### 4-4. 도입 우선순위

| 우선순위 | 항목 | 효과 |
|---|---|---|
| P1 | `role` 필드(in/out/transition/emphasis/loop) | 타이밍 의도 명확 |
| P1 | `smoothness/distance/duration` 추상화 → influence 변환 테이블 | 에이전트 설정 단순화·일관성 |
| P2 | `bundle` 다중 속성 묶음 | 재사용성 |
| P2 | Overshoot 3키 + Smoothness→influence 테이블 빌더 내장 | 물리 기반 자연스러움 |
| P3 | Wiggle/Looper 베이크 프리셋 | 프로시저럴 정적 근사 |

---

## 5. gemini 검증 rubric 적용 지침

분석·검증 시 아래로 판정한다(명명된 원칙 기준).

1. **influence 대칭?** in≈out → `easy_ease_default`(기계적, 개선 필요).
2. **도착 측 influence ≥70%?** 부드러운 착지 → `ease_out_snappy`/`ease_inout_dramatic`.
3. **속도 그래프 초반 가파름→완만?** ease-out → entrance 적합.
4. **value graph 목표 초과 후 복귀?** overshoot 존재 → 비율 10~20% 내인지.
5. **레이어 간 stagger 2~10f?** 자연스러운 overlapping.
6. **총 duration?** <12f snappy / ≥18f heavy.
7. **anticipation?** 주 동작 직전 반대 방향 3~6f → 원칙 점수 +.
8. **모션블러?** 이동 요소에 ON, shutter 180.
9. **폴리시?** Drop Shadow 3-스택 / Glow 2-패스 32bpc / Grain blend / vignette·black lift.

---

## 6. 빌더 확장 우선순위 요약

| 기법 | 현재 지원 | 확장 |
|---|---|---|
| Trim Paths 단일 draw-on | ✓ (`trimEnd`) | 즉시 |
| 줌 트랜지션 | △ (`scale`) | Motion Blur 토글 + shutter |
| Drop Shadow 3-스택 | △ (단일 120) | ①③ 추가 |
| `role` in/out 반전 | ✗ | 데이터+빌더 (P1) |
| smoothness/distance 추상화 | ✗ | influence 변환 테이블 (P1) |
| Text Animator type-on/reveal | △ (`textOffset` 확인) | shape/easeHigh/stagger |
| Glow 2-패스 | △ | pass2 + 32bpc |
| Linear/Gradient Wipe | ✗ | Effect 추가 prop |
| 셰이프 모핑 | ✗ | `vertices[]` prop |
| Trim 다중/양방향 | △ | `trimEnd[]`/`trimStart` |
| CC Particle World | ✗ | `particlePreset` |

---

## Sources

**이징·원칙**: [Adobe Speed](https://helpx.adobe.com/after-effects/using/speed.html) · [Mt.Mograph Graph Editor](https://mtmograph.com/blogs/tools/how-to-use-the-graph-editor-in-after-effects) · [MotionScript bounce/overshoot](https://www.motionscript.com/articles/bounce-and-overshoot.html) · [Motion Design School velocity](https://motiondesign.school/blog/keyframe-velocity/) · [Frame.io staggered sequence](https://blog.frame.io/2023/12/13/insider-tips-how-to-create-a-staggered-layer-sequence-in-after-effects/)

**트랜지션·타이포·셰이프·파티클**: [Adobe Transitions](https://helpx.adobe.com/after-effects/using/transition-effects.html) · [Adobe Animating Text](https://helpx.adobe.com/after-effects/using/animating-text.html) · [Adobe Shape/Path](https://helpx.adobe.com/after-effects/using/shape-attributes-paint-operations-path.html) · [Adobe Simulation/CC Particle](https://helpx.adobe.com/after-effects/using/simulation-effects.html) · [SOM Text Animators](https://www.schoolofmotion.com/blog/text-animators-after-effects) · [PremiumBeat Trim Paths](https://www.premiumbeat.com/blog/using-trim-paths-adobe-after-effects/) · [SOM Morphing Letters](https://www.schoolofmotion.com/blog/morphing-letters-after-effects) · [Motion Array Kinetic Typo](https://motionarray.com/learn/after-effects/after-effects-kinetic-typography/)

**폴리시 이펙트**: [PremiumBeat Shadows](https://www.premiumbeat.com/blog/tutorial-mastering-shadows-in-after-effects/) · [SOM Glow](https://www.schoolofmotion.com/blog/glows-after-effects) · [PremiumBeat Advanced Glow](https://www.premiumbeat.com/blog/advanced-glow-effect-after-effects/) · [Adobe Noise&Grain](https://helpx.adobe.com/after-effects/using/noise-grain-effects.html) · [Evercast Motion Blur](https://www.evercast.us/blog/after-effects-motion-blur) · [PremiumBeat Motion Blur](https://www.premiumbeat.com/blog/motion-blur-inside-adobe-after-effects/) · [PremiumBeat Vignettes](https://www.premiumbeat.com/blog/quick-and-easy-vignettes-in-after-effects/)

**Animation Composer**: [misterhorse.com](https://misterhorse.com/animation-composer-for-after-effects) · [help.misterhorse.com](https://help.misterhorse.com/hc/en-us/sections/360000933357-Animation-Composer) · [aescripts](https://aescripts.com/animation-composer/) · [olafmotion presets guide](https://olafmotion.com/tips/motion-design-presets-guide/)
