# adobe Stage1-2 P1 — 결정적 리서치 기반 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v3의 stdlib 리서치 레인 4종(위키·뉴스·CrossRef·OpenLibrary) + 수집기를 adobe `backend/research/`로 이식해, 쿼리 리스트를 받아 외부 소스를 병렬 수집·정규화·적재한다.

**Architecture:** v3 `auto_agent/research/`의 순수 stdlib 코드를 `backend/research/`로 이식(import 경로 재작성 + adobe 적응). LLM·브리프·오케스트레이션은 제외 — 입력은 쿼리 리스트. 진행 로그는 `PROGRESS_FILE` env 대신 `on_event` 콜백, 출력은 `proj_dir/research/`.

**Tech Stack:** Python stdlib 전용(urllib·xml.etree·concurrent.futures·hashlib·json·functools). 서드파티 0. 테스트는 pytest + 의존성 주입(fetch_impl) monkeypatch.

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트에서).

**이식 원본(읽기 전용):** `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/research/`

**전역 import 재작성 규칙(모든 이식 파일 공통):**
`from auto_agent.research.lanes.<X> import ...` → `from backend.research.lanes.<X> import ...`

---

## Task 1: 패키지 스켈레톤 + HTTP/텍스트 헬퍼

**Files:**
- Create: `backend/research/__init__.py` (빈 파일)
- Create: `backend/research/lanes/__init__.py` (이 태스크에선 빈 파일 — 익스포트는 Task 6)
- Create: `backend/research/lanes/_http.py`
- Create: `backend/research/lanes/_text.py`
- Test: `tests/test_research_text.py`

- [ ] **Step 1: 빈 패키지 파일 2개 생성**

`backend/research/__init__.py` (빈), `backend/research/lanes/__init__.py` (빈).

- [ ] **Step 2: `_http.py` 이식(verbatim — auto_agent import 없음)**

원본 `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/research/lanes/_http.py` 를 읽어 **그대로** `backend/research/lanes/_http.py` 로 복사한다. 이 파일은 `auto_agent` import가 없으므로 수정 불필요. (내용: `USER_AGENT`, `DEFAULT_TIMEOUT`, `JsonFetcher`/`TextFetcher` 타입, `fetch_json`, `fetch_text` — urllib 기반.)

- [ ] **Step 3: `_text.py` 이식(verbatim — auto_agent import 없음)**

원본 `.../lanes/_text.py` 를 그대로 `backend/research/lanes/_text.py` 로 복사한다. (내용: `contains_korean`, `wikipedia_languages_for_query`, `extract_domain`, `clean_html_fragment`, `clean_crossref_abstract`, `title_similar`, `split_google_news_title`.)

- [ ] **Step 4: Write the failing test** — `tests/test_research_text.py`:

```python
from backend.research.lanes import _text


def test_contains_korean():
    assert _text.contains_korean("한국어")
    assert not _text.contains_korean("english only")


def test_wikipedia_languages_order():
    assert _text.wikipedia_languages_for_query("한국") == ["ko", "en"]
    assert _text.wikipedia_languages_for_query("korea") == ["en", "ko"]


def test_extract_domain_strips_www():
    assert _text.extract_domain("https://www.example.com/path") == "example.com"
    assert _text.extract_domain("https://sub.go.kr") == "sub.go.kr"


def test_clean_html_fragment():
    assert _text.clean_html_fragment("<b>hi</b>  there") == "hi there"


def test_split_google_news_title():
    assert _text.split_google_news_title("Headline - Reuters") == ("Headline", "Reuters")
    assert _text.split_google_news_title("NoPublisher") == ("NoPublisher", "")


def test_title_similar():
    assert _text.title_similar("apple banana cherry", "apple banana cherry date")
    assert not _text.title_similar("apple banana cherry", "x y z w")
```

- [ ] **Step 5: Run test to verify it fails then passes**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_text.py -v`
Expected: 먼저 import 실패(파일 없을 때)였다가, 이식 후 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/research/__init__.py backend/research/lanes/__init__.py backend/research/lanes/_http.py backend/research/lanes/_text.py tests/test_research_text.py
git commit -m "feat(research): HTTP/텍스트 헬퍼 이식 — 리서치 레인 기반(stdlib)"
```

