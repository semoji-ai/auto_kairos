#!/usr/bin/env python3
"""상황 씬을 생성한다 — 등장 인물의 캐릭터 시트를 첨부해 얼굴을 고정한다.

씬마다 얼굴이 달라지는 것을 막는 유일한 방법은 시트를 첨부하는 것이다.
텍스트로 인상을 아무리 자세히 써도 매번 재해석된다(인물 시트에서 확인된 사실).

시트는 얼굴·머리·옷의 근거이고, 포즈와 구도는 씬 프롬프트가 정한다.
기존 파일은 지우지 않고 `_v2`, `_v3`로 버전을 올린다(프로젝트 규칙).

    python3 scripts/gen_scenes.py <project_dir> <prompt_dir> -o <out_dir>
    python3 scripts/gen_scenes.py ... --only 7,8,10
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
from auto_agent.utils.image_dedupe import reject_if_duplicate  # noqa: E402

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# 첨부 조합에 따라 지시가 달라진다 (kairos-ai 실증 구조).
# 사람 그림이 둘이면 섞인다 — 캐릭터 시트가 있으면 화풍 기준 시트를 붙이지 않는다.

STYLE_ONLY = """
## 첨부 이미지 — 그림체 기준 (세모지 공식 캐릭터 시트)

{base}

**이 그림을 보고 그대로 따라 그리세요.**

사람을 그릴 때는 **첨부한 그림에 있는 사람과 똑같은 몸으로** 그립니다.
머리 크기, 팔다리 길이, 키에 대한 머리의 비, 손발 크기 — 전부 그림에 있는 그대로입니다.
**말로 설명하지 않겠습니다. 그림을 보고 맞추세요.**

가져오지 말 것은 하나입니다 — **그 사람의 얼굴, 머리 모양, 옷, 성별.**
누구인지만 다르고, 몸과 그리는 방식은 같습니다.

**Match the attached image exactly for how bodies are drawn** — head size relative
to the whole figure, limb length, hand and foot size. Keep them exactly as drawn.
Change only WHO the person is: face, hairstyle, clothing, gender.
"""

CAST_ONLY = """
## 첨부 이미지 — 등장 인물

{sheets}

**생김새·옷차림·표정을 시트에서 가져옵니다.**
- 인물의 생김새, 머리 모양, 옷은 첨부한 시트 그대로입니다
- **자세는 복사하지 마세요.** 시트의 정면으로 선 자세를 그대로 쓰면 안 됩니다
- 자세와 동작은 아래 장면 설명을 따릅니다
- 몸을 그리는 방식은 시트 그대로입니다. 그림을 보고 맞추세요

**시트 아랫줄의 표정 칸을 쓰세요.** 평온·놀람·근심·낙담·기쁨이 그려져
있습니다. 이 장면의 인물이 어떤 마음인지 골라 그 얼굴을 씁니다.

앞서 이것을 「얼굴과 옷차림만 참고」라고 적어 두어, 표정 칸이 있는데도
모든 컷이 평온한 얼굴로 나왔다. 두려움을 말하는 씬이 「사람들이 편안한
평시 장터」로 읽힌 까닭이다.
"""

CASE_LIST = """
**이 화면에 사람은 {count}명입니다. 세어 보고 {count}명이어야 합니다.**

{people}

**{count}명 말고는 아무도 그리지 마세요.** 뒤에 지나가는 사람도, 멀리 선
구경꾼도, 화면 가장자리에 걸친 사람도 넣지 마세요. 화면이 허전해 보여도
사람으로 채우지 않습니다 — 소품과 공간으로 채웁니다.

사람을 늘리면 누가 주인공인지 흐려집니다. 한 명이어야 할 화면에 셋이 나와
누가 그 사람인지 알 수 없게 된 적이 있습니다.

{count}명은 서로 다른 사람입니다. 얼굴형, 머리 모양, 수염, 나이가 각각
다르게 보이도록 그리세요.
"""

PREV_CUT = """
## 첨부 이미지 — 바로 앞 컷 (이어지는 장면입니다)

{prev}

이 컷은 앞 컷에서 **이어집니다.** 같은 세계이고 같은 흐름입니다.

**앞 컷에서 가져올 것**
- 인물의 얼굴·머리 모양·옷차림
- 장소의 생김새와 소품
- 빛의 방향과 색, 시간대
- 그림체와 색감

