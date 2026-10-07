# impl_backgrounds

15개 기법을 전부 만들었습니다. 파일은 `src/lib/backgrounds.tsx`(신규)와 `src/gallery/backgrounds.tsx`(데모 18개, 총 1785f) 두 개만 건드렸습니다. `npx tsc --noEmit -p .` 에러 없이 통과했고, 스틸은 30장 정도 렌더해서 눈으로 확인했습니다. 그 과정에서 문제 3개가 보여 고쳤습니다: 모자이크가 안 생기던 것, 관객 실루엣이 머리만 점처럼 떠 있던 것, 태극기 태극 방향이 뒤집혀 있던 것. 방사형 광선 패턴은 한 곳도 쓰지 않았습니다. 무작위 요소는 모두 `random(seed)`라서 같은 프레임은 늘 같은 결과가 나옵니다.

**컴포넌트와 props** (`src/lib/backgrounds.tsx`)
1. `MatrixRain {color="#3FBF3F", head, bg="#000", speed, density, seed}` — 숫자와 라틴 글리프만 씁니다. 깊이 레이어 3개로 크기 16/26/40, 블러 1.8/0.7/0, 속도 5/9/15px/f, 불투명 0.35/0.65/1. 맨 앞 글리프는 흰빛이고, 가까운 레이어에 글로우가 있습니다. 청록 버전은 `color="#2FD6C8"`로 씁니다.
2. `MoneyRain {n=42, coinRatio=0.35, speed, seed, at}` — 플랫 녹색 지폐(₩)와 금화. 회전하면서 scaleX 플립을 하고, 지폐는 세로로 눌리며 뒤집힙니다. 배경이 투명한 오버레이이고 루프합니다.
3. `CodeScroll {bg="#1A2560", color, vx=-0.9, vy=-0.55, size, seed}` — 옅은 연두 코드 줄이 대각선으로 흐릅니다. 타일 구조라 이음매 없이 루프하고 비네트가 들어갑니다.
4. `BokehDrift {bg, colors(노랑/핑크/파랑/청록), n, pxPerSec=10, period=60, seed}` — 원 지름 60~250, 알파는 0.3↔0.7로 약 2초 주기입니다.
5. `SpotlightCone {x, floorY, topW, botW, bg, color, sparkles, fog, id, children}` — 블러를 준 사다리꼴 빔 하나와 바닥의 빛 웅덩이, 빔 안의 4각 트윙클. 인물은 `children`으로 빔 아래 레이어에 넣습니다. 안개는 `fog`를 켜거나 `FogBand {top=800, opacity, speed, seed}`를 따로 써도 됩니다.
6. `CrowdBokeh {bg, colors, lights, bpm=120, seed}` — 무대 보케 조명이 박자에 맞춰 깜빡입니다. 관객 실루엣은 2열로 박자에 들썩이고, 일부는 손을 들고 폰 라이트를 켭니다.
7. `CloudDrift {sky, pxPerSec=5, n, seed, children}` — 플랫 흰 구름이 좌→우로 흐르고 깊이에 따라 0.6~1.4배 속도가 다릅니다.
8. `BlurFillPhoto {img, ar=4/3, widthPct=0.88, maxHPct=0.9, kenBurns, kbFrames=120, text, textY, textSize, at, pop, pos}`
   - 배경은 같은 이미지를 1.3배, blur 30, 밝기 0.85로 깝니다.
   - 원본은 가운데에 폭 88%로 놓되, 세로 90%를 넘으면 맞춰 줄입니다.
   - 켄번스는 1.05→1.0 선형입니다.
   - 텍스트 오버레이는 같은 파일의 `OutlineText {lines, y, size, at}`(검정 글씨, 흰 외곽 8px, 그림자, textPop 등장)입니다.
9. `Pillarbox {img, source, ar=4/3, archive, kenBurns, pos}` — 출처 칩은 `SourceChip {text, right=36, top=880, size=22, at}`로 따로 export했습니다. 70% 다크 칩이고 자막 띠 바로 위에 붙습니다. InstaCard도 같은 칩을 씁니다.
10. `CaptureScroll {items:{img,title,meta?}[], channel, handle, avatar, bg="#F3ECDD", hold=9, ramp=18, vmax=9, cols=4}`
    - 브라우저 바, 채널 헤더, 탭, 썸네일 그리드로 페이지를 조립합니다.
    - 0.3초 멈췄다가 ease-in(속도 선형 증가)으로 등속 9px/f까지 올라갑니다.
    - 화면 아래로 새로 들어오는 줄은 blur 14→0으로 선명해집니다.
11. `PixelateAvatar {img, x, y, at, d=280, block=16, split="right"|"left"|"none", splitPx=9, verified, label, pos, id}` — photoPop으로 등장합니다. 파란 인증 배지와 라벨 칩이 붙습니다.
12. 번개는 두 컴포넌트입니다.
    - `LightningFlash {interval=45, flashLen=2, seed, rain, children}`: 먹구름, 빗줄기, 가지 친 흰 번개(글로우)가 1~2f 번쩍이고 그때 하늘도 밝아집니다.
    - `CartoonZaps {rect:[x,y,w,h], period=9, n=6, color="#FFE14A", at, seed}`: 사각형 둘레에서 노란 만화 번개 외곽선이 9f마다 자리를 바꾸며 깜빡입니다.
