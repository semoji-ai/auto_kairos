"""upscale.py 단위 테스트 — 실제 upscayl-bin 실행 없음(전부 mock)."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from auto_agent.tools import upscale


# ---------------------------------------------------------------------------
# upscayl_available
# ---------------------------------------------------------------------------

def test_upscayl_available_true_when_env_bin_executable(tmp_path, monkeypatch):
    bin_path = tmp_path / "upscayl-bin"
    bin_path.write_text("#!/bin/sh\n")
    bin_path.chmod(0o755)
    monkeypatch.setenv("UPSCAYL_BIN", str(bin_path))
    assert upscale.upscayl_available() is True


def test_upscayl_available_false_when_env_bin_not_executable(tmp_path, monkeypatch):
    bin_path = tmp_path / "upscayl-bin"
    bin_path.write_text("not executable")
    monkeypatch.setenv("UPSCAYL_BIN", str(bin_path))
    monkeypatch.setattr(upscale.shutil, "which", lambda name: None)
    assert upscale.upscayl_available() is False


def test_upscayl_available_falls_back_to_which(tmp_path, monkeypatch):
    monkeypatch.delenv("UPSCAYL_BIN", raising=False)
    monkeypatch.setattr(upscale.shutil, "which", lambda name: "/usr/local/bin/upscayl-bin")
    assert upscale.upscayl_available() is True


def test_upscayl_available_false_when_nothing_found(tmp_path, monkeypatch):
    monkeypatch.delenv("UPSCAYL_BIN", raising=False)
    monkeypatch.setattr(upscale, "_HOME_SHARE", tmp_path / "no-such-upscayl")
    monkeypatch.setattr(upscale.shutil, "which", lambda name: None)
    assert upscale.upscayl_available() is False


# ---------------------------------------------------------------------------
# 모델 선택 (_pick_model)
# ---------------------------------------------------------------------------

def _make_models(tmp_path, names):
    for n in names:
        (tmp_path / f"{n}.param").write_text("")


def test_pick_model_illustration_content(tmp_path, monkeypatch):
    _make_models(tmp_path, ["digital-art-4x", "upscayl-standard-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(tmp_path))
    assert upscale._pick_model("illustration", None) == "digital-art-4x"


def test_pick_model_photo_content(tmp_path, monkeypatch):
    _make_models(tmp_path, ["digital-art-4x", "upscayl-standard-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(tmp_path))
    assert upscale._pick_model("photo", None) == "upscayl-standard-4x"


def test_pick_model_explicit_model_wins(tmp_path, monkeypatch):
    _make_models(tmp_path, ["digital-art-4x", "upscayl-standard-4x", "remacri-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(tmp_path))
    assert upscale._pick_model("illustration", "remacri-4x") == "remacri-4x"


def test_pick_model_falls_back_when_wanted_not_installed(tmp_path, monkeypatch):
    _make_models(tmp_path, ["upscayl-standard-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(tmp_path))
    # illustration 원하지만 art류 없음 -> 설치된 것 중 폴백 (standard)
    assert upscale._pick_model("illustration", None) == "upscayl-standard-4x"


def test_pick_model_none_when_nothing_installed(tmp_path, monkeypatch):
    monkeypatch.setenv("UPSCAYL_MODELS", str(tmp_path))
    assert upscale._pick_model("illustration", None) is None


def test_available_models_lists_param_stems(tmp_path, monkeypatch):
    _make_models(tmp_path, ["digital-art-4x", "remacri-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(tmp_path))
    assert upscale.available_models() == ["digital-art-4x", "remacri-4x"]


# ---------------------------------------------------------------------------
# upscale_image 실패 경로
# ---------------------------------------------------------------------------

def test_upscale_image_fails_when_binary_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("UPSCAYL_BIN", raising=False)
    monkeypatch.setattr(upscale.shutil, "which", lambda name: None)
    src = tmp_path / "scene.png"
    src.write_bytes(b"fake")
    result = upscale.upscale_image(str(src))
    assert result["status"] == "failed"
    assert "error" in result


def test_upscale_image_fails_when_input_missing(tmp_path, monkeypatch):
    bin_path = tmp_path / "upscayl-bin"
    bin_path.write_text("#!/bin/sh\n")
    bin_path.chmod(0o755)
    monkeypatch.setenv("UPSCAYL_BIN", str(bin_path))
    result = upscale.upscale_image(str(tmp_path / "missing.png"))
    assert result["status"] == "failed"
    assert "error" in result


def test_upscale_image_fails_when_no_model_installed(tmp_path, monkeypatch):
    bin_path = tmp_path / "upscayl-bin"
    bin_path.write_text("#!/bin/sh\n")
    bin_path.chmod(0o755)
    monkeypatch.setenv("UPSCAYL_BIN", str(bin_path))
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setenv("UPSCAYL_MODELS", str(models_dir))
    src = tmp_path / "scene.png"
    src.write_bytes(b"fake")
    result = upscale.upscale_image(str(src))
    assert result["status"] == "failed"
    assert "error" in result


# ---------------------------------------------------------------------------
# upscale_image 성공 경로
# ---------------------------------------------------------------------------

def test_upscale_image_success(tmp_path, monkeypatch):
    bin_path = tmp_path / "upscayl-bin"
    bin_path.write_text("#!/bin/sh\n")
    bin_path.chmod(0o755)
    monkeypatch.setenv("UPSCAYL_BIN", str(bin_path))

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    _make_models(models_dir, ["digital-art-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(models_dir))

    src = tmp_path / "scene.png"
    src.write_bytes(b"fake-png-bytes")

    captured_cmd = {}

    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        captured_cmd["cmd"] = cmd
        captured_cmd["timeout"] = timeout
        # 실제 바이너리가 out 파일을 만드는 것처럼 흉내
        out_path = Path(cmd[cmd.index("-o") + 1])
        out_path.write_bytes(b"upscaled")
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(upscale.subprocess, "run", fake_run)

    result = upscale.upscale_image(str(src), content="illustration", scale=2)

    assert result["status"] == "completed"
    assert result["model"] == "digital-art-4x"
    assert result["scale"] == 2
    assert Path(result["path"]).is_file()

    cmd = captured_cmd["cmd"]
    assert "-s" in cmd and cmd[cmd.index("-s") + 1] == "2"
    assert "-f" in cmd and cmd[cmd.index("-f") + 1] == "png"
    assert captured_cmd["timeout"] == 600


def test_upscale_image_failure_when_subprocess_returns_nonzero(tmp_path, monkeypatch):
    bin_path = tmp_path / "upscayl-bin"
    bin_path.write_text("#!/bin/sh\n")
    bin_path.chmod(0o755)
    monkeypatch.setenv("UPSCAYL_BIN", str(bin_path))

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    _make_models(models_dir, ["digital-art-4x"])
    monkeypatch.setenv("UPSCAYL_MODELS", str(models_dir))

    src = tmp_path / "scene.png"
    src.write_bytes(b"fake")

    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="oops", stderr="boom")

    monkeypatch.setattr(upscale.subprocess, "run", fake_run)

    result = upscale.upscale_image(str(src))
    assert result["status"] == "failed"
    assert "log_tail" in result
