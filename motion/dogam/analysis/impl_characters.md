# impl_characters

## 결과 요약

15개 항목을 모두 구현했습니다. `npx tsc --noEmit -p .`는 에러 없이 통과했습니다. 갤러리 `Gallery-characters`는 데모 19개, 총 1,494f이고 약 50프레임을 스틸로 렌더해 직접 확인하면서 고쳤습니다. 방사형 줄무늬나 욱일 모양은 쓰지 않았습니다.

- 수정한 파일은 두 개뿐입니다: `motion/video/src/lib/characters.tsx`(신규), `motion/video/src/gallery/characters.tsx`(`DEMOS`, `GALLERY_DUR`, `Gallery = runGallery(DEMOS)`).
- 확인용 콘택트시트는 스크래치패드의 `char_sheet_a.jpg`부터 `char_sheet_h.jpg`까지입니다.

## 컴포넌트와 주요 props

좌표는 모두 화면 px 절대값입니다. 캐릭터 위치는 발밑 중앙 기준이고, 랜덤 요소는 `random(seed)`로 결정론적입니다.

**헬퍼**
- `pingPong(f, period, a, b, phase)`: 이지-이지 왕복 값.
- `bobbedY(y, ground, sy)`: 까딱이는 캐릭터 위의 한 점 y를 따라감.
- `Glove`, `GloveSvg`: 흰 장갑 SVG. pose는 idle, wave, surprised, point 4종.

**1. 마스코트화**
- `Mascot`: props는 `{x, y, w, h, img | children, at?, l?, r?, poses?:[{at,l?,r?}], legLen?, handSize?, handInset?, handDy?, legGap?, idle?, flip?, push?:{at,dx,dur?,pose?}, drop?:{at,dur?,from?}, glow?, seed?}`.
  - 대기 동작: 몸 전체 scaleY 1.0↔0.98을 20f 주기로 반복합니다.
  - 양손은 독립 위상으로 움직입니다. wave는 12f 주기로 ±26°, surprised는 2f마다 지터, point는 앞으로 찌르는 동작입니다.
  - 다리는 검정 막대, 신발은 흰 운동화 SVG입니다.
- `RivalEnter {a, b, at, pushDx=0.22W, pushDelay=5}`
  - b는 위에서 8f 동안 ease-out으로 떨어지고, 착지 후 2f 동안 스쿼시합니다(0.85/1.1).
  - a는 10f 동안 QUART_OUT으로 밀려나고, 손이 surprised로 하드 스왑됩니다.

**2. 얼굴 가면**
- `LogoFaceMask {cx, cy, faceW, at, ground?, bobPeriod/Amp/Phase?, img | text | children, cover=0.9, ratio=1.12, rot?}`
  - 캐릭터와 같은 bob 값을 주면 까딱임을 따라갑니다.

**3. 감정 기호**
- `AngerMark {x, y, at, size=60, color, out?, rot?}`: 0→1.3→1로 팝(4f)한 뒤, 2f/3f 교대로 1.0↔1.14 맥동합니다.
- `SurpriseLines {x, y, at, side: left | right | both, n=4, len, gap, spread, color, width}`: 3f 동안 선이 그려진 뒤 2f마다 지터. 흰색으로 지정하면 검정 외곽선이 붙습니다.
- `CloudBubble {x, y, at, text, w, h, tail?, size?, out?}`: 꼬리 점 2개가 1f씩 먼저 뜨고, 이어서 본체가 사진 팝으로 나타납니다.
- `CloudBubbles {head, items:[{text, at, out?}], dx, dy, w, h, first}`: 머리 위에서 좌우 번갈아 뜹니다.
- `DizzySwirl {x, y, at, r=70, color, speed}`: 납작한 3바퀴 나선이 회전하고, 별 2개가 궤도를 돕니다.
- `FallingBlocks {x, groundY, at, width, n, size, stagger, color}`: 중력으로 떨어지면서 회전하고, 착지할 때 튕긴 뒤 가운데가 높은 더미로 쌓입니다. 캐릭터보다 먼저 렌더하면 캐릭터 뒤에 쌓입니다.

**4. 연기 효과**
- `SmokeSwap {x, y, w, h, at, a, b, cover=10}`: 3f 만에 덮고 이 시점에 a→b로 교체합니다. 10f 유지 후 9f 동안 연기 덩어리가 하나씩 오그라들며 걷힙니다.
- `Teleport {x, y, w, h, at, mode: "in" | "out", children}`: 흰 4각 별이 2f 번쩍인 뒤 회색 연기가 6f 부풀고(캐릭터를 감쌈), 12f 동안 흩어집니다.

