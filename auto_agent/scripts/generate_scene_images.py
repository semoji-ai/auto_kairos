"""
씬 이미지 일괄 생성 스크립트

scene_specs.json에서 imageAsset이 있는 씬을 찾아
FAL AI nano-banana-2로 이미지를 생성한다.

캐릭터 레퍼런스:
  - characters/investor.png -> 메인 투자자 (PERSON 씬)
  - characters/warren_buffett.png -> 워런 버핏 (Scene 1)
"""
import json
import sys
import os
from pathlib import Path

from auto_agent.paths import get_workspace_dir, get_data_dir, DATA_DIR

from dotenv import load_dotenv
load_dotenv(get_workspace_dir() / ".env")

from auto_agent.tools.image_generate import generate_scene, generate_scene_flat
from auto_agent.scripts.project_paths import get_project_dir

PROJECT_ROOT = get_workspace_dir()  # 하위 호환

# 캐릭터가 필요한 씬과 캐릭터 매핑
PERSON_SCENES = {
    1:  {"chars": ["warren_buffett"], "info": "워런 버핏 실루엣"},
    4:  {"chars": ["investor"], "info": "두 권투 선수 (인덱스펀드 vs 헤지펀드)"},
    22: {"chars": ["investor"], "info": "교수 캐릭터가 칠판 앞에서 설명"},
    25: {"chars": ["investor"], "info": "밝은 표정으로 스마트폰으로 주식 구매"},
    30: {"chars": ["investor"], "info": "급여를 투자 통에 넣는 직장인"},
    37: {"chars": ["investor"], "info": "하락하는 차트를 보며 걱정하다 반등에 놀라는 투자자"},
    40: {"chars": ["investor"], "info": "명상하며 평온한 현명한 투자자"},
    44: {"chars": ["investor"], "info": "골짜기에서 올라가는 결연한 투자자"},
    45: {"chars": ["investor"], "info": "빨간 경고 사인에 둘러싸여 당황하는 투자자"},
    48: {"chars": ["investor"], "info": "출발선에 서서 자신있게 투자 여정을 시작하는 투자자"},
}


def main():
    project_dir = get_project_dir()
    scene_specs_path = project_dir / "scene_specs.json"
    images_dir = project_dir / "images"
    characters_dir = project_dir / "characters"
    images_dir.mkdir(parents=True, exist_ok=True)

    style_path = str(DATA_DIR / "artstyle" / "styles" / "quirky_cartoon.json")

    with open(scene_specs_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data["scenes"]
    targets = []

    for scene in scenes:
        ia = scene.get("imageAsset")
        if not ia:
            continue
        source = ia.get("source", "")
        if source != "generate":
            continue

        num = scene["sceneNumber"]
        output_path = images_dir / f"scene_{num:03d}.png"

        # 이미 생성된 이미지가 있으면 건너뛰기
        if output_path.exists():
            print(f"  Scene {num}: EXISTS -- skip")
            continue

        # 캐릭터 매핑
        person_info = PERSON_SCENES.get(num)
        char_paths = []
        chars_info = None
        if person_info:
            for char_name in person_info["chars"]:
                char_path = characters_dir / f"{char_name}.png"
                if char_path.exists():
                    char_paths.append(str(char_path))
            chars_info = person_info["info"]

        # placement에 따른 이미지 비율 결정
        placement = ia.get("placement", "background")
        if placement in ("right", "left"):
            aspect_ratio = "3:4"  # 에셋 이미지 (화면 한쪽 배치)
        else:
            aspect_ratio = "16:9"  # 배경 이미지 (전체 화면)

        targets.append({
            "sceneNumber": num,
            "query": ia.get("query", ""),
            "output_path": str(output_path),
            "characters": char_paths if char_paths else None,
            "characters_info": chars_info,
            "has_person": bool(person_info),
            "aspect_ratio": aspect_ratio,
            "placement": placement,
        })

    total = len(targets)
    print(f"이미지 생성 대상: {total}개 씬")
    print(f"  - 캐릭터 포함: {sum(1 for t in targets if t['has_person'])}개")
    print(f"  - 오브젝트 전용: {sum(1 for t in targets if not t['has_person'])}개")
    print(f"  - 에셋(3:4): {sum(1 for t in targets if t['aspect_ratio'] == '3:4')}개")
    print(f"  - 배경(16:9): {sum(1 for t in targets if t['aspect_ratio'] == '16:9')}개")

    success = 0
    fail = 0

    for i, t in enumerate(targets):
        num = t["sceneNumber"]
        query = t["query"]
        output = t["output_path"]

        print(f"\n[{i+1}/{total}] Scene {num}: 생성 중... ({t['placement']}, {t['aspect_ratio']})")
        print(f"  Prompt: {query[:80]}...")
        if t["characters"]:
            print(f"  Characters: {[Path(c).stem for c in t['characters']]}")

        try:
            if t["characters"]:
                # 캐릭터 레퍼런스가 있는 씬 -> generate_scene (cinematic)
                result = generate_scene(
                    prompt=query,
                    output_path=output,
                    style_path=style_path,
                    characters=t["characters"],
                    characters_info=t["characters_info"],
                    aspect_ratio=t["aspect_ratio"],
                )
            else:
                # 오브젝트 씬 -> generate_scene_flat
                result = generate_scene_flat(
                    prompt=query,
                    output_path=output,
                    style_path=style_path,
                    aspect_ratio=t["aspect_ratio"],
                )

            if result.get("success"):
                w = result.get("width", 0)
                h = result.get("height", 0)
                print(f"  OK -- {w}x{h}")
                success += 1
            else:
                print(f"  FAIL -- {result.get('error', 'unknown')}")
                fail += 1

        except Exception as e:
            print(f"  ERROR -- {e}")
            fail += 1

    print(f"\n완료: 성공 {success}, 실패 {fail} / 총 {total}")


if __name__ == "__main__":
    main()
