# Cross-Platform Compatibility Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** auto_kairos_v3 파이프라인이 macOS(x64/arm64), Windows 네이티브, WSL에서 Node.js 경로 자동 탐색으로 완전히 동작하게 한다.

**Architecture:** `auto_agent/utils/platform.py`를 단일 진실 공급원으로 신규 생성하여 Node.js 탐색, 명령어 해석, 환경변수 처리를 중앙화한다. 기존 파일의 하드코딩 경로와 `os.environ` 전역 수정을 이 유틸로 교체한다.

**Tech Stack:** Python 3.11+, `functools.lru_cache`, `shutil.which`, `pathlib.Path`, pytest, bash, PowerShell

**Spec:** `docs/superpowers/specs/2026-03-20-cross-platform-compatibility-design.md`

---

## File Map

| 파일 | 역할 |
|------|------|
| `auto_agent/utils/__init__.py` | 신규 — utils 패키지 |
| `auto_agent/utils/platform.py` | 신규 — 모든 플랫폼 로직의 단일 진실 공급원 |
| `tests/__init__.py` | 신규 — tests 패키지 |
| `tests/test_platform.py` | 신규 — platform.py 단위 테스트 |
| `app.py` | 수정 — L119-138 전역 PATH 주입 제거, npm/npx 호출에 platform 유틸 적용 |
| `auto_agent/orchestrator/runner.py` | 수정 — L1661-1664(os.environ), L2459-2461(PATH 구분자) |
| `auto_agent/dashboard/scene_editor.py` | 수정 — L152-157 os.environ 전역 수정 제거 |
| `auto_agent/tools/remotion_bridge.py` | 수정 — `_find_node_bin_dir()` 삭제 → `get_node_bin_dir()` |
| `auto_agent/scripts/layout_check.py` | 수정 — `"npx"` 하드코딩 → `get_npx_cmd()` |
| `auto_agent/cli.py` | 수정 — npm/npx 명령어 + env 전달 |
| `auto_agent/orchestrator/vault_rag.py` | 수정 — 하드코딩 기본 경로 제거 + 경고 |
| `start_dashboard.sh` | 수정 — PATH 하드코딩 제거 |
| `start_pipeline.sh` | 수정 — PATH 하드코딩 제거 |
| `.env.example` | 신규 — NODEJS_BIN_DIR, KAIROS_VAULT_DIR 예시 |
| `install.sh` | 수정 — 플랫폼 감지 강화, Node.js 탐색, npm install 추가 |
| `install.ps1` | 수정 — remotion npm install 단계 추가 |

---

## Chunk 1: platform.py 기반 구축 (TDD)

### Task 1: tests 패키지 및 failing 테스트 작성

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/test_platform.py`

- [ ] **Step 1: tests 디렉토리와 __init__.py 생성**

```bash
mkdir -p /Users/hannah/Projects/auto_kairos_v3/tests
touch /Users/hannah/Projects/auto_kairos_v3/tests/__init__.py
```

- [ ] **Step 2: test_platform.py 작성 (모두 failing 상태)**

```python
# tests/test_platform.py
"""platform.py 단위 테스트 — platform.py 작성 전에 먼저 작성"""
import os
import sys
from pathlib import Path
from unittest import mock

import pytest


def _clear():
    """lru_cache 리셋 헬퍼"""
    try:
        from auto_agent.utils.platform import get_node_bin_dir
        get_node_bin_dir.cache_clear()
    except Exception:
        pass


def test_get_node_bin_dir_env_override(tmp_path, monkeypatch):
    """NODEJS_BIN_DIR 환경변수가 있으면 그 경로를 반환"""
    _clear()
    fake_bin = tmp_path / "mynode" / "bin"
    fake_bin.mkdir(parents=True)
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()

    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()

    from auto_agent.utils.platform import get_node_bin_dir
    result = get_node_bin_dir()
    assert result == fake_bin
    _clear()


def test_get_node_bin_dir_found():
    """현재 환경에서 node 탐색 성공"""
    import shutil
    if not shutil.which("node"):
        pytest.skip("node가 설치되지 않은 환경 — 탐색 불가")
    _clear()
    from auto_agent.utils.platform import get_node_bin_dir
    result = get_node_bin_dir()
    assert result.exists()
    _clear()


def test_get_node_bin_dir_not_found(monkeypatch):
    """node 찾지 못하면 EnvironmentError"""
    _clear()
    monkeypatch.delenv("NODEJS_BIN_DIR", raising=False)

    with mock.patch("shutil.which", return_value=None), \
         mock.patch("pathlib.Path.exists", return_value=False), \
         mock.patch("pathlib.Path.iterdir", side_effect=FileNotFoundError):
        from auto_agent.utils.platform import get_node_bin_dir
        _clear()
        with pytest.raises(EnvironmentError, match="Node.js를 찾을 수 없습니다"):
            get_node_bin_dir()
    _clear()


