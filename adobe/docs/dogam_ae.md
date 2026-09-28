# 기법 도감 → AE (dogam_ae)

세모지 **기법 도감**(`semoji-motion/dogam`, 343기법)의 연출을 **고치기 쉬운 AE 레이어·키프레임**으로 옮기는 층입니다.
오토카이로스 결과물을 AE 에서 다듬을 때, 패널 **「기법 도감」 탭**에서 카드를 누르면 지금 열린 컴프에 그 연출이 걸립니다.

- 1단계 기반: 공용 코어 `core.jsx` · 동기화 `sync_dogam.py` · 검증 하네스 `dogam_verify.py`
- 2단계 파일럿: 12개 기법(레이어형 4 · 요소형 5 · 장면형 3)
- 3단계 패널 탭: `js/dogam.js`
- 나머지 약 320개는 같은 틀로 일괄 이식합니다(아래 「일괄 이식 계획」).

---

## 1. 구조

```
adobe/
├─ cep/com.autokairos.pd/
│  ├─ index.html · js/nav.js      「기법 도감」 탭(상세 뷰 세 번째 탭 + 목록 뷰 바로가기)
│  ├─ js/dogam.js                 카드·검색·변수 폼·적용/다시 적용/제거
│  └─ jsx/dogam/
│     ├─ core.jsx                 AKD 코어(디스패처·마커·이징 환산·세모지 헬퍼)
│     ├─ techniques/<id>.jsx      기법 하나 = 파일 하나 (AKD.register)
│     ├─ registry.json            AE 구현 목록 + 도감 메타(빌드 산출물, 커밋)
│     └─ assets/                  세모지 kit·소품·지도·미리보기 복사본(.gitignore, sync 로 재생성)
├─ scripts/
│  ├─ sync_dogam.py               에셋 복사 + registry 생성 + 변수 스키마 검증
│  ├─ dogam_verify.py             AE 렌더 ↔ 도감 미리보기 대조 시트
│  ├─ dogam_panel_check.py        패널 탭 스모크(Playwright, AE 없이)
│  └─ dogam_classify.py           343개 1차 분류 → docs/dogam_ae_classification.md
└─ docs/dogam_ae.md (이 문서) · dogam_ae_classification.md
```

**에셋을 확장 폴더 안(`jsx/dogam/assets`)에 두는 이유.** 패널은 심볼릭 링크로 설치돼 있어
`file://…/extensions/com.autokairos.pd/../../data` 처럼 `..` 로 나가면 링크 밖으로 풀립니다.
확장 폴더 안이면 패널(`<img src>`)과 JSX(`assetsRoot`)가 같은 상대 경로로 닿습니다 — `jsx/tylenol/assets` 와 같은 방식입니다.
미리보기 mp4(약 80MB)는 복사하지 않고 `assets/previews_src` → 세모지 도감 폴더 링크로 둡니다(`--mp4 copy` 가능).

### 1-1. 코어 API (`AKD`)

| 호출 | 하는 일 |
|---|---|
| `AKD.apply(id, ctx)` | 기법 적용. `ctx = {comp, layers, t, params, content, sceneNo, assetsRoot}` — 비우면 활성 컴프·선택 레이어·CTI·도감 기본값. 결과 JSON 문자열 `{ok, msg, group, names, error}` |
| `AKD.reapply({layer\|group, params, content})` | 같은 묶음을 지우고 (이전 변수 + 새 변수)로 같은 시각·같은 대상에 다시 |
| `AKD.remove({layer\|group})` | 만든 레이어 삭제 + 대상 레이어에 넣은 키·`AKD·` 효과·마스크 제거 + 바꾼 인/아웃·부모·정적 값 복원 |
| `AKD.selectedInfo()` | 선택 레이어의 `ak-dogam` 마커 목록(패널이 폼을 채울 때) |

**마커 규약.** 적용한 레이어마다 마커 `ak-dogam:<id>` 를 남기고 마커 파라미터에
`akd_group`(묶음) · `akd_role`(created/target) · `akd_t` · `akd_params` · `akd_content` · `akd_rec`(대상 레이어의 되돌리기 기록: 키 시각·원래 값·원래 인/아웃·부모)를 둡니다.
다시 적용·제거는 **이 마커만** 보고 동작합니다 — 이름 규칙에 기대지 않습니다.

**이징 환산(정확).** Remotion 의 `cubic-bezier(x1,y1,x2,y2)` 구간을 AE 템포럴 이즈로 바꿉니다.
나가는 키: 영향 `x1`, 속도 `(y1/x1)·Δ/T` · 들어오는 키: 영향 `1−x2`, 속도 `((1−y2)/(1−x2))·Δ/T`.
1차원 값 그래프에서 정확히 같은 곡선입니다. quad/cubic in·out, smoothstep(까딱 핑퐁)은 3차 베지어로 **정확**하고, easeInOutCubic 만 표준 근사(0.65,0,0.35,1)입니다.
스프링·감쇠 사인처럼 수식인 모션은 `AKD.fnKeys` 가 프레임마다 샘플한 뒤 **시작·끝·극값만 키**로 남기고 기울기를 이즈 속도로 넣습니다(고칠 수 있는 몇 개의 키).

