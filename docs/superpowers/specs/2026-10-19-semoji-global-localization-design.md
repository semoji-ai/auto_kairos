# 세모지 글로벌화(현지화) 파이프라인 설계

작성일: 2026-10-19 · 작업 폴더: `~/Projects/semoji_global` · 첫 테스트 편: C086 한국신선원료인증(프레쉬서트), 5:45, 29.97fps

## 1. 목표와 합의 사항

| 항목 | 결정 |
|---|---|
| 공개 형태 | 별도 글로벌 채널에 새 영상으로 업로드 (첫 언어 영어, 이후 일본어·중국어 등) |
| 번역 수준 | 현지화 번역: 구성·문장 대응은 유지, 해외 시청자에게 필요한 맥락은 짧게 보충, 단위·관용구는 자연스럽게 |
| 화면 텍스트 | 한글 0자. AE 텍스트 레이어 + 이미지에 박힌 글자까지 교체 |
| 음성 | 세모지 보이스 `W7FnAxJNpD5WGjrF5GLp` (ElevenLabs, 다국어 모델 + `language_code`) |
| 타이밍 | **B안: 영어 내레이션 길이에 맞춰 영상 레이어를 다시 배치(타임 워프)** |
| 링크 복구 | NAS 일괄 복구는 하지 않음. 글로벌화할 편을 로컬로 가져올 때 그 편만 복구 |
| 재사용성 | 편마다 "언어 중립 마스터"를 한 번 만들고, 언어 추가는 번역 파일 + 언어 프로필만 추가 |

성공 기준 (C086 영어판):
1. `render/en/C086_EN.mp4` 1920x1080 29.97fps, 화면 OCR 한글 0자.
2. 영어 내레이션이 장면과 맞음(구간 경계 오차 ±0.2초), 잘린 말·겹친 말 없음.
3. 영어 자막(번인) + `en.srt`.
4. 같은 마스터로 일본어판을 만들 때 코드 수정 없이 `l10n/ja.json` + `profiles/ja.json`만 추가하면 됨(설계 검증은 C086 영어판 완료 후 짧은 구간으로 확인).

## 2. 사전 조사에서 확인된 사실

