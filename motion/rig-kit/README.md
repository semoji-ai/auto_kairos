# semoji-rig-kit

코드로 그리는(HTML Canvas → MP4) 세모지 스타일 2D 리깅 캐릭터 엔진. 나레이션 문장에서 시간 슬롯을 만들고, 그 슬롯에 맞춰 캐릭터가 연기하는 장면을 붙인다.

```
engine/  base.js    캔버스, 상수, 2본 IK, 라인리스 그리기 도구
         rig360.js  360° 2D 리그(포즈, 팔 3D IK, 얼굴·몸·옷 그리기, 캐릭터 13명)
         stage.js   월드 좌표, nar()(나레이션→시간), label, 말풍선 등
         ctl.js     포즈 키 트랙(evalTrack), drawActor3
         props.js   소품 모양과 PROPS 등록
         seq.js     장면 이어 붙이기, 자막, 챕터 태그, step()/renderAt()
tools/   build.py shot.js strip.js board.js reach.js render.js jumps.js srt.js sheet.js probe.js pw.js
examples/ template_story.js(시작용 최소 예제), coffee_story.js(7장면 완성 예제)
cast.png  캐릭터 13명 생김새        props.png  소품 12종과 쥐는 지점
```

캐릭터나 소품을 고르기 전에 `cast.png`, `props.png`를 먼저 본다(이름만으로는 헬멧을 썼는지, 가방을 멨는지 알 수 없다).

## 명령

```bash
python3 tools/build.py my_story.js my_story.html           # 엔진 + 스토리 → HTML 한 장
node tools/shot.js my_story.html info                      # 장면 시작/길이, 나레이션 시간 슬롯
node tools/shot.js my_story.html '[[1.6,"a.png"],[4.2,"b.png"]]'   # 절대 시각(초)의 정지 프레임
node tools/strip.js my_story.html 3.6 5.2 8 move.png       # 3.6~5.2초 사이 8컷을 한 장에(움직임 확인)
node tools/reach.js my_story.html                          # 손이 닿지 않는 {hand} 목표 찾기 → "OK"가 나와야 한다
node tools/board.js my_story.html board.png 4              # 나레이션 줄마다 한 컷씩 타일(장면에 board:[t..]가 있으면 그 시각)
node tools/render.js my_story.html out.mp4 60              # 1920x1080 H.264
node tools/jumps.js my_story.html out.mp4                  # 영상 안의 급변 프레임(장면 경계의 페이드는 빼고 보여 준다)
node tools/srt.js my_story.html out.srt                    # 나레이션 타임코드
node tools/sheet.js my_story.html cast.png props.png       # 캐릭터·소품 일람(스토리에서 추가한 것 포함)
node tools/probe.js my_story.html '["새 캐릭터 이름"]'      # 360° 회전 튐 검사. 이름 뒤가 비어 있으면 정상
```

필요한 것: node, playwright(+chromium), ffmpeg, python3, 한글 폰트(Noto Sans CJK KR, macOS 는 시스템 한글 글꼴로도 된다).
이 폴더에서 `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm i` 로 playwright 를 받는다. 브라우저는 playwright 기본 → `$CHROMIUM` → `/opt/pw-browsers/chromium` → 이미 받아 둔 `ms-playwright` 캐시(chromium-*) 순서로 찾는다(`tools/pw.js`). `fc-list | grep -i "noto sans cjk"` 가 비면 한글이 깨진다.
URL 옵션: `?nosub=1`(자막 끔), `?syl=4.6`(초당 음절 수), `?live=1`(브라우저에서 재생), `?debug=1`(닿지 않는 손에 빨간 원).
`probe.js`는 스토리 HTML에 돌려야 스토리에서 `CAST.push`한 캐릭터가 들어 있다. 엔진만 검사하려면 `build.py --engine-only engine.html`.

## 좌표와 치수

