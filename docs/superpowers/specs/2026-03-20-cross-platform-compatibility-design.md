# Cross-Platform Compatibility Design
Date: 2026-03-20

## Overview
현재 auto_kairos_v3 파이프라인이 macOS 개발자 로컬 환경에 하드코딩되어 있어 윈도우(네이티브/WSL) 및 다른 맥 머신에서 실행 불가. 플랫폼 유틸 레이어 도입 + 기존 코드 패치 + 설치 스크립트 자동화로 완전한 크로스플랫폼 호환성 달성.

## Goals
- macOS (x64 / arm64), Windows 네이티브, WSL 모두 지원
- 기존 파이프라인 동작 완전 유지 (기능 변경 없음)
- 팀원이 `install.sh` 또는 `install.ps1` 한 번 실행으로 셋업 완료
- Node.js 자동 탐색 (nvm, volta, brew, 시스템 설치 등)
- Python 3.11+ 강제, venv 자동 생성

## Non-Goals
- Docker 컨테이너화
- Node.js 번들 내장
- pyenv 자동 설치
- WSL에서 Windows 바이너리 혼용 (WSL에서는 Linux 바이너리만 사용)

---

## Architecture

### 핵심 접근: 플랫폼 유틸 레이어 (B안)

`auto_agent/utils/platform.py` 하나를 신규 생성하여 모든 플랫폼 로직의 단일 진실 공급원(single source of truth)으로 삼는다. 기존 코드의 하드코딩 부분을 이 유틸 함수로 교체.

---

## Components

### 1. `auto_agent/utils/platform.py` (신규)

모든 플랫폼 추상화를 담당하는 유틸 모듈.

**제공 함수:**
```python
get_node_bin_dir() -> Path
    # 탐색 순서:
    # 1. NODEJS_BIN_DIR 환경변수
    # 2. shutil.which("node") 로 node 위치 탐색
    # 3. nvm 경로 — ~/.nvm/alias/default 파일로 기본 버전 확인 → 없으면 최신 버전 선택
    #    (~/.nvm/versions/node/*/bin)
    # 4. volta 경로 (~/.volta/bin)
    # 5. brew 경로 (/opt/homebrew/bin, /usr/local/bin)
    # 6. 윈도우 시스템 경로 (C:/Program Files/nodejs, AppData/Roaming/nvm/*)
    # 7. 실패 시 명확한 에러 메시지 + 설치 안내
    #
    # 성능: @functools.lru_cache(maxsize=1) 으로 캐싱
    # — 렌더링 중 subprocess 반복 호출 시 매번 파일시스템 탐색 방지
    # — 테스트 시 get_node_bin_dir.cache_clear()로 캐시 리셋 가능 (테스트 독립성 보장)

get_npm_cmd() -> str        # "npm" / "npm.cmd"  (cli.py에서 사용)
get_npx_cmd() -> str        # "npx" / "npx.cmd"  (runner.py, scene_editor.py, layout_check.py 에서 사용)

get_env_with_node() -> dict
    # os.environ.copy() + PATH에 node_bin_dir 추가
    # PATH 구분자는 os.path.pathsep 자동 사용
    # os.environ 전역 수정 금지

get_python_cmd() -> str     # "python3" / "python"
path_sep() -> str           # os.path.pathsep

is_windows() -> bool
is_wsl() -> bool
    # /proc/version 읽기로 감지 (FileNotFoundError/PermissionError 시 False 반환)
    # try: return "microsoft" in Path("/proc/version").read_text().lower()
    # except (FileNotFoundError, PermissionError): return False
is_macos() -> bool
```

**핵심 원칙:**
- `os.environ` 전역 수정 절대 금지 — `get_env_with_node()` dict를 subprocess `env=` 파라미터로 전달
- `NODEJS_BIN_DIR` 환경변수로 팀원 수동 오버라이드 가능
- 탐색 실패 시 에러 메시지에 설치 링크 포함

---

### 2. 기존 코드 수정 (9개 파일)

**수정 원칙:**
- 한 파일 수정 → 해당 기능 동작 확인 → 다음 파일 순서로 진행
- 수정 전 원본 로직 주석 보존 (`# COMPAT: was ...`)
- 파이프라인 로직은 건드리지 않고 경로/명령어 부분만 교체

#### `app.py` (Critical)
```python
# Before (L126, L137) — 하드코딩된 버전 + os.environ 전역 수정
Path.home() / "local" / "nodejs" / "node-v22.14.0-darwin-x64" / "bin"  # 버전 고정
os.environ["PATH"] = f"{_np}{os.pathsep}{os.environ.get('PATH', '')}"   # 전역 수정

# After — 모듈 레벨 전역 수정 제거, get_env_with_node()로 교체
# app.py는 FastAPI 서버이므로 모듈 임포트 시점 전역 os.environ 수정이 특히 위험
# subprocess 호출 시 env=get_env_with_node() 전달로 대체
```
- 수정 위치: L126 (하드코딩 경로 목록), L137 (os.environ 전역 수정)

