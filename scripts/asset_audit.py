#!/usr/bin/env python3
"""scene_specs의 이미지 계획을 자료 조사용으로 내보내고, 조사 결과를 되먹인다.

브랜드 다큐는 실물 아카이브가 먼저다. 씬마다 실제 자료가 있는지 확인한 뒤
source(search/generate)를 다시 정하기 위한 왕복 도구.

    export  : python3 scripts/asset_audit.py export <project_dir> -o <out.json>
    apply   : python3 scripts/asset_audit.py apply <project_dir> <decision.json>

export 결과는 씬별 나레이션과 현재 이미지 계획만 담은 압축본이다.
apply는 조사 보고서의 결정을 scene_specs에 반영하되, 원본을 백업하고
narration·layout 등 다른 필드는 건드리지 않는다.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


def load_specs(project: Path):
    f = project / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data.get("scenes", data) if isinstance(data, dict) else data
    return f, data, scenes


def cmd_export(args) -> int:
    _, _, scenes = load_specs(args.project)
    out = []
    for i, s in enumerate(scenes, 1):
        ia = s.get("imageAsset") or {}
        out.append(
            {
                "n": i,
                "sceneId": s.get("sceneId"),
                "narration": (s.get("narration") or "").replace("\n", " ")[:300],
                "headline": s.get("headline"),
                "source": ia.get("source"),
                "query": ia.get("query"),
                "prompt": (ia.get("prompt") or "")[:160],
            }
        )
    Path(args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"{len(out)}개 씬 내보냄 → {args.out}")
    return 0


def cmd_apply(args) -> int:
    f, data, scenes = load_specs(args.project)
    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    if isinstance(decisions, dict):
        decisions = decisions.get("scenes", [])

    by_id = {s.get("sceneId"): s for s in scenes if s.get("sceneId")}

    backup = f.with_suffix(".json.pre_asset_audit")
    if not backup.exists():
        shutil.copy2(f, backup)

    changed = to_search = to_generate = missing = 0
    for d in decisions:
        sid = d.get("sceneId")
        scene = by_id.get(sid)
        if scene is None:
            missing += 1
            continue

        # imageAsset이 아예 없거나 null인 씬이 있다 (텍스트 전용 레이아웃 등)
        ia = scene.get("imageAsset")
        if not isinstance(ia, dict):
            ia = {}
            scene["imageAsset"] = ia
        want = d.get("decision")
        if want not in ("search", "generate"):
            continue

        before = ia.get("source")
        ia["source"] = want

        if want == "search":
            if d.get("query"):
                ia["query"] = d["query"]
            # 조사에서 확인된 실물 후보를 남긴다 (렌더에는 쓰이지 않는 메모)
            if d.get("candidates"):
                ia["assetCandidates"] = d["candidates"][:5]
            ia.pop("prompt", None)
        else:
            if d.get("prompt"):
                ia["prompt"] = d["prompt"]

        if before != want:
            changed += 1
            if want == "search":
                to_search += 1
            else:
                to_generate += 1

    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"{args.project.name}: 변경 {changed}건 "
        f"(generate→search {to_search}, search→generate {to_generate}), "
        f"매칭 실패 {missing}"
    )
    return 0 if missing == 0 else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export")
    e.add_argument("project", type=Path)
    e.add_argument("-o", "--out", required=True)
    e.set_defaults(func=cmd_export)

    a = sub.add_parser("apply")
    a.add_argument("project", type=Path)
    a.add_argument("decisions", type=Path)
    a.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
