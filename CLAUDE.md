# Project Rules

## Language
- 항상 한글로 답변할 것

## 협업 원칙
- **무조건 동의 금지** — 사용자의 제안보다 더 나은 방향이 있으면 반론을 제시할 것
- 기술적으로 후진적이거나 비효율적인 접근이 있으면 근거와 대안을 함께 제시
- 목표는 **기술적 진보** — 편한 방향이 아니라 최선의 방향을 추구
- 래칫 원칙 적용: 기존보다 명확히 우위인 방식만 채택, 아니면 현상 유지

## 파이프라인 구조 (3단계)

```
Stage 1: research-orchestrator → research_report.json
Stage 2: script-director → scene_specs.json + fact-verifier → factcheck_report.json
Stage 3: assembly-director → TTS + 이미지 + 자막 + 매니페스트 + 렌더링
```

## CLI 사용법 (auto-agent)

### 기본 흐름
```
auto-agent project create                    # 프로젝트 생성
auto-agent run --project <slug>              # 전체 파이프라인 실행
auto-agent run --project <slug> --from step_2  # Stage 2부터
auto-agent run --project <slug> --only step_1  # Stage 1만
auto-agent dashboard                          # 대시보드 (http://localhost:8080)
```

### 백그라운드 실행
```
auto-agent bg start --project <slug>           # 백그라운드 시작
auto-agent bg start --project <slug> --from step_2
auto-agent bg status --project <slug>          # 상태 확인
auto-agent bg logs --project <slug>            # 로그
auto-agent bg stop --project <slug>            # 중단
auto-agent bg list                             # 전체 세션
```

### 스텝 ID
| 스텝 | 이름 | 에이전트/모듈 |
|------|------|-------------|
| step_0 | environment_check | preflight (모듈) |
| step_1 | deep_research | research-orchestrator |
| step_2 | script_and_direct | script-director |
| step_2_data | data_mapping | data-mapper |
| step_2b | fact_check | fact-verifier (비차단) |
| step_3a | image_batch | image_batch_module (모듈) |
| step_3b | assembly | assembly-director |

### 프로젝트 설정
```
auto-agent config set --project <slug> art_style quirky_cartoon
auto-agent config set --project <slug> voice_id <id>
auto-agent config set --project <slug> writing_style iromism
auto-agent config set --project <slug> duration_minutes 2
```

### Claude Code 슬래시 스킬
```
/auto-kairos [주제]          # 전체 파이프라인
/kairos-research [slug]      # Stage 1 리서치
/kairos-write [slug]         # Stage 2 원고+연출
/kairos-product [slug]       # Stage 3 에셋조립
```

## API 사용 규칙
- Anthropic API 직접 호출은 사용자가 명시적으로 요청할 때만 사용
- 기본적으로 모든 에이전트/서브에이전트 실행은 **Claude CLI (`claude` 바이너리)** 우선

## 반복 에러 방지 규칙

### 1. Remotion 수정 시 반드시 양쪽 동기화
- `remotion/src/` 수정 → `auto_agent/remotion_template/src/`에도 반드시 동일 수정
- 대시보드 반영 시 `cd remotion && npx vite build --config vite.thumb.config.ts && npx vite build --config vite.editor.config.ts` 필수
- **절대 한쪽만 수정하고 끝내지 말 것**

### 1-1. 씬 렌더링 단일 소스 — SceneRenderer.tsx
- **모든 씬 렌더링은 `remotion/src/components/SceneRenderer.tsx`의 `SceneRendererInner`를 사용**
- 스토리보드(ThumbComposition), 스튜디오(SingleScenePlayer), 씬에디터(SceneEditorPanel), Remotion Studio(SimpleVideo) 4뷰 모두 동일 렌더러
- 이미지 배치(fullscreen/side/center/background), 배경 텍스처, placeholder 등 모든 분기가 SceneRenderer에 집중
- **CreativeScene은 순수 텍스트/데이터 렌더링만 담당** — 이미지 처리를 직접 하지 않음
- 레이아웃/이미지 수정 시 **SceneRenderer.tsx 한 곳만 수정** — ThumbComposition/SingleScenePlayer/SimpleVideo에 중복 코드 넣지 말 것

