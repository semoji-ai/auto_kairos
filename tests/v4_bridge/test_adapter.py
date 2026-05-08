"""tests/v4_bridge/test_adapter.py — adapter.py 통합 테스트.

PD가 직접 작성한 outline.json + final_manuscript_marked.md 를 전제로 한다.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _write_minimal_outline(path: Path) -> None:
    outline = {
        "title": "다이소의 가격 비밀",
        "core_question": "다이소가 1500원으로 어떻게 살아남는가?",
        "target_duration_minutes": 1,
        "chapters": [
            {
                "chapter_number": 1,
                "title": "가격의 비밀",
                "act": 1,
                "purpose": "가격 정책 소개",
                "duration_ratio": 0.5,
                "research_focus": ["price_policy"],
                "key_points": ["4가격 정책"],
            },
            {
                "chapter_number": 2,
                "title": "회전율",
                "act": 3,
                "purpose": "회전율이 마진의 원천임을 보여줌",
                "duration_ratio": 0.5,
                "research_focus": ["turnover"],
                "key_points": ["하루 세 번 진열"],
            },
        ],
    }
    path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_minimal_marked(path: Path, original_text: str) -> None:
    """original_text를 보존하면서 마커만 추가한 marked manuscript."""
    marked = (
        "# Ch 1. 가격의 비밀\n\n"
        + original_text.split("\n\n")[0]
        + "\n\n---\n\n"
        "# Ch 2. 회전율\n\n"
        + "\n\n".join(original_text.split("\n\n")[1:])
    )
    path.write_text(marked, encoding="utf-8")


def _setup_project(tmp_path: Path) -> tuple[Path, str]:
    """fixture 파일을 tmp_path 프로젝트 구조로 복사. (outline + marked manuscript PD 작성 전제)"""
    manuscript_text = (FIXTURES / "final_manuscript.md").read_text(encoding="utf-8")

    # final_manuscript.md (원본)
    (tmp_path / "final_manuscript.md").write_text(manuscript_text, encoding="utf-8")

    # PD 작성 산출물
    _write_minimal_outline(tmp_path / "outline.json")
    _write_minimal_marked(tmp_path / "final_manuscript_marked.md", manuscript_text)

    # 리서치 디렉토리
    reports_dst = tmp_path / "research_reports"
    reports_dst.mkdir()
    for src in (FIXTURES / "research_reports").iterdir():
        shutil.copy(src, reports_dst / src.name)

    targeted_src = FIXTURES / "research_targeted"
    targeted_dst = tmp_path / "research_targeted"
    targeted_dst.mkdir()
    if targeted_src.exists():
        for src in targeted_src.iterdir():
            shutil.copy(src, targeted_dst / src.name)

    return tmp_path, manuscript_text


# ---------------------------------------------------------------------------
# 1. 4개 산출물 생성 + _bridge/ & root 양쪽 존재 확인
# ---------------------------------------------------------------------------

def test_run_adapter_produces_4_artifacts(tmp_path):
    project_dir, _ = _setup_project(tmp_path)

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    result = run_adapter(project_dir)

    assert "artifacts" in result

    expected_files = ["outline.json", "research_report.json", "art_style.json", "final_manuscript.md"]
    for fname in expected_files:
        bridge_path = project_dir / "_bridge" / fname
        root_path = project_dir / fname
        assert bridge_path.exists(), f"_bridge/{fname} 없음"
        assert root_path.exists(), f"루트/{fname} 없음"
        assert not bridge_path.is_symlink(), f"_bridge/{fname} 는 심볼릭 링크여선 안 됨"
        assert not root_path.is_symlink(), f"루트/{fname} 는 심볼릭 링크여선 안 됨"

    # artifacts 목록에 8개 경로 포함 (4파일 × 2위치)
    assert len(result["artifacts"]) == 8


def test_outline_json_preserved(tmp_path):
    """PD가 작성한 outline.json이 그대로 _bridge/에 복사되는지 확인."""
    project_dir, _ = _setup_project(tmp_path)

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    run_adapter(project_dir)

    outline = json.loads((project_dir / "_bridge" / "outline.json").read_text())
    assert "chapters" in outline
    assert len(outline["chapters"]) == 2
    assert outline["title"] == "다이소의 가격 비밀"


def test_art_style_override(tmp_path):
    project_dir, _ = _setup_project(tmp_path)

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    run_adapter(project_dir, style_id="quirky_cartoon", theme="dark")
    art_style = json.loads((project_dir / "_bridge" / "art_style.json").read_text())
    assert art_style.get("id") == "quirky_cartoon"


# ---------------------------------------------------------------------------
# 2. substring 검증 — marked manuscript가 원본을 보존하지 않으면 ValueError
# ---------------------------------------------------------------------------

def test_validates_substring_when_manuscript_changed_raises(tmp_path):
    project_dir, _ = _setup_project(tmp_path)

    # narration을 변경한 malformed marked manuscript 작성
    (project_dir / "final_manuscript_marked.md").write_text(
        "# Ch 1. 가격의 비밀\n\n완전히 다른 내용이 들어갔습니다.\n\n---\n",
        encoding="utf-8",
    )

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(ValueError, match="substring"):
        run_adapter(project_dir)


# ---------------------------------------------------------------------------
# 3. 필수 파일 누락 오류 케이스
# ---------------------------------------------------------------------------

def test_missing_outline_raises(tmp_path):
    project_dir, manuscript_text = _setup_project(tmp_path)
    (project_dir / "outline.json").unlink()

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(FileNotFoundError, match="outline.json"):
        run_adapter(project_dir)


def test_missing_marked_manuscript_raises(tmp_path):
    project_dir, _ = _setup_project(tmp_path)
    (project_dir / "final_manuscript_marked.md").unlink()

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(FileNotFoundError, match="final_manuscript_marked.md"):
        run_adapter(project_dir)


def test_missing_manuscript_raises(tmp_path):
    project_dir, _ = _setup_project(tmp_path)
    (project_dir / "final_manuscript.md").unlink()

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(FileNotFoundError, match="final_manuscript.md"):
        run_adapter(project_dir)


def test_missing_research_reports_raises(tmp_path):
    project_dir, _ = _setup_project(tmp_path)
    shutil.rmtree(project_dir / "research_reports")

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(FileNotFoundError, match="research_reports"):
        run_adapter(project_dir)


# ---------------------------------------------------------------------------
# 4. CLI — 절대경로 해석
# ---------------------------------------------------------------------------

def test_cli_absolute_path(tmp_path):
    project_dir, _ = _setup_project(tmp_path)

    from auto_agent.modules.v4_bridge.adapter import main

    main(["--project", str(project_dir)])

    assert (project_dir / "_bridge" / "outline.json").exists()


def test_cli_missing_project_raises(tmp_path):
    non_existent = tmp_path / "no_such_dir"

    from auto_agent.modules.v4_bridge.adapter import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--project", str(non_existent)])
    assert exc_info.value.code == 1


def test_cli_style_id_flag(tmp_path):
    project_dir, _ = _setup_project(tmp_path)

    from auto_agent.modules.v4_bridge.adapter import main

    main(["--project", str(project_dir), "--style-id", "quirky_cartoon", "--theme", "dark"])

    art_style = json.loads((project_dir / "art_style.json").read_text())
    assert art_style.get("id") == "quirky_cartoon"


# ---------------------------------------------------------------------------
# 5. __init__.py export
# ---------------------------------------------------------------------------

def test_init_exports_run_adapter():
    from auto_agent.modules.v4_bridge import run_adapter  # noqa: F401

    assert callable(run_adapter)
