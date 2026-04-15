# tests/test_image_assets_qa.py
import json
import tempfile
from pathlib import Path
import pytest
from auto_agent.tools import image_assets


@pytest.fixture
def images_dir(tmp_path):
    """임시 images 디렉토리 (image_assets.json 없음)."""
    return tmp_path / "images"


def _init_scene(images_dir: Path, scene_num: int):
    """테스트용 씬 등록."""
    images_dir.mkdir(exist_ok=True)
    image_assets.add_version(images_dir, scene_num, f"generated/scene_{scene_num:03d}_gen_01.png", "generate")


class TestSetQaResult:
    def test_passed_true(self, images_dir):
        _init_scene(images_dir, 1)
        image_assets.set_qa_result(images_dir, 1, passed=True)
        qa = image_assets.get_qa_result(images_dir, 1)
        assert qa is not None
        assert qa["passed"] is True
        assert qa.get("issues") == []
        assert "checked_at" in qa

    def test_passed_false_with_issues(self, images_dir):
        _init_scene(images_dir, 2)
        issues = ["캐릭터 의상 불일치", "프롬프트 미매칭"]
        image_assets.set_qa_result(images_dir, 2, passed=False, issues=issues)
        qa = image_assets.get_qa_result(images_dir, 2)
        assert qa["passed"] is False
        assert qa["issues"] == issues

    def test_overwrite_existing(self, images_dir):
        _init_scene(images_dir, 3)
        image_assets.set_qa_result(images_dir, 3, passed=False, issues=["issue1"])
        image_assets.set_qa_result(images_dir, 3, passed=True)
        qa = image_assets.get_qa_result(images_dir, 3)
        assert qa["passed"] is True

    def test_thread_safe(self, images_dir):
        import threading
        _init_scene(images_dir, 4)
        errors = []

        def write():
            try:
                image_assets.set_qa_result(images_dir, 4, passed=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


class TestGetQaResult:
    def test_returns_none_when_no_qa(self, images_dir):
        _init_scene(images_dir, 5)
        assert image_assets.get_qa_result(images_dir, 5) is None

    def test_returns_none_for_unknown_scene(self, images_dir):
        images_dir.mkdir(exist_ok=True)
        assert image_assets.get_qa_result(images_dir, 999) is None
