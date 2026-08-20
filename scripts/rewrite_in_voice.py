#!/usr/bin/env python3
"""감독이 고친 씬을 본보기 삼아 나머지 원고를 같은 목소리로 다시 쓴다.

문체를 말로 설명하면 어긋난다. 감독이 실제로 고쳐 놓은 문장을 그대로 보여
주고 「이 목소리로」라고 하는 편이 정확하다.

**씬을 다시 나눠도 된다.** 한 씬에 두 이야기가 들어 있으면 쪼개고, 이어
붙일 뿐인 씬이 연달아 있으면 합친다. 다만 **원래 씬 번호를 함께 적게** 해서
어떤 그림을 물려받을지 알 수 있게 한다.

결과는 제안 파일로 남는다. 바로 덮어쓰지 않는다 — 감독이 보고 정한다.

    python3 scripts/rewrite_in_voice.py EP01 --keep-through 12
    python3 scripts/rewrite_in_voice.py EP01 --chapter 2
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

PROMPT = """다큐멘터리 원고를 **감독의 목소리로** 다시 씁니다.

## 감독이 직접 고쳐 놓은 문장 — 이 목소리입니다

{samples}

## 이 목소리의 특징

읽어 보고 그대로 따르세요. 아래는 눈에 띄는 것들입니다.

- **이야기꾼처럼 엽니다.** 「~가 있었습니다. 그의 이름은 …」처럼 장면을
  세우고 인물을 뒤에 붙입니다.
- **말하듯 잇습니다.** 「~했는데요」, 「~하게 됩니다」, 「~했죠」, 「~거든요」.
- **접속어로 흐름을 만듭니다.** 그러던 중 · 그런데 · 하지만 · 이때 · 게다가 · 당연히.
- **문장을 짧게 끊지 않습니다.** 이어서 말합니다.
- **굵은 표시(**)를 쓰지 않습니다.** 강조는 말로 합니다.
- **메타 서술을 피합니다.** 「여러 기록은 ~고 전합니다」처럼 자료 이야기를
  앞세우지 않습니다. 필요하면 「~라고 전해집니다」 한 마디로 끝냅니다.
- **뒷편과 이어 줍니다.** 「이것이 훗날 LG와 GS의 깊은 관계의 시작이었죠」처럼
  지금 장면이 시리즈 어디로 이어지는지 짚습니다.

## 다시 쓸 원고

{scenes}

## 씬을 다시 나눠도 됩니다

- 한 씬에 두 이야기가 있으면 **쪼갭니다.**
- 이어 붙일 뿐인 씬이 연달아 있으면 **합칩니다.**
- 씬마다 `from` 에 **물려받을 원래 씬 번호**를 적으세요(합쳤으면 여럿).
  그 씬의 그림을 물려받게 됩니다. 새로 그려야 하면 빈 목록으로 두세요.

## 지켜야 할 것

- 사실을 바꾸지 마세요. 수치·이름·연도는 그대로입니다.
- 없는 사실을 만들지 마세요. 원고에 없는 일화를 넣지 않습니다.
- 한자·일본어 문자를 쓰지 않습니다(한글과 영어만).

## 낼 것 — JSON만

{{"scenes": [
  {{"narration": "다시 쓴 나레이션",
    "title": "짧은 씬 제목",
    "from": [원래 씬 번호],
    "note": "쪼갰거나 합쳤으면 왜"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=1800, env=env)
    except Exception as e:
        print(f"  호출 실패: {e}")
        return None
    out = r.stdout or ""
    i, j = out.find("{"), out.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(out[i:j + 1])
    except json.JSONDecodeError as e:
        print(f"  읽지 못함: {e}")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--keep-through", type=int, default=0,
                    help="이 씬까지는 손대지 않는다(감독이 이미 고친 곳)")
    ap.add_argument("--chapter", type=int, help="이 챕터만")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    order = [s.get("sceneNumber") for s in scenes]

    # 본보기 — 감독이 고친 씬(keep-through 안쪽에서 말이 있는 것)
    keep_idx = order.index(args.keep_through) if args.keep_through in order else -1
    samples = [s for s in scenes[:keep_idx + 1]
               if (s.get("narration") or "").strip() and not s.get("isChapterCard")]
    if not samples:
        raise SystemExit("본보기로 쓸 씬이 없습니다 — --keep-through 를 확인하세요")

    todo = [s for s in scenes[keep_idx + 1:]
            if not s.get("isChapterCard") and (s.get("narration") or "").strip()]
    if args.chapter:
        todo = [s for s in todo if s.get("chapter") == args.chapter]
    if not todo:
        raise SystemExit("다시 쓸 씬이 없습니다")

    out_dir = root / "_imggen" / f"{ep.lower()}_rewrite"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 챕터 단위로 나눠 부른다 — 한꺼번에 던지면 뒤로 갈수록 목소리가 흐려진다
    by_ch: dict = {}
    for s in todo:
        by_ch.setdefault(s.get("chapter"), []).append(s)

    for ch, group in sorted(by_ch.items(), key=lambda kv: (kv[0] is None, kv[0])):
        f = out_dir / f"ch{ch:02d}.json"
        if f.exists():
            print(f"챕터{ch}: 이미 있음 — {f.name}")
            continue
        body = "\n\n".join(
            f"[씬{s['sceneNumber']}] {(s.get('narration') or '').strip()}" for s in group)
        d = ask(PROMPT.format(
            samples="\n\n".join(f"[씬{s['sceneNumber']}] {s['narration'].strip()}"
                                for s in samples[-6:]),
            scenes=body))
        if not d or not d.get("scenes"):
            print(f"챕터{ch}: 실패")
            continue
        d["chapter"] = ch
        d["source_scenes"] = [s["sceneNumber"] for s in group]
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"챕터{ch}: {len(group)}씬 → {len(d['scenes'])}씬  ({f.name})")

    print(f"\n→ {out_dir}")
    print("보시고 마음에 들면 apply_rewrite.py 로 반영합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
