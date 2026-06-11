import json
import pytest
from pathlib import Path
from PIL import Image
from unittest.mock import MagicMock, patch

from auto_agent.modules.image_batch_module import run_batch, _build_char_result_path


@pytest.fixture
def project_dir(tmp_path):
    """최소 프로젝트 구조 생성."""
    d = tmp_path / "test_project"
    d.mkdir()
    (d / "characters").mkdir()
    (d / "images").mkdir()

    (d / "art_style.json").write_text(json.dumps({
        "id": "quirky_cartoon",
        "name": "Quirky Cartoon",
        "reference_image": "",
        "scene_style_description": "cartoon",
        "technical": {"critical_requirements": []},
    }))

    (d / "character_plan.json").write_text(json.dumps({
        "characters": [
            {
                "id": "char_001",
                "name": "테스트캐릭터",
                "description": "테스트용 캐릭터",
                "tags": ["테스트"],
                "person_photo": None,
            }
        ]
    }))

    (d / "scene_specs.json").write_text(json.dumps({
        "scenes": [
            {
                "sceneNumber": 1,
                "narration": "테스트 씬",
                "imageAsset": {"source": "generate", "prompt": "test scene"},
                "characters": ["char_001"],
            }
        ]
    }))
    return d


def test_character_reused_from_library(project_dir, tmp_path):
    """라이브러리에 캐릭터가 있으면 FAL 제출 없이 재사용한다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(
        library_dir=tmp_path / "chars",
        db_path=tmp_path / "chars.db",
    )
    dummy_png = tmp_path / "dummy.png"
    Image.new("RGB", (1, 1)).save(dummy_png)
    lib.register(dummy_png, {
        "character_name": "테스트캐릭터",
        "art_style": "quirky_cartoon",
        "tags": "테스트",
        "features": "테스트용",
        "source_project": "prev",
    })

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        # scene phase: run_batch(jobs, on_done=...) 가 결과를 콜백으로 전달
        scene_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/s.png", "width": 512, "height": 512}])
        mock_fq.run_batch.side_effect = lambda jobs, on_done=None, **kw: on_done and [on_done(scene_result)]
        mock_save.return_value = project_dir / "images" / "scene_001_gen_01.png"
        result = run_batch(project_dir, library=lib)

    # character was reused, not submitted for generation
    assert result["chars_reused"] == 1
    assert result["chars_generated"] == 0


def test_character_new_generation(project_dir, tmp_path):
    """라이브러리 미스 시 FAL 제출이 호출된다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(library_dir=tmp_path / "c", db_path=tmp_path / "c.db")

    char_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake.com/img.png", "width": 512, "height": 512}])
    scene_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/s.png", "width": 512, "height": 512}])

    batch_call_count = {"n": 0}
    def fake_run_batch(jobs, on_done=None, **kw):
        batch_call_count["n"] += 1
        # 1번째 배치 = 캐릭터, 2번째 = 씬
        on_done(char_result if batch_call_count["n"] == 1 else scene_result)
        return []

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.run_batch.side_effect = fake_run_batch
        mock_save.return_value = project_dir / "characters" / "char_001.png"
        result = run_batch(project_dir, library=lib)

    assert result["chars_generated"] == 1


def test_scene_batch_submitted(project_dir, tmp_path):
    """씬 이미지가 FAL에 일괄 제출된다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(library_dir=tmp_path / "c", db_path=tmp_path / "c.db")

    dummy_png = tmp_path / "dummy.png"
    Image.new("RGB", (1, 1)).save(dummy_png)
    lib.register(dummy_png, {
        "character_name": "테스트캐릭터",
        "art_style": "quirky_cartoon",
        "tags": "테스트",
        "features": "테스트",
        "source_project": "p",
    })

    scene_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/s.png", "width": 512, "height": 512}])

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.run_batch.side_effect = lambda jobs, on_done=None, **kw: on_done and [on_done(scene_result)]
        mock_save.return_value = project_dir / "images" / "scene_001_gen_01.png"
        result = run_batch(project_dir, library=lib)

    # scene 배치 1회만 실행 (캐릭터는 라이브러리 재사용)
    assert mock_fq.run_batch.call_count == 1
    assert "scenes_success" in result


def test_failed_character_scene_generated_without_ref(project_dir, tmp_path):
    """캐릭터 생성 실패 시 씬이 캐릭터 참조 없이 생성된다."""
    from auto_agent.tools.character_library import CharacterLibrary
    lib = CharacterLibrary(library_dir=tmp_path / "c", db_path=tmp_path / "c.db")

    char_fail = MagicMock(success=False, idx=0, error="FAL error", images=[])
    scene_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/s.png", "width": 512, "height": 512}])

    batch_call_count = {"n": 0}
    def fake_run_batch(jobs, on_done=None, **kw):
        batch_call_count["n"] += 1
        on_done(char_fail if batch_call_count["n"] == 1 else scene_result)
        return []

    with patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.run_batch.side_effect = fake_run_batch
        mock_save.return_value = project_dir / "images" / "scene_001_gen_01.png"
        result = run_batch(project_dir, library=lib)

    # 캐릭터 배치 + 씬 배치 = run_batch 2회 (캐릭터 실패해도 씬은 참조 없이 진행)
    assert mock_fq.run_batch.call_count == 2


def test_build_char_result_path(tmp_path):
    """_build_char_result_path returns correct path."""
    project_dir = tmp_path / "proj"
    result = _build_char_result_path(project_dir, "char_001")
    assert result == project_dir / "characters" / "char_001.png"
