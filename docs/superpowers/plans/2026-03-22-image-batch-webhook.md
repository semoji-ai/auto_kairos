# 이미지 배치 생성 & 캐릭터 라이브러리 구현 플랜

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FAL AI 이미지 생성을 Claude CLI 에이전트 방식에서 FAL queue + 폴링 배치 방식으로 전환하고, 캐릭터를 글로벌 라이브러리(`~/.auto_agent/characters/`)에 저장해 프로젝트 간 재활용한다.

**Architecture:** 3개 신규 파일(`fal_queue.py`, `character_library.py`, `image_batch_module.py`) + `image_generate.py`에 입력 빌드 함수 추출 추가. 기존 에이전트(`image-painter`)는 `step_8b_legacy`로 보존해 롤백 가능. `runner.py`의 `script_map`에 `image_batch` 추가.

**Tech Stack:** Python 3.12, fal-client SDK (queue API), Pillow (PNG tEXt 청크), SQLite (`~/.auto_agent/characters.db`), 기존 `image_generate.py` / `image_assets.py` 재사용

**Spec:** `docs/superpowers/specs/2026-03-21-image-batch-webhook-design.md`

---

## 파일 구조 요약

| 파일 | 신규/수정 | 역할 |
|------|-----------|------|
| `auto_agent/tools/fal_queue.py` | 신규 | FAL submit_batch / poll_all |
| `auto_agent/tools/character_library.py` | 신규 | 캐릭터 라이브러리 (PNG tEXt + SQLite) |
| `auto_agent/modules/image_batch_module.py` | 신규 | 파이프라인 진입점 — Phase1 캐릭터 + Phase2 씬 |
| `auto_agent/tools/image_generate.py` | 수정 | `_build_character_fal_input()`, `_build_scene_fal_input()` 추출 추가 |
| `auto_agent/orchestrator/runner.py` | 수정 | `script_map`에 `image_batch` 추가 |
| `auto_agent/data/pipeline.json` | 수정 | step_8b → image_batch 모듈, 기존은 step_8b_legacy |
| `auto_agent/scripts/migrate_characters.py` | 신규 | 기존 프로젝트 캐릭터 일괄 등록 |
| `tests/test_fal_queue.py` | 신규 | fal_queue 단위 테스트 |
| `tests/test_character_library.py` | 신규 | character_library 단위 테스트 |
| `tests/test_image_batch_module.py` | 신규 | image_batch_module 단위 테스트 |

---

## Chunk 1: fal_queue.py — FAL 비동기 큐 클라이언트

### Task 1: fal_queue.py — FalJob / FalResult 데이터클래스 + submit_batch

**Files:**
- Create: `auto_agent/tools/fal_queue.py`
- Create: `tests/test_fal_queue.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_fal_queue.py
import pytest
from unittest.mock import MagicMock, patch
from auto_agent.tools.fal_queue import FalJob, FalResult, submit_batch

def test_submit_batch_returns_request_ids():
    """submit_batch가 job당 request_id를 반환한다."""
    mock_handle = MagicMock()
    mock_handle.request_id = "req-abc123"

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.submit.return_value = mock_handle
        jobs = [
            FalJob(idx=0, endpoint="fal-ai/nano-banana-2", arguments={"prompt": "test"}),
            FalJob(idx=1, endpoint="fal-ai/nano-banana-2", arguments={"prompt": "test2"}),
        ]
        ids = submit_batch(jobs)

    assert len(ids) == 2
    assert ids[0] == "req-abc123"
    assert mock_fal.submit.call_count == 2

def test_submit_batch_empty():
    """빈 job 목록이면 빈 리스트 반환."""
    with patch("auto_agent.tools.fal_queue.fal_client"):
        result = submit_batch([])
    assert result == []
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
source .venv/bin/activate
pytest tests/test_fal_queue.py -v
```
Expected: `ImportError: cannot import name 'FalJob'`

- [ ] **Step 3: fal_queue.py 구현 (submit_batch)**

```python
# auto_agent/tools/fal_queue.py
"""FAL AI queue 비동기 클라이언트 — submit_batch / poll_all."""
from __future__ import annotations
import os
import logging
import time
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)

try:
    import fal_client
    FAL_AVAILABLE = True
except ImportError:
    fal_client = None
    FAL_AVAILABLE = False


def _ensure_fal_key():
    """FAL_API_KEY → FAL_KEY 자동 매핑."""
    if not os.environ.get("FAL_KEY") and os.environ.get("FAL_API_KEY"):
        os.environ["FAL_KEY"] = os.environ["FAL_API_KEY"]


@dataclass
class FalJob:
    idx: int
    endpoint: str
    arguments: dict


@dataclass
class FalResult:
    idx: int
    success: bool
    images: list = field(default_factory=list)  # [{"url":..,"width":..,"height":..}]
    error: str | None = None


def submit_batch(jobs: list[FalJob]) -> list[str]:
    """모든 job을 FAL queue에 제출. request_id 목록 반환."""
    if not jobs:
        return []
    if not FAL_AVAILABLE:
        raise RuntimeError("fal_client 미설치. pip install fal-client")
    _ensure_fal_key()

    request_ids: list[str] = []
    for job in jobs:
        handle = fal_client.submit(job.endpoint, arguments=job.arguments)
        request_ids.append(handle.request_id)
        logger.debug("submitted job %d → %s", job.idx, handle.request_id)
    return request_ids
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_fal_queue.py::test_submit_batch_returns_request_ids tests/test_fal_queue.py::test_submit_batch_empty -v
```
Expected: PASS 2개

---

### Task 2: fal_queue.py — poll_all (완료/실패/재시도/타임아웃)

