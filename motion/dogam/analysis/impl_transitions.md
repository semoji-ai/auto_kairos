# impl_transitions

## 요약

전환 컴포넌트 19종을 모두 구현했고, 갤러리 데모 19개도 채웠습니다. `npx tsc --noEmit -p .`는 에러 없이 통과합니다. 갤러리 스틸은 전환 중간 프레임과 전환 후 프레임을 전환마다 렌더해 눈으로 확인했습니다(총 약 45장). 그 과정에서 버그 두 개를 고쳤습니다.
- **NewspaperPullout**: 부제가 사진에 가려지던 레이아웃을 바로잡았습니다.
- **FireTransition**: 불꽃 안쪽이 연노랑 단색 덩어리로 보이던 것을 주황·노랑 띠가 번갈아 보이도록 바꿨습니다.

파일은 다음 두 개입니다. 다른 파일은 수정하지 않았습니다.
- `motion/video/src/lib/transitions.tsx` (신규, `src/lib` 폴더도 새로 만듦)
- `motion/video/src/gallery/transitions.tsx` (`DEMOS`, `GALLERY_DUR`, `Gallery = runGallery(DEMOS)`, 총 1355f)

## 공통 규약
- 기본 형태는 `<X at={f} from={A} to={B} />`입니다.
- `*_CUT` 상수는 at 기준으로 A가 B로 바뀌는 오프셋이고, `*_LEN`은 전환이 끝나는 오프셋입니다.
- 난수는 모두 `random(seed)`을 씁니다. SVG id는 `useId`로 만들어 한 화면에 여러 번 써도 충돌하지 않습니다.
- 방사형 광선·선버스트는 쓰지 않았습니다.
- `Shot({img,pos})`도 export합니다. 전체 화면 사진 씬을 만드는 헬퍼입니다.

## 컴포넌트 (API · 컷 · 길이)

| # | 컴포넌트 | 주요 props | 컷 | 끝 |
|---|---|---|---|---|
| 1 | `TheaterCurtain` | `{at, from, to, highlight?, shadow?}` | +33 (`CURTAIN_CUT`) | +56 |
| 2 | `CRTSwitch` | `{at, from, to, starSize?}` | +12 | +16 |
| 3 | `SlatMosaic` | `{at, from, imgs[4], bg?, stagger=8, gap?, labels?}` | +0 (크림 배경으로 하드컷) | +37 |
| 4 | `NewspaperPullout` | `{at, from, headline, sub?, masthead="NEWS", k=0.38}` | 컷 없음 (같은 씬이 사진으로 축소) | +15, 이후 흔들림 루프 |
| 5 | `MagazineFlip` | `{at, from, target, targetLeft?, title?, coverLines?, pages=4, bg?}` | 착지 +45 (`MAG_LAND`) | +50 |
| 6 | `ArcWipeIris` | `{at, from, reveal?, object?, center=[1500,520], radius=520, outer, inner, ringColor}` | +13 | +28 |
| 7 | `IrisFeather` | `{at, from?, to, cx, cy, r=280, feather=80, outside=0.2, openAt?, openDur=60, fadeIn=16}` | at | 페이드인 +16 |
| 8 | `EnergySlash` | `{at, from, to, color="#B5F5F0", angle=-28}` | +10 | +25 |
| 9 | `WhiteDip` / `DipToBlack` | `{at, from, to}` | +4 / +2 | +20 / +8 |
| 10 | `OrangeFlare` | `{at, from, to}` | 크로스 중심 +5 | +10, 꼬리 포함 +16 |
| 11 | `MangaPanels` | `{at, from, panels: {img, pts, from:"left"|"right"|"top"|"bottom"}[], stagger=9, slide=8, colorLast}` + `MANGA_DEFAULT_LAYOUT` (5칸) | at | (n−1)·9+8 |
| 12 | `SplitPanelWipe` | `{at, from, left:{title, content, color?}, right?, rightAt=at+60}` | 컷 없음 (오버레이형) | — |
| 13a | `VerticalPush` | `{at, from, to, dur=10, dir}` | — | — |
| 13b | `ParallaxPush` | `{at, fromLayers[], toLayers[], dur=20, speeds?}` | — | — |
| 13c | `FireTransition` | `{at, from, to, orange, yellow}` | +9 | +21, 불씨 꼬리 +10 |
| 13d | `GrayscaleBeat` | `{at, hold=20, ramp=10, children}` (래퍼) | — | — |
| 13e | `FocusPull` | `{at, from, to, dur=8, maxBlur=24}` | 진행 50% | — |
| 13f | `MagicMove` | `{at, from, to, hero, heroFrom?, heroTo={x:-390, y:0, s:0.9}, origin, dur=19, dissolve=4}` | — | — |

추가 메모:
- **TheaterCurtain**: 발랑스(상단 띠)는 +3부터 +56까지 보입니다.
- **ArcWipeIris**: `object`는 원판 위에서 +25에 팝합니다. `reveal`을 주면 반투명 원판 대신 그 씬이 원 안에 보입니다.
- **IrisFeather**: `openAt`을 주면 원이 약 2300px까지 열리고 비네트가 물러납니다.
- **SplitPanelWipe**: 이전 씬은 18f에 걸쳐 35%로 어두워집니다. `content`는 패널 기준 좌표(위쪽 230px 아래)에 놓이고, 패널이 넓어지면서 드러납니다.
- **ParallaxPush**: `layers[0]`이 배경이고, 새 씬 배경은 가장자리 클립으로 드러납니다. 기본 이동량은 배경 0.385W(약 740px, 최고 약 58px/f), 전경 0.8W(약 1530px, 최고 약 120px/f)입니다.
- **MagicMove**: `hero`는 원래 위치에 그리고, 이동량(px)과 스케일로 움직입니다.

