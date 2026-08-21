#!/usr/bin/env python3
"""배경 연속성을 데이터로 굳힌다 — 같은 장소는 같은 장소로 그려져야 한다.

씬이 나뉘어 컷이 바뀌어도, 장소와 상황이 이어지는 구간이 있다. 카메라 앵글과
사이즈만 달라질 뿐이다. scene_specs에는 그 장치가 이미 있다.

    background_context      이 씬이 서 있는 장소·상황
    is_first_of_background  그 배경의 첫 컷인가 (전체 구도를 세우는 컷)

그런데 이 두 필드가 비는 씬이 생긴다. 비면 이어지는 컷인지 알 수 없고,
`gen_scenes.py`가 참조할 그룹을 짚지 못해 같은 장소가 매번 다른 장소로 나온다.
인물은 캐릭터 시트로 잡아 두고 장소는 매번 새로 해석되는 상태다.

이 스크립트가 세 가지를 채운다.

  ① is_first_of_background 가 없는 씬 — 앞 씬과 background_context 를 견줘 정한다
  ② 이어짐(false)인데 background_context 가 빈 씬 — 앞 씬에서 물려받는다
  ③ camera 가 빈 씬 — 첫 컷은 전체 구도, 이어짐 컷은 앞 컷과 겹치지 않는 앵글

③이 없으면 같은 배경 세 컷이 똑같이 나오거나 제각각 나온다. 규칙이 요구하는
것은 "같은 배경에서 클로즈업·세부 앵글로 변화"다.

    python3 scripts/enforce_background_continuity.py <project_dir> [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 이어짐 컷에 돌려 쓰는 앵글. 첫 컷이 세운 전체 구도를 파고드는 순서로 둔다.
FOLLOW_ANGLES = [
    "Medium shot, slightly lower angle, same location as the establishing shot",
    "Close-up, straight-on angle, shallow depth of field, same location",
    "Medium close-up, over-the-shoulder, same location",
    "Detail shot, high angle looking down, same location",
    "Wide shot from the opposite side, same location",
]
FIRST_ANGLE = "Wide establishing shot, eye level, full view of the location"


def _cam(scene: dict) -> str:
    return ((scene.get("imageAsset") or {}).get("camera") or "").strip()


def _set_cam(scene: dict, value: str) -> None:
    scene.setdefault("imageAsset", {})["camera"] = value


def enforce(scenes: list[dict]) -> dict:
    stat = {"flag": 0, "bg": 0, "cam_first": 0, "cam_follow": 0, "groups": 0}
    prev_bg = None

    for i, sc in enumerate(scenes):
        bg = (sc.get("background_context") or "").strip()
        flag = sc.get("is_first_of_background")

        # ① 플래그가 없으면 앞 씬의 배경과 견줘 정한다
        if flag is None:
            flag = not (bg and bg == prev_bg)
            # 배경도 비었으면 앞 씬이 있는 한 이어지는 것으로 본다.
            # 끊는 쪽으로 틀리면 참조가 사라지고, 잇는 쪽으로 틀려도
            # 앞 컷을 참조할 뿐이라 손해가 작다.
            if not bg and i > 0:
                flag = False
            sc["is_first_of_background"] = flag
            stat["flag"] += 1

        # ② 이어짐인데 배경이 비었으면 물려받는다
        if flag is False and not bg:
            if prev_bg:
                sc["background_context"] = prev_bg
                bg = prev_bg
                stat["bg"] += 1
            else:
                # 물려받을 것이 없으면 이어짐이라 부를 수 없다
                sc["is_first_of_background"] = True
                flag = True

        # ③ 앵글
        if not _cam(sc):
            if flag:
                _set_cam(sc, FIRST_ANGLE)
                stat["cam_first"] += 1
            else:
                # 그룹 안 몇 번째 이어짐인지로 앵글을 고른다
                k = 0
                for j in range(i - 1, -1, -1):
                    if scenes[j].get("is_first_of_background"):
                        k = i - j - 1
                        break
                _set_cam(sc, FOLLOW_ANGLES[k % len(FOLLOW_ANGLES)])
                stat["cam_follow"] += 1

        if flag:
            stat["groups"] += 1
        prev_bg = sc.get("background_context") or prev_bg

    return stat


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    p = Path(a.project_dir) / "scene_specs.json"
    if not p.exists():
        print(f"ERROR: {p} 없음")
        return 1

    data = json.loads(p.read_text(encoding="utf-8"))
    scenes = data.get("scenes", [])
    st = enforce(scenes)

    print(f"  플래그 부여          {st['flag']}씬")
    print(f"  배경 물려받음        {st['bg']}씬")
    print(f"  앵글 부여 (첫 컷)    {st['cam_first']}씬")
    print(f"  앵글 부여 (이어짐)   {st['cam_follow']}씬")
    print(f"  배경 그룹            {st['groups']}개 / 전체 {len(scenes)}씬")

    # 남은 구멍이 있으면 알린다 — 조용히 넘어가면 그림에서 드러난다
    holes = [s["sceneNumber"] for s in scenes
             if not (s.get("background_context") or "").strip()]
    if holes:
        print(f"  ⚠ background_context 여전히 빈 씬: {len(holes)}개 {holes[:10]}")

    if a.dry_run:
        print("  (dry-run — 저장하지 않음)")
        return 0

    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  저장: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
