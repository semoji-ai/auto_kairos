"""scene_specs.json의 각 씬 narration이 final_manuscript.md의 substring인지 검증.

목적: script-director chapters 모드가 narration을 재작성하지 않고 manuscript에서
substring으로만 가져오는지 확인. PostToolUse hook으로 호출.

사용:
  python -m auto_agent.scripts.validate_narration_from_manuscript <PROJECT_DIR>

종료 코드:
  0 — 모든 narration이 manuscript의 substring (또는 final_manuscript.md 부재 시 skip)
  1 — 1개 이상 위반 (재작성 발견)

stderr로 위반 내역 출력 → LLM이 인지 가능.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _normalize(text: str) -> str:
    """공백/줄바꿈 정규화 — substring 매칭 시 미세 차이 무시."""
    return re.sub(r"\s+", " ", text).strip()


def validate(project_dir: Path) -> int:
    scene_specs = project_dir / "scene_specs.json"
    manuscript = project_dir / "final_manuscript.md"

    if not scene_specs.exists():
        # scene_specs가 없으면 검증할 게 없음 (다른 step의 작업)
        return 0
    if not manuscript.exists():
        # manuscript가 없으면 (legacy 흐름 또는 manuscript step 미실행) 검증 skip
        return 0

    try:
        specs = json.loads(scene_specs.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[validate_narration] scene_specs.json 파싱 실패: {e}", file=sys.stderr)
        return 1

    try:
        ms_text = manuscript.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[validate_narration] final_manuscript.md 읽기 실패: {e}", file=sys.stderr)
        return 1

    ms_norm = _normalize(ms_text)
    if not ms_norm:
        return 0  # 빈 manuscript

    scenes = specs.get("scenes", [])
    if not scenes:
        return 0

    violations: list[str] = []
    for scene in scenes:
        num = scene.get("sceneNumber") or scene.get("scene_number") or "?"
        narration = scene.get("narration", "")
        if not narration:
            continue
        narration_norm = _normalize(narration)
        if not narration_norm:
            continue
        if narration_norm not in ms_norm:
            # 부분 매칭이라도 가능한지 — 60% 이상의 단어가 manuscript에 등장하면 통과
            # (구두점/연결어 미세 변경은 허용)
            words = [w for w in re.split(r"\s+", narration_norm) if len(w) >= 2]
            if not words:
                continue
            hit = sum(1 for w in words if w in ms_norm)
            ratio = hit / len(words)
            if ratio < 0.6:
                snippet = narration_norm[:80]
                violations.append(
                    f"  씬 {num}: '{snippet}{'...' if len(narration_norm) > 80 else ''}' "
                    f"(단어 매칭률 {ratio:.0%})"
                )

    if violations:
        print(
            f"[validate_narration] ❌ {len(violations)}개 씬의 narration이 "
            f"final_manuscript.md에서 벗어났습니다 (재작성 의심):",
            file=sys.stderr,
        )
        for v in violations:
            print(v, file=sys.stderr)
        print(
            "\n해결: chapters 모드는 manuscript의 prose를 substring으로 자르기만 합니다. "
            "재작성/요약/단어 교체 금지. 다듬기가 필요하면 manuscript를 먼저 수정하세요.",
            file=sys.stderr,
        )
        return 1

    print(
        f"[validate_narration] ✓ {len(scenes)}개 씬 narration 모두 manuscript에서 유래",
        file=sys.stderr,
    )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        # 환경변수 fallback
        import os

        proj = os.environ.get("PROJECT_DIR", "")
        if not proj:
            print(
                "Usage: python -m auto_agent.scripts.validate_narration_from_manuscript <PROJECT_DIR>",
                file=sys.stderr,
            )
            return 0  # 인자 없으면 silent skip (hook 안전)
        project_dir = Path(proj)
    else:
        project_dir = Path(sys.argv[1])

    if not project_dir.exists() or not project_dir.is_dir():
        return 0  # 디렉토리 없으면 silent skip

    return validate(project_dir)


if __name__ == "__main__":
    sys.exit(main())
