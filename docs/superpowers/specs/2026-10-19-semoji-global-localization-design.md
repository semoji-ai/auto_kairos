# 세모지 글로벌화(현지화) 파이프라인 설계

작성일: 2026-10-19 (개정 2: 테스트 편을 코스트코로 변경) · 작업 폴더: `~/Projects/semoji_global`
첫 테스트 편: **브랜드백과 B209 코스트코** — 유튜브 `Vy2e0j_ny6g`(2025-05-09 업로드, 980초), 29.97fps 1080p

## 1. 목표와 합의 사항

| 항목 | 결정 |
|---|---|
| 공개 형태 | 별도 글로벌 채널에 새 영상으로 업로드 (첫 언어 영어, 이후 일본어·중국어 등) |
| 번역 수준 | 현지화 번역: 구성·문장 대응은 유지, 해외 시청자에게 필요한 맥락은 짧게 보충, 단위·관용구는 자연스럽게 |
| 화면 텍스트 | 한글 0자. AE 텍스트 레이어 + 이미지에 박힌 글자까지 교체 |
| 음성 | 세모지 보이스 `W7FnAxJNpD5WGjrF5GLp` (ElevenLabs, 다국어 모델 + `language_code`) |
| 타이밍 | **B안: 번역 내레이션 길이에 맞춰 영상·효과음·BGM을 다시 배치(타임 워프)** |
| 기준본 | **유튜브 업로드본**. 업로드 후 잘린 구간(코스트코: 마스터 914.3~923.3초, 9.0초)은 글로벌판에서도 뺀다 |
| 한국 전용 내용 | 댓글 이벤트·국내 한정 안내 등은 잘라낸다 |
| 링크 복구 | NAS 일괄 복구는 하지 않음. 글로벌화할 편만 로컬에서 복구하고, 이름으로 찾은 후보는 영상 대조로 확정 |
| 재사용성 | 편마다 "언어 중립 마스터"를 한 번 만들고, 언어 추가는 번역 파일 + 언어 프로필만 추가 |

성공 기준 (코스트코 영어판):
1. `episodes/B209/render/en/B209_EN.mp4` 1920x1080 29.97fps, 화면 OCR 한글 0자(글로벌 아웃트로 포함).
2. 영어 내레이션이 장면과 맞음(구간 경계 오차 ±0.2초), 잘린 말·겹친 말 없음. 효과음은 원래 장면에 붙어 있고, BGM 편집점이 장면 전환과 맞음.
3. 영어 자막(번인) + `en.srt`.
4. 같은 마스터로 일본어판을 만들 때 코드 수정 없이 `l10n/ja.json` + `profiles/ja.json`만 추가하면 됨(코스트코 영어판 완료 후 짧은 구간으로 확인).

## 2. 사전 조사에서 확인된 사실

### NAS·AE 일반
- NAS `002_intra/001_세상의모든지식`: aep 3,484개(자동저장 제외), 에피소드 폴더 556개. NAS 한글 이름은 NFD — 경로는 항상 디스크 실제 이름으로 해석.
- aep 안의 footage 경로는 RIFX `alas` 청크의 JSON(`fullpath`, `ascendcount_base/target`). AE는 절대경로 → `//서버/공유/…`를 `/Volumes/공유/…`로 변환 → 상대경로 순으로 찾는다. `scripts/aep_links.py`가 이를 재현(AE 결과와 일치 확인).
- 옛 PC 경로 대응: `D:\work\source\…` = NAS `001_shared_drive/1.Process/편집소스/source/…`. Epidemic Sound BGM(`C:\Users\…\Epidemic Sound\Music`) = NAS `001_shared_drive/2.edit_source/유투브용 무료음악/epidemic_sound/Music`.
- **같은 파일명·다른 내용이 흔하다**(세모지 트리에 `핀.ai` 10개, `63517.jpg` 1,295개) → 이름 매칭은 후보일 뿐, 렌더 후 기준본과 프레임 대조로 확정.
- **AE 2026(이 맥)은 SMB 공유의 한글 폴더 안 PNG를 읽지 못한다** → 로컬 사본(NFC 정규화)에서 작업.
- 폰트: 프로젝트는 SB 어그로 **TTF판** PS이름(`SBAggroM/L`)을 쓰는데 이 맥엔 **OTF판**(`OTSBAggroM/L`)만 있다 → 로컬 사본에서 일괄 매핑. 학교안심 알림장 TTF·긱블말랑이·배민 연성은 NAS에서 찾아 `~/Library/Fonts`에 설치함.
- AE 운용: JSX 객체 키 `in/out`은 따옴표 필수, 오토카이로스 `json2.jsx`는 parse 전용(직렬화는 `scripts/ae/lib.jsx`의 `S()`), `$.fileName`은 evalFile한 파일 기준이라 메인 스크립트 첫 줄에서 저장, 화면보호기가 켜지면 AE 대화상자를 못 닫음 → AE 작업 중 `caffeinate -d -u`.
- 디스크(228GB): AE 디스크 캐시가 렌더 한 번에 10GB까지 참 → `render.sh`/`run.sh`가 끝날 때 비움. 편 폴더는 통째로 복사하지 않고 실제 렌더에 쓰이는 파일만 복사(`reach.py`).
- 이 맥에 프리미어 없음 → `.prproj`(gzip XML)를 `parse_prproj.py`로 직접 파싱.

