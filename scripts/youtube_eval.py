#!/usr/bin/env python3
"""**세모지 유튜브 시청자 기준**으로 편을 채점한다 — 끝까지 볼 것인가.

`viewer_eval.py` 와 재는 것이 다르다. 그쪽은 **헷갈리는 자리**를 찾는다.
보는 사람 셋이 전부 검사관이고(납득 안 하면 멈춤·소리 없이도 알아야 함·
심심하면 넘김), 네 축 중 셋이 「틀리지 않았는가」다. 그 채점표의 만점은
「아무도 헷갈리지 않는 영상」이지 **많이 본 영상이 아니다.**

실제로 LG 1편에서 그림을 36컷 고쳐 그 지표를 56 → 62 로 올렸는데,
이해도는 63 → 70 으로 올라간 반면 몰입은 55 → 60 → 59 에서 멈췄다.
덜 헷갈리게만 만들고 있었다.

그래서 **채널이 이미 가진 기준**으로 잰다 —
`data/skills/agents/script-reviewer/SKILL.md` 의 시청자 100점 루브릭이다.
「유튜브에서 클릭한 시청자가 끝까지 볼 것인가」를 묻고, Hook·깊이·재미·
Payoff·이탈 위험에 배점이 있다. 새로 지어낸 잣대가 아니라 이 채널의
잣대인데 파이프라인에 스텝이 없어 한 번도 돌지 않았다.

보는 사람도 바꾼다. 검사관 대신 **이 채널을 실제로 보는 사람들**이다.

    python3 scripts/youtube_eval.py EP01
    python3 scripts/youtube_eval.py EP01 --chapter 3

두 단계로 본다. 채널이 긴 편이라 한 번에 다 못 본다.

  ① 구간별로 본다   어디서 나가고 싶었는가 · 어디가 좋았는가 · 어디가 뻔한가
  ② 그걸 손에 들고 편 전체를 100점으로 매긴다
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_agent.paths import resolve_project  # noqa: E402
from viewer_eval import ask, describe  # noqa: E402


def _dur(proj, scene) -> float:
    """그 컷이 실제로 몇 초인가 — 녹음 파일 길이.

    이것이 없으면 「같은 화면이 네 컷 이어진다」까지만 알 수 있다. 길이를
    알면 「12초 이어진다」가 되어 늘어짐을 제대로 잴 수 있다. 지속·절정은
    시간에 달린 항목인데 지금까지 감으로 매겨졌다.
    """
    proj = Path(scene.get("_proj") or proj)   # 합본 원고(공개 편)는 씬마다 제 프로젝트 폴더를 들고 온다
    for stem in (scene.get("sceneId"), f"scene_{scene.get('sceneNumber'):03d}"):
        if not stem:
            continue
        f = proj / "audio" / f"{stem}.mp3"
        if f.exists():
            # mp3 128kbps 기준 근사 — 매니페스트가 쓰는 것과 같은 셈
            return round(f.stat().st_size * 8 / 128000, 1)
    return 0.0

WINDOW = 22

# 검사관이 아니라 **이 채널을 보는 사람들**이다. 셋 다 결함을 찾는 눈을 두면
# 「아무도 헷갈리지 않지만 아무도 안 보는 영상」이 만점을 받는다.
# 시청자 정의는 원고 리뷰어와 함께 쓴다 — 한 곳에서만 고친다
_PERSONAS_MD = Path(__file__).resolve().parents[1] / "auto_agent/data/skills/shared/viewer-personas.md"
PERSONAS = _PERSONAS_MD.read_text(encoding="utf-8").split("---\n", 2)[2].lstrip("\n")

SEG = """{personas}

## 이 구간

{mode_note}

{scenes}

## 물을 것 — 실제로 볼 때 하는 행동으로

**컷마다 「길이: n초」가 적혀 있습니다.** 그게 그 화면이 실제로 떠 있는
시간입니다. 같은 그림이 네 컷 이어지면 그 초를 더해서 보세요 — 3초면
안 걸리지만 15초면 손가락이 움직입니다.

