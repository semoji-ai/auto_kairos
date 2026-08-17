# 레이어 패널 + 벡터라이징 — 포토샵식 목록과 SVG 내보내기

작성일: 2026-08-15
대상: `cep/com.autokairos.pd/js/storyboard.js`, `cep/com.autokairos.pd/index.html`,
`backend/imagegen.py`, `backend/manifest.py`, `backend/router.py`,
`backend/vectorize.py`(신규), `cep/com.autokairos.pd/jsx/build_scene.jsx`

## 목적

레이어를 나눈 뒤 씬별로 포토샵·일러스트레이터의 레이어 패널처럼 목록을 보며
눈을 켜고 끄고, 필요 없는 것을 프로젝트에서 빼고, 원하는 레이어를 벡터로
바꿀 수 있게 한다.

벡터화의 최종 목적은 **AE에서 확대해도 깨지지 않는 모션그래픽**이다. 이 문서의
모든 결정은 그 목적에 종속된다.

## 지금 상태

- 씬 행에 가로 썸네일 띠(`.lyr-strip`)가 있다 — `storyboard.js:220-290`의
  `renderRow`가 `s._layers`(`scenes.py:101`이 `layers/*{sid}*.png`를 글롭)를 매핑.
- 썸네일 hover 시 ✕(`.lyr-del`)·↻(`.lyr-regen`)가 뜬다(`index.html:100-107`).
- ✕는 `POST /api/layers/delete`(`router.py:594-615`) → `imagegen.delete_layer`
  (`imagegen.py:435-460`)가 PNG를 `layers/_prev/`로 옮기고 **배경 재생성 잡을 큐잉**한다.
- `manifest._scene_layers`(`manifest.py:35-83`)는 `_layers` 전부를 내보낸다 —
  포함/제외 기준이 없다.

## 결정 1 — 기존 ✕(배경 재생성)를 제거하고 🗑 제거로 대체한다

✕의 배경 재생성은 크로마 시절 설계다. 앞의 물체를 빼면 배경에 구멍이 나므로
메워야 했다.

**Seedream layerize는 z0을 완전히 인페인팅된 배경판으로 준다.** 요소 레이어를
빼도 구멍이 나지 않는다. 합성에서 빼면 그것으로 끝이다. 배경 재생성은 크레딧과
시간만 쓴다.

따라서 `.lyr-del`·`deleteLayer`·`POST /api/layers/delete`·`imagegen.delete_layer`를
없애고 아래의 제거 플래그로 대체한다. ↻(`regenLayer`, 씬 전체 재분리)는 남긴다.

## 결정 2 — 상태는 사이드카 플래그로, 파일은 움직이지 않는다

`layers/{sid}__elements.json`(`imagegen.py:372`, 스키마: `layer`·`index`·`name`·
`name_en`·`location`·`kind`·`intent`·`bbox`·`z`)에 두 필드를 더한다.

| 필드 | 뜻 | 기본(필드 없음) |
|---|---|---|
| `hidden` | 패널 미리보기에서 눈 끔 | `false` — 보임 |
| `removed` | 프로젝트에서 제거 | `false` — 살아 있음 |

**파일을 `_prev/`로 옮기지 않는다.** 복구가 플래그를 끄는 것으로 끝나고, 사이드카에
없는 레거시 레이어는 두 필드가 없으니 자동으로 "보임·살아있음"이 된다
(`load_element_specs`의 `_specs_from_filenames` 폴백 경로, `imagegen.py:385-410`).

두 상태의 효과는 다르다.

| | 패널 미리보기 | AE 내보내기 |
|---|---|---|
| `hidden` | 안 보임 | **들어감** |
| `removed` | 제거됨 구역에 흐리게 | 빠짐 |

`hidden`은 순수하게 눈으로 확인하기 위한 것이고 내보내기에 영향을 주지 않는다.

## 결정 3 — 씬 셀 미리보기를 레이어 합성으로 바꾼다

지금 씬 셀에는 스토리보드 원본 이미지가 뜬다. 눈을 꺼도 보이는 그림이 그대로면
토글이 무의미하다.

레이어가 있는 씬은 셀을 **합성 미리보기**로 바꾼다: 배경판을 깔고 그 위에 각
요소 PNG를 `bbox` 좌표로 CSS 절대배치한다. 눈을 끈 레이어는 그리지 않는다.

