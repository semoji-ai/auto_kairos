from backend import projects


def _make_project(root, pid, *, plan=True, manuscript=True, scenes=False):
    d = root / pid
    d.mkdir(parents=True)
    if plan:
        (d / "plan.md").write_text("# 테스트 제목\n\n톤: 다큐", encoding="utf-8")
    if manuscript:
        (d / "final_manuscript.md").write_text("원고 본문.", encoding="utf-8")
    if scenes:
        (d / "scenes.json").write_text("{}", encoding="utf-8")
    return d


def test_scan_finds_project(tmp_path):
    _make_project(tmp_path, "p1")
    rows = projects.scan_projects(tmp_path)
    assert any(r["project_id"] == "p1" for r in rows)


def test_scan_row_shape(tmp_path):
    _make_project(tmp_path, "p1")
    row = next(r for r in projects.scan_projects(tmp_path) if r["project_id"] == "p1")
    assert row["title"] == "테스트 제목"
    assert row["status"] == "manuscript"
    assert set(["project_id", "title", "status", "updated_at", "artifacts"]) <= set(row)
    assert row["artifacts"]["final_manuscript.md"] is True
    assert row["artifacts"]["scenes.json"] is False


def test_status_decomposed_when_scenes(tmp_path):
    _make_project(tmp_path, "p2", scenes=True)
    row = next(r for r in projects.scan_projects(tmp_path) if r["project_id"] == "p2")
    assert row["status"] == "decomposed"


def test_load_project_next_actions(tmp_path):
    _make_project(tmp_path, "p1")
    info = projects.load_project(tmp_path, "p1")
    assert info["project_id"] == "p1"
    assert "scene-decompose" in info["next_actions"]


def test_create_project(tmp_path):
    info = projects.create_project(tmp_path, "테슬라 역사", channel="semoji", duration="1분")
    pid = info["project_id"]
    assert (tmp_path / pid / "plan.md").exists()
    plan = (tmp_path / pid / "plan.md").read_text(encoding="utf-8")
    assert "테슬라 역사" in plan and "semoji" in plan and "1분" in plan
    row = next(r for r in projects.scan_projects(tmp_path) if r["project_id"] == pid)
    assert row["status"] == "planned"


def test_status_planned_when_plan_only(tmp_path):
    d = tmp_path / "x"; d.mkdir()
    (d / "plan.md").write_text("# T", encoding="utf-8")
    row = next(r for r in projects.scan_projects(tmp_path) if r["project_id"] == "x")
    assert row["status"] == "planned"


def test_list_files_groups(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "plan.md").write_text("기획", encoding="utf-8")
    (d / "research_report.json").write_text("{}", encoding="utf-8")
    (d / "draft.md").write_text("초고", encoding="utf-8")
    (d / "final_manuscript.md").write_text("원고", encoding="utf-8")
    (d / "scenes.json").write_text("{}", encoding="utf-8")          # 제외(스토리보드)
    (d / "notes.txt").write_text("메모", encoding="utf-8")           # 기타
    groups = projects.list_files(d)
    by = {g["label"]: g["files"] for g in groups}
    assert by["기획"] == ["plan.md"]
    assert by["리서치"] == ["research_report.json"]
    assert sorted(by["원고"]) == ["draft.md", "final_manuscript.md"]
    assert "scenes.json" not in by.get("기타", [])
    assert by["기타"] == ["notes.txt"]
    # 빈 그룹은 결과에 없음
    assert all(g["files"] for g in groups)


def test_list_files_missing_dir(tmp_path):
    assert projects.list_files(tmp_path / "nope") == []
