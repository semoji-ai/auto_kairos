#!/usr/bin/env python3
"""**시청자 셋에게 편을 보여 주고** 어디서 빠져나가는지 듣는다.

만든 사람은 자기 편을 처음 보는 눈으로 못 본다. 무엇을 그렸는지 알고
있으니 화면이 설명하지 않아도 알아본다. 그래서 **아무것도 모르는 눈**이
필요하다.

세 사람은 서로 다른 것을 본다. 한 사람만 두면 그 사람이 놓치는 것을
아무도 못 잡는다.

  김상현  숫자와 인과를 따진다. 「왜 그렇게 됐는지」가 화면에 없으면 멈춘다
  박영자  다른 일을 하며 듣는다. 말을 놓쳐도 그림만으로 뜻이 잡혀야 한다
  이지우  짧은 영상에 익숙하다. 화면이 심심해지면 그 자리에서 넘긴다

넷을 매긴다. **모두 높을수록 좋다.**

  이해도    화면이 말을 설명하는가
  흐름      앞뒤가 이어지는가
  몰입      계속 보게 되는가
  오해소지  틀리게 읽힐 자리가 없는가   ← 높을수록 안전하다는 뜻

    python3 scripts/viewer_eval.py EP01
    python3 scripts/viewer_eval.py EP01 --chapter 3
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

WINDOW = 22

PERSONAS = """## 보는 사람 셋

셋 다 이 회사도 이 인물도 모릅니다. **화면과 말만 보고 판단합니다.**

  김상현  마흔둘, 중소기업 운영. 숫자와 인과를 따집니다.
          「왜 그렇게 됐는지」가 화면에 없으면 납득하지 않습니다.
  박영자  쉰여섯. 설거지하며 소리로 듣다가 이따금 화면을 봅니다.
          말을 놓친 채 화면만 봐도 뜻이 잡혀야 합니다.
  이지우  스물넷. 짧은 영상에 익숙합니다.
          화면이 심심해지는 순간 넘깁니다. 참아 주지 않습니다.
"""

PROMPT = """{personas}

## 이 편의 장면들

첨부한 그림 파일을 **Read 로 직접 열어 보고** 판단하세요. 파일을 열지
않고 프롬프트 글만 읽고 판단하면 안 됩니다 — 실제로 그려진 것과 적어 둔
것이 다른 경우를 찾는 것이 이 일의 핵심입니다.

{scenes}

## 물을 것

각 씬마다 셋의 눈으로 봅니다.

  이 화면이 이 말을 설명하는가        아니면 그냥 옆에 있는가
  앞 씬에서 이어지는가                사람이 갑자기 딴사람이 되지 않는가
  여기서 넘기고 싶어지는가            이지우가 특히 예민합니다
  틀리게 읽힐 자리가 있는가           연도·인물·인과가 뒤바뀌어 보이는가

**인물이 같은 사람으로 이어지는지 특히 봅니다.** 나이·안경·옷·머리색이
같은 구간 안에서 달라지면 다른 사람으로 읽힙니다.

## 낼 것 — JSON만

