from pathlib import Path

ROOT = Path("/Users/jleavens_macmini/Projects/auto_kairos_v3")


def _read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def test_simple_video_does_not_add_percent_padding_to_audio_timing():
    for rel_path in (
        "remotion/src/SimpleVideo.tsx",
        "auto_agent/remotion_template/src/SimpleVideo.tsx",
    ):
        content = _read(rel_path)
        assert "rawFrames * 0.02" not in content
        assert "rawFrames + padding" not in content
        assert "Math.ceil(scene.audioDurationSec * fps)" in content


def test_subtitle_track_does_not_add_extra_frames_beyond_scene_duration():
    for rel_path in (
        "remotion/src/components/SubtitleTrack.tsx",
        "auto_agent/remotion_template/src/components/SubtitleTrack.tsx",
    ):
        content = _read(rel_path)
        assert "+ 2" not in content
        assert "Math.ceil(scene.audioDurationSec * fps)" in content


def test_subtitle_overlay_last_subtitle_hold_is_frame_sized_not_one_second():
    for rel_path in (
        "remotion/src/components/SubtitleOverlay.tsx",
        "auto_agent/remotion_template/src/components/SubtitleOverlay.tsx",
    ):
        content = _read(rel_path)
        assert "s.endSec + 1" not in content
        assert "1 / fps" in content