- 백엔드 호출이 없다. 브라우저가 이미 PNG를 갖고 있다.
- 좌표계: `bbox`는 배경판 픽셀 기준이다. 셀 폭에 맞춰 `bbox`를 비율로 환산한다
  (`left = l/plateW*100%` 형태). 배경판 실제 크기는 이미지의 `naturalWidth`로 읽는다.
- `bbox`가 없는 레거시 레이어는 풀프레임으로 겹친다(`manifest._alpha_foot` 폴백과
  같은 취급).
- 레이어가 없는 씬은 지금처럼 스토리보드 이미지를 쓴다.

기존 `toggleLayerOverlay`(`storyboard.js:402-419`, 썸네일 클릭 시 빨간 윤곽 오버레이)는
합성 미리보기가 그 역할을 대신하므로 없앤다.

## 결정 4 — 목록 UI

가로 썸네일 띠를 세로 목록으로 펼친다. **기본은 접힌 상태**(지금의 썸네일 띠)로
두어 씬이 100개를 넘는 시트에서 무거워지지 않게 한다.

```
▾ 레이어 5                    [전체 벡터화] [선택 벡터화]
  ☐ 👁  [썸] 노란옷 아이   인물  SVG   🗑
  ☐ 👁  [썸] 흰색 전기차   사물         🗑
  ☐ 🚫  [썸] 충전 케이블   사물         🗑
  ☐ 👁  [썸] 배경판        배경   SVG
  ─ 제거됨 ──────────────────────
       [썸] 간판                  ↩ 복구
```

- 체크박스는 **벡터화 선택 전용**이며 👁 과 무관하다.
- 배경판(`is_background_layer`, `imagegen.py:432`)에는 🗑 이 없다 — 빠지면 합성이
  성립하지 않는다.
- 정렬은 `z` 오름차순, 배경판이 맨 위(AE의 최하단). `manifest._scene_layers`의
  정렬과 같은 기준이다.
- `SVG` 배지는 `layers/{stem}.svg` 파일이 있을 때 붙는다.
- 제거된 레이어는 아래 별도 구역에 흐리게 남고 `↩ 복구`로 되돌린다.
- 패널은 순수 ES5다(`var`/`function`만, 번들러 없음). 화살표 함수·`let`·`const`·
  템플릿 리터럴을 쓰지 않는다. 기존 hover 오버레이 패턴(`index.html:100-107`)과
  `.mini`·`.ra` 버튼 클래스를 따른다.

## 결정 5 — 벡터화

Recraft로 PNG를 SVG로 바꾼다. **버튼을 누를 때만** 돈다 — 레이어 분리 직후 자동
실행하지 않는다. 지울 레이어에 크레딧을 쓰지 않기 위해서다.

### API 계약

`kairos-ai/netlify/functions/generateRecraftVectorize.js`에서 확인한 계약이다.

```
POST https://external.api.recraft.ai/v1/images/vectorize
Authorization: Bearer <RECRAFT_API_KEY>
multipart/form-data: file=<이미지>, response_format=url
응답: {"image": {"url": ...}} 또는 {"url": ...}
```

**결과 URL 다운로드에 브라우저 User-Agent가 반드시 필요하다.** 없으면 HTTP 403이
난다. 실측으로 확인했다.

비용은 이미지당 1크레딧, 소요는 장당 약 10초.

### 신규 모듈 `backend/vectorize.py`

`fal_api.py`와 같은 방식으로 stdlib `urllib`만 쓴다. 새 의존성을 넣지 않는다.
multipart 본문은 직접 조립한다.

- `api_key()` — `env.get_key("RECRAFT_API_KEY")`
- `vectorize_png(png_path) -> bytes` — SVG 바이트 반환, 실패 시 `VectorizeError`
- 키 값은 로그·예외 메시지에 절대 넣지 않는다.

### 엔드포인트

`POST /api/layers/vectorize` — 본문 `{"scene": <n>, "layers": ["stem", ...]}`.
`router.py`의 `_dispatch` 안에 기존 잡 패턴(`router.py:535-557`)을 따라 추가하고
비동기 잡으로 돌린다.

- **한 장이 실패해도 나머지를 계속 처리한다.** 잡 결과에 `{ok: [...], failed:
  [{layer, error}, ...]}`를 담아 실패한 것만 목록에 ⚠ 로 표시하고 개별 재시도를
  허용한다.
- 이미 `{stem}.svg`가 있으면 건너뛴다(결과의 `skipped`에 담는다). 재벡터화는
  개별 버튼으로만 한다 — 전체 버튼을 다시 눌렀다고 크레딧을 또 쓰지 않는다.
