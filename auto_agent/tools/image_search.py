"""
이미지 검색 래퍼 - Wikimedia + Serper + Pixabay

auto_kairos_v2/src/tools/serper.py에서 이식.
Google 이미지 검색(Serper), Wikimedia Commons, Pixabay 통합 검색.
scene_specs.json 기반 검색+다운로드 지원.
"""
import argparse
import json
import os
import hashlib
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, asdict, field
from io import BytesIO
from urllib.parse import urlparse

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

MAX_IMAGE_SIZE = 1920

CC_SAFE_DOMAINS = {
    "wikipedia.org", "wikimedia.org", "flickr.com",
    "unsplash.com", "pixabay.com", "pexels.com",
}


def _extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return ""


def _guess_license(domain: str) -> str:
    for safe in CC_SAFE_DOMAINS:
        if safe in domain:
            return "likely_cc"
    return "unknown"


@dataclass
class SearchedImage:
    """검색된 이미지 정보"""
    title: str
    image_url: str
    thumbnail_url: str = ""
    source: str = ""
    source_page: str = ""
    source_domain: str = ""
    width: int = 0
    height: int = 0
    license: str = ""
    description: str = ""
    local_path: str = ""
    downloaded_at: str = ""


@dataclass
class ImageSearchResult:
    """이미지 검색 결과"""
    query: str
    source: str
    total_results: int = 0
    images: List[SearchedImage] = field(default_factory=list)
    searched_at: str = ""

    def __post_init__(self):
        if not self.searched_at:
            self.searched_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)


