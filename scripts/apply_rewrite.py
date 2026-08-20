#!/usr/bin/env python3
"""다시 쓴 원고를 반영하고, 있던 그림을 새 씬에 물려준다.

씬을 다시 나누면 그림이 어긋난다. 이미지는 **씬 번호로** 묶여 있기 때문이다
(`image_assets.json`). 그래서 번호를 함부로 새로 매기지 않고, 새 씬마다
「어느 씬에서 왔는가(`from`)」를 따라 그림을 옮긴다.

  1:1  원래 번호를 그대로 쓴다 → 그림이 저절로 따라온다
  합침 첫 번호를 쓰고, 합쳐진 다른 씬의 그림은 **후보로 얹는다**
        (버리지 않는다 — 골라 쓸 수 있게)
  쪼갬 첫 조각이 원래 번호를 갖고, 나머지는 새 번호를 받는다.
        원래 씬에 그림이 여러 장이면 나눠 갖고, 모자라면 「그려야 함」으로 남는다

**그림 파일은 지우지 않는다.** 항목만 옮긴다.

    python3 scripts/apply_rewrite.py EP01              # 무엇이 바뀌는지만
    python3 scripts/apply_rewrite.py EP01 --apply
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

NEW_BASE = 700          # 쪼개서 생긴 씬에 줄 번호


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--chapter", type=int, help="이 챕터만")
    ap.add_argument("--files", help="배분 파일 이름들 (쉼표로 구분)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    spec_f = proj / "scene_specs.json"
    data = json.loads(spec_f.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    by_n = {s.get("sceneNumber"): s for s in scenes}

    img_f = proj / "images" / "image_assets.json"
    img_db = json.loads(img_f.read_text(encoding="utf-8")) if img_f.exists() else {"scenes": []}
    img_by_n = {e.get("sceneNumber"): e for e in img_db.get("scenes", [])}

    # 문장으로 배분한 결과가 있으면 그것을 쓴다. 없으면 다시 쓴 원고를 쓴다.
    split_dir = root / "_imggen" / f"{ep.lower()}_split"
    rw_dir = root / "_imggen" / f"{ep.lower()}_rewrite"
    # 배분 결과는 ch01.json 말고도 이름이 다양하다(resplit.json 등).
    # ch*.json 만 훑으면 넘겨준 파일을 못 찾는다.
    src_dir = split_dir if any(split_dir.glob("*.json")) else rw_dir
    plans = sorted(src_dir.glob("*.json"))
    if args.files:
        want = {x.strip().removesuffix(".json") for x in args.files.split(",")}
        plans = [f for f in plans if f.stem in want]
    elif args.chapter:
        plans = [f for f in plans if f.stem == f"ch{args.chapter:02d}"]
    if not plans:
        raise SystemExit(f"반영할 것이 없습니다: {src_dir}")
    print(f"바탕: {src_dir.name}")

    used_new = {n for n in by_n if isinstance(n, int) and n >= NEW_BASE}
    next_new = max(used_new, default=NEW_BASE - 1) + 1

    replaced: set = set()          # 이 씬들은 새 씬으로 갈음된다

    # 앞 단계(다시 쓰기)에서 다른 씬에 합쳐진 원본도 지운다. 배분 결과의
    # from 에는 대표 번호만 남아 있어서, 이걸 안 보면 합쳐진 원본이 그대로
    # 남아 같은 말이 두 번 나온다 — 실제로 씬16·22가 그랬다.
    merged_away: set = set()
    for f_ in sorted(rw_dir.glob("ch*.json")) if rw_dir.exists() else []:
        if args.chapter and f_.stem != f"ch{args.chapter:02d}":
            continue
        for row in json.loads(f_.read_text(encoding="utf-8")).get("scenes", []):
            fr = row.get("from")
            fr = fr if isinstance(fr, list) else [fr]
            fr = [x for x in fr if isinstance(x, int)]
            merged_away.update(fr[1:])
    made: list = []                # (새 씬, 물려받을 그림 항목)
    report: list = []

    for f in plans:
        plan = json.loads(f.read_text(encoding="utf-8"))
        ch = plan.get("chapter")
        for row in plan.get("scenes", []):
            froms = [int(x) for x in (row.get("from") or []) if int(x) in by_n]
            src = by_n.get(froms[0]) if froms else None

            # 번호 — 이 원본을 아직 안 썼으면 그 번호를, 이미 썼으면 새 번호
            if froms and froms[0] not in replaced:
                num = froms[0]
            else:
                num = next_new
                next_new += 1

            turn = row.get("kind") == "turn"
            s = {} if turn else (dict(src) if src else {})
            if turn:
                # 반전 접속사 카드 — 흰 화면에 한 마디, 빠르게 넘어간다.
                # 음성은 넣되 쉼표로 끊는다(「하지만,」). 화면 글자는 쉼표 없이.
                word = row.get("narration", "").strip().rstrip(".,")
                s.update({
                    "narration": word + ",",
                    "headline": word,
                    "title": word,
                    "layout": "turn_card",
                    "isTurnCard": True,
                    "visual_kind": "none",
                    "infoStructure": "scene",
                    "durationSec": 1.2,
                    "imageAsset": {"source": "none"},
                })
            s.update({
                "sceneNumber": num,
                "sceneId": s.get("sceneId") if num == (froms[0] if froms else None)
                else uuid.uuid4().hex[:8],
                "chapter": ch,
                "narration": s.get("narration") if turn else row.get("narration", "").strip(),
                "title": row.get("title", "") or s.get("title", ""),
                "narration_dirty": True,       # 말이 바뀌었으니 음성은 다시
            })
            s.pop("infographic", None)          # 화면 결정은 다시 한다

            # 그림 물려주기
            pool = []
            for fr in ([] if turn else froms):
                e = img_by_n.get(fr)
                if e:
                    pool.extend(e.get("images") or [])
            replaced.update(froms)
            replaced.update(merged_away)
            made.append((s, num, froms, pool))
            report.append((num, froms, len(pool), row.get("title", ""), row.get("note", "")))

    print(f"{ep}  다시 쓴 씬 {len(made)}개")
    for num, froms, npool, title, note in report:
        mark = "그대로" if froms and num == froms[0] else "새 번호"
        print(f"  씬{num:>4} ← {froms or '없음'}  그림 {npool}장  [{mark}] {title}"
              + (f"  ({note[:40]})" if note else ""))

    if not args.apply:
        print("\n--apply 를 붙이면 반영합니다. 그림 파일은 지우지 않습니다.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(spec_f, spec_f.with_suffix(f".json.bak_rewrite_{stamp}"))
    if img_f.exists():
        shutil.copy2(img_f, img_f.with_suffix(f".json.bak_rewrite_{stamp}"))

    # 씬 목록 다시 세우기 — 갈음된 씬은 빼고 새 씬을 그 자리에
    new_scenes = []
    placed = set()
    for s in scenes:
        n = s.get("sceneNumber")
        if n in replaced:
            for ns, num, froms, _pool in made:
                if froms and froms[0] == n and num not in placed:
                    new_scenes.append(ns)
                    placed.add(num)
            # 같은 원본에서 갈라진 나머지 조각도 바로 뒤에
            for ns, num, froms, _pool in made:
                if froms and froms[0] == n and num not in placed:
                    new_scenes.append(ns)
                    placed.add(num)
            continue
        new_scenes.append(s)
    for ns, num, froms, _pool in made:      # 원본이 사라진 경우 대비
        if num not in placed:
            new_scenes.append(ns)
            placed.add(num)

    data["scenes"] = new_scenes
    spec_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 이미지 항목 — 새 번호로 옮긴다. 파일은 그대로 두고 항목만 만든다.
    entries = {e.get("sceneNumber"): e for e in img_db.get("scenes", [])}

    # 한 씬에서 갈라져 나온 조각들이 같은 그림을 그대로 물려받으면 화면이
    # 되풀이된다. 원본에 여러 장이 있으면 **나눠 갖는다.**
    order_of: dict = {}
    for _ns, num, froms, _pool in made:
        key = froms[0] if froms else None
        order_of.setdefault(key, []).append(num)

    for ns, num, froms, pool in made:
        if not pool:
            continue
        seen, imgs = set(), []
        for im in pool:
            if im.get("file") in seen:
                continue
            seen.add(im.get("file"))
            imgs.append(dict(im))

        sibs = order_of.get(froms[0] if froms else None, [num])
        rank = sibs.index(num) if num in sibs else 0
        # 원래 고른 그림을 첫 조각이 갖고, 나머지는 다음 장을 하나씩
        first = next((i for i, x in enumerate(imgs) if x.get("selected")), 0)
        pick = imgs[(first + rank) % len(imgs)]
        for i in imgs:
            i["selected"] = i is pick
        entries[num] = {"sceneNumber": num, "images": imgs,
                        "selected": pick.get("file")}
    img_db["scenes"] = [entries[k] for k in sorted(entries)]
    img_f.parent.mkdir(parents=True, exist_ok=True)
    img_f.write_text(json.dumps(img_db, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n반영했습니다 (백업 .bak_rewrite_{stamp})")
    print(f"  씬 {len(scenes)} → {len(new_scenes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