**바꿀 것 — 여기가 핵심입니다**
- 카메라 자리와 각도를 확실히 옮깁니다. 크기도 한 단계 이상 바꿉니다
- 인물의 자세와 동작은 **이야기가 나아간 만큼 달라집니다.**
  앞 컷을 그대로 다시 그리는 것이 아닙니다

**앞 컷을 복사하지 마세요.** 같은 사람이 같은 곳에 있되, 다음 순간을
다른 자리에서 본 그림입니다.
"""

NO_PEOPLE = """
**이 화면에는 사람이 나오지 않습니다.** 사물·문서·건물·풍경만으로 채웁니다.
빈자리는 소품과 공간으로 메우세요.
"""

PEOPLE_BLOCK = """
**등장 인물 (이대로 그릴 것)**
{people}

**얼굴도 이대로 그립니다.** 옷만 바꾸고 얼굴은 첨부 그림 사람을 쓰면 안 됩니다.
위에 적힌 얼굴형·머리 모양대로, 사람마다 서로 다른 얼굴로 그리세요.
"""
DOC_REF = """
## 첨부 이미지 — 실물 자료 (고증 참조)

{docs}

이 자료는 **화면에 나가지 않습니다.** 보고 그리기 위한 것입니다.
- 건물·설비·병·복식의 **생김새와 구조**를 여기서 가져옵니다
- 사진을 그대로 옮기지 말고, 첨부한 그림체로 다시 그립니다
- 「형태만 참고」라고 적힌 자료는 시대가 다릅니다. 구조만 보고 시대는 장면 설명을 따르세요
"""

BG_REF = """
## 첨부 이미지 — 마스터 컷 (같은 장소)

{first}

첨부 그림은 **이 장소를 정해 둔 마스터**입니다. 베낄 그림이 아닙니다.

**첨부에서 가져올 것 — 세계를 고정합니다**
- 장소의 생김새와 건물, 놓인 소품
- 시간대와 날씨, 빛의 방향과 색
- 그림체와 색감

**무엇을 그릴지는 아래 Scene 이 정합니다.**
이 컷이 하는 말이 앞 컷과 다르면 **화면에 보이는 일도 달라야 합니다.**
사람의 자세와 행동, 손에 든 것, 놓인 물건, 누가 있고 누가 들어오는지가
그 말만큼 나아갑니다. 카메라 자리와 크기는 그 다음에 따라옵니다.

**앵글만 옮긴 같은 그림은 안 됩니다.** 같은 장소에서 **다음 일이 벌어지는**
그림입니다. 첨부 그림을 보고 「무엇이 그대로인가」와 「무엇이 달라졌는가」를
먼저 정한 뒤 그리세요.
"""

REDRAW_REF = """
## 첨부 이미지 — 고쳐 그릴 원래 그림 (구도·내용 참조)

{orig}

이 그림은 **구도와 내용의 참조**입니다. 화면의 짜임, 놓인 사물의 자리, 이야기하는
순간을 여기서 가져옵니다. 그림체는 세모지 기준(평면 색면·외곽선 없는 벡터)으로 그립니다.

**이번에 고칠 것:** {note}
"""

# 사용자 9/30 결함 점검 — 이미 쓰인 그림에서 나온 세 가지를 프롬프트 단계에서 막는다.
REAL_MOMENT = """
**화면은 실제로 있을 수 있는 한 순간입니다.** 바닥은 평평하고 벽·가구·물건은 제 모양
그대로이며, 사건은 사람의 행동과 표정, 손에 든 물건으로 보여 줍니다. 원고가 직접 비유를
말할 때만 그 비유를 그림으로 옮깁니다. 한 사람은 화면에 한 번만 나옵니다.
"""

EV_BATTERY = """
**배터리는 LG 전기차 배터리의 실제 모양으로 그립니다** — 은색 알루미늄 필름으로 감싼
얇고 넓적한 직사각형 파우치형 셀, 그 셀을 여러 장 겹쳐 묶은 직육면체 모듈, 차 바닥 전체에
깔리는 넓고 납작한 판 모양 팩. 첨부한 실물 사진(LG화학 파우치형 셀)의 생김새를 따릅니다.
"""
EV_BATTERY_REF = Path(__file__).resolve().parent.parent / \
    "output/6a20f346_lg_brand_encyclopedia_ep10/images/search/scene_038_search_01.jpg"

EDIT_FIX = """
## 첨부 이미지 — 고칠 그림 (지금 쓰이는 그림)

{cur}

이 그림을 **편집**합니다. 장면·구도·인물 자리·색감은 그대로 두고, 아래 「고칠 곳」만 바꿉니다.