```
여기서 껐는가              그 자리와 이유를 씬번호로
배속을 올렸는가            어느 구간인지
되감았는가                 못 알아들어서인지, 좋아서 다시 본 것인지
「오」 소리가 났는가        몰랐던 것이 나와 눈이 커진 자리
남에게 말하고 싶은가        어느 대목을 · 누구에게 · 왜
관점이 생겼는가            사실을 안 것을 넘어 세상을 보는 눈이 하나 생겼는가
못 믿겠는가                근거 없이 단정하거나 과장으로 들린 자리
```

**틀린 곳을 찾는 일이 아닙니다.** 실제로 볼 때 손가락이 어떻게 움직였는지만
정직하게 답하세요.

**제작 품질을 따지지 마세요.** 화풍이 튀는지, 인물 등신이 맞는지, 같은
그림이 두 번 쓰였는지는 **만드는 사람의 관심사이지 보는 사람의 것이 아닙니다.**
1.5배속으로 보는 사람은 그림을 한 장씩 뜯어보지 않습니다.

여러분이 답할 것은 하나입니다 — **쭉 봐졌는가.** 지루해서 손가락이
움직였다면 그렇게 적고, 재미있어서 끝까지 봤으면 그렇게 적으세요.

{seg_screen_note}

## 낼 것 — JSON만

{{"leave": [{{"n": 씬번호, "why": "왜 껐는가"}}],
 "speed_up": [{{"n": 씬번호, "why": "왜 배속을 올렸는가"}}],
 "rewound": [{{"n": 씬번호, "why": "못 알아들어서 | 좋아서"}}],
 "wow": [{{"n": 씬번호, "why": "무엇이 놀라웠는가"}}],
 "tell_others": [{{"n": 씬번호, "who": "누구에게", "why": "왜 말하고 싶은가"}}],
 "insight": ["사실을 넘어 관점이 생긴 대목"],
 "doubt": [{{"n": 씬번호, "why": "왜 못 믿겠는가"}}],
 "new_facts": ["이 구간에서 처음 알게 된 것"],
 "note": "이 구간을 한 줄로"}}
"""

# 채널이 이미 가진 잣대다. 배점을 그대로 옮긴다 —
# script-reviewer SKILL.md 「1. 시청자 리뷰어」 100점.
# 채점표는 **지식 콘텐츠를 실제로 소비하는 관점** 넷으로 짠다 —
# 재미 30 · 유용 30 · 확산 25 · 신뢰 15. 확산은 감독 지시로 뒤에 더했다:
# 한 편이 좋은 것과 「세모지 스타일로 다른 백과도 보고 싶어지는」 것은 다른 일이다. 앞선 판은 「천만 편 = 80점」이라는 근거 없는 앵커를
# 박아 두어 천장이 생겼고, 「이탈 위험」은 무엇이 높은 점수인지 적지 않아
# 일곱 번 내내 2/5 로 고정됐다. 깊이·인과·이해도 한 번도 안 움직였다.
# 40점어치가 무엇을 하든 같은 값이었다.
#
# **같은 사고가 「화면 신뢰」에서 한 번 더 났다.** 「어긋난 자리 셋 넘으면 0」이
# 길이에 상관없는 절대 개수라, 씬 177개짜리 편에서는 항상 0~2 였다. 열다섯 번
# 재는 동안 3점 이상이 한 번도 안 나왔다. 지금은 편 길이(씬 백 개당)로 나눈다.
#
# 눈금을 만들 때마다 물을 것 — **이 항목이 만점을 받을 수 있는가.**
#
# 그래서 **점수마다 무엇이 만점이고 무엇이 0점인지 행동으로 못 박는다.**
FINAL = """{personas}

## 이 편의 말 전체

{narration}

## 넷이 보면서 적은 것

{segments}

## 채점 — 지식 콘텐츠로서 어떤가

이 채널은 지식 콘텐츠입니다. 사람들은 **재미있어서 보고, 알아갈 게 있어서
남고, 믿을 만해서 다시 옵니다.** 그 셋으로 매깁니다.

### 재미 30점 — 계속 보게 되는가

**이 세 항목은 오직 「쭉 봐졌는가」로만 매깁니다.**
화풍이 튄다·인물이 달라 보인다·같은 그림이 두 번 쓰였다 같은 **제작 품질을
재미 감점의 근거로 쓸 수 없습니다.** 그건 아래 신뢰성에서 봅니다.
여기서 쓸 수 있는 근거는 **「지루해서 껐다」와 「못 알아들어서 껐다」** 둘뿐입니다.

