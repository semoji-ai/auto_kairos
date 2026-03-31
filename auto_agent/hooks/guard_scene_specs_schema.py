"""Hook: scene_specs 플랫 스키마 검증.

PostToolUse(Write) — scene_specs.json 작성 시 플랫 스키마 위반 검사.
CLAUDE.md §12: 모든 필드는 최상위, visualization.creative 중첩 구조 사용하지 않음.
"""
import json
import sys


BANNED_NESTED_KEYS = ["visualization", "creative", "visualization.creative"]


def check(tool_input: str) -> bool:
    """scene_specs에 중첩 구조가 있으면 True (차단)."""
    try:
        data = json.loads(tool_input)
        file_path = data.get("file_path", "")
        content = data.get("content", "")
    except (json.JSONDecodeError, AttributeError):
        return False

    if "scene_specs" not in file_path:
        return False

    # JSON 내용 파싱
    try:
        specs = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        return False

    # scenes 배열 검사
    scenes = specs if isinstance(specs, list) else specs.get("scenes", [])
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        for key in BANNED_NESTED_KEYS:
            if key in scene:
                print(
                    f"❌ BLOCKED: scene_specs 플랫 스키마 위반 — '{key}' 중첩 구조 감지",
                    file=sys.stderr,
                )
                sys.exit(1)

    return False


if __name__ == "__main__":
    tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
    check(tool_input)