**5. 점프**
- `HopArc {pts[], at, w, h, img | children, dur=12, rise=5, gap=6, height, dust, face}`
  - 포물선 궤적이고, 진행 방향으로 몸을 뒤집습니다.
  - 착지 시 2f 스쿼시(0.85/1.1)와 흰 타원 먼지 링(6f)이 붙습니다. 여러 번 연속 점프가 가능합니다.

**6. 전격**
- `RivalBeam {from, to, at, out?, thick=60, glow}`
  - 파랑/하늘/흰색 3겹 번개에 가지 2개와 글로우가 있고, 2~3f마다 모양이 다시 생성됩니다.
  - 2f 동안 뻗어나가며, 시작 3f는 소스 위치에 주황 플래시가 뜹니다.
- `ElectricCrack {x, y, r, at, n, color}`: 원 둘레에 노란 지그재그가 2f마다 다시 생성됩니다.

**7. 눈빛 광선**
- `EyeBeam {a, b, at, amp, wave, color, width, strands, flow, speedLines?}`: 양 끝이 가늘어지는 사인파가 6f 동안 뻗고, 위상이 흘러갑니다.
- `SpeedLines {at, n, speed, dir, color, bg}`

**8. 전화 벨**
- `PhoneRing {x, y, at, size, text="따르릉", color, phone?}`
  - 양옆에 부채꼴 빨간 지그재그 3개씩이 붙고, 4f/6f 교대로 모양이 바뀝니다.
  - 전화기가 흔들리고 "따르릉" 텍스트가 팝합니다.
  - 20f 주기 중 14f는 울리고 나머지는 쉽니다.

**9. 숨은 실루엣**
- `HiddenSilhouette {img, x, y, w, h?, at, dur=60, dx=170, opacity=0.5, color, children}`: children이 앞 캐릭터입니다. 실루엣은 sine in-out으로 천천히 옆으로 스며 나옵니다.

**10. 구석 손가락**
- `FingerFromCorner {tip, at, angle=-42, scale, slide=10, tapAt?, skin, sleeve, ripple, out?}`: 소매가 달린 플랫 손이 오른쪽 아래에서 대각선으로 10f 만에 들어와 한 번 톡 찌르고, 흰 링 파문이 퍼집니다.

**11. 군중**
- `CrowdRise {at, n, y, x0, x1, height, opacity=0.7, colors, rise=11, stagger}`: 환호 포즈 4종이 11f QUART_OUT으로 솟아오른 뒤 까딱이며 팔을 흔듭니다.

**12. 인생 경로**
- `WalkPath {y, x0, stops:[{x, label?, sub?, hold?}], at, w, h, img, speed=6, hold=16, stepLen, lineColor, occluders?, startLabel?}`
  - 캐릭터가 걸으며 까딱·기울기를 주고, 빨간 8px 선이 캐릭터를 따라 그려집니다.
  - 정지점마다 링 노드(Ø40, 흰 채움, 빨간 8px 테두리)가 3f 팝하고 라벨이 붙습니다.
  - `occluders`로 넘긴 건물 뒤를 지나갑니다.

**13. 승진 계단**
- `StairPromotion {x0, y0, steps:[{flag, sub?}], at, w, h, img, stepW, stepH, depth, every=15, colors}`
  - 아이소메트릭 계단이고 단마다 흰 깃발(연도/직함)이 있습니다.
  - 15f마다 점프컷으로 한 칸 오르며 3f 스쿼시가 들어갑니다. 현재 단은 강조되고, 지나온 깃발 글자는 빨간색이 됩니다.

**14. 슬라이드인 리프레임**
- `SlideInReframe {at, char, children, from, slide=17, dist=1150, zoom=0.045, dy=-70, camDur=9, origin}`: 래퍼 형태입니다.

**15. 포즈 스왑**
- `PoseSwap {x, y, w, h, poses:[{at, img, flip?, effect?:(fireAt)=>ReactNode}], glow, bob}`: 1f 하드 스왑이고, effect는 스왑 1f 뒤에 발사됩니다.

## 사양과 다르게 한 점