{{"scores": {{"이해도": 0-100, "흐름": 0-100, "몰입": 0-100, "오해소지": 0-100}},
 "skip_scenes": [넘기고 싶어진 씬번호],
 "unclear_scenes": [화면이 말을 설명하지 못하는 씬번호],
 "identity_issues": ["인물이 끊기는 자리를 한 줄씩"],
 "best_scenes": [{{"n": 씬번호, "why": "왜 좋은가"}}],
 "notes": "이 구간에서 가장 크게 걸린 것 한두 가지"}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(
            ["claude", "--allowedTools", "Read", "--output-format", "text"],
            input=prompt, capture_output=True, text=True, timeout=2400, env=env)
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


def describe(s: dict, proj: Path, root: Path, sel: str | None) -> str:
    """한 씬을 시청자가 볼 수 있는 형태로 적는다."""
    n = s.get("sceneNumber")
    head = f"  씬{n}"
    if s.get("isChapterCard"):
        return f"{head}  [챕터 카드] {(s.get('narration') or '').strip()[:40]}"
    if s.get("isTurnCard"):
        return f"{head}  [반전 카드] {(s.get('narration') or '').strip()[:40]}"
    lines = [f"{head}  말: {(s.get('narration') or '').strip()}"]
    kind = s.get("visual_kind")
    if kind == "infographic":
        g = s.get("infographic") or {}
        # 도해는 Remotion 이 명세로 직접 그린다 — 그림 파일이 아니라 명세를 준다
        el = " · ".join(f"{i.get('label') or i.get('id')}" for i in g.get("items") or [])
        mk = " ".join(m.get("text", "") for m in g.get("marks") or [])
        lines.append(f"      화면: [도해] 제목「{g.get('title','')}」 요소: {el}"
                     + (f" 기호: {mk}" if mk.strip() else ""))
        png = root / "_imggen" / f"{proj.name.split('_',1)[0]}_render"
        # 검수용 미리보기가 있으면 그것을 보게 한다
        prev = root / "_imggen" / f"{s.get('_ep','')}_render" / f"s{n:03d}.png"
        if prev.exists():
            lines.append(f"      미리보기: {prev}")
    elif sel:
        lines.append(f"      화면: {(proj / 'images' / sel).resolve()}")
    else:
        lines.append("      화면: (아직 없음)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--chapter", type=int, help="이 챕터만")
    ap.add_argument("--scenes", help="이 씬만 (쉼표로 구분)")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    ap.add_argument("-o", "--out", help="결과 JSON 경로")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    scenes = json.loads((proj / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]

    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected

    todo = list(scenes)
    if args.chapter is not None:
        todo = [s for s in todo if s.get("chapter") == args.chapter]
    if args.scenes:
        want = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")

    for s in todo:
        s["_ep"] = ep.lower()

    print(f"{ep}  씬 {len(todo)}개를 시청자 셋에게 보입니다")

    def run(chunk):
        body = "\n".join(
            describe(s, proj, root, get_selected(proj / "images", s["sceneNumber"]))
            for s in chunk)
        return ask(PROMPT.format(personas=PERSONAS, scenes=body))

    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    rows = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            if r:
                rows.append(r)

    if not rows:
        raise SystemExit("평가를 받지 못했습니다")

    keys = ("이해도", "흐름", "몰입", "오해소지")
    scores = {k: round(sum((r.get("scores") or {}).get(k, 0) for r in rows) / len(rows))
              for k in keys}
    out = {
        "episode": ep,
        "scenes": len(todo),
        "scores": scores,
        "total": round(sum(scores.values()) / len(keys)),
        "skip_scenes": sorted({n for r in rows for n in r.get("skip_scenes") or []}),
        "unclear_scenes": sorted({n for r in rows for n in r.get("unclear_scenes") or []}),
        "identity_issues": [x for r in rows for x in r.get("identity_issues") or []],
        "best_scenes": [x for r in rows for x in r.get("best_scenes") or []],
        "notes": [r.get("notes", "") for r in rows if r.get("notes")],
    }
    f = Path(args.out) if args.out else root / "_imggen" / f"{ep}_viewer.json"
    # 지난 평가를 덮지 않는다 — 점수가 오르내린 자취가 남아야 무엇이 통했는지 안다
    if f.exists():
        prev = f.with_name(f"{f.stem}.prev{f.suffix}")
        f.replace(prev)
        print(f"  지난 평가는 {prev.name} 로 옮겼습니다")
    f.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n  {'  '.join(f'{k} {scores[k]}' for k in keys)}   →  총점 {out['total']}")
    print(f"  넘기고 싶어진 씬 {len(out['skip_scenes'])}  "
          f"화면이 말을 못 받는 씬 {len(out['unclear_scenes'])}  "
          f"인물 끊김 {len(out['identity_issues'])}")
    print(f"\n{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