### 코스트코(B209) 구조 — 검증 완료
- 편 폴더 `◆브랜드백과사전/B209_코스트코_미나_편집완` (16GB). 메인 aep `B209_코스트코_미나.aep`는 맘스터치(B206) 템플릿 복제본 — 깨진 198링크는 전부 템플릿 잔재 컴프에만 있고 최종 렌더에 안 쓰임.
- AE 3파트(로컬 사본 `src/B209_main_ko.aep`에서 고유 이름으로 개명):

| 파트 | 원래 컴프(id) | 로컬 이름 | 길이 | 내레이션 레이어 |
|---|---|---|---|---|
| 미나 | `comp`(14989) | `MAIN_KO` | 534.13 | `B209_코스트코_오디오편집완_미나.wav` |
| 가영 | `comp_가영`(2370) | `MAIN_GAYOUNG` | 217.32 | `B209_코스트코_오디오가영.wav` |
| 가을 | `comp_가을`(5848) | `MAIN_GAEUL` | 226.63 | `B209_코스트코_오디오가을편집완.wav` |

- 프리미어 `B_코스트코_음악작업.prproj` 시퀀스 `54a2a221…`(988.35초): V1 = 미나 → 가영 → 가을(내부 컷 2곳) → 세모지 아웃트로, V2 = 수정1~4 패치(현재 AE 컴프에 이미 반영됨), A1 = 파트 영상 오디오(내레이션+AE 효과음), A2 = 파트별 효과음 wav, A3·A4 = Epidemic BGM 8곡(곡 안을 잘라 붙인 중첩 시퀀스), 아웃트로 BGM `Sand_Castle.mp3`.
- 검증: 로컬 3파트 렌더를 프리미어 V1대로 조립 → NAS `B209_코스트코_최종.mp4`와 평균 유사도 0.995(0.5초 단발 차이 7개: 전환 랜덤·패치 경계·노이즈). 유튜브와는 마스터 914.3~923.3초(9.0초)만 다르고 나머지 일치(0.997).
- 화면 한글: AE 텍스트 레이어 548개(자막 포함), 아웃트로 로고("세상의 모든지식"), 이미지 속 글자는 마스터 추출 단계에서 OCR로 목록화.

## 3. 구조

```
~/Projects/semoji_global/
  scripts/
    aep_links.py build_relink_jobs.py   링크 진단·복구 후보
    reach.py                            graph.json → 실제 렌더에 쓰이는 footage·시간 구간
    parse_prproj.py assemble_pr.py      프리미어 타임라인 파싱·조립
    compare_video.py                    두 영상 프레임 대조(오프셋 자동)
    ingest.py                           NAS → 로컬(사용 파일만, NFC) + 폰트 점검 + 기준본 다운로드
    master.py                           인벤토리·그래프·프리미어 → master/ 생성
    tts.py timewarp.py subtitles.py audio_mix.py qa.py
    ae/ lib.jsx run.sh render.sh relink.jsx inventory_full.jsx graph.jsx prep_main.jsx fontmap.jsx localize.jsx
  glossary/<lang>.json   profiles/<lang>.json   assets/outro/<lang>.mov
  episodes/<EP>/
    src/                       로컬 사본(사용 파일만), <EP>_main_ko.aep(개명·폰트 매핑 완료본)
    yt_master.mp4              기준본(유튜브)
    master/
      edl.json                 마스터 타임라인(파트·컷·오버레이·아웃트로) + 기준본 대비 컷 목록
      source.json              내레이션 구간·화면 문자열·이미지 글자·한국 전용 구간
      audio.json               효과음·BGM 배치(프리미어 층) + AE 내부 효과음 목록
    l10n/<lang>.json  l10n/<lang>_review.md
    tts/<lang>/  raster/<lang>/
    build/<lang>/  (warp.json, <EP>_<LANG>.aep, 파트 렌더, warnings.json)
    render/<lang>/<EP>_<LANG>.mp4, <lang>.srt, qa/
```