def test_get_node_bin_dir_caching(tmp_path, monkeypatch):
    """lru_cache로 두 번 호출해도 함수 본체는 1회만 실행"""
    _clear()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()
    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()

    from auto_agent.utils.platform import get_node_bin_dir
    r1 = get_node_bin_dir()
    r2 = get_node_bin_dir()
    assert r1 == r2
    info = get_node_bin_dir.cache_info()
    assert info.hits >= 1  # 두 번째 호출은 캐시에서
    _clear()


def test_get_env_with_node_path_contains_node(tmp_path, monkeypatch):
    """get_env_with_node()의 PATH에 node bin 경로 포함"""
    _clear()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()
    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()

    from auto_agent.utils.platform import get_env_with_node
    env = get_env_with_node()
    assert str(fake_bin) in env["PATH"]
    _clear()


def test_get_env_with_node_no_global_mutation(tmp_path, monkeypatch):
    """get_env_with_node()는 os.environ을 수정하지 않음"""
    _clear()
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()
    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()

    original_path = os.environ.get("PATH", "")
    from auto_agent.utils.platform import get_env_with_node
    get_env_with_node()
    assert os.environ.get("PATH", "") == original_path
    _clear()


def test_get_env_with_node_uses_pathsep(tmp_path, monkeypatch):
    """PATH 구분자로 os.path.pathsep 사용"""
    import inspect
    from auto_agent.utils import platform as p
    src = inspect.getsource(p.get_env_with_node)
    assert "os.path.pathsep" in src


def test_npm_cmd_correct():
    """npm 명령어: Windows면 npm.cmd, 아니면 npm"""
    from auto_agent.utils.platform import get_npm_cmd
    result = get_npm_cmd()
    if sys.platform == "win32":
        assert result == "npm.cmd"
    else:
        assert result == "npm"


def test_npx_cmd_correct():
    """npx 명령어: Windows면 npx.cmd, 아니면 npx"""
    from auto_agent.utils.platform import get_npx_cmd
    result = get_npx_cmd()
    if sys.platform == "win32":
        assert result == "npx.cmd"
    else:
        assert result == "npx"


def test_is_wsl_no_proc_version():
    """/proc/version 없어도 is_wsl()이 False를 반환 (예외 전파 안 함)"""
    from auto_agent.utils.platform import is_wsl
    with mock.patch("pathlib.Path.read_text", side_effect=FileNotFoundError):
        result = is_wsl()
    assert isinstance(result, bool)


def test_platform_flags_are_bool():
    """is_windows, is_macos, is_wsl 모두 bool 반환"""
    from auto_agent.utils.platform import is_windows, is_macos, is_wsl
    assert isinstance(is_windows(), bool)
    assert isinstance(is_macos(), bool)
    assert isinstance(is_wsl(), bool)
    # 플랫폼은 동시에 둘 이상이면 안 됨
    assert sum([is_windows(), is_macos(), is_wsl()]) <= 1
```

- [ ] **Step 3: 테스트 실행 — 모두 실패해야 정상**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
source .venv/bin/activate
pytest tests/test_platform.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'auto_agent.utils.platform'`

---

### Task 2: platform.py 구현

**Files:**
- Create: `auto_agent/utils/__init__.py`
- Create: `auto_agent/utils/platform.py`

- [ ] **Step 1: utils 패키지 생성**

```bash
touch /Users/hannah/Projects/auto_kairos_v3/auto_agent/utils/__init__.py
```

- [ ] **Step 2: platform.py 작성**

