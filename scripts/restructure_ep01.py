#!/usr/bin/env python3
"""1편 앞부분을 다시 짠다 — 오프닝을 넷으로 끝내고 챕터1부터 본편.

무엇이 문제였나.

  · 씬5~8이 본편(씬11~19)이 제대로 하는 이야기를 **미리 요약**하고 있었다.
    1931년 개업 → 첫해 손실 → 홍수 → 신용. 본편에서 한 번 더 한다.
    훅으로 붙잡아 놓고 줄거리를 미리 말하면 볼 이유가 사라진다.
  · 오프닝까지 챕터1에 들어가 있어 챕터 번호가 한 칸씩 밀려 있었다.
  · **왜 갑자기 장사를 하겠다고 했는지 계기가 없었다.** 장손이 붓을 놓는
    장면인데 이유 없이 「반대를 뚫고 시작했다」로 넘어간다.

계기는 지어내지 않았다. 한국경제인협회 연표에 있는 사실을 쓴다 —
중앙고보 학비를 대던 장인이 세상을 떠나 학업을 접고 귀향했다는 기록.

씬 번호는 그대로 둔다. 이미지가 번호로 묶여 있어 다시 매기면 어긋난다
(오디오는 sceneId로 묶여 있어 순서를 바꿔도 따라온다).

    python3 scripts/restructure_ep01.py --apply
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

DROP = [5, 6, 7, 8]          # 본편을 미리 요약하던 씬들

# 계기 — 씬11(장손) 다음에 들어간다
NEW = [
    {
        "sceneNumber": 951,
        "narration": "집안은 그를 공부시키려 했습니다. 서울의 중앙고등보통학교까지 보냈으니까요. "
                     "그런데 2년을 마칠 무렵, 학비를 대주던 장인이 세상을 떠납니다. "
                     "구인회는 학업을 접고 고향으로 돌아옵니다.",
        "title": "학비가 끊기던 해",
        "layout": "cinematic",
        "prompt": "레이어 분리형 세모지 3D 다큐 일러스트, 배경: 1920년대 서울 학교 건물의 담장과 겨울 나무, "
                  "중경: 짐을 싸 든 학생 한 명이 교문을 등지고 선 모습, 전경: 손에 들린 낡은 책 보따리, "
                  "차가운 잿빛 하늘과 낮은 겨울 햇빛, 16:9",
    },
    {
        "sceneNumber": 952,
        "narration": "그리고 고향에서 5년이 흐릅니다. "
                     "장손은 붓을 다시 들지 않았습니다. 스물다섯이 되던 해, 그는 집안 어른들 앞에서 말합니다. "
                     "**장사를 하겠습니다.**",
        "title": "스물다섯, 붓을 놓다",
        "layout": "cinematic",
        "prompt": "레이어 분리형 세모지 3D 다큐 일러스트, 배경: 1930년대 한옥 대청마루와 문중 어른들이 앉은 자리, "
                  "중경: 마루 가운데 무릎을 꿇고 앉아 고개를 든 스물다섯 청년, "
                  "전경: 밀어 놓은 벼루와 붓, 창호지로 든 따뜻한 빛, 16:9",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    emap = json.loads((root / "_imggen" / "ep_map.json").read_text(encoding="utf-8"))
    d = Path(next(v["dir"] for k, v in emap.items() if k.startswith("EP01")))
    f = d / "scene_specs.json"
    data = json.loads(f.read_text(encoding="utf-8"))
    scenes = data["scenes"]

    # ① 미리 요약하던 씬을 뺀다
    kept = [s for s in scenes if s.get("sceneNumber") not in DROP]
    print(f"뺌  씬 {DROP} — 본편이 같은 이야기를 제대로 한다")

    # ② 챕터를 한 칸 당긴다. 오프닝(씬1~4)은 챕터 밖(0)으로.
    for s in kept:
        n = s.get("sceneNumber")
        ch = s.get("chapter")
        if n in (1, 2, 3, 4):
            s["chapter"] = 0
        elif isinstance(ch, int) and ch >= 2:
            s["chapter"] = ch - 1
        if s.get("isChapterCard"):
            new_ch = s["chapter"]
            title = (s.get("headline") or "").split("\n", 1)[-1]
            s["headline"] = f"{{{{Chapter {new_ch}}}}}\n{title}"
            s["sceneNumber"] = 900 + new_ch
    print("당김 챕터 2→1, 3→2 … · 오프닝 씬1~4는 챕터 밖")

    # ③ 챕터1 카드를 오프닝 뒤에 세운다
    ch1_title = "선비 집안 장손이 장사꾼이 되다"
    card1 = {
        "sceneNumber": 901, "sceneId": uuid.uuid4().hex[:8], "chapter": 1,
        "isChapterCard": True, "title": "Ch1 카드", "narration": "",
        "headline": f"{{{{Chapter 1}}}}\n{ch1_title}",
        "layout": "headline_only", "infoStructure": "scene",
        "visual_kind": "none", "durationSec": 3.0,
        "imageAsset": {"source": "none"},
    }
    print(f"넣음 Ch1 카드 — {ch1_title}")

    # ④ 계기 두 씬을 씬11 뒤에
    made = []
    for row in NEW:
        made.append({
            "sceneNumber": row["sceneNumber"], "sceneId": uuid.uuid4().hex[:8],
            "chapter": 1, "narration": row["narration"], "title": row["title"],
            "layout": row["layout"], "infoStructure": "scene",
            "visual_kind": "generate_image", "narration_dirty": True,
            "imageAsset": {"source": "generate", "prompt": row["prompt"],
                           "placement": "background"},
        })
        print(f"넣음 씬{row['sceneNumber']} — {row['title']}")

    out = []
    for s in kept:
        out.append(s)
        if s.get("sceneNumber") == 4:
            out.append(card1)
        if s.get("sceneNumber") == 11:
            out.extend(made)

    # 옛 Ch1 카드(=지금 Ch1이 된 것)가 씬11 앞에 남아 있으면 뺀다 — 카드가 둘이 된다
    seen_card1 = False
    final = []
    for s in out:
        if s.get("isChapterCard") and s.get("chapter") == 1:
            if seen_card1:
                continue
            seen_card1 = True
        final.append(s)

    print(f"\n{len(scenes)}씬 → {len(final)}씬")
    print("\n새 앞부분:")
    for s in final[:12]:
        t = (s.get("narration") or "").replace("\n", " ").strip()
        head = (s.get("headline") or "").replace("\n", " / ") if s.get("isChapterCard") else ""
        print(f"  {s['sceneNumber']:4d} Ch{s.get('chapter')} {head}{t[:70]}")

    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(f, f.with_suffix(f".json.bak_restruct_{stamp}"))
        data["scenes"] = final
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장했습니다 (백업 .bak_restruct_{stamp})")
    else:
        print("\n--apply 를 붙이면 실제로 고칩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
