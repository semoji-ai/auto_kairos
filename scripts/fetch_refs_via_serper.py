#!/usr/bin/env python3
"""막힌 레퍼런스를 Serper 이미지 검색으로 우회해 받는다.

위키미디어는 스크립트의 연속 요청에 IP 단위 429(`retry-after: 600`)를 건다.
UA를 바꿔도 소용없고, 재시도가 오히려 차단을 연장한다. 조사에서 URL은 확보했는데
파일을 못 받아 `refAssets[].local`이 비면 `gen_scenes.py`가 첨부할 것이 없다.

Serper는 구글 이미지 색인을 쓰므로 원본 서버를 직접 두드리지 않고, 같은 자료의
다른 호스트 사본을 찾아 준다. 검색어는 조사가 남긴 `desc`/`subject`/`era` 로 만든다.

**받은 것이 진짜 그림인지 확인한다.** 검색 결과에는 썸네일·아이콘·로고가 섞인다.

    python3 scripts/fetch_refs_via_serper.py <project_dir> [-o _imggen/refs] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "\
     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MIN_BYTES = 8000
SIGS = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF8", b"RIFF")
# 원본이 막힌 곳 — 여기 호스트는 후보에서 뺀다(같은 429를 다시 만난다)
BLOCKED_HOSTS = ("upload.wikimedia.org", "commons.wikimedia.org")


def serper_images(query: str, key: str, count: int = 10) -> list[dict]:
    body = json.dumps({"q": query, "num": count}).encode()
    req = urllib.request.Request(
        "https://google.serper.dev/images", data=body,
        headers={"X-API-KEY": key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r).get("images", [])
    except Exception as e:
        print(f"    [serper] {type(e).__name__} {str(e)[:50]}")
        return []


def grab(url: str) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                   "Accept": "image/*,*/*;q=0.8"})
        with urllib.request.urlopen(req, timeout=35) as r:
            b = r.read()
    except Exception:
        return None
    if len(b) < MIN_BYTES or not any(b[:16].startswith(s) for s in SIGS):
        return None
    return b


def build_query(r: dict) -> str:
    """조사가 남긴 서술로 검색어를 만든다. 시기가 있으면 함께 건다."""
    for k in ("subject", "desc"):
        v = (r.get(k) or "").strip()
        if v:
            base = v[:70]
            break
    else:
        return ""
    era = (r.get("era") or "").strip()
    yr = "".join(ch for ch in era if ch.isdigit())[:4]
    return f"{base} {yr}".strip() if yr else base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("_imggen/refs"))
    ap.add_argument("--limit", type=int, default=0, help="처리할 최대 건수(0=전부)")
    a = ap.parse_args()

    key = os.environ.get("SERPER_API_KEY")
    if not key:
        for ln in Path(".env").read_text(encoding="utf-8").splitlines():
            if ln.startswith("SERPER_API_KEY="):
                key = ln.split("=", 1)[1].strip()
                break
    if not key:
        print("ERROR: SERPER_API_KEY 없음")
        return 1

    p = a.project / "scene_specs.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    a.out.mkdir(parents=True, exist_ok=True)

    todo = []
    for sc in data.get("scenes", []):
        for i, r in enumerate((sc.get("imageAsset") or {}).get("refAssets") or [], 1):
            if not r.get("local"):
                todo.append((sc["sceneNumber"], i, r))
    if a.limit:
        todo = todo[:a.limit]
    print(f"  로컬 없는 레퍼런스 {len(todo)}건")

    qcache: dict[str, str] = {}     # 검색어 → 이미 받은 로컬 경로
    ok = reuse = fail = 0
    for n, i, r in todo:
        q = build_query(r)
        if not q:
            fail += 1
            continue
        if q in qcache:
            r["local"] = qcache[q]
            reuse += 1
            continue
        got = None
        for cand in serper_images(q, key):
            u = cand.get("imageUrl") or ""
            if not u or any(h in u for h in BLOCKED_HOSTS):
                continue
            blob = grab(u)
            if blob:
                got = (u, blob)
                break
        if not got:
            fail += 1
            continue
        u, blob = got
        ext = ".png" if blob[:8].startswith(b"\x89PNG") else ".jpg"
        f = a.out / f"scene_{n:03d}_ref{i}{ext}"
        f.write_bytes(blob)
        r["local"] = str(f)
        r["serper_url"] = u
        r["serper_query"] = q
        qcache[q] = str(f)
        ok += 1
        if ok % 10 == 0:
            print(f"    … {ok}건", flush=True)
        time.sleep(0.3)

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  받음 {ok} · 재사용 {reuse} · 실패 {fail} → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
