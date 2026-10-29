# impl_charts

## 결과

13개 차트 컴포넌트를 `src/lib/charts.tsx`(838줄)에 만들었고, 갤러리 `src/gallery/charts.tsx`에 데모 16개(총 1820f)를 채웠습니다. `DEMOS`, `GALLERY_DUR`, `Gallery = runGallery(DEMOS)`는 그대로 export합니다. `npx tsc --noEmit -p .`는 에러 없이 통과했습니다. 스틸 약 30장(완성 프레임과 애니메이션 중간 프레임)을 렌더해 눈으로 확인했고, 겹침 두 건을 고쳤습니다. DiscPie3D에서 캐릭터가 %라벨을 가리던 것, WaterfallStairs 데모가 화면 한쪽에 몰려 있던 것입니다. 다른 공유 파일은 수정하지 않았습니다.

**규칙 준수:** 모든 컴포넌트는 `at`과 결정적 props만 받고, 난수는 `random(seed)`만 씁니다. 방사형 광선·선버스트 배경은 한 곳도 없고, 배경은 `GlowBg`(부드러운 radial glow)입니다. 한자 워드마크는 `hz()`로 감쌌습니다.

## 컴포넌트

| # | 이름 | 주요 props | 구현한 스펙 |
|---|---|---|---|
| 1 | `PieSweep` | `at,x,y,r,pct,base,wedge,long,fadeBase,second{pct,color,delay,label},icon,label,globe,wedgeText,sticker{img,side}` | 12시에서 시계방향 24f bezier(.3,0,.2,1), long은 48f easeInOut. 두 번째 쐐기, 아이콘 +6f 팝(0→1.15→1.0, 7f), 라벨 8f 페이드. 원 페이드인 8f. 지구본→파이(0.3→1.1→1.0 5f, 홀드 6f, 이후 #F8C900 쐐기가 안쪽 텍스트까지 함께 마스킹). 반쪽을 덮는 스티커 사진 |
| 2 | `BarChartH` | `at,title,subtitle,rows[],winner,max,ticks,unit` | #F9F7F1 격자 종이, 검정 리본 8f 드롭, 부제 5f, 라벨 필 320×68 팝(1.12, 3f), 행 간격 4f / 94px, 막대 21f bezier(.35,0,.25,1), 승자 #73AF03/#94BD29·나머지 #BDBBB7, 약 1초 뒤 빨간 손그림 원 드로잉 |
| 3 | `BarChartV` | `at,title,groups[{x,bars,caption,delay}],max,maxH,mascot` | 리본 9f, 기준선에서 동시에 15f ease-out 성장, 강조 #FB0000·나머지 #555, 막대 위 마스코트 팝, 그룹은 45f 간격 반복 |
| 4 | `LineChart` | `at,years,values,min,max,underlay,axis:"draw"\|"fade",dot:"big"\|"small",pills[],stamp,crowd,box,title` | 65% 딤 언더레이. L축은 한 패스로 드로잉(세로 14f ease-in → 가로 14f ease-out, 17px) 또는 6f 페이드(24px). 연도 라벨과 점선 가이드, 시작점 5f 팝, 값 필, 라인 22f ease-out, 끝점 4f, 도장 슬램, 오렌지 군중 11f 상승 후 둥실 루프(`CrowdRow`) |
| 5 | `Podium` | `at,title,items[{name,logo,color,h,rank}],underlay` | 25% 딤 배경, 회색 리본에 음절당 2f 타이핑. 1위 14f easeOutCubic 후 2f 바운스, 2위 +14f(12f), 3위 +28f |
| 6 | `TimelineBar` | `at,nodes[{x,label}],y,wordmark,bg` | 노드 Ø50(흰 채움·검정 테두리) 3f, 라벨 0.5→1 3f, +11f에 38px 선이 12f 드로잉하며 헤드에 가로 모션블러 꼬리, 끝 노드 3f, 톤온톤 대형 워드마크 |
| 7 | `ZigzagArrow` | `at,dir:"up"\|"down",pts?,color,width,dur` | 상승: #E0161E 22px, 4번 꺾여 화면 밖→화면 밖, 14f, 화살촉이 머리를 따라감. 하락: 흰색 + 3f 번개 섬광 스프라이트 |
| 8 | `CounterBadge` | `at,x,y,n,label,icon,iconBg,scale,badge=45` | 빨간 배지 Ø45가 가속 간격(11→9→7f…)으로 카운트. 흰 원 칩이 9f easeOut으로 캡슐로 늘어나는 동안 그룹 전체가 재중앙정렬되고, 라벨 팝 |
| 9 | `StatGauge` | `at,x,y,pct,label,icon,iconBg,w,color` | 위에서 10f 드롭, 12f 뒤 #1DA1E6가 12f linear로 채워지고 채움 머리에 전기 스파크(`Spark`) |
| 10 | `WaterfallStairs` | `at,labels[],colors,x0,y0,dx,dy,bw=140,bh=40,step=15,hop=15,mascot` | 5색 블록이 15f 간격으로 대각 등장, 엘보 화살표로 연결, 마스코트가 포물선으로 15f 점프하고 2f 착지 스쿼시 |
| 11 | `MoneyTitle` | `at,text,x,y,size,face,side,depth=18,pile` | 돈더미(SVG 지폐·금화, `MoneyPile`)가 11f easeOutBack으로 상승. 숫자는 #FA9C00 면과 18층 #EB8000 압출, 0.3→1.12→1.0 4f 팝 |
| 12 | `DiscPie3D` | `at,comp,compStart,main,compColor,hero,rival{delay},mainLabel,compLabel,mainLabelAt?` | 타원 윗면과 측면 40px 디스크, #29C5E6과 오렌지 경쟁 조각, 위에 선 캐릭터. 경쟁자는 40% 고스트에서 10f 동안 불투명(흑백→컬러) |
| 13 | `AgileRings` | `at,items[{label,caption,c1,c2}],y,d,every=15` | 무지개 그라디언트 굵은 화살표 와이프, 두 색 반원 도넛(흰 중앙에 라벨)이 15f 간격으로 팝, 회색 필 캡션 페이드 |

재사용할 수 있는 헬퍼도 함께 export합니다: `Ribbon`(접힌 꼬리 리본, 드롭·타이핑), `HandCircle`, `LogoChar`(둥근 로고 캐릭터), `GlowBg`, `DimUnderlay`, `StampSlam`, `CrowdRow`, `Spark`, `Globe`, `MoneyPile`.

## 스펙과 다른 점
- **CounterBadge:** 배지 Ø45와 아이콘 150px는 원 스펙 크기 그대로 두고, 그룹 전체를 `scale`(기본 1.8)로 키웠습니다.
- **CounterBadge:** N이 12보다 크면 카운트를 12단계로 묶어서 올립니다(간격 최소 2f).
- **WaterfallStairs:** 기본값은 스펙대로 140×40이지만, 갤러리 데모는 1080p에서 읽히도록 200×56으로 키웠습니다.
- **ZigzagArrow 하락:** 번개 섬광은 드로잉 55% 시점에 3f 동안 나오고, 화면에 옅은 흰 플래시가 같이 들어갑니다.
- **Podium:** 1위가 가운데, 2위가 왼쪽, 3위가 오른쪽입니다. 올라오는 순서는 1위 → 2위(+14f) → 3위(+28f)입니다.
- **로고:** 로고 캐릭터와 앱 아이콘은 실제 브랜드 이미지 대신 도형과 텍스트로 만든 플레이스홀더입니다.

스틸 파일은 `/private/tmp/claude-501/-Users-hannah/94296d75-2e8b-459f-bce7-a42143a2a6f6/scratchpad/` 아래 `gal_charts_*.jpg`와 `grid_*.jpg`에 있습니다.

---
## 최종 요약(에이전트 마지막 텍스트)

13개 차트 컴포넌트를 만들고 갤러리에 데모 16개를 채워서 결과를 넘겼습니다. 타입 체크는 에러 없이 통과했고, 스틸 약 30장을 직접 렌더해서 확인했습니다.

- **파일:** 컴포넌트는 `src/lib/charts.tsx`, 데모(총 1820프레임)는 `src/gallery/charts.tsx`에 있습니다. 다른 공유 파일(fx.tsx, Main.tsx, Root.tsx)은 수정하지 않았습니다.
- **렌더 확인 중 수정:**
  - DiscPie3D에서 캐릭터가 72% 라벨을 가리던 것을 고쳤습니다.
  - WaterfallStairs 데모가 화면 한쪽에 몰려 있던 것을 가운데로 옮겼습니다.
- **규칙:** 방사형 광선 배경은 한 곳도 없고, 배경은 부드러운 radial glow만 씁니다. 난수는 `random(seed)`만 쓰고, 한자 워드마크 "共和春"은 `hz()`로 감쌌습니다.
- **공용 헬퍼:** 리본 배너, 손그림 원, 둥근 로고 캐릭터, 딤 배경, 도장, 군중 줄 같은 헬퍼도 함께 export해서 다른 장면에서 가져다 쓸 수 있습니다.

**스펙과 다른 점:**
- **CounterBadge:** 배지 Ø45와 아이콘 150px는 스펙 크기 그대로 두고, 그룹 전체를 1.8배로 키웠습니다. 숫자가 12보다 크면 카운트를 12단계로 묶어서 올립니다.
- **WaterfallStairs:** 기본값은 스펙대로 140×40인데, 1080p에서 너무 작아서 갤러리 데모만 200×56으로 키웠습니다.
- **ZigzagArrow 하락:** 번개는 선이 55% 그려졌을 때 3프레임 나오고, 화면 전체에 옅은 흰 플래시가 같이 들어갑니다.
- **Podium:** 1위가 가운데, 2위가 왼쪽, 3위가 오른쪽입니다. 올라오는 순서는 1위, 2위(+14f), 3위(+28f)입니다.
- **로고:** 로고 캐릭터와 앱 아이콘은 실제 브랜드 이미지가 아니라 도형과 텍스트로 만든 임시 그림입니다.

확인용 스틸은 scratchpad 폴더(`/private/tmp/claude-501/-Users-hannah/94296d75-2e8b-459f-bce7-a42143a2a6f6/scratchpad/`)의 `gal_charts_*.jpg`와 `grid_*.jpg`에 있습니다.