```python
# auto_agent/utils/platform.py
"""
플랫폼 추상화 유틸 — Node.js 탐색, 명령어, PATH 처리

사용법:
    from auto_agent.utils.platform import get_env_with_node, get_npx_cmd
    subprocess.run([get_npx_cmd(), ...], env=get_env_with_node(), ...)

주의: os.environ을 직접 수정하지 않음.
      subprocess 호출 시 env=get_env_with_node() 로 전달할 것.
"""
import functools
import os
import shutil
import sys
from pathlib import Path
from typing import Optional


# ─── 플랫폼 감지 ───────────────────────────────────────────────────────────────

def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_wsl() -> bool:
    """/proc/version에서 'microsoft' 문자열로 WSL 감지. 파일 없으면 False."""
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except (FileNotFoundError, PermissionError):
        return False


# ─── Node.js 탐색 ──────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def get_node_bin_dir() -> Path:
    """
    Node.js 바이너리 디렉토리를 탐색하여 반환.

    탐색 순서:
        1. NODEJS_BIN_DIR 환경변수 (팀원 수동 오버라이드)
        2. shutil.which("node") → 부모 디렉토리
        3. nvm — ~/.nvm/alias/default → 버전 디렉토리, 없으면 최신 버전
        4. volta — ~/.volta/bin
        5. brew — /opt/homebrew/bin, /usr/local/bin
        6. Windows 시스템 경로 — C:/Program Files/nodejs, AppData nvm-windows

    Returns:
        Path: node 바이너리가 있는 디렉토리

    Raises:
        EnvironmentError: Node.js를 찾을 수 없을 때 (설치 안내 포함)

    Note:
        @lru_cache(maxsize=1) — 첫 탐색 결과를 캐싱.
        테스트에서는 get_node_bin_dir.cache_clear()로 리셋할 것.
    """
    node_exe = "node.exe" if is_windows() else "node"

    # 1. 환경변수 오버라이드
    env_override = os.environ.get("NODEJS_BIN_DIR")
    if env_override:
        p = Path(env_override)
        if (p / node_exe).exists():
            return p

    # 2. shutil.which
    node_path = shutil.which(node_exe)
    if node_path:
        return Path(node_path).parent

    # 3. nvm
    nvm_alias = Path.home() / ".nvm" / "alias" / "default"
    if nvm_alias.exists():
        try:
            default_ver = nvm_alias.read_text().strip()
            nvm_bin = Path.home() / ".nvm" / "versions" / "node" / default_ver / "bin"
            if (nvm_bin / node_exe).exists():
                return nvm_bin
        except OSError:
            pass
    nvm_versions = Path.home() / ".nvm" / "versions" / "node"
    if nvm_versions.exists():
        try:
            for ver_dir in sorted(nvm_versions.iterdir(), reverse=True):
                bin_dir = ver_dir / "bin"
                if (bin_dir / node_exe).exists():
                    return bin_dir
        except OSError:
            pass

    # 4. volta
    volta_bin = Path.home() / ".volta" / "bin"
    if (volta_bin / node_exe).exists():
        return volta_bin

    # 5. brew
    for brew_path in [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]:
        if (brew_path / node_exe).exists():
            return brew_path

    # 6. Windows 시스템 경로
    if is_windows():
        candidates = [
            Path("C:/Program Files/nodejs"),
            Path("C:/Program Files (x86)/nodejs"),
        ]
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / "nvm")
        for win_path in candidates:
            if win_path.exists() and (win_path / node_exe).exists():
                return win_path

    raise EnvironmentError(
        "Node.js를 찾을 수 없습니다.\n"
        "  macOS:   brew install node  또는  https://nodejs.org\n"
        "  Windows: winget install OpenJS.NodeJS  또는  https://nodejs.org\n"
        "  수동 지정: NODEJS_BIN_DIR=/path/to/node/bin  (.env에 추가)"
    )


def get_npm_cmd() -> str:
    """npm 실행 명령어 (Windows: npm.cmd)"""
    return "npm.cmd" if is_windows() else "npm"


def get_npx_cmd() -> str:
    """npx 실행 명령어 (Windows: npx.cmd)"""
    return "npx.cmd" if is_windows() else "npx"


def get_python_cmd() -> str:
    """Python 실행 명령어 (python3 우선)"""
    return shutil.which("python3") or shutil.which("python") or "python3"


def get_env_with_node() -> dict:
    """
    os.environ.copy() + PATH에 Node.js 바이너리 경로 추가한 dict 반환.
    os.environ을 직접 수정하지 않습니다.

    Returns:
        dict: subprocess env= 파라미터에 전달할 환경변수 dict

    Raises:
        EnvironmentError: get_node_bin_dir()에서 Node.js 못 찾을 때
    """
    env = os.environ.copy()
    node_bin = str(get_node_bin_dir())
    current_path = env.get("PATH", "")
    if node_bin not in current_path:
        env["PATH"] = node_bin + os.path.pathsep + current_path
    return env
```

- [ ] **Step 3: 테스트 실행 — 모두 통과해야 함**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
pytest tests/test_platform.py -v
```

Expected: 전체 PASS. `test_get_node_bin_dir_found`는 node 설치된 환경에서 PASS, 없으면 SKIP.

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/utils/__init__.py auto_agent/utils/platform.py tests/__init__.py tests/test_platform.py
git commit -m "feat: add platform.py util — cross-platform Node.js detection"
```

---

## Chunk 2: Critical 파일 수정 — app.py, runner.py, scene_editor.py

### Task 3: app.py — 모듈 레벨 전역 PATH 수정 제거

**Files:**
- Modify: `app.py` L119-138, L1354-1365, L1399-1410

**수정 전 확인:**
```bash
grep -n "node_candidates\|os.environ\[.PATH\]\|npm_cmd\|npx_cmd" app.py
```

- [ ] **Step 1: L119-138 블록 제거 및 platform import 추가**

L119-138 (Node.js PATH 보장 블록) 전체를 다음으로 교체:

```python
# Node.js 경로는 subprocess 호출 시 platform.get_env_with_node()로 주입
# (os.environ 전역 수정 제거 — COMPAT: was _node_candidates loop)
from auto_agent.utils.platform import get_env_with_node as _get_node_env
from auto_agent.utils.platform import get_npm_cmd as _get_npm_cmd
from auto_agent.utils.platform import get_npx_cmd as _get_npx_cmd
```

- [ ] **Step 2: L1354-1365 npm install 호출 수정**

