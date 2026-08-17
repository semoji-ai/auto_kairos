# SPEC — AE 패널 재설계: 탭 작업대 + 스토리보드 프로덕션 시트 + 협업형 제작 비서 (v0.2)

> 작성일 2026-06-09 (v0.1) · 사용자 검토 반영 v0.2. 대상: `auto_kairos_adobe` CEP 패널 + stdlib 백엔드.
> 결정 출처: 브레인스토밍 Q&A(§1) + 사용자 검토(§1.1) + v3/kairos_ai 스토리보드 레퍼런스 조사.

## 0. 목표 / 비전

AE 안에서 **콘텐츠 제작 비서(LLM 오케스트레이터)** 와 함께 기획 → 리서치 → 원고 → 에셋/씬 이미지 → (후속)비디오 → **AE 씬별 컴포지션 조립**까지 진행하는 통합 작업대. 비서는 자동 순차 실행이 아니라 **단계별 진행상황을 알려주며 함께 진행(협업형)**. 중심 화면은 **스토리보드 프로덕션 시트**.

## 1. 확정 결정 (브레인스토밍)

| 항목 | 결정 |
|---|---|
| 챗봇 역할 | 하이브리드 — 시트/탭=제어, 채팅=대화·진행 |
| 챗봇 능력 | 실행형 — 대화로 액션 호출 |
| 실행 성격 | **협업형 오케스트레이터** — 단계별 진행상황 보고하며 함께 진행(완전 자동 순차 아님), 체크포인트 게이트 |
| 실행 방식 | A. 구조화 의도 루프 — codex `--output-schema` `{reply, action, next}` |
| 창 형태 | 독립 플로팅·리사이즈 창 + 반응형 |
| 중심 | 스토리보드 프로덕션 시트 |

## 1.1 검토 반영 (사용자 v0.2)

- 상세 뷰를 **탭 구조**로 단순화: **기획 탭**(결과물 파일 뷰어) + **스토리보드 탭**(프로덕션 시트).
- 스토리보드 탭 내부 **갤러리 패널**(탐색기형): 프로젝트 이미지/비디오 소스 열람 + 드래그→시트 적용 + **수동 이미지 생성/검색**.
- 씬 이미지를 레이어로 나눈 경우, **씬별 레이어 썸네일 갤러리**를 시트에 표시.
- **제작 비서는 하단 채팅 영역**에 배치.
- **이미지: 생성 + 검색** 모두 — Serper(구글)·Pixabay·Unsplash. 검색 API는 auto_kairos 참고.
- **TTS: ElevenLabs**, 키는 auto_kairos `.env`(`ELEVENLABS_API_KEY` 등).
- **AE 가져오기(카이로스애펙 고유)**: 씬별 **각각 컴포지션**으로 가져와 타임라인 정렬. TTS 있으면 **TTS 길이 = 컴프 길이**, 순서대로 나열.
- 기획·리서치·원고 단계 **고도화는 auto_kairos_v4 방식 참고**.

## 2. 네비게이션 — 2뷰 모델

- **목록 뷰**: 새 프로젝트 폼 + 프로젝트 카드(제목·스타일·분량·상태) → 클릭 입장.
- **상세 뷰**: 프로젝트 전용 작업대(탭 구성, §3). 상단 `← 목록` 퇴장.
- 상태 `CURRENT_PROJECT`, show/hide(빌드 불필요).

## 3. 상세 뷰 — 탭 작업대

```
┌─ {제목} {스타일·분량}                          [← 목록] ┐
│ 태스크: ✅기획 ✅리서치 ✅원고 ✅씬분해 ⏳캐릭터 ⬜씬이미지 ⬜AE │
│ [ 기획 ] [ 스토리보드 ]   ← 탭                              │
├──────────────────────────────────────────────┤
│ (탭 콘텐츠)                                                  │
├──────────────────────────────────────────────┤
│ 💬 제작 비서 (하단 채팅, 항상 표시)   [입력…] [전송]         │
└──────────────────────────────────────────────┘
```

### 3.1 기획 탭 — 결과물 파일 뷰어

- 좌측 파일 트리/리스트: `plan.md`(기획서), `research/`·`research_report` 등(리서치), `draft.md`·`final_manuscript.md`(원고) 등 프로젝트 산출물을 **파일 단위로** 나열.
- 우측 뷰어: 선택 파일 렌더(md 렌더링/텍스트). 읽기 중심 + 비서로 수정 지시.
- 기획·리서치·원고 **고도화 절차는 v4 방식 참고**(skeleton→flesh→draft→targeted→manuscript, brief deepener). 비서가 이 단계들을 운전.

### 3.2 스토리보드 탭 — 프로덕션 시트 + 갤러리 패널

```
┌ 스토리보드 시트 (중심) ───────────┬ 갤러리 패널(탐색기) ┐
│ 씬#│미디어              │나레이션│캐릭터│ [이미지|비디오] 필터│
│ 1 │🖼 + (레이어 썸네일🔳🔳)│[편집] │지오 │ [🖼][🖼][🎬][🖼]  │
│ 2 │🖼/🎬               │[편집] │ —  │ 검색:[____][Serper▾]│
│ 선택액션:[컷나누기][병합][삭제]    │ [이미지 생성][에셋생성]│
│         [씬이미지 생성/검색][TTS]  │ (드래그→시트 적용)    │
└────────────────────────────┴──────────────┘
```

