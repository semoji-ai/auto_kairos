# Project Rules

## Language
- 항상 한글로 답변할 것

# currentDate
Today's date is 2026-03-16.

## API 사용 규칙
- Anthropic API 직접 호출은 사용자가 명시적으로 요청할 때만 사용
- 기본적으로 모든 에이전트/서브에이전트 실행은 **Claude CLI (`claude` 바이너리)** 우선
- AgentLoop(Anthropic API 직접) 대신 Claude Code의 Agent 도구 또는 `subprocess`로 `claude` CLI를 호출할 것

## 반복 에러 방지 규칙 (에러 볼트 기반)

> 아래 규칙은 ~/Desktop/kairos-vault/08-dev/errors/ 에 기록된 실제 에러에서 추출했습니다.
> 새로운 에러를 해결하면 볼트에 기록하고, 패턴이 보이면 이 섹션에 규칙을 추가하세요.

### 1. Remotion 수정 시 반드시 양쪽 동기화
- `remotion/src/` 수정 → `auto_agent/remotion_template/src/`에도 반드시 동일 수정
- 빌드 후 remotion_template에서 빌드 확인
- **절대 한쪽만 수정하고 끝내지 말 것** (3회 반복 에러)

### 2. 새 파일 추가 시 패키지 데이터 체크
- 스킬(.md), 스크립트(.js), 아트스타일(.json) 등 새 파일 추가 시:
  1. `pyproject.toml` package-data에 포함되는지 확인
  2. `.gitignore`에 의해 제외되지 않는지 확인
  3. `pip install -e .` 후 파일이 실제 존재하는지 확인

### 3. 스킬 추가 시 4단계 체크리스트
- [ ] 스킬 .md 파일 생성 (`auto_agent/data/skills/shared/`)
- [ ] `agents.json` shared_skills 목록에 등록
- [ ] `agents.json` 해당 에이전트 skills 배열에 추가
- [ ] `pipeline.json` 해당 step에 skills 추가 (필요 시)

### 4. 환경변수 의존 코드
- 새 환경변수 추가 시 `.env.example`에도 추가
- subprocess 실행 시 환경변수 전달 여부 확인
- SUPABASE_URL, SUPABASE_KEY, ELEVENLABS_API_KEY 등은 시작 시 검증

### 5. Node.js / npx 경로
- 이 머신의 Node.js 경로: `/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin`
- npx, node, npm 실행 전 반드시 PATH에 추가: `export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"`
- `python` → `python3`으로 사용 (시스템에 python 심볼릭 없음)

### 6. 서버 시작 시 .env 로드 필수
- uvicorn 등 서버 실행 전 반드시 `set -a; source .env; set +a` 실행
- 미로드 시 SUPABASE_URL 등 누락 → 500 Internal Server Error 발생

### 7. 경로 규칙
- 항상 `WORKSPACE_DIR` (읽기/쓰기) vs `PACKAGE_DIR` (읽기 전용) 구분
- 이미지/오디오 경로는 `resolveAsset()` 유틸 사용
- 절대경로/상대경로 혼용 금지

### 8. single_call (1턴) 모드 규칙
- CLI 호출 시 반드시 `--tools ""` 포함 (도구 비활성화) — 없으면 error_max_turns 발생
- 입력 파일이 50KB 이상이면 필요한 필드만 축약하여 전달
- 1턴 전용 프롬프트는 `auto_agent/data/prompts/single-call/` 에 관리
- 스킬 파일 통째 주입 금지 — 핵심 규칙만 인라인으로 집약
- 새 single_call 스텝 추가 시 `SINGLE_CALL_PROMPTS` 매핑 + 프롬프트 파일 + rule_store push 필요

### 9. mapScene 좌표 규칙
- scene_specs의 mapScene.center는 `[위도, 경도]` (LLM 자연 순서)
- Remotion/MapLibre는 `[경도, 위도]` — build_manifest.py가 swap 담당
- markers는 `{lat, lng}` → build_manifest가 `{coordinates: [lng, lat]}` 변환
- mapType 없으면 build_manifest가 `"location_reveal"` 기본값 설정
- camera.keyframes 없으면 build_manifest가 center/zoom에서 자동 생성
- **절대 프롬프트에서 [lng, lat] 순서를 강제하지 말 것** — LLM이 헷갈림

### 10. Remotion resolveLayout 규칙
- chartConfig는 `visualization` 레벨에 위치 (creative 안이 아님)
- resolveLayout에서 `data.chartConfig?.type`과 `creative.chartConfig?.type` 모두 체크
- 새 시각화 필드 추가 시 resolveLayout이 data/creative 어느 레벨에서 읽는지 확인 필수

### 11. 이미지 파일 삭제 절대 금지
- 이미지를 재생성/재검색할 때 **기존 이미지 파일을 절대 삭제하지 않는다**
- 새 이미지는 `_gen_02`, `_gen_03` 등 버전 번호로 생성
- `image_assets.json`에 새 버전 추가 + `selected` 필드만 전환
- `rm -f scene_*.png` 같은 명령 **절대 금지** — 이전 버전 복구 불가
- 이 규칙은 검색 이미지, 생성 이미지, 캐릭터 이미지 모두 해당

## 에러 볼트 워크플로우

에러를 해결할 때마다:
1. `~/Desktop/kairos-vault/08-dev/errors/` 에 에러 노트 생성 (tpl-error-fix 템플릿 사용)
2. 같은 유형의 에러가 3회 이상 반복되면 → 이 CLAUDE.md에 방지 규칙 추가
3. 스킬 관련 에러면 → 해당 SKILL.md에 가드레일 추가
