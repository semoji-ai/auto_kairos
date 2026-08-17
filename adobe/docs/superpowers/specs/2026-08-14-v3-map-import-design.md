# v3 지도 씬 임포트 — mapScene을 패널 좌표계로 번역

작성일: 2026-08-14
대상: `backend/v3_import.py`

## 문제

v3에서 프로젝트를 임포트하면 지도 씬이 `layout: "map"` 은 얻지만 **좌표를 얻지 못한다.** `_map_scene` 이 `mapScene` 원본을 `out["mapScene"]` 에 통째로 저장할 뿐, 패널이 읽는 필드로 옮기지 않는다.

패널의 `cep/com.autokairos.pd/js/mapgen.js` 는 씬에서 `map_center` · `map_zoom` · `map_markers` · `map_route` 를 읽는다. 그 필드가 없으면 기본값으로 떨어진다 — `map_center` 기본은 `[37.5, 127.0]`(서울). 이란 공습 지도를 임포트해도 서울이 렌더된다.

## 좌표 순서가 반대다

이 작업의 핵심이다.

- **v3는 `[경도, 위도]`** — 마커 `coordinates: [51.39, 35.69]` 는 테헤란(경도 51.39, 위도 35.69). 카메라 `center: [53, 30]` 도 같은 순서.
- **어도비는 `[위도, 경도]`** — `mapgen.js:113` 의 `_swapLL(c) { return [c[1], c[0]]; }` 이 MapLibre에 넘기기 전에 뒤집고, 기본값 `[37.5, 127.0]` 도 위도가 앞이다.

**뒤집지 않으면 조용히 엉뚱한 곳이 렌더된다.** 테헤란(51.39, 35.69)을 그대로 넘기면 위도 51.39·경도 35.69, 즉 동유럽이 나온다. 예외도 경고도 없고 지도는 정상적으로 그려지므로 사람이 지명을 알아보지 못하면 발견되지 않는다.

## 설계

### 1. 변환

`_map_scene` 이 `mapScene` 을 만나면 아래를 씬에 쓴다.

| 어도비 필드 | 출처 | 변환 |
|---|---|---|
| `layout` | — | `"map"` |
| `map_center` | `camera.keyframes[0].center` | 순서 뒤집기 |
| `map_zoom` | `camera.keyframes[0].zoom` | 그대로 |
| `map_markers` | `markers[]` | `{"coord": 뒤집은 좌표, "name": label}` |
| `map_route` | `route` 가 좌표 배열이면 | 각 점 뒤집기 |
| `headline` | `mapScene.title` | 레이아웃 제목 |
| `source` | `mapScene.source` | 출처 |
| `map_v3` | `mapScene` 원본 | 통째로 보관 |

**첫 키프레임을 쓴다.** 마커가 모두 화면에 들어오고, 어도비는 지도 씬에 `slow_zoom_in` 을 자동으로 건다(`manifest.py` 가 `is_map and cam is None` 일 때 `{"type": "slow_zoom_in", "amount": 6}` 를 넣는다). 그래서 v3의 "넓게 시작해 밀어들어가는" 연출이 그대로 재현된다.

씬의 `title`(시트에 보이는 씬 이름)은 건드리지 않는다 — v3 지도의 제목은 `headline` 으로 간다. 레이아웃 정규화가 `headline` 을 `title` 로 읽는다.

### 2. 버리는 것

`mapType` · `mapStyle`(11종) · `territories` · `labels` · `bearing` · `pitch` · `appearAtFrame` · `prerenderedBg` · `camera.easing` · 두 번째 이후 키프레임은 어도비에 대응이 없다. 쓰지 않되 **`map_v3` 에 원본을 통째로 남겨** 나중에 지원할 때 다시 임포트하지 않아도 되게 한다.

`mapStyle` 을 테마로 번역하지 않는다. 어도비는 지도 타일을 **프로젝트/씬 테마**가 정하므로(`themes` 의 `map.tile`), 씬마다 스타일을 넣으면 테마 체계와 충돌한다.

기존 `out["mapScene"]` 저장은 `map_v3` 로 이름을 바꾼다 — `mapScene` 이라는 이름은 v3 원본과 어도비 필드를 헷갈리게 한다.

### 3. 잘못된 값은 만들지 않는다

좌표를 만들어내는 것보다 **없는 편이 낫다** — 없으면 패널이 기본값으로 가고 사람이 알아채지만, 잘못된 좌표는 정상으로 보인다.

- `camera.keyframes` 가 비었거나 첫 키프레임의 `center` 가 길이 2의 숫자쌍이 아니면 `map_center` 를 쓰지 않는다.
- `zoom` 이 숫자가 아니면 `map_zoom` 을 쓰지 않는다(패널 기본 5).
- 마커의 `coordinates` 가 길이 2의 숫자쌍이 아니면 **그 마커만** 건너뛴다. 씬 전체를 버리지 않는다.
- `route` 가 좌표 배열이 아니면 `map_route` 를 쓰지 않는다.

## 파일

| 파일 | 변경 |
|---|---|
| `backend/v3_import.py` | `_map_scene` 의 `mapScene` 분기를 변환으로 교체, 좌표 뒤집기 헬퍼 추가 |
| `tests/test_v3_import.py` | 변환·폴백 테스트 |

## 테스트

실제 v3 데이터(이란 공습 씬)의 값으로 고정한다.

- 첫 키프레임 `center [53, 30]` · `zoom 3.5` → `map_center == [30, 53]` · `map_zoom == 3.5`.
- 테헤란 마커 `[51.39, 35.69]` → `map_markers[0] == {"coord": [35.69, 51.39], "name": "테헤란"}`.
- 키프레임이 여러 개일 때 첫 번째를 쓴다(두 번째 `zoom 5.0` 이 아니다).
- `title`·`source` 가 `headline`·`source` 로 간다.
- `map_v3` 에 원본이 통째로 남는다.
- 폴백: `camera` 없음 → `map_center` 키 자체가 없다. 좌표가 문자열·길이 1·`None` → 해당 항목만 빠진다. 마커 하나가 깨져도 나머지는 남는다.
- 지도가 아닌 씬은 `map_*` 키가 생기지 않는다.

**지도가 실제로 그 위치에 렌더되는지는 자동 검증할 수 없다.** 패널에서 🗺 버튼을 눌러 MapLibre 타일을 받아 봐야 한다.

## 범위 밖

- `mapType` 별 연출 차이(경로 애니메이션·영역 오버레이).
- `mapStyle` 을 테마로 번역하는 것.
- 마커 등장 타이밍(`appearAtFrame`)을 AE 키프레임으로 옮기는 것.
