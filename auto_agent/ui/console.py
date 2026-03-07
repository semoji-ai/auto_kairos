"""Rich Console 래퍼 — 브랜드 테마 + 공통 출력 헬퍼."""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

AUTO_AGENT_THEME = Theme(
    {
        "accent": "bold #F59E0B",
        "success": "bold green",
        "error": "bold red",
        "warning": "bold yellow",
        "info": "bold cyan",
        "muted": "dim",
    }
)

console = Console(theme=AUTO_AGENT_THEME)


def print_header(title: str):
    """브랜드 헤더 패널 출력."""
    console.print(Panel(f"[accent]{title}[/accent]", border_style="#F59E0B"))


def print_error(msg: str):
    console.print(f"[error]  ERROR [/error] {msg}")


def print_success(msg: str):
    console.print(f"[success]  ✓ [/success] {msg}")


def print_warning(msg: str):
    console.print(f"[warning]  WARN [/warning] {msg}")


def is_non_interactive() -> bool:
    """--non-interactive 플래그 또는 비-TTY 환경이면 True."""
    if "--non-interactive" in sys.argv:
        return True
    return not sys.stdin.isatty()
