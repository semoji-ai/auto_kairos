"""
이중 루트 경로 해석 (Dual Root Path Resolution)

PACKAGE_DIR:  패키지 설치 위치 (읽기 전용 -- skills, pipeline.json, agents.json 등)
WORKSPACE_DIR: 사용자 워크스페이스 (읽기/쓰기 -- output, .env, DB, remotion)

워크스페이스 결정 우선순위:
  1. --workspace <path> CLI 인자
  2. AUTO_AGENT_WORKSPACE 환경 변수
  3. 현재 작업 디렉토리 (CWD)
"""
import os
import sys
from pathlib import Path


def get_package_dir() -> Path:
    """패키지 루트 디렉토리 (auto_agent/)."""
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """번들 데이터 디렉토리 (pipeline.json, agents.json, skills/ 등)."""
    return get_package_dir() / "data"


def get_workspace_dir() -> Path:
    """사용자 워크스페이스 디렉토리 (output, .env, DB)."""
    # 1. --workspace CLI 인자
    for i, arg in enumerate(sys.argv):
        if arg == "--workspace" and i + 1 < len(sys.argv):
            p = Path(sys.argv[i + 1]).resolve()
            if p.exists():
                return p
            raise FileNotFoundError(f"Workspace not found: {p}")

    # 2. AUTO_AGENT_WORKSPACE 환경 변수
    env = os.getenv("AUTO_AGENT_WORKSPACE")
    if env:
        p = Path(env).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Workspace not found: {p}")

    # 3. CWD
    return Path.cwd()


# 모듈 레벨 상수 (자주 쓰이므로 미리 해석)
PACKAGE_DIR = get_package_dir()
DATA_DIR = get_data_dir()
