"""fresh_collector_module 단위 테스트 — lane을 mock하여 raw/manifests 출력만 검증."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from auto_agent.modules import fresh_collector_module as fc


SAMPLE_LANE_RESULTS = {
    "wikipedia": [
        {
            "title": "유한양행",
            "url": "https://ko.wikipedia.org/wiki/유한양행",
            "lang": "ko",
            "publisher": "Wikipedia",
            "snippet": "한국 제약회사",
            "kind": "reference",
            "lane": "wikipedia",
            "tier_hint": "A",
        }
    ],
    "news": [
        {
            "title": "유한양행 100주년",
            "url": "https://yna.co.kr/article/1",
            "publisher": "연합뉴스",
            "kind": "news",
            "lane": "google_news_rss",
            "tier_hint": "A",
            "published_at": "Mon, 01 Feb 2026",
        }
    ],
    "crossref": [
        {
            "title": "Yuhan Corp Study",
            "url": "https://doi.org/10.1234/x",
            "kind": "paper",
            "lane": "crossref",
            "tier_hint": "B",
        }
    ],
    "openlibrary": [
        {"error": "rate limited", "lane": "openlibrary"},
    ],
}


def test_collect_topic_writes_raw_and_manifests(tmp_path: Path):
    with patch.object(fc, "collect_lanes_parallel", return_value=SAMPLE_LANE_RESULTS):
        record = fc.collect_topic(
            tmp_path, topic_slug="유한양행", query="유한양행 100주년"
        )

    assert record["saved"] == 3
    assert record["lane_counts"]["wikipedia"] == 1
    assert record["tier_counts"]["A"] == 2
    assert record["tier_counts"]["B"] == 1
    assert len(record["errors"]) == 1  # openlibrary 에러 기록

    research = tmp_path / "research"
    sources_jsonl = research / "manifests" / "유한양행" / "sources.jsonl"
    runs_jsonl = research / "manifests" / "유한양행" / "runs.jsonl"
    assert sources_jsonl.exists()
    assert runs_jsonl.exists()

    # 3개 source 라인 적재
    lines = sources_jsonl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    first = json.loads(lines[0])
    assert "source_id" in first
    assert first["topic_slug"] == "유한양행"
    assert first["raw_path"].startswith("raw/유한양행/")

    # raw markdown 파일이 실제로 떨어졌나
    raw_files = list((research / "raw" / "유한양행").rglob("*.md"))
    assert len(raw_files) == 3
    md_text = raw_files[0].read_text(encoding="utf-8")
    assert "source_id:" in md_text
    assert "title:" in md_text


def test_collect_topic_skips_invalid_results(tmp_path: Path):
    bad_results = {
        "wikipedia": [
            {"title": "", "url": "https://wikipedia.org/x"},  # 제목 없음
            {"title": "good", "url": ""},  # url 없음
            {"error": "fail"},
            {"title": "valid", "url": "https://en.wikipedia.org/wiki/Valid",
             "lane": "wikipedia", "tier_hint": "A"},
        ],
        "news": [], "crossref": [], "openlibrary": [],
    }
    with patch.object(fc, "collect_lanes_parallel", return_value=bad_results):
        record = fc.collect_topic(tmp_path, topic_slug="t", query="q")

    assert record["saved"] == 1  # 유효 1개만
    assert len(record["errors"]) == 1


def test_extract_topics_from_brief_uses_real_topic_first():
    brief = {
        "real_topic": "유일한 박사와 유한양행",
        "entities": ["유한양행", "유일한", "안티푸라민"],
    }
    topics = fc._extract_topics_from_brief(brief, "fallback_slug")
    assert topics[0]["query"] == "유일한 박사와 유한양행"
    # entities 추가 (first 5)
    assert any(t["query"] == "유한양행" for t in topics)
    assert any(t["query"] == "유일한" for t in topics)


def test_extract_topics_falls_back_to_project_slug():
    topics = fc._extract_topics_from_brief({}, "유한양행_100주년")
    assert len(topics) == 1
    assert topics[0]["query"] == "유한양행 100주년"


def test_collect_lanes_parallel_calls_all_4(monkeypatch):
    called: list[str] = []
    monkeypatch.setattr(fc, "LANE_FUNCS", {
        "wikipedia": lambda q, l: [{"lane": "wikipedia", "title": "x", "url": "https://x"}] if not called.append("w") else [],
        "news": lambda q, l: [{"lane": "n", "title": "x", "url": "https://x"}] if not called.append("n") else [],
        "crossref": lambda q, l: [{"lane": "c", "title": "x", "url": "https://x"}] if not called.append("c") else [],
        "openlibrary": lambda q, l: [{"lane": "o", "title": "x", "url": "https://x"}] if not called.append("o") else [],
    })
    results = fc.collect_lanes_parallel("anything", limit_per_lane=1)
    assert set(called) == {"w", "n", "c", "o"}
    assert set(results.keys()) == {"wikipedia", "news", "crossref", "openlibrary"}


def test_lane_failure_recorded_as_error(monkeypatch):
    def bad(q, l):
        raise RuntimeError("network down")
    monkeypatch.setattr(fc, "LANE_FUNCS", {
        "wikipedia": bad,
        "news": lambda q, l: [],
        "crossref": lambda q, l: [],
        "openlibrary": lambda q, l: [],
    })
    results = fc.collect_lanes_parallel("anything", limit_per_lane=1)
    assert results["wikipedia"][0]["error"] == "network down"
