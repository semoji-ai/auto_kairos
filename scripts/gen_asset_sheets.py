#!/usr/bin/env python3
"""소품 시트·장소 마스터를 세모지 그림체로 그린다 — 씬 생성의 고증 참조용.

인물 시트(`gen_character_sheets.py`)와 같은 원리다. **그림체는 말로 쓰지 않고**
세모지 기준 시트를 첨부해 보여 주고, **생김새는 실물 사진**을 첨부해 보여 준다.
씬마다 실물 사진을 직접 붙이면 사진의 사실성이 딸려 와 화풍이 깨진다
(character-sheet-rules 3-1절). 한 번 세모지로 옮겨 그린 시트를 씬에 붙이면
생김새와 화풍을 함께 고정할 수 있다.

    prop      같은 물건을 정면·측면·위에서 본 모습 + 세부 한 칸 (1536x1024)
    lineup    여러 대상을 같은 바닥선에 순서대로 나란히 (1792x1024)
    location  사람 자리를 비워 둔 와이드 전경 한 장 (1792x1024)

입력 JSON 항목:
    {"id": "jeep_1946", "kind": "prop", "name": "미군 윌리스 지프",
     "era": "1946", "desc": "생김새 서술", "refs": ["경로", ...],
     "note": "그릴 때 주의", "text": "넣을 글자(선택)"}

기존 파일은 덮어쓰지 않고 `_v2`, `_v3` 으로 버전을 올린다(이미지 삭제 금지 규칙).

    python3 scripts/gen_asset_sheets.py <assets.json> -o <out_dir> [--only a,b] [-j 3]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.utils.codex_cli import claim_session_image, imagegen_model_args  # noqa: E402

HEAD = """$imagegen

**첨부한 그림을 먼저 view_image 도구로 불러와 대화 맥락에 넣으세요.**
경로를 읽고 말로 옮기지 말고, 그림 자체를 보고 그립니다.

첨부 이미지
{attach}

1번은 세모지 기준 캐릭터 시트입니다. **그림체만** 이 그림에서 가져옵니다 —
형태를 색면과 색면이 맞닿는 경계로만 만드는 방식, 같은 색의 한 단계 어두운
색면 하나로 넣는 그림자, 고르게 매끈한 색면, 또렷한 명도 대비.
{photo_line}
"""

PROP = """{head}
{name}({era})의 에셋 시트를 1번 그림체로 그려줘.

생김새: {desc}

레이아웃 — 밝은 아이보리 단색 바탕 위에 같은 물건을 네 칸으로 보여 줍니다.
왼쪽부터 정면, 측면, 비스듬히 위에서 본 모습, 그리고 오른쪽 끝에 세부를 크게
확대한 한 칸. 네 칸 모두 같은 물건이고 크기·색·비례가 서로 같습니다.
화면에는 이 물건만 놓습니다.
{note}{text}
size는 1536x1024입니다.

생성 후 이번 세션에서 만든 그림을 아래로 복사하세요:
{out}
"""

LINEUP = """{head}
{name}({era})의 라인업 시트를 1번 그림체로 그려줘.

여러 대상을 **같은 바닥선 위에 왼쪽부터 순서대로** 나란히 세운 한 장입니다.
각 대상의 생김새는 첨부한 실물 사진을 따르고, 서로 알아볼 수 있게 형태·색·층
구성을 또렷하게 가릅니다.

순서와 생김새: {desc}

밝은 아이보리 단색 바탕 위에 대상들만 놓습니다. 대상 사이에는 넉넉한 간격을 둡니다.
{note}{text}
size는 1792x1024입니다.

생성 후 이번 세션에서 만든 그림을 아래로 복사하세요:
{out}
"""

LOCATION = """{head}
{name}({era})의 장소 마스터 컷을 1번 그림체로 그려줘.