**Files:**
- Modify: `auto_agent/tools/fal_queue.py`
- Modify: `tests/test_fal_queue.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_fal_queue.py 에 추가
from auto_agent.tools.fal_queue import poll_all

def _make_jobs(n: int) -> list:
    from auto_agent.tools.fal_queue import FalJob
    return [FalJob(idx=i, endpoint="ep", arguments={}) for i in range(n)]

def test_poll_all_completes_all():
    """모든 job이 COMPLETED로 완료되면 on_done이 각각 호출된다."""
    from unittest.mock import MagicMock, patch
    jobs = _make_jobs(2)
    request_ids = ["req-0", "req-1"]
    done_results = []

    fake_status = MagicMock()
    fake_status.status = "COMPLETED"
    fake_result = {"images": [{"url": "http://x.com/img.png", "width": 512, "height": 512}]}

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.return_value = fake_status
        mock_fal.result.return_value = fake_result
        poll_all(jobs, request_ids, on_done=done_results.append)

    assert len(done_results) == 2
    assert all(r.success for r in done_results)

def test_poll_all_retries_on_failure():
    """FAILED 시 max_retries만큼 재제출하고 그래도 실패하면 success=False."""
    from unittest.mock import MagicMock, patch, call
    jobs = _make_jobs(1)
    request_ids = ["req-0"]
    done_results = []

    new_handle = MagicMock()
    new_handle.request_id = "req-retry"

    call_count = {"n": 0}
    def fake_status(req_id):
        s = MagicMock()
        s.status = "FAILED"
        return s

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.side_effect = fake_status
        mock_fal.submit.return_value = new_handle
        poll_all(jobs, request_ids, on_done=done_results.append, max_retries=1)

    assert len(done_results) == 1
    assert not done_results[0].success
    assert mock_fal.submit.call_count == 1  # 1번 재제출

def test_poll_all_timeout():
    """timeout 초과 시 미완료 job이 success=False로 처리된다."""
    from unittest.mock import MagicMock, patch
    jobs = _make_jobs(1)
    request_ids = ["req-0"]
    done_results = []

    fake_status = MagicMock()
    fake_status.status = "IN_QUEUE"

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.return_value = fake_status
        with patch("auto_agent.tools.fal_queue.time") as mock_time:
            mock_time.time.side_effect = [0, 0, 9999]  # 즉시 timeout
            mock_time.sleep = MagicMock()
            poll_all(jobs, request_ids, on_done=done_results.append, timeout=1.0)

    assert len(done_results) == 1
    assert not done_results[0].success
    assert "timeout" in (done_results[0].error or "")

def test_poll_all_callback_exception_continues():
    """on_done 콜백에서 예외 발생해도 폴링 루프가 계속된다."""
    from unittest.mock import MagicMock, patch
    jobs = _make_jobs(2)
    request_ids = ["req-0", "req-1"]
    success_count = {"n": 0}

    fake_status = MagicMock()
    fake_status.status = "COMPLETED"
    fake_result = {"images": [{"url": "http://x.com/img.png", "width": 512, "height": 512}]}

    def on_done(r):
        if r.idx == 0:
            raise ValueError("저장 실패")
        success_count["n"] += 1

    with patch("auto_agent.tools.fal_queue.fal_client") as mock_fal:
        mock_fal.status.return_value = fake_status
        mock_fal.result.return_value = fake_result
        poll_all(jobs, request_ids, on_done=on_done)

    assert success_count["n"] == 1  # idx=1은 정상 처리됨
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_fal_queue.py -v -k "poll"
```
Expected: `ImportError: cannot import name 'poll_all'`

- [ ] **Step 3: poll_all 구현**

```python
# auto_agent/tools/fal_queue.py 에 추가

def poll_all(
    jobs: list[FalJob],
    request_ids: list[str],
    on_done: Callable[[FalResult], None],
    poll_interval: float = 2.0,
    timeout: float = 3600.0,
    max_retries: int = 2,
) -> list[FalResult]:
    """모든 request_id 폴링. 완료마다 on_done 콜백 호출."""
    if not jobs:
        return []
    if not FAL_AVAILABLE:
        raise RuntimeError("fal_client 미설치. pip install fal-client")
    _ensure_fal_key()

    # pending: {request_id: (job, retry_count)}
    pending: dict[str, tuple[FalJob, int]] = {
        rid: (job, 0) for rid, job in zip(request_ids, jobs)
    }
    all_results: list[FalResult] = []
    start = time.time()

    while pending and (time.time() - start) < timeout:
        time.sleep(poll_interval)
        for req_id in list(pending):
            job, retry_count = pending[req_id]
            try:
                status_obj = fal_client.status(req_id)
                status = status_obj.status
            except Exception as e:
                logger.warning("status 조회 실패 (req=%s): %s", req_id, e)
                continue

            if status == "COMPLETED":
                try:
                    raw = fal_client.result(req_id)
                    result = FalResult(
                        idx=job.idx,
                        success=True,
                        images=raw.get("images", []),
                    )
                    try:
                        on_done(result)
                    except Exception as cb_err:
                        logger.warning("on_done 콜백 실패 (job %d): %s", job.idx, cb_err)
                    all_results.append(result)
                except Exception as e:
                    result = FalResult(idx=job.idx, success=False, error=str(e))
                    try:
                        on_done(result)
                    except Exception:
                        pass
                    all_results.append(result)
                del pending[req_id]

            elif status == "FAILED":
                if retry_count < max_retries:
                    try:
                        new_handle = fal_client.submit(job.endpoint, arguments=job.arguments)
                        del pending[req_id]
                        pending[new_handle.request_id] = (job, retry_count + 1)
                        logger.info("job %d 재제출 (retry %d): %s", job.idx, retry_count + 1, new_handle.request_id)
                    except Exception as e:
                        logger.warning("재제출 실패 (job %d): %s", job.idx, e)
                        del pending[req_id]
                        result = FalResult(idx=job.idx, success=False, error=f"재제출 실패: {e}")
                        try:
                            on_done(result)
                        except Exception:
                            pass
                        all_results.append(result)
                else:
                    del pending[req_id]
                    result = FalResult(idx=job.idx, success=False, error="max_retries 초과")
                    try:
                        on_done(result)
                    except Exception:
                        pass
                    all_results.append(result)

    # timeout 초과 잔여
    for req_id, (job, _) in pending.items():
        result = FalResult(idx=job.idx, success=False, error="timeout")
        try:
            on_done(result)
        except Exception:
            pass
        all_results.append(result)

    return all_results
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/test_fal_queue.py -v
```
Expected: PASS 6개

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/fal_queue.py tests/test_fal_queue.py
git commit -m "feat: fal_queue.py — FAL 비동기 submit_batch / poll_all 구현"
```

---

## Chunk 2: character_library.py — 캐릭터 글로벌 라이브러리

### Task 3: character_library.py — PNG tEXt embed/read + DB 스키마

**Files:**
- Create: `auto_agent/tools/character_library.py`
- Create: `tests/test_character_library.py`

**사전 지식:**
- Pillow로 PNG tEXt 청크 쓰기: `PngImagePlugin.PngInfo` → `img.save(path, pnginfo=info)`
- Pillow로 PNG tEXt 읽기: `Image.open(path).text` → `dict[str, str]`
- DB 경로: `~/.auto_agent/characters.db` (프로젝트 `auto_agent.db`와 분리)

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_character_library.py
import pytest
import sqlite3
from pathlib import Path
from PIL import Image
from auto_agent.tools.character_library import (
    CharacterLibrary, CharacterRecord, embed_png_metadata, read_png_metadata
)

@pytest.fixture
def tmp_library(tmp_path):
    """임시 라이브러리 인스턴스 (격리된 디렉토리 사용)."""
    lib = CharacterLibrary(
        library_dir=tmp_path / "characters",
        db_path=tmp_path / "characters.db",
    )
    return lib

@pytest.fixture
def sample_png(tmp_path) -> Path:
    """1×1 검은 PNG 파일."""
    p = tmp_path / "test.png"
    Image.new("RGB", (1, 1)).save(p)
    return p

def test_embed_and_read_metadata(sample_png):
    """PNG tEXt 청크에 메타데이터를 embed하고 다시 읽을 수 있다."""
    meta = {
        "character_name": "일론 머스크",
        "art_style": "quirky_cartoon",
        "tags": "기업인,테슬라",
        "features": "짧은 머리, 정장",
        "source_project": "test_proj",
    }
    embed_png_metadata(sample_png, meta)
    result = read_png_metadata(sample_png)
    assert result["character_name"] == "일론 머스크"
    assert result["art_style"] == "quirky_cartoon"
    assert result["tags"] == "기업인,테슬라"

def test_library_dir_created_on_init(tmp_path):
    """CharacterLibrary 초기화 시 디렉토리와 DB가 자동 생성된다."""
    lib_dir = tmp_path / "chars"
    db_path = tmp_path / "chars.db"
    assert not lib_dir.exists()
    CharacterLibrary(library_dir=lib_dir, db_path=db_path)
    assert lib_dir.exists()
    assert db_path.exists()

def test_db_schema_created(tmp_library):
    """초기화 후 characters 테이블이 존재한다."""
    conn = sqlite3.connect(str(tmp_library.db_path))
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "characters" in tables
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_character_library.py -v
```
Expected: `ImportError: cannot import name 'CharacterLibrary'`

