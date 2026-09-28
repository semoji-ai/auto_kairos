from auto_agent.scripts.preflight_check import _fill_missing_from_template


def test_fill_missing_never_deletes_or_overwrites(tmp_path):
    template = tmp_path / "template"
    (template / "src").mkdir(parents=True)
    (template / "package.json").write_text("{}")
    (template / "src" / "index.ts").write_text("new")
    remotion = tmp_path / "remotion"
    (remotion / "public" / "background").mkdir(parents=True)
    (remotion / "public" / "background" / "bg.jpg").write_bytes(b"keep")
    (remotion / "src").mkdir()
    (remotion / "src" / "index.ts").write_text("existing")

    added = _fill_missing_from_template(template, remotion)

    assert added == 1
    assert (remotion / "package.json").exists()
    assert (remotion / "public" / "background" / "bg.jpg").read_bytes() == b"keep"
    assert (remotion / "src" / "index.ts").read_text() == "existing"