이 장소를 처음 보여 주는 와이드 전경 한 장입니다. 뒤에 오는 여러 씬이 이
그림을 보고 같은 장소를 그리므로, 건물의 생김새·재질·색, 놓인 설비와 소품,
공간의 구조가 한눈에 읽혀야 합니다.

생김새: {desc}

화면은 배경·중경·전경이 층으로 겹치고, 사람이 들어설 빈자리가 중경에
넉넉히 열려 있습니다. 화면에는 건물·풍경·설비·소품만 놓습니다.
{note}{text}
size는 1792x1024입니다.

생성 후 이번 세션에서 만든 그림을 아래로 복사하세요:
{out}
"""


def next_version(out_dir: Path, aid: str) -> Path:
    base = out_dir / f"{aid}.png"
    if not base.exists():
        return base
    v = 2
    while (out_dir / f"{aid}_v{v}.png").exists():
        v += 1
    return out_dir / f"{aid}_v{v}.png"


def build(e: dict, base: Path, root: Path, out: Path) -> str:
    refs = [(root / r).resolve() for r in e.get("refs") or []]
    # 라인업은 대상마다 사진이 하나씩 필요하다 — 다섯까지 붙인다
    refs = [r for r in refs if r.exists()][:5 if e.get("kind") == "lineup" else 3]
    attach = [f"1번: {base}"] + [f"{i + 2}번: {r}" for i, r in enumerate(refs)]
    photo_line = ""
    if refs:
        photo_line = ("2번 이후는 실물 사진입니다. **생김새만** 여기서 가져옵니다 — "
                      "형태, 구조, 비례, 부품의 배치, 재질과 색. 사진의 명암과 질감은 "
                      "옮기지 말고 1번의 그림체로 다시 그립니다.\n")
    head = HEAD.format(attach="\n".join(attach), photo_line=photo_line)
    note = f"\n{e['note']}\n" if e.get("note") else ""
    text = (f"\n글자는 「{e['text']}」만 획이 또렷한 한글로 넣고, 그 밖의 면은 "
            "매끈한 빈 색면으로 둡니다.\n") if e.get("text") else (
            "\n표면은 매끈한 색면으로 두고 글자 대신 색과 형태로 구분합니다.\n")
    tpl = {"prop": PROP, "lineup": LINEUP}.get(e.get("kind"), LOCATION)
    return tpl.format(head=head, name=e["name"], era=e.get("era", ""),
                      desc=e.get("desc", ""), note=note, text=text, out=out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("assets", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--base", type=Path,
                    default=Path("auto_agent/data/artstyle/styles/semoji_character_sheet.png"))
    ap.add_argument("--only", help="쉼표로 구분한 id")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    entries = json.loads(args.assets.read_text(encoding="utf-8"))
    if args.only:
        want = {x.strip() for x in args.only.split(",") if x.strip()}
        entries = [e for e in entries if e["id"] in want]
    args.out.mkdir(parents=True, exist_ok=True)
    base = args.base.resolve()
    # refs 경로는 저장소 뿌리 기준이다
    root = Path(__file__).resolve().parent.parent

    def run(e: dict) -> tuple[str, bool, str]:
        out = next_version(args.out, e["id"]).resolve()
        prompt = build(e, base, root, out)
        try:
            res = subprocess.run(["codex", "exec", *imagegen_model_args(), "--skip-git-repo-check",
                                  "--sandbox", "workspace-write", prompt],
                                 stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                 timeout=args.timeout)
            # 병렬로 돌면 codex 가 남의 「최신 PNG」를 집어 온다 — 세션 폴더가 정본
            claim_session_image((res.stdout or "") + (res.stderr or ""), out)
        except subprocess.TimeoutExpired:
            pass
        return e["id"], out.exists(), out.name

    ok = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for aid, got, name in ex.map(run, entries):
            ok += got
            print(f"  {'✓' if got else '✗'} {aid:<28} {name}", flush=True)
    print(f"\n완료 {ok}/{len(entries)}")
    return 0 if ok == len(entries) else 1


if __name__ == "__main__":
    sys.exit(main())
