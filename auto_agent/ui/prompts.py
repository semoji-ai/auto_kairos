"""인터랙티브 프롬프트 -- questionary 기반."""

import json
from pathlib import Path

import questionary
from questionary import Choice, Style

from .console import print_header

# SimpleVideo 브랜드와 통일된 프롬프트 스타일
PROMPT_STYLE = Style(
    [
        ("qmark", "fg:#F59E0B bold"),
        ("question", "fg:white bold"),
        ("answer", "fg:#F59E0B bold"),
        ("pointer", "fg:#F59E0B bold"),
        ("highlighted", "fg:#F59E0B bold"),
        ("selected", "fg:white"),
    ]
)


def _ask_or_abort(question):
    """questionary 질문 실행. Ctrl+C 시 KeyboardInterrupt."""
    result = question.ask()
    if result is None:
        raise KeyboardInterrupt
    return result


# ── 개별 프롬프트 ────────────────────────────

def prompt_theme() -> str:
    """테마 선택."""
    return _ask_or_abort(
        questionary.select(
            "테마를 선택하세요:",
            choices=[
                Choice("Simple  (블랙 + 오렌지, 기본)", value="simple"),
                Choice("Kairos  (크림, 레거시)", value="kairos"),
            ],
            default="simple",
            style=PROMPT_STYLE,
        )
    )


