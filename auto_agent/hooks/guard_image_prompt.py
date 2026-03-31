"""Hook: 이미지 프롬프트 규칙 검증.

PostToolUse(Write) — scene_specs 또는 이미지 관련 파일 작성 시:
1. imageAsset.prompt에 아트스타일 키워드가 있으면 차단
2. imageAsset.prompt에 동작/움직임 표현이 있으면 경고
3. imageAsset.prompt에 텍스트/지도 생성 지시가 있으면 차단
4. imageAsset.source를 반드시 존중 (search/generate)
5. 프롬프트는 한글이어야 함
"""
import json
import re
import sys


# 아트스타일 키워드 (프롬프트에 넣으면 안 됨)
BANNED_STYLE_KEYWORDS = [
    "2d flat", "lego", "stickman", "quirky cartoon", "semoji style",
    "cartoon style", "anime style", "pixel art", "watercolor",
    "oil painting", "nano-banana", "fal-ai",
]

# 동작/움직임 표현 (경고)
MOTION_PATTERNS = [
    r"전환", r"움직이며", r"하는 모습", r"펼쳐지며", r"걸어가", r"달리는",
    r"walking", r"running", r"transitioning", r"revealing", r"moving",
]

# 텍스트/지도 생성 금지
BANNED_CONTENT = [
    r"텍스트.*생성", r"글자.*넣", r"text.*overlay", r"write.*text",
    r"지도.*그", r"map.*draw", r"include.*text", r"add.*text",
]


def check(tool_input: str) -> bool:
    """이미지 프롬프트 규칙 검증."""
    try:
        data = json.loads(tool_input)
        file_path = data.get("file_path", "")
        content = data.get("content", "")
    except (json.JSONDecodeError, AttributeError):
        return False

    if "scene_specs" not in file_path and "image" not in file_path.lower():
        return False

    # JSON 파싱 시도
    try:
        specs = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        # 마크다운이나 다른 형식이면 스킵
        return False

    scenes = specs if isinstance(specs, list) else specs.get("scenes", [])

    for scene in scenes:
        if not isinstance(scene, dict):
            continue

        image_asset = scene.get("imageAsset", {})
        if not isinstance(image_asset, dict):
            continue

        prompt = image_asset.get("prompt", "")
        source = image_asset.get("source", "")

        if not prompt:
            continue

        prompt_lower = prompt.lower()

        # 1. 아트스타일 키워드 차단
        for kw in BANNED_STYLE_KEYWORDS:
            if kw in prompt_lower:
                print(
                    f"❌ BLOCKED: imageAsset.prompt에 아트스타일 키워드 '{kw}' 감지. "
                    f"프롬프트는 내용만, 스타일은 도구가 처리.",
                    file=sys.stderr,
                )
                sys.exit(1)

        # 2. 동작/움직임 경고
        for pattern in MOTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                print(
                    f"⚠️ WARNING: imageAsset.prompt에 동작 표현 감지: '{pattern}'. "
                    f"스틸컷 이미지를 위한 정적 표현으로 변경 권장.",
                    file=sys.stderr,
                )

        # 3. 텍스트/지도 생성 차단
        for pattern in BANNED_CONTENT:
            if re.search(pattern, prompt, re.IGNORECASE):
                print(
                    f"❌ BLOCKED: imageAsset.prompt에 텍스트/지도 생성 지시 감지. "
                    f"이미지에 텍스트/지도는 생성 불가.",
                    file=sys.stderr,
                )
                sys.exit(1)

        # 4. source 존중 확인
        if source and source not in ("search", "generate"):
            print(
                f"⚠️ WARNING: imageAsset.source가 '{source}' — 'search' 또는 'generate'만 허용.",
                file=sys.stderr,
            )

    return False


if __name__ == "__main__":
    tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
    check(tool_input)
