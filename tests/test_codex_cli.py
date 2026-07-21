from pathlib import Path
from unittest.mock import patch
import pytest

from auto_agent.utils.codex_cli import (
    build_codex_exec_cmd, codex_available, find_codex_cli, read_output_last_message,
)


@patch("auto_agent.utils.codex_cli.shutil.which", return_value="/usr/local/bin/codex")
def test_build_cmd_basic(mock_which):
    cmd = build_codex_exec_cmd(workdir=Path("/tmp/w"), output_last_message="/tmp/last.txt")
    assert cmd[0] == "/usr/local/bin/codex"
    assert cmd[1] == "exec"
    assert ["-C", "/tmp/w"] == cmd[2:4]
    assert "--ephemeral" in cmd and "--skip-git-repo-check" in cmd
    assert ["--sandbox", "workspace-write"] == [cmd[i] for i in (cmd.index("--sandbox"), cmd.index("--sandbox") + 1)]
    assert "--search" not in cmd
    assert "-m" not in cmd  # model 미지정 시 CLI 기본


@patch("auto_agent.utils.codex_cli.shutil.which", return_value="/usr/local/bin/codex")
def test_build_cmd_search_and_model(mock_which):
    cmd = build_codex_exec_cmd(
        workdir=Path("/tmp/w"), output_last_message="/tmp/last.txt",
        model="o4-mini", search=True,
    )
    assert "--search" in cmd
    assert cmd[cmd.index("-m") + 1] == "o4-mini"
    # search는 최상위 플래그 (exec 앞에 위치)
    assert cmd.index("--search") < cmd.index("exec")


@patch("auto_agent.utils.codex_cli.shutil.which", return_value=None)
def test_find_codex_cli_missing(mock_which):
    assert codex_available() is False
    with pytest.raises(FileNotFoundError):
        find_codex_cli()


def test_read_output_last_message(tmp_path):
    p = tmp_path / "last.txt"
    p.write_text("  결과  ", encoding="utf-8")
    assert read_output_last_message(str(p), fallback="fb") == "결과"
    assert read_output_last_message(str(tmp_path / "none.txt"), fallback="fb") == "fb"
    assert read_output_last_message(None, fallback="fb") == "fb"
