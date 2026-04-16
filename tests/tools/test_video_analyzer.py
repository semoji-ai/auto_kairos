import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


def test_analyze_returns_scenes_list():
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "duration_sec": 61.0,
        "scenes": [
            {"start": 0.0, "end": 3.0, "description": "타이틀 카드 — 포켓몬 로고 등장", "tags": ["title", "logo"]},
            {"start": 3.0, "end": 8.0, "description": "피카츄 달리기 장면", "tags": ["pikachu", "action"]},
        ]
    })
    with patch("auto_agent.tools.video_analyzer._gemini_generate", return_value=mock_response):
        from auto_agent.tools.video_analyzer import analyze_video
        # stat() mock 필요
        fake_path = MagicMock(spec=Path)
        fake_path.suffix = ".mp4"
        fake_path.stat.return_value.st_size = 5 * 1024 * 1024  # 5MB
        fake_path.read_bytes.return_value = b"fake_video_data"
        result = analyze_video(fake_path)
    assert isinstance(result["scenes"], list)
    assert result["scenes"][0]["start"] == 0.0
    assert "description" in result["scenes"][0]


def test_analyze_handles_json_fenced():
    mock_response = MagicMock()
    mock_response.text = '```json\n{"duration_sec": 30.0, "language": "ja", "scenes": []}\n```'
    with patch("auto_agent.tools.video_analyzer._gemini_generate", return_value=mock_response):
        from auto_agent.tools.video_analyzer import analyze_video
        fake_path = MagicMock(spec=Path)
        fake_path.suffix = ".mp4"
        fake_path.stat.return_value.st_size = 1 * 1024 * 1024
        fake_path.read_bytes.return_value = b"fake"
        result = analyze_video(fake_path)
    assert result["duration_sec"] == 30.0


def test_analyze_large_file_uses_upload():
    mock_response = MagicMock()
    mock_response.text = json.dumps({"duration_sec": 200.0, "scenes": []})
    with patch("auto_agent.tools.video_analyzer._gemini_generate_large", return_value=mock_response) as mock_large:
        from auto_agent.tools.video_analyzer import analyze_video
        fake_path = MagicMock(spec=Path)
        fake_path.suffix = ".mp4"
        fake_path.stat.return_value.st_size = 25 * 1024 * 1024  # 25MB > 19MB
        result = analyze_video(fake_path)
    mock_large.assert_called_once()
    assert result["duration_sec"] == 200.0
