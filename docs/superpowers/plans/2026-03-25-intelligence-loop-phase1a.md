# 채널 인텔리전스 루프 Phase 1a — 데이터 기반 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** YouTube API 기반 데이터 수집 모듈 + 볼트 구조 셋업 + 중복 방지 메커니즘 구축

**Architecture:** data-collector Python 모듈이 YouTube Data/Analytics API로 데이터를 수집하고, vault_writer가 Obsidian 볼트에 마크다운 노트로 변환/저장한다. dedup 모듈이 워터마크+해시 기반 중복 방지를 담당한다.

**Tech Stack:** Python 3.11+, google-api-python-client, google-auth-oauthlib, discord-webhook, SQLite, pathlib

**Spec:** `docs/superpowers/specs/2026-03-25-stage0-stage4-intelligence-loop-design.md`

### 리뷰 반영 사항 (구현 시 주의)

1. **`link_video`/`get_linked_videos`는 `ProjectManager` 클래스 메서드로 추가** — 모듈 레벨 함수 아님. `self.db_path` 전달 패턴 준수.
2. **`CHANNEL_IDS`는 모듈 상수가 아닌 `DataCollector.__init__`에서 로드** — `.env` 로드 이후 시점 보장.
3. **`datetime.utcnow()` 대신 `datetime.now(timezone.utc)` 사용** — Python 3.12+ 호환.
4. **`_load_watchlist()` stub 유지** — 경쟁 채널 수집은 Phase 1a에서 watchlist 셋업만. 실제 파싱은 Phase 1b.
5. **`cmd_watchlist` approve/remove도 stub 표시** — `print_warning("Phase 1b에서 구현 예정")` 출력.
6. **`cmd_link`에서 DB 직접 접근 대신 `ProjectManager` 메서드 사용.**
7. **한글 파일명 sanitize** — NAS 인코딩 이슈 대비 vault_writer에서 파일명 정리 유틸 추가.
8. **`discord-webhook` 패키지 대신 `requests` 직접 사용 (의도적)** — 외부 의존성 최소화, requests는 이미 기존 의존성.
9. **테스트 보강** — `collect_all()`, `_collect_youtube()`, `write_analytics_note()`, `_parse_duration` 엣지 케이스, API 실패 graceful degradation 테스트 추가.

---

## File Structure

### 신규 생성

| 파일 | 역할 |
|------|------|
| `auto_agent/modules/data_collector/__init__.py` | 패키지 초기화 |
| `auto_agent/modules/data_collector/collector.py` | 메인 오케스트레이터 — 수집 소스별 순차 실행 |
| `auto_agent/modules/data_collector/youtube_collector.py` | YouTube Data API + Analytics API 수집 |
| `auto_agent/modules/data_collector/vault_writer.py` | 수집 데이터 → 마크다운 노트 변환 + 위키링크 생성 |
| `auto_agent/modules/data_collector/dedup.py` | 중복 방지 (state.json + hashes.db) |
| `auto_agent/modules/data_collector/discord_notifier.py` | Discord 웹훅 알림 |
| `auto_agent/modules/data_collector/vault_paths.py` | 볼트 경로 유틸 — KAIROS_VAULT_DIR 기반 |
| `tests/test_dedup.py` | dedup 모듈 테스트 |
| `tests/test_vault_writer.py` | vault_writer 테스트 |
| `tests/test_youtube_collector.py` | youtube_collector 테스트 (모킹) |
| `tests/test_collector.py` | collector 오케스트레이터 테스트 |
| `tests/test_discord_notifier.py` | discord_notifier 테스트 |

### 수정

| 파일 | 변경 내용 |
|------|-----------|
| `auto_agent/cli.py` | `collect`, `link`, `watchlist` 명령어 추가 |
| `auto_agent/db/schema.sql` | projects 테이블에 `video_id` 컬럼 추가 |
| `auto_agent/db/project_manager.py` | `link_video()`, `get_linked_videos()` 메서드 추가 |
| `auto_agent/paths.py` | `get_vault_dir()` 함수 추가 |
| `pyproject.toml` | 새 의존성 추가 + package-data에 data_collector 포함 |
| `.env.example` | YouTube OAuth, Discord 웹훅, KAIROS_VAULT_DIR 추가 |

---

## Chunk 1: 볼트 경로 + 중복 방지 기반

### Task 1: 볼트 경로 유틸 추가

**Files:**
- Modify: `auto_agent/paths.py`
- Create: `auto_agent/modules/data_collector/__init__.py`
- Create: `auto_agent/modules/data_collector/vault_paths.py`

- [ ] **Step 1: paths.py에 get_vault_dir() 추가**

```python
# auto_agent/paths.py — 기존 코드 하단에 추가

def get_vault_dir() -> Path:
    """Obsidian 볼트 디렉토리 (KAIROS_VAULT_DIR 환경변수)."""
    env = os.getenv("KAIROS_VAULT_DIR")
    if not env:
        raise EnvironmentError(
            "KAIROS_VAULT_DIR 환경변수가 설정되지 않았습니다. "
            ".env 파일에 KAIROS_VAULT_DIR=/path/to/kairos-vault 를 추가하세요."
        )
    p = Path(env).resolve()
    if not p.exists():
        raise FileNotFoundError(f"볼트 디렉토리를 찾을 수 없습니다: {p}")
    return p
```

- [ ] **Step 2: data_collector 패키지 + vault_paths 모듈 생성**

```python
# auto_agent/modules/data_collector/__init__.py
"""데이터 수집 모듈 — YouTube, 트렌드, 소셜 데이터를 볼트에 저장."""
```