```python
# Before:
npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"
npm_cmd = "npm.cmd" if IS_WINDOWS else "npm"
if not _find_cmd(npm_cmd):
    ...
    result = subprocess.run(
        [npm_cmd, "install"],
        cwd=str(REMOTION_DIR),
        capture_output=True, text=True, timeout=120,
    )

# After:
npm_cmd = _get_npm_cmd()
if not _find_cmd(npm_cmd):
    ...
    result = subprocess.run(
        [npm_cmd, "install"],
        cwd=str(REMOTION_DIR),
        env=_get_node_env(),
        capture_output=True, text=True, timeout=120,
    )
```

- [ ] **Step 3: L1399-1410 Remotion Studio 시작 수정**

```python
# Before:
npx_cmd = "npx.cmd" if IS_WINDOWS else "npx"
...
env = os.environ.copy()
env["BROWSER"] = "none"
_studio_proc = subprocess.Popen(
    [npx_cmd, "remotion", "studio", "--port", str(STUDIO_PORT)],
    ...
    env=env,
    ...
)

# After:
npx_cmd = _get_npx_cmd()
...
env = _get_node_env()
env["BROWSER"] = "none"
_studio_proc = subprocess.Popen(
    [npx_cmd, "remotion", "studio", "--port", str(STUDIO_PORT)],
    ...
    env=env,
    ...
)
```

- [ ] **Step 4: 동작 확인 — import 에러 없는지 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
source .venv/bin/activate
python -c "import app; print('app.py import OK')"
```

Expected: `app.py import OK`

- [ ] **Step 5: 커밋**

```bash
git add app.py
git commit -m "fix: remove global os.environ PATH mutation in app.py"
```

---

### Task 4: runner.py — 하드코딩 경로 + os.environ 전역 수정 제거

**Files:**
- Modify: `auto_agent/orchestrator/runner.py` L1659-1667, L2458-2461

- [ ] **Step 1: L1659-1699 썸네일 캡처 블록 전체 수정**

```python
# Before (L1659-1699):
node = shutil.which("node")
if not node:
    node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"
    if node_dir.exists():
        os.environ["PATH"] = str(node_dir) + ":" + os.environ.get("PATH", "")  # COMPAT: was this
        node = shutil.which("node")
if not node:
    print("    [SKIP] Node.js 없음 — 썸네일 캡처 스킵")
    return
...
result = subprocess.run(
    [node, str(script), str(manifest_path), str(self.project_dir), "--width=480"],
    cwd=str(script.parent),
    capture_output=True, text=True,
    timeout=300,
)

# After:
from auto_agent.utils.platform import get_node_bin_dir, get_env_with_node
try:
    _node_bin = get_node_bin_dir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    node = str(_node_bin / node_exe)
    _node_env = get_env_with_node()
except EnvironmentError:
    print("    [SKIP] Node.js 없음 — 썸네일 캡처 스킵")
    return
...
result = subprocess.run(
    [node, str(script), str(manifest_path), str(self.project_dir), "--width=480"],
    cwd=str(script.parent),
    env=_node_env,          # <-- 추가: node 경로 포함된 env 전달
    capture_output=True, text=True,
    timeout=300,
)
```

- [ ] **Step 2: L2458-2461 render_step의 env PATH 수정**

```python
# Before (L2458-2461):
# Node.js PATH 보장 (npx, node 등)
node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"
if node_dir.exists() and str(node_dir) not in env.get("PATH", ""):
    env["PATH"] = f"{node_dir}:{env.get('PATH', '')}"  # COMPAT: was this (: 구분자 하드코딩)

# After:
# Node.js PATH 보장 (platform 유틸 사용)
try:
    from auto_agent.utils.platform import get_node_bin_dir
    _node_bin = str(get_node_bin_dir())
    if _node_bin not in env.get("PATH", ""):
        import os as _os
        env["PATH"] = _node_bin + _os.path.pathsep + env.get("PATH", "")
except EnvironmentError:
    pass  # PATH에 이미 node가 있으면 그대로 진행
```

- [ ] **Step 3: runner.py 관련 기능 동작 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
python -c "from auto_agent.orchestrator.runner import Runner; print('runner.py import OK')"
```

Expected: `runner.py import OK`

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "fix: replace hardcoded node path in runner.py with platform util"
```

---

### Task 5: scene_editor.py — os.environ 전역 수정 제거

**Files:**
- Modify: `auto_agent/dashboard/scene_editor.py` L150-157

- [ ] **Step 1: L150-157 블록 수정**

```python
# Before (L150-157):
node = shutil.which("node")
if not node:
    # PATH에 node 추가 시도
    node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"  # COMPAT: was this
    if node_dir.exists():
        os.environ["PATH"] = str(node_dir) + ":" + os.environ.get("PATH", "")  # COMPAT: was this
        node = shutil.which("node")
if not node:
    return

# After:
from auto_agent.utils.platform import get_node_bin_dir, get_env_with_node
try:
    _node_bin = get_node_bin_dir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    node = str(_node_bin / node_exe)