```
후킹      10   첫 30초에 계속 볼 이유가 생겼는가
               넷 다 남았다 10 · 셋 7 · 둘 5 · 하나 2 · 아무도 0
지속      12   **넷 중 둘 이상이 배속을 올리거나 건너뛴 자리가 몇 곳인가**
               편 길이에 견줍니다 — 씬 백 개당
               없음 12 · 한 곳 11 · 두 곳 10 · 셋 8 · 넷 6 · 다섯 4 · 여섯 넘음 2
               ⚠ **한 사람만 움직인 자리는 세지 않습니다.** 민가영은 1.5배속이
                  기본이라 어느 원고에서나 손가락이 움직입니다. **둘 이상이
                  같은 자리를 짚어야** 그 대목이 늘어진 것입니다
               ⚠ **반전에서 배속을 되돌린 자리는 깎지 않습니다** — 통했다는 뜻입니다
               ⚠ **어미가 반복된다는 이유로 여기서 깎지 마세요.** 그건 정직에서
                  봅니다 — 같은 결함을 두 번 청구하면 우선순위가 망가집니다
               ⚠ 「비율」로 매기지 마세요. 긴 편일수록 늘어진 자리가 하나는
                  나오기 마련이라, 비율로 재면 어떤 원고도 만점이 안 됩니다
절정       8   되감거나 「오」 소리가 난 자리의 수
               세 곳 넘음 8 · 두 곳 6 · 한 곳 3 · 없음 0
```

### 유용성 30점 — 알아갈 것과 관점이 있는가

```
새로 안 것 12  몰랐던 사실이 **얼마나 묵직한가** — 개수가 아니라 무게입니다
               ⚠ 「다섯 개 넘으면 만점」처럼 세지 마세요. 10분이 넘는 편에서
                  처음 듣는 사실 다섯 개는 **어느 원고나 넘깁니다**
               세는 것은 **묵직한 것**뿐입니다.
                 · 널리 퍼진 통설을 뒤집는 사실
                 · 당사자의 증언·회고로 처음 드러나는 장면
                 · 확인된 숫자가 판을 뒤집는 대목
               연혁·목록에서 처음 들은 이름과 연도는 **여기 넣지 않습니다.**
               셋 넘음 12 · 둘 9 · 하나 6 · 묵직한 건 없지만 새 사실은 많다 3 · 없다 0
인사이트   12  사실을 안 것을 넘어 **세상을 보는 눈**이 하나 생겼는가
               「이 회사는 이래서 버텼구나」처럼 다른 일에도 갖다 댈 수 있는
               관점이 남는다 12 · 하나쯤 8 · 어렴풋 4 · 사실 나열뿐 0
남는 것    6   하루 뒤에도 장면과 함께 기억날 것이 있는가
               또렷이 6 · 하나쯤 4 · 흐릿 2 · 없음 0
```

### 확산과 성장 {spread_max}점 — 채널이 자라는가

이 축이 채널의 크기를 정합니다. 한 편이 좋은 것과, 그 편 때문에
**{spread_what}** 것은 다른 일입니다.

```
공유      10   남에게 링크를 보낼 것인가 — 넷 중 몇 명이, 누구에게
               셋 넘음 10 · 둘 7 · 하나 4 · 아무도 0
{next_rule}다른 시리즈 7  **이 편을 보고 나서 이 채널의 다른 주제도 궁금해졌는가.**
               브랜드백과의 다른 회사, 상식백과 같은 다른 주제를
               보고 싶어지면 됩니다. 내용이 좋아서든, 푸는 방식이 좋아서든,
               그림이 좋아서든 **가리지 않습니다.**
               「내용 때문이지 이 화풍 때문은 아니다」는 **감점 사유가
               아닙니다** — 어떤 이유로든 누르면 그만입니다
               ⚠ **「결말에 다른 백과로 이어 주는 다리가 없다」로 깎지 마세요.**
                  시리즈물의 결말은 **다음 편을 궁금하게 만드는 것이 본래
                  임무**입니다. 그걸 잘한 편을 여기서 깎으면, 잘 만든 구조를
                  결함으로 읽는 것이 됩니다. 끝에 광고 문구를 붙이라는 뜻이
                  아닙니다
               ⚠ **「이 사람은 다음 편을 먼저 보겠다고 했다」도 깎지 마세요.**
                  시리즈 중간에서는 당연한 일이고, 그 마음은 「다음 편」
                  항목이 이미 받고 있습니다 — 두 번 청구가 됩니다
               묻는 것은 **이 편이 남긴 인상**뿐입니다. 푸는 방식이 끌렸으면
               그 사람은 누른 것으로 봅니다
               넷 다 7 · 셋 5 · 둘 3 · 하나 1 · 아무도 0
```

