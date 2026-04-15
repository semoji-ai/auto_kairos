import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SAMPLE_PLAN = {
    "series_id": "lg_brand_encyclopedia",
    "title": "당신이 몰랐던 LG의 역사",
    "channel": "세모지",
    "writing_style": "semoji",
    "total_episodes": 2,
    "series_angle": "test",
    "series_hook": "test hook",
    "key_entities": [],
    "episodes": [
        {
            "episode_number": 1,
            "title": "EP1",
            "scope_start": "1907",
            "scope_end": "1947",
            "core_question": "Q1",
            "key_events": [],
            "key_persons": [],
        },
        {
            "episode_number": 2,
            "title": "EP2",
            "scope_start": "1947",
            "scope_end": "1969",
            "core_question": "Q2",
            "key_events": [],
            "key_persons": [],
        },
    ]
}

def test_build_episode_run_order():
    """에피소드는 episode_number 오름차순으로 실행되어야 한다."""
    from auto_agent.orchestrator.series_runner import build_episode_run_order
    order = build_episode_run_order(SAMPLE_PLAN)
    assert [ep["episode_number"] for ep in order] == [1, 2]

def test_build_episode_project_slug():
    """각 에피소드의 project_slug는 series_id_ep{N} 형식이어야 한다."""
    from auto_agent.orchestrator.series_runner import build_episode_project_slug
    slug = build_episode_project_slug("lg_brand_encyclopedia", 3)
    assert slug == "lg_brand_encyclopedia_ep03"

def test_series_run_dry_run_creates_brief_files():
    """dry_run=True이면 episode_brief.json 파일이 생성되어야 한다."""
    import tempfile
    from auto_agent.orchestrator.series_runner import series_run
    with tempfile.TemporaryDirectory() as tmpdir:
        series_run(SAMPLE_PLAN, output_base=Path(tmpdir), dry_run=True)
        for ep_num in [1, 2]:
            slug = f"lg_brand_encyclopedia_ep{ep_num:02d}"
            brief_path = Path(tmpdir) / slug / "episode_brief.json"
            assert brief_path.exists(), f"Missing: {brief_path}"

def test_series_run_calls_runner_for_each_episode():
    """series_run은 dry_run=False이면 각 에피소드마다 run_single_episode를 호출한다."""
    import tempfile
    from auto_agent.orchestrator.series_runner import series_run

    call_args = []
    def mock_run(project, stop_after_step=None, **kwargs):
        call_args.append({"project": project, "stop_after_step": stop_after_step})
        return {"status": "completed"}

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("auto_agent.orchestrator.series_runner.run_single_episode", mock_run):
            series_run(SAMPLE_PLAN, output_base=Path(tmpdir), dry_run=False)

    assert len(call_args) == 2
    assert all(c["stop_after_step"] == "step_2b" for c in call_args)
