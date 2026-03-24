"""
이미지 검색 래퍼 - Wikimedia + Serper + Pixabay

auto_kairos_v2/src/tools/serper.py에서 이식.
Google 이미지 검색(Serper), Wikimedia Commons, Pixabay 통합 검색.
scene_specs.json 기반 검색+다운로드 지원.
"""
import argparse
import json
import os
import sys
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

import re as _re

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

MAX_IMAGE_SIZE = 1920

CC_SAFE_DOMAINS = {
    "wikipedia.org", "wikimedia.org", "flickr.com",
    "unsplash.com", "pixabay.com", "pexels.com",
}

# 워터마크 흔한 도메인/소스
WATERMARK_DOMAINS = {
    "shutterstock.com", "gettyimages.com", "istockphoto.com",
    "dreamstime.com", "123rf.com", "depositphotos.com",
    "adobestock.com", "alamy.com", "stock.adobe.com",
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


# ── 이미지 품질 스코어링 ──

def _score_resolution(width: int, height: int) -> float:
    """해상도 점수 (0~30). 1920px 이상이면 만점."""
    pixels = max(width, height)
    if pixels >= 1920:
        return 30.0
    if pixels >= 1280:
        return 25.0
    if pixels >= 960:
        return 20.0
    if pixels >= 640:
        return 12.0
    if pixels >= 400:
        return 5.0
    return 0.0


def _score_aspect_ratio(width: int, height: int, preferred: str = "16:9") -> float:
    """종횡비 점수 (0~10). 선호 비율에 가까울수록 높은 점수."""
    if width == 0 or height == 0:
        return 0.0
    ratio = width / height
    targets = {"16:9": 16/9, "1:1": 1.0, "4:3": 4/3, "3:2": 3/2}
    target = targets.get(preferred, 16/9)
    diff = abs(ratio - target) / target
    if diff < 0.05:
        return 10.0
    if diff < 0.15:
        return 7.0
    if diff < 0.3:
        return 4.0
    return 2.0


def _score_license(license_str: str, source: str) -> float:
    """라이선스 점수 (0~20). CC/공개 도메인이면 높은 점수."""
    license_lower = license_str.lower()
    if any(tag in license_lower for tag in ("cc0", "public domain", "pd")):
        return 20.0
    if any(tag in license_lower for tag in ("cc", "likely_cc", "pixabay")):
        return 15.0
    if source in ("wikimedia", "pixabay", "wikipedia"):
        return 12.0
    return 3.0


def _score_relevance(query: str, title: str, description: str) -> float:
    """관련도 점수 (0~25). 쿼리 키워드가 제목/설명에 포함될수록 높은 점수."""
    query_words = set(query.lower().split())
    if not query_words:
        return 10.0  # 기본점
    text = f"{title} {description}".lower()
    matched = sum(1 for w in query_words if w in text)
    match_ratio = matched / len(query_words)
    return round(match_ratio * 25.0, 1)


def _score_source(source: str, source_domain: str) -> float:
    """소스 신뢰도 점수 (0~15). 워터마크 도메인이면 감점."""
    # 워터마크 유명 스톡사이트 -> 감점
    for wm_domain in WATERMARK_DOMAINS:
        if wm_domain in source_domain:
            return -20.0  # 페널티
    if source in ("wikimedia", "wikipedia"):
        return 15.0
    if source == "pixabay":
        return 13.0
    if source == "serper":
        # CC 안전 도메인이면 가산
        for safe in CC_SAFE_DOMAINS:
            if safe in source_domain:
                return 12.0
        return 5.0
    return 3.0


def score_image(img: SearchedImage, query: str, preferred_aspect: str = "16:9") -> float:
    """이미지 종합 스코어 (0~100). 높을수록 좋음."""
    s = 0.0
    s += _score_resolution(img.width, img.height)
    s += _score_aspect_ratio(img.width, img.height, preferred_aspect)
    s += _score_license(img.license, img.source)
    s += _score_relevance(query, img.title, img.description)
    s += _score_source(img.source, img.source_domain)
    return round(s, 1)


def rank_images(images: List[SearchedImage], query: str,
                preferred_aspect: str = "16:9") -> List[SearchedImage]:
    """이미지 목록을 스코어 기준으로 정렬 (높은 순)."""
    scored = [(img, score_image(img, query, preferred_aspect)) for img in images]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [img for img, _s in scored]


# ── 워터마크 감지 ──

def detect_watermark(image_path: str) -> bool:
    """다운로드된 이미지에서 워터마크 흔적을 감지.

    휴리스틱 기반:
    1. 대각선 반복 패턴 감지 (스톡 워터마크 특유)
    2. 중앙/하단 영역의 비정상적 반투명 오버레이 감지
    3. 이미지 전체의 고주파 텍스트 패턴 감지

    Returns:
        True면 워터마크 의심, False면 정상
    """
    if not HAS_PIL or not HAS_NUMPY:
        return False

    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size

        # 너무 작은 이미지는 검사 스킵
        if w < 200 or h < 200:
            return False

        arr = np.array(img, dtype=np.float32)

        # 1) 중앙 영역 반투명 오버레이 감지
        # 워터마크가 있으면 중앙부 밝기 분산이 비정상적으로 높음
        cx, cy = w // 2, h // 2
        margin_x, margin_y = w // 6, h // 6
        center_crop = arr[cy - margin_y:cy + margin_y, cx - margin_x:cx + margin_x]

        if center_crop.size > 0:
            # 그레이스케일 변환
            gray_center = center_crop.mean(axis=2)

            # 라플라시안(간이) -- 고주파 에지 밀도 측정
            # 워터마크 텍스트는 에지가 많고 반복적
            dx = np.diff(gray_center, axis=1)
            dy = np.diff(gray_center, axis=0)
            edge_density = (np.abs(dx).mean() + np.abs(dy).mean()) / 2

            # 에지 밀도가 높고 대비가 낮으면 워터마크 의심
            # (실제 내용물은 대비가 높고 에지가 자연스러움)
            contrast = gray_center.std()

            # 워터마크: 에지 밀도 높음 + 대비 중간 (반투명 오버레이)
            if edge_density > 15.0 and 10.0 < contrast < 40.0:
                return True

        # 2) 하단 1/6 영역 워터마크 텍스트 바 감지
        bottom_strip = arr[int(h * 0.83):, :]
        if bottom_strip.size > 0:
            gray_bottom = bottom_strip.mean(axis=2)
            bottom_std = gray_bottom.std()
            # 하단이 균일한 색상(바) + 약간의 텍스트 에지
            if bottom_std < 20.0:
                # 균일한 바 영역 -- 에지가 있는지 확인
                dx_b = np.abs(np.diff(gray_bottom, axis=1))
                if dx_b.mean() > 3.0:
                    return True

        # 3) 대각선 패턴 감지 (타일형 워터마크)
        # 이미지를 4x4 그리드로 나눠서 각 블록의 평균 밝기 패턴 비교
        block_h, block_w = h // 4, w // 4
        if block_h > 20 and block_w > 20:
            gray_full = arr.mean(axis=2)
            block_means = []
            for bi in range(4):
                row = []
                for bj in range(4):
                    block = gray_full[bi*block_h:(bi+1)*block_h,
                                      bj*block_w:(bj+1)*block_w]
                    row.append(block.mean())
                block_means.append(row)

            # 대각선 패턴: (0,0)≈(1,1)≈(2,2)≈(3,3) 이면서
            # (0,1)≈(1,2)≈(2,3) 이면 타일 반복 의심
            diag = [block_means[i][i] for i in range(4)]
            diag_std = np.std(diag)
            off_diag = [block_means[i][(i+1)%4] for i in range(4)]
            off_diag_std = np.std(off_diag)

            # 대각선과 오프다각 모두 균일하면 타일 워터마크
            if diag_std < 3.0 and off_diag_std < 3.0:
                # 전체 분산은 있어야 함 (균일색 이미지가 아닌 경우)
                full_std = gray_full.std()
                if full_std > 15.0:
                    return True

        return False
    except Exception:
        return False


def filter_watermarked(images: List[SearchedImage]) -> List[SearchedImage]:
    """다운로드된 이미지 목록에서 워터마크 감지된 것을 제거."""
    filtered = []
    for img in images:
        if not img.local_path:
            filtered.append(img)
            continue
        # Wikimedia Commons는 자체 라이선스 데이터 제공 -- 워터마크 없음, 감지 스킵
        if img.source == "wikimedia":
            filtered.append(img)
            continue
        if detect_watermark(img.local_path):
            print(f"    [WM] 워터마크 감지 -- 제외: {Path(img.local_path).name}", file=sys.stderr)
            # 워터마크 이미지 파일 삭제
            try:
                Path(img.local_path).unlink(missing_ok=True)
            except Exception:
                pass
        else:
            filtered.append(img)
    return filtered


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
            print(f"  Wikimedia 검색 실패: {e}", file=sys.stderr)
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
            print(f"  Serper 검색 실패: {e}", file=sys.stderr)
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
            print(f"  Pixabay 검색 실패: {e}", file=sys.stderr)
            return ImageSearchResult(query=query, source="pixabay")


class ImageSearcher:
    """통합 이미지 검색기"""

    def __init__(self, images_dir: Optional[Path] = None):
        self.wikimedia = WikimediaSearcher()
        self._serper = None
        self._pixabay = None
        self.images_dir = Path(images_dir) if images_dir else None
        self.last_all_ranked: List[SearchedImage] = []
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

            headers = {"User-Agent": "KairosAgent/3.1 (video-production; educational)"}
            # 위키미디어 rate limit 대응: 재시도 + 딜레이
            for attempt in range(3):
                response = requests.get(img.image_url, headers=headers, timeout=30)
                if response.status_code == 429:
                    import time as _time
                    _time.sleep(2 * (attempt + 1))
                    continue
                break
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
            print(f"  다운로드 실패: {img.image_url[:50]}... ({e})", file=sys.stderr)
            return None

    def search_and_download(self, query: str, limit: int = 5,
                            source: str = "wikimedia",
                            preferred_aspect: str = "16:9") -> List[SearchedImage]:
        """검색 -> 스코어링 -> 상위 N개 다운로드 -> 워터마크 필터링.

        전체 검색 결과(메타데이터)는 self.last_all_ranked에 보관된다.
        다운로드하지 않은 후보도 thumbnail_url로 접근 가능.
        """
        # 더 많이 검색해서 랭킹할 여지를 확보
        fetch_limit = max(limit * 3, 10)

        if source == "wikimedia":
            result = self.search_wikimedia(query, fetch_limit)
        elif source == "serper":
            result = self.search_serper(query, fetch_limit)
        elif source == "pixabay":
            result = self.search_pixabay(query, fetch_limit)
        else:
            raise ValueError(f"Unknown source: {source}")

        # 1) 스톡 워터마크 도메인 사전 필터링
        candidates = [
            img for img in result.images
            if not any(wd in img.source_domain for wd in WATERMARK_DOMAINS)
        ]
        if not candidates:
            candidates = result.images  # 폴백

        # 2) 메타데이터 기반 스코어링 + 정렬
        ranked = rank_images(candidates, query, preferred_aspect)

        # 전체 랭킹 결과 보관 (image_candidates.json 생성용)
        self.last_all_ranked = ranked

        # 3) 상위 N개만 다운로드
        downloaded = []
        for img in ranked:
            if len(downloaded) >= limit:
                break
            path = self.download_image(img)
            if path:
                downloaded.append(img)

        # 4) 워터마크 감지 필터링
        downloaded = filter_watermarked(downloaded)

        return downloaded

    def search_waterfall(self, query: str, limit: int = 3,
                         preferred_aspect: str = "16:9") -> List[SearchedImage]:
        """워터폴 폴백: wikimedia -> serper -> pixabay.
        모든 소스에서 후보를 모아 통합 랭킹."""
        all_candidates: List[SearchedImage] = []

        # 1. Wikimedia (무료/CC)
        result = self.search_wikimedia(query, limit * 3)
        all_candidates.extend(result.images)

        # 2. Serper (Google Images)
        try:
            result = self.search_serper(query, limit * 3)
            all_candidates.extend(result.images)
        except ValueError:
            pass

        # 3. Pixabay (스톡포토)
        try:
            result = self.search_pixabay(query, limit * 2)
            all_candidates.extend(result.images)
        except ValueError:
            pass

        if not all_candidates:
            return []

        # 스톡 워터마크 도메인 사전 필터링
        filtered = [
            img for img in all_candidates
            if not any(wd in img.source_domain for wd in WATERMARK_DOMAINS)
        ]
        if not filtered:
            filtered = all_candidates

        # 통합 랭킹
        ranked = rank_images(filtered, query, preferred_aspect)

        # 전체 랭킹 결과 보관
        self.last_all_ranked = ranked

        # 상위 N개 다운로드
        downloaded = []
        for img in ranked:
            if len(downloaded) >= limit:
                break
            path = self.download_image(img)
            if path:
                downloaded.append(img)

        # 워터마크 감지 필터링
        downloaded = filter_watermarked(downloaded)

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
            print(f"  Wikipedia 인물 이미지 검색 실패: {e}", file=sys.stderr)
        return None

    def search_for_scene_specs(self, scene_specs_path: Path, output_dir: Path) -> dict:
        """scene_specs.json의 imageAsset 기반 이미지 검색+다운로드

        source="wikimedia" -> search_wikimedia -> download
        source="search" -> search_serper -> download
        워터폴 폴백: wikimedia 실패 -> serper -> pixabay

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

            # placement에 따른 선호 종횡비 결정
            placement = asset.get("placement", "background")
            preferred = "1:1" if placement in ("left", "right") else "16:9"

            print(f"  [검색] scene_{scene_num:03d}: '{query}' (source={source}, {preferred})", file=sys.stderr)

            if source == "wikimedia":
                downloaded = self.search_and_download(query, 3, "wikimedia", preferred)
                if not downloaded:
                    downloaded = self.search_waterfall(query, 3, preferred)
            else:
                try:
                    downloaded = self.search_and_download(query, 3, "serper", preferred)
                except ValueError:
                    downloaded = []
                if not downloaded:
                    downloaded = self.search_waterfall(query, 3, preferred)

            if downloaded:
                best = downloaded[0]
                best_score = score_image(best, query, preferred)
                results[scene_num] = {
                    "local_path": best.local_path,
                    "license": best.license,
                    "source_url": best.source_page or best.image_url,
                    "source": best.source,
                    "title": best.title,
                    "width": best.width,
                    "height": best.height,
                    "score": best_score,
                }
                print(f"    -> {best.local_path} (score={best_score}, {best.width}x{best.height})", file=sys.stderr)
            else:
                print(f"    -> 이미지 없음", file=sys.stderr)

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
                          help="검색 소스 (waterfall: wikimedia->serper->pixabay)")
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