- [ ] **Step 3: character_library.py 기반 구현 (embed/read/init)**

```python
# auto_agent/tools/character_library.py
"""캐릭터 글로벌 라이브러리 — PNG tEXt 메타데이터 + SQLite 인덱스."""
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

_META_KEYS = ("character_name", "art_style", "tags", "features", "source_project", "created_at")


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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_character_library.py::test_embed_and_read_metadata tests/test_character_library.py::test_library_dir_created_on_init tests/test_character_library.py::test_db_schema_created -v
```
Expected: PASS 3개

---

### Task 4: character_library.py — register / search / copy_to_project

**Files:**
- Modify: `auto_agent/tools/character_library.py`
- Modify: `tests/test_character_library.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_character_library.py 에 추가

def test_register_adds_to_db_and_library(tmp_library, sample_png):
    """register()가 PNG를 라이브러리에 복사하고 DB에 레코드를 추가한다."""
    meta = {
        "character_name": "홍길동",
        "art_style": "quirky_cartoon",
        "tags": "영웅,조선시대",
        "features": "갓과 도포 착용, 의협심 강한 표정",
        "source_project": "test",
    }
    record = tmp_library.register(sample_png, meta)
    assert record.name == "홍길동"
    assert Path(record.file_path).exists()
    assert Path(record.file_path).parent == tmp_library.library_dir

def test_register_duplicate_features_skips(tmp_library, sample_png):
    """features_hash가 동일하면 두 번째 register는 기존 레코드를 반환한다."""
    meta = {
        "character_name": "홍길동",
        "art_style": "quirky_cartoon",
        "tags": "영웅",
        "features": "갓과 도포",
        "source_project": "test",
    }
    r1 = tmp_library.register(sample_png, meta)
    r2 = tmp_library.register(sample_png, meta)
    assert r1.id == r2.id  # 같은 레코드

def test_register_different_features_creates_new_record(tmp_library, sample_png, tmp_path):
    """features가 다르면 같은 이름+스타일이라도 별도 레코드를 생성한다."""
    base_meta = {"character_name": "일론 머스크", "art_style": "quirky_cartoon", "source_project": "t"}
    png2 = tmp_path / "test2.png"
    Image.new("RGB", (1, 1)).save(png2)

    r1 = tmp_library.register(sample_png, {**base_meta, "features": "젊은 시절, 청바지", "tags": ""})
    r2 = tmp_library.register(png2,       {**base_meta, "features": "현재 모습, 정장", "tags": ""})
    assert r1.id != r2.id

def test_search_returns_exact_match(tmp_library, sample_png):
    """name + art_style이 일치하는 레코드를 찾는다."""
    tmp_library.register(sample_png, {
        "character_name": "김철수",
        "art_style": "watercolor",
        "tags": "학생",
        "features": "교복",
        "source_project": "s1",
    })
    result = tmp_library.search("김철수", "watercolor")
    assert result is not None
    assert result.name == "김철수"

def test_search_returns_none_for_missing(tmp_library):
    """등록되지 않은 캐릭터는 None을 반환한다."""
    result = tmp_library.search("없는캐릭터", "any_style")
    assert result is None

def test_search_tags_score(tmp_library, sample_png, tmp_path):
    """복수 후보 중 tags 포함도가 높은 레코드를 우선 반환한다."""
    base = {"character_name": "박영희", "art_style": "comic", "source_project": "t"}
    png2 = tmp_path / "t2.png"; Image.new("RGB", (1,1)).save(png2)
    png3 = tmp_path / "t3.png"; Image.new("RGB", (1,1)).save(png3)

    tmp_library.register(sample_png, {**base, "features": "A", "tags": "과학자"})
    tmp_library.register(png2,       {**base, "features": "B", "tags": "과학자,교수,노벨상"})
    tmp_library.register(png3,       {**base, "features": "C", "tags": "교수"})

    result = tmp_library.search("박영희", "comic", tags=["과학자", "노벨상"])
    assert "노벨상" in result.tags  # features B가 가장 높은 점수

def test_copy_to_project(tmp_library, sample_png, tmp_path):
    """copy_to_project()가 프로젝트 characters/ 디렉토리에 파일을 복사한다."""
    record = tmp_library.register(sample_png, {
        "character_name": "테스트",
        "art_style": "comic",
        "tags": "",
        "features": "test",
        "source_project": "s",
    })
    project_dir = tmp_path / "project"
    dest = tmp_library.copy_to_project(record, project_dir)
    assert dest.exists()
    assert dest.parent == project_dir / "characters"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_character_library.py -v -k "register or search or copy"
```
Expected: FAIL (함수 미구현)

- [ ] **Step 3: register / search / copy_to_project 구현**

`CharacterLibrary` 클래스에 메서드 추가:

```python
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

        # tags 포함도 점수
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

    def _row_to_record(self, row) -> CharacterRecord:
        return CharacterRecord(
            id=row["id"], name=row["name"], art_style=row["art_style"],
            tags=row["tags"] or "", features=row["features"] or "",
            features_hash=row["features_hash"] or "",
            file_path=Path(row["file_path"]),
            source_project=row["source_project"] or "",
            created_at=row["created_at"],
        )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_character_library.py -v
```
Expected: PASS (전체)

---

### Task 5: character_library.py — rebuild_index

**Files:**
- Modify: `auto_agent/tools/character_library.py`
- Modify: `tests/test_character_library.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_character_library.py 에 추가

def test_rebuild_index_restores_db(tmp_library, sample_png, tmp_path):
    """DB 삭제 후 rebuild_index()가 PNG tEXt에서 레코드를 복원한다."""
    tmp_library.register(sample_png, {
        "character_name": "복원테스트",
        "art_style": "test_style",
        "tags": "a,b",
        "features": "복원 피처",
        "source_project": "x",
    })
    # DB 삭제
    tmp_library.db_path.unlink()
    tmp_library._init_db()

    count = tmp_library.rebuild_index()
    assert count == 1
    result = tmp_library.search("복원테스트", "test_style")
    assert result is not None

def test_rebuild_index_skips_no_metadata_png(tmp_library, tmp_path):
    """tEXt 청크 없는 PNG는 건너뛰고 오류를 내지 않는다."""
    plain_png = tmp_library.library_dir / "no_meta.png"
    Image.new("RGB", (1, 1)).save(plain_png)

    count = tmp_library.rebuild_index()
    assert count == 0  # 메타 없는 파일은 스킵
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_character_library.py::test_rebuild_index_restores_db tests/test_character_library.py::test_rebuild_index_skips_no_metadata_png -v
```
Expected: FAIL

