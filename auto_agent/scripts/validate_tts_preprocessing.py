"""
TTS Preprocessing Validator

scene_specs.json을 읽어 모든 씬의 narration_tts가 TTS-안전한지 검증한다.

검사 항목:
  1. narration이 있는 씬에 narration_tts 필드 존재 여부
  2. narration_tts에 의심 패턴(\\d+, [A-Za-z]{2,}, **) 잔존 여부
  3. 변환 누락된 영문 단위 (km, kg, % 등)

종료 코드:
  0 — 모든 씬 정상
  1 — 의심 패턴 또는 미생성 발견 (stderr로 보고)

사용법:
  python -m auto_agent.scripts.validate_tts_preprocessing <project_dir>
  PROJECT_DIR=<dir> python -m auto_agent.scripts.validate_tts_preprocessing
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# 의심 패턴 정의
SUSPECT_PATTERNS = {
    "digit": re.compile(r"\d+"),
    "english_word": re.compile(r"[A-Za-z]{2,}"),
    "markdown_bold": re.compile(r"\*\*"),
    "markdown_italic": re.compile(r"(?<!\*)\*(?!\*)[^\s*][^*]*(?<!\*)\*(?!\*)"),
}

# 변환 안 된 영문 단위 (단위 자체)
UNCONVERTED_UNITS = re.compile(r"\b(km|kg|cm|mm|ml|mg|nm)\b")


def _resolve_project_dir() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    env = os.environ.get("PROJECT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    print(
        "ERROR: project_dir 인수 또는 PROJECT_DIR 환경변수 필요",
        file=sys.stderr,
    )
    sys.exit(2)


def validate(project_dir: Path) -> int:
    scene_specs = project_dir / "scene_specs.json"
    if not scene_specs.exists():
        print(f"ERROR: {scene_specs} 없음", file=sys.stderr)
        return 2

    try:
        data = json.loads(scene_specs.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: scene_specs.json 파싱 실패: {e}", file=sys.stderr)
        return 2

    scenes = data.get("scenes", [])
    issues: list[dict] = []

    for scene in scenes:
        num = scene.get("sceneNumber") or scene.get("scene_number")
        narration = (scene.get("narration") or "").strip()
        narration_tts = (scene.get("narration_tts") or "").strip()

        # 1. narration 있는데 narration_tts 비어 있음
        if narration and not narration_tts:
            issues.append({
                "scene": num,
                "kind": "missing_narration_tts",
                "detail": "narration이 있지만 narration_tts가 비어 있음",
                "narration": narration[:80],
            })
            continue

        if not narration_tts:
            continue

        # 2. 의심 패턴 검사
        for kind, pat in SUSPECT_PATTERNS.items():
            m = pat.search(narration_tts)
            if m:
                issues.append({
                    "scene": num,
                    "kind": f"suspect_{kind}",
                    "detail": f"패턴 {kind!r} 발견: {m.group(0)!r}",
                    "narration_tts": narration_tts[:120],
                })

        # 3. 변환 안 된 영문 단위
        m = UNCONVERTED_UNITS.search(narration_tts)
        if m:
            issues.append({
                "scene": num,
                "kind": "unconverted_unit",
                "detail": f"미변환 영문 단위 {m.group(0)!r}",
                "narration_tts": narration_tts[:120],
            })

    # 결과 보고
    if not issues:
        print(f"[OK] {len(scenes)}개 씬 모두 TTS 안전 ({scene_specs})")
        return 0

    print(
        f"[FAIL] {len(issues)}건의 TTS 전처리 문제 발견 ({scene_specs})",
        file=sys.stderr,
    )
    for issue in issues:
        print(
            f"  - Scene {issue['scene']}: {issue['kind']} — {issue['detail']}",
            file=sys.stderr,
        )
        if "narration_tts" in issue:
            print(f"      tts: {issue['narration_tts']}", file=sys.stderr)
        if "narration" in issue:
            print(f"      raw: {issue['narration']}", file=sys.stderr)
    print(
        "\n해결: generate_tts.py를 다시 실행하여 narration_tts를 재생성하세요.",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    project_dir = _resolve_project_dir()
    return validate(project_dir)


if __name__ == "__main__":
    raise SystemExit(main())
