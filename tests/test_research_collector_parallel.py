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