- `world()` 좌표: 1단위 = 150px. x는 0(왼쪽)~12.8(오른쪽). **지면이 y=0, 위쪽이 음수.** 화면 맨 위는 y≈-6.2, 맨 아래는 y≈+0.97.
- 자막 띠는 화면 아래 966~1044px(월드 y +0.21~+0.73, 지면 바로 아래)에 깔린다. 챕터 태그는 왼쪽 위(대략 x<3.4, y<-5.4).
- 장면은 처음 0.22초 동안 페이드인, 마지막 0.18초 동안 페이드아웃한다. 프레임을 뽑을 때는 장면 시작+0.3초 ~ 끝-0.25초 사이에서 뽑는다.
- 캐릭터: 키 약 3.4단위(모자 포함 -4.2까지). 턱 y≈-2.57, 어깨선 y≈-2.37, 골반 y≈-1.49. 몸통 길이는 0.88뿐이다.
- 사람이 쓰는 물건의 치수: **작업대·카운터 윗면 y≈-1.1**(골반 높이에 두면 그 위 물건이 얼굴까지 올라온다), **문 높이 4.3 이상**, 간판·선반은 y -4.4보다 위. 창 안의 작은 인물(`sc`)은 4.2×sc 높이를 차지한다.
- yaw(트랙에서는 도 단위): 0=카메라 정면, 90=화면 오른쪽, -90=왼쪽, 180=뒷모습.
- z: +가 카메라 쪽(그만큼 화면에서 조금 아래로 그려진다). 보통 0.3~0.45에 세운다.
- **가까운 팔**: 오른쪽을 볼 때(yaw>0)는 `armR`, 왼쪽을 볼 때는 `armL`이 몸 앞에 그려진다. 보여줘야 할 동작과 소품은 가까운 팔에 준다. 먼 팔이 제 옆구리에 늘어져 있거나 거기서 든 소품은 몸에 가려진다(가슴 앞으로 뻗으면 먼 팔도 보인다).

## 손이 닿는 범위

손이 물건에 안 닿는 것이 가장 흔한 실수다. `{hand:[X,Y,Z]}`를 쓸 때 알아야 할 것:

1. 팔은 어깨선보다 0.15 아래, **y≈-2.22**에서 시작하고 길이는 **0.96**(캐릭터 `h` 배율만큼 곱)이다. 서 있는 인물의 손은 y≈-1.26 아래로 못 내려간다.
2. 어깨의 좌우 0.47은 캐릭터 기준이다. **옆모습에서는 그 0.47이 깊이(z)가 된다.** 가까운 어깨는 `인물 z + 0.47`쯤에 있으므로, 목표의 Z를 인물 z 근처로 주면 도달 거리의 절반을 화면 안쪽으로 가는 데 쓴다. **옆모습에서 가까운 팔의 목표는 Z = 인물 z + 0.35~0.5로 준다.**
3. 손은 화면에서 **y = Y + 0.16×Z**에 그려진다. y에 그려 둔 물건을 잡게 하려면 목표 Y를 0.16×Z만큼 위로(더 음수로) 준다.
4. 낮은 곳(y -1.3 아래)은 몸을 굽혀야 닿는다. `lean`(라디안, 기본 0.03, 0.9면 깊이 숙임)과 `hipY`(기본 1.49, **작을수록 앉음**)로 어깨를 내린다. 바닥에 내려놓기: 옆모습에서 0.42초에 `hipY:0.86, lean:0.9`, 손 목표 `[x+1.0, -0.5, z+0.35]`.
5. 두 사람이 건넬 때는 어깨 사이가 1.8 이하여야 손이 만난다. 멀면 둘 다 `lean:0.2`쯤 숙인다.

`node tools/reach.js story.html`이 닿지 않는 목표를 장면·인물·팔·부족한 거리·어깨 위치와 함께 알려 준다. **"OK"가 나올 때까지 고친다.**

## 장면