### 신뢰성 {trust_max}점 — 믿을 만한가

```
근거       6   주장에 수치·출처·사례가 붙는가
               거의 다 6 · 대체로 4 · 절반 2 · 맨말이 많다 0
정직       5   **두 가지를 함께 봅니다.**
               ① 확인 안 된 것을 확정처럼 말하지 않는가 — 해석·인과·속마음에
                  「~인 겁니다」「~던 거죠」「~증명된 셈입니다」를 붙이지 않는다
               ② **귀속이 가볍게 달려 있는가** — 문장 끝 서술어로 한 번이면
                  충분합니다(「~라고 합니다」「회사는 ~라고 설명합니다」
                  「~가 자체 집계했습니다」).
                  깎는 것은 **두 가지뿐**입니다.
                    · **한 문장에 두 겹** — 앞머리에 「후대 기록에 따르면」을
                      붙이고 끝에 다시 「전해집니다」를 다는 것
                    · **세 줄 넘게 잇달아** 같은 표현이 이어지는 것
                  편 전체에 흩어져 있는 것은 **깎지 않습니다.** 귀속은 많아도
                  됩니다 — 한자리에 겹치거나 잇달을 때만 무거워집니다
               **조항이 둘이니 눈금도 여섯 칸입니다.**
               둘 다 지켰다 5 · 한쪽에 한두 곳 4 · 한쪽에 여러 곳 3 ·
               양쪽에 걸린다 2 · 곳곳이 단정이다 1 · 전반이 단정이다 0
               ⚠ 한두 곳 걸렸다고 곧바로 1점으로 내리지 마세요.
                  잘된 편과 안 된 편을 가를 수 있어야 합니다
{screen_rule}```

## 채점할 때

**만점은 실제로 가능합니다.** 흠이 없으면 만점을 주세요. 어떤 편과
견주지 마세요 — 위에 적힌 기준만 봅니다.

**근거 없이 깎지 마세요.** 점수를 깎을 때마다 **어느 씬 때문인지 씬번호를
적습니다.** 씬번호를 못 대면 깎지 않습니다.

{cause_rule}

**넷의 답이 갈리면 다수를 따르되, 갈렸다는 것을 적으세요.**

## 낼 것 — JSON만

{{"scores": {{"hook": 0-10, "hold": 0-12, "peak": 0-8,
             "new": 0-12, "insight": 0-12, "stick": 0-6,
             "share": 0-10, {schema_next}"series": 0-7,
             "evidence": 0-6, "honest": 0-5{schema_screen}}},
 "deductions": [{{"item": "항목 이름", "scene": 씬번호,
                  "cause": {cause_opts}, "why": "왜 깎았는가"}}],
 "total": 0-{total_max},
 "quit_points": [{{"n": 씬번호, "why": "여기서 껐다"}}],
 "best": [{{"n": 씬번호, "why": ""}}],
 "verdict": "재미·유용성·확산·신뢰성 각각 한 줄씩",
 "series_pull": "이 편을 보고 다른 백과도 보고 싶어지는가 — 그 이유",
 "biggest_lever": "한 가지만 고친다면 무엇인가"}}
