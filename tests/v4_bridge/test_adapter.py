"""tests/v4_bridge/test_adapter.py — adapter.py 통합 테스트."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_project(tmp_path: Path) -> Path:
    """fixture 파일을 tmp_path 프로젝트 구조로 복사."""
    shutil.copy(FIXTURES / "plan.md", tmp_path / "plan.md")
    shutil.copy(FIXTURES / "final_manuscript.md", tmp_path / "final_manuscript.md")

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

    return tmp_path


# ---------------------------------------------------------------------------
# 1. 4개 산출물 생성 + _bridge/ & root 양쪽 존재 확인
# ---------------------------------------------------------------------------

def test_run_adapter_produces_4_artifacts(tmp_path, monkeypatch):
    project_dir = _setup_project(tmp_path)

    # chapter_marker LLM 호출 우회
    def fake_insert_markers(manuscript: str, outline: dict, project_dir: Path) -> str:
        return manuscript  # 그대로 반환

    monkeypatch.setattr(
        "auto_agent.modules.v4_bridge.adapter.insert_markers",
        fake_insert_markers,
    )

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    result = run_adapter(project_dir)

    assert "artifacts" in result

    expected_files = ["outline.json", "research_report.json", "art_style.json", "final_manuscript.md"]
    for fname in expected_files:
        bridge_path = project_dir / "_bridge" / fname
        root_path = project_dir / fname
        assert bridge_path.exists(), f"_bridge/{fname} 없음"
        assert root_path.exists(), f"루트/{fname} 없음"
        # 심볼릭 링크가 아닌 실제 파일인지 확인
        assert not bridge_path.is_symlink(), f"_bridge/{fname} 는 심볼릭 링크여선 안 됨"
        assert not root_path.is_symlink(), f"루트/{fname} 는 심볼릭 링크여선 안 됨"

    # artifacts 목록에 8개 경로 포함 (4파일 × 2위치)
    assert len(result["artifacts"]) == 8


def test_outline_json_has_chapters(tmp_path, monkeypatch):
    project_dir = _setup_project(tmp_path)

    monkeypatch.setattr(
        "auto_agent.modules.v4_bridge.adapter.insert_markers",
        lambda m, o, p: m,
    )

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    run_adapter(project_dir)

    outline = json.loads((project_dir / "_bridge" / "outline.json").read_text())
    assert "chapters" in outline
    assert len(outline["chapters"]) > 0
    assert "title" in outline
    assert outline["title"]  # 비어있지 않음


def test_art_style_override(tmp_path, monkeypatch):
    project_dir = _setup_project(tmp_path)

    monkeypatch.setattr(
        "auto_agent.modules.v4_bridge.adapter.insert_markers",
        lambda m, o, p: m,
    )

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    run_adapter(project_dir, style_id="quirky_cartoon", theme="dark")
    art_style = json.loads((project_dir / "_bridge" / "art_style.json").read_text())
    # build_art_style 은 "id" 키로 반환
    assert art_style.get("id") == "quirky_cartoon"


# ---------------------------------------------------------------------------
# 2. 오류 케이스
# ---------------------------------------------------------------------------

def test_missing_plan_md_raises(tmp_path):
    # final_manuscript.md 만 복사
    shutil.copy(FIXTURES / "final_manuscript.md", tmp_path / "final_manuscript.md")

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(FileNotFoundError, match="plan.md"):
        run_adapter(tmp_path)


def test_missing_manuscript_raises(tmp_path):
    shutil.copy(FIXTURES / "plan.md", tmp_path / "plan.md")

    from auto_agent.modules.v4_bridge.adapter import run_adapter

    with pytest.raises(FileNotFoundError, match="final_manuscript.md"):
        run_adapter(tmp_path)


# ---------------------------------------------------------------------------
# 3. CLI — 절대경로 해석
# ---------------------------------------------------------------------------

def test_cli_absolute_path(tmp_path, monkeypatch):
    project_dir = _setup_project(tmp_path)

    monkeypatch.setattr(
        "auto_agent.modules.v4_bridge.adapter.insert_markers",
        lambda m, o, p: m,
    )

    from auto_agent.modules.v4_bridge.adapter import main

    main(["--project", str(project_dir)])

    assert (project_dir / "_bridge" / "outline.json").exists()


def test_cli_missing_project_raises(tmp_path):
    non_existent = tmp_path / "no_such_dir"

    from auto_agent.modules.v4_bridge.adapter import main

    with pytest.raises(FileNotFoundError):
        main(["--project", str(non_existent)])


def test_cli_style_id_flag(tmp_path, monkeypatch):
    project_dir = _setup_project(tmp_path)

    monkeypatch.setattr(
        "auto_agent.modules.v4_bridge.adapter.insert_markers",
        lambda m, o, p: m,
    )

    from auto_agent.modules.v4_bridge.adapter import main

    main(["--project", str(project_dir), "--style-id", "quirky_cartoon", "--theme", "dark"])

    art_style = json.loads((project_dir / "art_style.json").read_text())
    assert art_style.get("id") == "quirky_cartoon"


# ---------------------------------------------------------------------------
# 4. __init__.py export
# ---------------------------------------------------------------------------

def test_init_exports_run_adapter():
    from auto_agent.modules.v4_bridge import run_adapter  # noqa: F401 — import 성공 여부만 검사

    assert callable(run_adapter)