```js
const S1=(()=>{ const N=nar(['문장 1','문장 2']);  ...actors, set...
  return {N, dur:N.dur, tag:'01', title:'제목', cam:[fx,fy,1,1.045], draw(t){ back(t); drawActor3(a,t); fx(t) }} })();
const SCENES=[S1,S2];   // 파일 맨 끝
```

- `nar(lines, lead=0.45, tail=0.75)` → `[{t0,t1,text}]` + `.dur`. 줄 길이는 음절 수 ÷ 5.2초(최소 1.2초, 한글·영문자·숫자만 센다), 줄 사이 0.38초. `lead`, `tail`은 장면마다 줄일 수 있다(한 줄짜리 장면은 `nar([...],0.3,0.4)`).
- **길이 예산**: 장면 길이 = lead + Σ(음절÷5.2) + 0.38×(줄 수-1) + tail. 장면 하나에 말 없는 시간이 1.2초 붙는다. 20초면 4장면·6줄·75~80음절, 45초면 7장면·12줄·190음절쯤이다. 실제 녹음 길이를 알면 줄을 `['문장', 3.2]`처럼 [문장, 초]로 쓰면 그 길이를 쓴다. 연기 키는 `N[i].t0`, `N[i].t1` 기준으로 쓰여 있으므로 함께 따라 움직인다.
- `cam:[fx,fy,z0,z1]`: (fx,fy)를 중심으로 장면 동안 z0→z1로 천천히 확대. 생략 가능. 1→1.04~1.05가 적당.
- `noTag: t`: 그 시각부터 왼쪽 위 챕터 태그를 숨긴다(끝 장면에 큰 제목을 띄울 때). `board:[t1,t2]`: 보드에 넣을 대표 시각(장면 시각).
- `draw(t)`의 t는 장면 안의 시각. 뒤에서 앞 순서로 그린다(배경 → 뒤 인물 → 가구 → 앞 인물 → 효과).
- 인물은 통째로 한 층이다. "상자 안에 넣기", "문 뒤에서 나오기"는 그리는 순서와 `c.clip()`으로 만든다: 상자 앞면을 인물 뒤에 다시 그리거나, 손을 떠난 물건은 소품을 끄고 배경 물체로 그린다. 아직 등장하면 안 되는 인물은 그 시각 전에는 그리지 않는다.

## 배우와 포즈 키

```js
const a={ch:who('직장인'), seed:0.13, kicks:[2.1], tracks:[ [...], [...] ], gy:-0.25, sc:0.86, noShadow:1, live:(q,t)=>{}};
const P=drawActor3(a,t);            // P.x, P.arms[0]=오른팔, [1]=왼팔 ...
const h=handOf(a,P,0);              // 손목의 월드 좌표 {x,y,ux,uy,sc}
```

- **트랙 = 독립 채널.** 키 `{t,d,e,...필드}`는 직전 상태에서 d초 동안 e(기본 E.io)로 넘어간다. 값은 누적된다.
- **한 트랙 안에서 `t+d`가 다음 키의 `t`보다 크면 포즈가 튄다.** 겹쳐야 하는 움직임(위치/방향/걸음/팔/표정)은 트랙을 나눈다. 같은 필드는 뒤 트랙이 이긴다(뒤 트랙에서 그 필드를 처음 쓴 키부터).
- `kicks:[t]`: 그 순간 몸이 살짝 출렁인다(도착, 받기, 놀람).
- `gy`, `sc`: 뒤쪽 인물은 `gy:-0.25, sc:0.86` 식으로 작게·위로.
- 이징: `E.lin`(걷기 이동), `E.io`, `E.out`, `E.in`, `E.back`(살짝 넘쳤다 돌아옴, 손 뻗기·팝).