```python
# auto_agent/modules/data_collector/vault_paths.py
"""볼트 내 경로 규칙 중앙 관리."""
from pathlib import Path
from auto_agent.paths import get_vault_dir


def vault_root() -> Path:
    return get_vault_dir()

def collector_dir() -> Path:
    return vault_root() / ".collector"

def channel_dir(channel: str) -> Path:
    return vault_root() / "channels" / channel

def videos_dir(channel: str) -> Path:
    return channel_dir(channel) / "videos"

def analytics_dir(channel: str) -> Path:
    return channel_dir(channel) / "analytics"

def competitors_dir() -> Path:
    return vault_root() / "channels" / "competitors"

def trends_dir() -> Path:
    return vault_root() / "market" / "trends"

def social_dir() -> Path:
    return vault_root() / "market" / "social"

def topics_dir() -> Path:
    return vault_root() / "topics"

def insights_dir() -> Path:
    return vault_root() / "insights"

def planning_dir() -> Path:
    return insights_dir() / "planning"

def feedback_dir() -> Path:
    return insights_dir() / "feedback"

def performance_dir() -> Path:
    return insights_dir() / "performance"

def templates_dir() -> Path:
    return vault_root() / "templates"

def watchlist_path() -> Path:
    return vault_root() / "channels" / "_watchlist.md"

def state_json_path() -> Path:
    return collector_dir() / "state.json"

def hashes_db_path() -> Path:
    return collector_dir() / "hashes.db"

def video_tracking_path() -> Path:
    return collector_dir() / "video_tracking.json"


def ensure_vault_structure():
    """볼트 기본 디렉토리 구조 생성. 이미 있으면 스킵."""
    dirs = [
        collector_dir(),
        channel_dir("이로미즘") / "analytics",
        channel_dir("이로미즘") / "videos",
        channel_dir("세모지") / "analytics",
        channel_dir("세모지") / "videos",
        competitors_dir(),
        trends_dir(),
        social_dir(),
        topics_dir(),
        planning_dir(),
        feedback_dir(),
        performance_dir(),
        templates_dir(),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/paths.py auto_agent/modules/data_collector/
git commit -m "feat: 볼트 경로 유틸 + data_collector 패키지 초기화"
```

---

### Task 2: 중복 방지 모듈 (dedup.py)

**Files:**
- Create: `auto_agent/modules/data_collector/dedup.py`
- Create: `tests/test_dedup.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_dedup.py
"""dedup 모듈 테스트 — 워터마크, 해시 DB, upsert 판단."""
import json
import tempfile
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.dedup import (
    DedupManager,
    UpsertAction,
)


@pytest.fixture
def dedup(tmp_path):
    """임시 디렉토리에 DedupManager 생성."""
    return DedupManager(collector_dir=tmp_path)


class TestWatermark:
    def test_get_returns_none_when_missing(self, dedup):
        assert dedup.get_watermark("youtube_analytics", "이로미즘") is None

    def test_set_and_get(self, dedup):
        dedup.set_watermark("youtube_analytics", "이로미즘", {"last_date": "2026-03-24"})
        result = dedup.get_watermark("youtube_analytics", "이로미즘")
        assert result["last_date"] == "2026-03-24"

    def test_persistence(self, dedup):
        dedup.set_watermark("trends", "global", {"last_fetch": "2026-03-25"})
        # 새 인스턴스로 다시 로드
        dedup2 = DedupManager(collector_dir=dedup._collector_dir)
        assert dedup2.get_watermark("trends", "global")["last_fetch"] == "2026-03-25"


class TestHashDB:
    def test_check_new_content(self, dedup):
        action = dedup.check("youtube_video", "abc123", "hello world")
        assert action == UpsertAction.CREATE

    def test_check_same_content(self, dedup):
        dedup.record("youtube_video", "abc123", "hello world", "videos/test.md")
        action = dedup.check("youtube_video", "abc123", "hello world")
        assert action == UpsertAction.SKIP

    def test_check_changed_content(self, dedup):
        dedup.record("youtube_video", "abc123", "hello world", "videos/test.md")
        action = dedup.check("youtube_video", "abc123", "hello world updated")
        assert action == UpsertAction.UPDATE

    def test_get_note_path(self, dedup):
        dedup.record("youtube_video", "abc123", "hello", "videos/test.md")
        assert dedup.get_note_path("youtube_video", "abc123") == "videos/test.md"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_dedup.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'auto_agent.modules.data_collector.dedup'`

- [ ] **Step 3: dedup.py 구현**

```python
# auto_agent/modules/data_collector/dedup.py
"""중복 방지 — 워터마크(state.json) + 콘텐츠 해시(hashes.db)."""
import hashlib
import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


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
        now = datetime.utcnow().isoformat()
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_dedup.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/dedup.py tests/test_dedup.py
git commit -m "feat: 중복 방지 모듈 (워터마크 + 해시 DB)"
```

---

### Task 3: 볼트 라이터 (vault_writer.py)