## 명세와 다른 점
- **CRT OFF 단계**: 6f 안에 포즈 4개를 넣느라 앞 두 포즈만 2f씩 유지하고, 0.3과 0.15 포즈는 1f씩입니다. ON 단계도 1f마다 포즈가 바뀝니다.
- **커튼 상승**: 10f 동안 약 1300px을 out-sine으로 올라가서, 초반 속도가 약 100px/f보다 빠릅니다. 커튼이 화면 밖으로 완전히 나가게 하려고 이렇게 했습니다.
- **ArcWipeIris**: "원형 마스크"는 반투명 흰 원판(α0.25)과 링을 여는 방식으로 해석했습니다. 초록 배경이 새 씬이 됩니다.
- **NewspaperPullout**: 회전 −3°에서 +2°는 화면에서 보이는 회전 기준입니다. 0°→−3°(4f)→+2°(8f)로 흔들린 뒤 멈춥니다. 사진 흰 테두리는 화면 기준 20px로 시작해 최종 크기에서는 약 7.6px로 줄어듭니다.
- **MagazineFlip**: 표지 앞에 A씬이 축소되며 사라지는 인트로 6f를 넣었습니다. 표지 이미지는 A씬입니다. 끝은 스프레드 화면으로 착지하고, 그 뒤로 확대해 들어가지는 않습니다.
- **FireTransition**: 불꽃은 38° 대각 축을 따라 가는 층 띠이고, 가장자리는 뾰족한 혀 모양입니다. 2f마다 모양이 새로 추첨되어 일렁입니다. 완전히 덮인 동안은 노랑 심지가 화면 대부분을 차지합니다.
- **FocusPull**: 같은 씬 안에서 배경과 전경의 초점을 옮기는 방식이 아닙니다. A는 흐려지며 빠지고 B는 선명해지며 들어오는 블러 크로스페이드로 일반화했습니다.

## 참고
스틸을 동시에 여러 장 렌더하면, 다른 에이전트의 webpack 캐시 경합 때문에 한 번 멈춘 적이 있습니다. 다시 렌더하니 정상이었습니다. `--timeout=60000`을 붙이고 3~4장씩 나눠 렌더하는 것을 권합니다.


---
## 최종 요약(에이전트 마지막 텍스트)

작업 보고를 전달했습니다. 전환 19종과 갤러리 데모 19개를 모두 구현했고, 타입 체크(`npx tsc --noEmit -p .`)는 에러 없이 통과합니다. 전환마다 전환 중간과 전환 후 프레임을 스틸로 렌더해(총 약 45장) 직접 확인했습니다. 그 과정에서 버그 두 개를 고쳤습니다.
- **신문 풀아웃**: 부제가 사진에 가려지던 레이아웃을 바로잡았습니다.
- **불꽃 전환**: 안쪽이 연노랑 단색으로 보이던 것을 주황·노랑 띠가 번갈아 보이도록 바꿨습니다.

파일은 `src/lib/transitions.tsx`(신규)와 `src/gallery/transitions.tsx` 두 개만 건드렸습니다. 사용법은 `<X at={f} from={A} to={B} />`이고, 각 전환 이름의 `_CUT`/`_LEN` 상수(예: `CURTAIN_CUT`)가 A→B로 바뀌는 시점과 전환이 끝나는 시점을 at 기준 오프셋으로 알려 줍니다.

명세와 다른 점은 다음과 같습니다.
- **CRT 전환**: 끄는 단계 6f 안에 포즈 4개를 넣느라, 마지막 두 포즈는 2f가 아니라 1f씩 유지됩니다.
- **극장 커튼**: 올라갈 때 커튼이 화면 밖으로 완전히 나가도록 해서, 초반 속도가 명세의 약 100px/f보다 빠릅니다.
- **아크 와이프 아이리스**: 원형 마스크를 "반투명 흰 원판(α0.25)을 여는 것"으로 해석했습니다. 초록 배경이 새 씬이 되고, 오브젝트는 원판 위에 나타납니다.
- **매거진 플립**: 앞씬이 표지로 줄어드는 6f 인트로를 넣었습니다. 끝은 펼친 두 페이지 화면에서 멈추고, 그 페이지로 확대해 들어가지는 않습니다.
- **포커스 풀**: 같은 씬 안에서 초점을 옮기는 방식이 아니라, 앞씬은 흐려지며 빠지고 새 씬은 선명해지며 들어오는 크로스페이드로 만들었습니다.

스틸을 한꺼번에 여러 장 렌더하다가 한 번 멈춘 적이 있습니다. 같은 시간에 다른 에이전트도 렌더 중이어서 캐시가 겹친 탓으로 보이고, 다시 렌더하니 정상이었습니다. 렌더할 때는 `--timeout=60000`을 붙이고 3~4장씩 나눠 돌리는 것을 권합니다.