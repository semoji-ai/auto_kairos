"""yt-dlp 기반 영상 검색·다운로드·클립 추출 어댑터 (L3 — v3 의존 0 *기본 기능*).

vendored: `_vendor/video_search_v3.py`.
- 검색·다운로드·클립 구간 추출: v3 의존 X
- Gemini 분석 / DB 프로젝트 조회: v3 부재 시 NotImplementedError (advanced 기능, 옵션)

이식된 규칙:
- yt-dlp로 후보 검색 (best quality 한도 내)
- ffmpeg로 클립 구간 추출
- 캐시 디렉토리 KAIROS_VAULT_DIR/cache/video 또는 ~/.auto_kairos_v4/cache/video
- editorial / fair_use 라이선스 가정 — 사용자 승인 필수
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ._vendor.video_search_v3 import search as _v3_search


def is_available() -> bool:
    return shutil.which("yt-dlp") is not None and shutil.which("ffmpeg") is not None


def search(
    query: str,
    *,
    limit: int = 5,
    duration_max_s: int | None = None,
) -> list[dict[str, Any]]:
    """yt-dlp 기반 영상 후보 검색."""
    try:
        results = _v3_search(query, limit=limit)
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for r in results or []:
        if duration_max_s and r.get("duration_s", 0) > duration_max_s * 4:
            continue
        out.append({
            "source_url": r.get("url") or r.get("webpage_url"),
            "title": r.get("title"),
            "duration_s": r.get("duration_s") or r.get("duration"),
            "uploader": r.get("uploader") or r.get("channel"),
            "view_count": r.get("view_count"),
            "thumbnail": r.get("thumbnail"),
            "license_hint": "editorial_or_fair_use_assumed",
            "license_terms": "yt-dlp 결과. 보도/뉴스는 fair_use 가정, 실 사용 시 사용자 승인 필수",
            "raw": r,
        })
    return out


def download_clip(
    source_url: str,
    out_path: Path,
    *,
    start_s: float | None = None,
    end_s: float | None = None,
    timeout: int = 300,
) -> Path:
    """yt-dlp로 다운로드 후 ffmpeg로 클립 구간 추출."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if start_s is not None and end_s is not None:
        cmd = [
            "yt-dlp", "--quiet",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--external-downloader", "ffmpeg",
            "--external-downloader-args", f"ffmpeg_i:-ss {start_s} -to {end_s}",
            "-o", str(out_path),
            source_url,
        ]
    else:
        cmd = [
            "yt-dlp", "--quiet",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", str(out_path),
            source_url,
        ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    if not out_path.exists():
        raise FileNotFoundError(f"yt-dlp did not produce {out_path}")
    return out_path


def cache_root() -> Path:
    """비디오 다운로드 캐시 위치."""
    vault = os.environ.get("KAIROS_VAULT_DIR")
    if vault:
        return Path(vault) / "cache" / "video"
    return Path.home() / ".auto_kairos_v4" / "cache" / "video"
