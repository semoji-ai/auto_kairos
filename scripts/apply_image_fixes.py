#!/usr/bin/env python3
"""`check_image_says.py` 의 처방을 **프롬프트에 반영한다.**

검사기가 「무엇이 빠졌는지」와 「무엇으로 바꾸는지」를 이미 적어 두었다.
그것을 손으로 옮기면 앞뒤 문장을 안 읽고 쓰게 된다 — 실제로 씬989 도해
제목을 「허만정이 넣은 돈」으로 잘못 붙인 적이 있다. 허만정은 그 시점에
나오지도 않았다.

`wrong` 과 `weak` 은 성격이 다르다.

  wrong  그림이 말과 반대다        화면을 통째로 다시 짠다 (replan_direction)
  weak   한 걸음 모자라다          **요소 하나를 더하거나 시점을 뒤집는다**

           씬973  말 「고향으로 돌아온다」 → 그림은 나가는 방향   (시점)
           씬981  「아버지와 상의한 끝에」 → 아버지가 화면에 없음  (요소)
           씬972  부고인데 종이가 백지라 시험지로도 읽힘          (요소)

weak 은 여기서 고친다. 지금 프롬프트를 살려 두고 빠진 것만 넣는다 —
통째로 다시 쓰면 멀쩡하던 부분까지 흔들린다.

    python3 scripts/apply_image_fixes.py EP01
    python3 scripts/apply_image_fixes.py EP01 --apply
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

WINDOW = 8

PROMPT = """그림이 **한 걸음 모자란** 씬들입니다. 프롬프트에 빠진 것만 넣습니다.

## 씬

{scenes}

## 해야 할 일

**지금 프롬프트를 살려 두고 모자란 것만 더합니다.** 통째로 다시 쓰면
멀쩡하던 부분까지 흔들립니다. 바꾸는 자리는 대개 하나입니다.

```
요소를 더한다   「아버지와 상의한 끝에」인데 아버지가 화면에 없다
                → 인물 줄에 중년의 아버지를 한 줄 더한다

시점을 뒤집는다  「고향으로 돌아온다」인데 집에서 나가는 방향이다
                → 마당에서 대문을 향해 들어오는 시점으로 바꾼다

물건을 바꾼다   부고인데 종이가 완전한 백지라 시험지로도 읽힌다
                → 검은 테두리가 둘린 종이로 바꾼다

표정을 바꾼다   「질서를 거스르는 일」인데 어른들이 온화하다
                → 굳은 입매와 내리깐 눈으로 바꾼다
```

**표정은 `people` 줄 끝에 적습니다.** 캐릭터 시트 아랫줄에 평온·놀람·
근심·낙담·기쁨 다섯이 그려져 있고, 적어 주지 않으면 전부 평온으로
나옵니다.

```
스물넷의 구인회, 흰 무명 저고리에 검정 조끼, 맨눈 — 낙담
```

### 지킬 것

**앞뒤 문장을 읽고 쓰세요.** 이 씬이 아직 질문이면 답을 그리면 안 됩니다 —
다음 씬이 할 말을 미리 써 버립니다.

**앞뒤 컷의 화면과 겹치지 마세요.** 위에 앞뒤 컷이 무엇을 그리고 있는지
적어 두었습니다. 같은 장소·같은 사물·같은 사건을 그리면 두 컷이 같은 말을
두 번 하게 됩니다. 실제로 씬1034와 1056이 둘 다 혼례식이 되었고,
씬1002와 1046이 둘 다 빈 궤짝이 되었습니다.

**부정문을 쓰지 마세요.** 「안경 없이」라고 쓰면 안경이 그려집니다.
빼고 싶은 것은 있는 것으로 바꿔 씁니다.

**화면에 글자를 넣지 마세요.** 글씨는 늘 빈 칸으로 나옵니다.
말을 물건으로 옮기세요 — 부고는 글씨가 아니라 검은 테두리로 읽힙니다.

**구인회의 안경은 나이로 갈립니다.** 마흔 전에는 맨눈입니다.
챕터1 스물넷 · 2 스물아홉 · 3 서른셋~다섯 · 4 서른여덟 · 5 마흔.

프롬프트 형식은 지금 것과 같은 레이어 분리형으로 유지합니다.

## 낼 것 — JSON만

