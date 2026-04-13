import json
from pathlib import Path

from auto_agent.modules.data_collector.signal_feed_collector import SignalFeedCollector


class _FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/rss+xml"):
        self._payload = payload
        self._content_type = content_type

    def read(self):
        return self._payload

    def getheader(self, name, default=None):
        if name.lower() == "content-type":
            return self._content_type
        return default

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_signal_feed_collector_writes_snapshot(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)

    config_path = vault / ".collector" / "signal_feeds.json"
    config_path.write_text(
        json.dumps(
            {
                "feeds": [
                    {
                        "name": "test-news",
                        "url": "https://example.com/feed.xml",
                        "target_dir": "market/news",
                        "enabled": True,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    rss = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Headline A</title>
      <link>https://example.com/a</link>
      <pubDate>Sat, 12 Apr 2026 10:00:00 GMT</pubDate>
      <description>Summary A</description>
    </item>
  </channel>
</rss>
"""

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=20: _FakeResponse(rss),
    )

    result = collector.collect_all(limit_per_feed=5)
    assert result["collected"] == 1
    files = list((vault / "market" / "news").glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["source"] == "test-news"
    assert payload["items"][0]["title"] == "Headline A"


def test_signal_feed_collector_bootstraps_default_config(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)
    config = json.loads((vault / ".collector" / "signal_feeds.json").read_text(encoding="utf-8"))
    names = [feed["name"] for feed in config["feeds"]]
    assert "google-news-top-ko" in names
    assert "daum-news-home" in names
    assert "daum-cafe-popular-mobile" in names
    assert "community-signals" in names
    assert "finance-community-signals" in names
    assert "ai-community-signals" in names
    assert "reddit-popular-hot" in names
    assert "hacker-news-frontpage" in names
    damoang = next(feed for feed in config["feeds"] if feed["name"] == "damoang-free")
    assert damoang["enabled"] is True


def test_signal_feed_collector_imports_manual_snapshot(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)
    source = tmp_path / "threads_snapshot.md"
    source.write_text("# Threads\n- 흑백요리사 관련 반응 급증", encoding="utf-8")
    output = collector.import_snapshot(source, "market/social", name="threads-hot")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == "manual-threads-hot"
    assert "흑백요리사" in payload["items"][0]["summary"]


def test_signal_feed_collector_imports_snapshot_url_html(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)

    html = """
<html><body>
  <a href=\"/post/1\">흑백요리사 이후 중화요리 4대문파가 다시 뜨는 이유</a>
  <a href=\"/post/2\">상여금 10억이면 실제 세금은 얼마나 뗄까</a>
</body></html>
""".encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=20: _FakeResponse(html, content_type="text/html; charset=utf-8"),
    )

    output = collector.import_snapshot_url(
        "https://damoang.net",
        "market/communities",
        name="damoang-home",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == "url-damoang-home"
    assert len(payload["items"]) == 2
    assert "흑백요리사" in payload["items"][0]["title"]


def test_signal_feed_collector_prefers_post_like_links(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)

    html = """
<html><body>
  <a href=\"/free\">자유게시판</a>
  <a href=\"/free/6122409\">4     숙종에 의해 노산군이 단종으로 복권된 이후, 금성대군은... N     15소년우주표류기 16:44 240 4</a>
  <a href=\"/free/6122280\">10     호르무즈 섬의 핏물 같은 땅과 바닷물,gif N     아름다워용 15:56 1.1k 10</a>
  <a href=\"/free/6122412#comments\">[3]</a>
</body></html>
""".encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=20: _FakeResponse(html, content_type="text/html; charset=utf-8"),
    )

    output = collector.import_snapshot_url(
        "https://damoang.net/free",
        "market/communities",
        name="damoang-free",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    titles = [item["title"] for item in payload["items"]]
    assert "자유게시판" not in titles
    assert any("숙종에 의해" in title for title in titles)
    assert any("호르무즈 섬의 핏물 같은 땅과 바닷물" in title for title in titles)


def test_signal_feed_collector_collect_all_with_html_feed(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)

    config_path = vault / ".collector" / "signal_feeds.json"
    config_path.write_text(
        json.dumps(
            {
                "feeds": [
                    {
                        "name": "damoang-free",
                        "url": "https://damoang.net/free",
                        "target_dir": "market/communities",
                        "enabled": True,
                    }
                ]
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    html = """
<html><body>
  <a href=\"/free\">자유게시판</a>
  <a href=\"/free/6122409\">4     숙종에 의해 노산군이 단종으로 복권된 이후, 금성대군은... N     15소년우주표류기 16:44 240 4</a>
  <a href=\"/free/6122280\">10     호르무즈 섬의 핏물 같은 땅과 바닷물,gif N     아름다워용 15:56 1.1k 10</a>
</body></html>
""".encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=20: _FakeResponse(html, content_type="text/html; charset=utf-8"),
    )

    result = collector.collect_all(limit_per_feed=5)
    assert result["collected"] == 2
    files = list((vault / "market" / "communities").glob("*.json"))
    assert len(files) == 1


def test_signal_feed_collector_drops_unparsed_html_instead_of_raw_dump(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)

    html = "<html><head><title>blocked</title></head><body>access denied</body></html>".encode("utf-8")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=20: _FakeResponse(html, content_type="text/html; charset=utf-8"),
    )

    output = collector.import_snapshot_url(
        "https://damoang.net/free",
        "market/communities",
        name="damoang-blocked",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["items"] == []


def test_signal_feed_collector_decodes_euc_kr_html(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    collector = SignalFeedCollector(vault_dir=vault)

    html = """
<html><body>
  <a href=\"/zboard/zboard.php?id=money\">재테크포럼</a>
  <a href=\"/zboard/view.php?id=regulation&page=1&no=6\">전체 게시판 이용 규칙</a>
  <a href=\"/zboard/view.php?id=money&no=1\">상여금 10억이면 세금은 얼마일까</a>
  <a href=\"/zboard/view.php?id=money&no=2\">IRP 계좌 고민입니다</a>
</body></html>
""".encode("cp949")

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout=20: _FakeResponse(html, content_type="text/html; charset=euc-kr"),
    )

    output = collector.import_snapshot_url(
        "https://www.ppomppu.co.kr/zboard/zboard.php?id=money",
        "market/communities",
        name="ppomppu-money",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    titles = [item["title"] for item in payload["items"]]
    assert "재테크포럼" not in titles
    assert "전체 게시판 이용 규칙" not in titles
    assert "상여금 10억이면 세금은 얼마일까" in titles
    assert "IRP 계좌 고민입니다" in titles
