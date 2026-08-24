import shutil

from backend import codex_runner
from backend.codex_runner import build_codex_cmd, codex_exe


def test_codex_exe_resolves_full_path(monkeypatch):
    """윈도우의 codex 는 `.CMD` 라 이름만으로는 CreateProcess 가 못 찾는다.

    `PATHEXT` 를 뒤지지 않으므로 `["codex", ...]` 는 [WinError 2] 로 죽는다.
    `claude` 는 `.EXE` 라 되고 codex 만 안 됐다 — 그래서 레이어 분석만 죽었다.
    """
    monkeypatch.setattr(shutil, "which",
                        lambda n: r"C:\npm\codex.CMD" if n == "codex" else None)
    assert codex_exe() == r"C:\npm\codex.CMD"
    assert build_codex_cmd()[0] == r"C:\npm\codex.CMD"


def test_codex_exe_falls_back_to_bare_name(monkeypatch):
    """PATH 에 없으면 이름만 — 못 찾는 것과 없는 것은 다르다."""
    monkeypatch.setattr(shutil, "which", lambda n: None)
    assert codex_exe() == "codex"


def test_build_basic_with_schema_and_output():
    cmd = build_codex_cmd(output_schema="/p/s.json", output_last="/p/out.json")
    assert cmd[0] == codex_runner.codex_exe()
    assert cmd[1] == "exec"
    assert "--skip-git-repo-check" in cmd
    assert "--json" in cmd
    assert cmd[cmd.index("--output-schema") + 1] == "/p/s.json"
    assert cmd[cmd.index("-o") + 1] == "/p/out.json"
    assert cmd[-1] == "-"  # 프롬프트는 stdin


def test_build_resume_session():
    cmd = build_codex_cmd(session_id="abc-123")
    assert cmd[1] == "exec"
    assert "resume" in cmd
    assert "abc-123" in cmd
    assert cmd[-1] == "-"


def test_no_json_when_disabled():
    cmd = build_codex_cmd(json_events=False)
    assert "--json" not in cmd


def test_build_cmd_with_sandbox():
    cmd = build_codex_cmd(sandbox="workspace-write")
    assert "-s" in cmd
    assert cmd[cmd.index("-s") + 1] == "workspace-write"


def test_build_cmd_no_sandbox_by_default():
    cmd = build_codex_cmd()
    assert "-s" not in cmd


def test_build_cmd_with_images():
    cmd = build_codex_cmd(images=["/a/scene.png"])
    assert "-i" in cmd
    assert cmd[cmd.index("-i") + 1] == "/a/scene.png"


def test_build_cmd_multiple_images():
    cmd = build_codex_cmd(images=["/a.png", "/b.png"])
    assert cmd.count("-i") == 2