- **SlideInReframe:** 명세의 "y −70px"은 콘텐츠를 −70px 옮기는 것으로 해석했습니다. 줌 4.5%만으로는 아래 가장자리에 약 46px 틈이 생기므로, 배경은 약 90px 여유(블리드)를 두고 크게 깔아야 합니다. 데모와 주석에 반영했습니다.
- **Mascot 손 위치:** 몸 박스 가장자리 기준 비율표로 정합니다. 이미지 가장자리에 투명 여백이 있으면 `handInset`으로 맞춰야 합니다(천장 항아리 = 0.07). 이미지의 실제 윤곽을 자동으로 감지하지는 않습니다.
- **RivalEnter 밀기 타이밍:** 밀기는 낙하 시작 5f 뒤에 시작해 착지 순간과 겹치게 했습니다(`pushDelay`로 조정).
- **CloudBubbles:** 같은 쪽에 다음 풍선이 오면 이전 풍선이 5f 전에 사라지도록 했습니다(겹침 방지).
- **Teleport:** "캐릭터를 감싼 연기"를 뒤쪽 링 연기로 표현했습니다. out 모드에서만 앞쪽을 덮는 연기가 추가됩니다.
- **PhoneRing:** 연속으로 울리지 않고 20f 중 14f만 울리게 했습니다.
- **얼굴 좌표:** 데모용 얼굴 좌표는 피부색 픽셀로 측정했습니다. woo는 얼굴 중심 (282, 238), 얼굴폭 300이고, kid는 (360, 390), 폭 540입니다.
- **FingerFromCorner:** 탭 시점 기본값은 at+14f입니다(`tapAt`으로 조정).

---
## 최종 요약(에이전트 마지막 텍스트)

15개 항목을 모두 구현해 보고를 넘겼습니다. 타입 검사는 에러 없이 통과했습니다. `Gallery-characters` 갤러리(데모 19개, 1,494f)는 스틸 약 50장을 렌더해 눈으로 보면서 손 위치, 얼굴 좌표, 연기 걷힘 등을 고쳤습니다. 방사형 줄무늬나 욱일 모양은 쓰지 않았습니다.

수정한 파일은 두 개뿐입니다.
- `motion/video/src/lib/characters.tsx` (신규, 컴포넌트 전부)
- `motion/video/src/gallery/characters.tsx` (데모 채움, 기존 export 유지)

**컴포넌트 목록** (좌표는 화면 px, 캐릭터는 발밑 중앙 기준)
- **마스코트화:** `Mascot`(장갑 손 4포즈, 막대 다리, 운동화, 대기 까딱, `push`/`drop` 옵션), `RivalEnter`(위에서 떨어진 뒤 착지 스쿼시, 기존 마스코트는 +22%W 밀려나며 surprised로 바뀜)
- **얼굴 가면:** `LogoFaceMask`(캐릭터와 같은 까딱 값을 주면 따라감)
- **감정 기호:** `AngerMark`, `SurpriseLines`, `CloudBubble`/`CloudBubbles`, `DizzySwirl`, `FallingBlocks`
- **연기:** `SmokeSwap`(제자리 교체), `Teleport`(in/out 모드)
- **점프:** `HopArc`(포물선 연속 점프, 착지 스쿼시와 먼지 링)
- **전격·광선:** `RivalBeam`, `ElectricCrack`, `EyeBeam`, `SpeedLines`
- **기타:** `PhoneRing`, `HiddenSilhouette`, `FingerFromCorner`, `CrowdRise`
- **타임라인:** `WalkPath`(건물 뒤 통과), `StairPromotion`
- **래퍼·헬퍼:** `SlideInReframe`, `PoseSwap`(효과는 스왑 1f 뒤 발사), `pingPong`, `bobbedY`, `Glove`

**사양과 다르게 한 점**
- **SlideInReframe:** "y −70px"을 콘텐츠를 위로 70px 옮기는 것으로 해석했습니다. 줌 4.5%로는 아래쪽에 약 46px 틈이 생겨서, 배경을 약 90px 여유를 두고 크게 깔아야 합니다. 반대 방향 의미였다면 부호만 바꾸면 됩니다.
- **Mascot 손 위치:** 몸 박스 비율표로 정합니다. 이미지 가장자리에 투명 여백이 있으면 `handInset`으로 맞춰야 합니다(항아리 이미지는 0.07). 실제 윤곽을 자동으로 찾지는 않습니다.
- **RivalEnter:** 밀기가 낙하 시작 5f 뒤에 시작해 착지와 겹칩니다(`pushDelay`로 조정).
- **CloudBubbles:** 같은 쪽에 다음 풍선이 뜨기 5f 전에 이전 풍선이 사라집니다. 겹침을 막으려고 넣었습니다.
- **Teleport:** "연기 안의 캐릭터"는 캐릭터 뒤를 두르는 연기로 표현했습니다. out 모드에서만 앞을 덮는 연기가 추가됩니다.
- **PhoneRing:** 계속 울리지 않고 20f 중 14f만 울립니다.
- **FingerFromCorner:** 톡 찌르는 시점 기본값은 at+14f입니다(`tapAt`으로 조정).
- **얼굴 좌표:** 데모용 얼굴 위치는 피부색 픽셀로 측정했습니다(woo 얼굴 중심 (282, 238)·폭 300, kid (360, 390)·폭 540).

확인용 콘택트시트는 스크래치패드의 `char_sheet_a.jpg`부터 `char_sheet_h.jpg`까지입니다.