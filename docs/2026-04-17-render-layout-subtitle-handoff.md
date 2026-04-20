# 2026-04-17 Render/Layout/Subtitle Audit Handoff

> 세션 컨텍스트를 비우고 다시 이어갈 때 바로 읽을 수 있는 작업 기억 문서.

## 현재 목표
- Stage2 → storyboard → Scene Editor → Studio 까지 스타일, 레이아웃, 의미있는 분기점이 단일 계약으로 일관되게 흐르는지 검토
- map scene / video asset / image asset 분기가 혼선 없이 storyboard, Scene Editor, Studio 에 공통 반영되는지 확인
- git pull 받은 다른 컴퓨터에서도 설정 누락 없이 동일하게 유지되는지 검토
- 추가로 업로드된 txt 문서의 자막/TTS 관련 12개 문제를 현재 코드 기준으로 실제 원인 존재 여부로 판정

---

## 이번 세션에서 이미 완료한 safe-scope 수정

### 1) storyboard 썸네일 parity 복구
수정 파일:
- `remotion/src/preview/ThumbComposition.tsx`
- `auto_agent/remotion_template/src/preview/ThumbComposition.tsx`
- `auto_agent/dashboard/helpers.py`
- `auto_agent/dashboard/templates/partials/_storyboard.html`
- `app.py`
- `tests/test_storyboard_parity_safe_scope.py`
- `auto_agent/dashboard/static/scene-thumb.js`

핵심 내용:
- storyboard thumb 에서 map placeholder 제거 후 `MapSceneRenderer` 사용
- storyboard thumb 에서 videoAsset 제거 분기 삭제
- dashboard helper 가 manifest 최종 layout 을 우선 사용
- storyboard template 이 `_layout` 기준으로 보이도록 정렬
- `/api/p/{slug}/art-style` 변경 시 config update 뿐 아니라 project local art style provision → manifest rebuild → studio refresh 까지 연결

검증:
- `python -m py_compile app.py auto_agent/dashboard/helpers.py`
- `node node_modules/vite/dist/node/cli.js build --config vite.thumb.config.ts`
- `./.venv/bin/python -m pytest tests/test_storyboard_parity_safe_scope.py -q`

커밋:
- `85af3fa` — `fix: storyboard thumbnail parity and art-style apply chain`

### 2) canonical art style source safe-scope 정리
수정 파일:
- `auto_agent/ui/prompts.py`
- `auto_agent/cli.py`
- `tests/test_style_source_safe_scope.py`

핵심 내용:
- style scan source 를 root ignore 디렉토리가 아니라 `auto_agent/data/artstyle/styles/*.json` 으로 정리
- CLI style add/remove 도 canonical package data 기준으로 동작하도록 정리

검증:
- `python -m py_compile auto_agent/ui/prompts.py auto_agent/cli.py`
- `./.venv/bin/python -m pytest tests/test_style_source_safe_scope.py -q`
- 통합 확인: `./.venv/bin/python -m pytest tests/test_storyboard_parity_safe_scope.py tests/test_style_source_safe_scope.py -q`

커밋:
- `efcf34b` — `refactor: use canonical art style source for cli and prompts`

---

## 현재 구조 판단 요약

### 이미 확인된 핵심 결론
1. **실제 단일 계약은 manifest 중심**이다.
2. **style-manager 는 런타임 authority 가 아니라 정의용**이다.
3. **canonical art style source 는 `auto_agent/data/artstyle/styles/*.json`** 이다.
4. **project runtime 에서는 project local `art_style.json` 우선권 유지**가 안전하다.
5. **storyboard 에서 map/video 를 제외하는 것은 의도된 분기가 아니라 버그**다.

### 아직 구조적으로 남은 리스크
1. root `remotion/` runtime 을 실제 app/studio 가 사용하지만, 핵심 파일 다수가 gitignore 또는 untracked 상태다.
2. root `artstyle/` 는 gitignore 라서 설정 재현성이 나쁘다.
3. subtitle/TTS/save/manifest 쪽은 이번 safe-scope 작업과 별개로 아직 불안정하다.

---

## git / 재현성 관련 핵심 메모

### 매우 중요
실행 런타임은 root `remotion/` 트리를 쓰는데, 아래 같은 파일들이 git 기준으로 안전하지 않다.

대표 예시:
- `remotion/package.json` → NOT_TRACKED
- `remotion/tsconfig.json` → NOT_TRACKED
- `remotion/vite.editor.config.ts` → NOT_TRACKED
- `remotion/vite.thumb.config.ts` → NOT_TRACKED
- `remotion/remotion.config.ts` → NOT_TRACKED
- `remotion/src/index.ts` → NOT_TRACKED
- `remotion/src/SceneEditor.tsx` → ignore (`.gitignore:108:/remotion/src/*`)
- `remotion/src/preview/ThumbMount.tsx` → ignore (`.gitignore:108:/remotion/src/*`)

추가:
- `artstyle/` 도 ignore (`.gitignore:83:/artstyle/`)

의미:
- 다른 컴퓨터가 git pull 만으로 동일 상태를 재현하지 못할 수 있음
- tracked template 와 local root runtime 이 drift 난 상태일 수 있음
- 특히 remotion runtime 관련 이슈는 **git 기준 미해결 / 로컬 머신 기준 불명확** 판단이 자주 필요함

---

## txt 문서 12개 문제 판정 결과
문서 경로:
- `/Users/jleavens_macmini/.hermes/cache/documents/doc_24f3171b59eb_152f83b13d3f1467.txt`

