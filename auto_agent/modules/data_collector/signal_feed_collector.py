"""External trend/news/social/community signal collector."""
import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

from auto_agent.paths import get_vault_dir

logger = logging.getLogger(__name__)

# 일부 사이트(예: ppomppu)가 비-브라우저 UA를 차단해 403 응답을 보낸다.
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


DEFAULT_SIGNAL_FEEDS = {
    "feeds": [
        {
            "name": "google-news-top-ko",
            "url": "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
            "target_dir": "market/news",
            "enabled": True,
        },
        {
            "name": "google-news-business-ko",
            "url": "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
            "target_dir": "market/news",
            "enabled": True,
        },
        {
            "name": "google-news-entertainment-ko",
            "url": "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=ko&gl=KR&ceid=KR:ko",
            "target_dir": "market/news",
            "enabled": True,
        },
        {
            "name": "daum-news-home",
            "url": "https://news.daum.net",
            "target_dir": "market/news",
            "enabled": False,
            "notes": "HTML import of Daum news home. More useful than daum.net main page for popular-news signals.",
        },
        {
            "name": "reddit-popular-hot",
            "url": "https://www.reddit.com/r/popular/.rss",
            "target_dir": "market/communities",
            "enabled": False,
            "notes": "Direct Atom feed for broad community hot posts.",
        },
        {
            "name": "reddit-todayilearned-hot",
            "url": "https://www.reddit.com/r/todayilearned/hot/.rss",
            "target_dir": "market/communities",
            "enabled": False,
            "notes": "Useful knowledge-style community feed for explainer topic discovery.",
        },
        {
            "name": "hacker-news-frontpage",
            "url": "https://news.ycombinator.com/rss",
            "target_dir": "market/communities",
            "enabled": False,
            "notes": "Direct RSS feed for tech/business community signals.",
        },
        {
            "name": "damoang-free",
            "url": "https://damoang.net/free",
            "target_dir": "market/communities",
            "enabled": True,
            "notes": "HTML list page import for Korean community hot-post signals.",
        },
        {
            "name": "daum-cafe-popular-mobile",
            "url": "https://m.cafe.daum.net",
            "target_dir": "market/communities",
            "enabled": True,
            "notes": "HTML import of Daum Cafe popular posts from the mobile ranking page.",
        },
        {
            "name": "social-signals",
            "url": "",
            "target_dir": "market/social",
            "enabled": False,
            "notes": "Add an RSS/Atom or proxy feed for X/Threads snapshots. Self-hosted RSSHub or manual snapshot import is recommended.",
        },
        {
            "name": "community-signals",
            "url": "",
            "target_dir": "market/communities",
            "enabled": False,
            "notes": "Use for Korean community hot-post aggregators without stable RSS. Prefer manual snapshot import from sources like 글토끼모아 or 다모앙.",
        },
        {
            "name": "finance-community-signals",
            "url": "https://www.ppomppu.co.kr/zboard/zboard.php?id=money",
            "target_dir": "market/communities",
            "enabled": False,
            "notes": "Starter Korean source for economic or personal-finance communities that match 이로미즘.",
        },
        {
            "name": "ai-community-signals",
            "url": "https://news.hada.io/",
            "target_dir": "market/communities",
            "enabled": False,
            "notes": "Starter Korean source for AI, model, GPU, and agent communities that match ai백과사전.",
        },
    ]
}


