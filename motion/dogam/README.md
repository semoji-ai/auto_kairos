# 세모지 모션 기법 도감 (Dogam)

유튜브 채널 **세모지(세상의 모든 지식)** 스타일의 모션그래픽 기법을 한곳에 모은 **데이터 레이어**입니다.
레퍼런스 영상을 프레임 단위로 실측한 분석 보고서와 `video/src` 의 Remotion 구현을 기법 하나당 한 항목으로 이어 줍니다.

- 무엇을, 언제 쓰는지 (`summary`)
- 원본에서 잰 수치 (`spec`: 프레임 수·이징·크기·색)
- 어느 영상 몇 분 몇 초에서 나왔는지 (`sources`)
- 구현된 컴포넌트와 파일, 미리보기 id (`component`·`file`·`preview`)
- 상태: `구현` / `분석만`(아직 컴포넌트 없음) / `금지`

## 폴더 구성

| 경로 | 내용 |
|---|---|
| `techniques.json` | 도감 본체. 기법 항목 배열 (빌더가 생성하므로 직접 고치지 않습니다) |
| `build_techniques.py` | 항목 원본(`ENTRIES`) + 파일 경로 자동 채움 + 검증 + 통계 출력 |
| `analysis/` | 분석 에이전트 보고서 원문 (아래 참고) |

## 레퍼런스 영상

| ref | 영상 | 쓰임 |
|---|---|---|
| ref1 | 중식 4대문파편 — https://youtu.be/NZsB8vnv1FU | 1차 모션 어휘(전환·팝·캐릭터·HUD 구 포맷) |
| ref2 | 마이크로소프트편 — https://youtu.be/kAFIom5Xrrw | 차트·콜아웃·전환·캐릭터 기호·배경 루프 확장 |
| ref3 | 리뉴얼 포맷(디아지오 증류소편) — https://youtu.be/Lh0drBozqck | 2026-09 리뉴얼 HUD·자막·내용출처 |

## 스키마

```jsonc
{
  "id": "pie-sweep",                 // kebab-case, 전체에서 유일
  "name": "파이차트 웨지 스윕",        // 한국어 이름
  "category": "차트·인포그래픽",       // 아래 11개 중 하나
  "summary": "한 줄 설명(무엇·언제 쓰나)",
  "spec": "측정 수치 요약(프레임·이징·크기·색)",
  "sources": [                       // 병합된 모든 출처 (자체 구현 기법은 빈 배열)
    { "ref": "ref2", "video": "https://youtu.be/kAFIom5Xrrw", "time": "138:02", "note": "24f, Azure 25%" }
  ],
  "component": "PieSweep",           // 컴포넌트 이름 또는 null
  "file": "video/src/lib/charts.tsx",// 프로젝트 루트 기준 경로 또는 null
  "preview": "charts-01",            // <group>-NN 또는 null
  "status": "구현",                   // 구현 | 분석만 | 금지
  "tags": ["파이"]
}
```

- **category**: `전환`, `카메라`, `텍스트·타이포`, `콜아웃·라벨`, `차트·인포그래픽`, `사진·자료 처리`, `캐릭터 연기`, `감정·효과 FX`, `배경·루프`, `HUD·자막·포맷`, `구성·엔딩`
- **time**: 분:초. ref2 는 2시간 반짜리라 `147:16` 처럼 분이 60을 넘을 수 있고, 구간으로 잰 기법은 `0:45–5:00` 처럼 범위로 적습니다.
- **status 규칙**
  - `구현`: `component` 가 있고 `file` 이 실제로 존재함
  - `분석만`: 보고서에는 있지만 컴포넌트가 없음 (`component`·`file`·`preview` 모두 null)
  - `금지`: **방사형 줄무늬 광선·선버스트 배경 계열**. 욱일기를 연상시켜 사용자가 금지했습니다. 보고는 남기되 쓰지 않습니다. 대체재는 `GlowPulse`(원형 글로우+링), `GlowBg`(부드러운 radial glow). `fx.tsx` 에 `Rays` 가 남아 있지만 사용 금지입니다.
