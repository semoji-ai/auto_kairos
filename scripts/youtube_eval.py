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
PERSONAS = """## 보는 사람 넷

세모지는 「세상의 모든 지식」을 다루는 지식 채널이고, 이 편은
브랜드백과사전 시리즈입니다. 회사가 어떻게 시작해서 어떻게 버텼는지를
10분 넘게 풀어 놓는 영상이고, 사람들은 그걸 **재미로** 봅니다.

  정하늘  서른셋. 이 채널 구독자. 브랜드 뒷이야기를 좋아해 알림을 켜 뒀습니다.
          「몰랐던 것」이 나오면 좋아하고, 아는 얘기만 나오면 배속을 올립니다.
          끝나면 댓글을 답니다 — 무엇에 대해 달지가 이 사람의 판단입니다.

  오세훈  마흔일곱. 구독은 안 했고 추천에 떠서 눌렀습니다.
          첫 30초 안에 「그래서 뭐?」가 들면 바로 나갑니다.
          한번 붙들리면 끝까지 봅니다.

  민가영  스물여섯. 알고리즘을 타고 왔습니다. 배속 1.5로 봅니다.
          같은 톤이 이어지면 손가락이 먼저 움직입니다.
          반전이 오면 배속을 되돌립니다.

  한경수  예순하나. 회사 다닌 세월이 길어 이 업계를 압니다.
          틀린 말이 나오면 거슬려 하고, 아는 이야기를 새 각도로 보여 주면
          누구에게 링크를 보냅니다.

넷 다 **재미로 보는 사람**입니다. 검사하러 온 사람이 아닙니다.
지루하면 나가고, 재미있으면 남습니다. 그것만 정직하게 답하세요.
"""