- [ ] **Step 3: rebuild_index 구현**

```python
    def rebuild_index(self) -> int:
        """LIBRARY_DIR 스캔 → PNG tEXt에서 DB 재구성. 복구된 레코드 수 반환."""
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
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/test_character_library.py -v
```
Expected: 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/tools/character_library.py tests/test_character_library.py
git commit -m "feat: character_library.py — PNG tEXt 메타데이터 + SQLite 글로벌 캐릭터 라이브러리"
```

---

## Chunk 3: image_generate.py — 입력 빌드 함수 추출

### Task 6: _build_character_fal_input / _build_scene_fal_input 추출

**Files:**
- Modify: `auto_agent/tools/image_generate.py`

**핵심:** 기존 `generate_character()`, `generate_scene()`, `generate_scene_flat()`, `generate_viz_background()`에서 `_call_fal()` 호출 직전까지의 로직을 두 함수로 추출. **기존 함수는 전혀 수정하지 않는다** — 이들은 그대로 레거시 에이전트에서 사용됨.

- [ ] **Step 1: _build_character_fal_input 추가**

`generate_character()` 직후에 추가 (L395 아래):

```python
def _build_character_fal_input(
    prompt: str,
    style_path: str,
    person_photo: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> tuple[str, dict]:
    """캐릭터 FAL 입력 빌드. generate_character()와 동일한 로직, _call_fal 직전에서 중단.

    Returns:
        (endpoint, fal_input) — fal_queue.submit_batch()에 전달할 값
    """
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    historical_period = art_style.get("historical_period", "")
    critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])

    prompt = _enrich_historical_context(prompt, historical_period)
    image_urls = []

    ref_image = art_style.get("reference_image", "")
    if ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))
    if person_photo and Path(person_photo).exists():
        image_urls.append(_image_to_data_uri(person_photo))

    parts = []
    if scene_style_desc:
        parts.append(scene_style_desc + "\n\n")
    parts.append(f"Style specification: {style_json_str}\n\n")
    if critical_reqs:
        parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs) + "\n\n")
    if len(image_urls) >= 2:
        parts.append(
            "**REFERENCE IMAGE GUIDE:**\n"
            "- FIRST image = ART STYLE reference. Match this style:\n"
            "  • Same eye drawing style, line weight, and body proportions\n"
            "  • Same color palette and flat shading approach\n"
            "- SECOND image = PERSON reference for facial features only\n"
            "- Draw the person from the second image IN THE STYLE of the first image\n\n"
        )
    elif len(image_urls) == 1:
        parts.append(
            "**STYLE REFERENCE:**\n"
            "The attached image defines the art style. Match this style:\n"
            "- Same eye drawing style, line weight, and body proportions\n"
            "- Same color palette and flat shading approach\n"
            "- Create a NEW character drawn in this same style\n\n"
        )
    parts.append(f"Character illustration:\n{prompt}\n\n")
    parts.append("No text, letters, numbers, captions, watermarks, or speech bubbles in the image.")

    full_prompt = "".join(parts)
    endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls
    return endpoint, fal_input
```

- [ ] **Step 2: _build_scene_fal_input 추가**

`generate_scene_flat()` 직후에 추가 (L654 아래):

```python
def _build_scene_fal_input(
    scene: dict,
    project_dir: Path,
    char_paths: Optional[Dict[str, Optional[Path]]] = None,
    style_path: Optional[str] = None,
) -> tuple[str, dict]:
    """씬 FAL 입력 빌드. (endpoint, fal_input) 반환.

    Args:
        scene: scene_specs.json의 씬 딕셔너리
        project_dir: 프로젝트 디렉토리 (art_style.json 경로 탐색용)
        char_paths: {char_id: Path | None} — None이면 해당 캐릭터 참조 없이 생성
        style_path: art_style.json 경로. None이면 project_dir/art_style.json 사용.

    viz_background 씬 타입이면 generate_viz_background와 동일한 입력 빌드.
    캐릭터 없는 씬은 generate_scene_flat, 있는 씬은 generate_scene 로직 사용.
    """
    if style_path is None:
        style_path = str(project_dir / "art_style.json")

    image_asset = scene.get("imageAsset") or {}
    scene_type  = image_asset.get("sceneType", "")

    # viz_background 타입: 배경 전용 빌드
    if scene_type == "viz_background":
        creative = scene.get("creative") or {}
        viz      = scene.get("visualization") or {}
        return _build_viz_fal_input(
            viz_title=creative.get("headline", scene.get("title", "")),
            viz_type=viz.get("type", ""),
            thematic_context=scene.get("narration", ""),
            style_path=style_path,
            aspect_ratio=image_asset.get("aspectRatio", "16:9"),
        )

    # 일반 씬
    prompt          = scene.get("imageAsset", {}).get("prompt") or scene.get("narration", "")
    characters_info = scene.get("imageAsset", {}).get("charactersInfo", "")
    background      = scene.get("imageAsset", {}).get("background", "")
    camera          = scene.get("imageAsset", {}).get("camera", "")
    aspect_ratio    = image_asset.get("aspectRatio", "16:9")
    staging         = image_asset.get("stagingStyle", "cinematic")

    # 유효한 캐릭터 경로만 추출
    char_path_strs: list[str] = []
    if char_paths:
        for cid, cp in char_paths.items():
            if cp and Path(cp).exists():
                char_path_strs.append(str(cp))

    if staging == "flat" or not char_path_strs:
        # generate_scene_flat 로직 재사용
        art_style = _load_art_style(style_path)
        style_json_str = _get_style_json_str(art_style)
        scene_style_desc = art_style.get("scene_style_description", "")
        historical_period = art_style.get("historical_period", "")
        ref_image = art_style.get("reference_image", "")
        critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])

        image_urls: list[str] = []
        has_char = False
        if char_path_strs:
            for cp in char_path_strs:
                image_urls.append(_image_to_data_uri(cp))
            has_char = True
        elif ref_image and Path(ref_image).exists():
            image_urls.append(_image_to_data_uri(ref_image))

        prompt = _enrich_historical_context(prompt, historical_period)
        scene_desc = _filter_text_descriptions(prompt)

        parts = []
        if scene_style_desc:
            parts.append(scene_style_desc)
        parts.append(style_json_str)
        if critical_reqs:
            parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs))
        parts.append(FLAT_STAGING_RULES)
        parts.append(scene_desc)
        if has_char:
            parts.append(
                "**Character Reference Rules:**\n"
                "- Use reference images ONLY for face and clothing appearance\n"
                "- ALL characters MUST face FORWARD (frontal view)"
            )
        struct = []
        if characters_info:
            struct.append(f"Character: {characters_info}")
        if background:
            struct.append(f"Background: {background} — fills entire canvas edge-to-edge, no empty space")
        struct.append("Camera: Front view, eye-level, centered, flat composition")
        parts.append("\n".join(struct))
        parts.append(
            "IMPORTANT: Do NOT include any text, letters, numbers, words, captions, "
            "watermarks, signatures, or any written characters in the image."
        )
        full_prompt = _translate_to_english("\n\n".join(parts))
        endpoint = ENDPOINT_CHARACTER if image_urls else ENDPOINT_GENERATE
        fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
        if image_urls:
            fal_input["image_urls"] = image_urls
        return endpoint, fal_input

    else:
        # cinematic — generate_scene 로직 재사용 (char_path_strs 있음)
        art_style = _load_art_style(style_path)
        style_json_str = _get_style_json_str(art_style)
        scene_style_desc = art_style.get("scene_style_description", "")
        historical_period = art_style.get("historical_period", "")
        critical_reqs = art_style.get("technical", {}).get("critical_requirements", [])

        image_urls = [_image_to_data_uri(cp) for cp in char_path_strs]
        prompt = _enrich_historical_context(prompt, historical_period)
        scene_desc = _filter_text_descriptions(prompt)

        parts = []
        if scene_style_desc:
            parts.append(scene_style_desc)
        parts.append(style_json_str)
        if critical_reqs:
            parts.append("**CRITICAL STYLE REQUIREMENTS:**\n" + "\n".join(f"- {r}" for r in critical_reqs))
        parts.append(scene_desc)
        parts.append(
            "**Character Reference Rules:**\n"
            "- Use reference images ONLY for face and clothing appearance\n"
            "- Do NOT copy the pose from reference images!\n"
            "- Maintain consistent eye, nose, mouth, and body proportions"
        )
        struct = []
        if characters_info:
            struct.append(f"Character: {characters_info}")
        if background:
            struct.append(f"Background: {background}")
        if camera:
            struct.append(f"Camera: {camera}")
        if struct:
            struct.append(
                "**Important: Maintain character body proportions, "
                "refer to reference image for each character's face"
            )
            parts.append("\n".join(struct))
        parts.append(
            "IMPORTANT: Do NOT include any text, letters, numbers, words, captions, "
            "watermarks, signatures, or any written characters in the image."
        )
        full_prompt = _translate_to_english("\n\n".join(parts))
        fal_input = {"prompt": full_prompt, "aspect_ratio": aspect_ratio, "image_urls": image_urls}
        return ENDPOINT_CHARACTER, fal_input


