#!/usr/bin/env python3
"""원고를 처음부터 훑으며 **씬마다 화면을 정한다.**

원고를 다시 쓰고 문장 단위로 나누면, 앞서 정해 둔 화면 판단은 전부 헐거워진다.
씬 경계가 달라졌으니 「이 씬을 무엇으로 보여줄까」의 전제가 바뀐 것이다.
실제로 EP01은 113씬이 같은 프롬프트를 나눠 갖고 있었고, 컷 관계는 하나도
정해져 있지 않았다.

**한 번에 정한다.** 화면 종류를 따로 정하고 컷을 따로 짜면, 도해로 갈 씬에도
컷을 짜고 사람이 이어지는 구간을 도해가 끊는다. 둘은 같은 판단이다.

  ① 이 씬을 무엇으로 보여줄까   재연 · 도해 · 실물 자료 · 지도
  ② 재연이면 앞 컷과 어떤 사이인가   이어짐 · 새 장면
  ③ 무엇을 어느 크기로 보는가        wide · medium · close

앞뒤를 보고 정해야 하므로 **순서대로 창을 밀며** 본다. 앞 몇 씬은 읽기만 하고
판단하지 않는다 — 흐름을 알아야 이어짐인지 알 수 있기 때문이다.

판단 기준은 `docs/rules/scene-visual-decision.md` 가 정본이다.

    python3 scripts/plan_screens.py EP01 --chapter 1
    python3 scripts/plan_screens.py EP01 --apply
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

WINDOW = 12          # 한 번에 판단하는 씬 수
LOOKBACK = 4         # 앞 흐름을 읽기만 하는 씬 수

PROMPT = """다큐멘터리의 한 대목입니다. **씬마다 화면을 정합니다.**

## 앞의 흐름 (읽기만 하세요, 판단하지 않습니다)

{before}

## 정할 씬

이 씬들은 **아직 그림이 없습니다.** 있는 그림에 맞추지 마세요 — 무엇으로
보여줄지 처음부터 정합니다. 실물 사진·문서가 있어야 믿기는 자리면 `archive`,
도해만 할 수 있는 일이면 `infographic` 입니다.

{scenes}

---

# 첫째 — 무엇으로 보여줄까

**도해는 예외입니다.** 같은 편에서 35씬을 도해로 돌렸다가 실제로 그려 견줘
보니 5씬만 맞았습니다.

|  | 도해 | 씬 그림 |
|---|---|---|
| 알아듣는가 | 22 | 8 |
| **보고 싶은가** | 5 | **25** |

이해는 도해가 빠릅니다. 그런데 **보고 싶지가 않습니다.** 도해가 이어지면
사람이 사라지고, 사람이 사라지면 이야기가 아니라 발표가 됩니다.

> **둘 다 이길 때만 도해입니다.** 하나라도 씬 그림이 나으면 씬 그림입니다.

`infographic` — 도해만 할 수 있는 일일 때
  · **「없음」을 보여야 할 때** — 「독립 근거가 확인되지 않았다」
    재연으로는 그릴 수 없습니다. 여기가 가장 확실합니다
  · 수치가 합쳐지거나 환산될 때 — 2,000 + 1,800 = 3,800 = 쌀 844가마
  · 둘을 견줄 때 — 내려놓은 것 ↔ 새로 잡은 것
  · 구조가 바뀔 때 — 기둥 둘이 빠져도 남는 것

`scene` — 재연 그림 (**기본값입니다**)
  · 사람이 무엇을 한다 · 감정이 실린 순간 · 공간의 공기가 곧 내용일 때
  · **인물이 이어지는 구간** — 도해가 끼면 사람이 끊깁니다

`map` — 어디인지가 내용일 때만 (진주에서 부산으로 옮긴다 같은)
`archive` — 실물 사진·문서가 있어야 믿기는 자리
`none` — 반전 카드·챕터 카드 (이미 정해져 있습니다)

**도해가 잇달아 나오지 않게 하세요.** 앞뒤가 도해면 이 씬은 씬 그림입니다.

# 둘째 — 재연이면, 앞 컷과 어떤 사이인가

`continuous` — 앞 컷에서 이어지는 장면
  같은 사람이 같은 곳에 있고 이야기가 그 자리에서 나아갑니다.
  **앞 컷 그림을 레퍼런스로 붙여** 그리므로 얼굴·옷·장소·빛은 저절로 이어집니다.
  정할 것은 무엇이 달라지는가입니다.
  · 카메라 자리와 각도를 옮기고, 크기는 **한 단계 이상** 바꿉니다
  · 자세와 동작은 이야기가 나아간 만큼 달라집니다. 앞 컷을 다시 그리는 것이
    아닙니다 — 손을 뻗었다면 이번엔 쥐고 있습니다

