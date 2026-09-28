import json

from auto_agent.orchestrator.execution import agent_hook_settings
from auto_agent.scripts.hooks.guard_agent_tools import check


def _bash(cmd, cwd=""):
    return check("Bash", {"command": cmd}, cwd)


def test_blocks_image_delete():
    assert _bash("rm images/scene_03_gen_01.png")
    assert _bash("cd images && rm -f *.png")
    assert _bash('find images -name "*.png" -delete')


def test_allows_non_image_delete_and_reads():
    assert _bash("rm -rf .execution/tmp.json") is None
    assert _bash("ls images/*.png") is None
    assert check("Write", {"file_path": "images/scene_01_gen_01.png"}) is None


def test_overwrite_blocked_only_when_destination_exists(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "scene_03_gen_01.png").write_bytes(b"x")
    assert _bash("cp new.png images/scene_03_gen_01.png", str(tmp_path))
    assert _bash("mv new.png images/scene_03_gen_02.png", str(tmp_path)) is None


def test_hook_settings_point_at_guard():
    settings = json.loads(agent_hook_settings())
    entry = settings["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == "Bash"
    assert "guard_agent_tools.py" in entry["hooks"][0]["command"]
