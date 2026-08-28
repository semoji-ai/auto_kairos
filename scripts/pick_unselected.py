#!/usr/bin/env python3
"""**고르지 않은 씬**의 여러 판을 열어 보고 그 말을 가장 잘 하는 하나를 고른다.

LG 1편에서 씬 20개가 「그림 없음」으로 보였다. 그런데 그림은 씬당 일곱에서
열두 장씩 이미 있었다. **고른 적이 없었을 뿐이다.**

`image_assets.json` 에 「고른 것」을 적는 칸이 둘이었던 탓이다.

    씬 단위     "selected": "generated/scene_001_gen_07.png"
    이미지 단위  images[].selected = true

`get_selected()` 는 이미지 단위만 본다. 그리고 그것이 옳다 — 씬 단위 칸은
낡아서 110개가 서로 다르고, 씬14 가 씬11 의 그림을, 씬32 가 씬33 의 그림을
가리키고 있었다. 예전에 씬을 재배치하면서 남은 잔재다.

그래서 **씬 단위 칸을 살리지 않는다.** 대신 후보를 직접 열어 보고 새로
고른다. 고르는 잣대는 `check_image_says` 와 같다 — 그림이 그 말을 하는가.

    python3 scripts/pick_unselected.py EP01
    python3 scripts/pick_unselected.py EP01 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

PROMPT = """한 씬에 여러 판의 그림이 있습니다. **그 말을 가장 잘 하는 하나**를 고릅니다.

첨부한 그림 파일을 **Read 로 하나씩 전부 열어 보고** 판단하세요. 파일 이름만
보고 고르면 이 일은 아무 의미가 없습니다.

## 이 씬

  말: {narration}
  앞 씬의 말: {prev}
  뒤 씬의 말: {next}
  화면 계획: {plan}

## 후보

{files}

## 고르는 잣대

```
① 그림이 그 말을 하는가
   말이 실패·부족·두려움인데 그림이 성공·풍족·활기면 고르지 않는다

② 앞뒤와 이어지는가
   같은 사람이 다른 사람으로 보이거나, 때와 곳이 어긋나면 고르지 않는다

③ 뒤 문장이 할 말을 미리 그리지 않았는가
   이 씬이 아직 질문이면 답이 그려진 판은 고르지 않는다

④ 화풍이 시리즈와 같은가
   인물이 사실적이거나 몸 비율이 다른 판은 고르지 않는다
```

**하나는 반드시 고릅니다.** 다 마음에 안 들어도 그중 가장 나은 것을 고르고,
무엇이 아쉬운지 적습니다. 다시 그릴지는 나중에 정합니다.

## 낼 것 — JSON만

{{"pick": "고른 파일 이름 (경로 그대로)",
  "why": "왜 이것인가 한 줄",
  "gap": "그래도 아쉬운 점 (없으면 빈 문자열)",
  "regen": true 또는 false}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--allowedTools", "Read",
                            "--output-format", "text"],
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
    ap.add_argument("--scenes")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected, select_version

    ss = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    order = [s["sceneNumber"] for s in ss]
    by = {s["sceneNumber"]: s for s in ss}
    af = proj / "images" / "image_assets.json"
    assets = {e.get("sceneNumber"): e
              for e in json.loads(af.read_text(encoding="utf-8"))["scenes"]}

    if args.scenes:
        todo = [int(x) for x in args.scenes.split(",")]
    else:
        todo = [n for n in order
                if not by[n].get("isChapterCard") and not by[n].get("isTurnCard")
                and by[n].get("visual_kind") != "infographic"
                and (by[n].get("narration") or "").strip()
                and not get_selected(proj / "images", n)]
    todo = [n for n in todo if (assets.get(n) or {}).get("images")]
    if not todo:
        raise SystemExit("고를 씬이 없습니다")

    print(f"{ep}  고르지 않은 씬 {len(todo)}개")

    def near(n, step):
        i = order.index(n)
        rng = range(i - 1, -1, -1) if step < 0 else range(i + 1, len(order))
        for k in rng:
            t = (by[order[k]].get("narration") or "").strip()
            if t:
                return t[:70]
        return ""

    def run(n):
        e = assets[n]
        files = [i["file"] for i in e.get("images") or []]
        body = "\n".join(f"  - {(proj / 'images' / f).resolve()}" for f in files)
        d = ask(PROMPT.format(
            narration=(by[n].get("narration") or "").strip(),
            prev=near(n, -1), next=near(n, +1),
            plan=((by[n].get("imageAsset") or {}).get("prompt") or "")[:200],
            files=body))
        if not d or not (d.get("pick") or "").strip():
            return n, None
        pick = d["pick"].strip()
        # 절대경로로 답해도 받아들인다
        for f in files:
            if pick.endswith(f) or Path(pick).name == Path(f).name:
                d["pick"] = f
                break
        else:
            return n, None
        return n, d

    picked = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for n, d in ex.map(run, todo):
            if not d:
                print(f"  씬{n:>5}  고르지 못함")
                continue
            picked[n] = d
            mark = " ⟳다시" if d.get("regen") else ""
            print(f"  씬{n:>5}  {Path(d['pick']).name}{mark}  {d.get('why','')[:52]}")
            if (d.get("gap") or "").strip():
                print(f"          아쉬움: {d['gap'][:66]}")

    f = root / "_imggen" / f"{ep}_picks.json"
    f.write_text(json.dumps({"episode": ep, "picks": picked}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"\n{f}")

    if not args.apply:
        print("  --apply 를 붙이면 고른 것을 반영합니다.")
        return 0

    for n, d in picked.items():
        select_version(proj / "images", n, d["pick"])
    print(f"  {len(picked)}개 씬의 그림을 골랐습니다.")
    later = [n for n, d in picked.items() if d.get("regen")]
    if later:
        print(f"  나중에 다시 그릴 씬: {sorted(later)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