**Files:**
- Create: `auto_agent/modules/data_collector/vault_writer.py`
- Create: `tests/test_vault_writer.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_vault_writer.py
"""vault_writer 테스트 — 마크다운 생성, 프론트매터, 위키링크."""
import tempfile
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.vault_writer import VaultWriter
from auto_agent.modules.data_collector.dedup import DedupManager


@pytest.fixture
def vault_env(tmp_path):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    collector_dir = vault_dir / ".collector"
    collector_dir.mkdir()
    dedup = DedupManager(collector_dir=collector_dir)
    writer = VaultWriter(vault_dir=vault_dir, dedup=dedup)
    return writer, vault_dir


class TestVideoNote:
    def test_creates_video_note(self, vault_env):
        writer, vault_dir = vault_env
        videos_dir = vault_dir / "channels" / "이로미즘" / "videos"
        videos_dir.mkdir(parents=True)

        writer.write_video_note(
            channel="이로미즘",
            video_id="abc123",
            title="미국-이란 전쟁",
            published="2026-03-20",
            duration="12:34",
            views=58300,
            likes=1200,
            project_slug="us-iran-war",
        )

        note_path = videos_dir / "미국-이란 전쟁.md"
        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert "video_id: \"abc123\"" in content
        assert "channel: 이로미즘" in content
        assert "[[미국-이란]]" not in content  # 토픽 연결은 별도

    def test_skips_duplicate(self, vault_env):
        writer, vault_dir = vault_env
        videos_dir = vault_dir / "channels" / "이로미즘" / "videos"
        videos_dir.mkdir(parents=True)

        kwargs = dict(
            channel="이로미즘", video_id="abc123", title="테스트",
            published="2026-03-20", duration="5:00", views=100, likes=10,
        )
        result1 = writer.write_video_note(**kwargs)
        result2 = writer.write_video_note(**kwargs)
        assert result1 == "created"
        assert result2 == "skipped"

    def test_updates_changed(self, vault_env):
        writer, vault_dir = vault_env
        videos_dir = vault_dir / "channels" / "이로미즘" / "videos"
        videos_dir.mkdir(parents=True)

        writer.write_video_note(
            channel="이로미즘", video_id="abc123", title="테스트",
            published="2026-03-20", duration="5:00", views=100, likes=10,
        )
        result = writer.write_video_note(
            channel="이로미즘", video_id="abc123", title="테스트",
            published="2026-03-20", duration="5:00", views=500, likes=50,
        )
        assert result == "updated"


class TestTrendNote:
    def test_creates_daily_trend(self, vault_env):
        writer, vault_dir = vault_env
        trends_dir = vault_dir / "market" / "trends"
        trends_dir.mkdir(parents=True)

        writer.write_trend_note(
            date="2026-03-25",
            trends=[
                {"keyword": "희토류", "volume_change": "+180%", "region": "KR"},
                {"keyword": "AI 규제", "volume_change": "+50%", "region": "KR"},
            ],
        )

        note_path = trends_dir / "2026-03-25-daily.md"
        assert note_path.exists()
        content = note_path.read_text(encoding="utf-8")
        assert "희토류" in content
        assert "+180%" in content


class TestCompetitorNote:
    def test_creates_competitor_note(self, vault_env):
        writer, vault_dir = vault_env
        comp_dir = vault_dir / "channels" / "competitors"
        comp_dir.mkdir(parents=True)

        writer.write_competitor_note(
            channel_id="UCxyz",
            name="슈카월드",
            category="경제/시사",
            subscribers=1500000,
            recent_videos=[
                {"title": "AI 버블론", "views": 120000, "published": "2026-03-22"},
            ],
        )

        note_path = comp_dir / "슈카월드.md"
        assert note_path.exists()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_vault_writer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: vault_writer.py 구현**

```python
# auto_agent/modules/data_collector/vault_writer.py
"""수집 데이터를 Obsidian 볼트 마크다운 노트로 변환."""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dedup import DedupManager, UpsertAction


class VaultWriter:
    """수집 데이터 → 볼트 마크다운 노트 변환 + 중복 방지."""

    def __init__(self, vault_dir: Path, dedup: DedupManager):
        self._vault = vault_dir
        self._dedup = dedup

    def write_video_note(
        self,
        channel: str,
        video_id: str,
        title: str,
        published: str,
        duration: str,
        views: int,
        likes: int,
        project_slug: Optional[str] = None,
    ) -> str:
        """영상 노트 생성/업데이트. 반환: 'created' | 'updated' | 'skipped'."""
        content = self._render_video_note(
            channel, video_id, title, published, duration, views, likes, project_slug
        )
        note_path = self._vault / "channels" / channel / "videos" / f"{title}.md"
        return self._upsert("youtube_video", video_id, content, note_path)

    def write_trend_note(self, date: str, trends: List[Dict]) -> str:
        """일일 트렌드 노트."""
        content = self._render_trend_note(date, trends)
        note_path = self._vault / "market" / "trends" / f"{date}-daily.md"
        return self._upsert("trend", date, content, note_path)

    def write_competitor_note(
        self,
        channel_id: str,
        name: str,
        category: str,
        subscribers: int,
        recent_videos: List[Dict],
    ) -> str:
        """경쟁 채널 노트."""
        content = self._render_competitor_note(
            channel_id, name, category, subscribers, recent_videos
        )
        note_path = self._vault / "channels" / "competitors" / f"{name}.md"
        return self._upsert("competitor", channel_id, content, note_path)

    def write_analytics_note(
        self,
        channel: str,
        date: str,
        metrics: Dict[str, Any],
    ) -> str:
        """채널 일일 Analytics 노트."""
        content = self._render_analytics_note(channel, date, metrics)
        note_path = (
            self._vault / "channels" / channel / "analytics" / f"{date}.md"
        )
        return self._upsert("analytics", f"{channel}:{date}", content, note_path)

    # ── 내부: upsert ──

    def _upsert(self, source: str, source_id: str, content: str, note_path: Path) -> str:
        action = self._dedup.check(source, source_id, content)
        if action == UpsertAction.CREATE:
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text(content, encoding="utf-8")
            self._dedup.record(source, source_id, content, str(note_path.relative_to(self._vault)))
            return "created"
        elif action == UpsertAction.UPDATE:
            existing_rel = self._dedup.get_note_path(source, source_id)
            target = self._vault / existing_rel if existing_rel else note_path
            target.write_text(content, encoding="utf-8")
            self._dedup.record(source, source_id, content, str(target.relative_to(self._vault)))
            return "updated"
        return "skipped"

    # ── 내부: 렌더링 ──

    def _render_video_note(
        self, channel, video_id, title, published, duration, views, likes, project_slug
    ) -> str:
        lines = [
            "---",
            f'video_id: "{video_id}"',
            f"channel: {channel}",
        ]
        if project_slug:
            lines.append(f"project_slug: {project_slug}")
        lines += [
            f"published: {published}",
            f'duration: "{duration}"',
            f"last_updated: {datetime.utcnow().strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {title}",
            "",
            "## 성과",
            f"- 조회수: {views:,}",
            f"- 좋아요: {likes:,}",
            "",
        ]
        return "\n".join(lines)

    def _render_trend_note(self, date: str, trends: List[Dict]) -> str:
        lines = [
            "---",
            "type: trend-daily",
            f"date: {date}",
            "---",
            "",
            f"# 트렌드 스냅샷 ({date})",
            "",
            "| 키워드 | 변화 | 지역 |",
            "|--------|------|------|",
        ]
        for t in trends:
            lines.append(f"| {t['keyword']} | {t.get('volume_change', '-')} | {t.get('region', '-')} |")
        lines.append("")
        return "\n".join(lines)

    def _render_competitor_note(
        self, channel_id, name, category, subscribers, recent_videos
    ) -> str:
        lines = [
            "---",
            f'channel_id: "{channel_id}"',
            f"name: {name}",
            f"category: {category}",
            f"subscribers: {subscribers:,}",
            f"last_updated: {datetime.utcnow().strftime('%Y-%m-%d')}",
            "---",
            "",
            f"# {name}",
            "",
            "## 최근 영상",
            "| 제목 | 조회수 | 게시일 |",
            "|------|--------|--------|",
        ]
        for v in recent_videos:
            lines.append(f"| {v['title']} | {v.get('views', '-'):,} | {v.get('published', '-')} |")
        lines.append("")
        return "\n".join(lines)

    def _render_analytics_note(self, channel: str, date: str, metrics: Dict) -> str:
        lines = [
            "---",
            "type: analytics-daily",
            f"channel: {channel}",
            f"date: {date}",
            "---",
            "",
            f"# {channel} Analytics ({date})",
            "",
        ]
        for key, value in metrics.items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
        return "\n".join(lines)
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_vault_writer.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/vault_writer.py tests/test_vault_writer.py
git commit -m "feat: 볼트 라이터 — 영상/트렌드/경쟁채널/Analytics 노트 생성"
```

---

## Chunk 2: YouTube 수집 + 오케스트레이터

### Task 4: YouTube 수집기 (youtube_collector.py)

**Files:**
- Create: `auto_agent/modules/data_collector/youtube_collector.py`
- Create: `tests/test_youtube_collector.py`

- [ ] **Step 1: 테스트 작성 (모킹)**

```python
# tests/test_youtube_collector.py
"""YouTube 수집기 테스트 — API 응답 모킹."""
from unittest.mock import MagicMock, patch
from datetime import datetime

