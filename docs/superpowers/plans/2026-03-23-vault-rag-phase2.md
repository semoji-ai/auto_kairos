# Vault RAG Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kairos-vault의 .md 파일을 로컬 벡터 DB(Chroma)에 인덱싱하여 파이프라인과 대시보드에서 시맨틱 검색이 가능하도록 Phase 1 키워드 검색을 업그레이드한다.

**Architecture:** `VaultIndexer`가 kairos-vault .md 파일을 청킹/임베딩하여 `~/.kairos/vault_chroma/`에 영구 저장한다. `VaultRAG.semantic_search()`가 Chroma를 쿼리하고, 미설치 시 기존 키워드 검색으로 폴백한다. 대시보드에 `/api/vault/search` API와 검색 UI가 추가된다.

**Tech Stack:** Python, sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2), chromadb, FastAPI/Jinja2, HTMX

**Spec:** `docs/superpowers/specs/2026-03-23-vault-rag-phase2-design.md`

---

## Chunk 1: 기반 작업 (경로 수정 + 의존성 + 인덱서)

### Task 1: 볼트 경로 버그 수정

**Files:**
- Modify: `auto_agent/orchestrator/vault_rag.py` (상단 VAULT_DIR 정의 부분)

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_vault_rag_path.py
import os
from pathlib import Path
from unittest.mock import patch


def test_vault_dir_prefers_projects_over_desktop(tmp_path):
    """Projects 경로가 존재하면 Desktop보다 우선한다."""
    projects_vault = tmp_path / "Projects" / "kairos-vault"
    projects_vault.mkdir(parents=True)
    desktop_vault = tmp_path / "Desktop" / "kairos-vault"
    desktop_vault.mkdir(parents=True)

    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.home", return_value=tmp_path):
            # vault_rag 모듈 재로드하여 VAULT_DIR 재계산
            import importlib
            import auto_agent.orchestrator.vault_rag as vr
            importlib.reload(vr)
            assert vr.VAULT_DIR == projects_vault


def test_vault_dir_falls_back_to_desktop(tmp_path):
    """Projects 경로가 없으면 Desktop을 사용한다."""
    desktop_vault = tmp_path / "Desktop" / "kairos-vault"
    desktop_vault.mkdir(parents=True)

    with patch.dict(os.environ, {}, clear=True):
        with patch("pathlib.Path.home", return_value=tmp_path):
            import importlib
            import auto_agent.orchestrator.vault_rag as vr
            importlib.reload(vr)
            assert vr.VAULT_DIR == desktop_vault


def test_vault_dir_env_var_overrides(tmp_path):
    """KAIROS_VAULT_DIR 환경변수가 있으면 최우선이다."""
    custom = tmp_path / "custom-vault"
    with patch.dict(os.environ, {"KAIROS_VAULT_DIR": str(custom)}):
        import importlib
        import auto_agent.orchestrator.vault_rag as vr
        importlib.reload(vr)
        assert vr.VAULT_DIR == custom
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
python -m pytest tests/test_vault_rag_path.py -v
```
Expected: FAIL (현재 Desktop만 체크)

- [ ] **Step 3: vault_rag.py 상단 `VAULT_DIR` 정의 수정**

`auto_agent/orchestrator/vault_rag.py` 상단의 `VAULT_DIR = ...` 라인을 다음으로 교체:

```python
def _resolve_vault_dir() -> Path:
    """볼트 경로 결정. 환경변수 → Projects → Desktop 순으로 시도."""
    if env := os.environ.get("KAIROS_VAULT_DIR"):
        return Path(env)
    projects_path = Path.home() / "Projects" / "kairos-vault"
    desktop_path = Path.home() / "Desktop" / "kairos-vault"
    if projects_path.exists():
        return projects_path
    if desktop_path.exists():
        print("[VaultRAG] 경고: ~/Desktop/kairos-vault 사용 중. ~/Projects/로 이전을 권장합니다.")
        return desktop_path
    return projects_path  # 기본값 (미존재 시 비활성)


VAULT_DIR = _resolve_vault_dir()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_vault_rag_path.py -v
```
Expected: PASS (3개)

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/orchestrator/vault_rag.py tests/test_vault_rag_path.py
git commit -m "fix: vault_rag 볼트 경로 기본값을 Projects로 수정, Desktop 폴백 유지"
```

