# 통합 모션 학습 라이브러리 설계 (gemini→JSON→AE 파이프라인 고급화)

> 작성: 2026-06-16 · 범위: P1(기초+정교화+디테일+폰트/컬러). P2/P3는 개요.

## 1. 목적

gemini 영상분석 → motion.json → build_from_json.jsx 파이프라인의 **모션 표현력을 고급 모션그래픽 수준으로** 끌어올린다. 현재 빌더는 opacity/scale/position/typeOn 4개 기본 모션뿐이라 "잘 만든 PPT" 수준. 모션·폰트·컬러를 **명명된 라이브러리(공유 어휘)**로 만들어, gemini가 프리셋명으로 영상 모션을 매핑하고 빌더가 정교하게 적용한다.

모션 디자이너 3인 패널 평가로 핵심 프리셋을 선정함(아래 §3).

## 2. 아키텍처

```
라이브러리(공유 어휘, data/artstyle/motion/):
  motion_presets.json   프리셋명 → {props, ease, params}
  font_map.json         역할 → 설치 PS폰트명
  color_tokens.json     키 → hex
        ↓ 어휘 카탈로그를 gemini 프롬프트에 주입
gemini  영상분석 → preset="pop_bounce", font="gothic_bold", color="brand_red", detail=["shadow","glow"]
        ↓ motion.json
빌더    라이브러리 로드 → 프리셋명을 AE 키프레임/이징/이펙트로 적용
```

**4층 라이브러리**:
1. 기초 모션 프리셋 (7종 + 커스텀 이징)
2. 디테일 레이어 (shadow/glow/depth_blur/motion_blur/grain) — 모션에 옵션 탑재
3. 고급 효과 프리셋 (P2 — 트랜지션/셰이프빌드/라이트/파티클, AE 네이티브 이펙트)
4. 하이브리드 마커 (P3 — 자동 불가 영역 가이드 레이어+주석)

**매핑 주체**: gemini가 직접 선택(라이브러리 어휘를 프롬프트에 주입). 빌더는 어휘→AE 변환.

**자동화 경계**: 1·2층 + P2의 AE 네이티브 이펙트는 자동. 유체 시뮬·캐릭터 리깅은 P3 수동 포인트 마커.

## 3. P1 — 기초 모션 프리셋 7종 (3인 패널 합의)

`data/artstyle/motion/motion_presets.json`:

| 프리셋 | props | 이징 | params | AE 구현 |
|---|---|---|---|---|
| `type_on` | textOffset | linear | cps(글자/초) | Text Animator Range Offset 0→100 |
| `fade_scale_in` | opacity, scale | easeOut | scaleFrom(85) | 키2 + Easy Ease |
| `slide_in` | position, opacity | easeOut | dir(left/right/up/down), offset | 키2 |
| `pop_bounce` | scale, opacity | out→in | overshoot(110), settle | scale 키3 [0,110,100] |
| `mask_reveal` | trimEnd 또는 maskExpansion | easeInOut | mode(trim/wipe), dir | Trim Paths End 0→100 / 마스크 |
| `tilt_2_5d` | rotationY | easeOut | angle(-15) | 3D 레이어 Y회전 |
| `stagger`(메타) | — | base 계승 | base(프리셋명), offset(f), dir | 자식 in-point 시차 |

**커스텀 이징**(KeyframeEase influence 매핑):
- `easeOut`: influence 75 (감속) — `[0,0,0.2,1]` 근사
- `easeInOut`: 양쪽 75
- `overshoot`: pop_bounce는 키프레임 3개로 물리 구현(익스프레션 회피)
- `anticipation`(옵션): 등장 전 반대 방향 미세 키프레임(스케일 95→0→110)
- `follow_through`(옵션): 정착 후 미세 잔여(위치 ±2px 감쇠)

**elastic 미채택**(3인 패널: 과한 탄성은 광고 부적합).

## 4. P1 — 디테일 레이어

`detail` 배열로 모션에 옵션 탑재 (gemini가 컷별 지정):
| 키 | AE 이펙트 | 기본값 |
|---|---|---|
| `shadow` | Drop Shadow | opacity 60, dist 20, soft 50 |
| `glow` | Glow | threshold 50%, radius 20, intensity 1 |
| `depth_blur` | Camera Lens Blur 또는 Gaussian(약) | 깊이별 약하게 |
| `motion_blur` | layer.motionBlur=true + comp 활성 | 모든 이동 모션 기본 ON |
| `grain` | Add Grain(조정 레이어, 폴백 Noise) | intensity 0.4 |

## 5. P1 — 폰트 맵 / 컬러 토큰

`font_map.json`: `{role: ps_name}`
- gothic_bold→OTSBAggroB, gothic_med→OTSBAggroM, gothic_light→OTSBAggroL,
  serif→GyeonggiBatangR, rounded→Cafe24Ssurround, sans→Pretendard-Regular,
  fallback→AppleSDGothicNeo-Bold

`color_tokens.json`: `{key: hex}`
- brand_red(#E4002B), ink(#333333), bg_gray(#F3F3F3), white(#FFFFFF), muted(#9AA0A6)
- gemini는 토큰키 또는 직접 hex. 빌더가 rgb 변환.

## 6. P1 — gemini 스키마 확장

기존 motion.json layer/anim에 추가:
- `anim`: `{preset: "pop_bounce", t0, dur, params:{...}}` (기존 prop/from/to 대신 preset명)
- layer: `font: "gothic_bold"`, `color: "brand_red"`, `detail: ["shadow","glow"]`
- 하위호환: preset 없으면 기존 prop 방식 유지

gemini 프롬프트에 7 프리셋 + 폰트역할 + 컬러키 + 디테일 카탈로그 주입.

## 7. P1 — 빌더 확장

`build_from_json.jsx`:
- `loadMotionLib()`: motion_presets/font_map/color_tokens 로드
- `applyPreset(layer, isText, presetName, t0, dur, params)`: 프리셋명 → 키프레임+이징 (현 applyAnim 대체/확장)
- `applyDetail(layer, detailArr)`: shadow/glow/blur/grain 이펙트
- `resolveFont(role)`, `resolveColor(key)`: 맵 조회
- makeText/makeRRect 등이 font/color/detail 반영

## 8. 단일 소스 / 모듈 / 테스트

- 라이브러리 3파일은 `data/artstyle/motion/` (단일 소스). 빌더가 jsx 폴더로 미러 or 직접 경로.
- 프리셋 추가는 motion_presets.json만 수정(빌더 코드 무관) — 데이터 주도.
- 테스트: 빌더 jsx 괄호/구문, motion_presets 스키마 유효성, applyPreset 분기 존재(panel structure 테스트).
- 하위호환: 기존 prop 방식 motion.json도 동작.

## 9. P2 / P3 (개요, 별도 스펙)

- **P2 고급 효과**: 트랜지션 디자인(와이프/모핑/줌/리퀴드), 셰이프 빌드/드로잉, 키네틱 타이포 고급(글자별 물리), 라이트/글로우 시퀀스, 파티클(CC Particle World 디졸브). AE 네이티브 이펙트 자동 추가.
- **P3 하이브리드 마커**: 유체 시뮬·복잡 합성 등 자동 불가 영역 → 빌더가 가이드 레이어+주석 생성, 디자이너 마무리.

## 10. 범위 밖 (YAGNI, P1)

- 고급 효과/파티클(P2), 하이브리드 마커(P3)
- elastic 이징(패널 비채택)
- 캐릭터 리깅·유체 시뮬(자동화 한계)