| 필드 | 뜻 |
|---|---|
| `x, z, y` | 위치(y는 점프) |
| `yaw, headTurn` | 몸 방향, 고개만 돌리기(도). headTurn은 yaw에 더해진다: +면 화면 오른쪽으로 |
| `walk, gait` | 0~1, `'walk'`/`'run'`. 이동 속도는 `SPEED('walk')`=2.8, `SPEED('run')`=6.25 단위/초에 맞춰야 발이 안 미끄러진다 |
| `swR, swL` | 걸을 때 팔 흔들기 세기(물건을 든 팔은 0) |
| `lean, hipY, nod` | 상체 숙임(라디안, 기본 0.03), 골반 높이(기본 1.49, 작을수록 앉음), 고개 끄덕임(+가 아래, -가 올려다봄) |
| `armR, armL` | `null`(내림) · `{a,b,ab,b2}`(각도: a 앞으로 들기, b 팔꿈치 굽힘, ab 옆으로 벌림) · `{hand:[X,Y,Z]}`(월드 목표) · `{local:[x,y,z]}`(몸 기준: x 그 팔 쪽 바깥이 +, y 어깨에서 아래로, z 앞으로) |
| `handR, handL` | `'open' 'grip' 'point' 'wave'` |
| `waveR, waveL, cheer, clap` | 0~1 반복 동작 |
| `propR, propL` | 소품 이름 또는 null (`d:0` 키로 바꾼다) |
| `propRot, steam, fill` | 소품 기울기(라디안), 컵 김, 바구니·스쿱 채움 |
| `mood, talk, blink, brow, look` | `'smile' 'grin' 'o'`, 말하기 0~1, 눈 감기 0~1, 눈썹 -1~1, 시선 [x,y] |

자주 쓰는 팔: 컵 들기 `{a:0.45,b:1.45}` · 옆으로 손 흔들기 `{a:0.25,ab:2.3,b2:0.55}`+`handR:'wave',waveR:1` · 옆모습에서 가리키기 `{a:1.75,b:0.55}`+`'point'` · 정면에서 위 가리키기 `{a:0.25,ab:2.55,b2:0.25}` · 던지기 `{a:-0.5,b:0.9}`→`{a:1.75,b:0.25}` · 주먹 불끈 `{a:0.95,b:1.75,ab:0.45}` · 마시기 `{local:[0.14,-0.2,0.5]}`+`propRot:-0.3` · 먼 손으로 바구니 `{local:[0.12,0.62,0.5]}`.

## 캐릭터

`who('이름')`: 바리스타, 라이더, 등산객, 요리사, 학생, 할머니, 화가, 러너, 직장인, 농부, 디제이, 비 오는 날, 로스터.
새 캐릭터는 스토리 파일 맨 위에서 `CAST.push({...})`. `name`은 필수다(`who()`가 이름으로 찾는다).

```js
CAST.push({name:'택배 기사',disc:'#CFE9DC',skin:SK[2],h:1.0,build:'std',brow:1.1,
 hair:{type:'short',col:'#2B2320'},hat:{type:'cap',col:'#2E7D5B',col2:'#256B4D'},eyes:'dot',mood:'grin',seed:0.7,
 top:{type:'jacket',col:'#2E7D5B',col2:'#FFFFFF',arms:'long',cuff:'#256B4D',collar:'#256B4D'},
 pants:{type:'long',col:'#2F3140'},shoe:{col:'#2F3140',sole:'#FFFFFF',stripe:'#2E7D5B'}});
```

주요 필드:

