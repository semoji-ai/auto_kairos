"""세모지 기법 도감 → AE 패널 동기화.

세모지 도감(semoji-motion/dogam)의 카탈로그·미리보기·키트 에셋을 패널 안으로 가져오고,
AE 구현(jsx/dogam/techniques/*.jsx)이 있는 기법만 모아 registry.json 을 만듭니다.

    python3 -m scripts.sync_dogam                # adobe/ 에서 실행
    python3 adobe/scripts/sync_dogam.py --check  # 복사 없이 registry 만 검증

경로
  원본: 환경변수 SEMOJI_MOTION_DIR → ~/Projects/semoji-motion → 저장소 내 번들 순
  대상: adobe/cep/com.autokairos.pd/jsx/dogam/assets/   ← .gitignore (재생성 가능한 복사본)
        adobe/cep/com.autokairos.pd/jsx/dogam/registry.json  ← 커밋(작고, 패널이 바로 읽음)

에셋을 확장 폴더 안에 두는 이유: 패널은 심볼릭 링크로 설치돼 있어 file:// 의 `..` 가
링크 밖(CEP/extensions)으로 풀립니다. 확장 폴더 안이면 패널(img/video src)과
JSX(assetsRoot) 가 같은 상대 경로로 닿습니다 — tylenol/assets 와 같은 방식입니다.

외부 원본의 미리보기 mp4는 기본적으로 링크하고, 저장소 번들의 12개 미리보기는
복사합니다. 따라서 다른 컴퓨터에는 별도 semoji-motion 저장소가 필요 없습니다.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ADOBE = Path(__file__).resolve().parents[1]
EXT = ADOBE / "cep" / "com.autokairos.pd"
DOGAM_JSX = EXT / "jsx" / "dogam"
ASSETS = DOGAM_JSX / "assets"
REGISTRY = DOGAM_JSX / "registry.json"
TECH_DIR = DOGAM_JSX / "techniques"
BUNDLED = ADOBE / "data" / "semoji-motion"

CASTS = ["walker1", "c2_boss", "c3_woman", "c4_elder", "c5_chef"]
# 기법 기본값(도감 미리보기와 같은 결과)에 쓰는 데모 에셋 — video/public 기준
DEMO_ASSETS = ["img/s06_kid.png"]


def semoji_dir() -> Path:
    explicit = os.environ.get("SEMOJI_MOTION_DIR")
    if explicit:
        return Path(explicit).expanduser()
    sibling = Path.home() / "Projects" / "semoji-motion"
    return sibling if (sibling / "dogam" / "techniques.json").is_file() else BUNDLED


def _same(a: Path, b: Path) -> bool:
    try:
        sa, sb = a.stat(), b.stat()
        return sa.st_size == sb.st_size and int(sa.st_mtime) <= int(sb.st_mtime)
    except FileNotFoundError:
        return False


def copy_file(src: Path, dst: Path) -> bool:
    if _same(src, dst):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def copy_tree(src: Path, dst: Path, pattern: str = "*") -> int:
    n = 0
    for f in sorted(src.glob(pattern)):
        if f.is_file():
            n += copy_file(f, dst / f.name)
    return n


def sync_assets(sm: Path, mp4_mode: str) -> dict:
    stats = {}
    stats["kit"] = sum(copy_tree(sm / "video/public/kit" / c, ASSETS / "kit" / c) for c in CASTS)
    stats["props"] = copy_tree(sm / "video/public/kit/props", ASSETS / "kit" / "props")
    stats["map"] = copy_file(sm / "ae/assets/map_bg.png", ASSETS / "map" / "map_bg.png")
    stats["demo"] = sum(copy_file(sm / "video/public" / rel, ASSETS / "demo" / Path(rel).name) for rel in DEMO_ASSETS)
    stats["catalog"] = copy_file(sm / "dogam/techniques.json", ASSETS / "catalog" / "techniques.json") + \
        copy_file(sm / "dogam/params.json", ASSETS / "catalog" / "params.json")
    stats["previews_jpg"] = copy_tree(sm / "dogam/previews", ASSETS / "previews", "*.jpg")
    link = ASSETS / "previews_src"
    if mp4_mode == "copy":
        if link.is_symlink():
            link.unlink()
        stats["previews_mp4"] = copy_tree(sm / "dogam/previews", link, "*.mp4")
    elif mp4_mode == "link":
        if link.is_symlink() or not link.exists():
            if link.is_symlink():
                link.unlink()
            link.symlink_to(sm / "dogam/previews", target_is_directory=True)
        stats["previews_mp4"] = "link"
    return stats


def find_node() -> str | None:
    d = os.environ.get("NODEJS_BIN_DIR") or os.environ.get("NODE_DIR")
    if d and (Path(d) / "node").exists():
        return str(Path(d) / "node")
    return shutil.which("node")


# node 로 techniques/*.jsx 를 읽어 register 인자(객체 리터럴)만 뽑습니다.
# apply 함수는 실행하지 않으므로 ExtendScript 전역(app 등)이 없어도 됩니다.
NODE_DUMP = r"""
const fs = require('fs'), path = require('path');
const out = {};
global.AKD = { register: (id, def) => { const o = {}; for (const k of Object.keys(def)) { const v = def[k]; if (typeof v !== 'function' && !(v instanceof RegExp)) o[k] = v; } out[id] = o; } };
for (const f of process.argv.slice(1)) { try { eval(fs.readFileSync(f, 'utf8')); } catch (e) { out['__error__' + path.basename(f)] = String(e); } }
process.stdout.write(JSON.stringify(out));
"""


def read_defs() -> dict:
    node = find_node()
    files = sorted(str(p) for p in TECH_DIR.glob("*.jsx"))
    if not node:
        sys.exit("node 를 찾지 못했습니다 — NODEJS_BIN_DIR 을 설정하세요")
    r = subprocess.run([node, "-e", NODE_DUMP, *files], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def build_registry(sm: Path) -> tuple[dict, list[str]]:
    cat = json.loads((sm / "dogam/techniques.json").read_text(encoding="utf-8"))
    by_id = {e["id"]: e for e in cat}
    defs = read_defs()
    warns, items = [], []
    for tid, d in sorted(defs.items()):
        if tid.startswith("__error__"):
            warns.append(f"{tid[9:]}: 로드 오류 {d}")
            continue
        e = by_id.get(tid)
        if not e:
            warns.append(f"{tid}: 도감에 없는 id")
            continue
        schema = e.get("params") or []
        dk = {p["key"] for p in schema}
        ak = set((d.get("params") or {}).keys())
        if dk != ak:
            warns.append(f"{tid}: 변수 불일치 도감only={sorted(dk - ak)} AEonly={sorted(ak - dk)}")
        for p in schema:   # 기본값 일치 확인(도감 = 기준)
            av = (d.get("params") or {}).get(p["key"])
            if av is not None and av != p["default"]:
                warns.append(f"{tid}.{p['key']}: 기본값 도감={p['default']} AE={av}")
        prev = e.get("preview")
        items.append({
            "id": tid, "name": e["name"], "category": e["category"], "summary": e["summary"], "spec": e.get("spec", ""),
            "tags": e.get("tags", []), "preview": prev,
            "previewJpg": f"jsx/dogam/assets/previews/{prev}.jpg" if prev else None,
            "previewMp4": f"jsx/dogam/assets/previews_src/{prev}.mp4" if prev else None,
            "kind": d.get("kind"), "create": bool(d.get("create")), "support": d.get("support", "native"),
            "aeNote": d.get("note", ""),
            "params": schema, "content": d.get("content") or {},
            "file": f"jsx/dogam/techniques/{tid}.jsx",
        })
    reg = {"version": 1, "source": "semoji-motion/dogam", "total_catalog": len(cat), "count": len(items),
           "categories": sorted({i["category"] for i in items}), "techniques": items}
    return reg, warns


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mp4", choices=["auto", "link", "copy", "none"], default="auto", help="미리보기 mp4: 원본이면 링크, 번들이면 복사(기본)·강제 링크·복사·생략")
    ap.add_argument("--assets-only", action="store_true", help="추가 도구 없이 포함된 registry를 유지하며 패널 에셋만 설치")
    ap.add_argument("--check", action="store_true", help="에셋 복사 없이 registry 만 만들고 검증")
    a = ap.parse_args()
    sm = semoji_dir()
    if not (sm / "dogam/techniques.json").exists():
        sys.exit(f"세모지 도감을 찾지 못했습니다: {sm} (SEMOJI_MOTION_DIR)")
    mp4_mode = ("copy" if sm == BUNDLED else "link") if a.mp4 == "auto" else a.mp4
    if not a.check:
        print("에셋 동기화:", sync_assets(sm, mp4_mode))
    if a.assets_only:
        if not REGISTRY.is_file():
            sys.exit(f"도감 registry가 없습니다: {REGISTRY}")
        print("기존 registry.json 유지 — 도감 패널 에셋 설치 완료")
        return
    reg, warns = build_registry(sm)
    REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"registry.json — AE 구현 {reg['count']} / 도감 {reg['total_catalog']}")
    for w in warns:
        print("  ⚠", w)


if __name__ == "__main__":
    main()