"""


def _merge(outs: list) -> dict:
    """여러 판을 항목별 중앙값으로 모은다.

    한 판의 총점은 **그 판에 채점자가 감점을 몇 건 썼는가**에 끌려간다
    (열세 편 실측 r = -0.85). 그리고 그 건수는 같은 원고에서 4~16건으로
    흔들린다. 그래서 한 판을 그대로 쓰지 않는다.

    · 항목마다 중앙값을 쓰고 **폭(min~max)을 함께 남긴다** — 폭이 넓은
      항목은 그 판에서 읽으면 안 되는 항목이다
    · 총점은 모델이 낸 숫자가 아니라 **중앙값의 합**이다
    · 감점은 **몇 판이 같은 자리를 짚었는가**(`runs`)로 정렬한다.
      여러 판이 되풀이해 짚은 자리가 신호이고, 한 판만 짚은 것은 잡음이다
    """
    import statistics

    keys = set()
    for o in outs:
        keys |= set((o.get("scores") or {}).keys())
    sc, spread = {}, {}
    for k in keys:
        vals = [o["scores"][k] for o in outs
                if isinstance((o.get("scores") or {}).get(k), (int, float))]
        if not vals:
            continue
        sc[k] = int(round(statistics.median(vals)))
        spread[k] = [min(vals), max(vals)]
    total = sum(sc.values())

    # 글(verdict·처방)은 총점이 가운데인 판의 것을 쓴다 — 평균낼 수 없다
    def _own(o):
        s = o.get("scores") or {}
        return sum(v for v in s.values() if isinstance(v, (int, float)))

    rep = min(outs, key=lambda o: abs(_own(o) - total))

    agg: dict = {}
    for o in outs:
        for d in (o.get("deductions") or []):
            e = agg.setdefault((d.get("item"), d.get("scene")), {**d, "runs": 0})
            e["runs"] += 1
    ded = sorted(agg.values(), key=lambda d: (-d["runs"], str(d.get("item"))))

    return {**rep, "scores": sc, "total": total, "deductions": ded,
            "runs": len(outs), "totals": [o.get("total") for o in outs],
            "spread": spread}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--specs", type=Path,
                    help="다른 scene_specs 로 채점 — 고치기 전 원고와 견줄 때")
    ap.add_argument("--tag", default="", help="결과 파일 꼬리표")
    ap.add_argument("--script-only", action="store_true",
                    help="원고만 채점 — 그림을 보이지 않고 화면 신뢰를 빼고 96점을 100점으로 환산")
    ap.add_argument("--final", action="store_true",
                    help="시리즈 마지막 편 — 누를 다음 편이 없으므로 그 항목을 빼고 88점으로 잰다")
    ap.add_argument("--runs", type=int, default=1,
                    help="최종 채점을 N번 반복해 항목별 중앙값을 쓴다. "
                         "구간 읽기는 한 번뿐이라 비용은 조금만 는다. 판단은 3판 이상에서")
    ap.add_argument("-j", "--jobs", type=int, default=3)
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    proj, ep = resolve_project(args.ep)
    spec = args.specs or (proj / "scene_specs.json")
    scenes = json.loads(spec.read_text(encoding="utf-8"))["scenes"]
    sys.path.insert(0, str(root))
    from auto_agent.tools.image_assets import get_selected

    todo = [s for s in scenes
            if args.chapter is None or s.get("chapter") == args.chapter]
    if not todo:
        raise SystemExit("볼 씬이 없습니다")
    for s in todo:
        s["_ep"] = ep.lower()

    print(f"{ep}  씬 {len(todo)}개를 세모지 시청자 넷에게 보입니다")

    # 원고 판에는 그림이 없다. 있는 척하면 「화면이 비었다」로 깎여
    # 원고로는 닿지 않는 점수가 총점에 섞인다.
    SO = args.script_only
    FIN = args.final
    mode_note = ("이 판에는 **그림이 아직 없습니다.** 귀로만 듣는다고 생각하고,\n"
                 "말만으로 쭉 들리는지 판단하세요. 화면 이야기는 하지 마세요."
                 if SO else
                 "첨부한 그림 파일을 **Read 로 직접 열어 보고** 판단하세요.")
    seg_screen_note = ("" if SO else
                       "다만 **화면이 말과 달라 이야기를 잘못 알아들은 자리**는 적습니다.\n"
                       "그건 제작 품질이 아니라 내용을 오해한 것이니까요.")

    def run(chunk):
        parts = []
        for s in chunk:
            if SO:
                line = f"  씬{s['sceneNumber']}  말: {(s.get('narration') or '').strip()}"
            else:
                line = describe(s, proj, root,
                                get_selected(proj / "images", s["sceneNumber"]))
            d = _dur(proj, s)
            if d:
                line += f"\n      길이: {d}초"
            parts.append(line)
        return ask(SEG.format(personas=PERSONAS, scenes="\n".join(parts),
                              mode_note=mode_note, seg_screen_note=seg_screen_note))

    chunks = [todo[i:i + WINDOW] for i in range(0, len(todo), WINDOW)]
    segs = []
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        for r in ex.map(run, chunks):
            if r:
                segs.append(r)
    print(f"  구간 {len(segs)}개를 봤습니다 — 이제 편 전체를 매깁니다")

    def fmt(i, s):
        L = [f"  구간 {i + 1}"]
        for k, lab in (("leave", "나가고 싶은 자리"), ("good", "좋았던 자리")):
            for x in (s.get(k) or [])[:6]:
                L.append(f"    {lab}: 씬{x.get('n')} — {x.get('why','')[:70]}")
        if s.get("obvious"):
            L.append(f"    뻔한 씬: {s['obvious'][:12]}")
        if (s.get("flat") or "").strip():
            L.append(f"    같은 톤이 이어진 구간: {s['flat']}")
        for f in (s.get("new_facts") or [])[:3]:
            L.append(f"    몰랐던 것: {f[:70]}")
        if s.get("note"):
            L.append(f"    한 줄: {s['note'][:90]}")
        return "\n".join(L)

    narr = "\n".join(f"  씬{s['sceneNumber']}: {(s.get('narration') or '').strip()}"
                     for s in todo if (s.get("narration") or "").strip())
    screen_rule = "" if SO else """화면 신뢰   4  **소리를 끄고 봤을 때 이야기를 잘못 이해하게 되는가**
               세는 것은 「말과 반대로 읽히는 자리」뿐입니다 —
               성공을 말하는데 실패가 보이거나, 앞장서라는데 등을 돌리고 나가거나,
               1955년 이야기에 2020년대 사진이 붙은 자리.
               「화면이 말과 접점이 약하다」·「그 말을 직접 안 그렸다」는
               여기서 세지 않습니다. 그건 재미(지속)와 유용(남는 것)에서
               이미 깎이고 있어 두 번 청구가 됩니다.

               편 길이에 견주어 매깁니다 — 씬 백 개당 몇 곳인가.
               백 개당 없음 4 · 한 곳 3 · 두 곳 2 · 셋 1 · 넷 넘음 0
