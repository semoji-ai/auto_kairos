import json
from unittest.mock import MagicMock, patch

import pytest

from auto_agent.modules.image_batch_module import _resolve_image_backend, run_batch


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_default_codex(mock_av, monkeypatch):
    monkeypatch.delenv("IMAGE_BACKEND", raising=False)
    assert _resolve_image_backend() == "codex"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_env_fal(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "fal")
    assert _resolve_image_backend() == "fal"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=False)
def test_degrade_to_fal_when_codex_missing(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "codex")
    assert _resolve_image_backend() == "fal"


@patch("auto_agent.modules.image_batch_module.codex_available", return_value=True)
def test_invalid_value_default_codex(mock_av, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "midjourney")
    assert _resolve_image_backend() == "codex"


# ── codex 경로 run_batch 통합 테스트 ──

@pytest.fixture
def codex_project_dir(tmp_path):
    """씬 2개(성공/실패 분기용) — 캐릭터 없이 씬 generate 경로만 검증."""
    d = tmp_path / "codex_project"
    d.mkdir()
    (d / "characters").mkdir()
    (d / "images").mkdir()

    (d / "art_style.json").write_text(json.dumps({
        "id": "quirky_cartoon",
        "name": "Quirky Cartoon",
        "reference_image": "",
        "scene_style_description": "cartoon",
        "style": {"art_style": "flat cute 2D"},
        "technical": {"critical_requirements": []},
    }))

    (d / "scene_specs.json").write_text(json.dumps({
        "scenes": [
            {
                "sceneNumber": 1,
                "narration": "성공 씬",
                "imageAsset": {"source": "generate", "prompt": "success scene"},
                "characters": [],
            },
            {
                "sceneNumber": 2,
                "narration": "실패 씬",
                "imageAsset": {"source": "generate", "prompt": "fail scene"},
                "characters": [],
            },
        ]
    }))
    return d


def test_run_batch_codex_success_registers_and_fail_falls_back_to_fal(codex_project_dir):
    """codex 배치: 성공 씬은 image_assets 등록, 실패 씬만 FAL 폴백 배치로 이동."""
    from auto_agent.tools.codex_fleet import CodexImageResult

    def fake_codex_batch(jobs, on_done=None, timeout=240):
        results = []
        for job in jobs:
            # idx 0 → 성공(파일이 실제로 out_path에 생겼다고 가정), idx 1 → 실패
            if job.idx == 0:
                job.out_path.parent.mkdir(parents=True, exist_ok=True)
                job.out_path.write_bytes(b"fake-png-bytes")
                res = CodexImageResult(idx=job.idx, success=True)
            else:
                res = CodexImageResult(idx=job.idx, success=False, error="codex 실패")
            if on_done:
                on_done(res)
            results.append(res)
        return results

    fal_result = MagicMock(success=True, idx=0, images=[{"url": "http://fake/fb.png"}])

    with patch("auto_agent.modules.image_batch_module.codex_available", return_value=True), \
         patch("auto_agent.modules.image_batch_module.run_codex_batch", side_effect=fake_codex_batch), \
         patch("auto_agent.modules.image_batch_module.validate_prompt", return_value=(True, "")), \
         patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq, \
         patch("auto_agent.modules.image_batch_module._save_image_from_url") as mock_save:
        mock_fq.run_batch.side_effect = lambda jobs, on_done=None, **kw: on_done and [on_done(fal_result)]
        mock_save.return_value = codex_project_dir / "images" / "generated" / "scene_002_gen_01.png"

        result = run_batch(codex_project_dir)

    assert result["backend"] == "codex"
    # 성공 씬(codex) + 실패 씬(FAL 폴백 성공) = 2 성공, 0 실패
    assert result["scenes_success"] == 2
    assert result["scenes_fail"] == 0
    # FAL 배치는 실패한 1개 씬에 대해서만 호출됨
    assert mock_fq.run_batch.call_count == 1
    fal_jobs_arg = mock_fq.run_batch.call_args[0][0]
    assert len(fal_jobs_arg) == 1


def test_run_batch_codex_registration_failure_keeps_orphan_no_fal_fallback():
    """codex 성공 + add_version 예외 시 FAL 폴백에 넣지 않고 실패 카운트만 한다."""
    from auto_agent.tools.codex_fleet import CodexImageResult
    import tempfile
    from pathlib import Path as _Path

    with tempfile.TemporaryDirectory() as tmp:
        d = _Path(tmp) / "orphan_project"
        d.mkdir()
        (d / "characters").mkdir()
        (d / "images").mkdir()
        (d / "art_style.json").write_text(json.dumps({
            "id": "quirky_cartoon", "name": "Quirky Cartoon", "reference_image": "",
            "scene_style_description": "cartoon", "style": {"art_style": "flat cute 2D"},
            "technical": {"critical_requirements": []},
        }))
        (d / "scene_specs.json").write_text(json.dumps({
            "scenes": [{
                "sceneNumber": 1, "narration": "성공 씬",
                "imageAsset": {"source": "generate", "prompt": "success scene"},
                "characters": [],
            }]
        }))

        def fake_codex_batch(jobs, on_done=None, timeout=240):
            results = []
            for job in jobs:
                job.out_path.parent.mkdir(parents=True, exist_ok=True)
                job.out_path.write_bytes(b"fake-png-bytes")
                res = CodexImageResult(idx=job.idx, success=True)
                if on_done:
                    on_done(res)
                results.append(res)
            return results

        with patch("auto_agent.modules.image_batch_module.codex_available", return_value=True), \
             patch("auto_agent.modules.image_batch_module.run_codex_batch", side_effect=fake_codex_batch), \
             patch("auto_agent.modules.image_batch_module.validate_prompt", return_value=(True, "")), \
             patch("auto_agent.modules.image_batch_module.image_assets.add_version",
                   side_effect=Exception("등록 실패")) as mock_add_version, \
             patch("auto_agent.modules.image_batch_module.fal_queue") as mock_fq:
            result = run_batch(d)

        assert result["backend"] == "codex"
        assert result["scenes_success"] == 0
        assert result["scenes_fail"] == 1
        # add_version은 1회 재시도까지 총 2회 호출되어야 함
        assert mock_add_version.call_count == 2
        # 등록 실패는 폴백 신호가 아니므로 FAL 배치는 전혀 호출되지 않는다
        assert mock_fq.run_batch.call_count == 0
        # codex가 만든 파일은 삭제되지 않고 그대로(고아) 남아 있어야 한다
        orphan_files = list((d / "images" / "generated").glob("*.png"))
        assert len(orphan_files) == 1
