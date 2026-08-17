# 레이어 분리 결과 수정 — 낱개 삭제·재생성

작성일: 2026-08-13
대상: `auto_kairos_adobe` 백엔드 + CEP 프로덕션 시트

## 문제

레이어 하나가 잘못 나와도 고칠 방법이 **씬 전체 재분리**뿐이다. 재분리는 codex를 (요소 수 + 1)회 부르므로 느리고, 멀쩡한 레이어까지 새로 뽑는다. 그동안 잘못된 레이어는 시트와 컴프에 그대로 남는다.

## 설계

### 1. 요소 명세 사이드카

분리에 쓴 요소 정보(name/location/kind)가 지금은 남지 않는다(`__kinds.json` 은 kind만). 레이어 하나를 다시 만들려면 그 요소의 프롬프트 재료가 필요하므로, 분리할 때 `layers/{sid}__elements.json` 을 같이 쓴다.

```json
[{"layer": "ab12__0_인물_char", "name": "왼쪽 인물", "location": "화면 좌측", "kind": "character"}]
```

`layer` 는 확장자·버전 접미사를 뺀 파일 stem. 사이드카가 없는 기존 프로젝트는 파일명 `{sid}__{i}_{슬러그}[_char]` 과 `__kinds.json` 으로 복원한다. `location` 만 비고 나머지는 동작한다.

### 2. 레이어 삭제 — `POST /api/layers/delete`

입력 `{project_id, sceneNumber, layer}` (layer = stem 또는 `layers/…png` 상대경로).

1. 파일을 지우지 않고 `layers/_prev/` 로 옮긴다 — 기존 `_archive_prev_layers` 와 같은 무삭제 규칙.
2. `__elements.json` · `__kinds.json` 에서 그 항목을 뺀다.
3. **남은 요소 기준으로 배경을 재생성한다.** 지운 요소는 이제 배경에 있어야 하기 때문. codex 호출 1회라 비동기 잡으로 돌린다.
4. 같은 씬의 배경 재생성 잡이 이미 running이면 **그 잡을 취소하고** 새로 시작한다. 연속으로 여러 개 지워도 배경은 사실상 마지막 한 번만 만들어진다.

배경 레이어(`{sid}__bg`)는 삭제 대상이 아니다(컴프에 필수). 요청이 오면 422.

### 3. 레이어 하나 재생성 — `POST /api/layers/regenerate`

그 요소의 명세로 요소 레이어만 다시 뽑는다. 기존 QC(투명 비율·위치 점수) + 1회 재시도 + 실패 시 이전 판 유지 로직을 그대로 쓴다. 이전 파일은 `_prev` 로. **배경은 건드리지 않는다** — 요소 구성이 그대로이므로.

### 4. imagegen 리팩터링

`split_scene_to_elements` 안의 클로저 `_element` / `_bg` 를 모듈 함수로 꺼낸다.

- `generate_element_layer(proj_dir, scene_image, sid, index, spec, others, *, out_base, scene_size, style)` → 결과 dict
- `generate_background_layer(proj_dir, scene_image, sid, names, *, out_base, scene_size, style)` → 결과 dict

세 경로(전체 분리 / 낱개 재생성 / 배경 재생성)가 같은 함수를 쓴다. 지금 `split_scene_to_elements` 는 130줄이 넘고 QC·재시도·배경을 한 몸에 갖고 있어, 나누면 각 함수를 따로 테스트할 수 있다.

### 5. 시트 UI

레이어 썸네일에 마우스를 올리면 우상단에 버튼 두 개.

- **✕** 삭제 — "이 레이어를 빼고 배경을 다시 만듭니다" 확인 후 실행
- **↻** 재생성 — 이 요소만 다시

배경 썸네일은 **↻** 만 보인다. 실행 중에는 해당 썸네일을 흐리게 하고 행 상태줄에 잡 로그를 표시한다. 완료되면 그 행만 새로고침한다.

### 6. 범위 밖

- 요소 목록 편집(둘을 하나로 합치기 등)은 기존 재분리 흐름(⧉ 레이어 → 분석 → 체크)을 쓴다.
- `_prev` 에 쌓인 파일 정리·복구 UI.

## 파일

| 파일 | 변경 |
|---|---|
| `backend/imagegen.py` | 요소/배경 생성 함수 추출, 요소 사이드카 읽기·쓰기, 낱개 삭제·재생성 |
| `backend/router.py` | `/api/layers/delete`, `/api/layers/regenerate` |
| `cep/…/js/storyboard.js` | 썸네일 hover 버튼, 잡 폴링, 행 새로고침 |
| `cep/…/index.html` | 버튼 스타일 |

## 테스트

- 사이드카 왕복: 분리 후 `__elements.json` 이 생기고, 삭제하면 항목이 빠진다.
- 사이드카 없는 옛 프로젝트: 파일명 + `__kinds.json` 으로 name/kind가 복원된다.
- 삭제: 파일이 `_prev` 로 이동하고 활성 폴더에서 사라진다. 배경 프롬프트의 제거 목록에서 지운 요소 이름이 빠진다.
- 배경 레이어 삭제 요청은 422.
- 연속 삭제: 같은 씬의 진행 중 배경 잡이 취소된다.
- codex 호출(`_run_codex_image`)은 가짜로 대체해 검증한다.
