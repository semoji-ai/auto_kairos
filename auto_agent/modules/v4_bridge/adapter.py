"""v4 research/script artifacts → v3 Stage 2 input adapter (top-level pipeline)."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from .build_outline import build_outline
from .build_research_report import build_research_report
from .build_art_style import build_art_style
from .chapter_marker import insert_markers


def _resolve_project_dir(project: str) -> Path:
    """slug 또는 절대경로 → 유일한 프로젝트 디렉토리 Path 반환."""
    p = Path(project)
    if p.is_absolute():
        if not p.exists():
            raise FileNotFoundError(f"프로젝트 경로가 존재하지 않습니다: {p}")
        return p

    # slug 검색: output/*_<slug>/
    output_dir = Path(__file__).parent.parent.parent.parent / "output"
    if not output_dir.exists():
        raise FileNotFoundError(f"output/ 디렉토리를 찾을 수 없습니다: {output_dir}")

    matches = sorted(output_dir.glob(f"*_{project}"))
    if not matches:
        matches = sorted(output_dir.glob(f"{project}"))
    if len(matches) == 0:
        raise FileNotFoundError(f"slug '{project}'에 해당하는 프로젝트를 찾을 수 없습니다.")
    if len(matches) > 1:
        raise ValueError(
            f"slug '{project}'에 해당하는 프로젝트가 여러 개입니다:\n"
            + "\n".join(str(m) for m in matches)
        )
    return matches[0]


def run_adapter(
    project_dir: Path,
    style_id: str = "quirky_cartoon",
    theme: str = "dark",
) -> dict[str, Any]:
    """v4 산출물 → v3 Stage 2 입력 변환.

    Args:
        project_dir: v4 프로젝트 루트 (plan.md, final_manuscript.md 포함)
        style_id: 아트스타일 ID
        theme: 테마 ("dark" | "light")

    Returns:
        {"artifacts": [<list of created paths>]}

    Raises:
        FileNotFoundError: plan.md 또는 final_manuscript.md 없을 때
    """
    project_dir = Path(project_dir)

    plan_path = project_dir / "plan.md"
    manuscript_path = project_dir / "final_manuscript.md"

    if not plan_path.exists():
        raise FileNotFoundError(f"plan.md 를 찾을 수 없습니다: {plan_path}")
    if not manuscript_path.exists():
        raise FileNotFoundError(f"final_manuscript.md 를 찾을 수 없습니다: {manuscript_path}")

    plan_md = plan_path.read_text(encoding="utf-8")
    manuscript_md = manuscript_path.read_text(encoding="utf-8")

    # 1. outline.json
    outline = build_outline(plan_md)

    # 2. research_report.json
    reports_dir = project_dir / "research_reports"
    targeted_dir = project_dir / "research_targeted"
    research_report = build_research_report(
        reports_dir=reports_dir,
        targeted_dir=targeted_dir,
        topic=outline.get("title", ""),
    )

    # 3. art_style.json
    art_style = build_art_style(style_id=style_id, theme=theme)

    # 4. chapter markers 삽입 → final_manuscript.md 업데이트 (in-memory)
    marked_manuscript = insert_markers(manuscript_md, outline, project_dir)

    # 5. _bridge/ 에 저장
    bridge_dir = project_dir / "_bridge"
    bridge_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, Any] = {
        "outline.json": outline,
        "research_report.json": research_report,
        "art_style.json": art_style,
        "final_manuscript.md": marked_manuscript,
    }

    artifacts: list[str] = []

    for filename, content in files.items():
        bridge_path = bridge_dir / filename
        root_path = project_dir / filename

        if isinstance(content, str):
            bridge_path.write_text(content, encoding="utf-8")
        else:
            bridge_path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")

        # project root 에도 복사 (심볼릭 링크 아닌 실제 복사)
        shutil.copy2(bridge_path, root_path)

        artifacts.append(str(bridge_path))
        artifacts.append(str(root_path))

    return {"artifacts": artifacts}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="v4 bridge adapter — 4개 산출물 통합 빌드",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="절대경로 또는 slug (output/*_<slug>/ 자동 탐색)",
    )
    parser.add_argument("--style-id", default="quirky_cartoon", help="아트스타일 ID")
    parser.add_argument("--theme", default="dark", choices=["dark", "light"], help="테마")
    args = parser.parse_args(argv)

    project_dir = _resolve_project_dir(args.project)
    result = run_adapter(project_dir, style_id=args.style_id, theme=args.theme)

    print("생성된 산출물:")
    for path in result["artifacts"]:
        print(f"  {path}")


if __name__ == "__main__":
    main()
