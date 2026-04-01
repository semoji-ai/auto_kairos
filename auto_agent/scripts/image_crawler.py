"""이미지 웹 크롤링 — Serper 검색 + 페이지 크롤링 + 워터마크 필터.

Usage:
  python -m auto_agent.scripts.image_crawler "구다이글로벌 CEO"
  python -m auto_agent.scripts.image_crawler "조선미녀 화장품" --save-vault
"""
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
except ImportError:
    pass

SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")

# 워터마크 도메인 블랙리스트
BLOCKED_DOMAINS = {
    "shutterstock.com", "gettyimages.com", "istockphoto.com",
    "alamy.com", "dreamstime.com", "123rf.com", "depositphotos.com",
    "bigstockphoto.com", "canstockphoto.com", "pond5.com",
}

# 이미지 확장자
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def search_images(query: str, num: int = 10) -> List[Dict]:
    """Serper 이미지 검색."""
    if not SERPER_API_KEY:
        logger.error("SERPER_API_KEY 미설정")
        return []

    resp = requests.post(
        "https://google.serper.dev/images",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": num, "gl": "kr", "hl": "ko"},
        timeout=10,
    )
    if not resp.ok:
        logger.error("Serper 검색 실패: %s", resp.status_code)
        return []

    results = []
    for img in resp.json().get("images", []):
        url = img.get("imageUrl", "")
        domain = urlparse(url).netloc.lower()

        # 워터마크 도메인 필터
        if any(blocked in domain for blocked in BLOCKED_DOMAINS):
            continue

        results.append({
            "url": url,
            "title": img.get("title", ""),
            "source": img.get("link", ""),
            "domain": domain,
            "width": img.get("imageWidth", 0),
            "height": img.get("imageHeight", 0),
        })

    return results


def search_web_for_images(query: str, num: int = 5) -> List[Dict]:
    """Serper 웹 검색 → 출처 페이지에서 이미지 추출."""
    if not SERPER_API_KEY:
        return []

    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": num, "gl": "kr", "hl": "ko"},
        timeout=10,
    )
    if not resp.ok:
        return []

    results = []
    for item in resp.json().get("organic", []):
        page_url = item.get("link", "")
        title = item.get("title", "")
        domain = urlparse(page_url).netloc.lower()

        if any(blocked in domain for blocked in BLOCKED_DOMAINS):
            continue

        # 페이지 크롤링 → 이미지 추출
        try:
            page_resp = requests.get(page_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if page_resp.ok:
                images = _extract_images_from_html(page_resp.text, page_url)
                for img in images[:3]:  # 페이지당 최대 3개
                    img["source_page"] = page_url
                    img["source_title"] = title
                    img["source_domain"] = domain
                    results.append(img)
        except Exception:
            continue

    return results


def _extract_images_from_html(html: str, base_url: str) -> List[Dict]:
    """HTML에서 이미지 태그 추출."""
    images = []
    # <img src="..." alt="..."> 패턴
    for match in re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE):
        src = match.group(1)
        # 상대 경로 → 절대 경로
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            parsed = urlparse(base_url)
            src = f"{parsed.scheme}://{parsed.netloc}{src}"
        elif not src.startswith("http"):
            continue

        # 이미지 확장자 확인 또는 큰 이미지 필터
        ext = Path(urlparse(src).path).suffix.lower()
        if ext not in IMAGE_EXTS and "image" not in src.lower():
            continue

        # alt 텍스트 추출
        alt_match = re.search(r'alt=["\']([^"\']*)["\']', match.group(0))
        alt = alt_match.group(1) if alt_match else ""

        # 작은 이미지 필터 (아이콘, 로고 등)
        width_match = re.search(r'width=["\']?(\d+)', match.group(0))
        width = int(width_match.group(1)) if width_match else 0
        if width > 0 and width < 100:
            continue

        images.append({
            "url": src,
            "alt": alt,
            "width": width,
        })

    return images


def collect_images(query: str) -> Dict:
    """이미지 + 웹 크롤링 통합 수집."""
    logger.info("이미지 수집: %s", query)

    # 1. 이미지 검색
    image_results = search_images(query)
    logger.info("  이미지 검색: %d개", len(image_results))

    # 2. 웹 크롤링 이미지
    web_results = search_web_for_images(query)
    logger.info("  웹 크롤링: %d개", len(web_results))

    # 중복 URL 제거
    seen = set()
    all_images = []
    for img in image_results + web_results:
        url = img.get("url", "")
        if url and url not in seen:
            seen.add(url)
            all_images.append(img)

    return {
        "query": query,
        "total": len(all_images),
        "images": all_images,
    }


def save_to_vault(query: str, images: List[Dict]):
    """볼트에 이미지 참조 md 저장."""
    vault_dir = Path(os.environ.get("KAIROS_VAULT_DIR", ""))
    if not vault_dir.exists():
        logger.warning("볼트 미연결")
        return

    # 이미지 참조 파일 저장
    slug = re.sub(r'[^\w가-힣-]', '', query.replace(" ", "-"))[:50]
    img_dir = vault_dir / "03-analysis" / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    content = f"""---
title: "{query} 이미지 참조"
type: image-reference
query: "{query}"
created: "{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}"
total_images: {len(images)}
tags: [image-reference, crawled]
---

# {query} — 이미지 참조 ({len(images)}개)

"""
    for i, img in enumerate(images, 1):
        source = img.get("source_domain", img.get("domain", ""))
        alt = img.get("alt", img.get("title", ""))
        content += f"## {i}. {alt[:50] or '이미지'}\n"
        content += f"- URL: {img['url']}\n"
        content += f"- 출처: {source}\n"
        if img.get("source_page"):
            content += f"- 원본 페이지: {img['source_page']}\n"
        if img.get("width"):
            content += f"- 크기: {img.get('width', '?')}×{img.get('height', '?')}\n"
        content += "\n"

    out_path = img_dir / f"{slug}.md"
    out_path.write_text(content, encoding="utf-8")
    logger.info("볼트 저장: %s (%d개 이미지)", out_path.name, len(images))


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m auto_agent.scripts.image_crawler '검색어' [--save-vault]")
        sys.exit(1)

    query = args[0]
    save_vault = "--save-vault" in args

    result = collect_images(query)
    print(f"\n총 {result['total']}개 이미지 수집")

    for i, img in enumerate(result["images"][:10], 1):
        domain = img.get("source_domain", img.get("domain", ""))
        alt = img.get("alt", img.get("title", ""))[:40]
        print(f"  {i}. [{domain}] {alt}")
        print(f"     {img['url'][:80]}")

    if save_vault:
        save_to_vault(query, result["images"])


if __name__ == "__main__":
    main()
