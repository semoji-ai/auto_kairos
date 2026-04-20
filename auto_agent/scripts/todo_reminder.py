"""1시간마다 TODO 리마인더 — TODO.md 단일 소스."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_CHANNEL = "1487476019559534642"
VAULT_DIR = Path(os.getenv("KAIROS_VAULT_DIR", ""))


def get_pending_items() -> str:
    """TODO.md에서 미완료 항목 추출."""
    todo_path = VAULT_DIR / "08-dev" / "TODO.md"
    if not todo_path.exists():
        return "✅ TODO.md 파일 없음"

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

    if not sections or all(len(v) == 0 for v in sections.values()):
        return "✅ 미완료 항목 없음!"

    total = sum(len(v) for v in sections.values())
    result = [f"📝 **TODO** ({total}개 미완료)"]

    for section, items in sections.items():
        if items:
            result.append(f"\n**{section}**")
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