- 저장 위치는 PNG 옆 `layers/{stem}.svg`.
- `removed` 레이어는 요청에 들어와도 처리하지 않는다.

## 결정 6 — 내보내기

### 매니페스트

`manifest._scene_layers`(`manifest.py:35-83`)가 두 가지를 더 한다.

1. **`removed`인 레이어를 거른다.** `hidden`은 무시한다.
2. **`layers/{stem}.svg`가 있으면 `path`를 그 SVG로**, 없으면 지금처럼 PNG로 한다.
   엔트리에 `vector: true`를 함께 넣어 jsx가 판단할 수 있게 한다.

`position`·`scale`·`foot` 계산은 바꾸지 않는다. Recraft SVG는 `width`/`height`
속성이 원본 PNG 크기와 정확히 같기 때문이다(실측: 968×440, 427×852, 1536×1024).
`viewBox`만 긴 변 2048로 정규화되며 비율은 보존된다.

### jsx

`build_scene.jsx`가 레이어를 얹을 때 **엔트리의 `vector`가 참이면
`layer.collapseTransformation = true`**로 연속 래스터화를 켠다.

이것이 이 작업의 핵심이다. AE는 SVG를 넣어도 기본값으로는 100% 크기에서 한 번만
래스터화한다. 그 상태로 확대하면 PNG와 똑같이 깨진다. 연속 래스터화를 켜야 배율마다
벡터에서 다시 그린다.

**알려진 부작용:** 연속 래스터화를 켠 레이어는 블렌딩 모드와 일부 이펙트가 무시된다.
레이어 분리 결과물은 Normal로 얹으므로 현재 모션에는 영향이 없다.

## 오류 처리

| 상황 | 처리 |
|---|---|
| `RECRAFT_API_KEY` 없음 | 잡을 시작하지 않고 "키 없음"으로 즉시 실패. 크레딧 소모 없음. |
| 벡터화 1장 실패 | 그 레이어만 `failed`에 담고 나머지 계속. |
| 결과 URL 403 | User-Agent를 붙여 재시도하지 않는다 — 처음부터 붙인다. |
| 사이드카 없는 레거시 씬 | 파일명 폴백 스펙에 플래그를 얹어 사이드카를 새로 쓴다. |
| 배경판에 제거 요청 | 거부한다(UI에 버튼이 없고 백엔드도 막는다). |
| SVG는 있는데 PNG가 없음 | SVG를 쓴다. 썸네일은 SVG를 그대로 `<img>`로 띄운다. |

## 테스트

pytest로 검증한다.

- `_scene_layers`: `removed` 레이어가 빠진다. `hidden` 레이어는 남는다.
- `_scene_layers`: `{stem}.svg`가 있으면 `path`가 SVG이고 `vector`가 참, 없으면
  PNG이고 `vector`가 없다.
- 사이드카 플래그 왕복: 숨김·제거·복구가 `{sid}__elements.json`에 남고 다시 읽힌다.
- 사이드카가 없는 레거시 레이어에 제거를 걸면 사이드카가 새로 생기고 나머지
  레이어는 영향이 없다.
- 벡터화 부분 실패: 3장 중 2번째가 실패해도 1·3번 SVG가 저장되고 결과에
  `ok` 2건·`failed` 1건이 담긴다(Recraft 호출은 가짜로 대체).
- 이미 `.svg`가 있는 레이어는 `skipped`에 담기고 API를 호출하지 않는다.
- 배경판 제거 요청이 거부된다.

**자동 검증이 안 되는 것:** 합성 미리보기의 시각적 정확성, AE의 SVG 임포트 결과
(이 맥에 After Effects가 설치돼 있지 않다 — 테스터 PC에서 확인해야 한다). 특히
그러데이션 렌더와 연속 래스터화의 확대 품질은 사람이 봐야 한다.

SVG 구조는 AE 임포터에 유리한 편이다. 실측 결과 `path`와 단순 `linearGradient`
뿐이고 `clipPath`·`mask`·`filter`·`<style>`·텍스트·`gradientTransform`이 하나도
없다 — AE 임포터가 어긋나는 대표 요인들이 모두 부재한다.

## 범위 밖

- 레이어 순서(z) 바꾸기, 이름 바꾸기, 그룹 묶기.
- 레이어 불투명도·블렌딩 모드를 패널에서 설정하는 것.
- SVG를 AE 셰이프 레이어로 변환하는 것(Create Shapes from Vector Layer).
- 벡터화 결과를 사람이 손보는 편집기.