- 같은 기법이 여러 보고서에 나오면 한 항목으로 합치고 `sources` 에 모두 넣습니다. 보고서끼리 측정값이 다르면 `spec` 에 두 값을 같이 적습니다(예: 까딱 실측 40f vs 사용자 사양 10f).

## 항목 추가·수정 방법

1. `build_techniques.py` 의 `ENTRIES` 에서 해당 카테고리 블록에 `E(...)` 한 줄을 추가합니다.
   ```python
   E("new-technique", "새 기법 이름", "전환",
     "한 줄 설명", "수치 요약",
     [S("ref2", "12:34", "메모"), S("ref1", 227.0)],   # 초(float)를 주면 m:ss 로 바뀜
     "ComponentName", "transitions-20", tags=["태그"])
   ```
   - `component` 를 주면 `file` 은 `fx.tsx` / `lib/*.tsx` 의 export 목록에서 자동으로 찾습니다. `Main.tsx` 처럼 export 되지 않은 컴포넌트는 `file=` 을 직접 넘깁니다.
   - `fx.tsx` 컴포넌트는 `preview` 를 비워 두면 `gallery/core.tsx` 데모 이름의 `"컴포넌트명 — …"` 접두로 자동 매핑됩니다.
   - `component` 를 비우면 `status` 는 자동으로 `분석만`, 금지 기법은 `status="금지"` 를 명시합니다.
2. 실행합니다.
   ```bash
   python3 dogam/build_techniques.py
   ```
   `techniques.json` 을 다시 쓰고, 카테고리·상태별 개수, 도감에 연결 안 된 갤러리 데모, 경고를 출력합니다.
   다음 경우는 **오류로 종료**합니다: `preview` id 가 갤러리 `DEMOS` 에 없음, `file` 이 없음, id 중복·kebab-case 아님, category/status 값 오류, `구현`인데 component 없음, `분석만`인데 component 있음.
3. 새 컴포넌트를 만들었다면 해당 갤러리 파일(`video/src/gallery/<group>.tsx`)의 `DEMOS` 끝에 데모를 추가하고 그 번호를 `preview` 로 씁니다. **중간에 끼워 넣으면 뒤 번호가 모두 밀리니** 끝에 붙이세요.

## 미리보기 생성

미리보기 id 는 `<group>-NN` 입니다. `group` 은 `core`, `charts`, `transitions`, `callouts`, `characters`, `backgrounds` 중 하나이고, `NN` 은 그 파일 `DEMOS` 배열의 1부터 센 순번(두 자리)입니다.
`video/src/dogam/registry.tsx` 가 모든 갤러리 데모를 이 id 로 모으고, `Dogam` 컴포지션이 `id` prop 하나를 받아 해당 데모만 그 길이만큼 렌더합니다.

```bash
cd video
# 영상 한 편
npx remotion render src/index.ts Dogam out/dogam/charts-01.mp4 --props='{"id":"charts-01"}'
# 썸네일용 스틸 (프레임 지정)
npx remotion still src/index.ts Dogam out/dogam/charts-01.png --props='{"id":"charts-01"}' --frame=60
# 도감 전체 일괄 렌더
python3 -c "import json;[print(e['preview']) for e in json.load(open('../dogam/techniques.json')) if e['preview']]" | sort -u | \
  while read id; do npx remotion render src/index.ts Dogam "out/dogam/$id.mp4" --props="{\"id\":\"$id\"}" --timeout=60000; done
```

### 미리보기 파일 위치 (저장소 밖)

미리보기 mp4·jpg(약 92MB, 650여 개)는 저장소에 넣지 않습니다. `previews_dir.py` 가 다음 순서로 찾습니다.

1. 환경변수 `DOGAM_PREVIEWS_DIR`
2. `motion/dogam/previews` — 로컬 캐시 또는 NAS 로 가는 심볼릭 링크 (`.gitignore`)
3. NAS 백업 `/Volumes/jleavens/007_AI_Projects/semoji-motion_backup_20261007/dogam/previews` (마운트돼 있을 때)