**시트(씬당 1행)** 컬럼: `씬# | 미디어 | 나레이션(편집) | 캐릭터 | (후속 TTS)`
- 씬 구조: 컷 나누기(split)·병합(merge)·추가·삭제·순서.
- 나레이션: 인라인 편집 + 비서 생성/수정 (`narration_dirty`).
- 씬 이미지: 행에서 **생성/재생성/검색** — 생성은 검증된 방식([[scene-image]]/[[character-sheet]]: 캐릭터+베이스 첨부, 비율 텍스트 없음).
- **레이어 썸네일**: 씬 이미지를 레이어로 분리한 경우, 그 씬 행에 분리된 레이어 이미지들을 **작은 썸네일 갤러리**로 표시.

**갤러리 패널(탐색기형, 시트 우측/접이식)**:
- 프로젝트의 이미지/비디오 소스를 종류 필터(이미지|비디오)로 열람.
- **드래그 → 시트 행 미디어에 적용/교체.**
- 패널 내 **수동 작업**: 이미지 생성(에셋/씬), 이미지 **검색**(Serper/Pixabay/Unsplash) → 결과를 소스로 저장.

### 3.3 하단 채팅 — 제작 비서 (§4)

상세 뷰 하단 고정. 어느 탭에서도 대화 가능.

## 4. 제작 비서 (협업형, 방식 A)

### 4.1 구조화 의도 루프

```
사용자 메시지 → POST /api/chat {project_id, message, session_id?}
  컨텍스트: 프로젝트 상태 + 태스크 + 액션 카탈로그 + codex 세션(resume)
  codex --output-schema → { reply, action:{name,args}|null, next: "continue"|"checkpoint"|"done" }
  action 있으면 → actions.dispatch(name,args) (화이트리스트) → 결과·태스크 갱신 → 컨텍스트 추가
  next=continue & 체크포인트 아님 → 다음 액션 루프 / checkpoint → 정지+확인 reply / done → 종료
  진행·결과 → 패널 스트리밍(job 로그 폴링 재사용)
```
협업형 원칙: 한 번에 끝까지 자동 돌리기보다 **단계마다 결과·다음 제안을 보고**하고, 사용자가 진행/수정 결정. 명시적으로 "여기까지 진행" 하면 연쇄.

### 4.2 액션 카탈로그 (화이트리스트)

`run_skill`(기획/리서치/원고 — v4 고도화 절차 포함), `decompose`(scene-decompose), `generate_character`, `generate_references`, `generate_scene_images`, `search_images`(serper/pixabay/unsplash), `generate_layers`, **시트 편집**(`update_narration`/`split_scene`/`merge_scenes`/`add_scene`/`delete_scene`/`regen_scene_image`), `generate_tts`, `import_to_ae`.

> 용어: 이 패널 **"스토리보드"** = 프로덕션 시트(§3.2). 기존 코드 `/api/storyboard`·`storyboard/` = 씬별 이미지(레거시 명칭) → 가능하면 `/api/scene-images`로 정리. 콘티(Seedance용 흑백 스케치)는 별개([[scene-image]] 규칙).

### 4.3 안전장치

화이트리스트만 실행 · 파괴 액션 없음(이미지/파일 하드 삭제 금지; 씬 삭제는 `_archived`+sceneId 보존) · 체크포인트 게이트 · workspace-write 한정.

## 5. 태스크 체크리스트

태스크 = 파이프라인 단계(기획→리서치→원고→씬분해→캐릭터→씬이미지→(레이어)→AE 조립). 상태는 산출물 존재로 자동 판정 + 명시 오버라이드. 상단 바 표시, 비서가 진행하며 갱신, 체크포인트 = 단계 경계.

## 6. 이미지 소스 — 생성 + 검색

- **생성**: codex image_gen (기존 `imagegen.py`, 검증된 방식).
- **검색**: `search_images(query, engine)` — `serper`(Google 이미지), `pixabay`, `unsplash`. **auto_kairos_v3 참고**: `auto_agent/tools/serper_search.py`, `image_search.py`. 결과 후보 → 선택 시 프로젝트 `images/search/`에 저장(무삭제·버전).
- 키: auto_kairos `.env`의 `SERPER_API_KEY`, `PIXABAY_API_KEY`(Unsplash 키 추가 시 활성).

## 7. TTS — ElevenLabs

- `generate_tts(scene)` — ElevenLabs API. **auto_kairos_v3 참고**: `auto_agent/tools/elevenlabs.py`, `tts_regenerate.py`.
- 키/설정: auto_kairos `.env` — `ELEVENLABS_API_KEY`(필수), `ELEVENLABS_VOICE_ID`/`ELEVENLABS_MODEL_ID`(선택, 기본 `eleven_multilingual_v2`).
- 씬 `narration_tts`(전처리) → 오디오 → `scenes.json`에 `audioPath`·`durationSec` 기록. 무삭제·버전.