`new` — 때나 곳이 바뀝니다. 자유롭게 새로 짭니다.
  「그러던 중」·「2년 뒤」처럼 시간을 옮기면 새 장면입니다.

# 셋째 — 이 화면에 사람이 있어야 하는가

**이것을 여기서 못 박습니다.** 비워 두면 생성기가 짐작하고, 짐작이 틀리면
「여인들이 옷에 돈을 썼다」인데 화면에 사람이 없거나, 현판을 보여야 할 컷에
사람 넷이 몰려 나옵니다. 실제로 39컷 중 24컷이 그렇게 어긋났습니다.

`people` 에 **화면에 나오는 사람을 한 명씩** 적습니다. 몇 명인지가 그대로
못이 됩니다.

  ["열네 살의 구인회, 사모관대 차림"]
  ["비단을 고르는 기생 차림 여인", "돈주머니를 든 넉넉한 차림의 여인"]

**사람이 필요 없으면 빈 배열 `[]` 로 둡니다.** 그때만 「사람 없음」이 붙습니다.

  사람이 있어야 한다  누가 무엇을 한다 · 감정이 실린 순간 · 사람이 주어인 말
                      (「진학했습니다」·「돈을 썼습니다」·「판단했습니다」)
  사물만으로 충분하다  현판·문서·간판·장부·물건이 내용일 때
                      (「그 집을 구교리댁이라 불렀다」 → 현판)

손이나 뒷모습만 나와도 **사람입니다.** 그때도 적으세요.
사람이 나오는 화면은 **꼭 필요한 사람만** 적습니다. 화면을 채우려 사람을
늘리면 누가 주인공인지 흐려집니다 — 구인회 한 명인 컷에 넷이 나왔습니다.

# 넷째 — 무엇을 어느 크기로 보는가

  wide      상황을 보여준다 — 어디서 벌어지는 일인가
  medium    사람이 무엇을 하는가
  close     한 가지만 본다 — 손·글씨·눈·물건·현판

**말이 화면에 보여야 합니다.** 시대와 분위기만 맞는 화면은 실패입니다.
「빚은 회사를 쓰러뜨립니다」인데 그냥 장부를 읽는 그림이면 말이 사라진 것입니다.
그 말을 **한 장면으로 어떻게 보이게 할지**를 정하세요.

**말이 가리키는 것을 화면이 봅니다.** 「할아버지는 홍문관 교리였다」면 현판이나
교지를, 「공부를 시켰다」면 서안과 붓을 봅니다.

**이어지는 컷이 같은 크기가 되지 않게** 하세요. 이 대목이 통째로 medium 이면
보는 사람은 화면이 멈춘 줄 압니다.

그릴 것은 **긍정형으로** 적습니다. 「~없음」처럼 빼는 말을 쓰지 마세요.

---

## 낼 것 — JSON만. 정할 씬 전부에 대해 한 줄씩.

