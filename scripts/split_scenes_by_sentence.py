#!/usr/bin/env python3
"""원고를 문장 단위로 쪼갠 뒤, 앞뒤를 보고 씬을 배분한다.

지금 씬은 너무 길게 묶여 있다. 한 씬에 서로 다른 장면이 서너 개씩 들어가
있으니 화면이 말을 따라가지 못한다.

그래서 순서를 이렇게 둔다.

  ① 원고를 고친다        rewrite_in_voice.py   (말만)
  ② 문장으로 쪼갠다      여기
  ③ 앞뒤를 보고 붙인다    여기 — 붙일지 따로 갈지 문장마다 정한다
  ④ 그림을 물려준다      apply_rewrite.py

**한 씬 = 한 화면**이다. 화면이 바뀌어야 하면 씬이 바뀐다.

## 나누는 기준

붙인다 — 같은 장면을 이어 말할 때
  · 앞 문장이 벌여 놓은 것을 뒤 문장이 마무리한다 (「~했는데요」 → 결과)
  · 같은 인물이 같은 자리에서 계속 한다
  · 수치 하나를 두 문장이 나눠 설명한다

가른다 — 화면이 달라져야 할 때
  · 때가 바뀐다 (2년 뒤, 그해 여름)
  · 곳이 바뀐다 (서울 → 진주)
  · 주체가 바뀐다 (구인회 → 아버지)
  · 「그런데」·「하지만」 반전이 온다 — 세모지의 뒤집는 자리다
  · 인용이 나온다 — 따옴표는 혼자 둔다
  · 핵심 한 방이다 — 「~이었습니다」로 못 박는 문장은 혼자 둔다

    python3 scripts/split_scenes_by_sentence.py EP01 --from-rewrite
    python3 scripts/split_scenes_by_sentence.py EP01 --chapter 2
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

PROMPT = """다큐멘터리 원고를 **화면 단위로** 나눕니다.

## 문장들

{blocks}

## 기본은 한 문장에 한 화면입니다

문장이 바뀌면 화면도 바뀝니다. **붙이는 것이 예외**입니다.

지금 원고는 한 화면에 서너 문장이 묶여 있어 화면이 말을 따라가지 못합니다.
문장 하나하나가 각자의 그림을 가질 수 있게 떼어 놓으세요.

## 붙이는 경우는 이것뿐입니다

  · 두 문장이 **모두 짧고**(각각 25자 안팎), 한 호흡으로 읽히며 같은 순간을
    말할 때. 「값은 깎아 주지 않았습니다. 대신 자를 속이지 않았죠.」
  · 앞 문장이 **질문**이고 뒤 문장이 곧바로 답할 때.
    「왜였을까요. 손님이 …때문이라고 판단한 겁니다.」

**붙여도 두 문장까지입니다. 셋은 안 됩니다.**
붙인 결과가 **60자를 넘으면 붙이지 마세요.**

수치를 대는 문장, 이유를 대는 문장, 결과를 말하는 문장은 각각 다른 화면입니다.
아래는 **셋으로 갈라야 합니다.**

  「좋은 자리에 앉았다고 장사가 저절로 되는 건 아니었습니다.」
  「개업 첫해 손실은 약 500원.」
  「지금 보면 잔돈처럼 보이지만, 새 가게 밑천을 눈에 띄게 깎아 먹는 큰돈이었습니다.」

## 낼 것 — JSON만

문장 번호로 묶습니다. 모든 문장이 어느 화면엔가 들어가야 합니다.
대부분은 `"blocks": [n]` 처럼 혼자입니다.

