"""fal.ai SeedVR2 비디오 업스케일 — fal-ai/seedvr/upscale/video.

로컬 mp4를 fal storage에 업로드 → subscribe(동기) → 결과 mp4 다운로드.
해상도는 target 모드(1080p/1440p/2160p)로 지정. 키는 fal_queue와 동일하게
FAL_API_KEY -> FAL_KEY 자동 매핑을 재사용한다.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path

from auto_agent.tools.fal_queue import FAL_AVAILABLE, _ensure_fal_key

ENDPOINT = "fal-ai/seedvr/upscale/video"

# CLI 옵션(1080/1440/2160) → fal target_resolution enum
RESOLUTIONS = {
    "1080": "1080p",
    "1440": "1440p",
    "2160": "2160p",
}
DEFAULT_RESOLUTION = "1080"


def build_arguments(video_url: str, resolution: str = DEFAULT_RESOLUTION) -> dict:
    """SeedVR 입력 페이로드 구성. resolution은 '1080'|'1440'|'2160'."""
    res = str(resolution).lower().rstrip("p")
    if res not in RESOLUTIONS:
        raise ValueError(f"지원하지 않는 해상도: {resolution} (가능: {', '.join(RESOLUTIONS)})")
    return {
        "video_url": video_url,
        "upscale_mode": "target",
        "target_resolution": RESOLUTIONS[res],
    }


def upscale_video(src_video, out_video=None, *, resolution: str = DEFAULT_RESOLUTION,
                  dry_run: bool = False) -> dict:
    """src를 SeedVR로 업스케일해 out(기본: src 옆 _up{res} 접미사)에 저장.

    반환: {status, path, resolution, request:{endpoint, arguments}} 또는 {status: failed, error}.
    dry_run=True면 업로드/과금 호출 없이 페이로드 검증까지만 수행.
    """
    src = Path(src_video)
    if not src.is_file():
        return {"status": "failed", "error": f"입력 없음: {src_video}"}
    try:
        args = build_arguments("<uploaded>", resolution)
    except ValueError as e:
        return {"status": "failed", "error": str(e)}

    res = str(resolution).lower().rstrip("p")
    out = Path(out_video) if out_video else src.with_name(f"{src.stem}_up{res}{src.suffix or '.mp4'}")

    if not FAL_AVAILABLE:
        return {"status": "failed", "error": "fal_client 미설치. pip install fal-client"}
    _ensure_fal_key()
    if not os.environ.get("FAL_KEY"):
        return {"status": "failed", "error": "FAL_API_KEY/FAL_KEY 미설정"}

    if dry_run:
        return {"status": "dry_run", "path": str(out), "resolution": RESOLUTIONS[res],
                "request": {"endpoint": ENDPOINT, "arguments": args}}

    import fal_client

    video_url = fal_client.upload_file(str(src))
    args["video_url"] = video_url
    try:
        raw = fal_client.subscribe(ENDPOINT, arguments=args)
    except Exception as e:
        return {"status": "failed", "error": f"SeedVR 호출 실패: {e}"}

    result_url = (raw or {}).get("video", {}).get("url")
    if not result_url:
        return {"status": "failed", "error": f"응답에 video.url 없음: {raw}"}

    out.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(result_url, out)
    return {"status": "completed", "path": str(out), "resolution": RESOLUTIONS[res],
            "request": {"endpoint": ENDPOINT, "arguments": args}}
