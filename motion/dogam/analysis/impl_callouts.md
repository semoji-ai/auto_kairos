# impl_callouts

## 결과 요약

21개 기법을 모두 구현해 갤러리 23데모(총 2650f)로 넣었습니다. BrowserMockup은 graph·shop 두 모드를 따로 보여 줍니다. `npx tsc --noEmit -p .`는 에러 없이 통과했고, 스틸 약 40장을 렌더해 직접 확인하면서 고쳤습니다. 방사형 광선은 쓰지 않았고, 우승 강조는 fx의 `GlowPulse`(소프트 글로우+링)로 처리했습니다.

**파일**
- `motion/video/src/lib/callouts.tsx` (신규)
- `motion/video/src/gallery/callouts.tsx` (`DEMOS`·`GALLERY_DUR`·`Gallery = runGallery(DEMOS)` 유지)

**다른 곳에서 가져다 쓸 수 있는 헬퍼:** `polyLen`, `polyUpTo`(등속 폴리라인 드로우), `dOf`, `HBlur`(가로 전용 모션블러), `Pill`, `Icon`(플랫 SVG 20종: doc·phone·chip·cloud·gear·bulb·cart·user·money·globe·heart·star·truck·chart·lock·factory·bowl·ship·search·mail), `CodeRainBg`

## 컴포넌트와 props (좌표는 1920×1080 절대 px, 시간은 모두 `at` 기준 프레임)

1. **CalloutConnector** `{at, label, labelX, labelY, box:[x,y,w,h], path:P[], part?{img,x,y,w,h}, title, titleX, titleY, titleColor?, subs?, cards?[{icon,text,color?}], cardsX?, cardsY?, color="#F60000", drawF=15}`
   - 흰 그라데이션 띠가 6f 와이프로 열리고 라벨(120px)이 나옵니다.
   - +8f에 빨강 박스(10px, r24)가 하드로 뜨고, +10f부터 라벨→대상 방향으로 직각선(10px 라운드캡)을 15f 동안 그립니다.
   - 선이 닿으면 부품 이미지와 제목(80px)이 팝, 부제가 6f 간격, 카드 3장이 5f 간격으로 팝합니다.
2. **DottedPathDraw** `{pts, at, lineAt?, color, dash=16, gap=12, width=4, speed=30, ends?, endSize}`: 끝점 아이콘이 5f 간격으로 팝한 뒤 30px/f 등속으로 그립니다.
3. **CircuitBranch** `{hub, at, hubNode?, branches[{pts,icon,label?}], color, drawF=7, stagger=4, iconSize}`: 선 6px, 끝 아이콘 0.3→1.1→1 (5f).
4. **PillArrowPill** `{a, b, at, x?, y?, step=15, color="#1FA3D6", spread, size}`
5. **PillCollision** `{left, right, big, at, color, textColor="#1F4E9C", ringColor, bigSize=240}`
   - pill 두 개가 8f easeIn으로 모이며 가로블러가 0→40 커지고, 1f 흰 섬광이 터집니다.
   - 손그림 링(두께 20px 밴드, feTurbulence 변위)이 4f 동안 Ø250→380으로 커진 뒤, 점선 호 14조각으로 15f 동안 흩어집니다.
   - 링 2f째에 큰 글자가 1.5x/α0.5 상태에서 1.0으로 3f 만에 떨어지고, +15f에 1.1x 잔상이 한 번 번쩍입니다.
