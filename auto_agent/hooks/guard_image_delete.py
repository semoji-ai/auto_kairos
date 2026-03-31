"""Hook: 이미지 삭제 명령 차단.

PreToolUse(Bash) — rm 명령에 이미지 파일이 포함되면 차단.
CLAUDE.md §9: 이미지 파일 삭제 절대 금지.
"""
import json
import re
import sys


def check(tool_input: str) -> bool:
    """삭제 명령에 이미지 파일이 포함되면 True (차단)."""
    try:
        data = json.loads(tool_input)
        command = data.get("command", "")
    except (json.JSONDecodeError, AttributeError):
        command = tool_input

    # rm 명령 감지
    if not re.search(r"\brm\b", command):
        return False

    # 이미지 파일 확장자 감지
    image_patterns = [
        r"scene_\d+", r"\.png\b", r"\.jpg\b", r"\.jpeg\b",
        r"\.webp\b", r"_gen_\d+", r"character_",
    ]
    for pattern in image_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            print(f"❌ BLOCKED: 이미지 삭제 명령 차단 — {command[:100]}", file=sys.stderr)
            sys.exit(1)

    return False


if __name__ == "__main__":
    tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
    check(tool_input)
