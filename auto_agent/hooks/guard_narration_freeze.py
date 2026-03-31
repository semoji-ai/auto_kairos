"""Hook: 나레이션 텍스트 변경 차단.

PreToolUse(Write) — assembly-director가 scene_specs의 narration을 수정하려고 하면 차단.
script-director만 narration을 작성할 수 있음.
"""
import json
import sys


def check(tool_input: str) -> bool:
    """scene_specs의 narration 필드가 변경되면 True (차단)."""
    try:
        data = json.loads(tool_input)
        file_path = data.get("file_path", "")
    except (json.JSONDecodeError, AttributeError):
        return False

    if "scene_specs" not in file_path:
        return False

    # assembly-director 컨텍스트에서 narration 변경 감지
    # 현재 단계가 Stage 3(assembly)인지 확인
    # Stage 3에서는 narration 필드를 건드리면 안 됨
    # 단, TTS 전처리(숫자 변환 등)는 별도 모듈에서 처리하므로 여기서는 차단

    # TODO: 단계 컨텍스트 확인 로직 추가
    # 현재는 경고만 출력
    print(
        "⚠️ WARNING: scene_specs 나레이션 변경 감지. "
        "assembly-director는 narration을 수정하면 안 됩니다.",
        file=sys.stderr,
    )

    return False


if __name__ == "__main__":
    tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
    check(tool_input)
