"""이미지 검색 어댑터 (L3 — v3 의존 0).

vendored: `_vendor/image_search_v3.py`. v3 폴더 없는 머신에서도 동작.

이식된 규칙:
- Wikimedia 우선(public_domain/CC), Pixabay(royalty_free), Serper(폴백, 비용 발생)
- min_width 기본 500px
- 다운로드 시 referrer/User-Agent 보전
- waterfall 검색
- 환경 변수 SERPER_API_KEY / PIXABAY_API_KEY
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from ._vendor.image_search_v3 import ImageSearcher, SearchedImage


def is_available() -> bool:
    return True  # vendored — 항상 가용


def search_combined(
    query: str,
    *,
    wikimedia_limit: int = 5,
    pixabay_limit: int = 3,
    serper_limit: int = 0,
) -> list[dict[str, Any]]:
    """다중 소스 검색 통합. Serper는 explicitly limit>0 일 때만 호출."""
    searcher = ImageSearcher()
    candidates: list[dict[str, Any]] = []

    try:
        wm = searcher.search_wikimedia(query, limit=wikimedia_limit)
        for img in wm.images:
            candidates.append({
                "source_name": "Wikimedia Commons",
                "source_url": img.image_url,
                "title": img.title,
                "license_type": "public_domain_or_cc",
                "license_cost": "free",
                "license_terms": "Wikimedia Commons. 라이선스별 attribution 확인",
                "attribution_required": True,
                "thumbnail": getattr(img, "thumbnail_url", None),
                "width": getattr(img, "width", None),
                "height": getattr(img, "height", None),
            })
    except Exception as e:
        candidates.append({"source_name": "Wikimedia Commons", "error": str(e)})

    if pixabay_limit > 0:
        try:
            px = searcher.search_pixabay(query, limit=pixabay_limit)
            for img in px.images:
                candidates.append({
                    "source_name": "Pixabay",
                    "source_url": img.image_url,
                    "title": img.title,
                    "license_type": "royalty_free",
                    "license_cost": "free",
                    "license_terms": "Pixabay Content License",
                    "attribution_required": False,
                    "thumbnail": getattr(img, "thumbnail_url", None),
                })
        except Exception as e:
            candidates.append({"source_name": "Pixabay", "error": str(e)})

    if serper_limit > 0:
        try:
            sp = searcher.search_serper(query, limit=serper_limit)
            for img in sp.images:
                candidates.append({
                    "source_name": "Serper(Google Images)",
                    "source_url": img.image_url,
                    "title": img.title,
                    "license_type": "unknown",
                    "license_cost": "unknown",
                    "license_terms": "Google 이미지 검색 결과 — 원본 사이트 라이선스 확인 필수",
                    "attribution_required": True,
                    "thumbnail": getattr(img, "thumbnail_url", None),
                })
        except Exception as e:
            candidates.append({"source_name": "Serper", "error": str(e)})

    return [c for c in candidates if "error" not in c]


def download(image_url: str, target_dir: Path, *, filename: str | None = None) -> Path | None:
    """이미지 다운로드. vendored 다운로더 사용(referrer/UA 보전)."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    searcher = ImageSearcher()
    img = SearchedImage(
        title=filename or Path(image_url).name,
        image_url=image_url,
        thumbnail_url=image_url,
        width=0, height=0,
        source="external",
        license_info=None,
    )
    path_str = searcher.download_image(img, target_dir=target_dir)
    return Path(path_str) if path_str else None
