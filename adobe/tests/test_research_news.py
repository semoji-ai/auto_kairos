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