## 4. 언어 중립 마스터

### 4.1 `master/edl.json` — 최종본이 어떻게 조립되는지
```json
{
  "fps": 29.97, "length": 979.35, "reference": "yt_master.mp4",
  "parts": [
    {"id": "mina", "aep_comp": "MAIN_KO", "pr_in": 0.0, "src_in": 0.0, "dur": 534.13},
    {"id": "gayoung", "aep_comp": "MAIN_GAYOUNG", "pr_in": 534.13, "src_in": 0.0, "dur": 217.32},
    {"id": "gaeul", "aep_comp": "MAIN_GAEUL", "pr_in": 751.45, "src_in": 0.0, "dur": 8.34},
    "... 프리미어 V1 클립 단위 그대로 ..."
  ],
  "cuts": [{"pr_in": 914.3, "pr_out": 923.3, "reason": "유튜브 업로드본에서 잘림"}],
  "outro": {"pr_in": 978.08, "dur": 10.27, "asset": "outro"}
}
```
- 프리미어 V1에서 생성하고, 기준본(유튜브)과 대조해 찾은 컷을 `cuts`에 더한다. 컷 적용 후 길이 = 기준본 길이(±0.1초)인지 검사.
- `pr_*`는 프리미어 시퀀스 시간(컷 적용 전). 그 밖의 모든 파일(source.json, audio.json, warp.json)의 **마스터 시간은 컷 적용 후(= 유튜브 시간)**로 통일하고, 파트 안 위치는 edl로 변환한다.

### 4.2 `master/source.json` — 바꿔야 할 것
```json
{
  "segments": [
    {"id": "n001", "part": "mina", "in": 0.52, "out": 3.90, "ko": "…", "subtitle_layers": ["#자막:12", "#자막:13"]}
  ],
  "strings": [
    {"id": "s0042", "comp": "…", "comp_id": 15167, "layer": 3, "ko": "최초의 회원제 창고형매장, 프라이스클럽",
     "font": "OTSBAggroM", "size": 80, "box": [1400, 120], "visible": [[309.6, 311.3]], "role": "title|label|subtitle"}
  ],
  "raster": [{"id": "r001", "file": "src/(Footage)/…", "ko_text": "…", "visible": [[…]], "action": "edit|keep|cut"}],
  "korea_only": [{"in": 0, "out": 0, "reason": "댓글 이벤트 등"}]
}
```
- **내레이션 구간**: 파트별 내레이션 wav를 무음 기준으로 문장 단위 분할(무음 ≥0.25초) → 같은 시간대 `#자막` 텍스트 레이어를 붙여 한글 문장 확보 → 원고 docx와 대조. 구간 시간은 마스터 시간.
- **화면 문자열**: 렌더에 도달하는 텍스트 레이어만(`reach.py` 규칙). 말자막(`#자막` 컴프)은 `role=subtitle`로 표시하고 번역 대상에서 제외(영어 자막은 새로 생성).
- **이미지 글자**: 기준본 프레임 OCR(macOS Vision, 1초 간격)로 한글 영역 → 그 시각 보이는 footage(`probe`) → 목록. 사람 검수로 `action` 확정.
- **한국 전용 구간**: 번역 단계에서 표시(내레이션 내용 기준) → `korea_only` → edl `cuts`로 반영.

### 4.3 `master/audio.json` — 내레이션 외 소리
- AE 내부 효과음: 파트 컴프 안 오디오 레이어(내레이션 레이어 제외) → AE 타임 워프가 함께 옮김.
- 프리미어 효과음 wav(파트별 1개, 이미 믹스됨): 무음(−45dBFS, ≥0.15초) 기준으로 소리 덩어리를 자르고 각 덩어리의 시작 시각을 기록.
- BGM: 프리미어 A3·A4 중첩 시퀀스를 끝까지 풀어서 `[master_in, master_out, file, src_in]` 조각 목록 + 클립 볼륨(dB). 조각 경계 = 음악 편집점.
- 아웃트로 BGM: `Sand_Castle.mp3`.

## 5. 번역 (`l10n/<lang>.json`)
```json
{"lang": "en",
 "segments": {"n001": {"text": "…", "tts": null, "drop": false}},
 "strings": {"s0042": {"text": "The First Membership Warehouse: Price Club", "font": null}},
 "raster": {"r001": {"text": "…"}}}
```
- Claude가 번역: 용어집 + 앞뒤 구간 + 같은 시간대 화면 문자열을 함께 보고 현지화.
- 길이 예산: 원래 구간 길이 × `profiles/<lang>.json`의 `chars_per_sec` 기준 ±25% 목표(초과 시 다시 씀). 타임 워프는 이 범위를 흡수.
- 화면 문자열은 원래 박스 폭 안에(넘치면 patch에서 글자 크기 축소, 최소 70%).
- 한국 전용 내용은 `drop: true` → 해당 구간 컷.
- 검수용 대조표 `l10n/<lang>_review.md`(한글 / 번역 / 예산 / 실측 길이).

