import json
from pathlib import Path

from auto_agent import cli
from auto_agent.ui import prompts


def test_scan_art_styles_reads_only_canonical_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    ws_dir = tmp_path / "workspace"
    canonical_dir = data_dir / "artstyle" / "styles"
    workspace_dir = ws_dir / "artstyle" / "styles"
    canonical_dir.mkdir(parents=True)
    workspace_dir.mkdir(parents=True)

    (canonical_dir / "semoji.json").write_text(
        json.dumps({"name": "세모지", "description": "canonical"}, ensure_ascii=False),
        encoding="utf-8",
    )
    (workspace_dir / "workspace_only.json").write_text(
        json.dumps({"name": "워크스페이스 스타일", "description": "should be ignored"}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr("auto_agent.paths.get_data_dir", lambda: data_dir)
    monkeypatch.setattr("auto_agent.paths.get_workspace_dir", lambda: ws_dir)

    styles = prompts._scan_art_styles()

    assert [style["filename"] for style in styles] == ["semoji.json"]
    assert styles[0]["name"] == "세모지"


def test_cmd_style_add_writes_to_canonical_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    canonical_dir = data_dir / "artstyle" / "styles"
    canonical_dir.mkdir(parents=True)

    monkeypatch.setattr("auto_agent.cli.get_data_dir", lambda: data_dir)

    cli.cmd_style([
        "add",
        "--name", "Safe Scope",
        "--description", "test style",
        "--style-desc", "flat style",
    ])

    created = canonical_dir / "safe_scope.json"
    assert created.exists()
    payload = json.loads(created.read_text(encoding="utf-8"))
    assert payload["name"] == "Safe Scope"
    assert payload["scene_style_description"] == "flat style"