def _build_viz_fal_input(
    viz_title: str,
    viz_type: str,
    thematic_context: str,
    style_path: str,
    aspect_ratio: str = "16:9",
) -> tuple[str, dict]:
    """viz_background 씬 FAL 입력 빌드. generate_viz_background()와 동일 로직."""
    art_style = _load_art_style(style_path)
    style_json_str = _get_style_json_str(art_style)
    scene_style_desc = art_style.get("scene_style_description", "")
    ref_image = art_style.get("reference_image", "")

    image_urls = []
    if ref_image and Path(ref_image).exists():
        image_urls.append(_image_to_data_uri(ref_image))

    viz_mood = {
        "bar_chart": "abstract shapes suggesting comparison and scale",
        "line_chart": "flowing lines and gradual progression",
        "pie_chart": "circular patterns and proportional segments",
        "timeline": "sequential flow and historical progression",
        "table_view": "organized grid-like patterns",
        "tech_tree": "branching connections and nodes",
        "compare_card": "balanced duality, two sides",
        "quote_card": "contemplative, open space for text",
        "list_card": "organized, structured layout atmosphere",
        "numbered_list": "sequential, step-by-step visual rhythm",
        "icon_grid": "organized grid with thematic elements",
        "icon_flow": "flowing process, connected steps",
    }.get(viz_type, "abstract decorative background")

    parts = []
    if scene_style_desc:
        parts.append(scene_style_desc)
    parts.append(style_json_str)
    parts.append(
        f"Create a decorative BACKGROUND illustration for a data visualization.\n\n"
        f"**Topic:** {viz_title}\n"
        f"**Context:** {thematic_context}\n"
        f"**Visual mood:** {viz_mood}\n\n"
        "**CRITICAL BACKGROUND REQUIREMENTS:**\n"
        "- This is a BACKGROUND image — data/charts will be overlaid on top\n"
        "- Use SOFT, MUTED, slightly desaturated colors\n"
        "- Keep the CENTER area relatively EMPTY and SIMPLE\n"
        "- Place decorative elements toward EDGES and CORNERS\n"
        "- NO specific characters in focus, NO faces\n"
        "- Think of it like a soft, blurred backdrop or wallpaper"
    )
    if image_urls:
        parts.append(
            "**STYLE REFERENCE ONLY:**\n"
            "The attached reference image is ONLY for art style.\n"
            "- COPY: Color palette, texture, rendering style\n"
            "- NEVER COPY: Any character, person, figure"
        )
    parts.append(
        f"aspect ratio {aspect_ratio}\n"
        "IMPORTANT: Do NOT include any text, letters, numbers in the image."
    )
    full_prompt = _translate_to_english("\n\n".join(parts))
    fal_input: dict = {"prompt": full_prompt, "aspect_ratio": aspect_ratio}
    if image_urls:
        fal_input["image_urls"] = image_urls
    return ENDPOINT_EDIT, fal_input
```

- [ ] **Step 3: 기존 함수 동작 보존 확인 (회귀 테스트)**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
source .venv/bin/activate
python3 -c "
from auto_agent.tools.image_generate import (
    generate_character, generate_scene, generate_scene_flat,
    _build_character_fal_input, _build_scene_fal_input
)
# 기존 함수가 import되면 OK
print('import OK')
# 빌드 함수 smoke test (실제 FAL 호출 없이)
import tempfile, json
from pathlib import Path
with tempfile.TemporaryDirectory() as d:
    # art_style.json 생성 (최소)
    style = {
      'id': 'test', 'name': 'test',
      'reference_image': '',
      'scene_style_description': 'cartoon',
      'technical': {'critical_requirements': []}
    }
    sp = Path(d) / 'art_style.json'
    sp.write_text(json.dumps(style))
    ep, fi = _build_character_fal_input('test char', str(sp))
    print('character input:', ep, list(fi.keys()))
"
```
Expected: `import OK` + `character input: fal-ai/nano-banana-2 ['prompt', 'aspect_ratio']`

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/tools/image_generate.py
git commit -m "feat: image_generate.py — _build_character_fal_input / _build_scene_fal_input 추출"
```

---

## Chunk 4: image_batch_module.py — 파이프라인 모듈

### Task 7: image_batch_module.py — Phase 1 캐릭터 배치

**Files:**
- Create: `auto_agent/modules/__init__.py` (빈 파일)
- Create: `auto_agent/modules/image_batch_module.py`
- Create: `tests/test_image_batch_module.py`

**사전 지식:**
- 이 모듈은 `runner.py`가 `sys.executable script.py` 방식으로 실행함
- `PROJECT_DIR` 환경변수로 프로젝트 디렉토리 경로를 받음
- 결과는 stdout으로 JSON 출력 (`{"status": "completed", "scene_count": N, ...}`)
- `PROGRESS_FILE` 환경변수로 진행 상황을 JSONL 파일에 기록

- [ ] **Step 1: 실패 테스트 작성**

```python
# tests/test_image_batch_module.py
import json
import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import MagicMock, patch