class SignalFeedCollector:
    """Collect bounded signal feeds into the vault."""

    def __init__(self, vault_dir: Optional[Path] = None):
        self._vault_dir = vault_dir or get_vault_dir()
        self._collector_dir = self._vault_dir / ".collector"
        self._collector_dir.mkdir(parents=True, exist_ok=True)
        self._config_path = self._collector_dir / "signal_feeds.json"
        self._ensure_default_config()

    def collect_all(self, limit_per_feed: int = 20) -> Dict:
        config = self._load_config()
        results = {"feeds": [], "collected": 0}
        for feed in config.get("feeds", []):
            if not feed.get("enabled"):
                continue
            url = str(feed.get("url", "")).strip()
            if not url:
                continue
            try:
                items = self._fetch_feed_items(url, limit=limit_per_feed)
                output = self._write_feed_snapshot(
                    name=str(feed.get("name", "signal-feed")),
                    target_dir=str(feed.get("target_dir", "market/news")),
                    source_url=url,
                    items=items,
                )
                results["feeds"].append(
                    {
                        "name": feed.get("name"),
                        "target_dir": feed.get("target_dir"),
                        "count": len(items),
                        "output": str(output),
                    }
                )
                results["collected"] += len(items)
            except Exception as exc:
                logger.error("signal feed collection failed [%s]: %s", feed.get("name"), exc)
                results["feeds"].append(
                    {
                        "name": feed.get("name"),
                        "target_dir": feed.get("target_dir"),
                        "count": 0,
                        "error": str(exc),
                    }
                )
        return results

    def import_snapshot(self, source_path: Path, target_dir: str, name: Optional[str] = None) -> Path:
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(source_path)
        items = self._load_snapshot_items(source_path)
        snapshot_name = name or source_path.stem
        return self._write_feed_snapshot(
            name=f"manual-{snapshot_name}",
            target_dir=target_dir,
            source_url=str(source_path),
            items=items,
        )

    def import_snapshot_url(self, source_url: str, target_dir: str, name: Optional[str] = None) -> Path:
        request = urllib.request.Request(source_url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
            content_type = (response.getheader("content-type") or "").lower()
        items = self._load_remote_items(payload, content_type=content_type, source_url=source_url)
        snapshot_name = name or Path(source_url.rstrip("/")).name or "url-import"
        return self._write_feed_snapshot(
            name=f"url-{snapshot_name}",
            target_dir=target_dir,
            source_url=source_url,
            items=items,
        )

    def _ensure_default_config(self) -> None:
        if self._config_path.exists():
            return
        self._config_path.write_text(
            json.dumps(DEFAULT_SIGNAL_FEEDS, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_config(self) -> Dict:
        return json.loads(self._config_path.read_text(encoding="utf-8"))

    def _fetch_feed_items(self, url: str, limit: int = 20) -> List[Dict]:
        request = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
            content_type = (response.getheader("content-type") or "").lower()
        items = self._load_remote_items(payload, content_type=content_type, source_url=url)
        return items[:limit]

    def _write_feed_snapshot(
        self,
        name: str,
        target_dir: str,
        source_url: str,
        items: List[Dict],
    ) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_dir = self._vault_dir / target_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{today}-{name}.json"
        payload = {
            "source": name,
            "source_url": source_url,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }
        output_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return output_path

    def _load_snapshot_items(self, source_path: Path) -> List[Dict]:
        text = source_path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            return []

        if source_path.suffix.lower() == ".json":
            payload = json.loads(text)
            if isinstance(payload, dict) and isinstance(payload.get("items"), list):
                return payload["items"]
            if isinstance(payload, list):
                return payload

        if source_path.suffix.lower() == ".jsonl":
            items = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                items.append(json.loads(line))
            return items

        if source_path.suffix.lower() in {".html", ".htm"}:
            return self._extract_items_from_html(text, base_url="")

        return [{"title": source_path.stem, "summary": text[:4000], "link": "", "published": ""}]

    def _load_remote_items(self, payload: bytes, content_type: str, source_url: str) -> List[Dict]:
        text = self._decode_payload(payload, content_type).strip()
        if not text:
            return []
        if "json" in content_type:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
                return parsed["items"]
            if isinstance(parsed, list):
                return parsed
        if "xml" in content_type or text.startswith("<?xml") or "<rss" in text or "<feed" in text:
            try:
                return self._parse_feed_payload(text)
            except Exception:
                pass
        if "html" in content_type or "<html" in text.lower():
            items = self._extract_items_from_html(text, base_url=source_url)
            return items
        return [{"title": Path(source_url).name or source_url, "summary": text[:4000], "link": source_url, "published": ""}]

    def _decode_payload(self, payload: bytes, content_type: str) -> str:
        charsets = []
        match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "", flags=re.I)
        if match:
            charsets.append(match.group(1).strip().strip('"').strip("'"))
        charsets.extend(["utf-8", "cp949", "euc-kr"])
        seen = set()
        for charset in charsets:
            normalized = charset.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            try:
                return payload.decode(charset)
            except Exception:
                continue
        return payload.decode("utf-8", errors="ignore")

    def _parse_feed_payload(self, text: str, limit: int = 20) -> List[Dict]:
        root = ET.fromstring(text)
        items: List[Dict] = []

        channel = root.find("channel")
        if channel is not None:
            for item in channel.findall("item")[:limit]:
                items.append(
                    {
                        "title": self._child_text(item, "title"),
                        "link": self._child_text(item, "link"),
                        "published": self._child_text(item, "pubDate"),
                        "summary": self._child_text(item, "description"),
                    }
                )
            return items

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns)[:limit]:
            link = ""
            link_el = entry.find("atom:link", ns)
            if link_el is not None:
                link = link_el.attrib.get("href", "")
            items.append(
                {
                    "title": self._child_text(entry, "{http://www.w3.org/2005/Atom}title"),
                    "link": link,
                    "published": self._child_text(entry, "{http://www.w3.org/2005/Atom}updated"),
                    "summary": self._child_text(entry, "{http://www.w3.org/2005/Atom}summary"),
                }
            )
        return items

    def _extract_items_from_html(self, html: str, base_url: str, limit: int = 25) -> List[Dict]:
        parser = _AnchorExtractor(base_url=base_url)
        parser.feed(html)
        seen = set()
        items: List[Dict] = []
        parsed_items = parser.items
        post_like_items = [item for item in parsed_items if self._looks_like_post_link(item["link"])]
        if post_like_items:
            parsed_items = post_like_items
        for item in parsed_items:
            title = self._normalize_html_title(item["title"])
            link = item["link"].strip()
            if not title or not link:
                continue
            if len(title) < 6 or len(title) > 140:
                continue
            lowered = title.lower()
            if lowered in {"로그인", "회원가입", "더보기", "menu", "home"}:
                continue
            if "#comments" in link or "/promotion/" in link or "go=comments" in link or "id=regulation" in link or "/user/" in link:
                continue
            if (
                title.startswith("공지 ")
                or "홍보 홍보" in title
                or "[삭제된 게시물입니다]" in title
                or title in {"GeekNews", "Weekly", "댓글과 토론"}
                or "이용 규칙" in title
            ):
                continue
            key = (title, link)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "title": title,
                    "link": link,
                    "published": "",
                    "summary": "",
                }
            )
            if len(items) >= limit:
                break
        return items

    def _child_text(self, node, tag: str) -> str:
        child = node.find(tag)
        if child is None or child.text is None:
            return ""
        return child.text.strip()

    def _looks_like_post_link(self, link: str) -> bool:
        return bool(
            re.search(r"/[A-Za-z0-9_-]+/\d+(?:$|[?#])", link)
            or re.search(r"view\.php\?.*\bno=\d+", link)
        )

    def _normalize_html_title(self, title: str) -> str:
        cleaned = " ".join(title.split())
        cleaned = re.sub(r"^순위\d+\s*", "", cleaned)
        cleaned = re.sub(r"^\d+\s+", "", cleaned)
        cleaned = re.sub(r"\bN\b", " ", cleaned)
        cleaned = re.sub(r"\s*카페명.*$", "", cleaned)
        cleaned = re.sub(r"\s+\[\d+\]\s*$", "", cleaned)
        cleaned = re.split(r"\s{2,}", cleaned)[0]
        return cleaned.strip(" -")


class _AnchorExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self._current_href = ""
        self._current_text: List[str] = []
        self.items: List[Dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs):
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href", "").strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            return
        self._current_href = urljoin(self.base_url, href) if self.base_url else href
        self._current_text = []

    def handle_data(self, data: str):
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str):
        if tag != "a" or not self._current_href:
            return
        text = "".join(self._current_text).strip()
        self.items.append({"title": text, "link": self._current_href})
        self._current_href = ""
        self._current_text = []
