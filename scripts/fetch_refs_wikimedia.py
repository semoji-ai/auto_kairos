#!/usr/bin/env python3
"""위키미디어 레퍼런스를 API 썸네일로 받는다 — 원본은 막혀 있다.

`upload.wikimedia.org`의 **원본** 파일은 스크립트 연속 요청에 IP 단위 429를 준다
(`retry-after: 600`). UA를 바꿔도 같고, 재시도가 차단을 연장한다.

그런데 **썸네일 경로는 막히지 않는다.** 다만 경로를 손으로 지어내면 400이 난다
(해시 디렉터리와 파일명 규칙이 있다). MediaWiki API 의 `imageinfo` 에
`iiurlwidth` 를 주면 정확한 썸네일 URL을 돌려준다. 이 길이 정상 경로다.

API 는 한 번에 파일 50개까지 물어볼 수 있어 요청 수도 크게 준다.

    python3 scripts/fetch_refs_wikimedia.py <project_dir> [-o _imggen/refs] [--width 1280]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

UA = "AutoKairosAssetFetcher/1.0 (documentary research; contact via project)"
API = "https://commons.wikimedia.org/w/api.php"
MIN_BYTES = 8000
SIGS = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF8", b"RIFF")
BATCH = 40


def wiki_title(url: str) -> str | None:
    """레퍼런스 URL에서 Commons 파일명을 뽑는다."""
    u = urllib.parse.unquote(url or "")
    for pat in (r"Special:Redirect/file/([^?#]+)",
                r"/wiki/File:([^?#]+)",
                r"upload\.wikimedia\.org/wikipedia/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/?#]+)"):
        m = re.search(pat, u)
        if m:
            return m.group(1)
    return None


def norm(t: str) -> str:
    """MediaWiki 는 밑줄을 공백으로 정규화한다 — 조회 키를 같은 꼴로."""
    return urllib.parse.unquote(str(t or "")).replace("_", " ").strip()


def api_thumbs(titles: list[str], width: int) -> dict[str, str]:
    q = {"action": "query", "format": "json", "prop": "imageinfo",
         "iiprop": "url", "iiurlwidth": str(width),
         "titles": "|".join(f"File:{t}" for t in titles)}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q),
                                 headers={"User-Agent": UA})
    out: dict[str, str] = {}
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            data = json.load(r)
    except Exception as e:
        print(f"    [api] {type(e).__name__} {str(e)[:60]}")
        return out
    for p in (data.get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        url = ii.get("thumburl") or ii.get("url")
        title = norm((p.get("title") or "").removeprefix("File:"))
        if url and title:
            out[title] = url
    return out


def grab(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            b = r.read()
    except Exception:
        return None
    if len(b) < MIN_BYTES or not any(b[:16].startswith(s) for s in SIGS):
        return None
    return b


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("_imggen/refs"))
    ap.add_argument("--width", type=int, default=1280)
    a = ap.parse_args()

    p = a.project / "scene_specs.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    a.out.mkdir(parents=True, exist_ok=True)

    todo = []
    for sc in data.get("scenes", []):
        for i, r in enumerate((sc.get("imageAsset") or {}).get("refAssets") or [], 1):
            if r.get("local"):
                continue
            t = wiki_title(r.get("url", "")) or wiki_title(r.get("page", ""))
            if t:
                todo.append((sc["sceneNumber"], i, r, t))
    print(f"  위키미디어 레퍼런스 {len(todo)}건")

    titles = sorted({t for *_, t in todo})
    thumb: dict[str, str] = {}
    for k in range(0, len(titles), BATCH):
        thumb.update(api_thumbs(titles[k:k + BATCH], a.width))
        time.sleep(0.5)
    print(f"  API가 돌려준 썸네일 URL {len(thumb)}건 / 파일 {len(titles)}종")

    cache: dict[str, str] = {}
    ok = reuse = fail = 0
    for n, i, r, t in todo:
        url = thumb.get(norm(t))
        if not url:
            fail += 1
            continue
        if url in cache:
            r["local"] = cache[url]
            reuse += 1
            continue
        blob = grab(url)
        time.sleep(0.4)
        if not blob:
            fail += 1
            continue
        ext = ".png" if blob[:8].startswith(b"\x89PNG") else ".jpg"
        f = a.out / f"scene_{n:03d}_ref{i}{ext}"
        f.write_bytes(blob)
        r["local"] = str(f)
        r["thumb_url"] = url
        cache[url] = str(f)
        ok += 1
        if ok % 20 == 0:
            print(f"    … {ok}건", flush=True)

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  받음 {ok} · 재사용 {reuse} · 실패 {fail} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