except EnvironmentError:
    return
```

- [ ] **Step 2: L165-172 asyncio.create_subprocess_exec 호출 수정**

```python
# Before (L165-172):
proc = await asyncio.create_subprocess_exec(
    node, str(script), str(manifest_path), output_dir,
    "--width=480",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env={**os.environ},      # COMPAT: was this — node 경로 미포함
    cwd=str(script.parent),
)

# After:
proc = await asyncio.create_subprocess_exec(
    node, str(script), str(manifest_path), output_dir,
    "--width=480",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=_node_env,           # get_env_with_node() 결과 (Step 1에서 설정)
    cwd=str(script.parent),
)
```

- [ ] **Step 3: scene_editor 동작 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
python -c "from auto_agent.dashboard.scene_editor import *; print('scene_editor.py import OK')"
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/dashboard/scene_editor.py
git commit -m "fix: replace hardcoded node path in scene_editor.py"
```

---

## Chunk 3: Critical 파일 수정 — remotion_bridge.py, layout_check.py

### Task 6: remotion_bridge.py — 독자 탐색 로직 제거

**Files:**
- Modify: `auto_agent/tools/remotion_bridge.py` L72-106

**수정 전 읽기:**

```bash
sed -n '55,110p' auto_agent/tools/remotion_bridge.py
```

- [ ] **Step 1: __init__ 에서 node_bin_dir 초기화 교체**

```python
# Before (L72):
self._node_bin_dir = self._find_node_bin_dir()

# After:
from auto_agent.utils.platform import get_node_bin_dir, get_env_with_node
try:
    self._node_bin_dir = str(get_node_bin_dir())
except EnvironmentError:
    self._node_bin_dir = None
```

- [ ] **Step 2: _find_node_bin_dir() 메서드 삭제**

L77-85의 `_find_node_bin_dir` 메서드 전체 삭제.

- [ ] **Step 3: _get_node_env() 메서드 교체**

```python
# Before (L102-106):
def _get_node_env(self) -> dict:
    env = dict(os.environ)
    if self._node_bin_dir:
        env["PATH"] = self._node_bin_dir + ":" + env.get("PATH", "")  # COMPAT: was ":"
    return env

# After:
def _get_node_env(self) -> dict:
    from auto_agent.utils.platform import get_env_with_node
    try:
        return get_env_with_node()
    except EnvironmentError:
        return dict(os.environ)
```

- [ ] **Step 4: _find_bin() 메서드 동작 확인**

`_find_bin()`은 `self._node_bin_dir`에 의존. 두 가지 경우:
- `get_node_bin_dir()` 성공 → `self._node_bin_dir = str(Path)` → `_find_bin()`이 그 경로에서 바이너리 탐색
- `EnvironmentError` → `self._node_bin_dir = None` → `_find_bin()`이 `shutil.which()`로 폴백 (기존 동작 유지)

이 흐름은 의도적. `_find_bin()` 메서드 수정 불필요.

- [ ] **Step 5: 동작 확인**

```bash
python -c "from auto_agent.tools.remotion_bridge import RemotionBridge; print('remotion_bridge.py import OK')"
```

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/tools/remotion_bridge.py
git commit -m "fix: replace _find_node_bin_dir() with platform.get_node_bin_dir() in remotion_bridge"
```

---

### Task 7: layout_check.py — npx 하드코딩 제거

**Files:**
- Modify: `auto_agent/scripts/layout_check.py` L86-100

- [ ] **Step 1: render_still 함수 수정**

```python
# Before (L86-100):
cmd = [
    "npx", "remotion", "still",   # COMPAT: was "npx" hardcoded
    "SimpleVideo",
    output_path,
    f"--frame={frame}",
    "--overwrite",
]
try:
    result = subprocess.run(
        cmd,
        cwd=remotion_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )

# After:
from auto_agent.utils.platform import get_npx_cmd, get_env_with_node
cmd = [
    get_npx_cmd(), "remotion", "still",
    "SimpleVideo",
    output_path,
    f"--frame={frame}",
    "--overwrite",
]
try:
    result = subprocess.run(
        cmd,
        cwd=remotion_dir,
        env=get_env_with_node(),
        capture_output=True,
        text=True,
        timeout=120,
    )
```

- [ ] **Step 2: 동작 확인**

```bash
python -c "from auto_agent.scripts.layout_check import render_still; print('layout_check.py import OK')"
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/scripts/layout_check.py
git commit -m "fix: replace hardcoded npx in layout_check.py"
```

---

## Chunk 4: High/Medium 파일 수정

### Task 8: cli.py — npm/npx 명령어 + env 전달

**Files:**
- Modify: `auto_agent/cli.py` L178-193, L256-263

- [ ] **Step 1: npm install 블록 수정 (L178-193)**

```python
# Before (L178-193):
import platform
npm_cmd = "npm.cmd" if platform.system() == "Windows" else "npm"   # COMPAT: was this
result = subprocess.run(
    [npm_cmd, "install"],
    cwd=str(remotion_dest),
    capture_output=True,
    text=True,
)