{{"scenes": [
  {{"blocks": [1], "title": "짧은 제목", "why": ""}},
  {{"blocks": [2, 3], "title": "짧은 제목", "why": "붙인 이유"}}
]}}
"""



def sentences(text: str) -> list[str]:
    """문장으로 쪼갠다. 따옴표 안의 마침표에 속지 않는다."""
    import re as _re

    t = _re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return []
    out, buf, quote = [], "", False
    for i, ch in enumerate(t):
        buf += ch
        if ch in "“”\"'":
            quote = not quote
        if ch in ".!?" and not quote:
            nxt = t[i + 1] if i + 1 < len(t) else " "
            if nxt == " ":
                out.append(buf.strip())
                buf = ""
    if buf.strip():
        out.append(buf.strip())
    return [s for s in out if s]


# 반전 접속사 — 화면을 뒤집는 자리다. 말에 묻어 두면 그냥 지나가지만,
# 떼어서 흰 화면에 한 마디로 띄우면 그 순간이 보인다.
TURN_WORDS = ("그런데 말입니다", "그런데요", "그런데", "하지만", "그러나", "그때")


def peel_turn(text: str) -> tuple[str, str]:
    """문장 앞머리의 반전 접속사를 떼어 낸다. (접속사, 남은 말)"""
    s = text.strip()
    for w in TURN_WORDS:
        if not s.startswith(w):
            continue
        after = s[len(w):]
        # 뒤에 조사가 붙으면 접속사가 아니다 — 「그때까지는 말입니다」의
        # 「그때」를 떼면 「까지는 말입니다」라는 말이 안 되는 문장이 남는다.
        if not after[:1] in (",", " ", "", "."):
            continue
        rest = after.lstrip(", ").strip()
        if rest:                              # 접속사만 남는 문장은 그대로 둔다
            return w, rest
    return "", s


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=1200, env=env)
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
    ap.add_argument("--from-rewrite", action="store_true",
                    help="다시 쓴 원고(_rewrite)를 쓴다. 없으면 지금 scene_specs")
    ap.add_argument("--keep-through", type=int, default=0)
    ap.add_argument("--scenes", help="이 씬들만 (쉼표로 구분)")
    ap.add_argument("--out", help="결과 파일 이름 (기본 ch<번호>.json)")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    by_n = {s.get("sceneNumber"): s for s in scenes}
    order = [s.get("sceneNumber") for s in scenes]

    # 말은 어디서 가져오나 — 다시 쓴 것이 있으면 그것으로
    text_of: dict = {}
    merged_away: set = set()      # 다른 씬에 합쳐진 원본 — 두 번 넣지 않는다
    rw_dir = root / "_imggen" / f"{ep.lower()}_rewrite"
    if args.from_rewrite and rw_dir.exists():
        for f in rw_dir.glob("ch*.json"):
            for row in json.loads(f.read_text(encoding="utf-8")).get("scenes", []):
                fr = row.get("from")
                fr = fr if isinstance(fr, list) else [fr]
                fr = [x for x in fr if isinstance(x, int)]
                if not fr:
                    continue
                text_of[fr[0]] = row.get("narration", "")
                merged_away.update(fr[1:])   # 합쳐진 나머지는 이미 그 말에 들어 있다

    keep_idx = order.index(args.keep_through) if args.keep_through in order else -1
    targets = [s for s in scenes[keep_idx + 1:]
               if not s.get("isChapterCard")
               and s.get("sceneNumber") not in merged_away
               and (text_of.get(s.get("sceneNumber")) or s.get("narration") or "").strip()]
    if args.chapter:
        targets = [s for s in targets if s.get("chapter") == args.chapter]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        targets = [s for s in targets if s.get("sceneNumber") in want]
    if not targets:
        raise SystemExit("나눌 씬이 없습니다")

    out_dir = root / "_imggen" / f"{ep.lower()}_split"
    out_dir.mkdir(parents=True, exist_ok=True)

    # --out 을 지정하면 챕터를 가르지 않고 한 묶음으로 본다.
    # 안 그러면 챕터마다 같은 파일에 덮어쓰고, 두 번째부터는 「이미 있음」으로
    # 건너뛴다 — 실제로 51씬을 넘겼는데 4문장만 처리됐다.
    by_ch: dict = {}
    if args.out:
        by_ch[targets[0].get("chapter")] = targets
    else:
        for s in targets:
            by_ch.setdefault(s.get("chapter"), []).append(s)

    for ch, group in sorted(by_ch.items(), key=lambda kv: (kv[0] is None, kv[0])):
        f = out_dir / (args.out or f"ch{ch:02d}.json")
        if f.exists():
            print(f"챕터{ch}: 이미 있음")
            continue

        blocks, owner = [], []
        for s in group:
            n = s["sceneNumber"]
            for sent in sentences(text_of.get(n) or s.get("narration") or ""):
                blocks.append(sent)
                owner.append(n)

        listing = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(blocks))
        d = ask(PROMPT.format(blocks=listing))
        if not d or not d.get("scenes"):
            print(f"챕터{ch}: 실패")
            continue

        # 문장 번호 → 말·원본 씬
        made = []
        for row in d["scenes"]:
            idx = [int(x) - 1 for x in row.get("blocks") or []
                   if 0 < int(x) <= len(blocks)]
            if not idx:
                continue
            body = " ".join(blocks[i] for i in idx)
            froms = sorted({owner[i] for i in idx})

            # 반전 접속사는 독립 씬으로 떼어 낸다 — 흰 화면에 한 마디,
            # 빠르게 넘어가고 다음 화면이 이어받는다
            turn, rest = peel_turn(body)
            if turn:
                made.append({
                    "narration": turn + ".",
                    "title": turn,
                    "from": froms,
                    "kind": "turn",
                    "why": "반전 — 흰 화면에 한 마디로 끊는다",
                })
                body = rest

            made.append({
                "narration": body,
                "title": row.get("title", ""),
                "from": froms,
                "why": row.get("why", ""),
            })
        out = {"chapter": ch, "blocks": len(blocks),
               "source_scenes": [s["sceneNumber"] for s in group], "scenes": made}
        f.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"챕터{ch}: {len(group)}씬 · 문장 {len(blocks)}개 → {len(made)}씬")

    print(f"\n→ {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
