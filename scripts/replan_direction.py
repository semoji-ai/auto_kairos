#!/usr/bin/env python3
"""씬마다 **제 문장으로** 화면을 다시 짠다. 물려받은 프롬프트를 끊는다.

LG 1편이 무너진 경로는 이랬다.

  ① 원고를 다시 쓰고 65씬 → 174씬으로 나눔
  ② 나뉜 조각이 원래 씬의 `imageAsset` 을 통째로 물려받음
  ③ 조각마다 그 프롬프트로 그림을 생성
  ④ 파일 이름은 다른데 그림은 거의 같음

원래 프롬프트는 **합쳐진 문장 전체**를 그린 것이라, 조각 하나에는 너무
많은 것이 들어 있다. 그래서 질문 컷에 답이 이미 그려진다.

  씬20   「보통 첫 실패 뒤에는 물건을 줄이기 마련인데요」
  씬997  「구인회는 반대로 구색을 늘렸습니다」            ← 반전
  둘 다  「…두 선택 사이에서 풍성한 쪽을 고르는 구인회…」

여기서는 **앞뒤를 보여 주되 제 문장만 그리게** 한다. 그리고 편 전체에
거는 규칙 셋을 함께 넣는다 — 이걸 씬마다 따로 판단하게 두면 같은 결과가
다시 나온다.

    python3 scripts/replan_direction.py EP01
    python3 scripts/replan_direction.py EP01 --chapter 1 --apply
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

WINDOW = 12

RULES = """## 이 편 전체에 거는 규칙 셋

**씬마다 따로 판단하지 마세요.** 아래 셋은 편 전체에서 지켜집니다.

### ① 인물은 표식으로 알아본다

얼굴만으로는 구별이 안 됩니다. 사람마다 **반드시 붙는 물건**이 있고,
얼굴이 작게 나오는 컷에서도 그 물건은 크게 보입니다.

```
구인회  나무 자          허만정  둥근 검은테 안경
허준구  감색 조끼        구철회  연회색 저고리에 남색 조끼
```

**구인회의 안경은 나이로 갈립니다.** 마흔 전에는 맨눈입니다.

```
챕터1  1931  스물넷        맨눈
챕터2  1936  스물아홉       맨눈
챕터3  1940~42 서른셋~다섯  맨눈
챕터4  1945  서른여덟       맨눈
챕터5  1947  마흔           가는 은테 안경
```

### ② 같은 장소는 다른 거리로

같은 곳이 여러 번 나오면 **거리를 바꿉니다.** 같은 거리로 되풀이하면
세 번째에서 넘깁니다.

```
① 문 밖에서 넓게        ② 위에서 내려다보며
③ 손과 물건만 아주 가까이  ④ 창이나 문틈 너머로
```

아래 「같은 곳이 이미 몇 번 나왔는지」를 보고 **아직 안 쓴 거리**를 고르세요.

### ③ 돈은 하나의 자로 잰다

금액이 나오면 **같은 나무 궤짝**으로 그립니다. 개수와 높이만 달라집니다.
밑천 2,000원이 궤짝 하나입니다. 매번 다른 그림으로 그리면 앞뒤가 안 맞습니다.
"""

PROMPT = """씬마다 **그 문장이 말하는 것**을 화면으로 짭니다.

{rules}

## 지금 상태

{scenes}

## 해야 할 일

각 씬의 **imageAsset.prompt 를 다시 씁니다.** 지금 프롬프트는 여러 문장을
합쳐 놓았던 시절의 것이라, 조각 하나에는 너무 많은 것이 들어 있습니다.

### 반드시 지킬 것

**앞뒤 문장은 맥락으로만 봅니다. 그리지 않습니다.**
특히 **뒤 문장이 반전이면 그 답을 이 컷에 그리면 안 됩니다.**

```
씬20   「보통 첫 실패 뒤에는 물건을 줄이기 마련인데요」
       → 줄어든 선반만. 구인회가 무엇을 고르는지는 아직 안 보인다
씬997  「구인회는 반대로 구색을 늘렸습니다」
       → 여기서 처음으로 가득 찬 선반이 나온다
```

**같은 묶음(sibling)으로 표시된 씬들은 서로 확실히 다른 화면이어야 합니다.**
장소가 같아도 거리·시점·보이는 사물이 달라야 합니다.

**말이 추상적이면 그 말이 가리키는 사물이나 동작을 찾습니다.**
「자기를 바꾸는 일」이라면 바꾸는 손과 바뀌는 물건이 화면에 있어야 합니다.

### 프롬프트 형식

기존과 같은 레이어 분리형으로 씁니다. 뒤에서 레이어로 갈라 움직이므로
층이 나뉘어야 합니다.

```
레이어 분리형 <무엇의> 일러스트, 배경: …, 중경: …, 인물: …, 전경: …,
<조명 서술>, 문자·로고 없음, 16:9
```

**부정문을 쓰지 마세요.** 「안경 없이」라고 쓰면 안경이 그려집니다.
빼고 싶은 것은 있는 것으로 바꿔 씁니다 — 「눈가가 훤히 드러난 맨눈」.

**화면에 글자를 넣지 마세요.** 현판·간판·장부의 글씨는 늘 빈 칸으로
나옵니다. 말을 물건으로 옮기세요.

**사람이 없어도 되는 화면이면 `people` 을 빈 배열로 둡니다.**
사람이 있으면 **한 줄에 한 사람**, 나이와 차림, 그리고 **표정**을 적습니다.

캐릭터 시트 아랫줄에 평온·놀람·근심·낙담·기쁨 다섯 표정이 그려져
있습니다. 적어 주지 않으면 전부 평온한 얼굴로 나옵니다 — 두려움을
말하는 씬이 「사람들이 편안한 평시 장터」로 읽힌 까닭입니다.

