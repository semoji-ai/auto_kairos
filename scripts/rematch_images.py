#!/usr/bin/env python3
"""있는 그림을 **실제로 보고** 지금 씬에 다시 붙인다. 한 파일은 한 씬에만.

씬을 다시 나누면서 그림은 물려받기로 메웠다. 그러다 보니 한 장이 여러 씬에
걸쳐 골라져 있다 — 화면이 되풀이된다. 반대로 물려받을 것이 아예 없는 씬도
있다.

물려받은 후보가 지금 씬에 **맞는지는 그림을 봐야 안다.** 원래 다른 말에
붙었던 그림이라 이름만으로는 알 수 없다.

  ① 씬마다 후보를 펼쳐 놓고 그림을 연다
  ② 지금 말과 맞는지 0~100 으로 매긴다
  ③ 점수가 높은 짝부터 붙인다 — **한 파일은 한 씬에만**
  ④ 남은 씬은 새로 그릴 목록으로

**그림 파일은 지우지 않는다.** 어디에 붙일지만 다시 정한다.

    python3 scripts/rematch_images.py EP01 --chapter 1
    python3 scripts/rematch_images.py EP01 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

FIT = 60          # 이 아래는 안 맞는 것으로 본다

PROMPT = """이 화면에 쓸 그림을 고릅니다. **후보를 하나씩 열어 보세요.**
Read 도구로 그림을 여는 것이 이 일의 전부입니다. 열지 않고 짐작하지 마세요.

## 이 화면이 할 말

{narration}

## 이 컷이 보기로 한 것

{subject}
크기: {size}

## 후보

{cands}

## 매기는 법

그림이 **이 말과 같은 장면인가**를 봅니다. 그림이 잘 그려졌는지가 아닙니다.

  90~100  이 말을 위해 그린 것 같다
  70~89   같은 장면이다. 조금 다르지만 쓸 수 있다
  40~69   시대와 분위기만 맞다. 가리키는 것이 다르다
   0~39   다른 장면이다

가리키는 것이 다르면 낮게 매기세요. 「현판을 본다」인데 사람이 앉아 있으면
40점입니다. 대충 맞는 그림을 쓰면 화면이 말을 배신합니다.

크기(wide/medium/close)가 어긋나는 것만으로 크게 깎지는 마세요 — 그건 다시
그릴 이유이지 안 맞는 그림이라는 뜻은 아닙니다. 다만 한 마디 적어 두세요.

## 낼 것 — JSON만

