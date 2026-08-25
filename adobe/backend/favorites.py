"""즐겨찾기 — 자주 쓰는 배경·소스를 한 곳에 모아 둔다.

소스 칸이 프로젝트의 이미지를 통째로 깔고 있었다. 디아지오편 기준 **1044장**
이고 그중 **565장이 내용이 같은 사본**이다(1.3GB) — 개발 과정에서
`images/generated/` 와 `storyboard/` 로 두 벌씩 남았다. 그 안에서 자주 쓰는
배경 한 장을 찾는 것은 일이다.

그래서 칸의 쓰임을 바꾼다.

    전    프로젝트 이미지 1044장을 다 깐다
    후    **즐겨찾기**만 깐다. 프로젝트 소스는 폴더를 열어 끌어다 쓴다

즐겨찾기는 **프로젝트 밖**에 둔다(`<작업폴더>/favorites/`). 자주 쓰는 배경은
편이 바뀌어도 계속 쓰는 것이고, 프로젝트를 지워도 남아야 한다.

파일은 **복사한다.** 원본을 가리키기만 하면 그 프로젝트를 지웠을 때 즐겨찾기가
통째로 깨진다. 같은 그림을 두 번 담아도 한 벌만 남는다(내용으로 판정).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg", ".mp4", ".mov"}
META = "favorites.json"


def root() -> Path:
    """즐겨찾기 폴더. `AK_FAVORITES` 로 옮길 수 있다."""
    p = os.environ.get("AK_FAVORITES")
    if p:
        return Path(p)
    # adobe/backend/favorites.py → adobe/backend → adobe → 작업 폴더
    return Path(__file__).resolve().parents[2] / "favorites"


def _meta_path() -> Path:
    return root() / META


def _load() -> dict:
    try:
        return json.loads(_meta_path().read_text(encoding="utf-8"))
    except Exception:
        return {"items": []}


def _save(d: dict) -> None:
    root().mkdir(parents=True, exist_ok=True)
    _meta_path().write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _digest(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def _free_name(name: str) -> Path:
    """이름이 겹치면 뒤에 번호를 붙인다 — **덮어쓰지 않는다.**"""
    d = root()
    out = d / name
    if not out.exists():
        return out
    stem, ext = (name.rsplit(".", 1) + [""])[:2]
    n = 2
    while (d / f"{stem}_{n}.{ext}").exists():
        n += 1
    return d / f"{stem}_{n}.{ext}"


def add(src, *, label: str = "", tags=None) -> dict:
    """파일 하나를 즐겨찾기에 담는다. 이미 있으면 그것을 돌려준다."""
    p = Path(src)
    if not p.is_file():
        return {"error": f"파일 없음: {p.name}"}
    if p.suffix.lower() not in EXTS:
        return {"error": f"담을 수 없는 형식: {p.suffix}"}
    root().mkdir(parents=True, exist_ok=True)
    d = _load()
    dig = _digest(p)
    for it in d["items"]:
        if it.get("md5") == dig and (root() / it["name"]).is_file():
            return {"ok": True, "already": True, "item": it}
    out = _free_name(p.name)
    shutil.copy2(p, out)
    it = {"name": out.name, "label": label or p.stem, "md5": dig,
          "from": str(p), "tags": list(tags or []), "at": round(time.time())}
    d["items"].append(it)
    _save(d)
    return {"ok": True, "already": False, "item": it}


def remove(name: str) -> dict:
    """즐겨찾기에서 뺀다. **파일도 지운다** — 여기 있는 것은 사본이다."""
    d = _load()
    keep, gone = [], None
    for it in d["items"]:
        if it.get("name") == name:
            gone = it
        else:
            keep.append(it)
    if gone is None:
        return {"error": f"없는 항목: {name}"}
    try:
        (root() / name).unlink(missing_ok=True)
    except OSError:
        pass
    d["items"] = keep
    _save(d)
    return {"ok": True, "removed": gone}


def listing() -> dict:
    """담긴 것들. 파일이 사라진 항목은 조용히 걸러 낸다."""
    d = _load()
    out, dirty = [], False
    for it in d.get("items", []):
        p = root() / it.get("name", "")
        if not p.is_file():
            dirty = True
            continue
        out.append({**it, "path": str(p), "size": p.stat().st_size,
                    "kind": "video" if p.suffix.lower() in (".mp4", ".mov") else "image"})
    if dirty:
        d["items"] = [x for x in d.get("items", []) if (root() / x.get("name", "")).is_file()]
        _save(d)
    out.sort(key=lambda x: -(x.get("at") or 0))
    return {"root": str(root()), "items": out}


def reveal(target) -> dict:
    """탐색기에서 그 파일이 든 폴더를 연다 — 끌어다 쓰라고.

    맥·윈도우·리눅스가 각각 다르다. 파일을 주면 그 파일을 고른 채로 연다.
    """
    p = Path(target)
    if not p.exists():
        return {"error": f"없는 경로: {p}"}
    sysname = platform.system()
    try:
        if sysname == "Darwin":
            subprocess.run(["open", "-R", str(p)] if p.is_file() else ["open", str(p)],
                           check=False)
        elif sysname == "Windows":
            if p.is_file():
                # /select 는 쉼표 뒤에 공백이 없어야 한다
                subprocess.run(f'explorer /select,"{p}"', shell=True, check=False)
            else:
                subprocess.run(["explorer", str(p)], check=False)
        else:
            subprocess.run(["xdg-open", str(p if p.is_dir() else p.parent)], check=False)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "opened": str(p if p.is_dir() else p.parent), "os": sysname}
