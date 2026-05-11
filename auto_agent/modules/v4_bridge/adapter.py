"""v4 research/script artifacts → v3 Stage 2 input adapter (top-level pipeline).

PD가 직접 작성하는 산출물:
  - final_manuscript_marked.md (마커 삽입된 원고)
  - outline.json (챕터 메타데이터)

어댑터가 빌드하는 산출물:
  - research_report.json (v4 research_reports/ + research_targeted/ 에서 조합)
  - art_style.json (스타일 디폴트 또는 PD 결정값)
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from auto_agent.paths import get_workspace_dir

from .build_research_report import build_research_report
from .build_art_style import build_art_style


def _strip_frontmatter(text: str) -> str:
    """YAML frontmatter (--- ... ---) 블록을 제거하고 본문만 반환."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        try:
            end = next(i for i, l in enumerate(lines[1:], 1) if l.strip() == "---")
            return "\n".join(lines[end + 1:])
        except StopIteration:
            pass
    return text


def _validate_substring(original: str, marked: str) -> None:
    """마커/주석/공백을 제거한 후 원본 narration이 그대로 들어 있는지 확인.

    실패 시 ValueError (PD가 narration을 변경했음).
    """
    def _strip_markers(text: str) -> str:
        """마커(# 헤더, --- 구분자, <!-- 주석), frontmatter 제거 후 순수 narration만 반환."""
        text = _strip_frontmatter(text)
        lines = [
            line for line in text.splitlines()
            if not line.startswith("#")
            and line.strip() != "---"
            and not (line.strip().startswith("<!--") and line.strip().endswith("-->"))
        ]
        return "\n".join(lines)

    original_narration = _strip_markers(original)
    marked_narration = _strip_markers(marked)

    norm = lambda s: " ".join(s.split())
    if norm(original_narration) not in norm(marked_narration):
        raise ValueError(
            "final_manuscript_marked.md의 본문이 final_manuscript.md의 substring이 아닙니다.\n"
            "마커/주석/공백 외에 narration 본문이 변경된 것으로 보입니다.\n"
            f"원본(norm) 앞 100자: {norm(original_narration)[:100]}\n"
            f"결과(norm) 앞 200자: {norm(marked_narration)[:200]}"
        )


def _resolve_project_dir(project: str) -> Path:
    """slug 또는 절대경로 → 유일한 프로젝트 디렉토리 Path 반환."""
    p = Path(project)
    if p.is_absolute():
        if not p.exists():
            raise FileNotFoundError(f"프로젝트 경로가 존재하지 않습니다: {p}")
        return p

    # slug 검색: output/*_<slug>/
    output_dir = get_workspace_dir() / "output"
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
    """v4 산출물(PD 작성 outline + marked manuscript 포함) → v3 Stage 2 입력.

    Args:
        project_dir: v4 프로젝트 루트.
            PD가 이미 작성했어야 하는 파일:
              - final_manuscript_marked.md
              - outline.json
              - final_manuscript.md (원본, substring 검증에 사용)
            연구 디렉토리:
              - research_reports/
              - research_targeted/
        style_id: 아트스타일 ID
        theme: 테마 ("dark" | "light")

    Returns:
        {"artifacts": [<list of created paths>]}

    Raises:
        FileNotFoundError: 필수 파일/디렉토리 없을 때
        ValueError: marked manuscript가 원본의 substring이 아닐 때
    """
    project_dir = Path(project_dir)

    # ── 1. 필수 입력 존재 확인 ──
    marked_path = project_dir / "final_manuscript_marked.md"
    outline_path = project_dir / "outline.json"
    manuscript_path = project_dir / "final_manuscript.md"
    reports_dir = project_dir / "research_reports"
    targeted_dir = project_dir / "research_targeted"

    if not marked_path.exists():
        raise FileNotFoundError(
            f"final_manuscript_marked.md 를 찾을 수 없습니다: {marked_path}\n"
            "finalize-for-bridge 스킬을 따라 PD가 직접 작성해야 합니다."
        )
    if not outline_path.exists():
        raise FileNotFoundError(
            f"outline.json 을 찾을 수 없습니다: {outline_path}\n"
            "finalize-for-bridge 스킬을 따라 PD가 직접 작성해야 합니다."
        )
    if not manuscript_path.exists():
        raise FileNotFoundError(
            f"final_manuscript.md 를 찾을 수 없습니다: {manuscript_path}"
        )
    if not reports_dir.exists():
        raise FileNotFoundError(
            f"research_reports/ 디렉토리를 찾을 수 없습니다: {reports_dir}"
        )
    if not targeted_dir.exists():
        raise FileNotFoundError(
            f"research_targeted/ 디렉토리를 찾을 수 없습니다: {targeted_dir}"
        )

    # ── 2. substring 검증 ──
    original_manuscript = manuscript_path.read_text(encoding="utf-8")
    marked_manuscript = marked_path.read_text(encoding="utf-8")
    _validate_substring(original_manuscript, marked_manuscript)

    # ── 3. outline.json 로드 (PD가 작성한 것) ──
    outline = json.loads(outline_path.read_text(encoding="utf-8"))

    # ── 4. research_report.json 빌드 ──
    research_report = build_research_report(
        reports_dir=reports_dir,
        targeted_dir=targeted_dir,
        topic=outline.get("title", ""),
    )

    # ── 5. art_style.json 빌드 ──
    art_style = build_art_style(style_id=style_id, theme=theme)

    # ── 6. _bridge/ 에 저장 + project root 복사 ──
    bridge_dir = project_dir / "_bridge"
    bridge_dir.mkdir(parents=True, exist_ok=True)

    files: dict[str, Any] = {
        "outline.json": outline,
        "research_report.json": research_report,
        "art_style.json": art_style,
        "final_manuscript.md": marked_manuscript,  # marked version → v3가 읽는 위치로
    }

    artifacts: list[str] = []

    for filename, content in files.items():
        bridge_path = bridge_dir / filename
        root_path = project_dir / filename

        if isinstance(content, str):
            bridge_path.write_text(content, encoding="utf-8")
        else:
            bridge_path.write_text(
                json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        # project root 에도 복사 (심볼릭 링크 아닌 실제 복사)
        shutil.copy2(bridge_path, root_path)

        artifacts.append(str(bridge_path))
        artifacts.append(str(root_path))

    return {"artifacts": artifacts}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "v4 bridge adapter — research_report + art_style 빌드 + "
            "PD 작성 outline/marked-manuscript 검증 후 v3 Stage 2 입력 통합"
        ),
    )
    parser.add_argument(
        "--project",
        required=True,
        help="절대경로 또는 slug (output/*_<slug>/ 자동 탐색)",
    )
    parser.add_argument("--style-id", default="quirky_cartoon", help="아트스타일 ID")
    parser.add_argument("--theme", default="dark", choices=["dark", "light"], help="테마")
    args = parser.parse_args(argv)

    try:
        project_dir = _resolve_project_dir(args.project)
    except (FileNotFoundError, ValueError) as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)

    result = run_adapter(project_dir, style_id=args.style_id, theme=args.theme)

    print("생성된 산출물:")
    for path in result["artifacts"]:
        print(f"  {path}")


if __name__ == "__main__":
    main()
