#!/usr/bin/env python3
"""쪼갠 씬마다 화면을 다시 설계한다 — 같은 그림을 나눠 갖지 않도록.

씬을 잘게 나누면 그림이 부족해진다. 물려받기로 메우면 **같은 프롬프트로 뽑은
변형들**이 이웃하게 되고, 카메라도 구도도 똑같아 화면이 멈춘 것처럼 보인다.
실제로 씬11·968·969가 그랬다 — 셋 다 「Medium shot, eye level」이었다.

한 이야기를 여러 컷으로 나눌 때는 **컷마다 크기가 달라야** 한다.

  와이드    상황을 보여준다        어디서 벌어지는 일인가
  미디엄    사람이 무엇을 하는가
  클로즈업  한 가지만 본다         손·글씨·눈·물건

말이 가리키는 것이 다르면 화면도 달라야 한다. 「집안이 공부를 시켰다」는
서안과 붓을 크게 보면 되고, 「할아버지는 홍문관 교리였다」는 현판이나 족보를
보면 된다. 같은 장면을 세 번 보여줄 이유가 없다.

    python3 scripts/replan_split_shots.py EP01 --scenes 11,968,969
    python3 scripts/replan_split_shots.py EP01            # 물려받은 씬 전부
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

PROMPT = """한 장면을 여러 컷으로 나눴습니다. **컷마다 화면을 다르게** 짭니다.

## 원래 화면

{base}

## 이 컷들이 하는 말

{lines}

## 먼저 — 이 컷이 앞 컷에 이어지는가

컷마다 앞 컷과의 관계를 정하세요. 규칙이 정반대입니다.

**`continuous` — 앞 컷에서 이어지는 장면**
  같은 사람이 같은 곳에 있고, 이야기가 그 자리에서 나아갑니다.
  이 컷은 **앞 컷 그림을 레퍼런스로 붙여서** 그립니다. 그러니 얼굴·옷·장소·
  빛·그림체는 저절로 이어집니다. 정할 것은 **무엇이 달라지는가**입니다.

  · 카메라 자리와 각도를 확실히 옮깁니다
  · 크기는 **한 단계 이상** 바꿉니다 (wide → close 는 좋고 medium → medium 은 안 됩니다)
  · **자세와 동작은 이야기가 나아간 만큼 달라집니다.** 앞 컷을 다시 그리는
    것이 아닙니다 — 손을 뻗었다면 이번엔 쥐고 있고, 서 있었다면 앉습니다
  · 다른 인물이 들어오거나 소품이 새로 나와도 됩니다
  · 필요하면 `extra_ref` 에 「무엇을 더 보여 줘야 하는가」를 적으세요
    (예: 「1930년대 진주 포목점 내부」) — 그 그림을 함께 붙입니다

**`new` — 때나 곳이 바뀐다**
  자유롭게 새로 짭니다. 장소·시간·인물이 달라져도 됩니다.
  다만 화풍과 시대는 유지합니다.

말이 「그러던 중」·「그러자」·「2년 뒤」처럼 시간을 옮기면 `new`입니다.
같은 순간을 다른 각도로 말하고 있으면 `continuous`입니다.

## 무엇을 보는가

  wide      상황을 보여준다 — 어디서 벌어지는 일인가
  medium    사람이 무엇을 하는가
  close     한 가지만 본다 — 손·글씨·눈·물건·현판

**말이 가리키는 것을 화면이 봅니다.** 「할아버지는 홍문관 교리였다」면 현판이나
교지를, 「공부를 시켰다」면 서안과 붓을, 「장손이 있었다」면 그 사람을 봅니다.

- 이어지는 컷이 **같은 크기가 되지 않게** 하세요.
- 그릴 것을 **긍정형으로** 적습니다. 「~없음」처럼 빼는 말을 쓰지 마세요.

## 낼 것 — JSON만

{{"shots": [
  {{"scene": 씬번호,
    "link": "continuous | new",
    "size": "wide | medium | close",
    "subject": "이 컷이 보는 것 한 마디",
    "prompt": "배경: … , 중경: … , 인물: … , 전경: … 형식의 한 줄",
    "camera": "예: Close-up, slight high angle, soft window light",
    "extra_ref": "이어지는 컷에 더 붙일 자료가 있으면 한 마디, 없으면 빈 칸"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=600, env=env)
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

    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    # 같은 프롬프트를 나눠 가진 무리를 찾는다 — 그게 쪼개진 흔적이다
    groups: dict = defaultdict(list)
    for s in scenes:
        if s.get("isTurnCard") or s.get("isChapterCard"):
            continue
        p = (s.get("imageAsset") or {}).get("prompt") or ""
        if p.strip():
            groups[p].append(s)

    want = {int(x) for x in args.scenes.split(",")} if args.scenes else None
    todo = []
    for p, group in groups.items():
        if len(group) < 2:
            continue
        if want and not any(s["sceneNumber"] in want for s in group):
            continue
        todo.append((p, group))

    print(f"{ep}  같은 화면을 나눠 가진 무리 {len(todo)}개")
    if not todo:
        return 0

    def run(job):
        base, group = job
        lines = "\n".join(
            f"  씬{s['sceneNumber']}: {(s.get('narration') or '').strip()[:90]}"
            for s in group)
        d = ask(PROMPT.format(base=base[:400], lines=lines))
        if not d or not d.get("shots"):
            return group[0]["sceneNumber"], "실패", []
        return group[0]["sceneNumber"], f"{len(d['shots'])}컷", d["shots"]

    made = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for head, msg, shots in ex.map(run, todo):
            sizes = " · ".join(
                f"{s.get('scene')}={s.get('size')}"
                f"{'↩' if s.get('link') == 'continuous' else ''}" for s in shots)
            print(f"  {head:>4} 무리  {msg}  {sizes}")
            made.extend(shots)

    if not args.apply:
        print("\n--apply 를 붙이면 프롬프트를 바꿉니다. 그림은 따로 생성해야 합니다.")
        return 0

    by_n = {s.get("sceneNumber"): s for s in scenes}
    hit = 0
    for sh in made:
        s = by_n.get(sh.get("scene"))
        if not s:
            continue
        ia = s.get("imageAsset")
        if not isinstance(ia, dict):
            ia = {}
            s["imageAsset"] = ia
        ia["source"] = "generate"
        ia["prompt"] = sh.get("prompt", "")
        ia["camera"] = sh.get("camera", "")
        ia["shot_size"] = sh.get("size", "")
        ia["continuity"] = sh.get("link", "new")
        if (sh.get("extra_ref") or "").strip():
            ia["extra_ref"] = sh["extra_ref"].strip()
        s["needs_image"] = True          # 새로 그려야 한다
        hit += 1

    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{hit}개 씬의 화면을 새로 짰습니다. 이제 그림을 생성하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