**난수.** Remotion `random(seed)`(mulberry32 + 문자열 해시)를 `AKD.rand` 로 그대로 옮겼습니다 — 연기 덩어리 배치·스타버스트 보일링·깜빡임 스케줄이 미리보기와 같습니다.

**표현식은 한 곳뿐.** `AKD.alphaBBox`(누끼 PNG 의 발밑 찾기)가 `sampleImage` 표현식을 **임시 널에서 한 번 읽고 지웁니다** — 스크립트로는 픽셀을 못 읽어 불가피합니다. 결과물에는 표현식이 남지 않습니다.

**세모지 헬퍼.** `castRig`(kit 부위 PNG → 캐스트 프리컴프, 어깨 피벗 팔, 깜빡임 홀드 키) · `bobNull`(까딱까딱 널 핑퐁) ·
`bubbleComp`(흰 타원 말풍선) · `text`(한자 구간만 송티로 — 연성·주아·잘난·나눔스퀘어네오엔 한자 글리프가 없음) ·
`rect/ellipse/path/mask/shadow/gblur` · `textPop` · `echoOf`(잔상 사본) · `spring/lerp/bez`.
효과·마스크 이름은 `AKD·…`, 레이어 이름은 `NN 요소명`(NN = 씬 번호: 선택 레이어 이름 앞 숫자 → 컴프 이름 숫자 → `00`).

### 1-2. 기법 형식(kind)

| kind | 뜻 | 선택이 없으면 |
|---|---|---|
| `layer` | 선택 레이어에 키를 건다 | 오류(단, `create:true` 면 세모지 기본 대상을 만들어 건다 — 도장·컷어웨이) |
| `element` | 새 레이어/프리컴프를 만든다 | 그대로 만든다 |
| `scene` | 전환·카메라 — 선택 레이어가 있으면 그 장면을 대상으로(컷 자르기·카메라 부모) | 새 오버레이·가이드만 |

---

## 2. 기법 추가 방법(템플릿)

1. `jsx/dogam/techniques/<도감 id>.jsx` 를 만듭니다. **변수 이름·기본값은 도감 `params` 와 똑같이**(sync 가 검사).

```js
/* <이름> — <id>  [도감 <preview> · <Remotion 파일> <컴포넌트>]
   무엇을 어떻게 옮겼는지 한두 줄. 근사한 부분이 있으면 그 이유. */
AKD.register("<id>", {
  kind: "element", name: "<도감 이름>",
  // support: "partial", note: "근사한 부분",        ← 부분 지원이면
  params: { /* 도감 params 의 key: default 그대로 */ },
  content: { /* 글자·좌표·데이터 — 도감 데모 값을 기본으로(= 미리보기와 같은 결과) */ },
  apply: function (X) {
    var A = AKD, P = X.P, C = X.C;
    // X.comp · X.layers · X.t · X.f(n)=시작 후 n프레임 · X.fd · X.sceneNo · X.assetsRoot
    var l = A.text(X.comp, C.text, A.name(X, "요소명"), { font: A.FONT.yeonsung, size: P.size });
    A.anim(A.S(l), [X.t, X.f(P.popLen)], [[0, 0], [100, 100]], "quadOut");   // Remotion lerp 기본 = cubicOut
    l.inPoint = X.t;
    return { msg: "요소명 적용" };
  }
});
```

2. 규칙
   - 모션은 **키프레임**. 대상 레이어의 값은 `A.anim / A.holdKeys / A.fnKeys / A.set / A.setAttr` 로만 바꿉니다(되돌리기 기록이 남음).
   - 새로 만드는 레이어는 `A.text/rect/ellipse/path/solid/adjust/nul/addItem` 으로(자동으로 묶음·마커).
   - 프리컴프 안을 만들 때는 `var rec = A._rec; A._rec = null; try { … } finally { A._rec = rec; }` — 안쪽 레이어는 기록하지 않습니다(프리컴프째 지워짐).
   - Remotion `lerp()` 의 기본 이징은 **cubicOut**, `kf()` 는 **linear** 입니다. 그대로 옮기세요.
   - CSS `blur(px)` → `px × A.BLUR_K`, `brightness(1−d)` → 검정 단색 불투명 d.
3. `python3 scripts/sync_dogam.py --check` → registry 갱신·변수 불일치 경고 확인.
4. `scripts/dogam_verify.py` 의 `CASES` 에 도감 데모와 같은 설정을 넣고 돌려 시트를 봅니다.