## 6. 음성 (`tts.py`)
- 세모지 보이스, `profiles/<lang>.json`의 모델(기본 `eleven_v3`, 첫 구간 몇 개로 `eleven_multilingual_v2`와 비교 후 확정) + `language_code`, `/with-timestamps`.
- 구간당 1파일 `tts/<lang>/n001.mp3` + `n001.align.json`, 앞뒤 무음 트림.
- Whisper ASR 대조로 누락·오독 검출 → 해당 구간만 재생성.
- ElevenLabs 키는 오토카이로스 `.env` 사용(brand_cn_expo `gen_tts.py` 범용화).

## 7. 타임 워프 (B안 핵심)

### 7.1 시간 변환표 (`timewarp.py` → `build/<lang>/warp.json`)
- 마스터 시간축 앵커: 각 구간의 in/out, 컷 경계, 파트 경계, 마스터 시작/끝.
- 구간 i 새 길이 = 번역 음성 길이 + 원래 앞뒤 여백. 구간 사이 무음은 원래 길이 유지(최소 0.15초). 컷 구간은 길이 0.
- 앵커 사이 선형 보간 → 단조 증가 함수 `T(t)`. 구간 비율이 0.6~1.6 밖이면 경고(번역 길이 재조정 권고).
- 파트별 로컬 변환 `T_part`를 edl로 유도해 함께 저장.

### 7.2 AE 적용 (`localize.jsx`, 파트 컴프마다)
| 레이어 | 규칙 |
|---|---|
| 모든 레이어 | in/out을 `T_part`로 변환. 모든 속성 키프레임 시간을 변환(값·보간·이즈 복사 후 재생성) |
| 정지 이미지·솔리드·셰이프·텍스트·.ai | 위치·길이를 변환된 in/out대로 |
| 영상 footage | 비율 r = 새 길이/원래 길이. 0.8≤r≤1.25면 stretch, r>1.25면 원속도 후 마지막 프레임 정지(time remap), r<0.8이면 0.8배 + 뒤를 자름 |
| 프리컴프 | 이 위치에서만 쓰이면 내부 레이어에 같은 변환을 재귀 적용 + 컴프 길이 조정. 여러 곳에서 쓰이면 복제 후 적용. 한 구간 안에 들어가는 짧은 연출 프리컴프(전환·라이트릭 등)는 stretch |
| 내레이션 wav 레이어 | 끔(영어 음성은 최종 믹스에서 넣음) |
| AE 효과음 레이어 | 시작 시각만 변환(길이·속도 유지) |
| time remap 레이어 | 리맵 키프레임 시간도 변환 |
| 표현식 | 그대로(`loopOut`·`wiggle` 까딱 모션은 시간 기반이라 자연히 유지). `time` 의존 표현식은 목록으로 보고 |
| `#자막` 컴프 | 숨김 |
| 텍스트 | 문자열 ID로 교체 + 폰트 매핑(`profiles`) + 박스 넘침 시 축소 |
| 이미지 글자 | `raster/<lang>/`로 footage replace |
- 결과 `build/<lang>/<EP>_<LANG>.aep`(src는 그대로), 파트별로 aerender → `build/<lang>/part_<id>.mp4`(오디오 포함: AE 효과음만).

### 7.3 프리미어 층 (`audio_mix.py`)
- 파트 영상: edl 순서대로 이어 붙임(컷 제외) + 언어별 글로벌 아웃트로.
- 효과음 wav 덩어리: 각 덩어리 시작 시각을 `T`로 옮겨 배치(덩어리 길이·속도 유지).
- BGM 조각: 시작을 `T(master_in)`, 끝을 `T(master_out)`로. 길어지면 같은 곡 소스를 더 재생(src_out 연장), 짧아지면 끝을 자르고 10프레임 페이드. 볼륨은 프리미어 값.
- 믹스: 영어 내레이션(−16 LUFS 기준) + AE 효과음 + 효과음 wav + BGM(원래 상대 레벨 유지) → ffmpeg로 최종 mp4.

