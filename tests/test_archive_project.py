"""완성한 편을 NAS 보관 워크스페이스로 옮긴다.

## 설계가 사고 하나를 피해 간다

`docs/v5-plan.md:76` 에 이렇게 적혀 있다.

> 오늘 DB의 `output_dir`이 NAS 경로로 박혀 대시보드가 죽는 일이 있었다

그래서 **DB 의 `output_dir` 은 NAS 를 가리키지 않는다.** 원래 자리에 작은 표석
(`ARCHIVED.json`)만 남기고 실물만 NAS 로 보낸다. 대시보드는 늘 있는 로컬 경로를
보고, NAS 가 안 붙어 있어도 죽지 않는다.

NAS 는 느리다(실측 쓰기 11MB/s, 작은 파일 4.3개/초). 7GB 짜리 한 편이 10분을
넘게 걸리므로 **중간에 끊겨도 원본이 남아 있어야 한다** — 복사 후 검증, 검증
통과 뒤에야 삭제한다.
"""
from __future__ import annotations

import json

import pytest

from auto_agent.scripts.archive_project import (
    ArchiveError,
    archive_project,
    is_archived,
    read_stub,
)


def _make_project(root, name="0000abcd_테스트편"):
    p = root / "output" / name
    (p / "images").mkdir(parents=True)
    (p / "audio").mkdir()
    (p / "plan.md").write_text("# 테스트편", encoding="utf-8")
    (p / "images" / "a.png").write_bytes(b"\x89PNG" + b"a" * 5000)
    (p / "audio" / "b.mp3").write_bytes(b"ID3" + b"b" * 3000)
    return p


class TestArchive:
    def test_moves_files_and_leaves_a_stub(self, tmp_path):
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"
        dest.mkdir()

        info = archive_project(proj, dest)

        moved = dest / proj.name
        assert (moved / "images" / "a.png").read_bytes().startswith(b"\x89PNG")
        assert (moved / "plan.md").exists()

        # 원래 자리에는 표석만 남는다 — 대시보드가 보는 경로는 계속 존재한다
        assert proj.is_dir()
        assert not (proj / "images").exists()
        stub = read_stub(proj)
        assert stub["archived_to"] == str(moved)
        assert stub["files"] == 3
        assert info["files"] == 3

    def test_is_archived_detects_the_stub(self, tmp_path):
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()
        assert is_archived(proj) is False
        archive_project(proj, dest)
        assert is_archived(proj) is True

    def test_original_survives_when_verification_fails(self, tmp_path, monkeypatch):
        """NAS 가 느려 중간에 끊기거나 내용이 어긋나면 **원본을 지우지 않는다.**"""
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()

        import auto_agent.scripts.archive_project as m
        monkeypatch.setattr(m, "_verify", lambda a, b: False)

        with pytest.raises(ArchiveError):
            archive_project(proj, dest)

        assert (proj / "images" / "a.png").exists(), "검증 실패인데 원본이 사라졌다"
        assert not is_archived(proj)

    def test_refuses_to_archive_twice(self, tmp_path):
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()
        archive_project(proj, dest)
        with pytest.raises(ArchiveError, match="이미 보관"):
            archive_project(proj, dest)

    def test_refuses_when_destination_already_taken(self, tmp_path):
        """같은 이름이 이미 NAS 에 있으면 덮지 않는다 — 덮으면 되돌릴 수 없다."""
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()
        (dest / proj.name).mkdir()
        with pytest.raises(ArchiveError, match="이미 있습니다"):
            archive_project(proj, dest)

    def test_dry_run_changes_nothing(self, tmp_path):
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()
        info = archive_project(proj, dest, dry_run=True)
        assert info["files"] == 3
        assert (proj / "images" / "a.png").exists()
        assert not (dest / proj.name).exists()
        assert not is_archived(proj)


class TestStubKeepsDashboardAlive:
    """표석의 존재 이유 — DB 가 가리키는 경로가 사라지면 안 된다."""

    def test_stub_dir_exists_and_is_readable(self, tmp_path):
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()
        archive_project(proj, dest)
        # 대시보드가 하는 일: Path(project["output_dir"]) 로 만들고 존재를 본다
        assert proj.exists() and proj.is_dir()
        assert json.loads((proj / "ARCHIVED.json").read_text(encoding="utf-8"))

    def test_stub_records_where_it_went(self, tmp_path):
        proj = _make_project(tmp_path)
        dest = tmp_path / "nas"; dest.mkdir()
        archive_project(proj, dest)
        s = read_stub(proj)
        assert set(s) >= {"archived_to", "archived_at", "files", "bytes"}
        assert s["bytes"] > 0
