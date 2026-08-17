import json
from pathlib import Path
from backend import edits


def test_save_file_creates_backup_and_log(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "final_manuscript.md").write_text("원래 문장이다.", encoding="utf-8")
    res = edits.save_file(d, "final_manuscript.md", "고친 문장이다.")
    assert res["ok"] and res["changed"] == 2                       # -1/+1
    assert (d / "final_manuscript.md").read_text(encoding="utf-8") == "고친 문장이다."
    assert (d / "_versions" / "final_manuscript.md.v1").read_text(encoding="utf-8") == "원래 문장이다."
    log = (d / edits.EDIT_LOG).read_text(encoding="utf-8").strip().splitlines()
    e = json.loads(log[-1])
    assert e["file"] == "final_manuscript.md" and "고친 문장" in e["diff"]


def test_save_file_no_change_no_log(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "plan.md").write_text("같음", encoding="utf-8")
    res = edits.save_file(d, "plan.md", "같음")
    assert res["ok"] and res["changed"] == 0
    assert not (d / edits.EDIT_LOG).exists()


def test_save_file_rejects_traversal_and_ext(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    assert "error" in edits.save_file(d, "../evil.md", "x")
    assert "error" in edits.save_file(d, "scenes.json", "x")       # json 비허용(전용 API 사용)


def test_recent_edits_text_for_prompt(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "plan.md").write_text("a", encoding="utf-8")
    edits.save_file(d, "plan.md", "b")
    txt = edits.recent_edits_text(d)
    assert "최근 사용자 수정 내역" in txt and "plan.md" in txt and "```diff" in txt
    assert edits.recent_edits_text(tmp_path / "none") == ""        # 로그 없으면 빈 문자열


def test_versions_increment(tmp_path):
    d = tmp_path / "p"; d.mkdir()
    (d / "plan.md").write_text("v1", encoding="utf-8")
    edits.save_file(d, "plan.md", "v2")
    edits.save_file(d, "plan.md", "v3")
    assert (d / "_versions" / "plan.md.v1").read_text(encoding="utf-8") == "v1"
    assert (d / "_versions" / "plan.md.v2").read_text(encoding="utf-8") == "v2"