#### `auto_agent/orchestrator/runner.py` (Critical)
```python
# Before
node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"
os.environ["PATH"] = str(node_dir) + ":" + os.environ.get("PATH", "")

# After
from auto_agent.utils.platform import get_env_with_node, get_npx_cmd
env = get_env_with_node()
result = subprocess.run([get_npx_cmd(), ...], env=env, ...)
```
- L1661-1663: node_dir 하드코딩 + os.environ 전역 수정 → get_env_with_node() 교체
- L2459-2461: `subprocess.run(command, shell=True, ..., env=env)` 패턴 — env dict를 get_env_with_node()로 교체 (shell=True는 유지)
- os.environ 전역 수정 완전 제거

#### `auto_agent/dashboard/scene_editor.py` (Critical)
```python
# Before
node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"
env["PATH"] = f"{node_dir}:{env.get('PATH', '')}"

# After
from auto_agent.utils.platform import get_env_with_node, get_npx_cmd
env = get_env_with_node()
```
- 수정 위치: L154-156

#### `auto_agent/cli.py` (High)
```python
# Before
npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"

# After
from auto_agent.utils.platform import get_npm_cmd
npm_cmd = get_npm_cmd()
```
- subprocess.run에 `env=get_env_with_node()` 추가

#### `auto_agent/tools/remotion_bridge.py` (Critical)
```python
# Before — 독자적인 Node.js 탐색 로직 (platform.py와 별개로 동작)
def _find_node_bin_dir(self) -> Optional[str]:
    ...  # 하드코딩 경로 탐색, shutil.which 폴백 없음

# After — platform.get_node_bin_dir() 사용으로 통일
# 1. _find_node_bin_dir() 삭제
# 2. __init__에서: self._node_bin_dir = str(get_node_bin_dir())
# 3. _find_bin(), _find_local_bin()은 self._node_bin_dir에 의존하므로 그대로 유지
#    (self._node_bin_dir이 올바른 값이 되면 자동으로 동작)
# 4. subprocess 호출 시 env=get_env_with_node() 전달
```

#### `auto_agent/scripts/layout_check.py` (Critical)
```python
# Before — npx 하드코딩 (Windows에서 즉시 실패)
["npx", "remotion", "still", ...]

# After
from auto_agent.utils.platform import get_npx_cmd, get_env_with_node
subprocess.run([get_npx_cmd(), "remotion", "still", ...], env=get_env_with_node(), ...)
```

#### `auto_agent/orchestrator/vault_rag.py` (Medium)
```python
# Before
VAULT_DIR = Path(os.environ.get("KAIROS_VAULT_DIR", os.path.expanduser("~/Projects/kairos-vault")))

# After — 기존 enabled=False fallback 유지 (볼트는 선택적 기능)
# EnvironmentError로 바꾸면 볼트 없는 환경에서 파이프라인 전체 중단 → Breaking Change
# 기본 경로 하드코딩만 제거하고, 미설정 시 경고 메시지 출력 + enabled=False 유지
VAULT_DIR_ENV = os.environ.get("KAIROS_VAULT_DIR")
if not VAULT_DIR_ENV:
    logger.warning("KAIROS_VAULT_DIR 미설정 — vault RAG 비활성화. .env.example 참조")
    # enabled = False 로 조용히 비활성화 (기존 동작 유지)
else:
    VAULT_DIR = Path(VAULT_DIR_ENV).expanduser()
```

#### `start_dashboard.sh` / `start_pipeline.sh` (Medium)
- `export PATH="/Users/hannah/local/nodejs/..."` 라인 제거
- Node.js 경로는 Python 코드 내부에서 `get_env_with_node()`로 처리

#### `.env.example` (Medium)
```dotenv
# Node.js 자동 탐색 실패 시에만 설정 (보통 불필요)
# NODEJS_BIN_DIR=/path/to/node/bin

# 팀원 각자 설정 필요
KAIROS_VAULT_DIR=~/Projects/kairos-vault
```

---

### 3. 설치 스크립트

#### `install.sh` (macOS / Linux / WSL) — 기존 개선

**실행 흐름:**
1. OS 감지 (macOS / Linux / WSL) — `/proc/version` 으로 WSL 감지
2. CPU 아키텍처 감지 (`uname -m` → x64 / arm64)
3. Python 3.11+ 확인 → 없으면 설치 링크 안내 후 중단
4. Node.js 탐색 (`which node` → nvm → volta → brew → 시스템)
   - 없으면 플랫폼별 설치 안내 후 중단
5. `.venv` 생성 → `pip install -e .`
6. `.env` 없으면 `.env.example` 복사 + `KAIROS_VAULT_DIR` 대화형 입력
7. `remotion_template` npm install
8. 완료 메시지 + 다음 단계 안내

**멱등성:** 이미 설치된 경우 각 단계 스킵. 여러 번 실행해도 안전.

#### `install.ps1` (Windows 네이티브) — 신규 작성

**실행 흐름:**
1. PowerShell 버전 확인 (5.1+ 또는 Core 7+)
2. Python 3.11+ 확인 (`python` / `py` 명령 시도)
   - 없으면 `winget install Python.Python.3.11` 안내
3. Node.js 탐색 (`where node` → nvm-windows → volta → Chocolatey → Scoop)
   - 없으면 `winget install OpenJS.NodeJS` 안내
