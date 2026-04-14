#!/usr/bin/env python3
"""
generate_presets.py — 아트스타일 JSON → TypeScript 프리셋 자동 생성

단일 소스(artstyle/styles/*.json)에서 remotion/src/design/presets/*.ts와
auto_agent/remotion_template/src/design/presets/*.ts를 자동 생성합니다.

사용법:
  python scripts/generate_presets.py           # 전체 재생성
  python scripts/generate_presets.py quirky_cartoon   # 특정 스타일만
  python scripts/generate_presets.py --check   # 변경사항 없는지 확인 (CI용)
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = REPO_ROOT / "auto_agent" / "data" / "artstyle" / "styles"
PRESET_DIRS = [
    REPO_ROOT / "remotion" / "src" / "design" / "presets",
    REPO_ROOT / "auto_agent" / "remotion_template" / "src" / "design" / "presets",
]

# snake_case → PascalCase 변환 (예: quirky_cartoon → QuirkyCartoon)
def to_pascal(s: str) -> str:
    return "".join(w.capitalize() for w in s.split("_"))


def json_to_ts_value(val, indent: int = 2) -> str:
    """JSON 값을 TypeScript 리터럴로 변환."""
    pad = " " * indent
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, str):
        escaped = val.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
        return f'"{val}"'
    if isinstance(val, list):
        if not val:
            return "[]"
        items = [f"{pad}  {json_to_ts_value(v, indent + 2)}" for v in val]
        return "[\n" + ",\n".join(items) + f",\n{pad}]"
    if isinstance(val, dict):
        if not val:
            return "{}"
        lines = []
        for k, v in val.items():
            key = f'"{k}"' if not k.isidentifier() or "-" in k else k
            lines.append(f"{pad}  {key}: {json_to_ts_value(v, indent + 2)},")
        return "{\n" + "\n".join(lines) + f"\n{pad}}}"
    return "undefined"


def build_preset_obj(dt: dict, style_id: str) -> dict:
    """design_tokens에서 TS 프리셋 오브젝트 구성."""
    preset: dict = {"artStyle": style_id}

    if base_theme := dt.get("baseTheme"):
        preset["baseTheme"] = base_theme

    # colors (accent 계열만 — bg/text는 baseTheme에서 자동)
    color_keys = [
        "accent", "accentRgb", "accentBg", "accentBorder", "accentSoft",
        "cardBg", "cardBorder",
    ]
    colors = dt.get("colors", {})
    color_obj = {k: colors[k] for k in color_keys if k in colors}
    if color_obj:
        preset["colors"] = color_obj

    # layout
    if layout := dt.get("layout"):
        preset["layout"] = layout

    # map
    if map_cfg := dt.get("map"):
        preset["map"] = map_cfg

    # fonts (design_tokens.fonts 섹션)
    fonts = dt.get("fonts", {})
    if fonts:
        preset["fonts"] = fonts

    # subtitle (design_tokens.subtitle 섹션 — fontFamily/fontSize/color 등)
    subtitle = dt.get("subtitle", {})
    if subtitle:
        # TS 프리셋에서 관리할 필드만 포함 (max_chars_per_line은 Python 전용)
        ts_subtitle_keys = [
            "fontSize", "fontFamily", "fontWeight", "color",
            "strokeWidth", "strokeColor",
            "keywordColor", "keywordStrokeColor",
            "backgroundColor", "borderRadius", "boxShadow",
            "bottomOffset", "maxWidth", "lineHeight",
        ]
        sub_obj = {k: subtitle[k] for k in ts_subtitle_keys if k in subtitle}
        if sub_obj:
            preset["subtitle"] = sub_obj

    return preset


def render_ts(style_id: str, preset_obj: dict) -> str:
    """프리셋 오브젝트를 TypeScript 소스로 렌더링."""
    pascal = to_pascal(style_id)
    const_name = f"{pascal.upper()}_PRESET"

    lines = [
        "// AUTO-GENERATED — auto_agent/data/artstyle/styles/{}.json에서 생성".format(style_id),
        "// 직접 수정 금지. JSON을 수정한 후 scripts/generate_presets.py를 실행하세요.",
        'import type { DesignPresetOverride } from "../types";',
        "",
        f"export const {const_name}: DesignPresetOverride = {{",
    ]

    for key, val in preset_obj.items():
        ts_val = json_to_ts_value(val, indent=2)
        lines.append(f"  {key}: {ts_val},")

    lines += ["};", ""]
    return "\n".join(lines)


def render_index(style_ids: list[str]) -> str:
    """index.ts — 모든 프리셋을 ART_PRESETS에 등록."""
    lines = [
        "// AUTO-GENERATED — scripts/generate_presets.py",
        "// 직접 수정 금지.",
        'import type { DesignPresetOverride } from "../types";',
    ]
    for sid in sorted(style_ids):
        pascal = to_pascal(sid)
        const = f"{pascal.upper()}_PRESET"
        lines.append(f'import {{ {const} }} from "./{sid}";')

    lines += [
        "",
        "export const ART_PRESETS: Record<string, DesignPresetOverride> = {",
    ]
    for sid in sorted(style_ids):
        pascal = to_pascal(sid)
        const = f"{pascal.upper()}_PRESET"
        lines.append(f"  {sid}: {const},")
    lines += ["};", ""]
    return "\n".join(lines)


def generate_style(style_id: str, check_only: bool = False) -> bool:
    """단일 스타일 JSON → TS 생성. 변경 있으면 True 반환."""
    json_path = STYLES_DIR / f"{style_id}.json"
    if not json_path.exists():
        print(f"  [SKIP] {style_id}.json 없음", file=sys.stderr)
        return False

    data = json.loads(json_path.read_text(encoding="utf-8"))
    dt = data.get("design_tokens", {})
    preset_obj = build_preset_obj(dt, style_id)
    ts_content = render_ts(style_id, preset_obj)

    changed = False
    for preset_dir in PRESET_DIRS:
        if not preset_dir.exists():
            continue
        out_path = preset_dir / f"{style_id}.ts"
        existing = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if existing != ts_content:
            changed = True
            if check_only:
                print(f"  [OUTDATED] {out_path.relative_to(REPO_ROOT)}")
            else:
                out_path.write_text(ts_content, encoding="utf-8")
                print(f"  [GENERATED] {out_path.relative_to(REPO_ROOT)}")
        else:
            if not check_only:
                print(f"  [OK] {out_path.relative_to(REPO_ROOT)} (변경 없음)")

    return changed


def generate_index(style_ids: list[str], check_only: bool = False) -> bool:
    """index.ts 재생성."""
    index_content = render_index(style_ids)
    changed = False
    for preset_dir in PRESET_DIRS:
        if not preset_dir.exists():
            continue
        out_path = preset_dir / "index.ts"
        existing = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
        if existing != index_content:
            changed = True
            if check_only:
                print(f"  [OUTDATED] {out_path.relative_to(REPO_ROOT)}")
            else:
                out_path.write_text(index_content, encoding="utf-8")
                print(f"  [GENERATED] {out_path.relative_to(REPO_ROOT)}")
        else:
            if not check_only:
                print(f"  [OK] {out_path.relative_to(REPO_ROOT)} (변경 없음)")
    return changed


def main():
    parser = argparse.ArgumentParser(description="아트스타일 JSON → TS 프리셋 생성")
    parser.add_argument("styles", nargs="*", help="생성할 스타일 ID (미지정 시 전체)")
    parser.add_argument("--check", action="store_true", help="변경사항만 확인 (파일 수정 없음)")
    args = parser.parse_args()

    # 대상 스타일 목록
    if args.styles:
        style_ids = args.styles
    else:
        style_ids = sorted(
            p.stem for p in STYLES_DIR.glob("*.json")
        )

    print(f"{'[CHECK]' if args.check else '[GENERATE]'} 아트스타일 프리셋 {'확인' if args.check else '생성'}: {', '.join(style_ids)}")
    print()

    any_changed = False
    for sid in style_ids:
        changed = generate_style(sid, check_only=args.check)
        any_changed = any_changed or changed

    # index.ts
    all_ids = sorted(p.stem for p in STYLES_DIR.glob("*.json"))
    changed = generate_index(all_ids, check_only=args.check)
    any_changed = any_changed or changed

    print()
    if args.check and any_changed:
        print("오래된 TS 프리셋 발견 — scripts/generate_presets.py를 실행하세요.")
        sys.exit(1)
    elif not any_changed:
        print("모든 프리셋이 최신 상태입니다.")
    else:
        print("프리셋 생성 완료.")


if __name__ == "__main__":
    main()