import pytest

from auto_agent.modules.data_collector.youtube_collector import YouTubeCollector


@pytest.fixture
def collector():
    with patch(
        "auto_agent.modules.data_collector.youtube_collector.YouTubeCollector._build_youtube_service"
    ) as mock_yt, patch(
        "auto_agent.modules.data_collector.youtube_collector.YouTubeCollector._build_analytics_service"
    ) as mock_analytics:
        mock_yt.return_value = MagicMock()
        mock_analytics.return_value = MagicMock()
        c = YouTubeCollector(
            client_id="test", client_secret="test", refresh_token="test"
        )
        yield c


class TestChannelVideos:
    def test_fetch_new_videos(self, collector):
        collector._youtube.search().list().execute.return_value = {
            "items": [
                {
                    "id": {"videoId": "vid1"},
                    "snippet": {
                        "title": "테스트 영상",
                        "publishedAt": "2026-03-20T10:00:00Z",
                    },
                }
            ]
        }
        collector._youtube.videos().list().execute.return_value = {
            "items": [
                {
                    "id": "vid1",
                    "snippet": {"title": "테스트 영상"},
                    "contentDetails": {"duration": "PT12M34S"},
                    "statistics": {"viewCount": "1000", "likeCount": "50"},
                }
            ]
        }
        videos = collector.fetch_channel_videos("UCxxxxxx", after="2026-03-19")
        assert len(videos) == 1
        assert videos[0]["video_id"] == "vid1"
        assert videos[0]["views"] == 1000


class TestCompetitorData:
    def test_fetch_competitor_info(self, collector):
        collector._youtube.channels().list().execute.return_value = {
            "items": [
                {
                    "id": "UCxyz",
                    "snippet": {"title": "슈카월드"},
                    "statistics": {"subscriberCount": "1500000"},
                }
            ]
        }
        collector._youtube.search().list().execute.return_value = {"items": []}
        info = collector.fetch_competitor_info("UCxyz")
        assert info["name"] == "슈카월드"
        assert info["subscribers"] == 1500000
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_youtube_collector.py -v`
Expected: FAIL

- [ ] **Step 3: youtube_collector.py 구현**

```python
# auto_agent/modules/data_collector/youtube_collector.py
"""YouTube Data API + Analytics API 수집."""
import re
from typing import Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


