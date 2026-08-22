#!/usr/bin/env python3
"""v3 에서 고친 씬 그림을 어도비 프로젝트로 옮긴다 (통합 전까지 쓰는 임시 다리).

어도비 패널은 v3 프로젝트를 **통째로 복사**해 쓴다. 그래서 v3 에서 그림을
다시 뽑아도 패널에는 옛 그림이 그대로다. 실제로 잔 모양 수정 9씬이 그렇게
반영되지 않았다.

    output/<uuid>_<slug>/images/generated/...   ← v3 가 고치는 곳
    adobe/projects/<id>/storyboard/sb_<sid>...  ← 패널이 보는 곳

**어도비 쪽이 더 최신인 씬을 덮으면 안 된다.** 패널에서 고친 그림(안경 제거,
자세 수정)은 v3 에 없다. 손으로 옮기다 109·110·112 를 덮을 뻔했다.
그래서 기본은 **어도비 쪽이 v3 보다 나중에 손댄 것이면 건너뛴다.**

    python3 scripts/sync_to_adobe.py <v3_project> <adobe_project> [--dry-run]

통합이 끝나면 이 스크립트는 필요 없어진다 — `docs/adobe-project-unification.md`.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def selected_images(v3: Path) -> dict:
    """v3 가 지금 쓰기로 한 그림. {씬번호: 경로}"""
    f = v3 / "images" / "image_assets.json"
    if not f.is_file():
        return {}
    out = {}
    for e in json.loads(f.read_text(encoding="utf-8")).get("scenes", []):
        rel = next((i["file"] for i in e.get("images", []) if i.get("selected")), None)
        if rel and (v3 / "images" / rel).is_file():
            out[e["sceneNumber"]] = v3 / "images" / rel
    return out


def next_version(sb: Path, sid: str) -> Path:
    """`sb_<sid>_v<N>.png`. 기존 파일은 지우지 않는다(이미지 삭제 금지)."""
    vs = [int(m.group(1)) for p in sb.glob(f"sb_{sid}_v*.png")
          if (m := re.search(r"_v(\d+)\.png$", p.name))]
    return sb / f"sb_{sid}_v{max(vs, default=1) + 1}.png"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("v3", type=Path)
    ap.add_argument("adobe", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="어도비 쪽이 더 최신이어도 덮는다 (패널에서 고친 것이 날아간다)")
    a = ap.parse_args()

    sc_f = a.adobe / "scenes.json"
    if not sc_f.is_file():
        print(f"  어도비 프로젝트가 아닙니다: {a.adobe}")
        return 1
    sel = selected_images(a.v3)
    if not sel:
        print(f"  v3 에 고른 그림이 없습니다: {a.v3}")
        return 1

    data = json.loads(sc_f.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data)
    sb = a.adobe / "storyboard"
    sb.mkdir(exist_ok=True)

    moved, kept, same = [], [], 0
    for s in scenes:
        src = sel.get(s.get("sceneNumber"))
        if not src:
            continue
        cur = s.get("imageRef") or ""
        curp = (a.adobe / cur) if cur else None
        if curp and curp.is_file():
            if curp.stat().st_size == src.stat().st_size:
                same += 1
                continue
            # **패널에서 고친 것을 덮지 않는다.** v3 보다 나중에 손댄 그림은
            # 여기에만 있는 작업이다(안경 제거·자세 수정).
            if not a.force and curp.stat().st_mtime > src.stat().st_mtime:
                kept.append((s["sceneNumber"], curp.name))
                continue
        dst = next_version(sb, s.get("sceneId") or "")
        if not a.dry_run:
            shutil.copy2(src, dst)
            s["imageRef"] = f"storyboard/{dst.name}"
        moved.append((s["sceneNumber"], src.name, dst.name))

    if not a.dry_run and moved:
        sc_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    tag = " [dry-run]" if a.dry_run else ""
    print(f"  옮김 {len(moved)} · 그대로 {same} · 어도비가 최신이라 건너뜀 {len(kept)}{tag}")
    for n, s_, d_ in moved:
        print(f"    {n}: {s_} → {d_}")
    for n, f_ in kept:
        print(f"    ! {n}: 패널에서 고친 {f_} 를 지켰습니다 (덮으려면 --force)")
    if not a.dry_run and moved:
        print("\n  패널에서 ↻ 새로고침 을 누르세요 — CEP 는 file:// 그림도 캐시합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