```
스물넷의 구인회, 흰 무명 저고리에 검정 조끼, 맨눈 — 근심
```

### 다시 안 써도 되는 씬

지금 그림이 그 말을 잘 하고 있으면 `keep: true` 로 두고 넘어갑니다.
**바꿀 이유가 없으면 바꾸지 않습니다.**

## 낼 것 — JSON만

{{"scenes": [
  {{"scene": 씬번호,
    "keep": false,
    "shot": "넓게 | 내려다 | 가까이 | 너머로",
    "prompt": "레이어 분리형 …, 16:9",
    "people": ["스물넷의 구인회, 흰 무명 저고리에 검정 조끼, 나무 자를 든 맨눈"],
    "why": "이 화면이 이 말의 무엇을 보이게 하는가 한 줄"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--allowedTools", "Read",
                            "--output-format", "text"],
                           input=prompt, capture_output=True, text=True,
                           timeout=2400, env=env)
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
    ap.add_argument("--scenes")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]
    order = [s.get("sceneNumber") for s in scenes]
    by_n = {s.get("sceneNumber"): s for s in scenes}

    assets = {e["sceneNumber"]: e for e in json.loads(
        (proj / "images" / "image_assets.json").read_text(encoding="utf-8"))["scenes"]}

    # 같은 프롬프트를 나눠 가진 씬끼리 묶어 둔다 — 서로 달라져야 할 짝이다
    import collections
    sib = collections.defaultdict(list)
    for s in scenes:
        p = ((s.get("imageAsset") or {}).get("prompt") or "").strip()
        if p:
            sib[p].append(s["sceneNumber"])
        for i in (assets.get(s["sceneNumber"]) or {}).get("images") or []:
            if i.get("selected") and i.get("prompt"):
                sib[i["prompt"].strip()].append(s["sceneNumber"])
    sibling = {}
    for p, ns in sib.items():
        ns = sorted(set(ns))
        if len(ns) > 1:
            for n in ns:
                sibling[n] = [x for x in ns if x != n]

    todo = [s for s in scenes
            if s.get("visual_kind") in (None, "", "generate_image")
            and not s.get("isChapterCard") and not s.get("isTurnCard")
            and (s.get("narration") or "").strip()]
    if args.chapter is not None:
        todo = [s for s in todo if s.get("chapter") == args.chapter]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")

    print(f"{ep}  씬 {len(todo)}개 · 프롬프트를 나눠 가진 씬 {len(sibling)}개")

    def describe(s):
        n = s["sceneNumber"]
        i = order.index(n)
        prev = next((by_n[order[k]] for k in range(i - 1, -1, -1)
                     if (by_n[order[k]].get("narration") or "").strip()), None)
        nxt = next((by_n[order[k]] for k in range(i + 1, len(order))
                    if (by_n[order[k]].get("narration") or "").strip()), None)
        L = [f"  씬{n}  (챕터 {s.get('chapter')})",
             f"    말: {(s.get('narration') or '').strip()}"]
        if prev:
            L.append(f"    앞: {(prev.get('narration') or '').strip()[:70]}")
        if nxt:
            tag = " ← 반전 카드" if nxt.get("isTurnCard") else ""
            L.append(f"    뒤: {(nxt.get('narration') or '').strip()[:70]}{tag}")
        if sibling.get(n):
            L.append(f"    **같은 프롬프트를 쓰는 씬: {sibling[n]} — 확실히 다른 화면이어야 합니다**")
        cur = (s.get("imageAsset") or {}).get("prompt") or ""
        if cur:
            L.append(f"    지금 프롬프트: {cur[:150]}")
        for im in (assets.get(n) or {}).get("images") or []:
            if im.get("selected"):
                L.append(f"    지금 그림: {(proj / 'images' / im['file']).resolve()}")
        if isinstance(s.get("people"), list):
            L.append(f"    지금 people: {s['people']}")
        return "\n".join(L)

    def run(chunk):
        return (ask(PROMPT.format(rules=RULES,
                                  scenes="\n\n".join(describe(s) for s in chunk)))
                or {}).get("scenes") or []

    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    made = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for rows in ex.map(run, chunks):
            made.extend(rows)

    keep = [r for r in made if r.get("keep")]
    new = [r for r in made if not r.get("keep") and (r.get("prompt") or "").strip()]
    print(f"\n  그대로 두는 씬 {len(keep)} · 다시 쓰는 씬 {len(new)}")
    import collections as _c
    print("  거리 배분:", dict(_c.Counter(r.get("shot", "?") for r in new)))
    for r in new[:6]:
        print(f"\n  씬{r['scene']} [{r.get('shot')}] {r.get('why','')[:70]}")
        print(f"    {r['prompt'][:130]}")

    if not args.apply:
        print("\n--apply 를 붙이면 반영합니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_replan_{datetime.now():%Y%m%d_%H%M%S}"))
    for r in new:
        s = by_n.get(r.get("scene"))
        if s is None:
            continue
        if not isinstance(s.get("imageAsset"), dict):
            s["imageAsset"] = {}
        s["imageAsset"]["prompt"] = r["prompt"].strip()
        s["imageAsset"]["source"] = "generate"
        if isinstance(r.get("people"), list):
            s["people"] = [str(x).strip() for x in r["people"] if str(x).strip()]
        if r.get("shot"):
            s["shot"] = r["shot"]
        # 다시 그려야 하는 씬임을 표시한다 — 옛 그림이 붙은 채 넘어가지 않게
        s["needs_image"] = True
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(new)}개 씬의 화면을 다시 짰습니다.")
    print("  다음: build_image_prompts.py → gen_scenes.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