### 7.4 자막 (`subtitles.py`)
- 영어 정렬 결과로 단어 단위 분할(profile: 한 줄 최대 42자, 1~2줄, 최소 노출 0.8초).
- 세모지 자막 스타일(하단 흰 박스 + 진한 글자) 그대로 새 자막 컴프로 생성해 파트별로 넣거나, 최종 조립 시 자막 레이어 렌더를 얹음(구현 계획에서 더 단순한 쪽 선택). `render/<lang>/<lang>.srt`도 출력.

## 8. 이미지 글자·아웃트로
- (개정 2026-10-20, 사용자 지시) 일러스트·이미지 글자: **글자 없는 판 + AE 텍스트 레이어**. footage를 내보내(벡터 k=4, 긴 변 1200px 이상) OCR(투명·흰·검은 배경) → 글자 자리를 판 색으로 채운 판 PNG(언어 무관, 1회) → footage와 같은 크기 프리컴프에 판(1/k) + 언어별 텍스트 레이어(위치·각도·색·두 색 강조·외곽선) → 모든 사용처 소스 교체. 뉴스 캡처는 작은 글자 흐림 + 큰 글자만 텍스트. 인페인팅·래스터 글자 그리기는 쓰지 않음(테두리·그라데이션 훼손). 사람이 고칠 것은 `raster/manual.json`. 원본/판 비교 시트로 검수.
- 공용 영상 에셋 속 글자(예: `세모지감정14_킥킥.mov`의 ㅋ)는 편별 교체가 아니라 언어별 에셋 대체 표로 다룬다(미정).
- 실제 로고·제품 패키지는 `keep`.
- 글로벌 아웃트로: 세모지 아웃트로(“세상의 모든지식” 로고)를 언어별 채널명으로 바꾼 버전을 한 번 만들어 `assets/outro/<lang>.mov`로 재사용. 채널 영문명은 사용자 확인 필요.

## 9. 렌더와 검수 (`qa.py`)
- OCR(1초 간격) 한글 잔존 0자 → 위치·시각 보고.
- Whisper ASR 전사 vs 번역 대조.
- 장면 전환(ffmpeg scdet) vs 앵커 변환 시각 비교, BGM 편집점 위치 확인.
- 콘택트시트(5초 간격), 길이·fps·해상도.
- 문제 구간만 수정 → 같은 명령으로 재빌드.

## 10. 에피소드 가져오기 (`ingest.py`)
1. 기준본: `yt-dlp`로 유튜브 업로드본 다운로드(1080p).
2. NAS aep를 AE로 읽기 전용으로 열어 `graph.jsx` → 메인 컴프(들) 찾기(렌더 큐·길이·프리미어 시퀀스 단서) → `reach.py`로 실제 사용 footage만 로컬 복사(NFC). 프리미어 프로젝트가 있으면 `parse_prproj.py`.
3. 누락 footage: NAS 인덱스로 후보(경로 꼬리 일치 점수) → 로컬 복사 → `relink.jsx`. 후보가 여럿이면 각 후보로 해당 시간대만 렌더해 기준본과 대조, 가장 비슷한 것으로 확정.
4. `prep_main.jsx`(파트 컴프 고유 이름) + `fontmap.jsx`(설치 안 된 폰트 → 대체 매핑, 매핑 표는 `profiles/ko.json`).
5. 재구성 검증: 파트 렌더 → 조립 → 기준본과 `compare_video.py`. 단발 차이 외 연속 차이가 있으면 원인(컷·패치·누락)을 찾아 edl에 반영할 때까지 반복. 통과해야 마스터 단계로.

## 11. 실패 처리
- AE 대화상자 멈춤: JSX 전체를 try/catch로 감싸 오류를 로그 파일에 기록, run.sh에 무진행 감시(스크린샷 + 중단).
- 경고(워프 비율·표현식·박스 넘침)는 `build/<lang>/warnings.json`에 모아 보고.
- 모든 단계 멱등. 산출물이 있으면 건너뛰고 `--force`로 재생성.
- 디스크 여유 10GB 미만이면 렌더·복사 중단.

## 12. 열어둔 기본값 (테스트 중 확정)
- 영어 폰트: SB 어그로 OTF의 영문 글리프로 먼저 렌더해 보고, 어색하면 비슷한 굵은 둥근 산세리프로 profile 매핑 변경.
- TTS 모델: eleven_v3 vs multilingual_v2 비교 후 profile 확정.
- 채널 영문명(아웃트로·용어집).

## 13. 범위 밖
- NAS aep 일괄 링크 복구(진단 도구·매핑은 있음)
- 썸네일·제목·설명 현지화, 업로드 자동화
- 일본어·중국어 실제 제작(구조 검증만 코스트코 영어판 이후 짧게)
