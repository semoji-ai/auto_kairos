#!/usr/bin/env python3
"""그린 그림을 **열어 보고** 이 말을 하는지 묻는다.

빠져 있던 고리다. 검사가 둘 있었는데 둘 다 그림을 안 봤다.

  check_prompt_match.py   나레이션 ↔ 프롬프트   글과 글
  check_asset_relevance.py  실물 자료 ↔ 나레이션  생성 이미지는 대상 밖

그래서 **그리고 난 뒤 아무도 묻지 않았다.** LG 1편에서 이런 것들이
그대로 화면에 올라갔다.

  씬993   말 「원하는 색·두께·무늬를 못 내놓았다」  (실패)
          그림 선반 가득한 가게에서 웃으며 천을 펼치는 주인  (성공)
  씬1004  말 「누가 비단을 사겠느냐」  (두려움)
          그림 맑은 하늘, 물건 가득한 좌판, 웃으며 걷는 사람들

프롬프트는 둘 다 정확했다. **그림이 프롬프트를 배신했다.** 원인은
프롬프트의 80%가 화풍 지시였고 그중 비율 블록이 스스로 「이 그림에서 가장
중요한 요구」라고 선언한 데 있다 — 모델은 시킨 대로 화풍을 지키고
이야기를 흘렸다.

고쳐도 또 생긴다. 그래서 **그릴 때마다 묻는 고리**를 둔다.

    python3 scripts/check_image_says.py EP01
    python3 scripts/check_image_says.py EP01 --chapter 1
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

WINDOW = 10

PROMPT = """그린 그림이 **그 말을 하는지** 봅니다.

첨부한 그림 파일을 **Read 로 반드시 열어 보고** 판단하세요. 프롬프트 글만
읽고 답하면 이 검사는 아무 의미가 없습니다 — 프롬프트는 맞는데 그림이
다른 경우를 찾는 것이 이 일의 전부입니다.

## 볼 것

{scenes}

## 판정

씬마다 셋 중 하나입니다.

```
ok      그림이 그 말을 한다
weak    말과 어긋나지는 않지만 그 말의 핵심이 화면에 없다
wrong   그림이 말과 반대이거나 딴 이야기를 한다   ← 반드시 다시 그린다
```

### wrong 으로 볼 것

**말이 실패·부족·두려움인데 그림이 성공·풍족·활기인 경우.**
이것이 가장 흔하고 가장 나쁩니다. 소리를 놓친 사람은 정확히 반대로 읽습니다.

**말이 가리키는 사람이 화면에 없거나 다른 사람인 경우.**
나이·옷·안경이 앞뒤 씬과 어긋나면 다른 사람으로 읽힙니다.

**말이 정한 때와 곳이 그림과 다른 경우.**
1920년대 이야기에 현대식 옷차림이 섞이면 wrong 입니다. 배경의 탈것·
기계·건물도 봅니다 — 1946년 항구에 컨테이너선과 갠트리 크레인이 서
있으면 시대가 통째로 무너집니다.

**표정이 말과 어긋나는 경우.**
캐릭터 시트에 평온·놀람·근심·낙담·기쁨 다섯 표정이 있습니다. 두려움이나
낙담을 말하는데 인물이 평온하게 웃고 있으면 어긋난 것입니다.
다만 얼굴이 아주 작게 나오는 컷에서는 표정을 따지지 않습니다 — 그때는
하늘 색·자세·향하는 방향·비어 있는 자리가 감정을 집니다.

### ok 로 둘 것

그림이 말을 **직접** 그리지 않아도, 그 말이 가리키는 사물이나 상태가
화면에 있으면 ok 입니다. 은유도 통하면 ok 입니다.

## 낼 것 — JSON만

{{"scenes": [
  {{"scene": 씬번호, "verdict": "ok | weak | wrong",
    "seen": "그림에 실제로 보이는 것을 한 줄로",
    "gap": "말과 어긋나는 지점 (ok 면 빈 문자열)",
    "fix": "무엇으로 바꾸면 되는가 — 화면에 보이는 것으로 (ok 면 빈 문자열)"}}
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
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]

    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected

    order = [s.get("sceneNumber") for s in scenes]
    by_n = {s.get("sceneNumber"): s for s in scenes}

    todo = [s for s in scenes
            if s.get("visual_kind") not in ("infographic", "map")
            and not s.get("isChapterCard") and not s.get("isTurnCard")
            and (s.get("narration") or "").strip()]
    if args.chapter is not None:
        todo = [s for s in todo if s.get("chapter") == args.chapter]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want]
    todo = [s for s in todo if get_selected(proj / "images", s["sceneNumber"])]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")

    print(f"{ep}  그림 {len(todo)}장을 말과 견줍니다")

    def describe(s):
        n = s["sceneNumber"]
        i = order.index(n)
        prev = next((by_n[order[k]] for k in range(i - 1, -1, -1)
                     if (by_n[order[k]].get("narration") or "").strip()), None)
        sel = get_selected(proj / "images", n)
        L = [f"  씬{n} (챕터 {s.get('chapter')})",
             f"    말: {(s.get('narration') or '').strip()}"]
        if prev:
            L.append(f"    앞 씬의 말: {(prev.get('narration') or '').strip()[:64]}")
        L.append(f"    그림: {(proj / 'images' / sel).resolve()}")
        return "\n".join(L)

    def run(chunk):
        return (ask(PROMPT.format(scenes="\n\n".join(describe(s) for s in chunk)))
                or {}).get("scenes") or []

    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            rows.extend(r)

    import collections
    c = collections.Counter(r.get("verdict", "?") for r in rows)
    print(f"\n  ok {c['ok']} · weak {c['weak']} · wrong {c['wrong']}   (본 것 {len(rows)})")

    bad = [r for r in rows if r.get("verdict") == "wrong"]
    for r in bad[:15]:
        n = r["scene"]
        print(f"\n  ✗ 씬{n}  {(by_n.get(n, {}).get('narration') or '')[:52]}")
        print(f"      보이는 것: {r.get('seen','')[:88]}")
        print(f"      어긋남: {r.get('gap','')[:88]}")

    f = root / "_imggen" / f"{ep}_image_says.json"
    if f.exists():
        f.replace(f.with_name(f"{f.stem}.prev{f.suffix}"))
    f.write_text(json.dumps({"episode": ep, "scenes": rows}, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"\n{f}")
    print(f"  다시 그릴 씬: {sorted(r['scene'] for r in bad)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