---

### Task 2: 의존성 추가

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: pyproject.toml `[project.optional-dependencies]`에 rag 그룹 추가**

```toml
[project.optional-dependencies]
dashboard = ["fastapi", "uvicorn", "jinja2", "websockets"]
sync = ["supabase>=2.0"]
rag = ["sentence-transformers>=2.7", "chromadb>=0.5"]
all = ["fastapi", "uvicorn", "jinja2", "websockets", "supabase>=2.0"]
```

`all`에는 포함하지 않는다 (RAG는 선택적 기능, 120MB 모델 다운로드 포함).

- [ ] **Step 2: rag 의존성 설치**

```bash
pip install -e ".[rag]"
```

- [ ] **Step 3: 설치 확인**

```bash
python -c "import sentence_transformers; import chromadb; print('OK')"
```
Expected: OK

- [ ] **Step 4: 커밋**

```bash
git add pyproject.toml
git commit -m "feat: pyproject.toml에 rag optional-dependencies 그룹 추가"
```

---

### Task 3: VaultIndexer 구현

**Files:**
- Create: `auto_agent/orchestrator/vault_indexer.py`
- Create: `tests/test_vault_indexer.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_vault_indexer.py
import json
from pathlib import Path
import pytest


@pytest.fixture
def sample_vault(tmp_path):
    """테스트용 볼트 구조 생성."""
    vault = tmp_path / "kairos-vault"
    patterns = vault / "01-patterns" / "hooks"
    patterns.mkdir(parents=True)

    (patterns / "도입부-후킹-패턴.md").write_text(
        "---\ntags: [hook, opening]\n---\n\n# 도입부 후킹 패턴\n\n"
        "현재 화제가 되는 사건이나 트렌드를 언급 → 궁금증 유발 → 본론 진입\n" * 10,
        encoding="utf-8"
    )

    templates = vault / "_templates"
    templates.mkdir()
    (templates / "tpl-error.md").write_text("# 템플릿", encoding="utf-8")

    return vault


def test_indexer_indexes_md_files(sample_vault, tmp_path):
    """볼트 .md 파일이 Chroma에 인덱싱된다."""
    from auto_agent.orchestrator.vault_indexer import VaultIndexer
    indexer = VaultIndexer(chroma_dir=tmp_path / "chroma", hash_cache=tmp_path / "hashes.json")
    result = indexer.index_all(sample_vault)
    assert result["indexed"] == 1  # _templates 제외
    assert result["total_chunks"] >= 1


def test_indexer_skips_unchanged_files(sample_vault, tmp_path):
    """동일 파일 두 번 인덱싱 시 두 번째는 skip."""
    from auto_agent.orchestrator.vault_indexer import VaultIndexer
    indexer = VaultIndexer(chroma_dir=tmp_path / "chroma", hash_cache=tmp_path / "hashes.json")
    indexer.index_all(sample_vault)
    result2 = indexer.index_all(sample_vault)
    assert result2["skipped"] == 1
    assert result2["indexed"] == 0


def test_indexer_reindexes_changed_files(sample_vault, tmp_path):
    """파일 수정 시 재인덱싱된다."""
    from auto_agent.orchestrator.vault_indexer import VaultIndexer
    indexer = VaultIndexer(chroma_dir=tmp_path / "chroma", hash_cache=tmp_path / "hashes.json")
    indexer.index_all(sample_vault)

    # 파일 수정
    md_file = sample_vault / "01-patterns" / "hooks" / "도입부-후킹-패턴.md"
    md_file.write_text(md_file.read_text(encoding="utf-8") + "\n새로운 내용", encoding="utf-8")

    result2 = indexer.index_all(sample_vault)
    assert result2["indexed"] == 1


def test_indexer_no_orphan_chunks_on_reindex(sample_vault, tmp_path):
    """재인덱싱 시 기존 청크가 삭제되고 새 청크로 교체된다 (중복 없음)."""
    from auto_agent.orchestrator.vault_indexer import VaultIndexer
    indexer = VaultIndexer(chroma_dir=tmp_path / "chroma", hash_cache=tmp_path / "hashes.json")

    result1 = indexer.index_all(sample_vault)
    chunks_before = result1["total_chunks"]

    # hash 캐시만 삭제하여 강제 재인덱싱
    (tmp_path / "hashes.json").unlink()
    result2 = indexer.index_all(sample_vault)
    chunks_after = result2["total_chunks"]

    stats = indexer.get_stats()
    assert stats["chunk_count"] == chunks_after  # 고아 청크 없음


def test_get_stats_returns_correct_structure(sample_vault, tmp_path):
    """get_stats()가 올바른 키를 반환한다."""
    from auto_agent.orchestrator.vault_indexer import VaultIndexer
    indexer = VaultIndexer(chroma_dir=tmp_path / "chroma", hash_cache=tmp_path / "hashes.json")
    indexer.index_all(sample_vault)
    stats = indexer.get_stats()
    assert "file_count" in stats
    assert "chunk_count" in stats
    assert "last_indexed_at" in stats
    assert stats["chunk_count"] >= 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_vault_indexer.py -v
```
Expected: FAIL (모듈 없음)