- NAS `002_intra/001_세상의모든지식`: aep 3,484개(자동저장 제외), 에피소드 폴더 556개. NAS 한글 이름은 NFD — 경로는 항상 디스크 실제 이름으로 해석.
- aep 안의 footage 경로는 RIFX `alas` 청크의 JSON(`fullpath`, `ascendcount_base/target`). AE는 절대경로 → `//서버/공유/…`를 `/Volumes/공유/…`로 변환 → 상대경로 순으로 찾는다. 진단 스크립트 `scripts/aep_links.py`가 이를 재현(AE 결과와 일치 확인).
- 최종 aep 556편 중 269편에 실제 깨진 링크(대부분 옛 PC 경로 `D:\work\…`, `C:\work\001_유튜브\…`; 같은 파일이 NAS에 있음). 결과: `reports/relink_plan.json`.
- **AE 2026(이 맥)은 SMB 공유의 한글 폴더 안 PNG를 읽지 못한다**(“File exists but couldn't be open for reading”). 로컬 디스크·한글 파일명·ASCII 폴더는 정상. → 모든 작업은 로컬 사본(NFC 정규화)에서.
- AE 운용: JSX 객체 키 `in/out`은 따옴표 필수, 오토카이로스 `json2.jsx`는 parse 전용(직렬화는 `scripts/ae/lib.jsx`의 `S()`), 화면보호기가 켜지면 AE 대화상자를 못 닫음 → 작업 중 `caffeinate -d -u`.
- C086 구조: `Final` 컴프(레이어 539, 텍스트 44), `#자막` 컴프(말자막 텍스트 150), 폰트 SBAggroM 위주, footage 697·누락 0. 씬 TTS가 `tts_<씬id>_*.mp3`로 Final에 개별 배치(오토카이로스 AE 파이프라인 산출).
- 화면 한글 유형: (a) AE 텍스트 레이어, (b) 이미지 속 글자(원재료명 라벨, 갈비탕·육개장 포장, 드럼 라벨 등), (c) 한국 전용 내용(마지막 댓글 이벤트·제품 증정).
- 로컬 디스크 여유 15GB(228GB 중). 편당 로컬 사본 + 렌더로 2~5GB 필요 → 편 작업 끝나면 로컬 사본 정리.

## 3. 구조

```
~/Projects/semoji_global/
  scripts/
    aep_links.py            aep 링크 진단 (AE 불필요)
    build_relink_jobs.py    링크 복구 매핑 생성
    ingest.py               NAS → 로컬 복사(NFC) + 링크 진단·복구 job
    extract.py              인벤토리 → master/source.json
    tts.py                  언어별 TTS + 타임스탬프 (세모지 보이스)
    timewarp.py             구간별 원래 길이/새 길이 → warp.json (시간 변환표)
    subtitles.py            언어별 자막 분할 + srt
    qa.py                   OCR 한글 잔존, ASR 대조, 길이, 콘택트시트
    ae/ lib.jsx run.sh render.sh relink.jsx inventory_full.jsx localize.jsx
  glossary/<lang>.json      시리즈 공통 용어집
  profiles/<lang>.json      폰트 매핑, 자막 규칙, TTS 모델·속도 범위, 글자수/초 기준
  episodes/<EP>/
    src/                    로컬 사본 (편집 원본, 수정 금지)
    inventory.json
    master/source.json      언어 중립 마스터
    master/raster/          이미지 텍스트 교체 대상 원본
    l10n/<lang>.json        번역 (마스터 ID 기준)
    tts/<lang>/             구간 음성 + align
    raster/<lang>/          언어별 교체 이미지
    build/<lang>/<EP>_<LANG>.aep
    render/<lang>/<EP>_<LANG>.mp4, <lang>.srt, qa/
```

## 4. 언어 중립 마스터 (`master/source.json`)

```json
{
  "episode": "C086", "aep": "src/한국신선원료인증 수정3.aep",
  "main_comp": "Final", "work_area": [0, 345.14], "fps": 29.97,
  "segments": [
    {"id": "n001", "in": 0.53, "out": 4.21, "audio_layer": "tts_0f1e37e2_…mp3",
     "ko": "마트에서 제품을 슬쩍 뒤집어 보신 적 있으시죠.", "scene": "0f1e37e2"}
  ],
  "strings": [
    {"id": "t017", "comp": "Final", "comp_id": 123, "layer": 88, "ko": "12종",
     "font": "SBAggroM", "size": 220, "box": [w, h], "visible": [[30.1, 34.6]]}
  ],
  "raster": [
    {"id": "r004", "file": "src/(Footage)/…/s05.png", "ko_text": "원재료명 …", "action": "edit|keep|cut"}
  ],
  "cuts": [{"in": 330.2, "out": 345.14, "reason": "한국 전용 댓글 이벤트"}],
  "subtitle_comp": "#자막"
}
```

- 구간(segments): Final의 TTS 오디오 레이어 = 내레이션 구간. 한글 문장은 같은 시간대의 `#자막` 레이어 텍스트를 이어붙여 얻고, 원고 docx와 대조.
- 문자열 ID는 `comp_id:layer` 기반으로 고정. 같은 문자열이 여러 곳이면 각각 ID(번역은 공유 가능).
- 이미지 텍스트 탐지: 렌더 mp4 프레임 OCR(macOS Vision) → 한글 영역이 있는 시각 → 그 시각에 보이는 footage 레이어(probe) → raster 목록. 사람 검수로 `action` 확정.
- 한국 전용 내용은 `cuts`로 표시(기본: 잘라냄. 필요하면 언어별 대체 아웃트로를 l10n에서 지정).

## 5. 번역 (`l10n/<lang>.json`)

```json
{
  "lang": "en",
  "segments": {"n001": {"text": "Ever flipped a product over at the store?", "tts": null}},
  "strings":  {"t017": {"text": "12 products", "font": null}},
  "raster":   {"r004": {"prompt_text": "Ingredients: …"}},
  "outro": null
}
```

- 번역은 Claude가 수행: 용어집 + 구간 맥락(앞뒤 구간, 화면 문자열)을 함께 주고 현지화 번역.
- 길이 예산: 원래 구간 길이 × 언어별 `chars_per_sec`(profile) 기준 **±25% 안**을 목표(타임 워프가 흡수하는 범위를 넘지 않게). 넘으면 다시 씀.
- 화면 문자열: 원래 박스 폭 안에 들어가게 짧게. 넘치면 patch 단계에서 글자 크기 자동 축소(최소 70%).
- `tts` 필드: 발음 교정용 별도 표기(숫자·약어·브랜드명), 없으면 `text` 사용.
- 산출물: 검수용 대조표 `l10n/<lang>_review.md`(한글/번역/길이 예산/실측 길이).

## 6. 음성 (`tts.py`)

- 세모지 보이스, `profiles/<lang>.json`의 모델(기본 `eleven_v3`; 결과 비교 후 `eleven_multilingual_v2`도 가능) + `language_code`. `/with-timestamps`로 글자 단위 정렬 저장.
- 구간당 1파일(`tts/en/n001.mp3`, `n001.align.json`), 앞뒤 무음 트림.
- ASR(Whisper) 대조로 누락·오독 검출 → 해당 구간 재생성.
- 키는 오토카이로스 `.env`의 ElevenLabs 키 사용(코드는 brand_cn_expo `gen_tts.py` 범용화).

## 7. 타임 워프 (B안 핵심)

### 7.1 시간 변환표
- 원래 타임라인을 앵커로 나눈다: 앵커 = 각 구간의 `in`, `out`, 컷 경계, 작업영역 시작/끝.
- 구간 i의 새 길이 = 영어 음성 길이 + 원래의 앞뒤 여백(구간 사이 무음은 원래 길이 유지, 단 최소 0.15초).
- 앵커 사이는 선형 보간 → 단조 증가하는 구간별 선형 함수 `T(t)`. 컷 구간은 길이 0으로 접음.
- `timewarp.py` → `build/<lang>/warp.json` = `[[old_t, new_t], …]` + 구간별 비율. 비율이 0.6~1.6을 벗어나면 경고(번역 길이 재조정 권고).

### 7.2 AE 적용 (`localize.jsx`, Final부터 재귀)
레이어 유형별 규칙:

| 레이어 | 규칙 |
|---|---|
| 모든 레이어 | `inPoint`·`outPoint`를 T로 변환. 모든 속성 키프레임 시간을 T로 변환(값·보간·이즈 복사 후 재생성) |
| 정지 이미지·솔리드·셰이프·텍스트 | 위치만 이동, 길이는 변환된 in/out 그대로 |
| 영상 footage(mp4/mov) | 새 길이/원래 길이 = r. 0.8≤r≤1.25면 stretch로 속도 조정, r>1.25면 원속도 재생 후 마지막 프레임 정지(time remap), r<0.8이면 속도 0.8 + 뒤를 자름 |
| 프리컴프 레이어 | 프리컴프가 이 위치에서만 쓰이면 **내부 레이어에도 같은 T(로컬 시간으로 이동)를 재귀 적용**하고 컴프 길이 조정. 여러 곳에서 쓰이면 복제 후 각각 적용. 내부에 타이밍 의미가 없는 짧은 연출 프리컴프(구간 하나 안에 들어가는 것)는 stretch로 처리 |
| 내레이션 TTS 오디오 | 삭제 후 영어 구간 음성을 `T(in)`에 배치 |
| 효과음 | 시작 시각만 T로 이동(길이·속도 유지) |
| BGM | 시작은 T로 이동, 끝은 새 작업영역 끝까지(필요하면 루프/페이드아웃) |
| time remap이 이미 켜진 레이어 | 리맵 키프레임 시간도 T로 변환(값은 유지) |
| 표현식 | 그대로 둠. `time` 기반 표현식은 목록으로 보고 |
| `#자막` 컴프 | 숨김(영어 자막은 새로 생성) |

- 컴프 길이·작업영역 = `T(원래 끝)`.
- 텍스트 교체: 문자열 ID로 소스텍스트(키프레임 포함) 교체 + 폰트 매핑 + 박스 넘침 시 축소.
- 이미지 교체: `raster/<lang>/` 파일로 footage replace.
- 저장: `build/<lang>/<EP>_<LANG>.aep` (src는 수정하지 않음).

### 7.3 자막
- 영어 정렬 결과로 단어 단위 분할(profile: 한 줄 최대 42자, 1~2줄, 최소 노출 0.8초).
- 새 자막 컴프를 원래 세모지 자막 스타일(흰 박스 + 네이비 글자, 하단)로 생성 — 오토카이로스 `subtitle_layers.jsx`/brand_cn `assemble.jsx` 스타일 재사용, 폰트는 profile.
- `render/<lang>/<lang>.srt`도 출력.

## 8. 이미지 텍스트 교체

- 대상: `raster` 중 `action=edit`.
- 방법: 코덱스 `$imagegen` 편집(공냥 규격 프롬프트, `check_prompt.mjs` 통과, 원본 크기 유지, generated_images에서 최신 PNG 회수). 글자만 바꾸고 그림은 유지하도록 지시. 결과는 원본과 나란히 비교 시트로 검수.
- 단순 라벨(단색 배경 위 글자)은 Pillow 패치가 더 정확하면 그쪽(brand_cn `make_zh_png.py` 방식) 사용.
- 실제 제품 패키지·로고 등 바꾸면 안 되는 것은 `keep`.
- 영상 클립(mp4) 안의 글자: 오토카이로스로 만든 모션그래픽이면 원본 스펙으로 재렌더, 아니면 해당 구간 위에 영어 오버레이 또는 `keep`.

## 9. 렌더와 검수

- `render.sh`(aerender, 화면 잠김에도 동작) → `render/<lang>/<EP>_<LANG>.mp4`.
- `qa.py`:
  - OCR(macOS Vision, 1초 간격)로 한글 잔존 0자 확인 → 위치·시각 보고
  - Whisper ASR 전사 vs 번역 대조
  - 구간 경계 확인: 장면 전환 시각(ffmpeg scdet) vs 앵커 변환 시각
  - 콘택트시트(5초 간격), 길이·fps·해상도
- 문제 구간만 수정 → 재빌드(같은 명령 반복).

## 10. 에피소드 가져오기 (`ingest.py`)

1. NAS 편 폴더 → `episodes/<EP>/src/` 복사(NFC 정규화, Auto-Save 제외, 디스크 여유 15GB 미만이면 중단).
2. `aep_links.py`로 로컬 aep 진단 → 깨진 링크는 NAS 인덱스로 후보 탐색 → 후보 파일도 로컬 `src/_relinked/`로 복사 → `relink.jsx`로 재연결해 `src/<이름>_relinked.aep` 저장.
3. `inventory_full.jsx` → `inventory.json`.

## 11. 실패 처리

- AE 대화상자 멈춤: run.sh에 감시(일정 시간 진행 없음 → 스크린샷 + 로그 남기고 중단). 스크립트는 전체를 try/catch로 감싸 오류를 로그 파일에 기록.
- 타임 워프 비율 범위 초과·표현식 경고·박스 넘침은 `build/<lang>/warnings.json`에 모아 보고.
- 모든 단계는 다시 실행해도 같은 결과(멱등). 단계별 산출물이 있으면 건너뛰고 `--force`로 재생성.

## 12. 열어둔 기본값 (테스트 중 확정)

- 마지막 댓글 이벤트 구간: 기본은 잘라냄(`cuts`). 영어 아웃트로가 필요하면 l10n `outro`로 추가.
- 영어 폰트: 먼저 SB 어그로의 영문 글리프로 렌더해 보고, 어색하면 비슷한 굵은 둥근 산세리프로 profile에서 매핑 변경.
- TTS 모델: eleven_v3 vs multilingual_v2 첫 구간 몇 개로 비교 후 profile 확정.

## 13. 범위 밖

- NAS aep 일괄 링크 복구(진단 도구와 매핑은 있음, 필요하면 별도 작업)
- 썸네일·제목·설명 현지화, 업로드 자동화
- 일본어·중국어 실제 제작(구조 검증만 C086 이후 짧게)
