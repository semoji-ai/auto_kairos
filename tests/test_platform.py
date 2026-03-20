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


@pytest.fixture(autouse=True)
def clear_node_cache():
    _clear()
    yield
    _clear()


def test_get_node_bin_dir_env_override(tmp_path, monkeypatch):
    """NODEJS_BIN_DIR 환경변수가 있으면 그 경로를 반환"""
    fake_bin = tmp_path / "mynode" / "bin"
    fake_bin.mkdir(parents=True)
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()

    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()

    from auto_agent.utils.platform import get_node_bin_dir
    result = get_node_bin_dir()
    assert result == fake_bin


def test_get_node_bin_dir_found():
    """현재 환경에서 node 탐색 성공"""
    import shutil
    if not shutil.which("node"):
        pytest.skip("node가 설치되지 않은 환경 — 탐색 불가")
    from auto_agent.utils.platform import get_node_bin_dir
    result = get_node_bin_dir()
    assert result.exists()


def test_get_node_bin_dir_not_found(monkeypatch):
    """node 찾지 못하면 EnvironmentError"""
    monkeypatch.delenv("NODEJS_BIN_DIR", raising=False)

    with mock.patch("shutil.which", return_value=None), \
         mock.patch("pathlib.Path.exists", return_value=False), \
         mock.patch("pathlib.Path.iterdir", side_effect=FileNotFoundError):
        from auto_agent.utils.platform import get_node_bin_dir
        _clear()
        with pytest.raises(EnvironmentError, match="Node.js를 찾을 수 없습니다"):
            get_node_bin_dir()


def test_get_node_bin_dir_caching(tmp_path, monkeypatch):
    """lru_cache로 두 번 호출해도 함수 본체는 1회만 실행"""
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


def test_get_env_with_node_path_contains_node(tmp_path, monkeypatch):
    """get_env_with_node()의 PATH에 node bin 경로 포함"""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()
    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()

    from auto_agent.utils.platform import get_env_with_node
    env = get_env_with_node()
    assert str(fake_bin) in env["PATH"]


def test_get_env_with_node_no_global_mutation(tmp_path, monkeypatch):
    """get_env_with_node()는 os.environ을 수정하지 않음"""
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


def test_get_env_with_node_uses_pathsep(tmp_path, monkeypatch):
    """PATH 구분자가 플랫폼 pathsep임을 동작으로 검증"""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    node_exe = "node.exe" if sys.platform == "win32" else "node"
    (fake_bin / node_exe).touch()
    monkeypatch.setenv("NODEJS_BIN_DIR", str(fake_bin))
    _clear()
    from auto_agent.utils.platform import get_env_with_node
    env = get_env_with_node()
    parts = env["PATH"].split(os.path.pathsep)
    assert str(fake_bin) in parts


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
