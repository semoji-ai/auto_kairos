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
    ap.add_argument("--drop-missing", action="store_true",
                    help="다시 쓸 때 뺀 씬을 실제로 지운다 (제안 파일에 없는 씬)")
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
                # 씬이 제 챕터를 들고 오면 그것을 쓴다. 묶음의 챕터를
                # 덮어씌우면 여러 챕터를 걸친 묶음에서 원고가 뭉개진다.
                "chapter": row.get("chapter",
                                   (src or {}).get("chapter", ch) if src else ch),
                "narration": s.get("narration") if turn else row.get("narration", "").strip(),
                "title": row.get("title", "") or s.get("title", ""),
                "narration_dirty": True,       # 말이 바뀌었으니 음성은 다시
            })
            s.pop("infographic", None)          # 화면 결정은 다시 한다

            # 길이도 다시 잰다. `dict(src)` 로 원본을 통째로 베끼기 때문에
            # **조각마다 원본의 길이가 그대로 따라붙는다.** 말은 6분의 1로
            # 줄었는데 길이는 25초 그대로인 것이다.
            #
            # EP03에서 실제로 그랬다 — 씬21과 조각 다섯이 각각 25.0초를 들고
            # 있어 합계가 35.3분으로 부풀었고, 채점기가 「빈 사무실 한 장이
            # 25초」로 읽어 지속 점수를 깎았다. 화면이 아니라 눈금이 틀린 것이다.
            #
            # 비워 두면 `rubric_autofill.fill_pacing` 이 TTS 실측으로,
            # 없으면 제 나레이션 길이로 다시 채운다.
            if not turn:
                s.pop("durationSec", None)
                s.pop("estimatedDurationSec", None)
                s.pop("hold", None)

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

    # 제안 파일에서 문장을 지워도 씬은 사라지지 않는다. 원본을 그대로 두기
    # 때문인데, 그러면 「뺐다고 생각한 말」이 화면에 남는다 — 검증 대목 다섯
    # 씬을 뺐는데 일곱 씬이 그대로 있었다.
    dropped: list = []
    if args.drop_missing:
        kept = {n for _ns, n, _fr, _p in made}
        touched = {x for _ns, _n, fr, _p in made for x in fr}
        chapters = {ns.get("chapter") for ns, _n, _fr, _p in made}
        for s in scenes:
            n = s.get("sceneNumber")
            if s.get("isChapterCard") or n in kept or n in touched:
                continue
            if s.get("chapter") in chapters and (s.get("narration") or "").strip():
                dropped.append(n)
        if dropped:
            print(f"  제안에서 빠진 씬 {len(dropped)}개를 지웁니다: {dropped[:12]}")

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
    if args.drop_missing and dropped:
        new_scenes = [s for s in new_scenes if s.get("sceneNumber") not in set(dropped)]
    for ns, num, froms, _pool in made:      # 원본이 사라진 경우 대비
        if num not in placed:
            new_scenes.append(ns)
            placed.add(num)

    data["scenes"] = new_scenes
    spec_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 이미지 항목 — 새 번호로 옮긴다. 파일은 그대로 두고 항목만 만든다.
    entries = {e.get("sceneNumber"): e for e in img_db.get("scenes", [])}

    # 한 씬에서 갈라져 나온 조각들에게 **원본의 후보를 나눠 주지 않는다.**
    #
    # 예전에는 나눠 줬다. 그림이 모자라니 있는 것으로 메운 것이다. 그런데
    # 원본의 후보 여러 장은 **같은 프롬프트로 뽑은 변형**이다. 조각마다
    # 프롬프트를 새로 써 두어도 화면은 같은 그림 여러 장이 된다.
    #
    # EP03에서 실제로 그랬다 — 씬18을 넷으로 가르고 `scene_018_gen_01~04`를
    # 한 장씩 나눠 줬더니, 채점에서 「네 컷이 같은 회의실 정지 그림」으로
    # 지속 점수가 9 → 6 으로 떨어졌다.
    #
    # 그래서 **첫 조각만 원본의 그림을 갖고, 나머지는 비운다.** 빈 자리는
    # 「그려야 함」으로 남아 다음 단계에서 제 프롬프트로 그려진다. 비어 있는
    # 것이 잘못된 그림보다 낫다 — 비면 눈에 띄어 반드시 채우게 된다.
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
        if rank > 0:
            # 갈라져 나온 조각 — 후보는 버리지 않고 얹어 두되 고르지는 않는다
            for i in imgs:
                i["selected"] = False
            entries[num] = {"sceneNumber": num, "images": imgs, "selected": None}
            continue
        first = next((i for i, x in enumerate(imgs) if x.get("selected")), 0)
        pick = imgs[first]
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