- `skin`(SK[0..5]), `h`(키 배율), `hd`(머리 배율), `build`(`std slim broad round`), `jaw`, `brow`, `nose`(`'short' 'round'`), `lash`, `lip`, `beard`, `stache`, `freckle`, `wrinkle`, `eyes`(`'dot' 'glasses' 'shades'`), `mood`, `seed`
- `hair:{type:'short|long|bun|pony|curly|bald', style:'part|bang|sweep|arch|perm', col}`
- `hat:{type:'beanie|cap|capBack|bucket|straw|toque|beret|helmet|headband|headphones', col, col2}`
- `top:{type:'apron|jacket|cardigan|raincoat|vest|chef|hoodie|stripe|tee|suit|overall', col, col2, arms:'long|short|none', cuff, collar}`
- `pants:{type:'long|shorts', col, cuff, fit:'std|wide|slim'}`, `shoe:{type:'sneaker|boot|dress', col, sole, stripe, toe}`
- `pack:{type:'box'|생략, col, col2, mat, charm}`, `scarf`, `towel`, `glove`(장갑 색), `watch`, `earring`, `sock`, `sockStripe`, `frame`(안경테), `disc`(바탕 원 색), `eyeR`(눈 크기)
- 옷 세부: `top.band`, `top.hem`, `top.sleeve`, `top.sleeveStripe`, `top.neck`, `top.tie`. `vest`는 `col`이 셔츠·소매, `col2`가 조끼. `apron`은 `col`이 셔츠, `col2`가 앞치마.

캐릭터를 추가하거나 리그를 고쳤으면 `probe.js`를 **스토리 HTML에** 돌려 360° 회전에 튀는 각도가 없는지 확인한다(`이름 median=… |` 뒤가 비어 있으면 정상).
알려진 저작권 캐릭터를 닮게 만들지 않는다. 오리지널만.

## 소품

기본: `'cup' 'case' 'parcel' 'bag'`. props.js: `'basket'`(fill) `'cherry'` `'rake'`(propRot) `'scoop'`(fill, propRot) `'trier'` `'kettle'`(propRot, 주둥이 끝 `KTIP`) `'sack'` `'beanbag'`.
추가: `PROPS.이름=(P,ux,uy)=>{ /* (0,0)이 쥐는 지점 */ }`. 인물 단위로, 손목에서 팔 방향으로 0.12 나간 지점에 그려지고 **손이 그 위에 덮인다**(작은 물건은 손가락 밖으로 0.1쯤 내밀어 그린다. 손과 같은 색이면 안 보인다). `P`는 포즈(`P.propRot`, `P.fill`, `P.t`), `(ux,uy)`는 팔뚝 방향.
모든 소품에는 모양 함수가 있어 손에 든 것과 바닥·탁자에 놓인 것을 같은 그림으로 쓸 수 있다: `cupShape(t,steam)`, `caseShape(w)`, `parcelShape()`, `bagShape()`, `basketShape(fill)`, `sackShape()`, `beanbagShape()`, `kettleShape()`, `rakeShape()`, `scoopShape(fill)`. 새 소품도 `xxxShape()`를 먼저 만들고 `PROPS.xxx=()=>xxxShape()`로 등록한다.
**소품을 건넬 때**: 주는 쪽 `propR:null`과 받는 쪽 `propL:'cup'`을 같은 시각의 `d:0` 키로 넣고, 두 손의 `{hand:[...]}` 목표를 같은 점 근처에 둔다.

## 그리기 도구

`F(col,x,y,w,h)` · `shape(pathFn,col)` · `rr(x,y,w,h,r)` `circ(x,y,r)` `poly(x1,y1,...)` `ell(x,y,rx,ry,rot)` → pathFn · `line(pathFn,w,col)` · `lifted(pathFn,col)`(작은 그림자로 띄우기) · `dk(hex,f)` `mix(hex,hex,k)` `lum(hex)` · `label(str,x,y,size,col,align,weight)`(월드 단위 글자) · `cloud` `tree` `heart` `sparkle` · `bubble(x,y,w,h,k,tail)`, `card(x,y,w,h,k)`(흰 말풍선/정보 카드. save를 열어 둔 채 돌아온다. 그 안 좌표로 내용 그린 뒤 `c.restore()`) · `popK(t,t0,d)`(튀어나오는 0→1) · `hash(n)`(고정 난수) · `sm(x)` `cl(x)` `lerp`.

스타일: 테두리 없는 평면 색. 형태는 색 차이와 작은 그림자(`SHC`, `TONE`)로 구분. 글자색은 `INK`, 배경은 `BG`.
