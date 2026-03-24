# auto_agent/utils/platform.py
"""
플랫폼 추상화 유틸 -- Node.js 탐색, 명령어, PATH 처리

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


# ─── 플랫폼 감지 ───────────────────────────────────────────────────────────────

def is_windows() -> bool:
    return sys.platform == "win32"


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_wsl() -> bool:
    """/proc/version에서 'microsoft' 문자열로 WSL 감지. 파일 없으면 False."""
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except (FileNotFoundError, PermissionError):
        return False


# ─── Node.js 탐색 ──────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def get_node_bin_dir() -> Path:
    """
    Node.js 바이너리 디렉토리를 탐색하여 반환.

    탐색 순서:
        1. NODEJS_BIN_DIR 환경변수 (팀원 수동 오버라이드)
        2. shutil.which("node") -> 부모 디렉토리
        3. nvm -- ~/.nvm/alias/default -> 버전 디렉토리, 없으면 최신 버전
        4. volta -- ~/.volta/bin
        5. brew -- /opt/homebrew/bin, /usr/local/bin
        5.5. 로컬 nodejs 설치 -- ~/local/nodejs/node-v*/bin
        6. Windows 시스템 경로 -- C:/Program Files/nodejs, AppData nvm-windows

    Returns:
        Path: node 바이너리가 있는 디렉토리

    Raises:
        EnvironmentError: Node.js를 찾을 수 없을 때 (설치 안내 포함)

    Note:
        @lru_cache(maxsize=1) -- 첫 탐색 결과를 캐싱.
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
            default_ver = nvm_alias.read_text(encoding="utf-8").strip()
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

    # 5.5. 로컬 nodejs 설치 (~/local/nodejs/node-v*/bin 형태)
    local_nodejs = Path.home() / "local" / "nodejs"
    if local_nodejs.exists():
        try:
            for ver_dir in sorted(local_nodejs.iterdir(), reverse=True):
                bin_dir = ver_dir / "bin"
                if (bin_dir / node_exe).exists():
                    return bin_dir
        except OSError:
            pass

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
    path_parts = current_path.split(os.path.pathsep)
    if node_bin not in path_parts:
        env["PATH"] = node_bin + os.path.pathsep + current_path
    return env
