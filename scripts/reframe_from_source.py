#!/usr/bin/env python3
"""연속 컷은 새로 그리지 않고 **원본을 잘라서** 만든다.

같은 순간을 다른 크기로 보여주는 컷(`continuity: continuous`)을 새로 생성하면
얼굴도 옷도 빛도 미묘하게 달라진다. 그림 모델은 같은 장면을 두 번 똑같이
그리지 못한다. 그러면 이어지는 컷이 아니라 **딴 장면**이 된다.

원본이 이미 있는데 새로 그릴 이유가 없다. 잘라 내면 인물·조명·소품이
저절로 같다. 이것이 실사 촬영에서 와이드를 찍어 두고 클로즈업을 따는 것과
같은 이치다.

  wide    원본 그대로
  medium  가운데 78% 쯤
  close   가리키는 것 둘레 46% 쯤 — 어디를 볼지는 화면을 보고 정한다

    python3 scripts/reframe_from_source.py EP01 --scenes 968,969
    python3 scripts/reframe_from_source.py EP01 --apply
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

RATIO = {"wide": 1.0, "medium": 0.78, "close": 0.46}

PROMPT = """첨부한 그림에서 **어디를 잘라낼지** 정합니다.
Read 도구로 그림을 열어 보세요.

{path}

이 컷이 보여줄 것: {subject}
크기: {size}

원본에서 그 부분이 어디 있는지 보고, 잘라낼 네모의 **가운데**를 백분율로
찍으세요. 화면 왼쪽 위가 (0,0), 오른쪽 아래가 (100,100)입니다.

잘라낼 것이 화면에 없으면 `"found": false` 로 답하세요 — 그때는 새로 그립니다.

{{"found": true, "cx": 50, "cy": 45, "why": "한 마디"}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--allowedTools", "Read", "--output-format", "text"],
                           input=prompt, capture_output=True, text=True, timeout=600, env=env)
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


def crop(src: Path, dst: Path, size: str, cx: float, cy: float) -> bool:
    """가운데를 (cx, cy)에 두고 잘라낸다. 비율은 원본을 따른다."""
    im = Image.open(src).convert("RGB")
    W, H = im.size
    r = RATIO.get(size, 0.78)
    w, h = int(W * r), int(H * r)
    x = int(W * cx / 100) - w // 2
    y = int(H * cy / 100) - h // 2
    x = max(0, min(W - w, x))          # 화면 밖으로 나가지 않게
    y = max(0, min(H - h, y))
    out = im.crop((x, y, x + w, y + h))
    if r < 1.0:                        # 원래 크기로 되돌린다 — 화면이 같아야 한다
        out = out.resize((W, H), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst)
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--scenes")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    by_n = {s.get("sceneNumber"): s for s in data["scenes"]}

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from auto_agent.tools.image_assets import get_selected

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    todo = [s for s in data["scenes"]
            if (s.get("imageAsset") or {}).get("continuity") == "continuous"
            and (not want or s.get("sceneNumber") in want)]

    print(f"{ep}  이어지는 컷 {len(todo)}개")
    if not todo:
        print("  (연속으로 표시된 씬이 없습니다 — replan_split_shots 를 먼저 돌리세요)")
        return 0

    img_dir = proj / "images"
    made = []
    for s in todo:
        n = s["sceneNumber"]
        ia = s.get("imageAsset") or {}
        sel = get_selected(img_dir, n)
        if not sel:
            print(f"  씬{n}: 원본이 없어 건너뜁니다")
            continue
        src = img_dir / sel
        size = ia.get("shot_size", "medium")
        d = ask(PROMPT.format(path=src.resolve(),
                              subject=ia.get("prompt", "")[:120], size=size))
        if not d or not d.get("found"):
            print(f"  씬{n}: 원본에 없어 새로 그려야 합니다")
            continue
        dst = img_dir / "generated" / f"scene_{n:03d}_reframe_{size}.png"
        print(f"  씬{n}: {size}  ({d.get('cx')}, {d.get('cy')})  {d.get('why','')[:40]}")
        if args.apply:
            crop(src, dst, size, float(d.get("cx", 50)), float(d.get("cy", 50)))
            made.append((n, f"generated/{dst.name}"))

    if not args.apply:
        print("\n--apply 를 붙이면 잘라 냅니다. 원본은 그대로 둡니다.")
        return 0

    # 잘라낸 그림을 그 씬의 것으로 등록한다. 원본 파일은 지우지 않는다.
    img_f = img_dir / "image_assets.json"
    db = json.loads(img_f.read_text(encoding="utf-8"))
    ent = {e.get("sceneNumber"): e for e in db.get("scenes", [])}
    for n, rel in made:
        e = ent.setdefault(n, {"sceneNumber": n, "images": []})
        for i in e["images"]:
            i["selected"] = False
        e["images"].append({"file": rel, "type": "reframe", "selected": True})
        e["selected"] = rel
        by_n[n].pop("needs_image", None)
    db["scenes"] = [ent[k] for k in sorted(ent)]
    img_f.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(made)}컷을 원본에서 잘라 냈습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
