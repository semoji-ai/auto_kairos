# 레이어 분리를 fal(grok-imagine-image edit)로 — 5레이어 예산 + 키 컬러 자동 선택

작성일: 2026-08-13
대상: `auto_kairos_adobe` 백엔드(imagegen) + 프로덕션 시트 레이어 모달

## 배경

레이어 분리는 지금 codex `$imagegen` 으로 요소마다 이미지를 다시 그려 뽑는다. 분리 품질을 올리기 위해 이 경로만 fal의 `xai/grok-imagine-image/v2.0/edit` 로 바꾼다. 동시에 두 가지를 정한다 — 레이어 개수 상한(요소 4 + 배경 1)과, 씬마다 마젠타/그린 중 알맞은 키 컬러 선택.

**규칙 예외**: 프로젝트 `CLAUDE.md` 는 외부 이미지 API 직접 호출을 금지한다(adobe 파이프라인 포함). 이번 변경은 그 규칙의 명시적 예외이며, `CLAUDE.md` 에 예외를 한 줄 기재한다. 씬 이미지·캐릭터 생성은 codex 경로를 그대로 쓴다.

## 1. 레이어 예산 — 요소 4 + 배경 1

`analyze_scene_layers` 가 반환하는 요소를 기존 우선순위(캐릭터 → 캐릭터를 가리는 전경 → 내용상 필요한 소품)대로 정렬해 **앞 4개만** 채택한다. 배경은 항상 1장이므로 씬당 최대 5레이어.

- 잘린 요소는 버리지 않고 `dropped: [...]` 로 함께 반환한다.
- 패널 모달은 `dropped` 를 회색 "예산 초과로 제외"로 표시하고, 체크는 4개까지만 허용한다. 제외된 것을 쓰려면 다른 하나를 끄면 된다.
- 배경 프롬프트의 제거 목록에는 **채택된 요소만** 넣는다. 잘린 요소는 배경에 남아야 한다.

상한은 `MAX_ELEMENTS = 4` 상수로 둔다.

## 2. fal 어댑터 — `backend/fal_api.py` (신규)

`tts.py` 의 ElevenLabs 호출과 같이 **stdlib `urllib` 만** 쓴다(새 의존성 없음).

```
edit_image(prompt: str, image_paths: list[Path], *,
           output_format="png", resolution="2k", timeout=180) -> bytes
```

- `POST https://fal.run/xai/grok-imagine-image/v2.0/edit`
- 헤더: `Authorization: Key {FAL_KEY}`, `Content-Type: application/json`
- 본문: `{prompt, image_urls, output_format, resolution, num_images: 1}`
- `image_urls` 는 로컬 파일을 base64 **data URI** 로 인라인한다. 모델이 최대 3장까지 받으므로 3장을 넘기면 앞 3장만 보낸다.
- data URI가 거부되면 fal 스토리지 업로드로 폴백한다(구현 시 문서 확인 — 설계 시점에 문서 접근이 429로 막혔다).
- 응답 `images[0].url` 을 내려받아 바이트로 반환한다.
- `FAL_KEY` 없음 / 비200 / 타임아웃은 예외를 던진다. 상위 잡이 실패로 표면화한다(조용한 폴백 없음).

키는 `env.get_key("FAL_KEY")` 로 읽는다(기존 키 조회 경로와 동일).

## 3. imagegen 연결

`_run_codex_image` 와 **같은 시그니처**의 `_run_fal_image(proj_dir, out, prompt, images=None, post=None)` 를 둔다. 반환도 `{"status": "completed"|"failed", "path": ...}` 로 맞춘다.

`generate_element_layer` / `generate_background_layer` 는 호출 대상만 `_run_fal_image` 로 바꾼다. QC(투명 비율·위치 점수), 1회 재시도, `_prev` 정리, 크기 정규화는 그대로 재사용한다.

`generate_one`(씬 이미지)·`generate_character` 는 codex 경로 그대로 둔다.

## 4. 키 컬러 자동 선택

```
pick_key_color(scene_image) -> {"key": "magenta"|"green", "rgb": [r,g,b], "coverage": {"magenta": f, "green": f}}
```

이미지를 작게 줄이고 후보 색(마젠타 `#FF00FF`, 그린 `#00FF00`) 각각에 대해 **그 색 근처인 픽셀 비율**(정규화 거리 < 0.25)을 잰다. 비율이 낮은 쪽을 쓴다. 동률이면 마젠타(기존 기본값).

씬당 한 번 계산해 `layers/{sid}__keycolor.json` 에 저장한다. **요소·배경·낱개 재생성이 같은 색을 써야** 하기 때문이다 — 요소를 그린으로 뽑고 재생성만 마젠타로 하면 키잉이 어긋난다. 파일이 있으면 재계산하지 않는다.

`chroma_key_magenta(src, out)` 를 `chroma_key(src, out, key="magenta")` 로 일반화하고 그린 수식을 추가한다. 임계값(0.18/0.22)과 가장자리 수축·페더는 두 색이 공유한다. 기존 이름은 얇은 별칭으로 남겨 호출부와 테스트를 깨지 않는다.

`build_element_layer_prompt` 와 배경 프롬프트의 "요소 외 전 영역을 마젠타로" 문구는 선택된 색 이름과 HEX로 치환한다.

## 5. 설정·문서

- `.env.example` 에 `FAL_KEY=` 추가.
- `CLAUDE.md` 에 예외 한 줄: 레이어 분리는 fal `xai/grok-imagine-image/v2.0/edit` 사용, 그 외 이미지 생성은 codex `$imagegen` 전용.
- 엔진 전환 UI는 만들지 않는다(YAGNI).

## 파일

| 파일 | 변경 |
|---|---|
| `backend/fal_api.py` | 신규 — fal edit 호출, data URI 인라인, 결과 다운로드 |
| `backend/imagegen.py` | `_run_fal_image`, `pick_key_color`, `chroma_key` 일반화, 요소 4개 상한, 프롬프트 키 컬러 반영 |
| `cep/…/js/storyboard.js` | 모달에 `dropped` 표시 + 체크 4개 상한 |
| `.env.example`, `CLAUDE.md` | 키·예외 기재 |

## 테스트

- fal 어댑터: `urlopen` 을 가짜로 바꿔 URL·헤더·본문(`image_urls` 가 data URI인지, 3장 초과 시 잘리는지)·응답 파싱을 검증. 키 없음/비200/타임아웃이 예외인지.
- 키 컬러: 마젠타가 넓은 이미지 → `green`, 초록이 넓은 이미지 → `magenta`, 둘 다 없으면 `magenta`. 사이드카가 있으면 재계산하지 않는지.
- `chroma_key` 그린 경로가 마젠타와 같은 기준으로 알파를 만드는지.
- 예산: 요소 6개 → 채택 4 + `dropped` 2, 배경 프롬프트에 채택 4개 이름만.
- 패널 구조: 모달에 `dropped` 표시와 4개 상한이 있는지.

**fal 호출 결과의 실제 분리 품질은 자동 검증할 수 없다** — `FAL_KEY` 를 넣고 씬 하나로 사람이 확인해야 한다.

## 범위 밖

- codex/fal 엔진 전환 UI.
- 씬 이미지·캐릭터 생성 경로 변경.
- 키 컬러 후보를 마젠타·그린 외로 늘리는 것.