6. **NeonTiles** `{letters, at, colors, margin=90, tile=240, stagger=5}`: TL→TR→BL→BR 순서로 꽝 떨어진 뒤, 결정론적으로 2~8f마다 α가 0.6↔1로 깜빡입니다.
7. **CompareAB** `{a, b, at, color="#E8521E", sign="<", bDelay=22}`
8. **TitleBox** `{title, sub?, at, subAt=at+39, y, w, size, subSize}`
9. **ScrimTypewriter** `{title, sub, at, badges[{label,color}], x, y}`
10. **Whiteboard** `{x, y, w, h, at, title, titleAt?, lines[{text,at}], wipe=22}`
11. **RedBoxBlink** `{rect, at, pills?, pillsX?, pillsY?, pillGap, pillsAt?, color="#E00000", pillColor}`: 16f 켜짐 / 12f 꺼짐을 두 번 반복한 뒤 켜진 채 유지합니다.
12. **HandDrawnCircle** `{cx, cy, rx, ry, at, dur=10, color, width=9, seed, turns=1.15}`
13. **BrowserMockup** `{at, url, mode:"graph"|"shop", x?, y?, w=1150, h=800, tab, typeAt?, contentAt?, shop?[{img,name,price}]}` + 배경용 **CodeRainBg** `{color, base="#1A2560", speed}`
14. **ScreenshotGrid** `{items, at, cols=4, cw=220, ch=150, gap, cy, bg, step=15}` / **ScreenshotCarousel** `{items, at, y, cw=400, ch=300, gap=30, speed=25(px/s), startX}`
15. **VersionStack** `{versions[{content,year}], at, hold=36, cx=1350, cy, endAt?}`
16. **IconRowGrid** `{items[{icon,label?}], at, stagger=11, perRow=[5,4], d=250, gapX, rowYs}`
17. **TreeDroplines** `{root, kids[{text,color?}], at, x, y, rise=60, kidY, spacing, lineColor, rootColor}`
18. **ShieldWings** `{text, at, x, y, shields[{label,icon?}], color="#2EC4E6"}`
19. **MapPin** `{img, x, y(꼬리 끝), at, d=130, color, label?, pos?}`
20. **MedallionTree** `{items[{img,name,color,x,y,pos?}], center, at, stagger=30, d=230, lineAt?, conclusion?, midY?}`
21. **PuzzleJoin** `{left, right, at, x, y, S=320, colors, dur=26, ringColor}`

## 사양과 다르게 한 부분

- **1 CalloutConnector:** 사양의 "reverse direction"은 라벨에서 대상 쪽으로 그리는 것으로 해석했습니다. 경로는 `path` 점 배열로 직접 지정합니다.
- **5 PillCollision:** 충돌 순간(8f째) pill이 사라지고 링과 텍스트로 이어집니다. pill 두 개가 화면에 남는 버전은 아닙니다.
- **6 NeonTiles:** "1.8x α0.4 → 0.75 → 1.0"을 크기 1.8→0.96→1.0, α 0.4→0.75→1.0으로 해석했습니다.
- **7 CompareAB:** B pill은 "<"가 나온 뒤 6f(at+22)에 팝합니다. `bDelay`로 조정할 수 있습니다.
- **14 ScreenshotGrid:** 컴포넌트 기본값은 사양대로 220×150입니다. 1920 화면에서 너무 작아 보여서 데모만 330×225로 키웠습니다.
- **15 VersionStack:** 옛 카드 간격을 120px(50% 겹침)로 두었습니다. 최신↔직전 간격은 160px라서, 카드를 하나 추가할 때마다 스택 전체가 왼쪽으로 160px 이동합니다.
- **20 MedallionTree:** 선이 한 줄로 겹쳐 마지막 색만 보이는 문제가 있어서, 중심 근처에 16px 간격의 평행 번들선으로 모이게 바꿨습니다. 교차는 없습니다.
- **9 ScrimTypewriter:** 배지 라벨은 원 안에 흰 글씨로 넣었습니다.
- **13 BrowserMockup · shop:** 클릭하면 버튼이 "담김 ✓"로 바뀌고, 리플과 장바구니 배지가 추가됩니다.
- **16 IconRowGrid:** 둘째 줄 첫 아이콘은 자기 위치 -320px에서 미끄러져 들어옵니다.

데모 텍스트는 짜장면·인천 주제의 한국어이고, 에셋은 public/img와 public/real을 썼습니다.

---
## 최종 요약(에이전트 마지막 텍스트)

콜아웃·텍스트·레이아웃 기법 21종을 모두 구현했고, 갤러리에 데모 23개(총 2650프레임)로 넣었습니다. BrowserMockup은 graph·shop 두 모드를 따로 보여 줍니다. `npx tsc --noEmit -p .`는 에러 없이 통과했고, 스틸 약 40장을 렌더해 직접 보면서 고쳤습니다. 방사형 광선은 쓰지 않았고, 우승 강조는 fx의 `GlowPulse`(부드러운 글로우 + 링)로 처리했습니다.

**렌더를 보고 고친 것**
- **CalloutConnector 데모:** 빨간 박스가 빈 곳에 떠 있어서 선반 위 항아리를 감싸도록 옮겼습니다. 카드 문구도 줄바꿈되지 않게 줄였습니다.
- **RedBoxBlink 데모:** 박스를 공화춘 정문에 맞추고, 파란 알약 라벨을 왼쪽으로 옮겼습니다.
- **MedallionTree:** 선들이 한 줄로 겹쳐 마지막 색만 보였습니다. 중심 근처에서 16px 간격 평행선으로 모이게 바꿔 색마다 따로 보이고 교차도 없습니다.
- **PillCollision 에너지 링:** 손그림 질감이 안 보였습니다. 같은 요소에 CSS 필터가 걸려 SVG 필터를 덮어쓰고 있었고, 그룹을 분리해 해결했습니다.