SEG = """{personas}

## 이 구간

첨부한 그림 파일을 **Read 로 직접 열어 보고** 판단하세요.

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

다만 **화면이 말과 달라 이야기를 잘못 알아들은 자리**는 적습니다.
그건 제작 품질이 아니라 내용을 오해한 것이니까요.

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
# 채점표는 **지식 콘텐츠를 실제로 소비하는 관점** 셋으로 짠다 —
# 재미·유용성·신뢰성. 앞선 판은 「천만 편 = 80점」이라는 근거 없는 앵커를
# 박아 두어 천장이 생겼고, 「이탈 위험」은 무엇이 높은 점수인지 적지 않아
# 일곱 번 내내 2/5 로 고정됐다. 깊이·인과·이해도 한 번도 안 움직였다.
# 40점어치가 무엇을 하든 같은 값이었다.
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
지속      12   배속·건너뛰기 없이 본 구간의 비율
               거의 전부 12 · 대부분 9 · 절반 6 · 절반 아래 2
절정       8   되감거나 「오」 소리가 난 자리의 수
               세 곳 넘음 8 · 두 곳 6 · 한 곳 3 · 없음 0
```

### 유용성 30점 — 알아갈 것과 관점이 있는가

```
새로 안 것 12  몰랐던 사실이 몇 개나 나왔고 얼마나 묵직한가
               다섯 개 넘고 묵직 12 · 서넛 9 · 둘 6 · 하나 3 · 없음 0
인사이트   12  사실을 안 것을 넘어 **세상을 보는 눈**이 하나 생겼는가
               「이 회사는 이래서 버텼구나」처럼 다른 일에도 갖다 댈 수 있는
               관점이 남는다 12 · 하나쯤 8 · 어렴풋 4 · 사실 나열뿐 0
남는 것    6   하루 뒤에도 장면과 함께 기억날 것이 있는가
               또렷이 6 · 하나쯤 4 · 흐릿 2 · 없음 0
```

### 확산과 성장 25점 — 채널이 자라는가

이 축이 채널의 크기를 정합니다. 한 편이 좋은 것과, 그 편 때문에
**다음 편과 다른 시리즈까지 보고 싶어지는** 것은 다른 일입니다.

```
공유      10   남에게 링크를 보낼 것인가 — 넷 중 몇 명이, 누구에게
               셋 넘음 10 · 둘 7 · 하나 4 · 아무도 0
다음 편    8   끝나고 이 시리즈의 다음 편을 누를 것인가
               넷 다 8 · 셋 6 · 둘 4 · 하나 2 · 아무도 0
다른 시리즈 7  **세모지 스타일로 다른 백과도 보고 싶어지는가.**
               브랜드백과의 다른 회사, 상식백과 같은 다른 주제를
               이 화풍과 이 방식으로 보고 싶다는 마음이 드는가
               넷 다 7 · 셋 5 · 둘 3 · 하나 1 · 아무도 0
```

### 신뢰성 15점 — 믿을 만한가

```
근거       6   주장에 수치·출처·사례가 붙는가
               거의 다 6 · 대체로 4 · 절반 2 · 맨말이 많다 0
정직       5   확인 안 된 것을 확정처럼 말하지 않는가
               귀속이 또렷하다 5 · 대체로 3 · 뭉갠 데가 있다 1 · 단정한다 0
화면 신뢰   4  화면이 말과 어긋나 오해를 만들지 않는가
               어긋난 자리 없음 4 · 한 곳 2 · 두 곳 1 · 셋 넘음 0
```

## 채점할 때

**만점은 실제로 가능합니다.** 흠이 없으면 만점을 주세요. 어떤 편과
견주지 마세요 — 위에 적힌 기준만 봅니다.

**근거 없이 깎지 마세요.** 점수를 깎을 때마다 **어느 씬 때문인지 씬번호를
적습니다.** 씬번호를 못 대면 깎지 않습니다.

**감점마다 원인을 답니다** — `cause` 에 「원고」「화면」「구성」 중 하나를
적습니다. 원고는 말 자체의 문제, 화면은 그림이 말을 못 받는 것, 구성은
순서와 되풀이의 문제입니다. 그래야 무엇을 고쳐야 점수가 오르는지 보입니다.

**제작 품질은 신뢰성에서만 봅니다.** 화풍·인물 일관성이 아쉬우면
「화면 신뢰」에서 깎고, 재미·확산에서는 깎지 않습니다.

**넷의 답이 갈리면 다수를 따르되, 갈렸다는 것을 적으세요.**

## 낼 것 — JSON만

{{"scores": {{"hook": 0-10, "hold": 0-12, "peak": 0-8,
             "new": 0-12, "insight": 0-12, "stick": 0-6,
             "share": 0-10, "next": 0-8, "series": 0-7,
             "evidence": 0-6, "honest": 0-5, "screen": 0-4}},
 "deductions": [{{"item": "항목 이름", "scene": 씬번호,
                  "cause": "원고 | 화면 | 구성", "why": "왜 깎았는가"}}],
 "total": 0-100,
 "quit_points": [{{"n": 씬번호, "why": "여기서 껐다"}}],
 "best": [{{"n": 씬번호, "why": ""}}],
 "verdict": "재미·유용성·확산·신뢰성 각각 한 줄씩",
 "series_pull": "이 편을 보고 세모지 스타일의 다른 백과를 보고 싶어지는가 — 그 이유",
 "biggest_lever": "한 가지만 고친다면 무엇인가"}}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ep")
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--specs", type=Path,
                    help="다른 scene_specs 로 채점 — 고치기 전 원고와 견줄 때")
    ap.add_argument("--tag", default="", help="결과 파일 꼬리표")
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

    def run(chunk):
        parts = []
        for s in chunk:
            line = describe(s, proj, root, get_selected(proj / "images", s["sceneNumber"]))
            d = _dur(proj, s)
            if d:
                line += f"\n      길이: {d}초"
            parts.append(line)
        return ask(SEG.format(personas=PERSONAS, scenes="\n".join(parts)))

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
    out = ask(FINAL.format(personas=PERSONAS, narration=narr,
                           segments="\n\n".join(fmt(i, s) for i, s in enumerate(segs))))
    if not out:
        raise SystemExit("채점을 못 받았습니다")

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
    print()
    cur = None
    for k in lab:
        if group[k] != cur:
            cur = group[k]
            tot = sum(mx[x] for x in lab if group[x] == cur)
            got = sum(sc.get(x, 0) for x in lab if group[x] == cur)
            print(f"\n  [{cur}]  {got} / {tot}")
        print(f"    {lab[k]:<8} {sc.get(k, 0):>3} / {mx[k]}")
    print(f"\n  총점 {out.get('total')} / 100")
    print(f"\n  끝까지 볼 것인가: {(out.get('verdict') or '')[:400]}")
    print(f"\n  다른 시리즈도 보고 싶은가: {(out.get('series_pull') or '')[:280]}")
    print(f"\n  한 가지만 고친다면: {(out.get('biggest_lever') or '')[:300]}")
    for d in (out.get("deductions") or [])[:12]:
        print(f"    깎음 [{d.get('cause','?')}] {d.get('item','')} "
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