from auto_agent.modules.image_batch_module import run_batch, _build_char_result_path

@pytest.fixture
def project_dir(tmp_path):
    """최소 프로젝트 구조 생성."""
    d = tmp_path / "test_project"
    d.mkdir()
    (d / "characters").mkdir()
    (d / "images").mkdir()

    # art_style.json
    (d / "art_style.json").write_text(json.dumps({
        "id": "quirky_cartoon",
        "name": "Quirky Cartoon",
        "reference_image": "",
        "scene_style_description": "cartoon",
        "technical": {"critical_requirements": []},
    }))

    # character_plan.json
    (d / "character_plan.json").write_text(json.dumps({
        "characters": [
            {
                "id": "char_001",
                "name": "테스트캐릭터",
                "description": "테스트용 캐릭터",
                "tags": ["테스트"],
                "person_photo": None,
            }
        ]
    }))

    # scene_specs.json (이미지 없는 씬만)
    (d / "scene_specs.json").write_text(json.dumps({
        "scenes": [
            {
                "sceneNumber": 1,
                "narration": "테스트 씬",
                "imageAsset": {"source": "generate", "prompt": "test scene"},
                "characters": ["char_001"],
            }
        ]
    }))
    return d

def test_character_reused_from_library(project_dir, tmp_path):
    """라이브러리에 캐릭터가 있으면 FAL 제출 없이 재사용한다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(
        library_dir=tmp_path / "chars",
        db_path=tmp_path / "chars.db",
    )
    # 더미 캐릭터 등록
    dummy_png = tmp_path / "dummy.png"
    Image.new("RGB", (1, 1)).save(dummy_png)
    lib.register(dummy_png, {
        "character_name": "테스트캐릭터",
        "art_style": "quirky_cartoon",
        "tags": "테스트",
        "features": "테스트용",
        "source_project": "prev",
    })

    submit_calls = []
    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq:
        mock_fq.submit_batch.side_effect = lambda jobs: (submit_calls.extend(jobs), [])[1]
        result = run_batch(project_dir, library=lib)

    assert mock_fq.submit_batch.call_count == 0 or len(submit_calls) == 0
    assert result["chars_reused"] == 1

def test_character_new_generation(project_dir, tmp_path):
    """라이브러리 미스 시 FAL 제출이 호출된다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(library_dir=tmp_path / "c", db_path=tmp_path / "c.db")

    dummy_result = MagicMock()
    dummy_result.success = True
    dummy_result.idx = 0
    dummy_result.images = [{"url": "http://fake.com/img.png", "width": 512, "height": 512}]

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.submit_batch.return_value = ["req-0"]
        mock_fq.poll_all.side_effect = lambda jobs, rids, on_done, **kw: on_done(dummy_result)
        mock_save.return_value = project_dir / "characters" / "char_001.png"
        result = run_batch(project_dir, library=lib)

    assert mock_fq.submit_batch.call_count == 1
    assert result["chars_generated"] == 1
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_image_batch_module.py -v
```
Expected: `ImportError: No module named 'auto_agent.modules'`

- [ ] **Step 3: modules 패키지 + image_batch_module.py Phase 1 구현**

```python
# auto_agent/modules/__init__.py
# (빈 파일)
```

```python
# auto_agent/modules/image_batch_module.py
"""이미지 배치 생성 파이프라인 모듈.

환경변수:
  PROJECT_DIR     프로젝트 디렉토리 경로
  PROGRESS_FILE   진행 상황 JSONL 파일 경로 (선택)
  FAL_API_KEY / FAL_KEY  FAL AI API 키

출력: stdout에 JSON {"status": "completed", ...}
"""
from __future__ import annotations
import json
import logging
import os
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from auto_agent.tools import fal_queue as fal_queue
from auto_agent.tools.fal_queue import FalJob
from auto_agent.tools.character_library import CharacterLibrary
from auto_agent.tools.image_generate import (
    _build_character_fal_input,
    _build_scene_fal_input,
    _save_fal_result,
)
from auto_agent.tools import image_assets

logger = logging.getLogger(__name__)

_PROGRESS_FILE: Optional[Path] = None


def _progress(msg: str, level: str = "info") -> None:
    print(f"[image_batch] {msg}", flush=True)
    if _PROGRESS_FILE:
        with open(_PROGRESS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"message": msg, "level": level}) + "\n")


def _save_image_from_url(url: str, dest: Path) -> Path:
    """URL에서 이미지를 다운로드해 저장."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, str(dest))
    return dest


def _build_char_result_path(project_dir: Path, char_id: str) -> Path:
    """캐릭터 결과 파일 경로 반환."""
    return project_dir / "characters" / f"{char_id}.png"


def run_batch(
    project_dir: Path,
    library: Optional[CharacterLibrary] = None,
) -> dict:
    """메인 배치 실행. summary dict 반환."""
    if library is None:
        library = CharacterLibrary()

    # ── 입력 로드 ──
    style_path = str(project_dir / "art_style.json")
    art_style  = json.loads((project_dir / "art_style.json").read_text())
    art_style_id = art_style.get("id", "default")

    char_plan_path = project_dir / "character_plan.json"
    characters = []
    if char_plan_path.exists():
        characters = json.loads(char_plan_path.read_text()).get("characters", [])

    # ── Phase 1: 캐릭터 배치 ──
    char_paths: dict[str, Optional[Path]] = {}
    reused, to_generate = [], []

    for char in characters:
        char_id   = char["id"]
        char_name = char["name"]
        tags      = char.get("tags", [])
        record = library.search(char_name, art_style_id, tags)
        if record:
            dest = library.copy_to_project(record, project_dir)
            char_paths[char_id] = dest
            reused.append(char_id)
            _progress(f"캐릭터 재사용: {char_name}")
        else:
            person_photo = char.get("person_photo")
            endpoint, arguments = _build_character_fal_input(
                prompt=char.get("description", char_name),
                style_path=style_path,
                person_photo=person_photo,
            )
            to_generate.append((char, FalJob(idx=len(to_generate), endpoint=endpoint, arguments=arguments)))

    if to_generate:
        jobs = [job for _, job in to_generate]
        _progress(f"캐릭터 {len(jobs)}개 FAL 제출 중...")
        request_ids = fal_queue.submit_batch(jobs)

        def on_char_done(result):
            char, _ = to_generate[result.idx]
            char_id = char["id"]
            if result.success and result.images:
                url  = result.images[0].get("url", "")
                dest = _build_char_result_path(project_dir, char_id)
                try:
                    _save_image_from_url(url, dest)
                    library.register(dest, {
                        "character_name": char["name"],
                        "art_style":      art_style_id,
                        "tags":           ",".join(char.get("tags", [])),
                        "features":       char.get("description", ""),
                        "source_project": project_dir.name,
                    })
                    char_paths[char_id] = dest
                    _progress(f"캐릭터 저장 완료: {char['name']}")
                except Exception as e:
                    logger.warning("캐릭터 저장 실패 (%s): %s", char_id, e)
            else:
                _progress(f"캐릭터 생성 실패: {char['name']} — {result.error}", level="warning")

        fal_queue.poll_all(jobs, request_ids, on_done=on_char_done)

    _progress(
        f"캐릭터 완료: 재사용 {len(reused)}개, 신규 생성 {len(to_generate)}개, "
        f"성공 {sum(1 for v in char_paths.values() if v is not None)}개"
    )

    return {
        "chars_reused": len(reused),
        "chars_generated": len(to_generate),
        "char_paths": {k: str(v) if v else None for k, v in char_paths.items()},
    }
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_image_batch_module.py -v
```
Expected: PASS 2개

---

### Task 8: image_batch_module.py — Phase 2 씬 배치 + main()

**Files:**
- Modify: `auto_agent/modules/image_batch_module.py`
- Modify: `tests/test_image_batch_module.py`

- [ ] **Step 1: Phase 2 테스트 추가**

```python
# tests/test_image_batch_module.py 에 추가

def test_scene_batch_submitted(project_dir, tmp_path):
    """씬 이미지가 FAL에 일괄 제출된다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(library_dir=tmp_path / "c", db_path=tmp_path / "c.db")

    dummy_png = tmp_path / "dummy.png"
    Image.new("RGB", (1, 1)).save(dummy_png)
    lib.register(dummy_png, {
        "character_name": "테스트캐릭터",
        "art_style": "quirky_cartoon",
        "tags": "테스트",
        "features": "테스트",
        "source_project": "p",
    })

    scene_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/s.png", "width": 512, "height": 512}])

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.submit_batch.return_value = ["req-s0"]
        mock_fq.poll_all.side_effect = lambda jobs, rids, on_done, **kw: on_done(scene_result)
        mock_save.return_value = project_dir / "images" / "scene_001_gen_01.png"
        result = run_batch(project_dir, library=lib)

    # 씬 제출 1회
    assert mock_fq.submit_batch.call_count == 1
    assert result["scenes_success"] >= 0  # 결과 키 존재