- [ ] **Step 3: VaultIndexer 구현**

`auto_agent/orchestrator/vault_indexer.py` 생성:

```python
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

# _로 시작하는 최상위 폴더는 제외 (_templates, _raw 등)
EXCLUDED_TOP_FOLDERS = {"_templates", "_raw"}


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
        self._model = None

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
            if top_folder in EXCLUDED_TOP_FOLDERS or top_folder.startswith("_"):
                continue

            file_hash = self._file_hash(md_file)
            if not force and hashes.get(str(relative)) == file_hash:
                stats["skipped"] += 1
                continue

            try:
                chunks_added = self.index_file(md_file, vault_dir)
                hashes[str(relative)] = file_hash
                stats["indexed"] += 1
                stats["total_chunks"] += chunks_added
            except Exception as e:
                print(f"[VaultIndexer] 오류 skip: {relative} — {e}")
                stats["errors"] += 1

        # 총 청크 수 (force 시 indexed 외 기존 청크도 포함)
        if force:
            stats["total_chunks"] = self._collection.count()
        else:
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

        # Chroma upsert
        ids = [f"{relative}#{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file": relative,
                "folder": top_folder,
                "tags": ",".join(tags),
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

    _meta_path = property(lambda self: self.hash_cache_path.parent / "vault_index_meta.json")

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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_vault_indexer.py -v
```
Expected: PASS (5개)

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/orchestrator/vault_indexer.py tests/test_vault_indexer.py
git commit -m "feat: VaultIndexer 구현 — sentence-transformers + Chroma 벡터 인덱싱"
```

---

## Chunk 2: VaultRAG 시맨틱 검색 업그레이드

### Task 4: semantic_search 메서드 추가

**Files:**
- Modify: `auto_agent/orchestrator/vault_rag.py`
- Create: `tests/test_vault_rag_semantic.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_vault_rag_semantic.py
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest


def test_semantic_search_returns_dict_list(tmp_path):
    """semantic_search가 올바른 dict 구조를 반환한다."""
    from auto_agent.orchestrator.vault_rag import VaultRAG

    # VaultIndexer를 mock하여 Chroma 없이 테스트
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["스토리텔링 내용"]],
        "metadatas": [[{"file": "01-patterns/hooks/도입부.md", "tags": "hook,opening", "folder": "01-patterns"}]],
        "distances": [[0.15]],
    }

    with patch("auto_agent.orchestrator.vault_rag.VaultRAG._get_collection", return_value=mock_collection):
        rag = VaultRAG(vault_dir=tmp_path)
        rag.enabled = True
        results = rag.semantic_search("브랜드 스토리 후킹", top_k=3)

    assert isinstance(results, list)
    assert len(results) == 1
    result = results[0]
    assert "file" in result
    assert "snippet" in result
    assert "score" in result
    assert "tags" in result
    assert isinstance(result["score"], float)
    assert result["score"] >= 0.0