`render_previews.py` 는 이 폴더에 쓰고, `build_viewer.py` 는 이 폴더를 보고 카드의 미리보기 유무를 정합니다. 뷰어(`index.html`)는 항상 상대 경로 `previews/` 를 읽으니 NAS 를 쓸 때는 `ln -s <NAS>/dogam/previews motion/dogam/previews` 로 링크하세요. 미리보기가 없어도 `build_techniques.py` 는 그대로 동작합니다(갤러리 `DEMOS` 만 봅니다).
AE 패널용 12개 미리보기는 `adobe/data/semoji-motion/dogam/previews` 에 따로 번들돼 있습니다.

여러 장을 동시에 렌더하면 webpack 캐시 경합으로 멈출 수 있습니다. 3~4개씩 나눠 돌리거나 `--timeout=60000` 을 붙이세요.
같은 컴포넌트의 변형 데모(예: `backgrounds-02` 청록 매트릭스)는 도감 항목과 1:1 로 연결되지 않을 수 있습니다. 빌더가 "연결 안 된 데모"로 알려 줍니다.

## analysis/ 폴더

분석 에이전트가 마지막에 넘긴 보고서 원문입니다. 각 파일 뒤에 에이전트의 짧은 최종 요약도 붙어 있습니다.
측정에 쓴 프레임 타일·스크립트는 세션 스크래치패드(`…/scratchpad/ana1~3`, `r2a1~4`)에 있어 휘발될 수 있습니다. 수치 근거는 이 폴더의 보고서를 기준으로 삼으세요.

| 파일 | 내용 |
|---|---|
| `ref1_00-05.md` | ref1 0:00–5:00 (카메라 원칙, 까딱 40f, 줌스루, 텍스트/원형 팝, 연도 태그 교체) |
| `ref1_05-10.md` | ref1 5:00–10:00 (풀백 리빌, 컬러 플리커 19f, 연기·불꽃 전환, 매직무브, 에코 팝) |
| `ref1_10-14.md` | ref1 10:00–14:28 (휩 v2, 블러 복제 배경, 이름표+화살표, 아이콘 흡입, 카드 플립, 아웃트로·엔드카드) |
| `ref2_00-39.md` | ref2 0:00–39:00 (꺾은선·파이 차트, 신문 풀아웃, 돋보기 콜아웃, 타자 인터스티셜, 글리치) |
| `ref2_39-78.md` | ref2 39:00–78:00 (지구본→파이, 콜아웃 커넥터, 버전 스택, 마스코트화, 배경 루프 5종) |
| `ref2_78-117.md` | ref2 78:00–117:00 (가로 막대, L축 선그래프, 필 충돌, CRT, 슬랫 모자이크, 캐릭터 소품) |
| `ref2_117-end.md` | ref2 117:00–154:57 (파이 24f, 분할 패널, 포디움, 커튼, 에너지 슬래시, 필름스트립, 엔딩) |
| `impl_charts.md` | 차트 13종 구현 보고 (`lib/charts.tsx`, 갤러리 16데모) |
| `impl_transitions.md` | 전환 19종 구현 보고 (`lib/transitions.tsx`, 컷/길이 상수) |
| `impl_callouts.md` | 콜아웃 21종 구현 보고 (`lib/callouts.tsx`, 갤러리 23데모) |
| `impl_characters.md` | 캐릭터 15항목 구현 보고 (`lib/characters.tsx`, 갤러리 19데모) |
| `impl_backgrounds.md` | 배경·미디어 15종 구현 보고 (`lib/backgrounds.tsx`, 갤러리 18데모) |

ref3(리뉴얼 포맷)은 별도 보고서 없이 `video/src/fx.tsx` 의 `HUD2`·`Subtitles` 주석과 `Main.tsx` 의 내용출처 표기를 근거로 넣었습니다.