{{"scenes": [
  {{"scene": 씬번호,
    "changed": "무엇을 바꿨는가 한 줄 — 요소 추가 / 시점 뒤집기 / 물건 교체 / 표정",
    "prompt": "고친 프롬프트 전문, 레이어 분리형 …, 16:9",
    "people": ["사람이 바뀌었으면 새 목록, 그대로면 지금 것을 그대로"]}}
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
    ap.add_argument("--report", help="기본: _imggen/<EP>_image_says.json")
    ap.add_argument("--verdict", default="weak", choices=("weak", "wrong", "both"))
    ap.add_argument("--all", action="store_true",
                    help="한 번만 잡힌 weak 까지 전부 — 기본은 확정된 것만")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    by_n = {s.get("sceneNumber"): s for s in data["scenes"]}
    order = [s.get("sceneNumber") for s in data["scenes"]]

    rf = Path(args.report) if args.report else root / "_imggen" / f"{ep}_image_says.json"
    if not rf.exists():
        raise SystemExit(f"검사 결과가 없습니다: {rf}")
    rows = json.loads(rf.read_text(encoding="utf-8")).get("scenes", [])
    want = ("weak", "wrong") if args.verdict == "both" else (args.verdict,)
    todo = [r for r in rows if r.get("verdict") in want and r.get("scene") in by_n]

    # weak 은 한 번 잡혔다고 결함이 아니다. 같은 그림을 다시 봐도 판정이
    # 뒤집히고, 손대지 않은 컷이 다음 회차에 새로 내려앉는다. **같은 갈래로
    # 두 번 연속 잡힌 것만** 고친다 — 이력은 check_image_says 가 쌓는다.
    # wrong 은 지적이 일관되므로 한 번이면 바로 고친다.
    if not args.all:
        hf = root / "_imggen" / f"{ep}_says_history.json"
        try:
            hist = json.loads(hf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            hist = {}
        def confirmed(r):
            # wrong 도 흔들린다. 손대지 않은 컷이 다음 회차에 사라지거나 새로
            # 올라온다 — 전수 세 번에서 겹친 wrong 은 씬21 하나뿐이었다.
            # 그래서 wrong 에도 같은 잣대를 쓴다.
            past = (hist.get(str(r["scene"])) or [])[-2:]
            hits = [p for p in past
                    if p.get("verdict") in ("weak", "wrong")
                    and p.get("tag") == (r.get("tag") or "").strip()]
            return len(hits) >= 2
        kept = [r for r in todo if confirmed(r)]
        if len(kept) != len(todo):
            print(f"  관찰 중 {len(todo) - len(kept)}컷은 건너뜁니다 "
                  f"(아직 한 번만 잡힘 — --all 로 강제)")
        todo = kept
    if not todo:
        raise SystemExit("고칠 씬이 없습니다 (확정된 것 기준)")

    print(f"{ep}  {args.verdict} {len(todo)}컷의 프롬프트를 손봅니다")

    def describe(r):
        n = r["scene"]
        s = by_n[n]
        i = order.index(n)
        prev = next((by_n[order[k]] for k in range(i - 1, -1, -1)
                     if (by_n[order[k]].get("narration") or "").strip()), None)
        nxt = next((by_n[order[k]] for k in range(i + 1, len(order))
                    if (by_n[order[k]].get("narration") or "").strip()), None)
        L = [f"  씬{n} (챕터 {s.get('chapter')})",
             f"    말: {(s.get('narration') or '').strip()}"]
        # 앞뒤의 **말만** 보여 주면 화면이 겹치는 것을 막지 못한다. 씬1034를
        # 고쳤더니 씬1056과 같은 혼례 그림이 됐고, 씬1002를 고쳤더니 씬1046과
        # 빈 궤짝이 겹쳤다 — 둘 다 이 도구가 만든 사고다. 앞뒤 컷이 **무엇을
        # 그리고 있는지**까지 보여 준다.
        for label, o in (("앞", prev), ("뒤", nxt)):
            if not o:
                continue
            L.append(f"    {label}: {(o.get('narration') or '').strip()[:66]}")
            op = ((o.get("imageAsset") or {}).get("prompt") or "").strip()
            if op:
                L.append(f"    {label} 컷의 화면: {op[:200]}")
        L += [f"    지금 그림에 보이는 것: {r.get('seen','')}",
              f"    모자란 것: {r.get('gap','')}",
              f"    검사기의 처방: {r.get('fix','')}",
              f"    지금 프롬프트: {((s.get('imageAsset') or {}).get('prompt') or '')}",
              f"    지금 people: {s.get('people')}"]
        return "\n".join(L)

    def run(chunk):
        return (ask(PROMPT.format(scenes="\n\n".join(describe(r) for r in chunk)))
                or {}).get("scenes") or []

    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    made = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            made.extend(r)

    made = [m for m in made if (m.get("prompt") or "").strip() and m.get("scene") in by_n]
    print(f"\n  손본 씬 {len(made)}")
    for m in made[:8]:
        print(f"    씬{m['scene']}  {m.get('changed','')[:74]}")

    if not args.apply:
        print("\n--apply 를 붙이면 반영합니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_imgfix_{datetime.now():%Y%m%d_%H%M%S}"))
    for m in made:
        s = by_n[m["scene"]]
        if not isinstance(s.get("imageAsset"), dict):
            s["imageAsset"] = {}
        s["imageAsset"]["prompt"] = m["prompt"].strip()
        s["imageAsset"]["source"] = "generate"
        if isinstance(m.get("people"), list) and m["people"]:
            s["people"] = [str(x).strip() for x in m["people"] if str(x).strip()]
        s["needs_image"] = True
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(made)}개 씬을 손봤습니다.")
    print("  다음: build_image_prompts.py → gen_scenes.py → check_image_says.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
