"""
SQLite 커넥션 매니저.
- AUTO_AGENT_DB 환경변수 또는 프로젝트 루트의 auto_agent.db 사용
- WAL 모드: NAS 동시 읽기 지원
- 트랜잭션 컨텍스트 매니저 제공
"""
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from auto_agent.paths import get_workspace_dir

# 하위 호환
PROJECT_ROOT = get_workspace_dir()


def get_db_path() -> Path:
    """DB 경로: AUTO_AGENT_DB 환경변수 > 워크스페이스/auto_agent.db"""
    env_path = os.getenv("AUTO_AGENT_DB")
    if env_path:
        return Path(env_path)
    return get_workspace_dir() / "auto_agent.db"


def get_connection(db_path: Path = None) -> sqlite3.Connection:
    """WAL 모드 + foreign_keys 활성화된 SQLite 커넥션 반환."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(str(path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction(db_path: Path = None):
    """DB 트랜잭션 컨텍스트 매니저. 예외 시 자동 롤백."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = None) -> Path:
    """schema.sql로 DB 초기화. 생성된 DB 경로 반환."""
    path = db_path or get_db_path()
    schema_path = Path(__file__).parent / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()
    conn = get_connection(path)
    conn.executescript(schema)
    conn.close()
    return path


def db_exists(db_path: Path = None) -> bool:
    """DB 파일 존재 여부 확인."""
    path = db_path or get_db_path()
    return path.exists()
