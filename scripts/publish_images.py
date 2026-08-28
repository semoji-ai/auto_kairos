#!/usr/bin/env python3
"""작업 폴더의 씬 이미지를 프로젝트 규격으로 옮긴다 — 대시보드가 읽을 수 있게.

`_imggen/ep##/current/`는 작업용이고, 대시보드와 렌더링은 프로젝트 폴더만 본다.

    output/{uuid}_{slug}/images/
      ├── generated/scene_###_gen_##.png   생성 이미지
      ├── search/scene_###_search_01.jpg   실물 자료
      └── image_assets.json                selected로 무엇을 쓸지 지정

`get_scene_image_url()`이 image_assets.json의 selected를 먼저 보고, 없으면
파일명 규칙으로 찾는다. 둘 다 맞춰 둔다.

기존 파일은 지우지 않고 버전을 올린다(이미지 삭제 금지 규칙).

    python3 scripts/publish_images.py <ep_dir> <project_dir>
"""
from __future__ import annotations
import argparse, json, re, shutil, sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("epdir", type=Path, help="_imggen/ep01 처럼 작업 폴더")
    ap.add_argument("project", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    # `current/` 가 있으면 그것을 쓰고, 없으면 `out/`(생성 결과)을 바로 본다.
    #
    # 예전에는 `current/` 만 봤다. 그래서 그릴 때마다 절차에 이 줄이 끼어 있었다.
    #
    #     cp _imggen/ep01_vN/out/scene_*.png _imggen/ep01_vN/current/
    #
    # 그 복사가 **사본을 한 벌씩 더 만든다.** EP01 작업 폴더 2.4GB 중 0.53GB(22%)가
    # out 과 current 에 같은 파일이 두 벌 있어 생긴 것이었다. 하루에 배치를 스무 번
    # 돌리면 그만큼 쌓인다.
    #
    # `current/` 를 계속 지원하는 이유는 organize_versions 로 여러 판 중 골라 담는
    # 흐름이 있기 때문이다. 고른 것이 있으면 그쪽이 이긴다.
    cur = args.epdir / "current"
    if not cur.exists():
        out = args.epdir / "out"
        if out.exists() and any(out.glob("scene_*.png")):
            cur = out
            print(f"  {args.epdir.name}: current 없음 → out 에서 바로 발행합니다")
        else:
            print(f"  {args.epdir.name}: current·out 둘 다 없음 — organize_versions 먼저")
            return 1

    spec = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in spec.get("scenes", spec)}

    dst = args.project / "images" / "generated"
    dst.mkdir(parents=True, exist_ok=True)
    db_path = args.project / "images" / "image_assets.json"
    db = json.loads(db_path.read_text(encoding="utf-8")) if db_path.exists() else {"scenes": []}
    by_n = {s["sceneNumber"]: s for s in db["scenes"]}

    moved = skipped = 0
    for src in sorted(cur.glob("scene_*.png")):
        n = int(re.match(r"scene_(\d+)", src.stem).group(1))
        s = scenes.get(n)
        if not s or (s.get("imageAsset") or {}).get("source") != "generate":
            skipped += 1
            continue
        entry = by_n.setdefault(n, {"sceneNumber": n, "images": []})
        gens = [i for i in entry["images"] if i.get("type") == "generate"]
        name = f"scene_{n:03d}_gen_{len(gens) + 1:02d}.png"
        if not args.dry_run:
            shutil.copy2(src, dst / name)
        for i in entry["images"]:
            i["selected"] = False
        entry["images"].append({
            "file": f"generated/{name}", "type": "generate", "selected": True,
            "prompt": (s.get("imageAsset") or {}).get("prompt", ""),
            "cast": s.get("cast"), "people": s.get("people"),
        })
        moved += 1

    db["scenes"] = sorted(by_n.values(), key=lambda x: x["sceneNumber"])
    if not args.dry_run:
        db_path.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")

    sel = sum(1 for s in db["scenes"] for i in s["images"] if i.get("selected"))
    print(f"  {args.project.name}: 생성 이미지 {moved}장 등록 / 건너뜀 {skipped} "
          f"→ 전체 {len(db['scenes'])}씬, selected {sel}"
          + (" [dry-run]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