class YouTubeCollector:
    """YouTube 채널/영상/Analytics 데이터 수집."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]

    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri="https://oauth2.googleapis.com/token",
            scopes=self.SCOPES,
        )
        self._youtube = self._build_youtube_service()
        self._analytics = self._build_analytics_service()

    def _build_youtube_service(self):
        return build("youtube", "v3", credentials=self._credentials)

    def _build_analytics_service(self):
        return build("youtubeAnalytics", "v2", credentials=self._credentials)

    # ── 채널 영상 ──

    def fetch_channel_videos(
        self, channel_id: str, after: Optional[str] = None, max_results: int = 10
    ) -> List[Dict]:
        """채널의 최근 영상 목록 + 통계."""
        params = {
            "channelId": channel_id,
            "part": "id,snippet",
            "order": "date",
            "maxResults": max_results,
            "type": "video",
        }
        if after:
            params["publishedAfter"] = f"{after}T00:00:00Z"

        search_result = self._youtube.search().list(**params).execute()
        video_ids = [item["id"]["videoId"] for item in search_result.get("items", [])]

        if not video_ids:
            return []

        details = (
            self._youtube.videos()
            .list(part="snippet,contentDetails,statistics", id=",".join(video_ids))
            .execute()
        )

        videos = []
        for item in details.get("items", []):
            videos.append(
                {
                    "video_id": item["id"],
                    "title": item["snippet"]["title"],
                    "published": item["snippet"].get("publishedAt", ""),
                    "duration": self._parse_duration(
                        item["contentDetails"].get("duration", "")
                    ),
                    "views": int(item["statistics"].get("viewCount", 0)),
                    "likes": int(item["statistics"].get("likeCount", 0)),
                }
            )
        return videos

    # ── 경쟁 채널 ──

    def fetch_competitor_info(self, channel_id: str) -> Dict:
        """경쟁 채널 기본 정보 + 최근 영상."""
        ch = (
            self._youtube.channels()
            .list(part="snippet,statistics", id=channel_id)
            .execute()
        )
        if not ch.get("items"):
            return {}
        item = ch["items"][0]
        info = {
            "channel_id": channel_id,
            "name": item["snippet"]["title"],
            "subscribers": int(item["statistics"].get("subscriberCount", 0)),
            "category": item["snippet"].get("description", "")[:100],
        }
        info["recent_videos"] = self.fetch_channel_videos(channel_id, max_results=5)
        return info

    # ── Analytics (내 채널만) ──

    def fetch_analytics(
        self, channel_id: str, start_date: str, end_date: str
    ) -> Dict:
        """내 채널 Analytics — CTR, 시청지속, 유입경로 등."""
        result = (
            self._analytics.reports()
            .query(
                ids=f"channel=={channel_id}",
                startDate=start_date,
                endDate=end_date,
                metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained,annotationClickThroughRate",
                dimensions="day",
            )
            .execute()
        )
        return result

    def fetch_video_analytics(self, video_id: str, channel_id: str) -> Dict:
        """개별 영상 Analytics."""
        result = (
            self._analytics.reports()
            .query(
                ids=f"channel=={channel_id}",
                startDate="2020-01-01",
                endDate="2030-12-31",
                metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained",
                filters=f"video=={video_id}",
            )
            .execute()
        )
        return result

    # ── 유틸 ──

    @staticmethod
    def _parse_duration(iso_duration: str) -> str:
        """ISO 8601 duration → "MM:SS" 형식."""
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
        if not match:
            return "0:00"
        h, m, s = (int(x or 0) for x in match.groups())
        total_min = h * 60 + m
        return f"{total_min}:{s:02d}"
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_youtube_collector.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/youtube_collector.py tests/test_youtube_collector.py
git commit -m "feat: YouTube 수집기 (Data API + Analytics API)"
```

---

### Task 5: Discord 알림 모듈

**Files:**
- Create: `auto_agent/modules/data_collector/discord_notifier.py`
- Create: `tests/test_discord_notifier.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_discord_notifier.py
"""Discord 알림 테스트 — 웹훅 호출 모킹."""
from unittest.mock import patch, MagicMock

import pytest

from auto_agent.modules.data_collector.discord_notifier import DiscordNotifier


@pytest.fixture
def notifier():
    return DiscordNotifier(webhook_url="https://discord.com/api/webhooks/test/test")


class TestFormatting:
    def test_format_planning_message(self, notifier):
        msg = notifier.format_planning(
            channel="이로미즘",
            date="03-25",
            topics=[
                {"title": "희토류 전쟁", "reason": "검색량 +180%", "estimate": "50~90K"},
            ],
        )
        assert "이로미즘" in msg
        assert "희토류 전쟁" in msg

    def test_format_video_performance(self, notifier):
        msg = notifier.format_video_performance(
            title="미국-이란 전쟁",
            days=7,
            views=42000,
            ctr=7.1,
            avg_watch="5:48",
            duration="12:34",
        )
        assert "7일" in msg
        assert "42,000" in msg

    def test_format_weekly_review(self, notifier):
        msg = notifier.format_weekly_review(
            channel="이로미즘",
            week="W12",
            total_views=125000,
            views_change="+12%",
            top_video="미국-이란 전쟁",
            approvals_needed=["trial→정규: 어쩌다어른"],
        )
        assert "W12" in msg
        assert "125,000" in msg


class TestSend:
    @patch("auto_agent.modules.data_collector.discord_notifier.requests")
    def test_send_calls_webhook(self, mock_requests, notifier):
        mock_requests.post.return_value = MagicMock(status_code=204)
        notifier.send("테스트 메시지")
        mock_requests.post.assert_called_once()
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_discord_notifier.py -v`
Expected: FAIL

- [ ] **Step 3: discord_notifier.py 구현**

```python
# auto_agent/modules/data_collector/discord_notifier.py
"""Discord 웹훅 알림."""
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord 웹훅으로 알림 발송."""

    MAX_LENGTH = 2000  # Discord 메시지 제한

    def __init__(self, webhook_url: str):
        self._url = webhook_url

    def send(self, message: str) -> bool:
        """메시지 발송. 성공 시 True."""
        if not self._url:
            logger.warning("Discord 웹훅 URL이 설정되지 않음 — 알림 스킵")
            return False
        try:
            resp = requests.post(
                self._url,
                json={"content": message[:self.MAX_LENGTH]},
                timeout=10,
            )
            if resp.status_code in (200, 204):
                return True
            logger.error("Discord 알림 실패: %d %s", resp.status_code, resp.text)
            return False
        except Exception as e:
            logger.error("Discord 알림 에러: %s", e)
            return False

    def format_planning(self, channel: str, date: str, topics: List[Dict]) -> str:
        lines = [f"📋 **{channel} 일일 기획안** ({date})", ""]
        for i, t in enumerate(topics, 1):
            lines.append(f"{i}. **{t['title']}**")
            lines.append(f"   {t.get('reason', '')} · 예상 {t.get('estimate', '?')}")
            lines.append("")
        return "\n".join(lines)

    def format_video_performance(
        self, title: str, days: int, views: int, ctr: float,
        avg_watch: str, duration: str,
    ) -> str:
        return "\n".join([
            f"📊 **{title}** {days}일 성과",
            "",
            f"조회수: {views:,}",
            f"CTR: {ctr}%",
            f"평균 시청: {avg_watch} / {duration}",
        ])

    def format_weekly_review(
        self, channel: str, week: str, total_views: int,
        views_change: str, top_video: str,
        approvals_needed: Optional[List[str]] = None,
    ) -> str:
        lines = [
            f"📈 **{channel} 주간 리뷰** ({week})",
            "",
            f"총 조회수: {total_views:,} ({views_change})",
            f"최고 성과: {top_video}",
        ]
        if approvals_needed:
            lines += ["", "⚡ **승인 필요**"]
            for item in approvals_needed:
                lines.append(f"• {item}")
        return "\n".join(lines)

    def format_error(self, source: str, error: str) -> str:
        return f"⚠️ **수집 오류** [{source}]\n{error}"
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_discord_notifier.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/discord_notifier.py tests/test_discord_notifier.py
git commit -m "feat: Discord 웹훅 알림 모듈"
```

---

### Task 6: 수집 오케스트레이터 (collector.py)

**Files:**
- Create: `auto_agent/modules/data_collector/collector.py`
- Create: `tests/test_collector.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/test_collector.py
"""수집 오케스트레이터 테스트."""
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from auto_agent.modules.data_collector.collector import DataCollector


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    (vault_dir / ".collector").mkdir()
    monkeypatch.setenv("KAIROS_VAULT_DIR", str(vault_dir))
    monkeypatch.setenv("YOUTUBE_CLIENT_ID", "test")
    monkeypatch.setenv("YOUTUBE_CLIENT_SECRET", "test")
    monkeypatch.setenv("YOUTUBE_REFRESH_TOKEN", "test")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/test")
    return vault_dir


