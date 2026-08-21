#!/usr/bin/env python3
"""레퍼런스 자료를 내려받는다 — 화면에 안 나가고, 그릴 때 보고 그리는 자료.

`fetch_assets.py`는 화면에 그대로 쓸 자료를 `images/search/`에 넣고 렌더러에
등록한다. 레퍼런스는 다르다. 화면에 나가지 않으므로 등록하지 않고, 대신
**이미지 생성 시점에 codex 에 첨부**해야 한다. URL만 있으면 붙일 수가 없다.

그래서 별도 폴더에 받고 `refAssets[].local` 에 경로를 적어 둔다.
`gen_scenes.py` 가 그 경로를 읽어 `view_image` 로 붙인다.

**받은 것이 진짜 그림인지 확인한다.** HTML이 내려오거나 너무 작은 것은 버린다 —
조사에서 인용구 그래픽을 초상으로 잘못 기록한 적이 있다.

    python3 scripts/fetch_ref_assets.py <project_dir> [-o _imggen/refs]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# 위키미디어는 도구를 식별하는 UA 를 요구한다. 브라우저를 흉내 내면 429 를 준다.
UA = "AutoKairosAssetFetcher/1.0 (documentary research; contact via project)"
THROTTLE = 0.8          # 초 — 이보다 빨리 때리면 429 가 돌아온다
RETRY = 3
MIN_BYTES = 8000        # 이보다 작으면 아이콘·썸네일이라 참조가 안 된다
SIGS = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF8", b"RIFF", b"<svg")


def looks_like_image(b: bytes) -> bool:
    head = b[:16]
    if any(head.startswith(s) for s in SIGS):
        return True
    return b[:400].lstrip().lower().startswith(b"<svg")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("_imggen/refs"))
    a = ap.parse_args()

    p = a.project / "scene_specs.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    a.out.mkdir(parents=True, exist_ok=True)

    seen: dict[str, str] = {}      # url → 로컬 경로 (같은 자료가 여러 씬에 붙는다)
    ok = fail = reuse = 0
    fails: list[tuple[int, str]] = []

    for sc in data.get("scenes", []):
        n = sc.get("sceneNumber")
        refs = (sc.get("imageAsset") or {}).get("refAssets") or []
        for i, r in enumerate(refs, 1):
            url = (r.get("url") or "").strip()
            if not url:
                continue
            if url in seen:
                r["local"] = seen[url]
                reuse += 1
                continue
            blob = None
            last = ""
            for attempt in range(1, RETRY + 1):
                try:
                    time.sleep(THROTTLE)
                    req = urllib.request.Request(url, headers={
                        "User-Agent": UA, "Accept": "image/*,*/*;q=0.8"})
                    with urllib.request.urlopen(req, timeout=40) as resp:
                        blob = resp.read()
                    break
                except urllib.error.HTTPError as e:
                    last = f"HTTP {e.code}"
                    if e.code in (429, 503):
                        time.sleep(THROTTLE * 4 * attempt)   # 물러섰다 다시
                        continue
                    break
                except Exception as e:
                    last = f"{type(e).__name__} {str(e)[:30]}"
                    break
            if blob is None:
                fails.append((n, last))
                fail += 1
                continue
            if not looks_like_image(blob) or len(blob) < MIN_BYTES:
                fails.append((n, f"그림이 아니거나 너무 작음 ({len(blob)}B)"))
                fail += 1
                continue
            ext = ".png" if blob[:8].startswith(b"\x89PNG") else ".jpg"
            f = a.out / f"scene_{n:03d}_ref{i}{ext}"
            f.write_bytes(blob)
            r["local"] = str(f)
            seen[url] = str(f)
            ok += 1

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  받음 {ok}건 · 재사용 {reuse}건 · 실패 {fail}건 → {a.out}")
    for n, why in fails[:12]:
        print(f"    ✗ 씬{n}: {why}")
    if len(fails) > 12:
        print(f"    … 외 {len(fails)-12}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