13. `FlagWave {flags=["kr","cn"], x, y, w, hold=60, xfade=15, amp=30, slices=96, pole}` — 세로 슬라이스 96개를 사인으로 흔들고 명암을 줍니다. 깃대 쪽은 고정됩니다. 기본 깃발은 태극기(4괘 포함), 오성홍기, 3색기 세 가지이고, 다른 깃발은 ReactNode로 직접 넘기면 됩니다.
14. `InstaCard {img, user, caption, likes, source, bw=true, at, avatar, pos}` — 흰 카드 왼쪽에 흑백 사진, 오른쪽에 캡션 컬럼과 아이콘. 배경은 같은 사진을 blur 40으로 깔고 비네트를 줍니다. 출처 칩이 붙습니다.
15. `TonalWordmark {text, bg="#C8412F", tone="rgba(255,255,255,0.08)", size=300, pxPerSec=12, y, rows, font="Jalnan", children}`

**사양과 다른 점**
- **PixelateAvatar 모자이크 방식:** "작게 렌더한 뒤 `image-rendering: pixelated`로 확대"는 Chrome 렌더링에서 모자이크가 생기지 않았습니다. transform으로 확대하면 원본에서 바로 다시 그려 버립니다. 그래서 역시 canvas를 안 쓰는 SVG 필터(feFlood+feTile로 블록당 한 점만 샘플한 뒤 feMorphology dilate로 채움)로 바꿨습니다. 16px 블록이 제대로 나오는 것을 확인했고, RGB 분리도 SVG 필터(R과 GB 채널을 반대로 밀고 screen 합성)입니다.
- **MoneyRain 지폐:** 지폐 모양을 흉내 내지 않고 ₩ 문양만 넣은 플랫 녹색 지폐로 만들었습니다.
- **TonalWordmark 루프:** 텍스트를 8번 반복해 두고 흘리는 방식이라 완벽한 루프는 아닙니다. 12px/s면 몇 분은 버팁니다.
- **CloudDrift 속도:** 사양대로 5px/s라 90f 데모에서는 움직임이 거의 안 보입니다. 기본값은 그대로 두었고 `pxPerSec`로 올릴 수 있습니다.
- **같은 화면에 여러 개 쓸 때:** SpotlightCone과 PixelateAvatar는 SVG 필터 id가 겹치지 않도록 인스턴스마다 `id` prop을 다르게 줘야 합니다.



---
## 최종 요약(에이전트 마지막 텍스트)

15개 기법을 모두 만들어서 결과를 보고했습니다. 결과는 다음과 같습니다.

- **수정한 파일:** `src/lib/backgrounds.tsx`(새로 만듦)와 `src/gallery/backgrounds.tsx`(데모 18개, 총 1785프레임) 두 개만 건드렸습니다.
- **검증:** `npx tsc --noEmit -p .`는 에러 없이 통과했습니다. 스틸은 약 30장 렌더해서 직접 봤습니다.
- **렌더 보고 고친 문제 3개:**
  - PixelateAvatar에 모자이크가 안 생기던 것
  - 관객 실루엣이 머리만 점처럼 떠 있던 것
  - 태극기의 태극 방향이 뒤집혀 있던 것
- **규칙 준수:** 방사형 광선 패턴은 한 곳도 없습니다. 무작위 요소는 전부 시드 기반이라 같은 프레임은 늘 같은 결과가 나옵니다.

**사양과 다른 점**
- **PixelateAvatar 모자이크 방식:** 지시대로 작게 렌더한 뒤 `image-rendering: pixelated`로 확대해 봤지만 Chrome에서 모자이크가 생기지 않았습니다. transform으로 키우면 Chrome이 작은 이미지가 아니라 원본을 바로 다시 그리기 때문입니다. 그래서 canvas 없이 SVG 필터로 모자이크를 만들었고, 16px 블록이 제대로 나오는 것을 확인했습니다. 반쪽 RGB 분리도 SVG 필터입니다.
- **TonalWordmark:** 텍스트를 반복해 흘리는 방식이라 완벽한 루프는 아닙니다. 기본 속도(12px/s)면 몇 분은 문제없습니다.
- **CloudDrift:** 측정값인 5px/s를 그대로 써서 90프레임 데모에서는 움직임이 거의 안 보입니다. 필요하면 `pxPerSec` 값을 올리면 됩니다.
- **MoneyRain:** 지폐는 실제 지폐를 흉내 내지 않고 ₩ 문양만 넣은 플랫 녹색 지폐로 그렸습니다.

**쓸 때 주의할 점**
- SpotlightCone이나 PixelateAvatar를 한 화면에 여러 개 올리면 인스턴스마다 `id`를 다르게 줘야 SVG 필터가 서로 겹치지 않습니다.
- 출처 칩(`SourceChip`)은 따로 export했습니다. Pillarbox와 InstaCard가 같이 쓰고, 다른 장면에도 바로 붙일 수 있습니다.

컴포넌트별 전체 props 목록은 보고서에 따로 정리해 두었으니 필요하면 말씀해 주세요.