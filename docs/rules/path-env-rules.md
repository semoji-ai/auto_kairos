# 경로 및 환경변수 규칙

## 경로
- 항상 `pathlib.Path` 사용 (문자열 결합 금지)
- 절대경로 하드코딩 금지 — `KAIROS_HOME` 또는 `get_workspace_dir()` 사용
- `get_workspace_dir()` fallback: `get_package_dir().parent` (CWD에 의존하지 않음)
- 크로스플랫폼: `os.name`, `platform.system()` 분기
- Windows backslash: ChromaDB 등에 전달 시 `str(path).replace("\\", "/")` 필수
- 프로젝트 경로: `project["output_dir"]`에서 직접 Path 생성 (slug 기반 경로 조합 금지 — uuid 접두사)

## 환경변수
- 새 환경변수 추가 시 `.env.example`에도 추가
- subprocess 실행 시 환경변수 전달 여부 확인
- `CLAUDECODE` 환경변수는 서브프로세스에서 pop 해야 함 (중첩 세션 방지)
- `AUTO_AGENT_DB` 환경변수 필수 (CWD에 따라 DB 못 찾음)

## Node.js / npx
- `NODEJS_BIN_DIR` 또는 `NODE_DIR` 환경변수로 설정
- 코드에서 하드코딩 금지 — `auto_agent/utils/platform.py`의 `find_node()` 사용

## 서버 시작 시
- .env 로드 필수
