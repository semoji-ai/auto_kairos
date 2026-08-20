#!/usr/bin/env python3
"""챕터가 바뀌는 자리에 제목 카드를 넣는다.

말 없이 3초. 챕터 번호와 제목만 뜬다. 긴 편에서는 지금 어디를 지나고 있는지
알려 주는 표지가 있어야 한다 — 없으면 사건이 계속 이어져 어디서 이야기가
바뀌었는지 모른다.

제목은 원고(final_manuscript.md)의 `# Ch1. …` 줄에서 가져온다. 씬에는
챕터 번호만 있고 제목이 없어서다.

**기존 씬 번호는 건드리지 않는다.** 카드에는 900번대 번호를 새로 준다 —
image_assets.json이 번호로 묶여 있어 다시 매기면 그림이 어긋난다. 순서는
배열 순서가 정한다.

    python3 scripts/add_chapter_cards.py            # 보여만 준다
    python3 scripts/add_chapter_cards.py --apply
    python3 scripts/add_chapter_cards.py --apply --ep 1
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402

DURATION = 3.0          # 초 — 읽고 넘어갈 만큼만
CARD_BASE = 900         # 카드 씬 번호는 여기서부터


def chapter_titles(project: Path) -> dict[int, str]:
    """원고에서 `# Ch1. 제목` 을 긁는다."""
    f = project / "final_manuscript.md"
    if not f.exists():
        return {}
    out = {}
    for m in re.finditer(r"^#{1,3}\s*(?:Ch|Chapter|챕터)\s*(\d+)[.:]?\s*(.+)$",
                         f.read_text(encoding="utf-8"), re.M):
        out[int(m.group(1))] = m.group(2).strip()
    return out


def _tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", s or "")}


def suspicious(title: str, narrations: list[str]) -> bool:
    """이 제목이 이 챕터 내용과 맞는가.

    5편의 원고 제목이 옛 판본이라 「1947년 부산, 크림 한 통에서 시작됐다」가
    LG 개명 이야기 위에 붙어 있었다. 낱말이 하나도 겹치지 않으면 의심한다.
    """
    if not title or re.fullmatch(r"Chapter \d+", title.strip()):
        return True
    body = _tokens(" ".join(narrations))
    return not (_tokens(title) & body)


TITLE_PROMPT = """다큐멘터리 한 챕터의 첫 부분입니다. 이 챕터의 **제목**을 지으세요.

{body}

- 한국어로 12자 안팎. 짧을수록 좋습니다.
- 무슨 일이 벌어지는지 드러나야 합니다. 「~에 대하여」처럼 비어 있으면 안 됩니다.
- 결론을 미리 말하지 마세요. 궁금하게 두되 낚지는 않습니다.

제목만 한 줄로 출력하세요. 따옴표도 붙이지 마세요."""


def make_title(narrations: list[str]) -> str:
    """씬을 보고 챕터 제목을 짓는다."""
    import os
    import subprocess

    body = "\n".join(n.strip() for n in narrations if n.strip())[:1200]
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"],
                           input=TITLE_PROMPT.format(body=body),
                           capture_output=True, text=True, timeout=300, env=env)
    except Exception:
        return ""
    line = (r.stdout or "").strip().splitlines()
    return line[-1].strip().strip('"\'' ) if line else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--ep", type=int, default=None, help="한 편만")
    ap.add_argument("--slug", help="시리즈가 아닌 프로젝트 하나에 적용")
    ap.add_argument("--fix-titles", action="store_true",
                    help="원고 제목이 내용과 어긋나면 씬을 보고 새로 짓는다")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    # 시리즈면 지도에서 편을 모두 돌고, 아니면 지정한 프로젝트 하나만 돈다
    f_map = root / "_imggen" / "ep_map.json"
    if f_map.exists() and not args.slug:
        emap = json.loads(f_map.read_text(encoding="utf-8"))
        live = {int(re.match(r"EP(\d+)", k).group(1)): v["dir"] for k, v in emap.items()}
    else:
        d_, _label = resolve_project(args.slug or "")
        live = {1: str(d_)}
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for ep in sorted(live):
        if args.ep and ep != args.ep:
            continue
        d = Path(live[ep])
        f = d / "scene_specs.json"
        data = json.loads(f.read_text(encoding="utf-8"))
        scenes = data.get("scenes", [])
        titles = chapter_titles(d)

        # 이미 넣어 둔 카드가 있으면 다시 넣지 않는다
        has = {s.get("chapter") for s in scenes if s.get("isChapterCard")}

        out, seen, added = [], set(), []
        for s in scenes:
            ch = s.get("chapter")
            if ch is not None and ch not in seen and ch not in has:
                seen.add(ch)
                # 1장은 오프닝(훅·타이틀)이 그 자리를 하므로 카드를 넣지 않는다
                if ch != 1:
                    title = titles.get(ch, "")
                    if args.fix_titles:
                        body = [x.get("narration") or "" for x in scenes
                                if x.get("chapter") == ch][:4]
                        if suspicious(title, body):
                            fresh = make_title(body)
                            if fresh:
                                print(f"   Ch{ch} 제목 새로 지음: 「{title}」 → 「{fresh}」")
                                title = fresh
                    out.append({
                        "sceneNumber": CARD_BASE + ch,
                        "sceneId": uuid.uuid4().hex[:8],
                        "chapter": ch,
                        "isChapterCard": True,
                        "title": f"Ch{ch} 카드",
                        "narration": "",
                        "headline": f"{{{{Chapter {ch}}}}}\n{title}" if title else f"{{{{Chapter {ch}}}}}",
                        "layout": "headline_only",
                        "infoStructure": "scene",
                        "visual_kind": "none",
                        "durationSec": DURATION,
                        "imageAsset": {"source": "none"},
                    })
                    added.append((ch, title))
            elif ch is not None:
                seen.add(ch)
            out.append(s)

        print(f"══ {ep}편  ({len(scenes)}씬)")
        if not added:
            print("   넣을 카드 없음 (이미 있거나 챕터가 하나)")
        for ch, t in added:
            print(f"   Ch{ch}  {t or '(제목 없음 — 원고에서 못 찾음)'}")

        if args.apply and added:
            shutil.copy2(f, f.with_suffix(f".json.bak_chcard_{stamp}"))
            data["scenes"] = out
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"   저장 — {len(scenes)}씬 → {len(out)}씬")

    if not args.apply:
        print("\n--apply 를 붙이면 실제로 넣습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