class TestCollectorInit:
    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_creates_collector(self, mock_yt, mock_env):
        collector = DataCollector()
        assert collector._vault_dir == mock_env


class TestVideoTracking:
    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_register_video(self, mock_yt, mock_env):
        collector = DataCollector()
        collector.register_video_tracking("vid1", "test-project", "이로미즘")

        tracking = collector._load_video_tracking()
        assert len(tracking["tracking"]) == 1
        assert tracking["tracking"][0]["video_id"] == "vid1"
        assert "1d" in tracking["tracking"][0]["checkpoints"]

    @patch("auto_agent.modules.data_collector.collector.YouTubeCollector")
    def test_get_due_checkpoints(self, mock_yt, mock_env):
        collector = DataCollector()
        collector.register_video_tracking("vid1", "test-project", "이로미즘")

        # 모든 체크포인트는 미래이므로 오늘 due인 것은 없어야 함
        # (등록 직후는 +1d가 내일)
        due = collector.get_due_checkpoints()
        assert len(due) == 0
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_collector.py -v`
Expected: FAIL

- [ ] **Step 3: collector.py 구현**

```python
# auto_agent/modules/data_collector/collector.py
"""데이터 수집 메인 오케스트레이터."""
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_vault_dir
from .dedup import DedupManager
from .discord_notifier import DiscordNotifier
from .vault_writer import VaultWriter
from .youtube_collector import YouTubeCollector

logger = logging.getLogger(__name__)

# 채널 ID 매핑 — 초기 설정 시 .env에서 로드
CHANNEL_IDS = {
    "이로미즘": os.getenv("YOUTUBE_CHANNEL_ID_IROMISM", ""),
    "세모지": os.getenv("YOUTUBE_CHANNEL_ID_SEMOJI", ""),
}

CHECKPOINT_DAYS = {"1d": 1, "3d": 3, "7d": 7, "28d": 28}


class DataCollector:
    """데이터 수집 오케스트레이터 — YouTube 중심."""

    def __init__(self):
        self._vault_dir = get_vault_dir()
        self._collector_dir = self._vault_dir / ".collector"
        self._collector_dir.mkdir(parents=True, exist_ok=True)

        self._dedup = DedupManager(collector_dir=self._collector_dir)
        self._writer = VaultWriter(vault_dir=self._vault_dir, dedup=self._dedup)

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
        self._notifier = DiscordNotifier(webhook_url=webhook_url)

        self._youtube = YouTubeCollector(
            client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
            client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
            refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
        )

    # ── 전체 수집 ──

    def collect_all(self):
        """전체 수집 실행 (cron 05:30)."""
        errors = []
        for source, fn in [
            ("youtube", self._collect_youtube),
            ("video_tracking", self._collect_video_tracking),
        ]:
            try:
                fn()
            except Exception as e:
                logger.error("수집 실패 [%s]: %s", source, e)
                errors.append((source, str(e)))

        if errors:
            for source, err in errors:
                self._notifier.send(self._notifier.format_error(source, err))

    def collect_youtube(self):
        self._collect_youtube()

    # ── YouTube 수집 ──

    def _collect_youtube(self):
        """내 채널 + 경쟁 채널 데이터 수집."""
        for channel_name, channel_id in CHANNEL_IDS.items():
            if not channel_id:
                continue
            # 워터마크 확인
            wm = self._dedup.get_watermark("youtube_videos", channel_name)
            after = wm.get("last_published") if wm else None

            videos = self._youtube.fetch_channel_videos(channel_id, after=after)
            for v in videos:
                self._writer.write_video_note(
                    channel=channel_name,
                    video_id=v["video_id"],
                    title=v["title"],
                    published=v["published"],
                    duration=v["duration"],
                    views=v["views"],
                    likes=v["likes"],
                )

            if videos:
                self._dedup.set_watermark(
                    "youtube_videos",
                    channel_name,
                    {
                        "last_video_id": videos[0]["video_id"],
                        "last_published": videos[0]["published"][:10],
                        "last_fetch": datetime.utcnow().isoformat(),
                    },
                )

        # 경쟁 채널
        self._collect_competitors()

    def _collect_competitors(self):
        """경쟁 채널 공개 데이터 수집 (주 1회 체크)."""
        wm = self._dedup.get_watermark("competitors", "global")
        if wm:
            last = datetime.fromisoformat(wm["last_fetch"])
            if (datetime.utcnow() - last).days < 7:
                return  # 주 1회

        watchlist = self._load_watchlist()
        for ch in watchlist:
            try:
                info = self._youtube.fetch_competitor_info(ch["channel_id"])
                if info:
                    self._writer.write_competitor_note(
                        channel_id=info["channel_id"],
                        name=info["name"],
                        category=info.get("category", ""),
                        subscribers=info["subscribers"],
                        recent_videos=[
                            {
                                "title": v["title"],
                                "views": v["views"],
                                "published": v["published"][:10],
                            }
                            for v in info.get("recent_videos", [])
                        ],
                    )
            except Exception as e:
                logger.error("경쟁 채널 수집 실패 [%s]: %s", ch.get("name"), e)

        self._dedup.set_watermark(
            "competitors", "global", {"last_fetch": datetime.utcnow().isoformat()}
        )

    # ── 영상 추적 ──

    def register_video_tracking(self, video_id: str, project_slug: str, channel: str):
        """영상 추적 등록 (auto-agent link 시 호출)."""
        tracking = self._load_video_tracking()
        now = datetime.utcnow()

        entry = {
            "video_id": video_id,
            "project_slug": project_slug,
            "channel": channel,
            "linked_at": now.isoformat(),
            "checkpoints": {},
        }
        for key, days in CHECKPOINT_DAYS.items():
            due = (now + timedelta(days=days)).strftime("%Y-%m-%d")
            entry["checkpoints"][key] = {"due": due, "status": "pending"}

        tracking["tracking"].append(entry)
        self._save_video_tracking(tracking)

    def get_due_checkpoints(self) -> List[Dict]:
        """오늘 수집해야 할 체크포인트 반환."""
        tracking = self._load_video_tracking()
        today = datetime.utcnow().strftime("%Y-%m-%d")
        due = []
        for entry in tracking["tracking"]:
            for cp_key, cp in entry["checkpoints"].items():
                if cp["due"] <= today and cp["status"] == "pending":
                    due.append({
                        "video_id": entry["video_id"],
                        "project_slug": entry["project_slug"],
                        "channel": entry["channel"],
                        "checkpoint": cp_key,
                    })
        return due

    def _collect_video_tracking(self):
        """오늘 due인 영상 성과 수집."""
        due = self.get_due_checkpoints()
        tracking = self._load_video_tracking()

        for item in due:
            try:
                channel_id = CHANNEL_IDS.get(item["channel"], "")
                if not channel_id:
                    continue
                analytics = self._youtube.fetch_video_analytics(
                    item["video_id"], channel_id
                )
                # 볼트 노트 업데이트는 analytics 데이터로
                # (상세 구현은 Phase 1b에서 performance-analyst가 담당)
                self._mark_checkpoint(
                    item["video_id"], item["checkpoint"], "done"
                )
            except Exception as e:
                logger.error(
                    "영상 추적 실패 [%s/%s]: %s",
                    item["video_id"], item["checkpoint"], e,
                )
                self._mark_checkpoint(
                    item["video_id"], item["checkpoint"], "retry"
                )

    def _mark_checkpoint(self, video_id: str, checkpoint: str, status: str):
        tracking = self._load_video_tracking()
        for entry in tracking["tracking"]:
            if entry["video_id"] == video_id:
                entry["checkpoints"][checkpoint]["status"] = status
                if status == "done":
                    entry["checkpoints"][checkpoint]["collected_at"] = (
                        datetime.utcnow().isoformat()
                    )
                break
        self._save_video_tracking(tracking)

    # ── 파일 I/O ──

    def _load_video_tracking(self) -> Dict:
        path = self._collector_dir / "video_tracking.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"tracking": []}

    def _save_video_tracking(self, data: Dict):
        path = self._collector_dir / "video_tracking.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_watchlist(self) -> List[Dict]:
        """_watchlist.md에서 active + trial 채널 ID 목록 추출."""
        watchlist_path = self._vault_dir / "channels" / "_watchlist.md"
        if not watchlist_path.exists():
            return []
        # 간단한 마크다운 테이블 파싱 — channel_id가 frontmatter에 있다고 가정
        # 실제 구현은 watchlist 형식에 맞게 조정
        return []
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `cd /Users/hannah/Projects/auto_kairos_v3 && python -m pytest tests/test_collector.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/modules/data_collector/collector.py tests/test_collector.py
git commit -m "feat: 수집 오케스트레이터 + 영상 추적 스케줄러"
```

