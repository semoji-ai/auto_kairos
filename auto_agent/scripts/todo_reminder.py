"""1시간마다 TODO 미완료 항목을 디스코드에 알림."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

DISCORD_CHANNEL = "1487476019559534642"
VAULT_TODO = os.getenv("KAIROS_VAULT_DIR", "") + "/08-dev/TODO.md"


def get_pending_items() -> str:
    """TODO.md에서 미완료 항목 추출."""
    p = Path(VAULT_TODO)
    if not p.exists():
        return "TODO.md를 찾을 수 없습니다."

    content = p.read_text(encoding="utf-8")
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
        return "✅ 미완료 항목 없음!"

    total = sum(len(v) for v in sections.values())
    result = [f"📋 **TODO 리마인더** ({total}개 미완료)\n"]

    for section, items in sections.items():
        if items:
            result.append(f"**{section}**")
            for item in items[:3]:  # 섹션당 최대 3개
                result.append(f"  • {item[:80]}")
            if len(items) > 3:
                result.append(f"  ... 외 {len(items)-3}개")
            result.append("")

    return "\n".join(result)


def main():
    from auto_agent.modules.discord_bot_notify import DiscordBotNotify

    bot = DiscordBotNotify(channel_id=DISCORD_CHANNEL)
    message = get_pending_items()
    bot.send_to_channel(message)


if __name__ == "__main__":
    main()