# After:
from auto_agent.utils.platform import get_npm_cmd, get_env_with_node
npm_cmd = get_npm_cmd()
result = subprocess.run(
    [npm_cmd, "install"],
    cwd=str(remotion_dest),
    env=get_env_with_node(),
    capture_output=True,
    text=True,
)
```

- [ ] **Step 2: remotion studio 실행 블록 수정 (L256-263)**

```python
# Before (L256-263):
import platform
npx_cmd = "npx.cmd" if platform.system() == "Windows" else "npx"  # COMPAT: was this
subprocess.run(
    [npx_cmd, "remotion", "studio"],
    cwd=str(remotion_dir),
    env={**__import__("os").environ, **env},
)

# After:
from auto_agent.utils.platform import get_npx_cmd, get_env_with_node
npx_cmd = get_npx_cmd()
node_env = get_env_with_node()
node_env.update(env)   # 기존 env 오버레이 유지
subprocess.run(
    [npx_cmd, "remotion", "studio"],
    cwd=str(remotion_dir),
    env=node_env,
)
```

- [ ] **Step 3: 동작 확인**

```bash
python -c "from auto_agent.cli import cmd_init; print('cli.py import OK')"
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "fix: use platform util for npm/npx commands in cli.py"
```

---

### Task 9: vault_rag.py — 하드코딩 기본 경로 제거

**Files:**
- Modify: `auto_agent/orchestrator/vault_rag.py` L19-23

- [ ] **Step 1: VAULT_DIR 기본값 수정**

```python
# Before (L19-23):
VAULT_DIR = Path(os.environ.get(
    "KAIROS_VAULT_DIR",
    os.path.expanduser("~/Projects/kairos-vault"),   # COMPAT: was hardcoded
))

# After:
_vault_dir_env = os.environ.get("KAIROS_VAULT_DIR")
if _vault_dir_env:
    VAULT_DIR = Path(_vault_dir_env).expanduser()
else:
    # KAIROS_VAULT_DIR 미설정 — 기본 경로 시도, 없으면 비활성
    VAULT_DIR = Path.home() / "Projects" / "kairos-vault"
    # (VaultRAG.__init__에서 self.enabled = self.vault_dir.exists() 로 자동 비활성)
```

**중요:** `EnvironmentError`를 던지지 않음. 기존 `enabled = self.vault_dir.exists()` 로직이 자동으로 비활성화.
변경 사항: 하드코딩된 개발자 경로(`~/Projects/kairos-vault`) 제거. 경고는 기존 `print()` 방식 유지 (logging import 불필요).

- [ ] **Step 2: 동작 확인**

```bash
python -c "from auto_agent.orchestrator.vault_rag import VaultRAG; print('vault_rag.py import OK')"
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/orchestrator/vault_rag.py
git commit -m "fix: remove hardcoded ~/Projects/kairos-vault default in vault_rag.py"
```

---

### Task 10: start scripts — PATH 하드코딩 제거

**Files:**
- Modify: `start_dashboard.sh` L12-13
- Modify: `start_pipeline.sh` L12-13

- [ ] **Step 1: start_dashboard.sh 수정**

```bash
# Before (L12-13):
# Node.js 경로
export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"

# After (L12-13 전체 교체):
# Node.js 경로는 Python 코드 내부에서 platform.get_env_with_node()로 처리
# (COMPAT: was export PATH="/Users/hannah/local/nodejs/..." hardcoded)
```

즉 두 줄(주석 + export)을 한 줄 주석으로 교체.

- [ ] **Step 2: start_pipeline.sh 동일하게 수정**

- [ ] **Step 3: start_dashboard.sh가 Python import 가능한지 확인**

```bash
bash -n start_dashboard.sh && echo "bash syntax OK"
bash -n start_pipeline.sh  && echo "bash syntax OK"
```

- [ ] **Step 4: 커밋**

```bash
git add start_dashboard.sh start_pipeline.sh
git commit -m "fix: remove hardcoded Node.js PATH from start scripts"
```

---

### Task 11: .env.example 생성

**Files:**
- Create: `.env.example`

- [ ] **Step 1: .env.example 작성**

```bash
# .env.example — 팀원 설정 가이드
# 복사: cp .env.example .env

# ─── Vault (선택) ──────────────────────────────────────────────
# Obsidian 볼트 경로. 없으면 VaultRAG 자동 비활성화.
KAIROS_VAULT_DIR=~/Projects/kairos-vault

# ─── Node.js (보통 불필요) ─────────────────────────────────────
# nvm/volta/brew로 설치된 경우 자동 탐색.
# 자동 탐색 실패 시에만 직접 지정.
# NODEJS_BIN_DIR=/path/to/node/bin

