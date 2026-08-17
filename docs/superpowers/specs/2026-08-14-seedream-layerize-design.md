# 레이어 분리를 Seedream layerize로 전환

작성일: 2026-08-14
대상: `auto_kairos_adobe` 레이어 분리 경로(`imagegen`·`fal_api`·`manifest`·`build_scene.jsx`)

## 배경

지금 방식은 요소마다 이미지를 **다시 그린다** — "이 인물만 그리고 나머지는 전부 마젠타로" → 마젠타를 키잉해 투명 PNG. 다시 그리기 때문에 원위치·원크기가 어긋나고, 그걸 막으려고 키 컬러 자동 선택·크로마 키잉·위치 점수 QC·재시도가 붙어 있다.

Seedream v5 pro layerize는 **오려낸다.** 실호출로 확인한 결과(`docs/notes/seedream-layerize-trial-response.json`):

- 호출 1회에 투명 PNG 여러 장 + `name`·`description`·`z_index`·`bounding_box`.
- 합성 결과가 원본과 평균 픽셀차 **6.8/255**, 커버리지 1.0 — 사실상 원본 복원.
- 프롬프트에 영어로 쓴 이름 그대로 나뉜다. **이름을 안 쓴 요소는 배경에 남는다**(왼쪽 가족이 그렇게 남았다).
- 비용 레이어당 $0.03375(1536×1536 픽셀 이하). 씬당 5장이면 $0.169로, 현행 fal edit 방식 $0.45의 3분의 1.

다시 그리지 않으므로 원위치 문제가 원천적으로 없다 — 지금의 방어 장치 전부가 불필요해진다.

## API 실측

`POST https://fal.run/bytedance/seedream/v5/pro/layerize`, 헤더는 기존 fal 호출과 동일(`Authorization: Key {FAL_KEY}`).

입력: `image_url`(**data URI 허용 — 실호출로 확인**), `prompt`, `image_size`(`auto` 기본), `sync_mode`, `enable_safety_checker`, `enhance_prompt_mode`.

출력:

```json
{"images": [...],
 "layers": [{"image": {"url": "...", "file_size": 1564022, "width": null, "height": null},
             "z_index": 0, "bounding_box": null, "name": null, "description": null},
            {"image": {...}, "z_index": 3,
             "bounding_box": {"absolute": [344, 500, 1254, 912], "normalized": [...]},
             "name": "white electric car",
             "description": "White electric sedan, only extract the car body, ..."}]}
```

실측에서 확인한 세 가지 함정:

1. **`width`/`height` 가 `null` 로 온다.** 내려받은 PNG를 직접 열어 크기를 재야 한다.
2. **레이어 PNG 크기가 bbox 크기와 다르다.** 배율이 레이어마다 제각각이다(트라이얼: 충전기 3.4배, 차 1.16배, 사람 2.17배, 케이블 2.8배, 배경판 1.0배). 비율은 유지되므로 균등 스케일로 맞출 수 있다.
3. **`z_index 0` 은 특별하다** — `name`·`bounding_box` 가 `null`, RGB 전체 캔버스, 그리고 **요소가 지워진 자리가 인페인팅된 완전한 배경판**이다.

## 설계

### 1. 호출

`backend/fal_api.py` 에 추가한다.

```
layerize(image_path: Path, names: list, *, timeout=600) -> dict
```

프롬프트는 분석이 낸 **영어 이름(`name_en`)만** 나열한다. **`background` 는 절대 쓰지 않는다** — 쓰면 구멍 뚫린 배경 요소 레이어(z1)가 한 장 더 오고, 그건 z0과 내용이 겹치는 데다 하늘·도로가 비어 있어 쓸 수 없으며, 레이어 한 장 값이 더 든다.

`edit_image` 와 같은 실패 규약: 키 없음·비200·타임아웃·레이어 없음은 `FalError`.

### 2. 저장

`z_index` 오름차순으로 처리한다.

| 응답 | 저장 경로 |
|---|---|
| `z_index 0`(이름·bbox 없음) | `layers/{sid}__bg.png` |
| 이름 있는 레이어 | `layers/{sid}__{i}_{슬러그}[_char].png` |

둘 다 **기존 파일명 규칙 그대로**다. 그래서 매니페스트의 배경 판별(`__bg`), 낱개 삭제·재생성, 패널 썸네일이 손대지 않아도 동작한다. `i` 는 요청한 이름 목록에서의 순번, `_char` 접미사는 분석이 준 `kind == "character"` 일 때 붙인다(모션 규칙이 이 접미사를 본다).

요청 목록에 없는 이름이 오면 버리지 않고 저장하되 결과에 `unexpected` 로 표시한다.

### 3. 위치 — 요소 사이드카에 bbox

크롭돼 오므로 위치를 따로 보관해야 한다. **이미 있는 `layers/{sid}__elements.json`** 에 두 필드를 더한다(새 파일을 만들지 않는다).

```json
{"layer": "ab__0_white_electric_car", "index": 0, "name": "차량",
 "name_en": "white electric car", "kind": "object", "intent": "...",
 "bbox": [344, 500, 1254, 912], "z": 3}
```

`z` 는 모델이 준 `z_index` 다. 지금은 분석 결과의 나열 순서를 앞뒤로 쓰는데, 모델이 실제 겹침 순서를 알려주므로 그것을 쓴다.

### 4. 배치 — 매니페스트가 좌표를 계산