---

## Chunk 3: CLI 통합 + 환경 설정

### Task 7: DB 스키마에 video_id 추가

**Files:**
- Modify: `auto_agent/db/schema.sql`
- Modify: `auto_agent/db/project_manager.py`

- [ ] **Step 1: schema.sql에 video_id 컬럼 추가**

projects 테이블에 `video_id TEXT DEFAULT NULL` 컬럼을 추가하는 마이그레이션:

```sql
-- auto_agent/db/schema.sql 의 projects 테이블 정의에 추가
-- video_id TEXT DEFAULT NULL,  -- YouTube 영상 ID (업로드 후 연결)
```

`project_manager.py`에 마이그레이션 헬퍼 추가:

```python
def _migrate_add_video_id(conn):
    """projects 테이블에 video_id 컬럼 추가 (없으면)."""
    cursor = conn.execute("PRAGMA table_info(projects)")
    columns = [row[1] for row in cursor.fetchall()]
    if "video_id" not in columns:
        conn.execute("ALTER TABLE projects ADD COLUMN video_id TEXT DEFAULT NULL")
        conn.commit()
```

- [ ] **Step 2: link_video / get_linked_videos 메서드 추가**

```python
# auto_agent/db/project_manager.py 에 추가

def link_video(project_slug: str, video_id: str):
    """프로젝트에 YouTube 영상 ID 연결."""
    with transaction() as conn:
        _migrate_add_video_id(conn)
        conn.execute(
            "UPDATE projects SET video_id = ? WHERE slug = ?",
            (video_id, project_slug),
        )

def get_linked_videos() -> list:
    """video_id가 연결된 모든 프로젝트 반환."""
    conn = get_connection()
    _migrate_add_video_id(conn)
    rows = conn.execute(
        "SELECT slug, video_id, channel FROM projects WHERE video_id IS NOT NULL"
    ).fetchall()
    return [{"slug": r[0], "video_id": r[1], "channel": r[2]} for r in rows]
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/db/schema.sql auto_agent/db/project_manager.py
git commit -m "feat: projects 테이블에 video_id 컬럼 + link/get 메서드"
```

---

### Task 8: CLI 명령어 추가 (collect, link, watchlist)

**Files:**
- Modify: `auto_agent/cli.py`

- [ ] **Step 1: cmd_collect 함수 추가**

```python
# auto_agent/cli.py 에 추가

def cmd_collect(args):
    """데이터 수집 (YouTube, 트렌드, 소셜)."""
    from auto_agent.modules.data_collector.collector import DataCollector

    print_header("Auto Agent — 데이터 수집")
    collector = DataCollector()

    if not args or "--all" in args:
        collector.collect_all()
        print_success("전체 수집 완료")
    elif "--youtube" in args:
        collector.collect_youtube()
        print_success("YouTube 수집 완료")
    else:
        print_error("Usage: auto-agent collect [--all|--youtube|--trends|--social]")
```

- [ ] **Step 2: cmd_link 함수 추가**

