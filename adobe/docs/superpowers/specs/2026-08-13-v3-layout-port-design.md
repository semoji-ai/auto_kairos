# v3 레이아웃 이식 — 공통 계약 + 범용 렌더러 + 별칭 폴백

작성일: 2026-08-13
대상: `auto_kairos_adobe` 씬 레이아웃(`build_scene.jsx` renderLayout) + 매니페스트 + v3 임포트 + 씬 스키마

## 문제

v3는 씬마다 `visualization` 객체를 갖고 Remotion 컴포넌트 **21종**이 그렸다 — BarChart·LineChart·PieChart·Compare·Timeline·TableView·TechTree, Slide 계열 13종(List, Numbered, Highlight, Statistic, Proscons, Definition, Summary, Profile, Ranking, Process, Checklist, Qna, Countdown).

어도비는 **7종**만 안다: `cinematic` `headline_only` `items_list` `metric_spotlight` `bar` `quote` `map`. 그리고 v3에서 임포트하면 그마저도 쓰이지 않는다 — `v3_import._map_scene` 이 `visualization.creative.layout`·`items`·`values`·`mapScene` 을 모두 버려서 **모든 씬이 `cinematic`(이미지 씬)이 된다.**

어휘는 이미 같다. v3 `creative.layout` 값이 `"headline_only"` 로, 어도비 `layout` 필드와 같은 이름이다. 끊긴 것은 배선이지 개념이 아니다.

## 핵심 관찰

v3 컴포넌트 21종은 **데이터 계약이 거의 하나다.** 실제 사용 빈도:

| 필드 | 사용 컴포넌트 수 |
|---|---|
| `title` | 32 |
| `items` | 29 |
| `imagePath` | 23 |
| `source` | 22 |
| `values` | 14 |
| `unit` | 11 |
| `descriptions` | 8 |
| `left`/`right` | 6 |
| `profileName`/`profileSubtitle` | 2 |
| `relations` | 1 |

즉 21개의 서로 다른 구조가 아니라 **하나의 구조에 렌더러가 21개**다. 그래서 그 필드만으로 그리는 범용 렌더러 하나면 어떤 레이아웃이든 내용은 온전히 화면에 나온다 — 모양이 그 레이아웃 고유의 생김새가 아닐 뿐이다.

## 설계

### 1. 공통 데이터 계약

씬에 v3와 같은 필드를 둔다.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `title` | string | 제목/헤드라인 |
| `items` | string[] | 항목 |
| `values` | number[] | 수치(`items` 와 인덱스 대응) |
| `descriptions` | string[] | 항목별 보조 설명 |
| `unit` | string | 값 단위(`%`, `만 명`) |
| `source` | string | 출처 표기 |
| `left`/`right` | {title, items} | 비교 양쪽 |
| `relations` | string[] | 노드 연결(tech_tree) |
| `profileName`/`profileSubtitle` | string | 인물 카드 |

**기존 어휘는 버리지 않고 정규화한다.** 정규화는 `backend/scene_layouts.py`(신규) 한 곳에서만 한다.

| 기존 | 정규 |
|---|---|
| `headline` | `title` |
| `sub` | `descriptions[0]` |
| `chart.labels` / `chart.values` | `items` / `values` |
| `value` + `label` | `values[0]` + `items[0]` |
| `quote_text` / `quote_who` | `items[0]` / `source` |

매니페스트는 **정규화된 형태만** jsx에 넘긴다. jsx는 별칭을 몰라도 되고, 기존 프로젝트는 그대로 돈다.

### 2. 레이아웃 해석 — 3단

`resolve_layout(name) -> str` 이 어떤 이름을 받아도 그릴 수 있는 렌더러 이름으로 바꾼다.

1. **고유 렌더러가 있으면 그것.**
2. **없으면 별칭.** v3 라우터가 이미 쓰는 매핑을 그대로 가져온다 — `impact_count`·`dramatic_number`·`counter_wall`·`icon_stat`·`slide_bignum` → `slide_statistic`, `split_contrast` → `compare`, `spotlight_reveal`·`title_card` → `slide_highlight`, `narrative_build`·`word_cascade`·`icon_grid` → `slide_list`, `reveal_sequence` → `slide_numbered`, `graph` → `bar_chart`, `diagram`·`slide_compare` → `compare`.
3. **그래도 없으면 범용 렌더러.** 제목 + 항목 목록(값이 있으면 항목 옆 수치, 설명이 있으면 아랫줄, 출처는 하단).

**`cinematic` 으로 떨어지는 경우는 없다.** 0단계만 끝나도 v3의 21종 전부가 화면에 제대로 나온다.

### 3. 단계

- **0단계(필수)** — 공통 계약 + 정규화 + 별칭표 + 범용 렌더러. 여기까지가 "대응 완료"다.
- **1단계** — 목록형 고유 렌더러 6종: `slide_list` `slide_numbered` `slide_checklist` `slide_summary` `slide_ranking` `slide_statistic`.
- **2단계** — 구조형 4종: `compare`(=proscons) `slide_process` `timeline` `table`.
- **3단계** — 차트·특수 8종: `line_chart` `pie_chart` `tech_tree` `slide_profile` `slide_qna` `slide_definition` `slide_countdown` `slide_highlight`.