`manifest._scene_layers` 가 사이드카를 읽어 레이어 항목에 두 값을 더한다.

- `position` = bbox 중심 `[(l+r)/2, (t+b)/2]`
- `scale` = `(r-l) / PNG폭 × 100`

`build_scene.jsx` 의 `addLayerObj` 에는 이미 `layer.position` + `layer.scale` 분기가 있다. 값을 주면 그 경로를 타고, **bbox가 없으면 지금처럼 풀프레임 1:1** 로 간다. 기존 프로젝트가 그대로 돈다.

까딱 모션 피벗(`foot`)도 바뀐다. 지금은 알파 bbox를 추정하는데, bbox가 있으면 **하단 중앙**을 쓴다 — 더 정확하고 계산도 없다.

레이어 순서는 사이드카의 `z` 오름차순으로 정렬해 매니페스트에 싣는다(배경이 맨 앞 = AE 최하단).

### 5. 제거

layerize는 오려내므로 다시 그리기용 방어 장치가 전부 불필요하다. 아래를 지운다.

`pick_key_color` · `color_coverage` · `scene_key_color` · `chroma_key` · `chroma_key_magenta` · `_key_distance` · `KEY_COLORS`/`KEY_HEX`/`KEY_LABEL`/`_COVER_DIST` · `{sid}__keycolor.json` · `position_score` · `_qc_feedback` · `_gen_element_once` · `generate_element_layer` · `generate_background_layer` · `build_element_layer_prompt` · `_run_fal_image` · `flatten_colors` · `_aspect_mismatch` · `normalize_layer_size` · `_alpha_foot`(bbox로 대체).

`split_scene_to_elements` 는 시그니처를 유지하되 내부가 layerize 호출로 바뀐다 — 라우터·비서·테스트가 그대로 부른다.

**되돌리기 어려운 삭제다.** layerize가 실제 프로젝트에서 기대에 못 미치면 복구는 git 되돌리기다. 두 경로를 유지하는 비용이 더 크다고 판단해 일원화한다.

### 6. 낱개 재생성의 의미 변화

layerize는 씬 단위 호출이라 **레이어 한 장만 다시 뽑을 수 없다.** `regenerate_layer` 는 "그 씬을 다시 분리"가 되고 비용도 씬 전체다. 패널의 ↻ 버튼 툴팁을 "이 씬을 다시 분리합니다(레이어 전체가 새로 만들어집니다)"로 바꾼다.

낱개 **삭제**는 그대로 유효하다 — 파일을 `_prev` 로 치우고 사이드카에서 빼면 된다. 다만 삭제 후 배경 재생성은 **씬 재분리**가 되므로, 삭제 확인 문구도 그에 맞게 고친다.

### 7. 예산

`MAX_ELEMENTS = 4` 는 그대로다. 프롬프트에 이름을 4개까지만 쓰고 배경판이 1장 더해져 씬당 5레이어, $0.169. 모델이 이름 외의 것을 쪼개 6장 이상 오면 요금은 그만큼 나가지만 우리는 채택분만 쓴다(`unexpected` 로 기록해 사람이 볼 수 있게 한다).

## 파일

| 파일 | 변경 |
|---|---|
| `backend/fal_api.py` | `layerize()` 추가 |
| `backend/imagegen.py` | `split_scene_to_elements` 를 layerize 기반으로 재작성, 위 목록 제거, 사이드카에 bbox·z 저장 |
| `backend/manifest.py` | 사이드카 bbox → `position`/`scale`/`foot`, `z` 순 정렬 |
| `cep/…/js/storyboard.js` | ↻·✕ 문구 수정 |
| 테스트 | 프롬프트·저장·사이드카·매니페스트 좌표·기존 프로젝트 폴백 |

## 테스트

fal 호출은 트라이얼 응답(`docs/notes/seedream-layerize-trial-response.json`)을 고정 픽스처로 써서 가짜로 대체한다.

- 프롬프트에 `name_en` 만 들어가고 `background` 가 없다.
- `z_index 0` 이 `{sid}__bg.png` 로, 이름 레이어가 `{sid}__{i}_{슬러그}` 로 저장된다. `kind == "character"` 면 `_char` 접미사가 붙는다.
- 사이드카에 `bbox`·`z` 가 남고 `load_element_specs` 로 다시 읽힌다.
- 매니페스트 좌표를 트라이얼 실측값으로 고정: 차 레이어 bbox `[344,500,1254,912]`, PNG 1052×477 → `position == [799, 706]`, `scale == 86.5`(소수 첫째 자리).
- `foot` 이 bbox 하단 중앙(`[799, 912]`)이다.
- bbox 없는 기존 레이어는 `position`·`scale` 없이 나가고 jsx 풀프레임 경로를 탄다.
- 요청 목록에 없는 이름은 `unexpected` 로 보고된다.
- `FAL_KEY` 없음·비200·레이어 0장이 `FalError`.

**실제 분리 품질과 AE 배치 정확도는 자동 검증할 수 없다.** `projects/tesla` 씬 5로 한 번 돌려 AE에서 원본과 겹쳐 확인해야 한다.

## 범위 밖

- `image_size` 를 `auto` 외의 값으로 조정하는 것(요금 구간이 바뀐다).
- 모델이 준 `description` 을 활용하는 것.
- v3 지도 임포트, 레이아웃 1~3단계(각각 별도 작업).