class WikimediaSearcher:
    """Wikimedia Commons API 검색기"""

    BASE_URL = "https://commons.wikimedia.org/w/api.php"

    def search(self, query: str, limit: int = 20, min_width: int = 500) -> ImageSearchResult:
        import re
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": "6",
            "gsrlimit": limit * 2,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 800,
        }
        try:
            headers = {"User-Agent": "AutoAgentV2/1.0"}
            response = requests.get(self.BASE_URL, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            images = []
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue
                imageinfo = page.get("imageinfo", [{}])[0]
                width = imageinfo.get("width", 0)
                if width < min_width:
                    continue
                extmeta = imageinfo.get("extmetadata", {})
                description = extmeta.get("ImageDescription", {}).get("value", "")
                license_info = extmeta.get("LicenseShortName", {}).get("value", "CC")
                if description:
                    description = re.sub(r'<[^>]+>', '', description)[:200]
                images.append(SearchedImage(
                    title=page.get("title", "").replace("File:", ""),
                    image_url=imageinfo.get("url", ""),
                    thumbnail_url=imageinfo.get("thumburl", ""),
                    source="wikimedia",
                    source_page=f"https://commons.wikimedia.org/wiki/{page.get('title', '')}",
                    width=width,
                    height=imageinfo.get("height", 0),
                    license=license_info,
                    description=description,
                ))
                if len(images) >= limit:
                    break
            return ImageSearchResult(query=query, source="wikimedia", total_results=len(images), images=images)
        except Exception as e:
            print(f"  Wikimedia 검색 실패: {e}")
            return ImageSearchResult(query=query, source="wikimedia")


class SerperSearcher:
    """Serper.dev Google 이미지 검색"""

    BASE_URL = "https://google.serper.dev/images"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY", "")
        if not self.api_key:
            raise ValueError("SERPER_API_KEY가 설정되지 않았습니다.")

    def search(self, query: str, limit: int = 20) -> ImageSearchResult:
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": min(limit, 100)}
        try:
            response = requests.post(self.BASE_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            images = []
            for item in data.get("images", []):
                page_url = item.get("link", "")
                domain = _extract_domain(page_url)
                images.append(SearchedImage(
                    title=item.get("title", ""),
                    image_url=item.get("imageUrl", ""),
                    thumbnail_url=item.get("thumbnailUrl", ""),
                    source="serper",
                    source_page=page_url,
                    source_domain=domain,
                    width=item.get("imageWidth", 0),
                    height=item.get("imageHeight", 0),
                    license=_guess_license(domain),
                ))
            return ImageSearchResult(query=query, source="serper", total_results=len(images), images=images)
        except Exception as e:
            print(f"  Serper 검색 실패: {e}")
            return ImageSearchResult(query=query, source="serper")


class PixabaySearcher:
    """Pixabay 스톡 이미지 검색"""

    BASE_URL = "https://pixabay.com/api/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PIXABAY_API_KEY", "")
        if not self.api_key:
            raise ValueError("PIXABAY_API_KEY가 설정되지 않았습니다.")

    def search(self, query: str, limit: int = 5) -> ImageSearchResult:
        params = {
            "key": self.api_key, "q": query, "per_page": min(limit, 200),
            "image_type": "photo", "orientation": "horizontal",
            "min_width": 960, "safesearch": "true", "lang": "en",
        }
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            images = []
            for hit in data.get("hits", []):
                images.append(SearchedImage(
                    title=hit.get("tags", ""),
                    image_url=hit.get("largeImageURL", hit.get("webformatURL", "")),
                    thumbnail_url=hit.get("previewURL", ""),
                    source="pixabay",
                    source_page=hit.get("pageURL", ""),
                    source_domain="pixabay.com",
                    width=hit.get("imageWidth", 0),
                    height=hit.get("imageHeight", 0),
                    license="pixabay_license",
                    description=hit.get("tags", ""),
                ))
            return ImageSearchResult(query=query, source="pixabay", total_results=len(images), images=images)
        except Exception as e:
            print(f"  Pixabay 검색 실패: {e}")
            return ImageSearchResult(query=query, source="pixabay")


class ImageSearcher:
    """통합 이미지 검색기"""

    def __init__(self, images_dir: Optional[Path] = None):
        self.wikimedia = WikimediaSearcher()
        self._serper = None
        self._pixabay = None
        self.images_dir = Path(images_dir) if images_dir else None
        if self.images_dir:
            self.images_dir.mkdir(parents=True, exist_ok=True)

    def search_wikimedia(self, query: str, limit: int = 10) -> ImageSearchResult:
        return self.wikimedia.search(query, limit)

    def search_serper(self, query: str, limit: int = 10) -> ImageSearchResult:
        if self._serper is None:
            self._serper = SerperSearcher()
        return self._serper.search(query, limit)

    def search_pixabay(self, query: str, limit: int = 5) -> ImageSearchResult:
        if self._pixabay is None:
            self._pixabay = PixabaySearcher()
        return self._pixabay.search(query, limit)

    def search_combined(self, query: str, wikimedia_limit: int = 5,
                        serper_limit: int = 5) -> List[SearchedImage]:
        images = []
        wiki_result = self.search_wikimedia(query, wikimedia_limit)
        images.extend(wiki_result.images)
        try:
            serper_result = self.search_serper(query, serper_limit)
            images.extend(serper_result.images)
        except ValueError:
            pass
        return images

    def download_image(self, img: SearchedImage, target_dir: Optional[Path] = None) -> Optional[str]:
        save_dir = target_dir or self.images_dir
        if not save_dir:
            return None
        save_dir.mkdir(parents=True, exist_ok=True)
        try:
            url_hash = hashlib.md5(img.image_url.encode()).hexdigest()[:12]
            ext = Path(urlparse(img.image_url).path).suffix.lower()
            if ext not in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                ext = ".jpg"
            local_path = save_dir / f"{url_hash}{ext}"
            if local_path.exists():
                img.local_path = str(local_path)
                return str(local_path)

            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(img.image_url, headers=headers, timeout=30)
            response.raise_for_status()

            if HAS_PIL:
                pil_img = Image.open(BytesIO(response.content))
                if pil_img.mode in ('RGBA', 'P'):
                    pil_img = pil_img.convert('RGB')
                w, h = pil_img.size
                if max(w, h) > MAX_IMAGE_SIZE:
                    pil_img.thumbnail((MAX_IMAGE_SIZE, MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
                if ext == ".png":
                    pil_img.save(local_path, "PNG", optimize=True)
                else:
                    local_path = local_path.with_suffix(".jpg")
                    pil_img.save(local_path, "JPEG", quality=90)
            else:
                with open(local_path, "wb") as f:
                    f.write(response.content)

            img.local_path = str(local_path)
            img.downloaded_at = datetime.now().isoformat()
            return str(local_path)
        except Exception as e:
            print(f"  다운로드 실패: {img.image_url[:50]}... ({e})")
            return None

    def search_and_download(self, query: str, limit: int = 5,
                            source: str = "wikimedia") -> List[SearchedImage]:
        if source == "wikimedia":
            result = self.search_wikimedia(query, limit)
        elif source == "serper":
            result = self.search_serper(query, limit)
        elif source == "pixabay":
            result = self.search_pixabay(query, limit)
        else:
            raise ValueError(f"Unknown source: {source}")

        downloaded = []
        for img in result.images:
            path = self.download_image(img)
            if path:
                downloaded.append(img)
        return downloaded

    def search_waterfall(self, query: str, limit: int = 3) -> List[SearchedImage]:
        """워터폴 폴백: wikimedia → serper → pixabay 순서로 시도"""
        # 1. Wikimedia (무료/CC)
        result = self.search_wikimedia(query, limit)
        downloaded = []
        for img in result.images:
            path = self.download_image(img)
            if path:
                downloaded.append(img)
        if downloaded:
            return downloaded

        # 2. Serper (Google Images)
        try:
            result = self.search_serper(query, limit)
            for img in result.images:
                path = self.download_image(img)
                if path:
                    downloaded.append(img)
            if downloaded:
                return downloaded
        except ValueError:
            pass

        # 3. Pixabay (스톡포토)
        try:
            result = self.search_pixabay(query, limit)
            for img in result.images:
                path = self.download_image(img)
                if path:
                    downloaded.append(img)
        except ValueError:
            pass

        return downloaded

    def search_wikipedia_person(self, name: str, output_dir: Path) -> Optional[str]:
        """Wikipedia pageimages API로 인물 이미지 검색 + 다운로드"""
        try:
            params = {
                "action": "query",
                "format": "json",
                "titles": name,
                "prop": "pageimages",
                "piprop": "original",
                "redirects": "1",
            }
            headers = {"User-Agent": "AutoAgentV2/1.0"}
            resp = requests.get("https://en.wikipedia.org/w/api.php",
                                params=params, headers=headers, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    continue
                original = page.get("original", {})
                img_url = original.get("source", "")
                if img_url:
                    img = SearchedImage(
                        title=f"Wikipedia: {name}",
                        image_url=img_url,
                        source="wikipedia",
                        source_domain="wikipedia.org",
                        width=original.get("width", 0),
                        height=original.get("height", 0),
                        license="CC",
                    )
                    path = self.download_image(img, target_dir=output_dir)
                    return path
        except Exception as e:
            print(f"  Wikipedia 인물 이미지 검색 실패: {e}")
        return None

    def search_for_scene_specs(self, scene_specs_path: Path, output_dir: Path) -> dict:
        """scene_specs.json의 imageAsset 기반 이미지 검색+다운로드

        source="wikimedia" → search_wikimedia → download
        source="search" → search_serper → download
        워터폴 폴백: wikimedia 실패 → serper → pixabay

        Returns:
            {scene_number: {local_path, license, source_url, source}}
        """
        with open(scene_specs_path, "r", encoding="utf-8") as f:
            specs = json.load(f)

        scenes = specs.get("scenes", [])
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_images_dir = self.images_dir
        self.images_dir = output_dir

        results = {}
        for scene in scenes:
            asset = scene.get("imageAsset")
            if not asset:
                continue
            source = asset.get("source", "")
            if source not in ("wikimedia", "search"):
                continue

            scene_num = scene.get("sceneNumber", 0)
            query = asset.get("query", asset.get("subject", ""))
            if not query:
                continue

            print(f"  [검색] scene_{scene_num:03d}: '{query}' (source={source})")

            if source == "wikimedia":
                downloaded = self.search_and_download(query, 3, "wikimedia")
                if not downloaded:
                    # 폴백: serper → pixabay
                    downloaded = self.search_waterfall(query, 3)
            else:
                downloaded = self.search_and_download(query, 3, "serper")
                if not downloaded:
                    downloaded = self.search_waterfall(query, 3)

            if downloaded:
                best = downloaded[0]
                results[scene_num] = {
                    "local_path": best.local_path,
                    "license": best.license,
                    "source_url": best.source_page or best.image_url,
                    "source": best.source,
                    "title": best.title,
                    "width": best.width,
                    "height": best.height,
                }
                print(f"    → {best.local_path}")
            else:
                print(f"    → 이미지 없음")

        self.images_dir = saved_images_dir
        return results


# ── CLI 진입점 ──

def _cli_main():
    """python3 -m src.tools.image_search 로 호출 가능한 CLI"""
    parser = argparse.ArgumentParser(description="이미지 검색/다운로드 CLI 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="단일 쿼리 검색 + 다운로드")
    p_search.add_argument("--query", required=True, help="검색 키워드")
    p_search.add_argument("--source", default="wikimedia",
                          choices=["serper", "wikimedia", "pixabay", "waterfall"],
                          help="검색 소스 (waterfall: wikimedia→serper→pixabay)")
    p_search.add_argument("--output", required=True, help="다운로드 디렉터리")
    p_search.add_argument("--count", type=int, default=5, help="결과 수")

    # wikipedia
    p_wiki = subparsers.add_parser("wikipedia", help="Wikipedia 인물 이미지 검색")
    p_wiki.add_argument("--name", required=True, help="인물 영문 이름")
    p_wiki.add_argument("--output", required=True, help="다운로드 디렉터리")

    # search-for-specs
    p_specs = subparsers.add_parser("search-for-specs",
                                     help="scene_specs.json 기반 자동 검색")
    p_specs.add_argument("--scene-specs", required=True, help="scene_specs.json 경로")
    p_specs.add_argument("--output", required=True, help="다운로드 디렉터리")

    args = parser.parse_args()

    if args.command == "search":
        searcher = ImageSearcher(images_dir=Path(args.output))
        if args.source == "waterfall":
            downloaded = searcher.search_waterfall(args.query, args.count)
        else:
            downloaded = searcher.search_and_download(args.query, args.count, args.source)
        result = [asdict(img) for img in downloaded]
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "wikipedia":
        searcher = ImageSearcher()
        path = searcher.search_wikipedia_person(args.name, Path(args.output))
        if path:
            print(json.dumps({"local_path": path}, ensure_ascii=False))
        else:
            print(json.dumps({"error": "이미지를 찾을 수 없습니다"}, ensure_ascii=False))

    elif args.command == "search-for-specs":
        searcher = ImageSearcher(images_dir=Path(args.output))
        results = searcher.search_for_scene_specs(
            Path(args.scene_specs), Path(args.output))
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _cli_main()