# ─── API Keys ──────────────────────────────────────────────────
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=
```

- [ ] **Step 2: 커밋**

```bash
git add .env.example
git commit -m "docs: add .env.example with NODEJS_BIN_DIR and KAIROS_VAULT_DIR"
```

---

## Chunk 5: 설치 스크립트

### Task 12: install.sh — 플랫폼 감지 강화 + Node.js 탐색 + npm install

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: 현재 install.sh 구조 파악**

```bash
cat install.sh | head -60
```

- [ ] **Step 2: OS/아키텍처 감지 함수 교체**

기존 `detect_os()` 함수는 유지하되, WSL 감지를 `/proc/version` 방식으로 교체:

```bash
detect_os() {
    local uname_s uname_m
    uname_s="$(uname -s)"
    uname_m="$(uname -m)"
    # WSL 감지: /proc/version에 microsoft 포함
    if [ -f /proc/version ] && grep -qi "microsoft" /proc/version 2>/dev/null; then
        printf 'WSL'
    elif [ "$uname_s" = 'Darwin' ]; then
        printf 'macOS'
    else
        printf 'Linux'
    fi
}

detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64) printf 'x64' ;;
        arm64|aarch64) printf 'arm64' ;;
        *) printf 'unknown' ;;
    esac
}
```

- [ ] **Step 3: Python 버전 체크를 3.10 → 3.11로 업데이트**

기존 `ensure_python()` 함수(L51-70)에서 버전 체크만 수정:

```bash
# Before (L55):
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" 2>/dev/null; then

# After:
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)" 2>/dev/null; then
```

그리고 경고 메시지 (L59):
```bash
# Before:
warn "Python 3.10+ 필요 (현재 $ver)"

# After:
warn "Python 3.11+ 필요 (현재 $ver)"
```

- [ ] **Step 4: ensure_node() — nvm/volta 탐색 강화**

기존 `ensure_node()` 함수(L72-85)에 nvm/volta PATH 탐색 로직 추가.
기존 함수는 `which node` 성공 시 바로 return하므로, 실패 시 설치 전에 PATH를 확장해서 재시도:

```bash
ensure_node() {
  # 1. which (PATH에 이미 있으면 OK)
  if command -v node >/dev/null 2>&1; then
    info "Node.js $(node -v) ✓"; return 0
  fi
  # 2. nvm 수동 탐색 (nvm 사용자는 기본적으로 PATH에 없을 수 있음)
  if [ -d "$HOME/.nvm/versions/node" ]; then
    local nvm_default="$HOME/.nvm/alias/default"
    local ver_dir=""
    if [ -f "$nvm_default" ]; then
      ver_dir=$(cat "$nvm_default" 2>/dev/null | tr -d '[:space:]')
    fi
    if [ -z "$ver_dir" ]; then
      ver_dir=$(ls -1 "$HOME/.nvm/versions/node" 2>/dev/null | sort -rV | head -1)
    fi
    if [ -n "$ver_dir" ] && [ -x "$HOME/.nvm/versions/node/$ver_dir/bin/node" ]; then
      export PATH="$HOME/.nvm/versions/node/$ver_dir/bin:$PATH"
      info "Node.js $(node -v) [nvm] ✓"; return 0
    fi
  fi
  # 3. volta
  if [ -x "$HOME/.volta/bin/node" ]; then
    export PATH="$HOME/.volta/bin:$PATH"
    info "Node.js $(node -v) [volta] ✓"; return 0
  fi
  # 4. 자동 설치 (기존 로직 유지)
  info "Node.js 설치 중..."
  case "$(detect_pm)" in
    brew)   brew install node ;;
    apt)    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash - && sudo apt-get install -y nodejs ;;
    dnf)    curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash - && sudo dnf install -y nodejs ;;
    pacman) sudo pacman -S --noconfirm nodejs npm ;;
    *)      fail "Node.js를 수동 설치하세요: https://nodejs.org" ;;
  esac
  success "Node.js 설치 완료"
}
```

- [ ] **Step 5: remotion_template npm install 단계 추가 (기존에 없으면 추가)**

```bash
# remotion_template npm install
REMOTION_DIR="$SCRIPT_DIR/auto_agent/remotion_template"
if [ -f "$REMOTION_DIR/package.json" ]; then
    if [ ! -d "$REMOTION_DIR/node_modules" ]; then
        info "Remotion 의존성 설치 중..."
        npm install --prefix "$REMOTION_DIR" || {
            warn "npm install 실패. 나중에 수동 실행: cd $REMOTION_DIR && npm install"
        }
    else
        info "Remotion node_modules 이미 존재 — 스킵"
    fi