4. `.venv` 생성 → `pip install -e .`
5. `.env` 없으면 `.env.example` 복사 + `KAIROS_VAULT_DIR` 입력 받기
6. `remotion_template` npm install
7. 완료 메시지

---

## Data Flow: Node.js 경로 처리

```
[subprocess 호출 전]
  get_env_with_node()
    ├─ NODEJS_BIN_DIR 환경변수 있으면 → 그 경로 사용
    ├─ shutil.which("node") 성공 → 부모 디렉토리 사용
    ├─ nvm/volta/brew 경로 탐색 → 발견한 경로 사용
    └─ 실패 → EnvironmentError (설치 안내 메시지 포함)

  반환: os.environ.copy() + PATH에 node_bin_dir 추가
    (구분자: os.path.pathsep 자동 — ":" macOS/Linux, ";" Windows)

[subprocess.run 호출]
  subprocess.run([get_npx_cmd(), ...], env=get_env_with_node(), ...)
```

---

## Testing Strategy

### 사전 조건
- `tests/` 디렉토리가 없으면 신규 생성

### 단위 테스트: `tests/test_platform.py`
```python
test_get_node_bin_dir_found()              # node 탐색 성공
test_get_node_bin_dir_not_found()          # 없으면 EnvironmentError
test_get_node_bin_dir_env_override()       # NODEJS_BIN_DIR 환경변수 우선
test_get_node_bin_dir_caching()            # 두 번 호출해도 파일시스템 탐색 1회만
test_get_env_with_node_path_contains_node()  # env에 node 경로 포함
test_get_env_with_node_no_global_mutation()  # os.environ 전역 수정 없음
test_path_sep_correct()                    # 플랫폼별 구분자
test_npm_cmd_correct()                     # 플랫폼별 명령어 (npm.cmd / npm)
test_is_wsl_no_proc_version()              # /proc/version 없어도 False 반환
test_is_windows_macos_wsl()                # 플랫폼 감지
```

### 기능별 통합 테스트 (파일 수정 후 각각 확인)
- [ ] `node --version` 실행 가능
- [ ] `npx remotion render` 실행 가능 (runner.py 수정 후)
- [ ] 씬 에디터 빌드 성공 (scene_editor.py 수정 후)
- [ ] `npm install` remotion_template 성공 (cli.py 수정 후)
- [ ] 썸네일 생성 성공 (runner.py + remotion_bridge.py 수정 후)
- [ ] layout_check.py 실행 성공 (layout_check.py 수정 후)

### 회귀 체크리스트 (전체 수정 완료 후)
- [ ] 전체 파이프라인 smoke test (실제 영상 1개 생성)
- [ ] 대시보드 씬 에디터 정상 동작
- [ ] `install.sh` 신규 머신 환경에서 실행 테스트
- [ ] `install.ps1` 윈도우 환경에서 실행 테스트

---

## Error Handling

| 상황 | 처리 |
|------|------|
| Node.js 탐색 실패 | `EnvironmentError` + 플랫폼별 설치 안내 |
| KAIROS_VAULT_DIR 미설정 | 경고 로그 출력 + `enabled=False` (볼트는 선택적 기능, 파이프라인 중단 없음) |
| Python 3.11 미만 | install 스크립트에서 중단 + 업그레이드 안내 |
| npm install 실패 | subprocess 에러 그대로 전파 (기존 동작 유지) |

---

## Rollback Plan
- 수정 전 각 파일 원본 로직 주석 보존 (`# COMPAT: was ...`)
- 기능별로 커밋 분리하여 파이프라인 깨지면 즉시 revert 가능
- `platform.py`는 새 파일이므로 기존 코드에 영향 없음

---

## Files Changed Summary

| 파일 | 변경 유형 | 우선순위 |
|------|-----------|---------|
| `auto_agent/utils/platform.py` | 신규 생성 | Critical |
| `tests/test_platform.py` | 신규 생성 | Critical |
| `app.py` | os.environ 전역 수정 제거, 하드코딩 경로 제거 | Critical |
| `auto_agent/orchestrator/runner.py` | 경로 교체 | Critical |
| `auto_agent/dashboard/scene_editor.py` | 경로 교체 | Critical |
| `auto_agent/tools/remotion_bridge.py` | 독자 탐색 로직 → platform.py 통일 | Critical |
| `auto_agent/scripts/layout_check.py` | npx 하드코딩 → get_npx_cmd() | Critical |
| `auto_agent/cli.py` | 명령어 교체 | High |
| `auto_agent/orchestrator/vault_rag.py` | 기본 경로 제거 + 경고 메시지 (enabled=False 유지) | Medium |
| `start_dashboard.sh` | PATH 하드코딩 제거 | Medium |
| `start_pipeline.sh` | PATH 하드코딩 제거 | Medium |
| `.env.example` | NODEJS_BIN_DIR 항목 추가 | Medium |
| `install.sh` | 플랫폼 감지 강화, Node 탐색, npm install 추가 | High |
| `install.ps1` | 신규 작성 (Windows 지원, remotion npm install 포함) | High |
