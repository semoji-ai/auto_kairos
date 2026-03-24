"""캐릭터 글로벌 라이브러리 -- PNG tEXt 메타데이터 + SQLite 인덱스."""
from __future__ import annotations
import hashlib
import logging
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image, PngImagePlugin

logger = logging.getLogger(__name__)

_DEFAULT_LIBRARY_DIR = Path.home() / ".auto_agent" / "characters"
_DEFAULT_DB_PATH     = Path.home() / ".auto_agent" / "characters.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    art_style     TEXT NOT NULL,
    tags          TEXT NOT NULL DEFAULT '',
    features      TEXT NOT NULL DEFAULT '',
    features_hash TEXT NOT NULL DEFAULT '',
    file_path     TEXT NOT NULL UNIQUE,
    source_project TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_characters_name_style ON characters(name, art_style);
"""


@dataclass
class CharacterRecord:
    id: int
    name: str
    art_style: str
    tags: str
    features: str
    features_hash: str
    file_path: Path
    source_project: str
    created_at: str


def embed_png_metadata(png_path: Path, meta: dict) -> None:
    """PNG tEXt 청크에 메타데이터를 embed."""
    img = Image.open(png_path)
    info = PngImagePlugin.PngInfo()
    for k, v in meta.items():
        info.add_text(k, str(v))
    img.save(png_path, pnginfo=info)


def read_png_metadata(png_path: Path) -> dict:
    """PNG tEXt 청크에서 메타데이터를 읽어 반환. 없으면 빈 dict."""
    try:
        img = Image.open(png_path)
        return dict(img.text) if hasattr(img, "text") else {}
    except Exception as e:
        logger.warning("PNG 메타데이터 읽기 실패 (%s): %s", png_path, e)
        return {}


def _features_hash(features: str) -> str:
    """features 문자열의 SHA-256 앞 8자."""
    return hashlib.sha256(features.encode()).hexdigest()[:8]


class CharacterLibrary:
    def __init__(
        self,
        library_dir: Path = _DEFAULT_LIBRARY_DIR,
        db_path: Path = _DEFAULT_DB_PATH,
    ):
        self.library_dir = Path(library_dir)
        self.db_path = Path(db_path)
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def register(self, png_path: Path, metadata: dict) -> CharacterRecord:
        """PNG를 라이브러리에 등록. 동일 features_hash면 기존 반환."""
        name     = metadata.get("character_name", "")
        style    = metadata.get("art_style", "")
        tags     = metadata.get("tags", "")
        features = metadata.get("features", "")
        fhash    = _features_hash(features)
        source   = metadata.get("source_project", "")
        now      = datetime.now(timezone.utc).isoformat()

        # 중복 체크
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM characters WHERE name=? AND art_style=? AND features_hash=?",
                (name, style, fhash),
            ).fetchone()
            if row:
                return self._row_to_record(row)

        # 파일명: {name}__{style}__{hash8}.png
        safe = lambda s: s.replace(" ", "_").replace("/", "-")[:30]
        fname = f"{safe(name)}__{safe(style)}__{fhash}.png"
        dest = self.library_dir / fname
        shutil.copy2(png_path, dest)

        # PNG tEXt embed
        embed_meta = {
            "character_name": name,
            "art_style": style,
            "tags": tags,
            "features": features,
            "source_project": source,
            "created_at": now,
        }
        embed_png_metadata(dest, embed_meta)

        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO characters (name, art_style, tags, features, features_hash, "
                "file_path, source_project, created_at) VALUES (?,?,?,?,?,?,?,?)",
                (name, style, tags, features, fhash, str(dest), source, now),
            )
            row_id = cur.lastrowid

        return CharacterRecord(
            id=row_id, name=name, art_style=style, tags=tags,
            features=features, features_hash=fhash,
            file_path=dest, source_project=source, created_at=now,
        )

    def search(
        self,
        name: str,
        art_style: str,
        tags: list[str] | None = None,
    ) -> Optional[CharacterRecord]:
        """name + art_style로 검색. tags 있으면 포함도로 정렬."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM characters WHERE name=? AND art_style=? ORDER BY created_at DESC",
                (name, art_style),
            ).fetchall()

        if not rows:
            return None
        if len(rows) == 1 or not tags:
            return self._row_to_record(rows[0])

        def score(row) -> int:
            row_tags = set(t.strip() for t in (row["tags"] or "").split(",") if t.strip())
            return sum(1 for t in tags if t in row_tags)

        best = max(rows, key=score)
        return self._row_to_record(best)

    def copy_to_project(self, record: CharacterRecord, project_dir: Path) -> Path:
        """라이브러리 파일을 프로젝트 characters/ 디렉토리로 복사."""
        dest_dir = project_dir / "characters"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / Path(record.file_path).name
        shutil.copy2(record.file_path, dest)
        return dest

    def rebuild_index(self) -> int:
        """LIBRARY_DIR 스캔 -> PNG tEXt에서 DB 재구성. 복구된 레코드 수 반환."""
        count = 0
        for png_path in sorted(self.library_dir.glob("*.png")):
            meta = read_png_metadata(png_path)
            if not meta.get("character_name"):
                logger.warning("tEXt 메타 없음, 건너뜀: %s", png_path.name)
                continue
            name     = meta["character_name"]
            style    = meta.get("art_style", "")
            features = meta.get("features", "")
            fhash    = _features_hash(features)
            with self._connect() as conn:
                existing = conn.execute(
                    "SELECT id FROM characters WHERE file_path=?", (str(png_path),)
                ).fetchone()
                if existing:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO characters "
                    "(name, art_style, tags, features, features_hash, file_path, source_project, created_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (
                        name, style,
                        meta.get("tags", ""), features, fhash,
                        str(png_path), meta.get("source_project", ""),
                        meta.get("created_at", datetime.now(timezone.utc).isoformat()),
                    ),
                )
            count += 1
        return count

    def _row_to_record(self, row) -> CharacterRecord:
        return CharacterRecord(
            id=row["id"], name=row["name"], art_style=row["art_style"],
            tags=row["tags"] or "", features=row["features"] or "",
            features_hash=row["features_hash"] or "",
            file_path=Path(row["file_path"]),
            source_project=row["source_project"] or "",
            created_at=row["created_at"],
        )
