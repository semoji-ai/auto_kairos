"""파이프라인 에이전트용 PreToolUse 가드 — 이미지 삭제·덮어쓰기를 실제로 막는다.

예전에는 runner.py 의 HookManager.register_pre_tool 로 등록했지만, 에이전트는
`claude` CLI 서브프로세스로 돌기 때문에 그 가드는 한 번도 호출되지 않았다.
규칙은 프롬프트에만 있었고 코드로는 막히지 않았다.

이 스크립트는 Claude Code 훅 계약을 따른다: stdin 으로 도구 호출 JSON 을 받고,
막을 때는 exit 2 + stderr 로 이유를 돌려준다(모델이 그 이유를 읽고 다른 길을 찾는다).
연결: execution.agent_hook_settings() 가 만든 설정을 run_cli 가 `--settings` 로 넘긴다.
"""
from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

IMAGE = re.compile(r"(scene_\d+|_gen_\d+|\.(png|jpe?g|webp)\b)", re.IGNORECASE)
DELETE = re.compile(r"(^|[;&|\s])(rm|unlink|trash)\s")
FIND_DELETE = re.compile(r"\bfind\b.*-delete\b")
COPY_MOVE = re.compile(r"(^|[;&|]\s*)(cp|mv)\s[^;&|]+")


def _overwrites_existing_image(cmd: str, cwd: str) -> bool:
    """cp/mv 의 목적지가 이미 있는 이미지 파일이면 참 — 새 버전 저장은 통과시킨다."""
    for m in COPY_MOVE.finditer(cmd):
        try:
            args = [a for a in shlex.split(m.group(0))[1:] if not a.startswith("-")]
        except ValueError:
            continue
        if len(args) < 2 or not IMAGE.search(args[-1]):
            continue
        dest = Path(args[-1]).expanduser()
        if not dest.is_absolute():
            dest = Path(cwd or ".") / dest
        if dest.is_file():
            return True
    return False


def check(tool_name: str, tool_input: dict, cwd: str = "") -> str | None:
    if tool_name != "Bash":
        return None
    cmd = str(tool_input.get("command", ""))
    if (DELETE.search(cmd) or FIND_DELETE.search(cmd)) and IMAGE.search(cmd):
        return ("이미지 파일 삭제는 막혀 있습니다(CLAUDE.md 필수 규칙 2). "
                "재생성본은 새 버전 번호(_gen_02 …)로 만들고 image_assets.json 의 selected 만 바꾸세요.")
    if _overwrites_existing_image(cmd, cwd):
        return ("기존 버전 이미지 위에 덮어쓰는 cp/mv 는 막혀 있습니다. "
                "빈 버전 번호로 저장하고 selected 를 바꾸세요.")
    return None


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    reason = check(data.get("tool_name", ""), data.get("tool_input") or {}, data.get("cwd", ""))
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
