#!/usr/bin/env python3
"""1편 — 왜 장사를 택했는지, 무엇으로 손님을 붙잡았는지 채운다.

앞서 계기를 넣으면서 「혼례를 앞둔 집과 권번의 기생들」이라고 썼는데
틀렸다. 기생은 혼례를 하지 않는다. 확인되지 않은 것을 문장으로 만든
셈이라 걷어낸다.

실제 계기는 기록에 있다 — 경남일보·진주경제발전추진위원회·경상대
기업가정신추진단 공동기획 「일취월장 진주경제[5] 연암 구인회의 기업가 정신」
(https://www.gnnews.co.kr/news/articleView.html?idxno=415989)

  · 진주는 「유행의 도시요 소비의 도시」였다. 부유한 사람들이 모여들었고
    **기생들과 돈 많은 여인들의 사치**가 비단과 외국 포목에 관심을 모았다
  · 연암은 포목상을 **일본인 상인과 경쟁해 성공할 큰 업종**이라고 봤다
  · 이 시기에 **사농공상의 직업 차별 의식에서 완전히 벗어났다**
  · 값을 깎아 주지 않는 대신 **자를 속이지 않았다**
  · 비단·인조견에 **수를 놓거나 무늬를 염색해** 파는 등 소비자 선호를
    조사해 반영했다 ← 「기생에게 비단옷」으로 회자되는 이야기의 실체에
    가장 가까운, 근거 있는 장면

    python3 scripts/ep01_motive.py --apply
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path

SRC = "경남일보 「일취월장 진주경제[5] 연암 구인회의 기업가 정신」"

# 씬952를 갈아 끼우고(계기), 뒤에 953을 새로 붙인다
REPLACE_952 = {
    "narration": "그가 돌아온 진주는 **유행의 도시이자 소비의 도시**였습니다. "
                 "돈이 도는 곳이라 사람이 모였고, 그 돈은 비단과 외국 포목으로 흘렀습니다. "
                 "기생들과 형편이 넉넉한 여인들이 옷에 아낌없이 썼거든요.",
    "title": "돈이 옷으로 흐르던 도시",
    "layout": "cinematic",
    "prompt": "레이어 분리형 세모지 3D 다큐 일러스트, 배경: 1930년대 진주 번화가의 이층 상점 거리와 초저녁 등불, "
              "중경: 비단 두루마기와 고운 색 한복을 입고 지나가는 여인들, "
              "전경: 상점 앞에 펼쳐 놓은 비단 필과 그 위에 떨어진 등불 빛, 16:9",
}

NEW_953 = {
    "sceneNumber": 953,
    "narration": "그 좋은 자리는 일본인 상인들이 쥐고 있었습니다. "
                 "구인회는 거기서 붙어 볼 만하다고 봤습니다. "
                 "선비 집안 장손이 붓을 놓은 건 형편이 어려워서가 아니라, **이길 수 있다고 판단해서**였습니다. "
                 "스물다섯이 되던 해, 그는 집안 어른들 앞에서 말합니다. **장사를 하겠습니다.**",
    "title": "이길 수 있다고 봤다",
    "layout": "cinematic",
    "prompt": "레이어 분리형 세모지 3D 다큐 일러스트, 배경: 1930년대 한옥 대청마루와 문중 어른들이 앉은 자리, "
              "중경: 마루 가운데 무릎을 꿇고 앉아 고개를 든 스물다섯 청년, "
              "전경: 밀어 놓은 벼루와 붓, 창호지로 든 따뜻한 빛, 16:9",
}

# 씬18(구색이 부족했다) 다음 — 취향을 어떻게 읽었나
NEW_954 = {
    "sceneNumber": 954,
    "narration": "그래서 손을 댄 것이 옷감 자체였습니다. "
                 "비단과 인조견에 **수를 놓고, 무늬를 새로 물들여** 내놓았습니다. "
                 "무엇이 팔리는지 묻고 다니며 그때그때 반영했죠. "
                 "값은 깎아 주지 않았습니다. 대신 **자를 속이지 않았습니다.**",
    "title": "수를 놓고 무늬를 물들이다",
    "layout": "cinematic",
    "prompt": "레이어 분리형 세모지 3D 다큐 일러스트, 배경: 1930년대 포목점 안쪽의 나무 선반과 개어 놓은 옷감 더미, "
              "중경: 작업대에 펼친 비단 위로 수를 놓는 손과 물들인 무늬 견본들, "
              "전경: 놋쇠 자와 가위, 창으로 드는 오후 빛, 16:9",
}


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

    def mk(row: dict) -> dict:
        return {
            "sceneNumber": row["sceneNumber"], "sceneId": uuid.uuid4().hex[:8],
            "chapter": 1, "narration": row["narration"], "title": row["title"],
            "layout": row["layout"], "infoStructure": "scene",
            "visual_kind": "generate_image", "narration_dirty": True,
            "source": SRC,
            "imageAsset": {"source": "generate", "prompt": row["prompt"],
                           "placement": "background"},
        }

    out = []
    for s in scenes:
        n = s.get("sceneNumber")
        if n == 952:
            s["narration"] = REPLACE_952["narration"]
            s["title"] = REPLACE_952["title"]
            s["layout"] = REPLACE_952["layout"]
            s["source"] = SRC
            s["narration_dirty"] = True
            (s.setdefault("imageAsset", {})).update(
                {"source": "generate", "prompt": REPLACE_952["prompt"]})
            print(f"고침 씬952 → {REPLACE_952['title']}")
            out.append(s)
            out.append(mk(NEW_953))
            print(f"넣음 씬953 → {NEW_953['title']}")
            continue
        out.append(s)
        if n == 18:
            out.append(mk(NEW_954))
            print(f"넣음 씬954 → {NEW_954['title']}")

    print(f"\n{len(scenes)}씬 → {len(out)}씬")
    print("\n새 흐름 (챕터1 앞부분):")
    for s in out:
        if s.get("chapter") != 1:
            continue
        t = (s.get("narration") or "").replace("\n", " ").strip()
        if s.get("isChapterCard"):
            t = (s.get("headline") or "").replace("\n", " / ")
        print(f"  {s['sceneNumber']:4d} {t[:78]}")
        if s.get("sceneNumber") == 20:
            break

    if args.apply:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(f, f.with_suffix(f".json.bak_motive_{stamp}"))
        data["scenes"] = out
        f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n저장했습니다 (백업 .bak_motive_{stamp})")
    else:
        print("\n--apply 를 붙이면 실제로 고칩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