## 8. AE 가져오기 (카이로스애펙 고유)

- **씬별 각각 컴포지션** 생성 → 메인 타임라인에 **순서대로 정렬**.
- **TTS 있는 씬**: TTS 오디오 길이 = 씬 컴프 길이. 없으면 기본 길이(스펙: `durationFrames` 또는 기본값).
- 컴프 내용: 씬 미디어(이미지/비디오/레이어) 배치. 레이어가 있으면 레이어별 트랙.
- ExtendScript(`jsx/import_to_ae.jsx` 확장): 씬 컴프 생성 + 마스터 컴프 타임라인 정렬 + 오디오 길이 동기.

## 9. 백엔드 변경

- **`backend/actions.py`**(신규): 액션 본문 → 호출가능 순수 함수 + 화이트리스트 레지스트리(엔드포인트·비서 공용).
- **`backend/scenes.py`**(신규): `scenes.json` CRUD(load/save/update_narration/split/merge/add/delete, sceneId 보존, `_archived`).
- **`backend/search.py`**(신규): serper/pixabay/unsplash 검색(v3 참고 이식, 키는 auto_kairos .env).
- **`backend/tts.py`**(신규): ElevenLabs(v3 참고 이식).
- **`backend/tasks.py`**(신규): 산출물 기반 태스크 상태.
- **`backend/chat.py`**(신규): 구조화 의도 루프 + actions.dispatch + 세션 resume + 체크포인트.
- **`backend/env.py`** 또는 로더: auto_kairos `.env` 경로에서 키 로드(ELEVENLABS/SERPER/PIXABAY). 경로는 설정/환경변수.
- **router**: `/api/chat`, `/api/scenes`(GET/PATCH/split/merge/add/delete), `/api/tasks`, `/api/search-images`, `/api/tts`, `/api/import-ae`. 기존 이미지/캐릭터 엔드포인트는 `actions.py` 호출로 정리.

## 10. 패널 변경

- `index.html`: 목록 뷰 / 상세 뷰(2섹션). 상세 = 태스크바 + 탭(기획·스토리보드) + 하단 채팅.
- 반응형 CSS: 넓으면 시트+갤러리 2열, 좁으면 갤러리·채팅 접이식.
- `js/` 모듈: `nav.js`, `planning.js`(파일 뷰어), `storyboard.js`(시트·행작업·레이어썸네일), `gallery.js`(탐색기·드래그·수동 생성/검색), `chat.js`(비서), `tasks.js`. 기존 `main.js` 함수 재사용/이전.
- `jsx/import_to_ae.jsx`: 씬별 컴프 + 타임라인 정렬 + TTS 길이 동기.
- CEP manifest: 플로팅/리사이즈 크기 범위.

## 11. 구현 분해 (P1~P7) — 설계는 한 번에, 구현은 단계로

- **P1**: 네비게이션 셸(목록↔상세) + 탭 골격(기획/스토리보드) + 하단 채팅 자리 + 반응형.
- **P2**: 기획 탭 파일 뷰어(산출물 트리+렌더).
- **P3**: 스토리보드 시트(씬 행 조회·나레이션 편집·씬 이미지 생성/재생성·레이어 썸네일) + `/api/scenes` GET/PATCH.
- **P4**: 갤러리 패널(탐색기·드래그→적용·수동 생성·**검색** serper/pixabay) + `backend/search.py`.
- **P5**: 씬 구조 편집(split/merge/add/delete) + 태스크 체크리스트.
- **P6**: 액션 디스패치 리팩터(`actions.py`) + TTS(`tts.py`) + AE 씬별 컴프 가져오기(`import_to_ae.jsx`).
- **P7**: 제작 비서(`/api/chat` 구조화 루프 + 체크포인트 + 운전) + 채팅 UI.

각 Phase 독립 테스트·커밋. P1~P6은 비서 없이 동작(점진 출시).

## 12. 비목표

- 비디오 생성(Seedance) 실제 연동 — 미디어 토글·소스 관리까지만.
- 씬별 다중 캐릭터 roster 자동 매핑 — 행에서 수동 지정.
- Remotion 이식(명시 제외).

## 13. 테스트

- 백엔드 stdlib + pytest(`/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest`, repo 루트). `scenes/actions/tasks/chat/search/tts` 순수 함수 단위 테스트(외부 API·codex monkeypatch). tmp_path 격리.
- 패널 JS: `node -e "new Function(...)"` 문법 체크. 라이브 API/codex 호출은 사용자 확인 후.

## 14. 미해결 → 결정

- 스트리밍: job 로그 폴링 재사용(SSE 후속).
- 씬 삭제: `_archived`+sceneId 보존(하드 삭제 금지).
- auto_kairos `.env` 경로: 환경변수 `AUTO_KAIROS_ENV`(미설정 시 `../auto_kairos_v3/.env` 후보) — 구현 시 확정.
- Unsplash: .env 키 부재 → 키 추가 시 활성, 기본은 serper/pixabay.
