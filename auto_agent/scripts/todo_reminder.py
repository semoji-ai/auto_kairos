"""1시간마다 TODO 리마인더 — 볼트 세션 요약 + TODO.md 통합."""
import os
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_CHANNEL = "1487476019559534642"
VAULT_DIR = Path(os.getenv("KAIROS_VAULT_DIR", ""))


def get_pending_items() -> str:
    """최신 세션 요약 + TODO.md에서 미완료 항목 통합."""
    parts = []

    # 1. 최신 세션 요약에서 "미해결" + "다음 우선순위" 추출
    session_todo = _get_session_todo()
    if session_todo:
        parts.append(session_todo)

    # 2. TODO.md에서 미완료 항목 (보조)
    todo_items = _get_todo_md_items()
    if todo_items:
        parts.append(todo_items)

    if not parts:
        return "✅ 미완료 항목 없음!"

    return "\n".join(parts)


def _get_session_todo() -> str:
    """볼트 09-memory/sessions/ 최신 세션에서 TODO 추출."""
    sessions_dir = VAULT_DIR / "09-memory" / "sessions"
    if not sessions_dir.exists():
        return ""

    files = sorted(sessions_dir.glob("*.md"), reverse=True)
    if not files:
        return ""

    latest = files[0]
    content = latest.read_text(encoding="utf-8")

    # "미해결", "다음 우선순위", "TODO" 섹션 추출
    lines = content.split("\n")
    todo_lines = []
    in_section = False

    for line in lines:
        lower = line.lower()
        if any(k in lower for k in ["미해결", "다음 우선순위", "다음 세션", "todo"]):
            in_section = True
            todo_lines.append(f"**{line.strip().lstrip('#').strip()}**")
        elif in_section:
            if line.startswith("## ") or line.startswith("# "):
                in_section = False
            elif line.strip():
                todo_lines.append(f"  {line.strip()}")

    if not todo_lines:
        return ""

    session_date = latest.stem[:10]
    header = f"📋 **세션 기반 TODO** (최근: {session_date})\n"
    return header + "\n".join(todo_lines)


def _get_todo_md_items() -> str:
    """TODO.md에서 미완료 항목 추출."""
    todo_path = VAULT_DIR / "08-dev" / "TODO.md"
    if not todo_path.exists():
        return ""

    content = todo_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    sections = {}
    current_section = None

    for line in lines:
        if line.startswith("## ") and "완료" not in line and "규칙" not in line:
            current_section = line.replace("## ", "").strip()
            sections[current_section] = []
        elif current_section and line.strip().startswith("- [ ]"):
            item = line.strip().replace("- [ ] ", "")
            sections[current_section].append(item)

    if not sections:
        return ""

    total = sum(len(v) for v in sections.values())
    result = [f"\n📝 **TODO.md** ({total}개 미완료)"]

    for section, items in sections.items():
        if items:
            result.append(f"**{section}**")
            for item in items:
                result.append(f"  • {item}")

    return "\n".join(result)


def main():
    from auto_agent.modules.discord_bot_notify import DiscordBotNotify

    bot = DiscordBotNotify(channel_id=DISCORD_CHANNEL)
    message = get_pending_items()
    bot.send_to_channel(message)


if __name__ == "__main__":
    main()