def test_failed_character_scene_generated_without_ref(project_dir, tmp_path):
    """캐릭터 생성 실패 시 씬이 캐릭터 참조 없이 생성된다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(library_dir=tmp_path / "c", db_path=tmp_path / "c.db")

    char_fail = MagicMock(success=False, idx=0, error="FAL error", images=[])
    scene_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/s.png", "width": 512, "height": 512}])

    submitted_args = []
    def capture_submit(jobs):
        submitted_args.extend(jobs)
        return ["req-s0"]

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.submit_batch.side_effect = [
            ["req-c0"],    # 캐릭터 제출
            capture_submit,  # 씬 제출
        ]
        call_count = {"n": 0}
        def fake_poll(jobs, rids, on_done, **kw):
            call_count["n"] += 1
            if call_count["n"] == 1:
                on_done(char_fail)
            else:
                on_done(scene_result)
        mock_fq.poll_all.side_effect = fake_poll
        mock_save.return_value = project_dir / "images" / "scene_001_gen_01.png"
        result = run_batch(project_dir, library=lib)

    # 씬은 여전히 제출됨 (캐릭터 없이)
    assert mock_fq.submit_batch.call_count == 2
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_image_batch_module.py::test_scene_batch_submitted -v
```
Expected: FAIL (`scenes_success` 키 없음)

- [ ] **Step 3: Phase 2 + main() 구현**

`run_batch()` 함수에 Phase 2 추가, `main()` 진입점 작성:

```python
# run_batch() return 직전에 Phase 2 추가:

    # ── Phase 2: 씬 배치 ──
    scene_specs_path = project_dir / "scene_specs.json"
    scenes_success, scenes_fail = 0, 0
    if scene_specs_path.exists():
        scene_specs = json.loads(scene_specs_path.read_text())
        images_dir  = project_dir / "images"
        images_dir.mkdir(exist_ok=True)

        scene_jobs: list[tuple[dict, FalJob]] = []
        for scene in scene_specs.get("scenes", []):
            if scene.get("imageAsset", {}).get("source") != "generate":
                continue
            scene_char_paths = {
                cid: char_paths.get(cid)
                for cid in scene.get("characters", [])
            }
            try:
                endpoint, arguments = _build_scene_fal_input(
                    scene, project_dir, scene_char_paths
                )
                scene_jobs.append((scene, FalJob(idx=len(scene_jobs), endpoint=endpoint, arguments=arguments)))
            except Exception as e:
                logger.warning("씬 %s 입력 빌드 실패: %s", scene.get("sceneNumber"), e)
                scenes_fail += 1

        if scene_jobs:
            jobs = [job for _, job in scene_jobs]
            _progress(f"씬 {len(jobs)}개 FAL 제출 중...")
            request_ids = fal_queue.submit_batch(jobs)

            def on_scene_done(result):
                nonlocal scenes_success, scenes_fail
                scene, _ = scene_jobs[result.idx]
                scene_num = scene.get("sceneNumber", result.idx + 1)
                if result.success and result.images:
                    url      = result.images[0].get("url", "")
                    filename = image_assets.next_filename(images_dir, scene_num, "gen", ".png")
                    dest     = images_dir / filename
                    try:
                        _save_image_from_url(url, dest)
                        image_assets.add_version(images_dir, scene_num, filename, "generate")
                        scenes_success += 1
                        _progress(f"씬 {scene_num} 저장 완료: {filename}")
                    except Exception as e:
                        logger.warning("씬 %s 저장 실패: %s", scene_num, e)
                        scenes_fail += 1
                else:
                    _progress(f"씬 {scene_num} 생성 실패: {result.error}", level="warning")
                    scenes_fail += 1

            fal_queue.poll_all(jobs, request_ids, on_done=on_scene_done)

    _progress(f"씬 완료: 성공 {scenes_success}개, 실패 {scenes_fail}개")

    return {
        "chars_reused":    len(reused),
        "chars_generated": len(to_generate),
        "scenes_success":  scenes_success,
        "scenes_fail":     scenes_fail,
    }


def main():
    """파이프라인 runner가 subprocess로 실행하는 진입점."""
    global _PROGRESS_FILE
    project_dir_str = os.environ.get("PROJECT_DIR", "")
    if not project_dir_str:
        print(json.dumps({"status": "failed", "error": "PROJECT_DIR 환경변수 없음"}))
        sys.exit(1)

    project_dir = Path(project_dir_str)
    progress_path = os.environ.get("PROGRESS_FILE", "")
    if progress_path:
        _PROGRESS_FILE = Path(progress_path)

    try:
        summary = run_batch(project_dir)
        summary["status"] = "completed"
        print(json.dumps(summary, ensure_ascii=False))
    except Exception as e:
        logger.exception("image_batch_module 실행 실패")
        print(json.dumps({"status": "failed", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
pytest tests/test_image_batch_module.py -v
```
Expected: 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/__init__.py auto_agent/modules/image_batch_module.py tests/test_image_batch_module.py
git commit -m "feat: image_batch_module.py — Phase1 캐릭터 배치 + Phase2 씬 배치 구현"
```

---

## Chunk 5: 파이프라인 연결 + 마이그레이션

### Task 9: runner.py + pipeline.json 연결

**Files:**
- Modify: `auto_agent/orchestrator/runner.py`
- Modify: `auto_agent/data/pipeline.json`

- [ ] **Step 1: runner.py script_map에 image_batch 추가**

`auto_agent/orchestrator/runner.py` L2517-L2530 `script_map` 딕셔너리에 추가:

```python
# 기존 script_map에 한 줄 추가
script_map = {
    "preflight": "scripts/preflight_check.py",
    "duplicate-checker": "scripts/duplicate_check.py",
    "tts-preprocess": "tools/korean_tts_preprocessor.py",
    "tts-generator": "scripts/generate_tts.py",
    "image-generator": "scripts/generate_images.py",
    "image_batch": "modules/image_batch_module.py",   # ← 추가
    "subtitle-sync": "scripts/generate_subtitles.py",
    "tts-verifier": "scripts/verify_tts.py",
    "data-validator": "scripts/validate_data.py",
    "manifest-builder": "scripts/build_manifest.py",
    "layout-check": "scripts/layout_check.py",
    "video-assembler": None,
}
```

- [ ] **Step 2: runner.py 문법 검사**

```bash
python3 -c "import ast; ast.parse(open('auto_agent/orchestrator/runner.py').read()); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: pipeline.json step_8b 교체**

`auto_agent/data/pipeline.json`에서 기존 step_8b를 찾아 다음으로 교체:

기존 step_8b 정의 앞에 step_8b_legacy를 삽입하고, step_8b를 image_batch 모듈로 교체.

```json
{
  "id": "step_8b_legacy",
  "name": "image_asset_sourcing_legacy",
  "description": "이미지 소싱 레거시 — Claude CLI image-painter 에이전트 방식 (롤백용 보존)",
  "type": "agent",
  "agent": "image-painter",
  "skip": true,
  "input": ["scene_specs.json", "art_style.json"],
  "output": ["images/image_assets.json"]
},
{
  "id": "step_8b",
  "name": "image_asset_sourcing",
  "description": "이미지 배치 생성 — 캐릭터 라이브러리 조회 → FAL queue 배치 제출 → 폴링",
  "type": "module",
  "module": "image_batch",
  "input": [
    "character_plan.json",
    "scene_specs.json",
    "art_style.json"
  ],
  "output": ["images/image_assets.json", "characters/"]
}
```

- [ ] **Step 4: pipeline.json 유효성 검사**

```bash
python3 -c "import json; json.load(open('auto_agent/data/pipeline.json')); print('JSON OK')"
```
Expected: `JSON OK`

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/orchestrator/runner.py auto_agent/data/pipeline.json
git commit -m "feat: pipeline 연결 — image_batch 모듈 등록 및 step_8b 교체 (레거시 보존)"
```

---

### Task 10: migrate_characters.py — 기존 캐릭터 마이그레이션 스크립트

**Files:**
- Create: `auto_agent/scripts/migrate_characters.py`

기존 프로젝트 `output/*/characters/*.png` 파일들을 글로벌 라이브러리로 마이그레이션하는 one-time 스크립트.

- [ ] **Step 1: 스크립트 작성**

```python
#!/usr/bin/env python3
"""기존 프로젝트 캐릭터 이미지를 글로벌 라이브러리로 마이그레이션.

