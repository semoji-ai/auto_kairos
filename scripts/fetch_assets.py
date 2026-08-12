#!/usr/bin/env python3
"""확정된 실물 자료를 내려받아 프로젝트에 넣는다.

조사로 URL과 라이선스만 확정해 두면 화면은 여전히 비어 있다. 전체 779씬 중
229씬(29%)이 그 상태였다. 파일을 받아 `images/search/`에 넣고
`image_assets.json`에 등록해야 렌더링이 쓴다.

**받은 파일이 진짜 사진인지 확인한다.** 조사에서 인용구 그래픽을 초상으로
잘못 기록한 적이 두 번 있었다(구인회·허만정). 여기서는 형식과 크기로 거른다 —
HTML이 내려오거나, 너무 작아 화면에 못 쓰는 것(가로 400px 미만)은 실패로 본다.
그림 내용까지는 멀티모달 검수가 본다.

    python3 scripts/fetch_assets.py <project_dir> --ledger <ledger.json>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
# 위키미디어는 브라우저 흉내 UA를 429로 막는다. 정책상 무엇을 하는 누구인지
# 밝히고 연락처를 남긴 UA를 요구한다.
WIKI_UA = ("SemojiDocResearch/1.0 (https://github.com/kimsh-1/auto_kairos_v3; "
           "documentary research) Python-urllib")


def headers_for(url: str) -> dict:
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if "wikimedia.org" in host or "wikipedia.org" in host:
        return {"User-Agent": WIKI_UA}
    # 이미지 직링크를 막는 곳은 대개 같은 도메인에서 온 요청만 받는다
    return {**UA, "Referer": f"https://{host}/", "Accept": "image/*,*/*"}
MIN_WIDTH = 400          # 이보다 좁으면 풀스크린에 못 쓴다
EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
       "image/gif": ".gif"}


def fetch(url: str, dest_stem: Path, retries: int = 3) -> tuple[Path | None, str]:
    # 429는 서버가 잠깐 기다리라는 뜻이다 — 간격을 두면 대부분 회복된다
    body = ctype = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers_for(url))
            with urllib.request.urlopen(req, timeout=40) as r:
                ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip()
                body = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < retries - 1:
                time.sleep(8 * (i + 1))
                continue
            return None, f"HTTP {e.code}"
        except Exception as e:
            if i < retries - 1:
                time.sleep(4)
                continue
            return None, type(e).__name__
    if body is None:
        return None, "응답 없음"

    if ctype not in EXT:
        return None, f"이미지가 아님 ({ctype or '알 수 없음'})"
    if len(body) < 3000:
        return None, f"너무 작음 ({len(body)}B)"

    path = dest_stem.with_suffix(EXT[ctype])
    path.write_bytes(body)
    try:
        from PIL import Image
        with Image.open(path) as im:
            w, h = im.size
        if w < MIN_WIDTH:
            path.unlink()
            return None, f"해상도 부족 ({w}x{h})"
        return path, f"{w}x{h}"
    except Exception:
        return path, "크기 확인 불가"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--ledger", required=True, type=Path)
    args = ap.parse_args()

    spec_path = args.project / "scene_specs.json"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data.get("scenes", data)}

    led = json.loads(args.ledger.read_text(encoding="utf-8"))
    entries = [e for e in led.get("scenes", led) if e.get("found") and e.get("image_url")]

    outdir = args.project / "images" / "search"
    outdir.mkdir(parents=True, exist_ok=True)

    db_path = args.project / "images" / "image_assets.json"
    db = json.loads(db_path.read_text(encoding="utf-8")) if db_path.exists() else {"scenes": []}
    by_n = {s["sceneNumber"]: s for s in db["scenes"]}

    ok, fail = 0, []
    for e in entries:
        n = e["n"]
        s = scenes.get(n)
        if not s or (s.get("imageAsset") or {}).get("source") != "search":
            continue
        # 「이 씬 내용과 어떻게 이어지는가」를 못 적었으면 쓸 근거가 없다.
        # 이 검사가 없어서 부산 이전 씬에 1945년 귀환선 사진이, 1940년대 동업
        # 설명에 2005년 GS 출범식 사진이 붙었다. 둘 다 desc는 정확했다.
        if not (e.get("relevance") or "").strip():
            fail.append((n, "relevance 공란 — 씬과의 연결 근거 없음"))
            continue
        stem = outdir / f"scene_{n:03d}_search_01"
        got = next((p for p in outdir.glob(f"scene_{n:03d}_search_01.*")), None)
        if got:
            path, info = got, "이미 있음"
        else:
            path, info = fetch(e["image_url"], stem)
        if info != "이미 있음":
            time.sleep(1.5)
        if not path:
            fail.append((n, info))
            continue
        ok += 1
        rec = {"file": f"search/{path.name}", "type": "search", "selected": True,
               "source_url": e["image_url"], "page_url": e.get("page_url"),
               "holder": e.get("holder"), "license": e.get("license"),
               "checked": e.get("checked"), "relevance": e.get("relevance"),
               "size": info}
        entry = by_n.setdefault(n, {"sceneNumber": n, "images": []})
        entry["images"] = [i for i in entry["images"] if i.get("type") != "search"]
        for i in entry["images"]:
            i["selected"] = False
        entry["images"].append(rec)

    db["scenes"] = sorted(by_n.values(), key=lambda x: x["sceneNumber"])
    db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  {args.project.name}: 확보 {ok}/{len(entries)}건")
    for n, why in fail[:8]:
        print(f"      씬 {n:>3} 실패 — {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