**고칠 곳:** {note}
"""

SCENE = """$imagegen

**첨부한 그림을 먼저 view_image 도구로 불러와 대화 맥락에 넣으세요.**
경로를 읽고 말로 옮기지 마세요 — 그림 자체가 맥락에 있어야 합니다.
(이 단계가 빠져 536컷이 시트를 못 본 채 만들어졌다.)

{prompt}
{ref_block}
size는 {size}입니다.

생성 후 $CODEX_HOME/generated_images/ 의 최신 PNG를 아래로 복사하세요:
{out}
"""


# 한 줄에 여러 사람을 적으면 **세는 수와 그리는 수가 어긋난다.**
# 「인부 둘」은 항목 하나로 세어 「사람은 1명입니다」라고 못 박히는데,
# 같은 프롬프트 본문은 「두 사람」이라 말한다. 모델은 한 명만 그린다 —
# EP01 의 「사람 없음」 모순과 같은 계열이다.
_COUNTED = re.compile(r"(?:^|[\s,·])(둘|셋|넷|다섯|여섯"
                      r"|두 사람|세 사람|네 사람|두 명|세 명|네 명)\s*$")
_COUNT = {"둘": 2, "두 사람": 2, "두 명": 2, "셋": 3, "세 사람": 3, "세 명": 3,
          "넷": 4, "네 사람": 4, "네 명": 4, "다섯": 5, "여섯": 6}
# 수가 없는 무리 — 「상인들」·「아이들」·「사람들」. 몇 명인지 못 박을 수 없다.
# 「줄」은 빼 둔다 — 「사원증 줄」처럼 물건 이름 끝에 붙어 한 사람을 무리로 셌다(EP08 1015).
_CROWD = re.compile(r"(들|무리|행렬)\s*$")


def split_plural(people: list) -> tuple[list, list]:
    """한 줄에 여럿을 담은 항목을 갈라 낸다. (갈라낸 목록, 손댄 자리)

    수가 있으면 그 수만큼 자리를 갈라 적고, 수가 없는 무리는 세지 않는
    배경 사람들로 넘긴다 — 못 박을 수 있는 것만 못 박는다.
    """
    out, touched = [], []
    where = ["왼쪽", "오른쪽", "가운데", "뒤쪽", "앞쪽", "옆"]
    for d in people:
        s = str(d).strip()
        m = _COUNTED.search(s)
        if m:
            n = _COUNT.get(m.group(1))
            base = s[:m.start()].rstrip(" ,·")
            if n and base:
                for i in range(n):
                    tag = where[i] if i < len(where) else str(i + 1)
                    out.append(f"{base} — {tag}에 선 사람")
                touched.append((s, n))
                continue
        if _CROWD.search(s):
            # 통째로 남긴다. 낱말을 떼면 무엇을 그릴지가 사라진다.
            out.append(f"{s} (여럿 — 화면 뒤를 채운다)")
            touched.append((s, 0))
            continue
        out.append(s)
    return out, touched


_made: list = []                 # 이번 판에서 만든 그림 — 병렬 복사 섞임을 잡는다
_made_lock = __import__("threading").Lock()


def next_version(out_dir: Path, n: int) -> Path:
    """기존 파일을 덮어쓰지 않는다 — 이미지 삭제·덮어쓰기 금지 규칙."""
    base = out_dir / f"scene_{n:03d}.png"
    if not base.exists():
        return base
    v = 2
    while (out_dir / f"scene_{n:03d}_v{v}.png").exists():
        v += 1
    return out_dir / f"scene_{n:03d}_v{v}.png"


def latest_version(out_dir: Path, n: int) -> Path | None:
    """그 씬의 가장 최신 판을 돌려준다 — 이어짐 컷이 참조할 그림."""
    cands = sorted(out_dir.glob(f"scene_{n:03d}*.png"))
    return cands[-1] if cands else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("prompt_dir", type=Path)
    ap.add_argument("-o", "--out", required=True, type=Path)
    ap.add_argument("--sheets", type=Path, default=None,
                    help="비우면 paths.get_charsheet_dir() 을 쓴다 — 경로 규칙은 한 곳에만 있다")
    ap.add_argument("--base", type=Path,
                    default=Path("auto_agent/data/artstyle/styles/semoji_character_sheet.png"),
                    help="화풍 기준 시트 — 인물이 없는 씬에도 붙인다")
    ap.add_argument("--roster", type=Path, default=Path("_imggen/characters/roster.json"))
    ap.add_argument("--only", help="쉼표로 구분한 씬 번호")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    ap.add_argument("--emit-jsonl", type=Path, default=None,
                    help="codex 를 부르지 않고 codex-fleet 러너용 jsonl 을 쓴다 "
                         "({id, prompt, ar, size, output_path, refs})")
    ap.add_argument("--emit-id-prefix", default="",
                    help="jsonl id 앞머리 (예: EP01)")
    ap.add_argument("--allow-empty", action="store_true",
                    help="빈 프롬프트도 생성 (장면이 날조되므로 쓰지 말 것)")
    args = ap.parse_args()

    if args.sheets is None:
        from auto_agent.paths import get_charsheet_dir
        args.sheets = get_charsheet_dir() or Path("_imggen/characters/sheets")

    data = json.loads((args.project / "scene_specs.json").read_text(encoding="utf-8"))
    scenes = {s["sceneNumber"]: s for s in data.get("scenes", data)}
    names = {e["id"]: e["name"] for e in json.loads(args.roster.read_text(encoding="utf-8"))}

    # 이어지는 컷은 앞 컷을 레퍼런스로 붙인다. 같은 사람이 같은 곳에 있는데
    # 말로만 설명하면 얼굴도 옷도 빛도 매번 다시 해석된다 — 시트로 얼굴을
    # 고정한 것과 같은 이유다. 그림을 보여 주는 편이 정확하다.
    order = [s.get("sceneNumber") for s in data.get("scenes", data)]
    # 앞 컷은 **그림 컷** 중에서 찾는다. 바로 앞이 도해·글자 카드면 그것을
    # 붙이면 도해가 장면에 섞인다(EP01 1026 이 1024 궤짝 도해를 앞 컷으로 받을 뻔했다).
    prev_of = {}
    for i, n_ in enumerate(order):
        for j in range(i - 1, max(-1, i - 4), -1):
            if scenes.get(order[j], {}).get("visual_kind", "generate_image") == "generate_image":
                prev_of[n_] = order[j]
                break
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from auto_agent.tools.image_assets import get_selected

    def prev_cut(n: int) -> Path | None:
        """앞 컷의 고른 그림. 앞 컷도 아직 안 그렸으면 없다."""
        p = prev_of.get(n)
        if p is None:
            return None
        # 이번 판에서 방금 그린 것을 먼저 본다. 프로젝트에 붙이는 것은 나중이라
        # 여기만 보면 이어지는 컷이 레퍼런스 없이 그려진다 — 씬986 이 그랬다.
        for cand in (args.out / f"scene_{p:03d}.png", args.out / f"scene_{p}.png"):
            if cand.exists():
                return cand.resolve()
        lv = latest_version(args.out, p)
        if lv:
            return lv.resolve()
        sel = get_selected(args.project / "images", p)
        if not sel:
            return None
        f = (args.project / "images" / sel).resolve()
        return f if f.exists() else None
    jobs = json.loads((args.prompt_dir / "jobs.json").read_text(encoding="utf-8"))

    if args.only:
        want = {int(x) for x in args.only.split(",")}
        jobs = [j for j in jobs if j["sceneNumber"] in want]
    # 프롬프트가 빈 씬을 생성에 넘기면 모델이 장면을 지어낸다.
    # EP01 씬 68(클리프행어)이 현대 사무실로 나온 원인이다. 경고가 아니라 막는다.
    empty = [j["sceneNumber"] for j in jobs if "프롬프트 비어 있음" in (j.get("issues") or [])]
    if empty:
        print(f"  ✗ 프롬프트가 빈 씬 {len(empty)}개: {empty}")
        print("    나레이션을 읽고 imageAsset.prompt를 쓴 뒤 다시 실행하세요.")
        print("    (--allow-empty 로 강제할 수 있으나 장면이 날조됩니다)")
        if not args.allow_empty:
            return 2
    args.out.mkdir(parents=True, exist_ok=True)

    import re as _re

    def people_in_prompt(text: str) -> str:
        """프롬프트의 「인물:」 칸에 적힌 사람. 없으면 빈 문자열."""
        m = _re.search(r"인물\s*[:：]\s*([^,\n]+)", text or "")
        if not m:
            return ""
        v = m.group(1).strip()
        # 「인물: 화면은 사물만으로 채운다」 같은 **사람 없음 선언**을 사람으로 세면
        # 「이 화면에 사람은 1명입니다 — 화면은 사물만으로 채운다」가 된다.
        if v in ("없음", "-", "무") or _re.search(r"화면은|채운다|사람 없|사물만", v):
            return ""
        return v

    def run(job: dict) -> tuple[int, bool, str]:
        n = job["sceneNumber"]
        cast = scenes.get(n, {}).get("cast") or []
        lines: list = []
        for cid in cast:
            p = (args.sheets / f"{cid}_sheet.png").resolve()
            if p.exists():
                lines.append(f"- {names.get(cid, cid)}: {p}")
        scene = scenes.get(n, {})
        people = scene.get("people") or []
        people, plural = split_plural(people)
        for src, cnt in plural:
            print(f"    씬{n}: 「{src}」를 {cnt}명으로 갈랐습니다", flush=True)
        body = Path(job["prompt_file"]).read_text(encoding="utf-8")
        # 사람이 있어야 하는가는 **화면을 짤 때 정한 것**(`people`)이 정본이다.
        # 빈 배열이면 정말로 사물만 나오는 화면이니 그대로 「사람 없음」을 붙인다.
        #
        # 그 칸 자체가 없는 옛 씬만 프롬프트의 「인물:」을 읽어 짐작한다. 짐작도
        # 안 하면 한 프롬프트 안에서 말이 엇갈리고 모델은 「사람 없음」을 따른다
        # — 씬986 이 그랬다: 「여인들이 옷에 돈을 썼다」인데 사람이 없었다.
        # people 이 빈 배열이어도 프롬프트 「인물:」 칸에 사람이 적혀 있으면 그 사람을 그린다
        # (image-review-rules: 「사람 없음」은 인물 칸이 실제로 비었을 때만) — EP08 1015 가
        # 「연구원 한 명」 인데 「사람이 나오지 않습니다」를 함께 받을 뻔했다.
        if not people and not lines:
            who = people_in_prompt(body)
            if who:
                people = [who]
        if lines:
            # 캐릭터 시트가 있으면 그것만 붙인다. 화풍 기준 시트를 함께 주면
            # 두 사람 그림이 섞여 정체성이 깨진다.
            ref = CAST_ONLY.format(sheets="\n".join(lines))
        else:
            ref = STYLE_ONLY.format(base=args.base.resolve())
            # 베끼지 말라고만 하면 대신 그릴 것이 없다. 무명 인물이라도
            # 누가 나오는지 적어 주면 시트를 베낄 이유가 사라진다.
            if people:
                ref += PEOPLE_BLOCK.format(
                    people="\n".join(f"- {d}" for d in people))
        # 화면에 누가 몇 명 있는지 못박지 않으면 남는 자리를 같은 얼굴로 채운다.
        # 씬 11에서 어른 둘이 복제된 얼굴로 나왔다 — 시트도 설명도 없는 자리였다.
        # 시트로 붙인 사람을 people 에도 적어 두면 **한 사람이 둘로 센다.**
        # 씬11 은 cast 둘 + people 하나로 3명이 됐고, 화면에도 셋이 나왔다.
        #
        # 더 나아가, **people 에 없는 시트는 아예 붙이지 않는다.** cast 는 그
        # 씬에 관계된 인물을 넓게 적어 둔 것이라, 이 컷에 나오지 않는 사람까지
        # 들어 있다. 붙이면 모델이 「첨부한 사람들」을 다 그린다 — 씬11 은
        # 구인회 한 명짜리 화면인데 구재서 시트가 따라붙어 노인이 하나 더 나왔다.
        # 「사물만」이라고 정한 화면(people 이 빈 배열)에는 시트를 붙이지
        # 않는다. cast 는 그 씬에 관계된 인물을 넓게 적어 둔 것이라 남아
        # 있기 마련인데, 붙이면 모델이 그 사람을 그린다 — 사람이 없어야 할
        # 화면에 한 명이 섰다.
        if isinstance(scene.get("people"), list) and not scene["people"] and not people:
            cast = []
        used, extra = [], list(people)
        for cid in cast:
            # `_up`(키운 판)이 있으면 그것을 쓴다. 다만 **기본 시트보다 낡았으면
            # 쓰지 않는다** — 시트를 다시 만들어도 낡은 `_up` 이 이기면 새 얼굴이
            # 통째로 무시된다. 허만정이 그랬다: 실사진에 맞춰 시트를 새로 만들었는데
            # 8월 12일자 `_up` 이 먼저 붙어 일곱 컷이 다시 백발로 나왔다.
            up = args.sheets / f"{cid}_sheet_up.png"
            base = args.sheets / f"{cid}_sheet.png"
            f_ = up
            if not up.exists():
                f_ = base
            elif base.exists() and base.stat().st_mtime > up.stat().st_mtime:
                print(f"    {cid}: _up 시트가 낡아 기본 시트를 씁니다", flush=True)
                f_ = base
            if not f_.exists():
                continue
            nm = names.get(cid, cid)
            hit = next((d for d in extra if nm and nm in str(d)), None)
            if hit is not None:
                extra.remove(hit)          # 한 사람은 한 번만 센다
                used.append((nm, f_))
            elif not people:
                used.append((nm, f_))      # people 을 안 정한 옛 씬은 그대로
        if people:
            lines = [f"- {nm}: {f_.resolve()}" for nm, f_ in used]
            if lines:
                ref = CAST_ONLY.format(sheets="\n".join(lines))
            else:
                ref = STYLE_ONLY.format(base=args.base.resolve())
                ref += PEOPLE_BLOCK.format(people="\n".join(f"- {d}" for d in extra))
        roster = [f"- {nm} (첨부한 시트의 인물)" for nm, _ in used]
        roster += [f"- {d}" for d in extra if "여럿" not in str(d)]
        crowd = [d for d in extra if "여럿" in str(d)]
        if roster:
            ref += CASE_LIST.format(count=len(roster), people="\n".join(roster))
            if crowd:
                ref += ("\n**그 밖에 화면 뒤를 채우는 사람들이 있습니다.** "
                        "얼굴이 또렷하지 않게, 멀리 작게 그리세요.\n"
                        + "\n".join(f"- {d}" for d in crowd) + "\n")
        elif crowd:
            # 무리만 있는 화면(창단식 무대의 선수단 등) — 「사람 없음」을 붙이면 무리가 지워진다
            ref += ("\n**이 화면의 사람은 멀리 선 무리뿐입니다.** 얼굴이 또렷하지 않게, "
                    "작은 색면 실루엣으로 그리세요.\n" + "\n".join(f"- {d}" for d in crowd) + "\n")
        elif scene.get("people") is None and not people_in_prompt(body):
            # 사람 칸을 정하지 않은 씬(9/20 V카드 재작성 등 — 프롬프트가 줄글)은
            # 「사람 없음」을 붙이지 않는다. 본문이 「직원 두 명이 옮긴다」라고 해도
            # 「사람이 나오지 않습니다」가 이겨 사람이 지워진다(EP11 353).
            ref += ("\n**사람이 나오면 장면 설명에 적힌 사람만, 적힌 수만큼 그립니다.** "
                    "서로 다른 얼굴로 그리고, 한 사람은 화면에 한 번만 나옵니다.\n")
        else:
            # 사람을 안 적으면 모델이 화면을 채우려 사람을 그리고, 정보가 없으니
            # 견본 시트를 베낀다. 아무도 없는 화면이면 그렇다고 못박는다.
            ref += NO_PEOPLE
        # 조사로 확보한 실물 자료 — 건물·설비·병·복식을 보고 그린다.
        # 데이터에만 있고 그림을 안 보여 주면 모델이 지어낸다. 디아지오편에서
        # 병 라벨 숫자가 8·12·15·18 로 나온 것이 이것이 없어서였다.
        docs = []
        for r in ((scene.get("imageAsset") or {}).get("refAssets") or []):
            lp = r.get("local")
            if lp and Path(lp).exists():
                tail = f"  [{r['note']}]" if r.get("note") else ""
                docs.append(f"- {r.get('desc') or r.get('subject') or '실물 자료'}: "
                            f"{Path(lp).resolve()}{tail}")
        # 이 씬 후보로 모아 둔 실물 사진(image_assets 의 search) — 제품·인물의 형태를 맞춘다.
        # 다시 그리는 컷도 실물이 있으면 보고 그린다(사용자 9/30).
        if len(docs) < 4:
            try:
                ia_all = json.loads((args.project / "images" / "image_assets.json").read_text(encoding="utf-8"))
                for e in ia_all.get("scenes", []):
                    if e.get("sceneNumber") != n:
                        continue
                    for im in e.get("images") or []:
                        fp = args.project / "images" / (im.get("file") or "")
                        if im.get("type") == "search" and fp.is_file() and len(docs) < 4:
                            what = im.get("desc") or im.get("caption") or im.get("relevance") or "이 씬의 실물 사진"
                            docs.append(f"- {str(what)[:80]}: {fp.resolve()}  [형태만 참고]")
            except (OSError, ValueError):
                pass
        if docs:
            ref += DOC_REF.format(docs="\n".join(docs[:4]))

        # 같은 장소가 이어지는 컷 — 앞 컷 그림을 붙여 장소를 고정한다.
        # 데이터에 「같은 배경」이라 적혀 있어도 그림을 안 보여 주면 매번 새로
        # 해석된다. 인물을 시트로 잡은 것과 같은 방식이다.
        #
        # **앞 컷 그림은 한 장만 붙인다.** `continuity` 를 쓰는 씬과
        # `is_first_of_background` 를 쓰는 씬이 섞여 있어 둘 다 보되,
        # 둘이 함께 붙으면 모델이 두 장을 섞는다.
        if scene.get("redraw_ref") or scene.get("redraw_method") == "fix":
            pass   # 원래 그림을 고쳐 그리는 컷 — 앞 컷을 함께 붙이면 두 장이 섞인다
        elif (scene.get("imageAsset") or {}).get("continuity") == "continuous":
            p = prev_cut(n)
            if p:
                ref += PREV_CUT.format(prev=p)
        elif lead.get(n):
            first_n = lead[n]
            fp = latest_version(args.out, first_n)
            if fp is None:
                # 마스터 컷이 이번 판 대상이 아니면 프로젝트에서 고른 그림을 쓴다
                sel = get_selected(args.project / "images", first_n)
                cand = (args.project / "images" / sel) if sel else None
                fp = cand if cand and cand.exists() else None
            if fp:
                ref += BG_REF.format(first=f"- 앞 컷(씬 {first_n}): {fp.resolve()}")
        # 다시 그리기 표시에 원래 그림이 걸려 있으면(redraw_ref) 구도·내용 참조로 붙인다.
        rr = scene.get("redraw_ref")
        if rr:
            rp = (args.project / "images" / rr)
            if rp.exists():
                ref += REDRAW_REF.format(orig=f"- 원래 그림: {rp.resolve()}",
                                         note=scene.get("redraw_note") or scene.get("needs_image_reason") or "")
        narr = scene.get("narration") or ""
        if re.search(r"배터리|전지|셀|팩", body + narr) and re.search(r"전기차|자동차|차량|EV|완성차|GM|볼트", body + narr):
            ref += EV_BATTERY + (f"\n- LG화학 파우치형 셀 실물 사진: {EV_BATTERY_REF}  [형태만 참고]\n"
                                 if EV_BATTERY_REF.exists() else "")
        ref += REAL_MOMENT
        # 결함 점검(defect0930)이 「부분 수정」으로 정한 씬 — 지금 그림을 첨부해 고친다.
        # 「새로」로 정한 씬은 지금 그림을 붙이지 않는다(같은 결함이 옮는다).
        if scene.get("redraw_method") == "fix":
            cur = get_selected(args.project / "images", n)
            cp = (args.project / "images" / cur) if cur else None
            if cp and cp.exists():
                ref = EDIT_FIX.format(cur=f"- 지금 그림: {cp.resolve()}",
                                      note=scene.get("redraw_note") or scene.get("needs_image_reason") or "") + ref
        if args.emit_jsonl:
            dep = dep_of(n)
            if dep is not None and dep in want_set and latest_version(args.out, dep) is None:
                return n, None, f"대기 — 앞 그림(씬 {dep})을 먼저 그립니다"
            k = 1
            while (args.out / f"scene_{n:03d}_v{k}.png").exists():
                k += 1
            out = args.out / f"scene_{n:03d}_v{k}.png"
            refs = []
            for m in _re.finditer(r"(/[^\s]+?\.(?:png|jpe?g|webp))", ref):
                if m.group(1) not in refs and Path(m.group(1)).exists():
                    refs.append(m.group(1))
            with _made_lock:
                emitted.append({"id": f"{args.emit_id_prefix}_{n}" if args.emit_id_prefix else str(n),
                                "sceneNumber": n, "prompt": ref.strip() + "\n\n" + body.strip(),
                                "ar": "16:9", "size": job.get("size", "1792x1024"),
                                "output_path": str(out.resolve()), "refs": refs})
            return n, True, out.name
        out = next_version(args.out, n)
        # 생성이 실패하면 codex 가 직전(또는 병렬로 돈 다른 씬의) PNG 를 새 이름으로 복사해 온다.
        # 이 씬의 기존 버전 · 이번 판에 나온 다른 그림과 내용이 같으면 실패로 친다.
        before = sorted(args.out.glob(f"scene_{n:03d}*.png"))
        prompt = SCENE.format(prompt=body, ref_block=ref, size=job.get("size", "1792x1024"), out=out)
        r = subprocess.run(
            ["codex", "exec", "--json", "--skip-git-repo-check", "--sandbox", "workspace-write", prompt],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            # 프롬프트가 길고 참조 그림이 여러 장인 컷은 20분을 넘긴다
            # (디아지오 126씬은 병 4종 라벨 + 잔 4종 + 참조 사진 4장이라 7.5KB).
            timeout=int(os.environ.get('GEN_TIMEOUT', '2400')),
        )
        # 병렬로 돌리면 「generated_images 의 최신 PNG」가 다른 씬의 그림일 수 있다
        # (코리안에어 씬46 자리에 씬7 공항 그림이 들어갔다). 이 세션의
        # thread_id 폴더에서 나온 그림으로 덮어쓴다.
        tid = next((m.group(1) for m in re.finditer(r'"thread_id"\s*:\s*"([^"]+)"', r.stdout or "")), None)
        if tid:
            gdir = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "generated_images" / tid
            own = sorted(gdir.glob("*.png"), key=lambda p: p.stat().st_mtime) if gdir.exists() else []
            if own:
                shutil.copy2(own[-1], out)
            elif out.exists():
                # 이 세션은 그림을 만들지 않았다 — 복사된 것은 남의 그림이다
                out.replace(out.with_suffix(".foreign_rejected.png"))
        if out.exists():
            with _made_lock:
                others = before + list(_made)
                if reject_if_duplicate(out, others):
                    print(f"  ✗ scene {n:>3}  {out.name} — 기존 그림과 내용이 같아 버림(.dup_rejected)", flush=True)
                    return n, False, out.name
                _made.append(out)
        return n, out.exists(), out.name

    # 같은 장소가 이어지는 컷은 앞 컷 그림을 참조해야 한다. 그러려면 그룹의
    # 첫 컷이 먼저 나와 있어야 하므로 두 판으로 나눠 돌린다. 한 번에 병렬로
    # 돌리면 참조할 그림이 아직 없어 같은 장소가 매번 다른 장소로 나온다.
    lead = {}          # 씬번호 → 그 그룹 첫 컷의 씬번호
    cur = None
    for n in order:
        s = scenes[n]
        if s.get("is_first_of_background") is False and cur is not None:
            lead[n] = cur
        else:
            cur = n
    want_set = {j["sceneNumber"] for j in jobs}
    emitted: list = []

    def dep_of(n: int):
        """이 컷이 참조할 앞 그림의 씬 번호 (이어짐 → 앞 컷, 같은 배경 → 마스터)."""
        if scenes.get(n, {}).get("redraw_ref") or scenes.get(n, {}).get("redraw_method") == "fix":
            return None
        if (scenes.get(n, {}).get("imageAsset") or {}).get("continuity") == "continuous":
            return prev_of.get(n)
        return lead.get(n)

    pass1 = [j for j in jobs if j["sceneNumber"] not in lead]
    pass2 = [j for j in jobs if j["sceneNumber"] in lead]

    ok = 0

    def sweep(batch, label):
        nonlocal ok
        if not batch:
            return
        print(f"  ── {label} {len(batch)}컷", flush=True)
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for n, got, name in ex.map(run, batch):
                if got is None:
                    print(f"  … scene {n:>3}  {name}", flush=True)
                    continue
                ok += got
                print(f"  {'✓' if got else '✗'} scene {n:>3}  {name}", flush=True)

    if args.emit_jsonl:
        # jsonl 만 쓴다. 앞 그림이 이번 판에서 새로 그려질 컷은 다음 판으로 미룬다.
        sweep(jobs, "jsonl — 이번 판에 그릴 컷")
        emitted.sort(key=lambda e: e["sceneNumber"])
        args.emit_jsonl.parent.mkdir(parents=True, exist_ok=True)
        args.emit_jsonl.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in emitted),
                                   encoding="utf-8")
        print(f"\njsonl {len(emitted)}줄 → {args.emit_jsonl}  (미룬 컷 {len(jobs) - len(emitted)})")
        return 0
    sweep(pass1, "1판 — 장소를 세우는 컷")
    sweep(pass2, "2판 — 같은 장소의 다른 앵글")

    print(f"\n완료 {ok}/{len(jobs)}  (이어짐 컷 {len(pass2)}개)")
    return 0 if ok == len(jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