사용법:
  python3 auto_agent/scripts/migrate_characters.py [--dry-run] [--output-root OUTPUT_DIR]

기본 output 디렉토리: WORKSPACE_DIR/output/
"""
import argparse
import json
import sys
from pathlib import Path

from auto_agent.paths import get_workspace_dir
from auto_agent.tools.character_library import CharacterLibrary, read_png_metadata


def migrate(output_root: Path, dry_run: bool = False) -> None:
    lib = CharacterLibrary()
    total, skipped, registered = 0, 0, 0

    for char_png in sorted(output_root.glob("*/characters/*.png")):
        total += 1
        meta = read_png_metadata(char_png)

        # PNG tEXt 없으면 파일명에서 추측 (char_id만 알 수 있음)
        if not meta.get("character_name"):
            print(f"  [SKIP] tEXt 없음: {char_png}")
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] {meta['character_name']} / {meta.get('art_style')} — {char_png.name}")
        else:
            record = lib.register(char_png, meta)
            print(f"  [REG] id={record.id} {record.name} / {record.art_style}")
            registered += 1

    print(f"\n총 {total}개 중 등록 {registered}개, 스킵 {skipped}개 (dry_run={dry_run})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-root", default=None)
    args = parser.parse_args()

    output_root = Path(args.output_root) if args.output_root else get_workspace_dir() / "output"
    if not output_root.exists():
        print(f"output 디렉토리 없음: {output_root}", file=sys.stderr)
        sys.exit(1)

    migrate(output_root, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 문법 검사**

```bash
python3 -c "import py_compile; py_compile.compile('auto_agent/scripts/migrate_characters.py', doraise=True); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/scripts/migrate_characters.py
git commit -m "feat: migrate_characters.py — 기존 프로젝트 캐릭터를 글로벌 라이브러리로 마이그레이션"
```

---

## Chunk 6: 전체 통합 검증

### Task 11: 전체 테스트 실행 + smoke test

**Files:** 없음 (검증만)

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
cd /Users/hannah/Projects/auto_kairos_v3
source .venv/bin/activate
pytest tests/test_fal_queue.py tests/test_character_library.py tests/test_image_batch_module.py -v
```
Expected: 전체 PASS

- [ ] **Step 2: import smoke test**

```bash
python3 -c "
from auto_agent.tools.fal_queue import FalJob, FalResult, submit_batch, poll_all
from auto_agent.tools.character_library import CharacterLibrary, embed_png_metadata, read_png_metadata
from auto_agent.modules.image_batch_module import run_batch
from auto_agent.tools.image_generate import _build_character_fal_input, _build_scene_fal_input
print('All imports OK')
"
```
Expected: `All imports OK`

- [ ] **Step 3: pipeline.json step_8b 확인**

```bash
python3 -c "
import json
data = json.load(open('auto_agent/data/pipeline.json'))
for phase in data['phases']:
    for step in phase['steps']:
        if step['id'] in ('step_8b', 'step_8b_legacy'):
            print(step['id'], ':', step.get('module', step.get('agent', '?')), '| skip:', step.get('skip', False))
"
```
Expected:
```
step_8b_legacy : image-painter | skip: True
step_8b : image_batch | skip: False
```

- [ ] **Step 4: migrate_characters.py dry-run (출력 디렉토리 있을 경우)**

```bash
python3 auto_agent/scripts/migrate_characters.py --dry-run
```
Expected: 에러 없이 실행, `총 N개 중 등록 0개` (dry_run)

- [ ] **Step 5: 최종 커밋**

```bash
git add -A
git status  # 미커밋 파일 없는지 확인
git push origin main
```

---

## 롤백 방법

step_8b_legacy의 `"skip": true` → `"skip": false` 로 변경하고, step_8b의 `"skip": false` → `"skip": true`로 변경:

```bash
# pipeline.json에서 두 줄만 수정하면 즉시 레거시 에이전트로 복귀
```
