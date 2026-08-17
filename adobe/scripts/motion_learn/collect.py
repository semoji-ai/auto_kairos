"""큐레이션 URL → yt-dlp 다운 + 메타. 무삭제·멱등(slug 기준)."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from scripts.motion_learn import state


def slug_for(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _run_ytdlp(url: str, out: Path) -> None:
    subprocess.run(
        ["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]",
         "--merge-output-format", "mp4", "-o", str(out), url],
        check=True, capture_output=True, timeout=600)


def _probe_meta(path: Path) -> dict:
    import shutil
    if not shutil.which("ffprobe"):
        return {}
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height:format=duration:format_tags=title",
         "-of", "json", str(path)], capture_output=True, text=True, timeout=60)
    try:
        j = json.loads(r.stdout)
        st = (j.get("streams") or [{}])[0]
        fmt = j.get("format") or {}
        title = (fmt.get("tags") or {}).get("title", "")
        return {"width": st.get("width"), "height": st.get("height"),
                "duration": float(fmt.get("duration", 0) or 0), "title": title}
    except (json.JSONDecodeError, ValueError):
        return {}


def collect(urls: list[str], refs_dir: Path) -> list[dict]:
    """각 URL → refs/{slug}.mp4 + refs/{slug}/state.json. 반환 [{slug,path,...}]."""
    refs_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for url in urls:
        slug = slug_for(url)
        mp4 = refs_dir / (slug + ".mp4")
        ref_dir = refs_dir / slug
        if not mp4.exists():
            _run_ytdlp(url, mp4)
        meta = _probe_meta(mp4)
        meta["url"] = url
        state.set_stage(ref_dir, "collected", meta)
        out.append({"slug": slug, "path": str(mp4), **meta})
    return out