---

## 3. 검증 절차

```bash
cd adobe
python3 scripts/sync_dogam.py                     # 에셋·registry
python3 scripts/dogam_verify.py                   # 파일럿 전부(AE 필요)
python3 scripts/dogam_verify.py stamp-slam        # 하나만
python3 scripts/dogam_verify.py --no-ae stamp-slam  # 시트만 다시
python3 scripts/dogam_panel_check.py              # 패널 탭 스모크(AE 불필요)
```

- 테스트 컴프는 1920×1080 30fps, 도감 데모와 같은 데이터·시작 프레임. 배경은 **도감 미리보기의 기법 시작 전 프레임을 2배로 키운 판**이라
  배경 차이 없이 기법만 비교합니다(그래서 전체 유사도 상한은 약 95~96% — 판 확대 손실).
- 시트: `adobe/tmp/dogam_verify/<id>/sheet.png` (왼쪽 도감 · 가운데 AE · 오른쪽 차이×3), 수치 `summary.json`
  (`sim` = 240×135 로 줄여 평균 색차, `region_sim` = 판과 달라진 픽셀만 — 기법 영역).
- **열린 AE 프로젝트는 닫지도 저장하지도 않습니다.** `_AKD_VERIFY` 폴더에 만들고 끝나면 새 아이템(id 스냅샷 밖)을 전부 지웁니다.
  스크립트 전체가 try/finally + `beginSuppressDialogs` — 모달이 뜨면 AE 가 멈추기 때문입니다.

---

## 4. 파일럿 결과

측정: `python3 scripts/dogam_verify.py` (2026-09-28). 유사도 = 240×135 로 줄여 평균 색차(100 − MAD/255). 배경이 미리보기 판을 2배 확대한 것이라
전체 유사도 상한이 약 95~96%입니다 — **기법 영역**(판과 달라진 픽셀만)과 시트를 눈으로 보는 것이 판정 기준입니다.
시트: `adobe/tmp/dogam_verify/<id>/sheet.png` (재생성: `--no-ae`).

| 기법 id | kind | AE 지원 | 전체 유사도 | 기법 영역 | 판정·차이점 |
|---|---|---|---:|---:|---|
| photo-pop | layer | native | 95.99 | 89.04 | 팝 곡선·줌블러·흰 링 일치. 원 안 사진 크롭 배율이 도감보다 약간 큼(도감은 사진이 조금 더 작게 들어감) |
| stamp-slam | layer (+생성) | native | 95.63 | 95.59 | 슬램·흔들림·잔상·깜빡임 타이밍 일치. 도장 위치 몇 px 차 |
| idle-bob | layer | partial | 99.03 | — | 인물 3명 위상·깜빡임 스케줄까지 일치(판 없이 레이어 씬 재구성). drift(패럴랙스) 미이식 |
| dim-cutaway-drop-exit | layer (+생성) | native | 96.79 | 95.43 | 딤·슬라이드업·와이프·낙하·딤 해제 일치(캐스트 리그 walker1). 와이프 중간 프레임 폭 약간 느림 |
| starburst-echo | element | native | 96.32 | 98.01 | 본체 팝·고스트 에코·보일링 모양(같은 난수) 일치 |
| year-tag | element | native | 96.64 | 96.58 | 슬라이드·교체(이전 태그 자동 아웃) 일치. 교체 중 두 롤러가 1~2f 더 보임 |
| scroll-label | element | native | 96.09 | 93.98 | 펼침·스프링(극값 키)·한자 세로쓰기·퇴장 일치 |
| wipe-reveal-bubble | element | native | 98.48 | 93.62 | 와이프·퇴장 축소 일치. 차이는 배경 판의 입 모양(도감은 말하는 입) |
| bar-chart-v | element | native | 98.92 | 96.95 | 리본·막대·값·마스코트 팝·그룹 스태거 일치 |
| smoke-wipe | scene | native | — | — | **AE 검증 보류**(사용자 AE 작업으로 중단) — 코드·난수 배치는 준비됨 |
| map-route | scene | partial | — | — | **AE 검증 보류** — 지도 PNG 프리렌더, 울릉도·독도 도형 포함 |
| pullback-reveal | scene | native | — | — | **AE 검증 보류** — 가이드 널 스케일·위치 키 |

**AE 실측으로 드러나 고친 것(다음 이식에도 해당)**