def _scan_art_styles() -> list:
    """패키지 + 워크스페이스의 아트스타일 JSON 스캔."""
    from auto_agent.paths import get_data_dir, get_workspace_dir

    seen = set()
    styles = []

    for base in [get_data_dir(), get_workspace_dir()]:
        styles_dir = base / "artstyle" / "styles"
        if not styles_dir.exists():
            continue
        for f in sorted(styles_dir.glob("*.json")):
            if f.name in seen:
                continue
            seen.add(f.name)
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                styles.append(
                    {
                        "name": data.get("name", f.stem),
                        "description": data.get("description", ""),
                        "path": str(f),
                        "filename": f.name,
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
    return styles


def prompt_art_style() -> str:
    """아트스타일 선택. 경로 문자열 반환."""
    styles = _scan_art_styles()
    if not styles:
        return ""

    choices = [
        Choice(
            f"{s['name']}  --  {s['description'][:50]}" if s["description"] else s["name"],
            value=s["path"],
        )
        for s in styles
    ]

    return _ask_or_abort(
        questionary.select(
            "아트스타일을 선택하세요:",
            choices=choices,
            style=PROMPT_STYLE,
        )
    )


def prompt_voice() -> tuple:
    """음성 선택. (voice_id, voice_settings) 반환."""
    from auto_agent.voice_manager import VoiceManager

    vm = VoiceManager()
    presets = vm.list_voices()

    choices = []
    for p in presets:
        vid = p.get("voice_id", "")
        label = f"{p['name']}  ({vid[:12]}...)" if len(vid) > 12 else f"{p['name']}  ({vid})"
        choices.append(Choice(label, value=p))

    choices.append(Choice("직접 입력 (ElevenLabs Voice ID)", value="__custom__"))

    selected = _ask_or_abort(
        questionary.select(
            "음성을 선택하세요:",
            choices=choices,
            style=PROMPT_STYLE,
        )
    )

    if selected == "__custom__":
        voice_id = _ask_or_abort(
            questionary.text(
                "ElevenLabs Voice ID:",
                validate=lambda t: len(t.strip()) > 0 or "ID를 입력해주세요",
                style=PROMPT_STYLE,
            )
        )
        return voice_id.strip(), None

    return selected["voice_id"], selected.get("voice_settings")


def prompt_confirm(message: str, default: bool = True) -> bool:
    """확인 프롬프트."""
    return _ask_or_abort(
        questionary.confirm(message, default=default, style=PROMPT_STYLE)
    )


# ── 통합: 프로젝트 생성 ────────────────────────

def prompt_project_create() -> dict:
    """인터랙티브 프로젝트 생성 플로우.

    Returns:
        {name, slug, topic, theme, art_style, voice_id, voice_settings}
    """
    print_header("auto-agent -- 새 프로젝트 만들기")

    name = _ask_or_abort(
        questionary.text(
            "프로젝트 이름:",
            validate=lambda t: len(t.strip()) > 0 or "이름을 입력해주세요",
            style=PROMPT_STYLE,
        )
    )

    from auto_agent.scripts.project_paths import slugify

    slug = slugify(name)

    topic = _ask_or_abort(
        questionary.text(
            "영상 주제/제목:",
            validate=lambda t: len(t.strip()) > 0 or "주제를 입력해주세요",
            style=PROMPT_STYLE,
        )
    )

    theme = prompt_theme()
    art_style = prompt_art_style()
    voice_id, voice_settings = prompt_voice()

    return {
        "name": name.strip(),
        "slug": slug,
        "topic": topic.strip(),
        "theme": theme,
        "art_style": art_style,
        "voice_id": voice_id,
        "voice_settings": voice_settings,
    }


def prompt_voice_add() -> dict:
    """음성 프리셋 추가 프롬프트.

    Returns:
        {name, voice_id, description}
    """
    print_header("음성 프리셋 추가")

    name = _ask_or_abort(
        questionary.text(
            "프리셋 이름:",
            validate=lambda t: len(t.strip()) > 0 or "이름을 입력해주세요",
            style=PROMPT_STYLE,
        )
    )
    voice_id = _ask_or_abort(
        questionary.text(
            "ElevenLabs Voice ID:",
            validate=lambda t: len(t.strip()) > 0 or "ID를 입력해주세요",
            style=PROMPT_STYLE,
        )
    )
    description = _ask_or_abort(
        questionary.text(
            "설명 (선택사항):",
            default="",
            style=PROMPT_STYLE,
        )
    )

    return {
        "name": name.strip(),
        "voice_id": voice_id.strip(),
        "description": description.strip(),
    }


def prompt_font() -> str:
    """인터랙티브 폰트 선택. 퍼지 검색으로 시스템 폰트 + 번들 폰트 선택.

    Returns:
        선택된 폰트 패밀리 이름
    """
    from auto_agent.font_manager import FontManager, DEFAULT_FONT

    fm = FontManager()
    all_fonts = fm.list_fonts()

    if not all_fonts:
        return DEFAULT_FONT

    selected = _ask_or_abort(
        questionary.autocomplete(
            "폰트를 선택하세요 (입력하여 검색):",
            choices=[f["family"] for f in all_fonts],
            default=DEFAULT_FONT,
            style=PROMPT_STYLE,
            validate=lambda t: len(t.strip()) > 0 or "폰트를 선택해주세요",
        )
    )

    return selected.strip()


def prompt_style_add() -> dict:
    """아트스타일 추가 프롬프트.

    Returns:
        {name, description, art_style, color_palette, mood_and_tone}
    """
    print_header("아트스타일 추가")

    name = _ask_or_abort(
        questionary.text(
            "스타일 이름:",
            validate=lambda t: len(t.strip()) > 0 or "이름을 입력해주세요",
            style=PROMPT_STYLE,
        )
    )
    description = _ask_or_abort(
        questionary.text(
            "간단한 설명:",
            style=PROMPT_STYLE,
        )
    )
    art_style = _ask_or_abort(
        questionary.text(
            "화풍 설명 (영어, 이미지 생성 프롬프트에 사용):",
            style=PROMPT_STYLE,
        )
    )
    color_palette = _ask_or_abort(
        questionary.text(
            "컬러 팔레트 설명 (선택사항):",
            default="Vibrant and bold colors",
            style=PROMPT_STYLE,
        )
    )
    mood = _ask_or_abort(
        questionary.text(
            "분위기/톤 (선택사항):",
            default="Friendly and engaging",
            style=PROMPT_STYLE,
        )
    )

    return {
        "name": name.strip(),
        "description": description.strip(),
        "art_style": art_style.strip(),
        "color_palette": color_palette.strip(),
        "mood_and_tone": mood.strip(),
    }
