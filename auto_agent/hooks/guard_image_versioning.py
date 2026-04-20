"""Hook: 이미지 버전 관리 규칙.

PreToolUse(Write) — 이미지 파일 작성 시:
1. 기존 이미지가 있으면 버전 번호로 생성 (_gen_02, _gen_03)
2. 기존 이미지를 직접 덮어쓰기 금지
3. image_assets.json의 selected 필드로만 전환

CLAUDE.md §9: 이미지 파일 삭제 절대 금지, 새 이미지는 버전 번호로 생성.
"""
import json
import os
import re
import sys


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def check(tool_input: str) -> bool:
    """이미지 버전 관리 규칙 검증."""
    try:
        data = json.loads(tool_input)
        file_path = data.get("file_path", "")
    except (json.JSONDecodeError, AttributeError):
        return False

    # 이미지 파일인지 확인
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in IMAGE_EXTENSIONS:
        return False

    # 기존 파일이 있으면 덮어쓰기 차단
    if os.path.exists(file_path):
        # 버전 번호가 있는지 확인 (_gen_02 등)
        if not re.search(r"_gen_\d+", file_path):
            print(
                f"❌ BLOCKED: 기존 이미지 덮어쓰기 금지. "
                f"버전 번호를 붙여 새 파일로 생성하세요 (예: _gen_02). "
                f"파일: {file_path}",
                file=sys.stderr,
            )
            sys.exit(1)

    return False


if __name__ == "__main__":
    tool_input = sys.argv[1] if len(sys.argv) > 1 else ""
    check(tool_input)
