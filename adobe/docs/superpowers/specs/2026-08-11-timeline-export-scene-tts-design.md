# 타임라인 내보내기 · 씬별 작업 버튼 · TTS/자막 텍스트 분리

작성일: 2026-08-11
대상: `auto_kairos_adobe` CEP 패널(After Effects) + 로컬 백엔드

## 문제

1. 패널에서 씬 컴프를 조립한 뒤 **AE 타임라인으로 내려놓는 수단이 없다.** 렌더 큐 추가만 가능.
2. TTS 생성 버튼이 시트 상단 일괄 도구상자에만 있어, 한 씬만 다시 만들려면 체크 → 버튼 왕복이 필요하다.
3. TTS 발음용 텍스트와 화면 자막 텍스트가 한 필드(`narration`)에 묶여 있다. 발음 교정을 하면 자막이 망가지고, 자막을 다듬으면 발음이 망가진다.

## 설계

### 1. 텍스트 3필드 분리

`scenes.json` 의 각 씬에 필드 3개를 둔다.

| 필드 | 용도 | 비었을 때 |
|---|---|---|
| `narration` | 원고. 진실 소스. 기존 시트 텍스트 영역 | — |
| `narration_tts` | TTS 발음용 | `tts._clean_text(narration)` 을 계산해 보여줌(저장하지 않음) |
| `subtitle_text` | 화면 자막용 | `narration` 사용 |

- `narration` 을 고쳐도 나머지 둘은 자동으로 덮어쓰지 않는다. 대신 "원고와 다름" 표시와 "원고에서 다시 채우기" 버튼을 준다. 손으로 다듬은 결과를 조용히 날리지 않기 위해서다.
- TTS를 생성할 때 실제로 합성에 보낸 텍스트를 `narration_tts` 에 확정 저장한다.
- 백엔드는 이미 `narration_tts` 를 우선 읽는다(`router.py`). 필드를 채우면 그대로 붙는다.

접근자는 `backend/scenes.py` 에 둔다.

```
tts_text(scene)      -> narration_tts 또는 _clean_text(narration)
subtitle_text(scene) -> subtitle_text 또는 narration
update_texts(proj_dir, scene_number, *, narration_tts=None, subtitle_text=None)
```

### 2. 자막 타이밍 매핑

ElevenLabs alignment는 **TTS 텍스트의 문자열** 기준이다. 화면에는 `subtitle_text` 를 띄워야 하므로 둘을 이어 붙인다.

1. 두 텍스트를 문장 단위로 쪼갠다(`.!?。` 경계).
2. 문장 개수가 같으면, 문장 i의 시간 구간을 alignment에서 얻고(첫 글자 start ~ 끝 글자 end), 그 구간 안에서 자막 문장의 줄들(기존 `split_lines`, 20자)을 글자수 비율로 나눈다.
3. 문장 개수가 다르면 씬 전체 구간을 자막 줄들의 글자수 비율로 나눈다(폴백).
4. 타임스탬프 자체가 없으면 기존 균등 분배 폴백을 그대로 쓴다.

두 텍스트가 같으면 문장 짝짓기가 1:1로 맞아떨어지므로 **현재 동작과 결과가 같다**(회귀 없음).

### 3. 타임라인 내보내기

**타이밍 기준**(사용자 확정): 씬 길이 = TTS 오디오 길이, 없으면 **5.0초**. 씬 시작점 = 앞 씬 길이의 누적합. 전체·개별 모두 같은 절대 시점을 쓰므로, 개별로 다시 내려도 제자리에 들어간다.

백엔드 `backend/timeline.py`:

```
build_plan(proj_dir, only_scene=None) -> {
  items: [{sceneNumber, comp, start, duration}], total
}
```

`comp` 는 매니페스트와 같은 규칙 `S{NN}_{sceneId}`. 라우터는 `POST /api/timeline/plan`.

ExtendScript `cep/com.autokairos.pd/jsx/place_on_timeline.jsx`:

```
akPlaceOnTimeline(planJson) -> "OK: ..." | "ERROR: ..."
```

- 대상 컴프 = AE 활성 컴프. 없으면 `Final` 컴프. 둘 다 없으면 에러.
- 대상 컴프가 계획 자신인 경우(활성 컴프가 배치하려는 씬 컴프)는 순환이므로 에러.
- 항목마다 프로젝트에서 컴프를 이름으로 찾아 `layers.add(comp)` → `startTime = start`, `inPoint = start`, `outPoint = start + duration`.
- 같은 이름의 레이어가 이미 대상 컴프에 있으면 지우고 다시 놓는다(중복 방지 = 멱등).
- 대상 컴프 길이가 모자라면 `duration` 을 늘린다.
- 컴프를 못 찾은 씬은 건너뛰고 결과 문자열에 씬 번호를 적는다.
- 전부 `beginUndoGroup` 한 덩어리 — 한 번의 Undo로 되돌아간다.

### 4. UI

**전체**: 우측 도구상자에 `⤓ 타임라인` 버튼.

**씬 행**(`col-work`): 아이콘 버튼 4개 — 체크박스와 무관하게 그 씬에 즉시 실행.

- `▣` 이미지 재생성
- `♪` TTS 재생성
- `✎` 텍스트 편집 → 행 아래 접이식 패널: **TTS 텍스트** / **자막 텍스트** textarea 2개 + `저장` + `저장 후 TTS 재생성`
- `⤓` 타임라인 내보내기(그 씬만)

상단 일괄 도구상자는 그대로 둔다(다중 씬용).

## 파일

| 파일 | 변경 |
|---|---|
| `backend/scenes.py` | 텍스트 접근자 3개, `update_texts` |
| `backend/subtitles.py` | 문장 짝짓기 매핑 |
| `backend/timeline.py` | 신규 — 배치 계획 |
| `backend/router.py` | `POST /api/timeline/plan`, `POST /api/scenes/texts` |
| `cep/…/jsx/place_on_timeline.jsx` | 신규 |
| `cep/…/js/storyboard.js` | 행 버튼, 텍스트 편집 패널, 내보내기 호출 |
| `cep/…/js/main.js` | 전체 타임라인 내보내기 |
| `cep/…/index.html` | 버튼·스타일 |

## 테스트

- `tests/test_timeline.py` — 오디오 있는/없는 씬 혼재 시 start 누적과 5초 기본값, `only_scene` 이 전체와 같은 start를 주는지.
- `tests/test_subtitles.py` 확장 — 자막 텍스트가 TTS 텍스트와 다를 때 줄 텍스트는 자막 쪽이고 타이밍은 alignment 범위 안에 있는지, 두 텍스트가 같을 때 기존 결과와 동일한지.
- `tests/test_scenes.py` 확장 — 접근자 폴백과 `update_texts` 저장.
- `tests/test_panel_structure.py` 확장 — 새 버튼 id와 jsx 함수 존재.

## 범위 밖

- v3의 `KoreanTTSPreprocessor`(숫자·영문 한글 읽기 변환) 포팅. 지금은 기존 `_clean_text` 로 초기값을 만들고 사람이 고친다.
- 자막 줄 나눔 규칙 변경. 기존 20자 어절 분할을 유지한다.
