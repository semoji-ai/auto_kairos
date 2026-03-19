"""Serper.dev Google 이미지 검색."""
import os
import requests


def search_images(query: str, count: int = 12) -> list:
    """Google 이미지 검색 (Serper API).

    Returns:
        [{"title", "imageUrl", "thumbnail_url", "source", "link"}]
    """
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        return []

    try:
        resp = requests.post(
            "https://google.serper.dev/images",
            json={"q": query, "num": count},
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for img in data.get("images", [])[:count]:
            results.append({
                "title": img.get("title", ""),
                "imageUrl": img.get("imageUrl", ""),
                "thumbnail_url": img.get("thumbnailUrl", img.get("imageUrl", "")),
                "original_url": img.get("imageUrl", ""),
                "source": img.get("source", ""),
                "link": img.get("link", ""),
                "license": "Google Images",
            })
        return results
    except Exception as e:
        print(f"[serper] 검색 실패: {e}")
        return []