**사양과 다르게 한 부분**
- **CalloutConnector:** "reverse direction"은 라벨에서 대상 쪽으로 선을 그리는 것으로 해석했습니다. 경로는 점 배열(`path`)로 직접 넘깁니다.
- **PillCollision:** 충돌 순간(8프레임째) 알약 두 개가 사라지고 링과 큰 글자로 넘어갑니다. 알약이 화면에 남는 버전은 아닙니다.
- **NeonTiles:** "1.8x α0.4 → 0.75 → 1.0"은 크기 1.8 → 0.96 → 1.0, 투명도 0.4 → 0.75 → 1.0으로 해석했습니다.
- **CompareAB:** B 알약은 "<"가 뜬 뒤 6프레임 후(at+22)에 팝합니다. `bDelay`로 바꿀 수 있습니다.
- **ScreenshotGrid:** 기본값은 사양대로 220×150입니다. 1920 화면에서 너무 작아 보여 데모에서만 330×225로 키웠습니다.
- **VersionStack:** 옛 카드끼리는 120px 간격(50% 겹침), 최신 카드와 직전 카드는 160px 간격입니다. 그래서 카드가 추가될 때마다 스택이 왼쪽으로 160px 밀립니다.
- **ScrimTypewriter:** 배지 라벨은 원 안에 흰 글씨로 넣었습니다.
- **BrowserMockup 쇼핑:** 클릭하면 버튼이 "담김 ✓"로 바뀌고, 퍼지는 원과 장바구니 숫자 배지를 추가했습니다.
- **IconRowGrid:** 둘째 줄 첫 아이콘은 자기 자리의 320px 왼쪽에서 미끄러져 들어옵니다.

**컴포넌트와 주요 props** (좌표는 1920×1080 픽셀, 시간은 모두 `at` 기준 프레임)
1. `CalloutConnector` — `at, label, labelX, labelY, box, path, part?, title, titleX, titleY, subs?, cards?, color="#F60000", drawF=15`
2. `DottedPathDraw` — `pts, at, color, dash=16, gap=12, width=4, speed=30, ends?`
3. `CircuitBranch` — `hub, at, hubNode?, branches[{pts, icon, label?}], drawF=7, stagger=4`
4. `PillArrowPill` — `a, b, at, step=15, color="#1FA3D6"`
5. `PillCollision` — `left, right, big, at, textColor="#1F4E9C", bigSize=240`
6. `NeonTiles` — `letters, at, colors, tile=240, stagger=5`
7. `CompareAB` — `a, b, at, color="#E8521E", sign="<", bDelay=22`
8. `TitleBox` — `title, sub?, at, subAt=at+39`
9. `ScrimTypewriter` — `title, sub, at, badges[{label, color}]`
10. `Whiteboard` — `x, y, w, h, at, title, lines[{text, at}], wipe=22`
11. `RedBoxBlink` — `rect, at, pills?, pillsX?, pillsY?, pillsAt?`
12. `HandDrawnCircle` — `cx, cy, rx, ry, at, dur=10, seed`
13. `BrowserMockup` — `at, url, mode: "graph" | "shop", shop?`, 배경용 `CodeRainBg`
14. `ScreenshotGrid` — `items, at, cw=220, ch=150` / `ScreenshotCarousel` — `items, speed=25`(px/초)
15. `VersionStack` — `versions[{content, year}], at, hold=36, cx=1350`
16. `IconRowGrid` — `items, at, stagger=11, perRow=[5,4], d=250`
17. `TreeDroplines` — `root, kids, at, rise=60`
18. `ShieldWings` — `text, at, shields[{label, icon?}]`
19. `MapPin` — `img, x, y`(꼬리 끝), `at, d=130, label?`
20. `MedallionTree` — `items[{img, name, color, x, y}], center, at, stagger=30, conclusion?`
21. `PuzzleJoin` — `left, right, at, dur=26`

다른 곳에서도 쓸 수 있게 공용 헬퍼를 export 했습니다: 선을 일정 속도로 그리는 `polyUpTo`, 가로 방향 모션블러 `HBlur`, 알약 라벨 `Pill`, 플랫 아이콘 20종 `Icon`, 코드가 흐르는 배경 `CodeRainBg`. 데모 문구는 짜장면·인천 주제 한국어이고, 이미지는 public/img와 public/real에 있는 것만 썼습니다.

Files are in motion/video/src:
- lib/callouts.tsx
- gallery/callouts.tsx