{{"screens": [
  {{"scene": 씬번호,
    "kind": "scene | infographic | map | archive | none",
    "why": "왜 이 방식인가 한 마디",

    "link": "continuous | new",
    "size": "wide | medium | close",
    "subject": "이 컷이 보는 것 한 마디",
    "people": ["화면에 나오는 사람 (사물만이면 빈 배열)"],
    "prompt": "배경: … , 중경: … , 인물: … , 전경: … 형식의 한 줄",
    "camera": "예: Close-up, slight high angle, soft window light",

    "structure": "도해일 때만 — metric | contrast | chronology | enumeration | causal | statement | quote | metric_group",
    "shows": "도해일 때만 — 화면이 보여줄 것 한 마디"}}
]}}
"""


def ask(prompt: str) -> dict | None:
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        r = subprocess.run(["claude", "--output-format", "text"], input=prompt,
                           capture_output=True, text=True, timeout=1800, env=env)
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


def line(s: dict) -> str:
    n = s.get("sceneNumber")
    t = (s.get("narration") or "").strip()
    tag = ""
    if s.get("isTurnCard"):
        tag = " [반전 카드 — 흰 화면]"
    elif s.get("isChapterCard"):
        tag = " [챕터 카드]"
    return f"  씬{n}{tag}: {t[:140]}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--chapter", type=int, help="이 챕터만")
    ap.add_argument("--scenes", help="이 씬만 (쉼표로 구분) — 화면이 말을 못 잡았을 때")
    ap.add_argument("--needs", action="store_true",
                    help="새로 그려야 하는 씬만 — 무엇으로 보여줄지 다시 묻는다")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("-j", "--jobs", type=int, default=4)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    f = proj / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    todo = [s for s in scenes if s.get("chapter") == args.chapter] if args.chapter else list(scenes)
    # 카드는 이미 화면이 정해져 있다 — 판단에서 뺀다
    todo = [s for s in todo if not s.get("isChapterCard")]
    if args.scenes:
        want_n = {int(x) for x in args.scenes.split(",")}
        todo = [s for s in todo if s.get("sceneNumber") in want_n]
    if args.needs:
        # 새로 그려야 하는 씬은 「이미 그림이 있으니 재연」이라는 관성이 없다.
        # 여기서 도해·실물 자료를 다시 묻는 것이 맞다.
        todo = [s for s in todo if s.get("needs_image")]
    if not todo:
        raise SystemExit("정할 씬이 없습니다")

    idx = {s.get("sceneNumber"): i for i, s in enumerate(scenes)}
    out_dir = root / "_imggen" / f"{ep.lower()}_screens"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 창을 밀며 본다. 앞 LOOKBACK 씬은 읽기만 한다 — 이어짐인지 알려면
    # 앞 장면을 알아야 한다.
    jobs = []
    for k in range(0, len(todo), WINDOW):
        chunk = todo[k:k + WINDOW]
        head = idx.get(chunk[0].get("sceneNumber"), 0)
        jobs.append((scenes[max(0, head - LOOKBACK):head], chunk))

    tag = (("s" + args.scenes.replace(",", "_")) if args.scenes else "") \
        + ("needs" if args.needs else "") + (f"ch{args.chapter:02d}" if args.chapter else "all")
    print(f"{ep}  씬 {len(todo)}개 · 창 {len(jobs)}개")

    def run(job):
        before, chunk = job
        d = ask(PROMPT.format(
            before="\n".join(line(s) for s in before) or "  (편의 시작입니다)",
            scenes="\n".join(line(s) for s in chunk)))
        return chunk[0].get("sceneNumber"), (d or {}).get("screens") or []

    made = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for head, rows in ex.map(run, jobs):
            print(f"  씬{head:>4}부터  {len(rows)}개")
            made.extend(rows)

    plan_f = out_dir / f"{tag}.json"
    plan_f.write_text(json.dumps({"screens": made}, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    import collections
    kinds = collections.Counter(r.get("kind") for r in made)
    links = collections.Counter(r.get("link") for r in made if r.get("kind") == "scene")
    sizes = collections.Counter(r.get("size") for r in made if r.get("kind") == "scene")
    print(f"\n화면 종류  {dict(kinds)}")
    print(f"컷 관계    {dict(links)}")
    print(f"컷 크기    {dict(sizes)}")
    print(f"→ {plan_f}")

    if not args.apply:
        print("\n--apply 를 붙이면 반영합니다.")
        return 0

    shutil.copy2(f, f.with_suffix(f".json.bak_screens_{datetime.now():%Y%m%d_%H%M%S}"))
    by_n = {s.get("sceneNumber"): s for s in scenes}
    KIND = {"scene": "generate_image", "infographic": "infographic",
            "map": "map", "archive": "search_image", "none": "none"}
    hit = 0
    for r in made:
        s = by_n.get(r.get("scene"))
        if not s or s.get("isChapterCard"):
            continue
        kind = r.get("kind", "scene")
        s["visual_kind"] = KIND.get(kind, "generate_image")
        s["visual_why"] = r.get("why", "")
        if kind == "infographic":
            s["infoStructure"] = r.get("structure") or s.get("infoStructure") or "statement"
            s["info_shows"] = r.get("shows", "")
            s.pop("needs_image", None)
        elif kind == "scene":
            s["infoStructure"] = "scene"
            ia = s.get("imageAsset")
            if not isinstance(ia, dict):
                ia = {}
                s["imageAsset"] = ia
            # 사람이 있어야 하는지는 여기서 정한 것이 정본이다. 생성기가
            # 프롬프트 글자로 짐작하면 사물만 나와야 할 화면에도 사람이 든다.
            s["people"] = [x for x in (r.get("people") or []) if str(x).strip()]
            ia.update({"source": "generate",
                       "prompt": r.get("prompt", "") or ia.get("prompt", ""),
                       "camera": r.get("camera", ""),
                       "shot_size": r.get("size", ""),
                       "continuity": r.get("link", "new")})
            s["needs_image"] = True
        hit += 1

    f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{hit}개 씬의 화면을 정했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