---

## Task 2: 신뢰도 tier 분류 (_trust + trust_tiers.json)

**Files:**
- Create: `backend/research/lanes/trust_tiers.json`
- Create: `backend/research/lanes/_trust.py`
- Test: `tests/test_research_trust.py`

- [ ] **Step 1: `trust_tiers.json` 복사(verbatim)**

원본 `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/research/trust_tiers.json` 를 **그대로** `backend/research/lanes/trust_tiers.json` 로 복사한다(A/B/C tier 도메인 데이터, 156줄).

- [ ] **Step 2: `_trust.py` 이식 + 경로/임포트 적응**

원본 `.../lanes/_trust.py` 를 `backend/research/lanes/_trust.py` 로 이식하되 **2가지 수정**:
1. import 재작성: `from auto_agent.research.lanes._text import extract_domain` → `from backend.research.lanes._text import extract_domain`
2. trust_tiers.json 경로: 원본의 `Path(__file__).resolve().parents[1] / "trust_tiers.json"` → **`Path(__file__).resolve().parent / "trust_tiers.json"`** (adobe에선 trust_tiers.json을 `lanes/`에 두므로 `parent`).

나머지(`_domain_match`, `_load_tiers`, `_flatten_domains`, `classify_tier`, `is_evidence_eligible`)는 그대로.

- [ ] **Step 3: Write the failing test** — `tests/test_research_trust.py`:

```python
from backend.research.lanes import _trust


def test_classify_tier_encyclopedia_is_A():
    assert _trust.classify_tier("https://en.wikipedia.org/wiki/X") == "A"


def test_classify_tier_wildcard_go_kr_is_A():
    assert _trust.classify_tier("https://kostat.go.kr/portal") == "A"


def test_classify_tier_unknown_domain():
    assert _trust.classify_tier("https://some-random-blog.example/post") == "unknown"


def test_classify_tier_empty_url():
    assert _trust.classify_tier("") == "unknown"


def test_is_evidence_eligible():
    assert _trust.is_evidence_eligible("https://en.wikipedia.org/wiki/X")
    assert not _trust.is_evidence_eligible("https://some-random-blog.example/post")
```

- [ ] **Step 4: Run test**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_trust.py -v`
Expected: 5 passed. (실패 먼저 확인 후 이식.)

주의: 만약 `en.wikipedia.org`가 trust_tiers.json A의 encyclopedia 목록에 없다면 테스트가 깨진다 — 복사한 trust_tiers.json에 해당 도메인이 있는지 먼저 확인하고, 없으면 실제 파일에 있는 A-tier 도메인으로 테스트 기대값을 맞춘다(파일이 진실).

- [ ] **Step 5: Commit**

```bash
git add backend/research/lanes/trust_tiers.json backend/research/lanes/_trust.py tests/test_research_trust.py
git commit -m "feat(research): 도메인 신뢰도 tier 분류 이식(trust_tiers)"
```

---

## Task 3: 위키·CrossRef·OpenLibrary 레인

**Files:**
- Create: `backend/research/lanes/wikipedia.py`, `crossref.py`, `openlibrary.py`
- Test: `tests/test_research_lanes_basic.py`

- [ ] **Step 1: 3개 레인 이식 + import 재작성**

각각 원본을 이식하되 `from auto_agent.research.lanes.<X>` → `from backend.research.lanes.<X>` 로만 수정(로직 동일):
- `.../lanes/wikipedia.py` → `backend/research/lanes/wikipedia.py` (`search_wikipedia`, `fetch_wikipedia_article_content`)
- `.../lanes/crossref.py` → `backend/research/lanes/crossref.py` (`search_crossref`)
- `.../lanes/openlibrary.py` → `backend/research/lanes/openlibrary.py` (`search_openlibrary`)

- [ ] **Step 2: Write the failing test** — `tests/test_research_lanes_basic.py`:

```python
from backend.research.lanes.wikipedia import search_wikipedia
from backend.research.lanes.crossref import search_crossref
from backend.research.lanes.openlibrary import search_openlibrary


