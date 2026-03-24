"""
VaultIndexer — kairos-vault .md 파일을 Chroma DB에 벡터 인덱싱.

사용:
    indexer = VaultIndexer()
    indexer.index_all(vault_dir)        # 변경 파일만 재인덱싱
    indexer.index_all(vault_dir, force=True)  # 전체 재인덱싱
    indexer.get_stats()                 # 통계
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ~/.kairos/ 기본 저장 경로
_KAIROS_DIR = Path.home() / ".kairos"
DEFAULT_CHROMA_DIR = _KAIROS_DIR / "vault_chroma"
DEFAULT_HASH_CACHE = _KAIROS_DIR / "vault_index_hashes.json"
COLLECTION_NAME = "kairos_vault"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

_CHANNEL_KEYWORDS = {
    "이로미즘": ["이로미즘", "iromism"],
    "세모지": ["세모지", "semoji"],
}


def _extract_channel(tags: list[str]) -> str:
    """태그 목록에서 채널명 추출. 없으면 빈 문자열."""
    tags_lower = [t.lower().strip() for t in tags]
    for channel, keywords in _CHANNEL_KEYWORDS.items():
        if any(kw in tags_lower for kw in keywords):
            return channel
    return ""


class VaultIndexer:
    """Obsidian 볼트 벡터 인덱서."""

    def __init__(
        self,
        chroma_dir: Optional[Path] = None,
        hash_cache: Optional[Path] = None,
    ):
        self.chroma_dir = chroma_dir or DEFAULT_CHROMA_DIR
        self.hash_cache_path = hash_cache or DEFAULT_HASH_CACHE
        self._collection = None

    # ── 공개 API ────────────────────────────────────────────

    def index_all(self, vault_dir: Path, force: bool = False) -> dict:
        """
        볼트 전체 인덱싱.
        force=True: 해시 캐시 무시, 전체 재인덱싱.
        반환: {"indexed": int, "skipped": int, "errors": int, "total_chunks": int}
        """
        self._ensure_initialized()
        hashes = {} if force else self._load_hashes()

        stats = {"indexed": 0, "skipped": 0, "errors": 0, "total_chunks": 0}

        for md_file in sorted(vault_dir.rglob("*.md")):
            # 최상위 폴더가 _ 로 시작하면 제외
            relative = md_file.relative_to(vault_dir)
            top_folder = relative.parts[0] if len(relative.parts) > 1 else ""
            if top_folder.startswith("_"):
                continue

            file_hash = self._file_hash(md_file)
            if not force and hashes.get(str(relative)) == file_hash:
                stats["skipped"] += 1
                continue

            try:
                chunks_added = self.index_file(md_file, vault_dir)
                hashes[str(relative)] = file_hash
                stats["indexed"] += 1
            except Exception as e:
                print(f"[VaultIndexer] 오류 skip: {relative} -- {e}")
                stats["errors"] += 1

        stats["total_chunks"] = self._collection.count()

        self._save_hashes(hashes)
        self._update_last_indexed()
        print(f"[VaultIndexer] 완료: {stats}")
        return stats

    def index_file(self, path: Path, vault_dir: Path) -> int:
        """
        단일 파일 인덱싱.
        1. 기존 청크 삭제
        2. 본문 청킹 + 임베딩 + upsert
        반환: 추가된 청크 수
        """
        self._ensure_initialized()
        relative = str(path.relative_to(vault_dir))
        top_folder = relative.split("/")[0] if "/" in relative else ""

        # frontmatter 파싱
        text = path.read_text(encoding="utf-8")
        tags, body = self._parse_md(text)

        if not body.strip():
            return 0

        # 기존 청크 삭제 (file 메타데이터로 조회)
        existing = self._collection.get(where={"file": relative})
        if existing["ids"]:
            self._collection.delete(ids=existing["ids"])

        # 청킹
        chunks = self._chunk_text(body)
        if not chunks:
            return 0

        # 채널 추출 (이로미즘/세모지)
        channel = _extract_channel(tags)

        # Chroma upsert
        ids = [f"{relative}#{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file": relative,
                "folder": top_folder,
                "tags": ",".join(tags),
                "channel": channel,
                "chunk_index": i,
            }
            for i in range(len(chunks))
        ]
        self._collection.upsert(documents=chunks, ids=ids, metadatas=metadatas)
        return len(chunks)

    def get_stats(self) -> dict:
        """인덱스 통계."""
        self._ensure_initialized()
        meta = self._load_meta()
        return {
            "file_count": len(self._load_hashes()),
            "chunk_count": self._collection.count(),
            "last_indexed_at": meta.get("last_indexed_at"),
            "chroma_dir": str(self.chroma_dir),
            "vault_dir": str(meta.get("vault_dir", "")),
        }

    # ── 내부 유틸 ────────────────────────────────────────────

    def _ensure_initialized(self):
        """Chroma + 임베딩 모델 지연 초기화."""
        if self._collection is not None:
            return
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            raise ImportError(
                "RAG 의존성이 없습니다. 설치: pip install -e '.[rag]'"
            )

        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.chroma_dir))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=MODEL_NAME
        )
        self._collection = client.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=ef
        )

    def _parse_md(self, text: str) -> tuple[list, str]:
        """frontmatter 파싱 + [[위키링크]] 제거. 반환: (tags, body)"""
        tags = []
        body = text

        # frontmatter 추출
        if text.startswith("---"):
            end = text.find("---", 3)
            if end > 0:
                fm = text[3:end]
                body = text[end + 3:].strip()
                # tags 파싱
                m = re.search(r"tags:\s*\[([^\]]+)\]", fm)
                if m:
                    tags = [t.strip() for t in m.group(1).split(",")]

        # [[위키링크]] 제거 (링크 텍스트만 유지)
        body = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", body)
        return tags, body

    def _chunk_text(self, text: str) -> list[str]:
        """500자 청킹, 100자 오버랩."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = end - CHUNK_OVERLAP
        return chunks

    def _file_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def _load_hashes(self) -> dict:
        if self.hash_cache_path.exists():
            try:
                return json.loads(self.hash_cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_hashes(self, hashes: dict):
        self.hash_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.hash_cache_path.write_text(
            json.dumps(hashes, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @property
    def _meta_path(self) -> Path:
        return self.hash_cache_path.parent / "vault_index_meta.json"

    def _load_meta(self) -> dict:
        if self._meta_path.exists():
            try:
                return json.loads(self._meta_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _update_last_indexed(self):
        meta = self._load_meta()
        meta["last_indexed_at"] = datetime.now(timezone.utc).isoformat()
        self._meta_path.parent.mkdir(parents=True, exist_ok=True)
        self._meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