"""
    cause_rule = ("**감점마다 원인을 답니다** — `cause` 에 「원고」「구성」 중 하나를\n"
                  "적습니다. 원고는 말 자체의 문제, 구성은 순서와 되풀이의 문제입니다.\n\n"
                  "**그림은 채점하지 않습니다.** 이 판에는 화면이 없습니다. "
                  "「화면이 비었다」·「그림이 오래 떠 있다」로 깎지 마세요 — "
                  "말이 그 시간을 못 버티는 것이면 그것은 **원고** 문제로 적습니다."
                  if SO else
                  "**감점마다 원인을 답니다** — `cause` 에 「원고」「화면」「구성」 중 하나를\n"
                  "적습니다. 원고는 말 자체의 문제, 화면은 그림이 말을 못 받는 것, 구성은\n"
                  "순서와 되풀이의 문제입니다. 그래야 무엇을 고쳐야 점수가 오르는지 보입니다.\n\n"
                  "**제작 품질은 신뢰성에서만 봅니다.** 화풍·인물 일관성이 아쉬우면\n"
                  "「화면 신뢰」에서 깎고, 재미·확산에서는 깎지 않습니다.")
    fp = FINAL.format(personas=PERSONAS, narration=narr,
                           segments="\n\n".join(fmt(i, s) for i, s in enumerate(segs)),
                           trust_max=11 if SO else 15,
                           screen_rule=screen_rule, cause_rule=cause_rule,
                           schema_screen="" if SO else ', "screen": 0-4',
                           cause_opts='"원고 | 구성"' if SO else '"원고 | 화면 | 구성"',
                           spread_max=17 if FIN else 25,
                           spread_what=('다른 시리즈까지 보고 싶어지는' if FIN
                                        else '다음 편과 다른 시리즈까지 보고 싶어지는'),
                           next_rule=('' if FIN else
                                      '다음 편    8   끝나고 이 시리즈의 다음 편을 누를 것인가\n'
                                      '               넷 다 8 · 셋 6 · 둘 4 · 하나 2 · 아무도 0\n'),
                           schema_next='' if FIN else '"next": 0-8, ',
                           total_max=(88 if FIN else 96) if SO else (92 if FIN else 100))
    # 한 판의 총점은 그 판에 쓴 감점 건수에 끌려간다. 여러 판을 재서 중앙값을 쓴다.
    outs = []
    for i in range(max(1, args.runs)):
        r = ask(fp)
        if r and (r.get("scores") or r.get("total") is not None):
            outs.append(r)
        if args.runs > 1:
            print(f"  채점 {i + 1}판 — 받은 것 {len(outs)}개"
                  + (f" (총점 {r.get('total')})" if r else " (실패)"))
    if not outs:
        raise SystemExit("채점을 못 받았습니다")
    out = _merge(outs) if len(outs) > 1 else outs[0]

    sc = out.get("scores") or {}
    lab = {"hook": "후킹", "hold": "지속", "peak": "절정",
           "new": "새로안것", "insight": "인사이트", "stick": "남는것",
           "share": "공유", "next": "다음편", "series": "다른시리즈",
           "evidence": "근거", "honest": "정직", "screen": "화면신뢰"}
    mx = {"hook": 10, "hold": 12, "peak": 8,
          "new": 12, "insight": 12, "stick": 6,
          "share": 10, "next": 8, "series": 7,
          "evidence": 6, "honest": 5, "screen": 4}
    group = {"hook": "재미", "hold": "재미", "peak": "재미",
             "new": "유용", "insight": "유용", "stick": "유용",
             "share": "확산", "next": "확산", "series": "확산",
             "evidence": "신뢰", "honest": "신뢰", "screen": "신뢰"}
    if SO:
        for _d in (lab, mx, group):
            _d.pop("screen", None)
    if FIN:
        for _d in (lab, mx, group):
            _d.pop("next", None)
    print()
    cur = None
    for k in lab:
        if group[k] != cur:
            cur = group[k]
            tot = sum(mx[x] for x in lab if group[x] == cur)
            got = sum(sc.get(x, 0) for x in lab if group[x] == cur)
            print(f"\n  [{cur}]  {got} / {tot}")
        _sp = (out.get("spread") or {}).get(k)
        # 폭이 넓은 항목은 이 판에서 읽으면 안 된다 — 그 값은 잡음이다
        _w = (f"   판마다 {_sp[0]}~{_sp[1]}" + ("  ⚠ 읽지 말 것" if _sp[1] - _sp[0] >= 3 else "")
              if _sp and _sp[1] > _sp[0] else "")
        print(f"    {lab[k]:<8} {sc.get(k, 0):>3} / {mx[k]}{_w}")
    if out.get("totals"):
        print(f"\n  판별 총점 {out['totals']}  →  중앙값의 합을 씁니다")
    _t = out.get("total")
    if SO and isinstance(_t, (int, float)):
        _m = 88 if FIN else 96
        print(f"\n  총점 {_t} / {_m}   →   원고 점수 {round(_t * 100 / _m)} / 100")
    else:
        print(f"\n  총점 {_t} / 100")
    print(f"\n  끝까지 볼 것인가: {(out.get('verdict') or '')[:400]}")
    print(f"\n  다른 시리즈도 보고 싶은가: {(out.get('series_pull') or '')[:280]}")
    print(f"\n  한 가지만 고친다면: {(out.get('biggest_lever') or '')[:300]}")
    _n = out.get("runs") or 1
    if _n > 1:
        print(f"\n  감점 — {_n}판 중 몇 판이 짚었는가 (여러 판이 짚은 것만 신호입니다)")
    for d in (out.get("deductions") or [])[:14]:
        _r = f"[{d.get('runs')}/{_n}판] " if _n > 1 else ""
        print(f"    깎음 {_r}[{d.get('cause','?')}] {d.get('item','')} "
              f"씬{d.get('scene')} — {str(d.get('why',''))[:56]}")
    lp = out.get("quit_points") or []
    if lp:
        print(f"\n  끈 자리 {len(lp)}곳")
        for x in lp[:10]:
            print(f"    씬{x.get('n')}  {x.get('why','')[:76]}")

    f = root / "_imggen" / f"{ep}_youtube{args.tag}.json"
    if f.exists():
        f.replace(f.with_name(f"{f.stem}.prev{f.suffix}"))
    f.write_text(json.dumps({"episode": ep, "segments": segs, **out},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
