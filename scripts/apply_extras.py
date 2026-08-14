#!/usr/bin/env python3
"""무명 인물 조사 결과를 scene_specs의 `people`에 넣는다.

이름 없는 사람도 적어 두지 않으면 모델이 화면을 채우려다 옆 사람 얼굴을
복사한다. EP01 씬 11에서 집안 어른 둘이 같은 얼굴로 나왔다.

같은 배역이 여러 씬에 나오면 문장이 글자까지 같아야 한다 — 조금이라도 다르면
다른 사람이 된다. 조사 결과의 `recurring`을 기준으로 삼아 씬별 서술을 덮어쓴다.

    python3 scripts/apply_extras.py EP01
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    res = json.loads((root / "_imggen" / f"{a.ep}_extras.json").read_text(encoding="utf-8"))
    # 반복 배역은 한 문장으로 통일한다
    canon = {r["role"]: r["desc"] for r in res.get("recurring", [])}
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    proj = Path(next(v["dir"] for k, v in emap.items() if k.startswith(a.ep)))
    sp = proj / "scene_specs.json"
    data = json.loads(sp.read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data["scenes"]}

    n_set = n_people = 0
    for item in res["scenes"]:
        s = scenes.get(item["n"])
        if not s:
            continue
        ppl = []
        for d in item["people"]:
            role = d.split("(")[0].strip()
            ppl.append(canon.get(role, d))
        s["people"] = ppl
        n_set += 1; n_people += len(ppl)
    if not a.dry_run:
        sp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    empty = sum(1 for i in res["scenes"] if not i["people"])
    print(f"  {a.ep}: {n_set}씬에 인물 {n_people}명분 / 사람 없는 씬 {empty}"
          + ("  [dry-run]" if a.dry_run else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