def test_wikipedia_normalizes(monkeypatch):
    def fake_json(url, **k):
        return {"query": {"search": [{"title": "유한양행", "snippet": "<b>제약</b> 회사"}]}}
    out = search_wikipedia("유한양행", limit=3, fetch_json_impl=fake_json)
    assert out[0]["title"] == "유한양행"
    assert out[0]["lane"] == "wikipedia"
    assert out[0]["tier_hint"] == "A"
    assert "<b>" not in out[0]["snippet"]
    assert out[0]["url"].startswith("https://ko.wikipedia.org/wiki/")


def test_wikipedia_lane_error_entry():
    def boom(url, **k):
        raise RuntimeError("net")
    out = search_wikipedia("x", fetch_json_impl=boom)
    assert any(r.get("error") for r in out)


def test_crossref_normalizes():
    def fake_json(url, **k):
        return {"message": {"items": [{
            "title": ["A Study"], "URL": "https://doi.org/10.1/x", "DOI": "10.1/x",
            "author": [{"given": "Jane", "family": "Doe"}],
            "publisher": "Elsevier", "created": {"date-parts": [[2020, 5, 1]]},
            "abstract": "<p>abs</p>"}]}}
    out = search_crossref("study", limit=3, fetch_json_impl=fake_json)
    assert out[0]["title"] == "A Study"
    assert out[0]["lane"] == "crossref"
    assert out[0]["kind"] == "paper"
    assert out[0]["doi"] == "10.1/x"
    assert "Jane Doe" in out[0]["author"]


def test_openlibrary_normalizes():
    def fake_json(url, **k):
        return {"docs": [{"title": "Book", "key": "/works/OL1W",
                          "author_name": ["Kim"], "publisher": ["Munhak"],
                          "first_publish_year": 1999}]}
    out = search_openlibrary("book", limit=3, fetch_json_impl=fake_json)
    assert out[0]["title"] == "Book"
    assert out[0]["lane"] == "openlibrary"
    assert out[0]["kind"] == "book"
    assert out[0]["url"] == "https://openlibrary.org/works/OL1W"
