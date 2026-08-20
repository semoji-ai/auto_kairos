#!/usr/bin/env python3
"""인포그래픽 씬을 조립한다 — 만들어 둔 요소를 화면 어디에 놓을지 정한다.

에셋만 쌓아 두고 화면을 만드는 단계가 없었다. 그래서 재분석으로 인포그래픽이
된 씬도 스토리보드에는 옛 재연 그림만 보였다.

여기서 하는 일은 **자리를 정해 숫자로 적는 것**뿐이다. 그림을 굽지 않는다.
같은 숫자를 스토리보드 미리보기와 Remotion이 함께 읽는다 — 두 곳에서 따로
배치하면 반드시 어긋난다.

자리는 `composition.form`이 정한다. 재분석이 이름을 자유롭게 짓기 때문에,
아는 이름이면 그 배치로 가고 모르면 가로로 고르게 늘어놓는다.

    python3 scripts/compose_infographics.py EP01
    python3 scripts/compose_infographics.py EP01 --apply
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def slots(form: str, n: int) -> list[dict]:
    """요소가 놓이는 자리 — 화면 대비 백분율(가운데 기준)."""
    f = (form or "").lower()

    if any(k in f for k in ("orbit", "center", "around", "surround")):
        rest = max(1, n - 1)
        out = [{"left": 50, "top": 48, "size": 34}]
        for i in range(1, n):
            import math
            a = 2 * math.pi * (i - 1) / rest - math.pi / 2
            out.append({"left": 50 + math.cos(a) * 30,
                        "top": 48 + math.sin(a) * 26, "size": 18})
        return out

    if any(k in f for k in ("branch", "fork", "split", "diverge")):
        rest = max(1, n - 1)
        return [{"left": 24, "top": 50, "size": 28} if i == 0
                else {"left": 70, "top": 100 * i / (rest + 1), "size": 20}
                for i in range(n)]

    if any(k in f for k in ("stack", "pile", "removal", "tower", "layer")):
        step = 52 / max(1, n - 1) if n > 1 else 0
        return [{"left": 50, "top": 82 - i * step, "size": 26} for i in range(n)]

    if any(k in f for k in ("scale", "compare", "versus", "vs")):
        return [{"left": 100 * (i + 1) / (n + 1), "top": 55,
                 "size": 14 + 18 * i / max(1, n - 1)} for i in range(n)]

    # flow · chain · 그 밖 — 가로로 고르게
    size = 17 if n > 4 else 22
    return [{"left": 100 * (i + 1) / (n + 1), "top": 52, "size": size}
            for i in range(n)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    proj = Path(next(v["dir"] for k, v in emap.items() if k.startswith(args.ep)))
    mode_f = root / "_imggen" / f"{args.ep}_mode.json"
    if not mode_f.exists():
        raise SystemExit(f"재분석 결과가 없습니다: {mode_f}")
    mode = {s["n"]: s for s in json.loads(mode_f.read_text(encoding="utf-8"))["scenes"]
            if s.get("mode") == "infographic"}

    # 씬 그림과 견줘 「씬 그림이 낫다」고 정한 씬은 다시 인포로 만들지 않는다.
    # 이 판정을 안 보면 되돌려 놓은 것이 조립할 때마다 되살아난다.
    pick_dir = root / "_imggen" / f"{args.ep.lower()}_pick"
    picks = {}
    for f_ in pick_dir.glob("s*.json") if pick_dir.exists() else []:
        try:
            picks[int(f_.stem[1:])] = json.loads(f_.read_text(encoding="utf-8")).get("pick")
        except Exception:
            continue

    layout_dir = root / "_imggen" / f"{args.ep.lower()}_layout"
    asset_dir = root / "_imggen" / f"{args.ep.lower()}_info"
    have = {p.stem: p for p in asset_dir.glob("*.png") if "_raw" not in p.name} \
        if asset_dir.exists() else {}

    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))

    done, missing, skipped, passed = 0, [], [], []
    for s in data.get("scenes", []):
        n = s.get("sceneNumber")
        spec = mode.get(n)
        if not spec:
            continue
        if picks.get(n) in ("scene", "overlay"):
            passed.append(n)
            continue

        # 설계가 있으면 그것을 쓴다. 규칙으로 나눈 자리는 그냥 늘어놓은
        # 화면이 되고, 시험작에 있던 문법(항 묶기·기호·강조)이 없다.
        lay_f = layout_dir / f"s{n:03d}.json"
        lay = None
        if lay_f.exists():
            try:
                lay = json.loads(lay_f.read_text(encoding="utf-8"))
            except Exception:
                lay = None

        if lay and lay.get("skip"):
            # 도해로 만들면 힘이 빠지는 씬 — 재연 그림으로 되돌린다
            if s.get("visual_kind") == "infographic":
                s["visual_kind"] = "generate_image"
                s.pop("infographic", None)
                s.setdefault("imageAsset", {})["source"] = "generate"
            skipped.append((n, lay.get("why", "")))
            continue

        items = []
        if lay and lay.get("items"):
            for it in lay["items"]:
                p_ = have.get(f"s{n:03d}_{it['id']}")
                if not p_:
                    missing.append(f"s{n:03d}_{it['id']}")
                    continue
                items.append({
                    "id": it["id"], "src": f"{asset_dir.name}/{p_.name}",
                    "left": it.get("left", 50), "top": it.get("top", 50),
                    "size": it.get("size", 20),
                    "label": it.get("label", ""),
                    "emphasis": it.get("emphasis", "normal"),
                })
        else:
            for a in spec.get("assets") or []:
                stem = f"s{n:03d}_{a['id']}"
                p_ = have.get(stem)
                if not p_:
                    missing.append(stem)
                    continue
                items.append({"id": a["id"], "src": f"{asset_dir.name}/{p_.name}"})
            if items:
                pos = slots((spec.get("composition") or {}).get("form", ""), len(items))
                labels = spec.get("labels") or []
                for i, it in enumerate(items):
                    it.update(pos[i])
                    it["emphasis"] = "normal"
                    if i < len(labels):
                        it["label"] = labels[i]

        if not items:
            continue

        s["infographic"] = {
            "title": (lay or {}).get("title", ""),
            # 그리드 대신 그 씬의 지도·그림을 배경으로 깔 수 있다.
            # 지도 위에 요소를 얹으면 「어디」와 「무엇이」가 한 화면에 온다.
            "background": (lay or {}).get("background", "grid"),
            # 글자가 읽히는 방식 — 배경이 복잡할수록 판을 깐다
            "contrast": (lay or {}).get("contrast", "plain"),
            "split_hint": (lay or {}).get("split_hint", ""),
            "divider": (lay or {}).get("divider", "none"),
            "marks": (lay or {}).get("marks", []),
            "form": (spec.get("composition") or {}).get("form", ""),
            "note": (lay or {}).get("why") or (spec.get("composition") or {}).get("note", ""),
            "designed": bool(lay),
            "items": items,
        }
        s["visual_kind"] = "infographic"
        s.setdefault("imageAsset", {})["source"] = "infographic"
        done += 1

    designed = sum(1 for s in data.get("scenes", [])
                   if (s.get("infographic") or {}).get("designed"))
    print(f"{args.ep}  인포그래픽 씬 {len(mode)}개 중 {done}개 조립 (설계본 {designed}개)")
    if passed:
        print(f"  씬 그림으로 정한 씬 {len(passed)}개는 건드리지 않았습니다")
    for n, why in skipped:
        print(f"  씬{n:>3} 재연으로 되돌림 — {why[:60]}")
    if missing:
        print(f"  요소 파일이 없어 건너뜀 {len(missing)}개: {missing[:6]}")

    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(f, f.with_suffix(f".json.bak_compose_{stamp}"))
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  저장했습니다 (백업 .bak_compose_{stamp})")
    else:
        print("  --apply 를 붙이면 실제로 씁니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
