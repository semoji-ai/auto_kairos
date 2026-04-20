"""중복 방지 — 워터마크(state.json) + 콘텐츠 해시(hashes.db)."""
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class UpsertAction(Enum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"


class DedupManager:
    """워터마크 + 해시 기반 중복 판별."""

    def __init__(self, collector_dir: Path):
        self._collector_dir = collector_dir
        self._collector_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = collector_dir / "state.json"
        self._db_path = collector_dir / "hashes.db"
        self._init_db()

    # ── 워터마크 ──

    def get_watermark(self, source: str, key: str) -> Optional[Dict]:
        state = self._load_state()
        return state.get(source, {}).get(key)

    def set_watermark(self, source: str, key: str, data: Dict):
        state = self._load_state()
        if source not in state:
            state[source] = {}
        state[source][key] = data
        self._save_state(state)

    # ── 해시 DB ──

    def check(self, source: str, source_id: str, content: str) -> UpsertAction:
        content_hash = self._hash(content)
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT hash FROM collected WHERE source = ? AND source_id = ?",
                (source, source_id),
            ).fetchone()
            if row is None:
                return UpsertAction.CREATE
            return UpsertAction.SKIP if row[0] == content_hash else UpsertAction.UPDATE
        finally:
            conn.close()

    def record(self, source: str, source_id: str, content: str, note_path: str):
        content_hash = self._hash(content)
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """INSERT INTO collected (source, source_id, hash, note_path, created, updated)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(source, source_id)
                   DO UPDATE SET hash = excluded.hash, note_path = excluded.note_path, updated = excluded.updated""",
                (source, source_id, content_hash, note_path, now, now),
            )
            conn.commit()
        finally:
            conn.close()

    def get_note_path(self, source: str, source_id: str) -> Optional[str]:
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT note_path FROM collected WHERE source = ? AND source_id = ?",
                (source, source_id),
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    # ── 내부 ──

    def _init_db(self):
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """CREATE TABLE IF NOT EXISTS collected (
                source    TEXT,
                source_id TEXT,
                hash      TEXT,
                note_path TEXT,
                created   TEXT,
                updated   TEXT,
                PRIMARY KEY (source, source_id)
            )"""
        )
        conn.commit()
        conn.close()

    def _load_state(self) -> Dict:
        if self._state_path.exists():
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        return {}

    def _save_state(self, state: Dict):
        self._state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