{{"picks": [
  {{"file": "후보 파일 이름 그대로", "fit": 0, "seen": "그림에 보이는 것 한 마디",
    "why": "이 점수인 이유 한 마디"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--allowedTools", "Read", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=1800, env=env)
    except Exception:
        return None
    out = r.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(out[i:j + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    spec_f = proj / "scene_specs.json"
    data = json.loads(spec_f.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    img_dir = proj / "images"
    img_f = img_dir / "image_assets.json"
    db = json.loads(img_f.read_text(encoding="utf-8"))
    ent = {e.get("sceneNumber"): e for e in db.get("scenes", [])}

    # 그림이 필요한 씬만 본다 — 카드와 도해는 그림을 안 쓴다
    todo = [s for s in scenes
            if not s.get("isChapterCard") and not s.get("isTurnCard")
            and s.get("visual_kind") in (None, "", "generate_image")]
    if args.chapter:
        todo = [s for s in todo if s.get("chapter") == args.chapter]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")

    out_dir = root / "_imggen" / f"{ep.lower()}_rematch"
    out_dir.mkdir(parents=True, exist_ok=True)
    tag = f"ch{args.chapter:02d}" if args.chapter else "all"

    # 후보 — 물려받아 들고 있는 그림들. 실제로 파일이 있는 것만.
    cand_of: dict = {}
    for s in todo:
        n = s["sceneNumber"]
        files = []
        for im in (ent.get(n) or {}).get("images") or []:
            f = im.get("file")
            if f and (img_dir / f).exists() and f not in files:
                files.append(f)
        cand_of[n] = files

    empty = [s["sceneNumber"] for s in todo if not cand_of[s["sceneNumber"]]]
    have = [s for s in todo if cand_of[s["sceneNumber"]]]
    print(f"{ep}  그림 쓸 씬 {len(todo)}개 · 후보 있음 {len(have)} · 후보 없음 {len(empty)}")

    def run(s: dict):
        n = s["sceneNumber"]
        ia = s.get("imageAsset") or {}
        cands = cand_of[n]
        listing = "\n".join(f"- {f}\n  {(img_dir / f).resolve()}" for f in cands)
        d = ask(PROMPT.format(
            narration=(s.get("narration") or "").strip()[:200],
            subject=ia.get("prompt", "")[:200] or "(아직 정하지 않음)",
            size=ia.get("shot_size", "") or "(정하지 않음)",
            cands=listing))
        picks = (d or {}).get("picks") or []
        keep = {f for f in cands}
        return n, [p for p in picks if p.get("file") in keep]

    scored: dict = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, picks in ex.map(run, have):
            scored[n] = picks
            best = max((p.get("fit", 0) for p in picks), default=0)
            print(f"  씬{n:>4}  후보 {len(picks)}장  최고 {best}", flush=True)

    # 점수 높은 짝부터 붙인다. 한 파일은 한 씬에만.
    pairs = sorted(((p.get("fit", 0), n, p) for n, ps in scored.items() for p in ps),
                   key=lambda x: -x[0])
    taken_file: set = set()
    taken_scene: dict = {}
    for fit, n, p in pairs:
        if fit < FIT or n in taken_scene or p["file"] in taken_file:
            continue
        taken_scene[n] = p
        taken_file.add(p["file"])

    # 두 번째 바퀴 — 제 원본에서만 후보를 보면 놓치는 것이 많다. 원래 다른
    # 씬에 붙었던 그림이 지금 말에 더 맞을 수 있다. 아직 아무 씬도 가져가지
    # 않은 그림을 남은 씬에 펼쳐 놓고 다시 본다.
    pool = []
    for s in todo:
        for im in (ent.get(s["sceneNumber"]) or {}).get("images") or []:
            f = im.get("file")
            if f and f not in taken_file and f not in pool and (img_dir / f).exists():
                pool.append(f)
    left = [s for s in todo if s["sceneNumber"] not in taken_scene]
    if pool and left:
        print(f"\n두 번째 바퀴 — 남은 씬 {len(left)} · 안 쓰인 그림 {len(pool)}장")

        def run2(s: dict):
            n = s["sceneNumber"]
            ia = s.get("imageAsset") or {}
            cands = [f for f in pool if f not in cand_of[n]][:12]
            if not cands:
                return n, []
            listing = "\n".join(f"- {f}\n  {(img_dir / f).resolve()}" for f in cands)
            d = ask(PROMPT.format(
                narration=(s.get("narration") or "").strip()[:200],
                subject=ia.get("prompt", "")[:200] or "(아직 정하지 않음)",
                size=ia.get("shot_size", "") or "(정하지 않음)",
                cands=listing))
            return n, [p for p in (d or {}).get("picks") or [] if p.get("file") in set(cands)]

        more = []
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for n, picks in ex.map(run2, left):
                more.extend((p.get("fit", 0), n, p) for p in picks)
                print(f"  씬{n:>4}  최고 {max((p.get('fit', 0) for p in picks), default=0)}",
                      flush=True)
        for fit, n, p in sorted(more, key=lambda x: -x[0]):
            if fit < FIT or n in taken_scene or p["file"] in taken_file:
                continue
            taken_scene[n] = p
            taken_file.add(p["file"])

    need = [s["sceneNumber"] for s in todo if s["sceneNumber"] not in taken_scene]
    plan = {"matched": {str(k): v for k, v in taken_scene.items()}, "need_new": need}
    (out_dir / f"{tag}.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n물려줄 씬 {len(taken_scene)} · 새로 그릴 씬 {len(need)}")
    print(f"  (한 파일은 한 씬에만 — 쓰인 파일 {len(taken_file)}장)")
    print(f"→ {out_dir / (tag + '.json')}")
    if not args.apply:
        print("\n--apply 를 붙이면 반영합니다. 그림 파일은 지우지 않습니다.")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(img_f, img_f.with_suffix(f".json.bak_rematch_{stamp}"))
    shutil.copy2(spec_f, spec_f.with_suffix(f".json.bak_rematch_{stamp}"))

    by_n = {s.get("sceneNumber"): s for s in scenes}
    for n in [s["sceneNumber"] for s in todo]:
        e = ent.setdefault(n, {"sceneNumber": n, "images": []})
        pick = taken_scene.get(n)
        # 두 번째 바퀴에서 고른 그림은 **다른 씬의 것**이라 이 씬의 images 에
        # 없다. 그대로 두면 e["selected"] 에 이름만 남고 개별 표시는 하나도
        # 켜지지 않는다 — 정본은 개별 표시(`get_selected`)이므로 그림이
        # 사라진 것처럼 보인다. EP02 에서 20씬이 그랬다.
        if pick and not any(im.get("file") == pick["file"]
                            for im in e.get("images") or []):
            e.setdefault("images", []).append(
                {"file": pick["file"], "type": "generated", "selected": True})
        for im in e.get("images") or []:
            im["selected"] = bool(pick) and im.get("file") == pick["file"]
        e["selected"] = pick["file"] if pick else None
        if pick:
            by_n[n].pop("needs_image", None)
        else:
            by_n[n]["needs_image"] = True

    db["scenes"] = [ent[k] for k in sorted(ent)]
    img_f.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    spec_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n반영했습니다 (백업 .bak_rematch_{stamp})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
