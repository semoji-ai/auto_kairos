"""이미지 검색(serper/pixabay) + 다운로드(무삭제 버전). HTTP는 urllib(stdlib)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

from backend import env
from backend.imagegen import versioned_path

SERPER_URL = "https://google.serper.dev/images"
PIXABAY_URL = "https://pixabay.com/api/"


def _post_json(url, payload, headers, timeout=20):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_json(url, timeout=20):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _download(url, dest: Path, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        dest.write_bytes(r.read())


def search_images(query: str, engine: str = "serper", count: int = 12) -> dict:
    """{images:[{title,url,thumb,source}]} 또는 {error, images:[]}."""
    eng = (engine or "serper").lower()
    if eng == "serper":
        key = env.get_key("SERPER_API_KEY")
        if not key:
            return {"error": "SERPER_API_KEY 없음(auto_kairos .env)", "images": []}
        data = _post_json(SERPER_URL, {"q": query, "num": count},
                          {"X-API-KEY": key, "Content-Type": "application/json"})
        imgs = [{"title": i.get("title", ""), "url": i.get("imageUrl", ""),
                 "thumb": i.get("thumbnailUrl", i.get("imageUrl", "")), "source": "serper"}
                for i in data.get("images", [])[:count] if i.get("imageUrl")]
        return {"images": imgs}
    if eng == "pixabay":
        key = env.get_key("PIXABAY_API_KEY")
        if not key:
            return {"error": "PIXABAY_API_KEY 없음(auto_kairos .env)", "images": []}
        qs = urllib.parse.urlencode({"key": key, "q": query, "per_page": count,
                                     "image_type": "photo", "safesearch": "true"})
        data = _get_json(f"{PIXABAY_URL}?{qs}")
        imgs = [{"title": h.get("tags", ""),
                 "url": h.get("largeImageURL", h.get("webformatURL", "")),
                 "thumb": h.get("previewURL", h.get("webformatURL", "")), "source": "pixabay"}
                for h in data.get("hits", [])[:count] if h.get("webformatURL") or h.get("largeImageURL")]
        return {"images": imgs}
    return {"error": f"unknown engine: {engine}", "images": []}


def save_image(proj_dir: Path, url: str, name: str, subdir: str = "images/search") -> dict:
    """검색 결과 1장 다운로드 → proj/subdir/name (무삭제 버전)."""
    out_dir = proj_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = versioned_path(out_dir, Path(name).name)
    try:
        _download(url, dest)
    except Exception as e:  # 네트워크/URL 오류
        return {"status": "failed", "error": str(e)}
    return {"status": "completed", "path": str(dest),
            "rel": dest.relative_to(proj_dir).as_posix()}