### 확실히 현재 코드에도 남아 있는 것
1. `format_srt_time` 절삭 버그
2. 마지막 자막이 씬 끝보다 빨리 사라짐
3. 빈 자막 entry 저장 허용
5. 자막 저장 후 storyboard 프리뷰 미갱신
6. TTS 재생성 시 display/TTS 라인 수 불일치 시 비례 분배 fallback
7. Studio 자막 저장 시 숫자/영문 혼합 타이밍 보정 부재
9. 특정 씬 TTS regenerate 후 `subtitles.json` 이 부분 데이터로 덮여 manifest 에 전파될 가능성
11. Remotion timeline track limit 미설정

### 부분적이거나 전용 수정 없음
4. 특정 단어 0초 duration 문제를 막는 전용 보정은 현재 없음
8. 복합 숫자 자막 분할 방지 규칙은 일부 있으나 충분하지 않음
10. 생성 단계의 자막 gap 제거는 일부 있으나 핵심 onset 기반 정렬은 없음

### txt 에 적힌 정확한 원인은 현재 코드와 다른 것
12. 문자 단위 타임스탬프 그대로 사용이 root cause 라는 서술은 현재 코드와 불일치
- 현재 `generate_subtitles.py` 에는 `chars_to_words()` 가 이미 존재함
- 다만 다른 경로의 분절/정렬 문제는 여전히 가능

---

## P0 우선순위

### P0-1. scene regenerate 가 전체 subtitles/manifest 를 깨뜨리는 체인 차단
문제 축:
- `auto_agent/dashboard/actions.py`
- `auto_agent/scripts/generate_subtitles.py`
- `auto_agent/scripts/build_manifest.py`

현재 위험:
- `tts_regenerate --scene N` 이후 `subtitle_sync --scene N`
- `generate_subtitles.py` 가 현재 처리한 씬만 포함한 `subtitles.json` 재기록 가능
- `build_manifest.py` 가 `subtitles.json` 을 그대로 읽어 전체 manifest 에 반영

의미:
- 제일 위험함. 다른 씬 자막까지 연쇄 손상 가능

### P0-2. 자막 시간 계산의 기본 정확도 복구
문제 축:
- `generate_subtitles.py`
- `app.py save_subtitles()`

핵심 이슈:
- ms 절삭
- 마지막 end 가 실제 MP3 길이가 아니라 마지막 char timestamp 기준
- 빈 entry 저장 허용
- 저장 시 단어 경계 보정 없음

### P0-3. 저장 후 반영 일관성 복구
문제 축:
- `_storyboard.html`
- `_studio.html`
- 필요시 manifest cache helper

핵심 이슈:
- Studio subtitle save 후 iframe refresh 만 하고 storyboard cache invalidate 가 없음

---

## 다음 세션에서 바로 할 일

### 1단계: `#9` 먼저 막기
대상 파일:
- `auto_agent/dashboard/actions.py`
- `auto_agent/scripts/generate_subtitles.py`
- `auto_agent/scripts/build_manifest.py`

작업 방향:
- partial scene subtitle regenerate 가 기존 `subtitles.json` 전체를 덮지 않도록 방어
- scene partial mode 와 full rebuild mode 를 분리
- manifest rebuild 가 부분 손상 JSON 에 휘둘리지 않도록 방어
- 회귀 테스트 추가

### 2단계: `#1 #2 #3` 자막 저장/생성 기초 수정
대상 파일:
- `auto_agent/scripts/generate_subtitles.py`
- `app.py`
- `tests/...` 신규 추가

작업 방향:
- ms 계산을 round 기반으로 정리
- 마지막 자막 end 는 실제 MP3 길이 기준 우선
- 빈 text entry 는 저장 단계에서 제거
- 저장 시 entry 정규화 로직 추가

### 3단계: `#5 #7` save 반영/타이밍 보정
대상 파일:
- `auto_agent/dashboard/templates/partials/_storyboard.html`
- `auto_agent/dashboard/templates/partials/_studio.html`
- `app.py`

작업 방향:
- subtitle save 성공 시 storyboard cache clear / preview refresh
- 숫자/영문 혼합 자막 저장 시 무보정 저장이 아니라 최소한의 경계 스냅 전략 도입 검토

### 4단계: `#6 #11` 보강
대상 파일:
- `auto_agent/scripts/generate_subtitles.py`
- `auto_agent/remotion_template/remotion.config.ts`
- root remotion runtime 비교 필요

---

## 다음 세션 재개용 명령
프로젝트 루트:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3`

권장 재시작 프롬프트 예시:
- `docs/2026-04-17-render-layout-subtitle-handoff.md 읽고 이어서 진행해주세요. 우선 P0-1 (#9)부터 수정하고 테스트까지 해주세요.`

필요시 재확인 명령:
- `git status --short`
- `./.venv/bin/python -m pytest tests/test_storyboard_parity_safe_scope.py tests/test_style_source_safe_scope.py -q`
- `python -m py_compile app.py auto_agent/dashboard/helpers.py auto_agent/ui/prompts.py auto_agent/cli.py`

---

## 세션 클리어 전 기억해야 할 핵심 한 줄
**지금 가장 위험한 건 subtitle partial regenerate 가 `subtitles.json` 과 manifest 를 연쇄 손상시킬 수 있는 구조(#9)이고, 그 다음이 자막 저장/타이밍 기초 정확도(#1 #2 #3 #5 #7)입니다.**
