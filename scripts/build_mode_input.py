#!/usr/bin/env python3
"""시각화 방식 재분석에 넣을 입력을 만든다 — `{EP}_mode_in.json`.

씬을 무엇으로 보여줄지(재연·인포그래픽·실물·콜라주·지도) 정하려면 판단에
필요한 것이 한자리에 있어야 한다. 나레이션만으로는 리듬을 볼 수 없고,
지금의 연출만으로는 왜 그렇게 됐는지 알 수 없다.

그래서 씬마다 이만큼을 모은다.

    나레이션 · 지금의 연출(프롬프트까지) · 등장 인물 · 확보한 실물 자료

**실물 자료는 relevance가 채워진 것만 싣는다.** 공란은 「그 씬 내용을 직접
증명하는가」에 답하지 못한 자료이고, 지난번 오용 76%가 전부 그 안에 있었다.
판단 재료로 올리면 같은 실수를 다시 부른다.

    python3 scripts/build_mode_input.py EP02 --slug lg_brand_encyclopedia_ep02
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_project(slug: str) -> Path:
    """slug로 프로젝트 output 디렉토리를 찾는다."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from auto_agent.db.project_manager import ProjectManager

    p = ProjectManager().get_project(slug=slug)
    if not p:
        raise SystemExit(f"프로젝트를 찾을 수 없습니다: {slug}")
    return Path(p["output_dir"])


def load_ledger(root: Path, ep: str) -> dict[int, dict]:
    """자료 대장 — 씬 번호 → 조사 결과.

    relevance는 scene_specs가 아니라 대장(`{EP}_search_assets2.json`)에 있다.
    조사한 사람이 「이 자료가 이 씬 내용과 어떻게 이어지는지」 적는 자리다.
    """
    f = root / "_imggen" / f"{ep}_search_assets2.json"
    if not f.exists():
        return {}
    raw = json.loads(f.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("assets") or raw.get("scenes") or []
    return {r["n"]: r for r in rows if r.get("n") is not None}


def real_asset_of(scene: dict, led: dict) -> dict | None:
    """이 씬이 쓰는 실물 자료. **관련성이 적힌 것만** 낸다.

    공란은 「이 씬 내용을 직접 증명하는가」에 답하지 못한 자료다. 지난번
    오용 76%가 전부 그 안에 있었으므로 판단 재료로 올리지 않는다.
    """
    if not led or not led.get("found"):
        return None
    rel = (led.get("relevance") or "").strip()
    if not rel:
        return None
    return {
        "desc": led.get("desc"),
        "relevance": rel,
        "holder": led.get("holder"),
        "license": led.get("license"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep", help="EP02 처럼 대문자 편 이름 — 출력 파일 이름에 쓴다")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    out_dir = find_project(args.slug)
    specs = json.loads((out_dir / "scene_specs.json").read_text(encoding="utf-8"))
    ledger = load_ledger(root, args.ep)

    rows = []
    for s in specs.get("scenes", []):
        ia = s.get("imageAsset") or {}
        rows.append({
            "n": s.get("sceneNumber"),
            "chapter": s.get("chapter"),
            "narration": s.get("narration") or "",
            "headline": s.get("headline") or "",
            "infoStructure": s.get("infoStructure") or "scene",
            "layout": s.get("layout") or "",
            "cast": s.get("cast") or [],
            "people": s.get("people") or [],
            "now_source": ia.get("source") or "none",
            "now_prompt": ia.get("prompt") or "",
            "real_asset": real_asset_of(s, ledger.get(s.get("sceneNumber"), {})),
            "items": s.get("items") or [],
            "values": s.get("values") or [],
            "unit": s.get("unit"),
            "badge": s.get("badge"),
            "duration_sec": s.get("durationSec"),
        })

    dst = args.out or (root / "_imggen" / f"{args.ep}_mode_in.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    kinds: dict[str, int] = {}
    for r in rows:
        kinds[r["now_source"]] = kinds.get(r["now_source"], 0) + 1
    withreal = sum(1 for r in rows if r["real_asset"])
    print(f"{dst}  {len(rows)}씬")
    print(f"  지금 연출: {kinds}")
    print(f"  관련성 적힌 실물 자료: {withreal}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