### 2. 새 파일 추가 시 패키지 데이터 체크
- 스킬(.md), 스크립트(.js), 아트스타일(.json) 등 새 파일 추가 시:
  1. `pyproject.toml` package-data에 포함되는지 확인
  2. `.gitignore`에 의해 제외되지 않는지 확인

### 3. 스킬 추가 시 체크리스트
- [ ] 스킬 .md 파일 생성 (`auto_agent/data/skills/shared/`)
- [ ] `agents.json` 해당 에이전트 shared_skills 배열에 추가
- [ ] `rule_manager.py` RULE_MANIFEST에 등록

### 4. 환경변수
- 새 환경변수 추가 시 `.env.example`에도 추가
- subprocess 실행 시 환경변수 전달 여부 확인

### 5. Node.js / npx 경로
- `NODEJS_BIN_DIR` 또는 `NODE_DIR` 환경변수로 설정
- 코드에서 하드코딩 금지 — `auto_agent/utils/platform.py`의 `find_node()` 사용

### 6. 서버 시작 시 .env 로드 필수
- 대시보드/파이프라인 실행 전 `.env` 로드 확인

### 7. 경로 규칙
- 항상 `pathlib.Path` 사용 (문자열 결합 금지)
- 절대경로 하드코딩 금지 — `KAIROS_HOME` 환경변수 또는 `get_workspace_dir()` 사용
- 크로스플랫폼: `os.name`, `platform.system()` 분기

### 8. mapScene 좌표 규칙
- scene_specs: `[위도, 경도]` (LLM 자연 순서)
- Remotion/MapLibre: `[경도, 위도]` — build_manifest.py가 swap 담당
- **절대 프롬프트에서 [lng, lat] 순서를 강제하지 말 것**

### 9. 이미지 파일 삭제 절대 금지
- 재생성/재검색 시 기존 파일 유지
- 새 이미지는 버전 번호로 생성 (`_gen_02`, `_gen_03`)
- `image_assets.json`의 `selected` 필드만 전환
- `rm -f scene_*.png` 같은 명령 **절대 금지**

### 10. Remotion 렌더러 규칙
- 씬 렌더링은 **CreativeScene** (`remotion/src/simple/CreativeScene.tsx`)만 수정
- 디자인 토큰은 `artstyle/styles/*.json`의 `design_tokens`에서 관리 (단일 소스)
- `remotion/src/design/presets/*.ts`는 artstyle JSON에서 import

### 11. 디자인 시스템
- 단일 소스: `auto_agent/data/artstyle/styles/<style>.json`의 `design_tokens`
- TypeScript: `resolvePreset.ts` → `DesignPresetProvider`
- Python: `helpers.py` → `_load_design_tokens()` → `get_mood_color()`
- 하드코딩 색상 금지 — 프리셋에서 읽을 것

### 12. scene_specs 플랫 스키마
- 모든 필드는 최상위 (layout, motion, mood, headline, items 등)
- `visualization.creative` 중첩 구조 사용하지 않음
- `imageAsset.prompt`로 장면 묘사 (한글), 아트스타일 키워드 넣지 않음
- `imageAsset.source`를 반드시 존중 (search/generate)

## 볼트 기억 시스템

NAS 볼트(`/Volumes/kairos/kairos_vault/kairos-vault/09-memory/`)에 세션 기억을 저장.

### 세션 시작 시 (필수)
```
볼트 09-memory/sessions/ 에서 최근 3개 세션 요약 읽기
→ 이전 작업 컨텍스트 복원
→ 미해결 문제 확인
```

### 세션 종료 시 (필수)
```
볼트 09-memory/sessions/{date}-{topic}.md 에 저장:
- 완료한 작업
- 미해결 문제
- 다음 우선순위
- 내린 설계 결정 (중요한 건 decisions/에도 별도 저장)
```

### 설계 결정 시
```
볼트 09-memory/decisions/{date}-{title}.md 에 기록:
- 결정 내용 + 근거 + 래칫 검증 결과 + 롤백 조건
```

## 에러 볼트 워크플로우

에러를 해결할 때마다:
1. `~/Desktop/kairos-vault/08-dev/errors/` 에 에러 노트 생성
2. 같은 유형의 에러가 3회 이상 반복되면 → 이 CLAUDE.md에 방지 규칙 추가
