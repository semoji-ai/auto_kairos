# codex 프로바이더 라우팅 설계 — 리서치 + 이미지 생성

날짜: 2026-07-21
브랜치: v4-bridge

## 목표

1. 웹 리서치 에이전트 2종(flesh-researcher, targeted-researcher)을 **codex CLI 기본**으로 실행해 Claude 토큰을 절약한다. 옵션으로 claude 복귀 가능.
2. 이미지 생성을 **codex-fleet(codex 내장 image_gen 병렬 스폰) 기본 + FAL 폴백**으로 전환한다.

## 현황 (검증된 사실)

- 파이프라인 에이전트 스텝은 `auto_agent/orchestrator/runner.py::_run_agent_step`이 claude CLI 전용으로 호출.
- `auto_agent/modules/agent_runner.py`에 검증된 codex 호출 코드 존재: `_build_codex_cmd`(`codex exec -C <dir> --skip-git-repo-check --ephemeral --sandbox workspace-write --json --output-last-message <tmp> -m <model>`, stdin 프롬프트) + `_read_output_last_message`. 단 파이프라인 러너와는 미연결.
- `auto_agent/modules/image_batch_module.py`는 FAL 전용(`tools/fal_queue.py`, `image_generate.py`).
- `auto_agent/tools/codex_image.py`는 codex 내장 image_gen 단건 호출 모듈 — 어디에서도 import되지 않는 미배선 상태.
- codex-fleet 패턴 문서: `~/.codex/skills/codex-imagegen/SKILL.md` — 병렬 스폰, RAM 기반 auto 스케일, mtime 기반 회수의 레이스 버그 경고(claimed-set으로 해결).

## 1. 리서치 codex 라우팅

### 스위치

- `agents.json`의 flesh-researcher / targeted-researcher 정의에 `"provider": "codex"` 필드 추가 (기본값).
- 오버라이드 우선순위: **프로젝트 config `research_provider` > env `AUTO_AGENT_RESEARCH_PROVIDER` > agents.json `provider` > `claude`**.
- research-strategist는 claude(opus) 유지. 다른 에이전트는 변경 없음.

### 실행 경로

- codex 명령 빌더/출력 회수를 공용 유틸 `auto_agent/utils/codex_cli.py`로 추출:
  - `find_codex_cli()`, `build_codex_exec_cmd(model, reasoning_effort, output_last_message, workdir, search=False)`, `read_output_last_message(path, fallback)`.
  - `modules/agent_runner.py`는 이 유틸을 사용하도록 리팩터 (중복 제거).
- `orchestrator/runner.py::_run_agent_step`에 provider 분기:
  - provider가 codex면 codex exec 명령으로 실행 (stdin 프롬프트, `--search` 플래그로 내장 웹 검색 활성화).
  - claude 전용 플래그(`--allowedTools`, `--max-turns`, claude 모델명)는 codex 경로에서 제외. codex 모델은 agents.json `codex_model` 필드가 있으면 `-m`으로 전달, 없으면 `-m` 생략하고 codex CLI 기본 모델을 따른다.
  - `CLAUDECODE` env pop 유지.
- 프롬프트: 기존 SKILL.md 주입 방식 그대로. 단 claude 도구명 지시(WebSearch/WebFetch)는 "웹 검색 도구" 중립 표현으로 SKILL.md 정리.

### 폴백/검증

- codex CLI 부재, 비정상 종료, 또는 산출물 파일(chapter_facts/, targeted_claims.json) 미생성 시 → 동일 스텝을 claude로 1회 재실행.
- **구현 첫 단계는 스모크 테스트**: `codex exec --search`로 실제 웹 검색 + 파일 산출이 되는지 검증. 실패하면 설계 재검토 (블로커).
- resume 계약(출력 파일 존재 시 스킵)은 provider와 무관하게 동일.

## 2. 이미지 codex-fleet 기본 + FAL 폴백

### 라우터

- `image_batch_module.py` 진입부에서 backend 결정: 프로젝트 config / env `IMAGE_BACKEND=codex|fal`, 기본 `codex`. 단 `codex_available()` false면 자동 FAL로 강등 (progress 로그 명시).

### codex 경로

- `tools/codex_image.py`를 codex-fleet 패턴으로 확장 (또는 `tools/codex_fleet.py` 신설, 단건 함수 재사용):
  - `codex exec` 병렬 스폰 — ThreadPool, `PARALLEL=auto`(여유 RAM ÷ 0.4GB, HARD_CAP 32, START 3에서 램프업, 429 감지 시 성장 정지).
  - 회수는 **out_path 직접 복사(1차) + 세션ID 파싱(2차)** — `codex_generate`가 세션 안에서 out_path로 직접 복사하므로 워커 간 회수 레이스 자체가 없음 (구현 시 claimed-set보다 단순·안전해 이 방식 채택. mtime 전역 스캔은 사용하지 않음).
  - 씬별 타임아웃 240s, 회수 후 PIL 강제 리사이즈(내장 툴 크기 비결정성 보정).
  - `env -u OPENAI_API_KEY` 유지 — OpenAI API 직접 호출 금지 규칙 준수.
- **실패 씬만 FAL로 개별 폴백** (모더레이션 거부 포함). 캐릭터 배치도 동일 라우팅.

### 프롬프트 빌더

- FAL용 빌더(`_build_scene_fal_input` 등)와 별도로 gpt-image-2용 빌더 추가:
  - 공냥 규격: 네거티브 표현 금지(긍정형 치환), 앞머리 브래킷 금지, 끝에 `AR x:y` 토큰, 6섹션 템플릿, 사이즈 락 6종 매핑(16:9→1792x1024 등).
  - 생성 전 `node ~/.claude/skills/image-prompt/scripts/check_prompt.mjs` 검증 — `ok:true` 필수, 실패 프롬프트는 수정 후 재검증.
- 아트스타일(design_tokens/artstyle JSON)의 스타일 키워드는 codex 프롬프트에 병합 (FAL 경로와 시각 일관성 유지).

### 불변 규칙

- 이미지 파일 삭제 절대 금지, 재생성은 `_gen_02` 버전 번호, `image_assets.json` selected만 전환 — 백엔드 무관 동일.
- assembly-director의 Phase B-3 멀티모달 검수 흐름 변경 없음 (module 출력 계약 동일).

## 테스트

- 유틸 단위 테스트: 명령 빌드, provider 우선순위 해석, 프롬프트 빌더의 공냥 규격 출력.
- 스모크: codex 리서치 1스텝(`--only step_2_target`), codex 이미지 2~3씬 생성 → 회수 1:1 매칭 확인.
- 회귀: FAL 강등 경로(`IMAGE_BACKEND=fal`), claude 폴백 경로.

## 비채택 대안

- 리서치 스텝의 module 재작성 — SKILL.md/래칫 체계와 이원화되어 기각.
- pipeline.json 스텝별 provider 플래그 — 대상이 2종뿐이라 agents.json 필드로 충분.
- mtime 전역 스캔 기반 이미지 회수 — 병렬 시 레이스 버그(codex-imagegen 스킬 문서 경고)라 비채택. 세션ID 파싱은 2차 안전망으로만 사용.