```python
def cmd_link(args):
    """프로젝트에 YouTube 영상 ID 연결."""
    project_slug = None
    video_id = None

    for i, arg in enumerate(args):
        if arg == "--project" and i + 1 < len(args):
            project_slug = args[i + 1]
        elif arg == "--video-id" and i + 1 < len(args):
            video_id = args[i + 1]

    if not project_slug or not video_id:
        print_error("Usage: auto-agent link --project <slug> --video-id <id>")
        sys.exit(1)

    from auto_agent.db.project_manager import link_video
    from auto_agent.modules.data_collector.collector import DataCollector

    link_video(project_slug, video_id)

    # 영상 추적 등록
    from auto_agent.db.connection import get_connection
    conn = get_connection()
    row = conn.execute(
        "SELECT channel FROM projects WHERE slug = ?", (project_slug,)
    ).fetchone()
    channel = row[0] if row else "이로미즘"

    collector = DataCollector()
    collector.register_video_tracking(video_id, project_slug, channel)

    print_success(f"영상 연결 완료: {project_slug} ← {video_id}")
    print_success("성과 추적 등록: +1d, +3d, +7d, +28d")
```

- [ ] **Step 3: cmd_watchlist 함수 추가**

```python
def cmd_watchlist(args):
    """경쟁 채널 워치리스트 관리."""
    from auto_agent.paths import get_vault_dir

    vault = get_vault_dir()
    watchlist_path = vault / "channels" / "_watchlist.md"

    if not args:
        # 목록 표시
        if watchlist_path.exists():
            console.print(watchlist_path.read_text(encoding="utf-8"))
        else:
            print_warning("워치리스트가 없습니다.")
        return

    subcmd = args[0]
    if subcmd == "approve" and len(args) > 1:
        channel_name = args[1]
        # _watchlist.md에서 trial → active 전환
        if watchlist_path.exists():
            content = watchlist_path.read_text(encoding="utf-8")
            # Trial 테이블에서 해당 채널 행을 Active로 이동
            # (마크다운 파싱 + 재구성)
            print_success(f"채널 승격: {channel_name} (trial → active)")
        else:
            print_error("워치리스트가 없습니다.")

    elif subcmd == "remove" and len(args) > 1:
        channel_name = args[1]
        print_success(f"채널 제거 승인: {channel_name} → archived")
    else:
        print_error("Usage: auto-agent watchlist [approve|remove] <채널명>")
```

- [ ] **Step 4: main() 라우터에 명령어 등록**

`cli.py`의 `main()` 함수 내 명령어 분기에 추가:

```python
elif cmd == "collect":
    cmd_collect(remaining)
elif cmd == "link":
    cmd_link(remaining)
elif cmd == "watchlist":
    cmd_watchlist(remaining)
```

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/cli.py
git commit -m "feat: CLI collect/link/watchlist 명령어 추가"
```

---

### Task 9: 환경 설정 파일 업데이트

**Files:**
- Modify: `.env.example`
- Modify: `pyproject.toml`

- [ ] **Step 1: .env.example에 새 환경변수 추가**

```
# YouTube OAuth (채널 인텔리전스)
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
YOUTUBE_CHANNEL_ID_IROMISM=
YOUTUBE_CHANNEL_ID_SEMOJI=

# Discord 알림
DISCORD_WEBHOOK_URL=

# 볼트
KAIROS_VAULT_DIR=/path/to/kairos-vault
```

- [ ] **Step 2: pyproject.toml에 의존성 추가**

```toml
# [project] dependencies 에 추가
"google-api-python-client>=2.0",
"google-auth-oauthlib>=1.0",
```

- [ ] **Step 3: pyproject.toml package-data에 data_collector 포함 확인**

기존 패키지 데이터 패턴에 `modules/data_collector/**` 가 포함되는지 확인. Python 파일은 자동 포함되므로 별도 설정 불필요할 수 있지만, 확인 필요.

- [ ] **Step 4: 커밋**

```bash
git add .env.example pyproject.toml
git commit -m "chore: YouTube/Discord/볼트 환경변수 + 의존성 추가"
```

---

### Task 10: 볼트 초기 구조 + 템플릿 생성

**Files:**
- Create: 볼트 템플릿 파일들 (vault_paths.ensure_vault_structure 실행)
- Create: `.obsidianignore`

- [ ] **Step 1: CLI에 vault init 명령 추가 또는 collect 첫 실행 시 자동 셋업**

`collector.py`의 `__init__`에서 `ensure_vault_structure()` 호출:

```python
from .vault_paths import ensure_vault_structure
# __init__ 내부
ensure_vault_structure()
```

- [ ] **Step 2: .obsidianignore 생성 로직 추가**

`ensure_vault_structure()`에 추가:

```python
obsidianignore = vault_root() / ".obsidianignore"
if not obsidianignore.exists():
    obsidianignore.write_text(".collector/\n.lance/\n", encoding="utf-8")
```

- [ ] **Step 3: 템플릿 파일 생성**

`ensure_vault_structure()`에서 템플릿 디렉토리에 기본 템플릿 생성:

```python
# templates/video-note.md
video_template = templates_dir() / "video-note.md"
if not video_template.exists():
    video_template.write_text("""---
video_id: ""
channel:
project_slug:
published:
duration: ""
---

## 성과
| 지표 | 7일 | 28일 | 현재 |
|------|-----|------|------|
| 조회수 | | | |
| CTR | | | |
| 평균 시청 지속 | | | |

## 유입 경로

## 연결
""", encoding="utf-8")
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/modules/data_collector/vault_paths.py auto_agent/modules/data_collector/collector.py
git commit -m "feat: 볼트 초기 구조 자동 생성 + .obsidianignore + 템플릿"
```

---

## 완료 체크

Phase 1a 완료 시 사용 가능한 명령어:

```bash
# 환경변수 설정 후
auto-agent collect --all           # YouTube 데이터 수집 → 볼트 저장
auto-agent collect --youtube       # YouTube만
auto-agent link --project <slug> --video-id <id>  # 영상 연결 + 추적 등록
auto-agent watchlist               # 워치리스트 확인
auto-agent watchlist approve <name>  # 승격
auto-agent watchlist remove <name>   # 제거
```

Phase 1b (별도 계획 문서)에서 추가될 항목:
- trend-analyst / performance-analyst 에이전트
- 에이전트 스킬 (market-analysis, channel-metrics)
- agents.json 업데이트
- `auto-agent plan` / `auto-agent analyze` 명령
- `auto-agent project create --from-plan`
- cron 스케줄 설정
- Discord 알림 통합
