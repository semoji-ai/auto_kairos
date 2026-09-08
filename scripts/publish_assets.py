#!/usr/bin/env python3
"""도해 요소와 인물 시트를 **프로젝트 폴더로 발행한다.**

씬 이미지는 이미 `publish_images.py` 가 `_imggen/<ep>/out/` 에서
`output/…/images/generated/` 로 옮긴다. 그런데 **도해와 시트는 그 길이
없었다.** 만든 자리에 그대로 두고 화면이 작업 폴더를 직접 읽었다.

무엇이 잘못되는가.

  · 프로젝트 폴더만 백업하면 **도해가 통째로 빠진다** — 씬 이미지만 있고
    화면의 절반이 없다
  · `output` 은 NAS 인데 도해만 로컬이라 **워크스페이스를 옮기면 깨진다**
  · 앱이 `/infoassets/` 로 `_imggen` 을 직접 읽는데, 그 라우트가 폴더
    이름 규칙(`<ep>_info`)에 매여 있었다. 도해를 한 장으로 그리는 방식으로
    바꾸면서 폴더가 `<ep>_infoscene` 이 되자 **열두 편이 전부 404** 였다
  · 작업 폴더가 자산 저장소를 겸하니 **비울 수가 없다**

옮기는 곳은 이렇다.

    output/{uuid}_{slug}/images/info/        도해 요소·도해 한 장
    output/_series/<series_id>/characters/   인물 시트 (편이 함께 쓴다)

**파일은 복사한다. 지우지 않는다.** 만드는 곳은 여전히 `_imggen` 이다 —
코덱스가 NAS 에 쓰지 못하기 때문이다.

    python3 scripts/publish_assets.py EP01
    python3 scripts/publish_assets.py --all
    python3 scripts/publish_assets.py --all --sheets
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import (  # noqa: E402
    get_charsheet_dir,
    get_series_dir,
    resolve_project,
)

ROOT = Path(__file__).resolve().parent.parent


def series_id_of(proj: Path) -> str | None:
    f = proj / "episode_brief.json"
    if not f.is_file():
        return None
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return None
    return ((d.get("_series") or {}) or {}).get("series_id")


def publish_info(ep: str, apply: bool) -> int:
    """씬이 실제로 쓰는 도해 파일만 옮긴다 — 작업 중 버린 것까지 끌고 가지 않는다."""
    proj, label = resolve_project(ep)
    spec_f = proj / "scene_specs.json"
    if not spec_f.is_file():
        print(f"  {label}: scene_specs.json 없음 — 건너뜀")
        return 0
    spec = json.loads(spec_f.read_text(encoding="utf-8"))
    dst_dir = proj / "images" / "info"

    moved = missing = same = 0
    changed = False
    for s in spec.get("scenes", []):
        ig = s.get("infographic") or {}
        for it in ig.get("items") or []:
            src = (it.get("src") or "").strip()
            if not src or src.startswith("info/"):
                continue                     # 이미 옮긴 것
            srcp = ROOT / "_imggen" / src
            if not srcp.is_file():
                missing += 1
                print(f"    파일 없음: {src}  (씬{s.get('sceneNumber')})")
                continue
            name = f"{Path(src).parent.name}__{Path(src).name}"
            dstp = dst_dir / name
            if apply:
                dst_dir.mkdir(parents=True, exist_ok=True)
                if dstp.exists() and dstp.stat().st_size == srcp.stat().st_size:
                    same += 1
                else:
                    shutil.copy2(srcp, dstp)
                    moved += 1
                it["src"] = f"info/{name}"
                changed = True
            else:
                moved += 1

    if apply and changed:
        spec_f.write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {label}: 도해 {moved}장 발행"
          + (f" · 이미 있음 {same}" if same else "")
          + (f" · 원본 없음 {missing}" if missing else ""))
    return moved


def publish_sheets(series: str, apply: bool) -> int:
    src_dir = get_charsheet_dir()
    if not src_dir:
        print("  인물 시트 폴더를 찾지 못했습니다")
        return 0
    dst_dir = get_series_dir(series, create=apply) / "characters"
    n = 0
    for p in sorted(Path(src_dir).glob("*_sheet*.png")):
        if apply:
            dst_dir.mkdir(parents=True, exist_ok=True)
            q = dst_dir / p.name
            if not (q.exists() and q.stat().st_size == p.stat().st_size):
                shutil.copy2(p, q)
        n += 1
    # 로스터도 함께 — 시트의 근거가 여기 적혀 있다
    roster = Path(src_dir).parent / "roster.json"
    if roster.is_file() and apply:
        shutil.copy2(roster, dst_dir / "roster.json")
    print(f"  시트 {n}장 → {dst_dir}")
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep", nargs="?")
    ap.add_argument("--all", action="store_true", help="시리즈 열두 편 전부")
    ap.add_argument("--sheets", action="store_true", help="인물 시트도 함께 발행")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    eps = [f"EP{i:02d}" for i in range(1, 13)] if args.all else [args.ep]
    if not eps or not eps[0]:
        ap.error("편을 지정하거나 --all 을 쓰세요")

    total = 0
    series = None
    for ep in eps:
        try:
            proj, _ = resolve_project(ep)
        except Exception as e:
            print(f"  {ep}: 건너뜀 ({e})")
            continue
        series = series or series_id_of(proj)
        total += publish_info(ep, args.apply)

    if args.sheets and series:
        publish_sheets(series, args.apply)

    print(f"\n도해 {total}장" + ("" if args.apply else "  — --apply 를 붙이면 실제로 옮깁니다"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