기존 5종(`headline_only` `items_list` `metric_spotlight` `bar` `quote`)은 그대로 두고, v3 이름이 오면 별칭으로 잇는다: `slide_list`≈`items_list`, `slide_statistic`≈`metric_spotlight`, `slide_highlight`≈`headline_only`, `bar_chart`=`bar`. `quote` 는 v3에 대응이 없어 어도비 고유로 남는다.

**이 스펙의 범위는 0단계까지다.** 1~3단계는 각각 별도 계획으로 잡는다 — 0단계가 끝나면 모든 레이아웃이 이미 동작하므로, 이후는 미관 개선이고 급하지 않다.

### 4. jsx 구조

`build_scene.jsx` 는 623줄이고 `renderLayout` 이 5종에 90줄이다. 20종이 되면 1,000줄을 넘는다. **레이아웃 렌더러를 `jsx/layouts.jsx` 로 분리**하고 `main.js` 가 `json2.jsx + layouts.jsx + build_scene.jsx` 순으로 이어 붙인다 — 지금 `json2.jsx + build_scene.jsx` 를 잇는 방식 그대로다.

레이아웃 하나 = `akLayout_<이름>(comp, s, ctx)` 함수 하나. `ctx` 는 `{W, H, S, colors, type, addTextL, addRectL, addBarShape}` — 기존 헬퍼를 넘겨 렌더러가 그것만 쓰게 한다. 등록표 `AK_LAYOUTS` 에서 이름으로 찾고, 없으면 `akLayout_generic`.

`build_scene.jsx` 의 `renderLayout` 은 등록표 조회 + 배경 솔리드만 남기고 나머지는 옮긴다.

### 5. 레이아웃 목록의 단일 출처

지금 목록이 세 곳에 흩어져 있고 **이미 어긋나 있다** — `backend/scene_analysis.py` 의 `_LAYOUTS` 에 `bar` 가 빠져서 정상 `bar` 씬이 "layout 비표준값"으로 지적된다. `scene_layouts.py` 가 목록을 만들고 `scenes.schema.json` 검증과 `scene_analysis` 가 그것을 참조하게 한다.

### 6. v3 임포트

`v3_import._map_scene` 이 레이아웃과 데이터를 옮긴다.

- 레이아웃 이름: `visualization.vizType`(구형) → `creative.layout`(신형) 순으로 읽어 **원본 그대로** `layout` 에 넣는다. 어도비가 모르는 이름이어도 버리지 않는다 — 별칭표나 범용 렌더러가 받는다.
- 데이터: `title`·`items`·`values`·`descriptions`·`unit`·`source`·`left`·`right`·`relations`·`profileName`·`profileSubtitle` 을 그대로 복사.
- `mapScene` 이 있으면 `layout: "map"`.

## 파일

| 파일 | 변경 |
|---|---|
| `backend/scene_layouts.py` | 신규 — 레이아웃 목록, 별칭표, `resolve_layout`, `normalize_fields` |
| `backend/manifest.py` | 정규화된 데이터 필드를 매니페스트에 실음 |
| `backend/scene_analysis.py` | `_LAYOUTS` 를 `scene_layouts` 참조로 |
| `backend/v3_import.py` | 레이아웃·데이터 이관 |
| `skills/scene-decompose/scenes.schema.json` | enum 확장 |
| `cep/…/jsx/layouts.jsx` | 신규 — 렌더러 등록표 + 범용 렌더러 + 기존 5종 이관 |
| `cep/…/jsx/build_scene.jsx` | `renderLayout` 을 등록표 조회로 축소 |
| `cep/…/js/main.js` | jsx 이어붙이기에 `layouts.jsx` 추가 |

## 테스트

- 정규화: 별칭 각각(`headline`·`sub`·`chart`·`value`+`label`·`quote_text`+`quote_who`)이 정규 필드로 바뀌는지, 정규 필드가 이미 있으면 덮어쓰지 않는지.
- `resolve_layout`: 고유 → 별칭 → 범용 3단이 순서대로 동작하는지, 빈 값·`None`·모르는 이름이 범용으로 가는지, **어떤 입력도 `cinematic` 을 반환하지 않는지.**
- 레이아웃 목록이 스키마 enum과 `scene_analysis` 에서 같은지(어긋남 재발 방지). `bar` 가 세 곳 모두에 있는지.
- v3 임포트: `vizType` 우선순위, `creative.layout` 폴백, 데이터 필드 복사, `mapScene` → `map`.
- 매니페스트가 정규화된 필드를 싣는지.
- jsx 구조: `AK_LAYOUTS` 등록표와 `akLayout_generic` 존재, `main.js` 가 `layouts.jsx` 를 이어 붙이는지.

**AE 실제 렌더 결과는 자동 검증이 안 된다.** 범용 렌더러가 실제로 읽을 만하게 그리는지는 씬 하나를 AE에서 직접 봐야 한다.

## 범위 밖

- 1~3단계 고유 렌더러(별도 계획).
- `relations`(tech_tree 노드 연결선)의 시각화 — 범용 렌더러는 노드 이름만 나열하고 연결은 생략한다. 3단계에서 고유 렌더러가 그린다.
- v3 Remotion의 애니메이션(`vizAnimation`)·전환(`transition`) 이식.