fi
```

- [ ] **Step 6: install.sh 문법 검증**

```bash
bash -n install.sh && echo "bash syntax OK"
```

- [ ] **Step 7: 커밋**

```bash
git add install.sh
git commit -m "fix: improve install.sh — platform detection, Node.js search, npm install"
```

---

### Task 13: install.ps1 — remotion npm install 단계 추가

**Files:**
- Modify: `install.ps1`

- [ ] **Step 1: 현재 install.ps1 구조 파악**

```bash
cat install.ps1 | head -80
```

- [ ] **Step 2: remotion npm install 함수 추가**

`Setup-Env` 함수 이후, `Sync-Projects` 이전에 삽입:

```powershell
function Install-RemotionDeps {
    $remotionDir = Join-Path $PSScriptRoot "auto_agent\remotion_template"
    if (-not (Test-Path "$remotionDir\package.json")) {
        Write-Host "  [SKIP] remotion_template/package.json 없음" -ForegroundColor Yellow
        return
    }
    if (Test-Path "$remotionDir\node_modules") {
        Write-Host "  [SKIP] Remotion node_modules 이미 존재" -ForegroundColor DarkGray
        return
    }
    Write-Host "  [NPM] Remotion 의존성 설치 중..." -ForegroundColor Cyan
    $result = & npm install --prefix $remotionDir 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "npm install 실패. 나중에 수동 실행: cd $remotionDir; npm install"
    } else {
        Write-Host "  [OK] Remotion 의존성 설치 완료" -ForegroundColor Green
    }
}
```

메인 흐름에 `Install-RemotionDeps` 호출 추가.

- [ ] **Step 3: PowerShell 문법 검증**

```bash
# macOS에서는 pwsh(PowerShell Core)로 문법 검증
pwsh -NoProfile -Command "
\$content = Get-Content 'install.ps1' -Raw
\$errors = \$null
[System.Management.Automation.Language.Parser]::ParseInput(\$content, [ref]\$null, [ref]\$errors)
if (\$errors.Count -eq 0) { Write-Host 'Syntax OK' } else { \$errors | ForEach-Object { Write-Warning \$_.Message } }
" 2>/dev/null || echo "pwsh 없음 — 윈도우 환경에서 검증 필요"
```

- [ ] **Step 4: 커밋**

```bash
git add install.ps1
git commit -m "fix: add remotion npm install step to install.ps1"
```

---

## Chunk 6: 최종 검증

### Task 14: 전체 통합 테스트 + 회귀 체크

- [ ] **Step 1: platform.py 단위 테스트 전체 재실행**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
source .venv/bin/activate
pytest tests/test_platform.py -v
```

Expected: 전체 PASS

- [ ] **Step 2: Python import 체인 검증**

```bash
python -c "
import app
from auto_agent.orchestrator.runner import Runner
from auto_agent.dashboard.scene_editor import generate_thumbnails
from auto_agent.tools.remotion_bridge import RemotionBridge
from auto_agent.scripts.layout_check import render_still
from auto_agent.cli import cmd_init
from auto_agent.orchestrator.vault_rag import VaultRAG
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 3: node 탐색 동작 확인**

```bash
python -c "
from auto_agent.utils.platform import get_node_bin_dir, get_env_with_node, get_npm_cmd, get_npx_cmd
print('node bin dir:', get_node_bin_dir())
print('npm cmd:', get_npm_cmd())
print('npx cmd:', get_npx_cmd())
env = get_env_with_node()
print('PATH includes node:', str(get_node_bin_dir()) in env['PATH'])
import os; print('os.environ unchanged:', os.environ.get('PATH') == env.get('PATH') or str(get_node_bin_dir()) in os.environ.get('PATH', ''))
"
```

- [ ] **Step 4: os.environ 전역 수정 코드 잔존 여부 검사**

```bash
grep -rn 'os\.environ\["PATH"\]\s*=' auto_agent/ app.py
```

Expected: 아무 것도 나오지 않아야 함 (0 matches)

- [ ] **Step 5: 하드코딩 경로 잔존 여부 검사**

```bash
grep -rn "node-v[0-9]" auto_agent/ app.py start_dashboard.sh start_pipeline.sh
```

Expected: 아무 것도 나오지 않아야 함 (0 matches)

- [ ] **Step 6: 최종 커밋 (미커밋 파일 있을 경우)**

```bash
# 미커밋 파일 확인 후 명시적으로 지정 (git add -A 금지 — 불필요한 파일 포함 위험)
git status
# 위 결과 확인 후 필요한 파일만 추가:
# git add <file1> <file2> ...
git commit -m "chore: cross-platform compatibility complete — all hardcoded paths removed"
```

---

## 검증 체크리스트 (구현 완료 후 수동 확인)

- [ ] `node --version` 실행 가능 (platform.get_node_bin_dir() 기반)
- [ ] 대시보드 씬 에디터 빌드 성공 (`scene_editor.py` 썸네일 생성)
- [ ] Remotion Studio 시작 성공 (`app.py` npm/npx 호출)
- [ ] `npm install` remotion_template 성공 (`cli.py`)
- [ ] `npx remotion render` 성공 (`runner.py` 렌더링)
- [ ] `vault_rag.py` — KAIROS_VAULT_DIR 없어도 파이프라인 중단 없음
- [ ] `install.sh` — 신규 맥에서 처음부터 실행 테스트
- [ ] `install.ps1` — 윈도우 환경에서 실행 테스트