```

- [ ] **Step 3: Run test**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_lanes_basic.py -v`
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/research/lanes/wikipedia.py backend/research/lanes/crossref.py backend/research/lanes/openlibrary.py tests/test_research_lanes_basic.py
git commit -m "feat(research): 위키/CrossRef/OpenLibrary 레인 이식"
```

---

## Task 4: 뉴스 RSS 레인 (Google News + Naver)

**Files:**
- Create: `backend/research/lanes/news_rss.py`
- Test: `tests/test_research_news.py`

- [ ] **Step 1: `news_rss.py` 이식 + import 재작성**

원본 `.../lanes/news_rss.py` 를 이식하되 import만 재작성(`auto_agent.research.lanes._http/_text/_trust` → `backend.research.lanes....`). 로직 동일: `search_google_news_rss`, `search_naver_news_api`(env 키 없으면 빈 리스트), `search_news`(통합·dedup), `_confidence_from_tier`. `classify_tier`를 쓰므로 Task 2의 trust_tiers.json이 있어야 한다.

- [ ] **Step 2: Write the failing test** — `tests/test_research_news.py`:

```python
from backend.research.lanes.news_rss import search_google_news_rss, search_news

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Big News - Example Times</title><link>https://some-random-news.example/a</link>
<pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate></item>
</channel></rss>"""


def test_google_news_rss_parses(monkeypatch):
    out = search_google_news_rss("topic", limit=5, fetch_text_impl=lambda u, **k: RSS)
    hits = [r for r in out if not r.get("error")]
    assert hits and hits[0]["title"] == "Big News"
    assert hits[0]["publisher"] == "Example Times"
    assert hits[0]["lane"] == "google_news_rss"
    assert hits[0]["kind"] == "news"


def test_google_news_rss_error_entry():
    def boom(u, **k):
        raise RuntimeError("net")
    out = search_google_news_rss("x", fetch_text_impl=boom)
    assert any(r.get("error") for r in out)


def test_search_news_no_naver_keys(monkeypatch):
    monkeypatch.delenv("NAVER_API_CLIENT_ID", raising=False)
    monkeypatch.delenv("NAVER_API_CLIENT_SECRET", raising=False)
    out = search_news("topic", limit=5, fetch_text_impl=lambda u, **k: RSS)
    assert any(r.get("title") == "Big News" for r in out)
```

(테스트 도메인 `some-random-news.example`는 tier unknown → confidence medium → 블록 안 됨. 만약 trust_tiers.json에 `.example`가 C로 잡히면 테스트가 비게 되니, 실제 파일에 `.example`가 없음을 전제로 한다 — 없으면 unknown.)

- [ ] **Step 3: Run test**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_news.py -v`
Expected: 3 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/research/lanes/news_rss.py tests/test_research_news.py
git commit -m "feat(research): 뉴스 RSS 레인 이식(Google News+Naver)"
```

---

## Task 5: 레인 패키지 익스포트

**Files:**
- Modify: `backend/research/lanes/__init__.py`
- Test: `tests/test_research_lanes_exports.py`

- [ ] **Step 1: `lanes/__init__.py` 작성**

`backend/research/lanes/__init__.py` 를 아래로 채운다:

```python
"""Research lanes — 외부 소스별 검색 모듈. 공통 결과 스키마(title/url/publisher/...)."""
from backend.research.lanes.wikipedia import search_wikipedia, fetch_wikipedia_article_content
from backend.research.lanes.news_rss import search_news
from backend.research.lanes.crossref import search_crossref
from backend.research.lanes.openlibrary import search_openlibrary

__all__ = [
    "search_wikipedia",
    "fetch_wikipedia_article_content",
    "search_news",
    "search_crossref",
    "search_openlibrary",
]
```

- [ ] **Step 2: Write the failing test** — `tests/test_research_lanes_exports.py`:

```python
def test_lane_exports_importable():
    from backend.research.lanes import (
        search_wikipedia, search_news, search_crossref, search_openlibrary,
        fetch_wikipedia_article_content,
    )
    for fn in (search_wikipedia, search_news, search_crossref, search_openlibrary):
        assert callable(fn)
```

- [ ] **Step 3: Run test**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_lanes_exports.py -v`
Expected: 1 passed.

- [ ] **Step 4: Commit**

```bash
git add backend/research/lanes/__init__.py tests/test_research_lanes_exports.py
git commit -m "feat(research): 레인 패키지 익스포트"
```

---

## Task 6: 수집기 — 병렬 수집 + 정규화/적재 헬퍼

**Files:**
- Create: `backend/research/collector.py`
- Test: `tests/test_research_collector_parallel.py`

- [ ] **Step 1: Write the failing test** — `tests/test_research_collector_parallel.py`:

```python
from backend.research import collector


def test_collect_lanes_parallel_aggregates(monkeypatch):
    monkeypatch.setattr(collector, "search_wikipedia",
                        lambda q, limit=8: [{"title": "W", "url": "u1", "lane": "wikipedia"}])
    monkeypatch.setattr(collector, "search_news",
                        lambda q, limit=8: [{"title": "N", "url": "u2", "lane": "google_news_rss"}])
    monkeypatch.setattr(collector, "search_crossref",
                        lambda q, limit=8: [{"error": "boom", "lane": "crossref"}])
    monkeypatch.setattr(collector, "search_openlibrary",
                        lambda q, limit=8: [{"title": "B", "url": "u3", "lane": "openlibrary"}])
    out = collector.collect_lanes_parallel("q")
    assert set(out.keys()) == {"wikipedia", "news", "crossref", "openlibrary"}
    assert out["wikipedia"][0]["title"] == "W"
    assert out["crossref"][0]["error"] == "boom"   # 한 레인 실패해도 나머지 정상


def test_normalize_source_skips_error_and_incomplete():
    assert collector._normalize_source({"error": "x"}, run_id="r", topic_slug="t") is None
    assert collector._normalize_source({"title": "", "url": "u"}, run_id="r", topic_slug="t") is None
    s = collector._normalize_source(
        {"title": "T", "url": "https://x", "kind": "news", "lane": "google_news_rss",
         "tier_hint": "A"}, run_id="r", topic_slug="t")
    assert s["source_id"].startswith("src_")
    assert s["raw_path"].endswith(".md")
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_collector_parallel.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.research.collector`.

- [ ] **Step 3: `collector.py` 작성(헬퍼 + 병렬 수집)**

`backend/research/collector.py`:

```python
"""결정적 리서치 수집 — 쿼리 리스트를 받아 4레인 병렬 호출 → 정규화 → 적재.
v3 fresh_collector_module 이식. 진행 로그는 on_event 콜백(PROGRESS_FILE env 제거).
입력은 쿼리 리스트(브리프/LLM은 상위 단계)."""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.research.lanes import (
    search_crossref,
    search_news,
    search_openlibrary,
    search_wikipedia,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(text: str, *, max_len: int = 60) -> str:
    s = re.sub(r"[^\w\s가-힣-]", "", str(text or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:max_len] or "topic"


def _hash_short(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _source_id(item: dict) -> str:
    title = str(item.get("title") or "").strip()
    url = str(item.get("url") or "").strip()
    base = f"{_slug(title, max_len=40)}_{_hash_short(url or title)}"
    return f"src_{base}"


def collect_lanes_parallel(query: str, *, limit_per_lane: int = 8,
                           max_workers: int = 4) -> dict[str, list[dict]]:
    """4레인 병렬 호출, lane명→결과. 한 레인 실패는 error 엔트리로 격리."""
    lane_funcs = {           # 람다가 모듈 전역 함수를 호출 시점에 해석 → 테스트 monkeypatch 가능
        "wikipedia": lambda q, lim: search_wikipedia(q, limit=lim),
        "news": lambda q, lim: search_news(q, limit=lim),
        "crossref": lambda q, lim: search_crossref(q, limit=lim),
        "openlibrary": lambda q, lim: search_openlibrary(q, limit=lim),
    }
    out: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fn, query, limit_per_lane): name
                   for name, fn in lane_funcs.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                out[name] = fut.result()
            except Exception as exc:
                out[name] = [{"error": str(exc), "lane": name, "query": query}]
    return out


def _normalize_source(item: dict, *, run_id: str, topic_slug: str) -> dict[str, Any] | None:
    """레인 결과를 공통 source 스키마로. error/불완전 엔트리는 None."""
    if item.get("error"):
        return None
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or "").strip()
    if not url or not title:
        return None
    sid = _source_id(item)
    return {
        "source_id": sid,
        "title": title,
        "url": url,
        "publisher": str(item.get("publisher") or ""),
        "published_at": str(item.get("published_at") or ""),
        "retrieved_at": _now_iso(),
        "source_type": str(item.get("kind") or "reference"),
        "lane": str(item.get("lane") or ""),
        "tier_hint": str(item.get("tier_hint") or "unknown"),
        "snippet": str(item.get("snippet") or ""),
        "lang": str(item.get("lang") or ""),
        "doi": str(item.get("doi") or ""),
        "author": str(item.get("author") or ""),
        "topic_slug": topic_slug,
        "run_id": run_id,
        "raw_path": f"raw/{topic_slug}/{run_id}/source_notes/{sid}.md",
    }


def _write_source_note(research_dir: Path, source: dict) -> None:
    note_path = research_dir / source["raw_path"]
    note_path.parent.mkdir(parents=True, exist_ok=True)
    front = (
        f"---\n"
        f"source_id: {source['source_id']}\n"
        f"title: {json.dumps(source['title'], ensure_ascii=False)}\n"
        f"url: {source['url']}\n"
        f"publisher: {json.dumps(source.get('publisher', ''), ensure_ascii=False)}\n"
        f"published_at: {source.get('published_at', '')}\n"
        f"retrieved_at: {source['retrieved_at']}\n"
        f"lane: {source['lane']}\n"
        f"tier_hint: {source['tier_hint']}\n"
        f"topic_slug: {source['topic_slug']}\n"
        f"run_id: {source['run_id']}\n"
        f"---\n\n"
        f"# {source['title']}\n\n"
        f"- URL: {source['url']}\n"
    )
    if source.get("author"):
        front += f"- Author: {source['author']}\n"
    if source.get("publisher"):
        front += f"- Publisher: {source['publisher']}\n"
    if source.get("snippet"):
        front += f"\n## Snippet\n\n{source['snippet']}\n"
    note_path.write_text(front, encoding="utf-8")


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_collector_parallel.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/research/collector.py tests/test_research_collector_parallel.py
git commit -m "feat(research): 수집기 병렬호출+정규화/적재 헬퍼 이식"
```

---

## Task 7: 수집기 진입점 — collect_topic + collect_queries

**Files:**
- Modify: `backend/research/collector.py` (함수 2개 추가)
- Test: `tests/test_research_collect_queries.py`

- [ ] **Step 1: Write the failing test** — `tests/test_research_collect_queries.py`:

```python
import json
from pathlib import Path
from backend.research import collector


def _patch_lanes(monkeypatch):
    monkeypatch.setattr(collector, "collect_lanes_parallel", lambda q, **k: {
        "wikipedia": [{"title": "W", "url": "https://ko.wikipedia.org/wiki/W",
                       "lane": "wikipedia", "tier_hint": "A", "kind": "reference",
                       "snippet": "s"}],
        "crossref": [{"error": "boom", "lane": "crossref"}],
    })


def test_collect_queries_writes_notes_and_manifests(tmp_path, monkeypatch):
    _patch_lanes(monkeypatch)
    events = []
    out = collector.collect_queries(tmp_path, ["유한양행"], on_event=events.append)
    assert out["sources"] == 1
    # 소스노트 1개 + manifests
    notes = list((tmp_path / "research" / "raw").rglob("*.md"))
    assert len(notes) == 1
    manifest = Path(out["manifest"])
    assert manifest.is_file()
    rows = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["title"] == "W" and rows[0]["tier_hint"] == "A"
    runs = (tmp_path / "research" / "manifests" / collector._slug("유한양행") / "runs.jsonl")
    assert runs.is_file()
    assert events                                  # on_event 호출됨


def test_collect_queries_skips_blank_and_counts(tmp_path, monkeypatch):
    _patch_lanes(monkeypatch)
    out = collector.collect_queries(tmp_path, ["", "  ", "주제"])
    assert len(out["runs"]) == 1                   # 빈 쿼리 스킵
    assert out["sources"] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_collect_queries.py -v`
Expected: FAIL — `AttributeError: ... has no attribute 'collect_queries'`.

- [ ] **Step 3: `collect_topic` + `collect_queries` 추가**

`backend/research/collector.py` 끝에 추가:

```python
def collect_topic(proj_dir: Path, *, topic_slug: str, query: str,
                  limit_per_lane: int = 8, on_event=None) -> dict[str, Any]:
    """단일 토픽(=쿼리) 수집 → research/raw + manifests 적재. run_record 반환."""
    research_dir = Path(proj_dir) / "research"
    run_id = _run_id()
    manifests_dir = research_dir / "manifests" / topic_slug
    sources_jsonl = manifests_dir / "sources.jsonl"
    runs_jsonl = manifests_dir / "runs.jsonl"

    if on_event:
        on_event(f"리서치 '{topic_slug}' 수집 시작 (query={query})")
    lane_results = collect_lanes_parallel(query, limit_per_lane=limit_per_lane)

    saved = 0
    errors: list[dict] = []
    tier_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}
    for lane_name, items in lane_results.items():
        for item in items:
            if item.get("error"):
                errors.append({"lane": lane_name, "error": item["error"]})
                continue
            source = _normalize_source(item, run_id=run_id, topic_slug=topic_slug)
            if not source:
                continue
            _write_source_note(research_dir, source)
            _append_jsonl(sources_jsonl, source)
            tier_counts[source["tier_hint"]] = tier_counts.get(source["tier_hint"], 0) + 1
            lane_counts[source["lane"]] = lane_counts.get(source["lane"], 0) + 1
            saved += 1

    run_record = {
        "run_id": run_id, "topic_slug": topic_slug, "query": query,
        "started_at": _now_iso(), "lanes": list(lane_results.keys()),
        "saved": saved, "errors": errors,
        "tier_counts": tier_counts, "lane_counts": lane_counts,
    }
    _append_jsonl(runs_jsonl, run_record)
    if on_event:
        on_event(f"리서치 '{topic_slug}' 완료 — {saved}개 source, errors={len(errors)}")
    return run_record


def collect_queries(proj_dir, queries: list, *, limit_per_lane: int = 8,
                    on_event=None) -> dict[str, Any]:
    """쿼리 리스트(각 str 또는 {'query':...})를 토픽별 수집. 진입점.
    반환: {'runs': [run_record...], 'sources': 총 적재수, 'manifest': 마지막 sources.jsonl 경로}."""
    proj_dir = Path(proj_dir)
    runs: list[dict] = []
    total = 0
    last_manifest = ""
    for q in queries:
        query = (q.get("query") if isinstance(q, dict) else str(q or "")).strip()
        if not query:
            continue
        topic_slug = _slug(query)
        rec = collect_topic(proj_dir, topic_slug=topic_slug, query=query,
                            limit_per_lane=limit_per_lane, on_event=on_event)
        runs.append(rec)
        total += rec.get("saved", 0)
        last_manifest = str(proj_dir / "research" / "manifests" / topic_slug / "sources.jsonl")
    return {"runs": runs, "sources": total, "manifest": last_manifest}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_collect_queries.py -v`
Expected: 2 passed.

- [ ] **Step 5: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존 391 + 신규(~23) 전부 PASS, 실패 0.

- [ ] **Step 6: Commit**

```bash
git add backend/research/collector.py tests/test_research_collect_queries.py
git commit -m "feat(research): collect_queries 진입점 — 쿼리 리스트→소스노트/매니페스트 적재"
```

---

## Self-Review 결과

**Spec coverage:**
- 모듈 레이아웃(lanes/_http,_text,_trust,trust_tiers.json,4레인,collector) → Task 1~7 ✓
- 정규화 스키마(title/url/lang/snippet/publisher/kind/lane/tier_hint) → 레인 이식(원본 유지) ✓
- 공개 인터페이스(search_X, collect_lanes_parallel, collect_queries) → Task 3~7 ✓
- 적응(import 재작성, trust_tiers 경로, PROGRESS_FILE→on_event, PROJECT_DIR→proj_dir, 출력 proj_dir/research) → Task 2·6·7 ✓
- 출력 포맷 v3 동일(source_notes frontmatter + sources.jsonl + runs.jsonl) → Task 6·7 ✓
- 에러 처리(부분 실패 허용·error 엔트리) → Task 3·4·6 테스트 ✓
- 테스트(레인 monkeypatch·trust·병렬·적재·on_event) → 전 태스크 ✓
- 범위 밖(LLM/브리프/오케스트레이션/원고) → 미포함 확인 ✓

**Placeholder scan:** 이식 태스크는 "원본 경로 + 정확한 수정 목록"으로 구체적(추상 지시 아님). 신규 코드·테스트는 전부 완전. ✓

**Type consistency:** `collect_lanes_parallel`/`_normalize_source`/`collect_topic`/`collect_queries` 시그니처가 Task 6→7에서 일치. 레인 함수명(`search_wikipedia/news/crossref/openlibrary`)이 collector import·monkeypatch 지점과 일치. trust_tiers.json 경로는 `lanes/`(parent)로 Task 2·_trust 일관. ✓

**알려진 가정:** trust_tiers.json의 실제 A-tier 도메인(en.wikipedia.org 등)이 테스트 기대값과 맞는지 Task 2/4에서 파일 기준으로 확인(파일이 진실).