def test_semantic_search_falls_back_to_keyword_when_no_chroma(tmp_path):
    """Chroma 없으면 키워드 검색으로 폴백하고 동일한 dict 구조를 반환한다."""
    # 실제 .md 파일 생성
    patterns = tmp_path / "01-patterns" / "hooks"
    patterns.mkdir(parents=True)
    (patterns / "도입부-후킹-패턴.md").write_text(
        "# 도입부 후킹\n브랜드 스토리 후킹 방법", encoding="utf-8"
    )

    from auto_agent.orchestrator.vault_rag import VaultRAG

    with patch("auto_agent.orchestrator.vault_rag.VaultRAG._get_collection", side_effect=ImportError):
        rag = VaultRAG(vault_dir=tmp_path)
        rag.enabled = True
        results = rag.semantic_search("브랜드 스토리", top_k=5)

    assert isinstance(results, list)
    if results:
        assert "file" in results[0]
        assert "score" in results[0]
        assert results[0]["score"] == 0.0  # 키워드 폴백은 점수 0


def test_semantic_search_with_folder_filter(tmp_path):
    """folder_filter가 Chroma where 절에 적용된다."""
    from auto_agent.orchestrator.vault_rag import VaultRAG

    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [[]], "metadatas": [[]], "distances": [[]]
    }

    with patch("auto_agent.orchestrator.vault_rag.VaultRAG._get_collection", return_value=mock_collection):
        rag = VaultRAG(vault_dir=tmp_path)
        rag.enabled = True
        rag.semantic_search("후킹", top_k=5, folder_filter="01-patterns")

    call_kwargs = mock_collection.query.call_args[1]
    assert call_kwargs.get("where") == {"folder": "01-patterns"}
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
python -m pytest tests/test_vault_rag_semantic.py -v
```
Expected: FAIL

- [ ] **Step 3: VaultRAG에 `_get_collection` + `semantic_search` 추가**

`auto_agent/orchestrator/vault_rag.py`에 다음 메서드들을 `VaultRAG` 클래스 내 추가:

```python
def _get_collection(self):
    """Chroma 컬렉션 반환. ImportError 또는 미설치 시 예외 발생."""
    from auto_agent.orchestrator.vault_indexer import VaultIndexer, DEFAULT_CHROMA_DIR, COLLECTION_NAME
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.PersistentClient(path=str(DEFAULT_CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    return client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=ef)

def semantic_search(
    self,
    query: str,
    top_k: int = 5,
    folder_filter: str = None,
) -> list[dict]:
    """
    시맨틱 검색. Chroma 미설치 시 키워드 검색으로 폴백.
    반환: [{"file": str, "snippet": str, "score": float, "tags": list}]
    """
    if not self.enabled or not query.strip():
        return []

    try:
        collection = self._get_collection()
        where = {"folder": folder_filter} if folder_filter else None
        query_kwargs = {"query_texts": [query], "n_results": top_k}
        if where:
            query_kwargs["where"] = where

        raw = collection.query(**query_kwargs)
        results = []
        docs = raw.get("documents", [[]])[0]
        metas = raw.get("metadatas", [[]])[0]
        dists = raw.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            results.append({
                "file": meta.get("file", ""),
                "snippet": doc[:200] if doc else "",
                "score": round(1 - dist, 4),  # cosine: distance → similarity
                "tags": [t for t in meta.get("tags", "").split(",") if t],
            })
        return results

    except ImportError:
        print("[VaultRAG] Chroma/sentence-transformers 미설치, 키워드 폴백")
        return self._keyword_fallback(query, top_k)
    except Exception as e:
        print(f"[VaultRAG] 검색 오류 ({type(e).__name__}: {e}), 키워드 폴백")
        return self._keyword_fallback(query, top_k)

def _keyword_fallback(self, query: str, top_k: int) -> list[dict]:
    """키워드 검색 폴백. semantic_search와 동일한 dict 구조 반환."""
    raw = self.search_by_keyword(query, max_results=top_k)
    results = []
    for path, snippet in raw:
        try:
            file_str = str(path.relative_to(self.vault_dir))
        except ValueError:
            file_str = path.name
        results.append({"file": file_str, "snippet": snippet[:200], "score": 0.0, "tags": []})
    return results
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
python -m pytest tests/test_vault_rag_semantic.py -v
```
Expected: PASS

- [ ] **Step 5: `search_for_research` 시맨틱 검색 우선 적용**

`auto_agent/orchestrator/vault_rag.py`의 `search_for_research` 메서드 상단에 시맨틱 검색 블록 추가:

```python
def search_for_research(self, topic: str, category: str = "") -> str:
    if not self.enabled:
        return ""

    sections = []

    # Phase 2: 시맨틱 검색 우선 시도
    semantic_results = self.semantic_search(topic, top_k=5)
    if semantic_results:
        sections.append("## 관련 지식 (볼트 시맨틱 검색)")
        for r in semantic_results:
            sections.append(f"### {r['file']}\n{r['snippet']}\n")
        # 시맨틱 결과가 있으면 키워드 검색 스킵
        if sections:
            return (
                "<vault_knowledge>\n"
                "아래는 이전에 수행된 리서치 결과입니다.\n"
                "⚠️ 이미 확보된 정보를 다시 검색하지 마세요. 아래 내용을 기반으로:\n"
                "1. 기존 리서치의 핵심 팩트를 그대로 활용하세요\n"
                "2. 최신 정보(날짜/수치 변경, 새로운 사건)만 추가 검색하세요\n"
                "3. 기존 소스가 여전히 유효한지 교차 검증하세요\n"
                "4. 새로 발견된 정보만 추가 섹션으로 보고하세요\n\n"
                + "\n".join(sections)
                + "\n</vault_knowledge>"
            )

    # Phase 1 폴백: 기존 키워드 검색 (이하 기존 코드 유지)
    # ... (기존 _search_files 로직 그대로)
```

`search_for_manuscript`도 동일하게 시맨틱 우선 적용 (folder_filter="01-patterns").

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/orchestrator/vault_rag.py tests/test_vault_rag_semantic.py
git commit -m "feat: VaultRAG.semantic_search() 추가, search_for_research/manuscript 시맨틱 우선 적용"
```

---

## Chunk 3: CLI + 대시보드 API + UI

### Task 5: CLI `vault` 서브커맨드

**Files:**
- Modify: `auto_agent/cli.py`

- [ ] **Step 1: `auto_agent/cli.py`에 `cmd_vault` 함수 추가**

`COMMANDS` 딕셔너리 바로 위에 추가:

```python
def cmd_vault(args):
    """볼트 인덱스 관리: index / stats / search."""
    from auto_agent.orchestrator.vault_rag import VAULT_DIR

    sub = args[0] if args else "stats"

    if sub == "index":
        force = "--force" in args
        try:
            from auto_agent.orchestrator.vault_indexer import VaultIndexer
        except ImportError:
            print_error("RAG 의존성 미설치. 설치: pip install -e '.[rag]'")
            sys.exit(1)

        if not VAULT_DIR.exists():
            print_error(f"볼트를 찾을 수 없음: {VAULT_DIR}")
            sys.exit(1)

        console.print(f"[bold]볼트 인덱싱 시작[/bold]: {VAULT_DIR}")
        if force:
            console.print("[yellow]--force: 전체 재인덱싱[/yellow]")
        indexer = VaultIndexer()
        result = indexer.index_all(VAULT_DIR, force=force)
        console.print(f"[green]완료[/green] — 인덱싱: {result['indexed']}, "
                      f"스킵: {result['skipped']}, 오류: {result['errors']}, "
                      f"총 청크: {result['total_chunks']}")

    elif sub == "stats":
        try:
            from auto_agent.orchestrator.vault_indexer import VaultIndexer
            stats = VaultIndexer().get_stats()
            console.print(f"파일 수: {stats['file_count']}")
            console.print(f"청크 수: {stats['chunk_count']}")
            console.print(f"마지막 인덱싱: {stats['last_indexed_at'] or '없음'}")
            console.print(f"Chroma 경로: {stats['chroma_dir']}")
        except ImportError:
            print_error("RAG 의존성 미설치. 설치: pip install -e '.[rag]'")

    elif sub == "search":
        query = " ".join(a for a in args[1:] if not a.startswith("-"))
        if not query:
            print_error("사용법: auto-agent vault search <쿼리>")
            sys.exit(1)
        from auto_agent.orchestrator.vault_rag import VaultRAG
        rag = VaultRAG()
        results = rag.semantic_search(query, top_k=5)
        if not results:
            console.print("[yellow]결과 없음[/yellow]")
            return
        for r in results:
            console.print(f"\n[bold]{r['file']}[/bold] (유사도: {r['score']})")
            console.print(f"  {r['snippet'][:150]}...")
    else:
        console.print("사용법: auto-agent vault index|stats|search")
```

`COMMANDS`에 추가:
```python
COMMANDS = {
    ...
    "vault": cmd_vault,
}
```

- [ ] **Step 2: 수동 테스트**

```bash
auto-agent vault stats
auto-agent vault index
auto-agent vault search "브랜드 스토리 후킹"
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat: auto-agent vault index/stats/search CLI 명령어 추가"
```

---

### Task 6: 대시보드 검색 API

**Files:**
- Create: `auto_agent/dashboard/vault_routes.py`
- Modify: `app.py`

- [ ] **Step 1: `auto_agent/dashboard/vault_routes.py` 생성**

`memory_routes.py`와 동일한 패턴을 따른다:

```python
"""
대시보드 Vault RAG 검색 API.

Routes:
    GET /api/vault/search?q=쿼리&top_k=5&folder=01-patterns
    GET /api/vault/stats
"""
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(tags=["vault"])


@router.get("/api/vault/search")
async def vault_search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    folder: str = Query(None),
):
    """볼트 시맨틱 검색 API."""
    try:
        from auto_agent.orchestrator.vault_rag import VaultRAG
        rag = VaultRAG()
        if not rag.enabled:
            return JSONResponse({"results": [], "query": q, "total": 0, "mode": "disabled"})

        results = rag.semantic_search(q, top_k=top_k, folder_filter=folder)
        mode = "keyword" if all(r["score"] == 0.0 for r in results) else "semantic"
        return {"results": results, "query": q, "total": len(results), "mode": mode}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/api/vault/stats")
async def vault_stats():
    """볼트 인덱스 통계."""
    try:
        from auto_agent.orchestrator.vault_indexer import VaultIndexer
        return VaultIndexer().get_stats()
    except ImportError:
        return {"error": "RAG 미설치", "chunk_count": 0, "file_count": 0}
```

- [ ] **Step 2: `app.py`에 라우터 등록**

기존 `include_router` 블록 근처에 추가:

```python
from auto_agent.dashboard.vault_routes import router as vault_router
app.include_router(vault_router)
```

- [ ] **Step 3: API 동작 확인**

서버 실행 후:
```bash
curl "http://localhost:8000/api/vault/stats"
curl "http://localhost:8000/api/vault/search?q=브랜드+스토리&top_k=3"
```
Expected: JSON 응답

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/dashboard/vault_routes.py app.py
git commit -m "feat: 대시보드 /api/vault/search + /api/vault/stats API 추가"
```

---

### Task 7: 대시보드 검색 UI

**Files:**
- Create: `auto_agent/dashboard/templates/vault_search.html`
- Modify: `auto_agent/dashboard/templates/base.html`
- Modify: `app.py`

- [ ] **Step 1: `vault_search.html` 생성**

```html
{% extends "base.html" %}

{% block title %}볼트 검색 — Auto Agent{% endblock %}

{% block content %}
<div style="padding: 24px; max-width: 900px; margin: 0 auto;">
  <h2 style="color: #E4E4E7; margin-bottom: 8px;">📚 볼트 검색</h2>

  <!-- 검색 폼 -->
  <form id="vault-search-form" style="display:flex; gap:8px; margin-bottom:16px;">
    <input
      id="vault-query"
      type="text"
      placeholder="검색어 입력 (예: 브랜드 스토리 후킹)"
      style="flex:1; padding:10px 14px; background:#1C1C1E; border:1px solid #3F3F46;
             border-radius:8px; color:#E4E4E7; font-size:14px;"
    />
    <select id="vault-folder"
      style="padding:10px; background:#1C1C1E; border:1px solid #3F3F46;
             border-radius:8px; color:#E4E4E7; font-size:13px;">
      <option value="">전체 폴더</option>
      <option value="01-patterns">01-patterns</option>
      <option value="02-research">02-research</option>
      <option value="03-analysis">03-analysis</option>
      <option value="07-projects">07-projects</option>
      <option value="08-dev">08-dev</option>
    </select>
    <button type="submit"
      style="padding:10px 20px; background:#6366F1; border:none; border-radius:8px;
             color:white; font-size:14px; cursor:pointer;">검색</button>
  </form>

  <!-- 통계 -->
  <div id="vault-stats" style="font-size:12px; color:#71717A; margin-bottom:16px;">
    로딩 중...
  </div>

  <!-- 결과 -->
  <div id="vault-results"></div>
</div>

<script>
async function loadStats() {
  const res = await fetch('/api/vault/stats');
  const data = await res.json();
  document.getElementById('vault-stats').textContent =
    `인덱싱된 파일 ${data.file_count || 0}개 · 청크 ${data.chunk_count || 0}개 · 마지막 인덱싱: ${data.last_indexed_at || '없음'}`;
}

document.getElementById('vault-search-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const q = document.getElementById('vault-query').value.trim();
  const folder = document.getElementById('vault-folder').value;
  if (!q) return;

  document.getElementById('vault-results').innerHTML = '<p style="color:#71717A">검색 중...</p>';

  const params = new URLSearchParams({ q, top_k: 5 });
  if (folder) params.set('folder', folder);

  const res = await fetch(`/api/vault/search?${params}`);
  const data = await res.json();

  if (!data.results || data.results.length === 0) {
    document.getElementById('vault-results').innerHTML = '<p style="color:#71717A">결과 없음</p>';
    return;
  }

  const mode = data.mode === 'semantic' ? '🔍 시맨틱' : '📝 키워드';
  let html = `<p style="font-size:12px;color:#71717A;margin-bottom:12px">${mode} 검색 — ${data.total}건</p>`;

  for (const r of data.results) {
    const obsidianUrl = `obsidian://open?vault=kairos-vault&file=${encodeURIComponent(r.file)}`;
    const score = data.mode === 'semantic' ? `<span style="color:#6366F1;font-size:11px">${(r.score * 100).toFixed(0)}%</span>` : '';
    const tags = r.tags.map(t => `<span style="background:#27272A;padding:2px 6px;border-radius:4px;font-size:11px;color:#A1A1AA">${t}</span>`).join(' ');

    html += `
      <div style="background:#18181B;border:1px solid #27272A;border-radius:10px;padding:16px;margin-bottom:10px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <a href="${obsidianUrl}" style="color:#818CF8;font-size:13px;font-weight:600;text-decoration:none">${r.file}</a>
          ${score}
        </div>
        ${tags ? `<div style="margin-bottom:8px">${tags}</div>` : ''}
        <p style="color:#A1A1AA;font-size:13px;line-height:1.6;margin:0">${r.snippet}</p>
      </div>`;
  }

  document.getElementById('vault-results').innerHTML = html;
});