1. `layer.setParentWithJump(p)` 는 스크립트에서 **값을 그대로 둬 자식이 화면에서 튑니다.** 화면 위치를 지키는 것은 `layer.parent = p` 입니다(`AKD.parent`).
2. 도형 그룹·효과 목록에 속성을 **하나 더 붙이면 앞서 받아 둔 형제 속성 참조가 무효**("Object is invalid")가 됩니다. 다 붙인 뒤 다시 찾습니다.
3. 마스크·패스 값은 템포럴 이즈 속도로 환산할 수 없어 이징 구간을 프레임 키로 굽습니다(`shapeAnim`).
4. 스케일은 3차원 값 — 2차원만 넘기면 이즈 계산에서 NaN(코어가 0 으로 채움).
5. 스크립트 오류가 AE 모달로 뜨면 AE 가 멈춰 사용자가 OK 를 눌러야 합니다 — 하네스는 전부 try/finally, 오류 메시지 조립도 try 로.

**아직 확인 못 한 것**: smoke-wipe·map-route·pullback-reveal 의 AE 렌더 대조, 왕복 검사(`dogam_verify.py --roundtrip`: 적용→다시 적용→제거 후 대상 레이어 원상 복구 — 도장·까딱·사진 팝·연기 컷·가이드 카메라·컷어웨이).
재개하면 `python3 scripts/dogam_verify.py smoke-wipe map-route pullback-reveal && python3 scripts/dogam_verify.py --roundtrip`.


---

## 5. 일괄 이식 계획(나머지 약 320)

1차 분류 전체 표: [`dogam_ae_classification.md`](dogam_ae_classification.md) (`scripts/dogam_classify.py`)

| 분류 | native | partial | render | 제외 | 합계 |
|---|---:|---:|---:|---:|---:|
| HUD·자막·포맷 | 9 | 3 | 0 | 0 | 12 |
| 감정·효과 FX | 12 | 12 | 7 | 5 | 36 |
| 구성·엔딩 | 12 | 2 | 0 | 2 | 16 |
| 배경·루프 | 5 | 14 | 3 | 5 | 27 |
| 사진·자료 처리 | 22 | 7 | 2 | 0 | 31 |
| 전환 | 19 | 19 | 4 | 0 | 42 |
| 차트·인포그래픽 | 38 | 9 | 3 | 0 | 50 |
| 카메라 | 10 | 2 | 0 | 0 | 12 |
| 캐릭터 연기 | 27 | 12 | 1 | 0 | 40 |
| 콜아웃·라벨 | 42 | 9 | 0 | 0 | 51 |
| 텍스트·타이포 | 21 | 5 | 0 | 0 | 26 |
| **합계** | **217** | **94** | **20** | **12** | **343** |

- **native(217)** — 트랜스폼·마스크·도형·텍스트·기본 효과로 키프레임 재현. 파일럿 헬퍼(`textPop`·`bubbleComp`·`castRig`·`echoOf`·`fnKeys`)로 대부분 30~80줄.
- **partial(94)** — 핵심 모션은 키, 한 부분만 근사: 지도(MapBg 프리렌더 PNG), 노이즈·그레인·글리치(AE 효과), 입자·연기(키 굽기, 무거움), 3D 카드 플립(3D 레이어), 물리 흔들림(fnKeys).
- **render(20)** — WebGL 지구본·셰이더 터널·유체·불꽃처럼 키로 옮기면 손이 더 가는 것. Remotion 에서 **알파 영상(ProRes 4444)이나 PNG 시퀀스**로 뽑아 AE 레이어로 얹고, 시작 시각·크기만 AE 에서 고칩니다. 한 번 렌더 러너(`npx remotion render … --props`)를 도감 id 로 호출하는 `render` 형식을 추가하는 것이 다음 기반 작업입니다.
- **제외(12)** — 금지(방사형 광선 10) · 분석만(구현 없음 2).

**순서 제안(난이도·재사용 기준)**

1. **콜아웃·라벨 / 텍스트·타이포(native 63)** — 파일럿 요소형과 같은 틀(말풍선·두루마리·도장·텍스트 팝). 가장 빨리 늘어납니다.
2. **차트·인포그래픽(native 38)** — `bar-chart-v` 의 막대 헬퍼를 `chart` 공용으로 올린 뒤 가로 막대·파이·선 그래프(Trim Paths).
3. **전환·카메라(native 29)** — `smoke-wipe`(컷 자르기)·`pullback-reveal`(가이드) 패턴. 휩(방향 블러)·디졸브·커버는 한 파일에 kind=scene 으로.
4. **캐릭터 연기(native 27)** — `castRig` 로 포즈·표정 교체(홀드 키), 팔 회전(어깨 피벗).
5. **partial** — 효과 근사 규칙을 코어에(`A.noise`, `A.tint`, `A.threeD`) 모은 뒤 일괄.
6. **render** — 렌더 러너 형식 추가 후 일괄.

에이전트 병렬화: 카테고리별로 나누되 **코어는 한 사람만** 고칩니다(헬퍼 추가는 코어 PR 먼저 → 기법 PR).
각 기법 PR 은 `sync_dogam --check` 경고 0 + `dogam_verify` 시트 첨부가 조건입니다.
