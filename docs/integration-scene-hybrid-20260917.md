# 씬 개선 · Claude/Codex 선택 실행 통합 검증

2026-09-17. 기존 작업 폴더의 미커밋 변경을 건드리지 않고 별도 worktree에서 통합했습니다.

## 범위

- 씬 브랜치 HEAD `56856bb`의 18개 고유 커밋과 main `a4fbb62`를 병합.
- 비디오 트랙 계약/resolver/Adobe 배치 코드는 main 그대로 보존.
- 사용자 승인에 따라 main 대비 남아 있던 `adobe/projects/` 자료 18개 삭제 포함. Git 이력에서 복구 가능하며 운영 워크스페이스의 원본 파일을 삭제하는 작업은 하지 않음.
- 미커밋 작업에서 공통 실행기, Claude/Codex 모델 라우팅, CLI 옵션, 기획/검수 적응형 반복, 해당 의존 파일과 테스트를 선별 반영.
- 별도 원고 스튜디오, LG 평가 개정, GPT 이미지 검수 변경, 서브모듈 등 나머지 미커밋 작업은 원래 작업 폴더에 보존. 이 PR에 전부 포함됐다고 간주하지 않음.

## 충돌 해결

- gitignore: 양쪽 스크립트/캐시 규칙을 유지. 옛 프로젝트 사본 삭제는 유지하되 폴더 전체 ignore는 제거하여 main의 작은 보관 기록 추적 정책과 산출물 검사를 보존.
- Adobe index: main의 스크립트 구성을 유지하고 저장소 pre-commit의 캐시버스터 갱신 사용.
- runner의 챕터 호출: Claude는 공통 정적 시스템 프롬프트 캐시 유지, Codex는 동일 지침을 stdin으로 전달. Codex 선택에서는 Claude 캐시 워밍 금지, Claude 워밍 모델은 선택된 모델 사용.
- Remotion은 소스 변경 없이 저장소 동기화 스크립트로 파생 파일 생성.

## 검증

Python 3.12, 실제 모델 호출 없이 mocked CLI 및 로컬 테스트 수행.

1. 공통 실행·라우팅·캐싱·v4 bridge·TTS parity: 86 passed.
2. Adobe 비디오 트랙·LLM 라우팅·CLI adapter·기획/원고 검수·manifest·timeline·Premiere·pipeline: 131 passed.
3. legacy gating·until·팩트체크·원고 gate·문체 분리·기획·Codex CLI·스킬 슬라이싱·토큰 최적화·산출물 가드·스토리보드·대시보드(아래 기존 실패 파일 제외): 138 passed.
4. `tests/dashboard/test_route_v4_context.py`: 3 failed, 1 passed. 별도 pristine main `a4fbb62`에서도 같은 세 테스트 실패 재현. 테스트 프로젝트 등록/DB 격리 및 404 문제이며 이번 통합의 신규 회귀로 판단하지 않음. 이 PR에서 무관한 대시보드 테스트를 수정하지 않음.
5. `auto-agent run --help`에서 provider/profile/model 옵션 확인.
6. Remotion mirror check, staged diff whitespace/conflict 검사 및 산출물 commit guard 수행.

통과 355개는 위 1~3의 합계이며 전체 테스트 스위트 통과를 뜻하지 않습니다.
Claude/Codex 실제 로그인/모델 접근, 유료 생성, 앱 GUI, Premiere/AE 호스트 및 실제 영상 렌더는 이번 통합에서 실행하지 않았습니다.

## 후속 작업

- 실행 방법과 미전환 독립 보조 모듈 범위는 `docs/hybrid-execution.md` 참고.
- 남은 원고 스튜디오/GPT 이미지 검수 등 로컬 변경은 별도 검토 후 반영.
- 원래 맥미니 작업 폴더의 브랜치와 미커밋 파일은 그대로 보존되어 있으므로, 원격 main 병합과 로컬 앱의 실행 코드 갱신을 구별할 것. dirty worktree에서 reset/강제 checkout 하지 말 것.