loadStats();
</script>
{% endblock %}
```

- [ ] **Step 2: `base.html` 네비게이션에 볼트 검색 링크 추가**

`base.html`의 사이드바 nav 섹션에 추가:
```html
<a href="/vault/search" class="sidebar-link">📚 볼트 검색</a>
```

- [ ] **Step 3: `app.py`에 페이지 라우트 추가**

```python
@app.get("/vault/search", response_class=HTMLResponse)
async def vault_search_page(request: Request):
    return templates.TemplateResponse("vault_search.html", {"request": request})
```

- [ ] **Step 4: 대시보드 실행 후 UI 확인**

```bash
auto-agent dashboard
```

브라우저에서 `http://localhost:8000/vault/search` 접속.
- 통계 로딩 확인
- 검색 폼 동작 확인
- 결과 카드 렌더링 확인

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/dashboard/templates/vault_search.html \
        auto_agent/dashboard/templates/base.html \
        app.py
git commit -m "feat: 대시보드 볼트 검색 UI 추가 (/vault/search)"
```

---

## 최종 통합 테스트

- [ ] **실제 볼트로 E2E 테스트**

```bash
# 1. 인덱싱
auto-agent vault index

# 2. 통계 확인
auto-agent vault stats

# 3. CLI 검색
auto-agent vault search "브랜드 스토리 후킹"

# 4. API 검색
curl "http://localhost:8000/api/vault/search?q=AI+반도체&top_k=3"

# 5. 기존 파이프라인 테스트 (폴백 동작 확인)
python -c "
from auto_agent.orchestrator.vault_rag import VaultRAG
rag = VaultRAG()
result = rag.search_for_research('AI 반도체', 'technology')
print(result[:500] if result else '결과 없음')
"
```

- [ ] **최종 커밋**

```bash
git add .
git commit -m "feat: Vault RAG Phase 2 완료 — 시맨틱 검색, CLI, 대시보드 UI"
```
