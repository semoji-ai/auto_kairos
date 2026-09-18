"""여러 씬에 걸치는 비디오 트랙 — 계약·resolver·manifest 통합.

원칙: 트랙 파일이 없으면 아무것도 달라지지 않는다. 활성 클립이 덮는 씬은
씬별 영상이 빠진다(자동 v_<sid> 선택이 명시 배치를 못 덮게). 잘못된 클립은
조용히 얹지 않고 errors 로 드러낸다.
"""
import json
import pytest
from pathlib import Path

from backend import manifest, video_tracks

JSX_DIR = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd" / "jsx"


@pytest.fixture(autouse=True)
def fake_probe(monkeypatch):
    # Contract unit tests use placeholder bytes. Real ffprobe is tested separately.
    monkeypatch.setattr("auto_agent.video_tracks.media_duration", lambda p: 12.0)


def _proj(tmp_path, n_scenes=3):
    d = tmp_path / "p"; d.mkdir()
    arr = [{"sceneNumber": i + 1, "sceneId": f"sid{i + 1}",
            "duration_estimate_sec": 4} for i in range(n_scenes)]
    (d / "scenes.json").write_text(json.dumps({"scenes": arr}), encoding="utf-8")
    (d / "video_sources").mkdir()
    (d / "video_sources" / "clip.mp4").write_bytes(b"\x00" * 16)
    return d


def _tracks(clip_over=None):
    clip = {"clipId": "c1", "enabled": True,
            "sourcePath": "video_sources/clip.mp4",
            "sceneIds": ["sid1", "sid2"],
            "anchor": {"sceneId": "sid1", "offsetFrames": 0},
            "sourceInSec": 0, "sourceOutSec": 8.0,
            "playbackRate": 1, "audioPolicy": "mute"}
    clip.update(clip_over or {})
    return {"schemaVersion": 1, "revision": 1,
            "tracks": [{"trackId": "primary-video", "enabled": True, "clips": [clip]}]}


def test_no_file_resolves_empty_and_manifest_unchanged(tmp_path):
    d = _proj(tmp_path)
    r = video_tracks.resolve(d, video_tracks.load(d))
    assert r["clips"] == [] and r["covered"] == set() and r["errors"] == []
    manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert "videoClips" not in mf and "videoClipErrors" not in mf


def test_resolve_places_at_first_scene_in_point(tmp_path):
    d = _proj(tmp_path)
    (d / "video_tracks.json").write_text(json.dumps(_tracks()), encoding="utf-8")
    r = video_tracks.resolve(d, video_tracks.load(d))
    assert not r["errors"]
    c = r["clips"][0]
    assert c["start"] == 0.0                     # 첫 씬 in점
    assert c["duration"] == 8.0                  # 씬1+씬2 = 8초 범위와 일치
    assert c["muted"] is True
    assert r["covered"] == {"sid1", "sid2"}


def test_resolve_clamps_long_source_to_scene_range(tmp_path):
    """원본이 범위보다 길면 범위 끝에서 자른다 — 다음 씬을 조용히 덮지 않는다."""
    d = _proj(tmp_path)
    (d / "video_tracks.json").write_text(
        json.dumps(_tracks({"sourceOutSec": 11.0})), encoding="utf-8")
    r = video_tracks.resolve(d, video_tracks.load(d))
    c = r["clips"][0]
    assert c["duration"] == 8.0 and c["warnings"]


def test_resolve_rejects_bad_clips(tmp_path):
    d = _proj(tmp_path)
    bad = _tracks()
    bad["tracks"][0]["clips"] += [
        {**_tracks()["tracks"][0]["clips"][0], "clipId": "no-src",
         "sourcePath": "video_sources/none.mp4"},
        {**_tracks()["tracks"][0]["clips"][0], "clipId": "bad-scene",
         "sceneIds": ["sid1", "없는씬"]},
        {**_tracks()["tracks"][0]["clips"][0], "clipId": "not-consecutive",
         "sceneIds": ["sid1", "sid3"], "anchor": {"sceneId": "sid1"}},
        {**_tracks()["tracks"][0]["clips"][0], "clipId": "overlap"},  # c1 과 같은 구간
        {**_tracks()["tracks"][0]["clips"][0], "clipId": "inverted",
         "sourceInSec": 5, "sourceOutSec": 3},
    ]
    (d / "video_tracks.json").write_text(json.dumps(bad), encoding="utf-8")
    r = video_tracks.resolve(d, video_tracks.load(d))
    assert [c["clipId"] for c in r["clips"]] == ["c1"]
    joined = "\n".join(r["errors"])
    for key in ("no-src", "bad-scene", "not-consecutive", "overlap", "inverted"):
        assert key in joined


def test_disabled_clip_and_track_are_ignored(tmp_path):
    d = _proj(tmp_path)
    t = _tracks({"enabled": False})
    (d / "video_tracks.json").write_text(json.dumps(t), encoding="utf-8")
    assert video_tracks.resolve(d, video_tracks.load(d))["clips"] == []


def test_manifest_suppresses_scene_video_for_covered_scenes(tmp_path):
    """활성 클립이 덮는 씬은 v_<sid> 자동 선택이 빠진다 — 두 벌 재생 방지."""
    d = _proj(tmp_path)
    (d / "video").mkdir()
    (d / "video" / "v_sid1_h3.mp4").write_bytes(b"\x00")   # 씬별 영상(자동 선택 대상)
    (d / "video" / "v_sid3_h3.mp4").write_bytes(b"\x00")   # 트랙 밖 씬 — 유지돼야 한다
    (d / "video_tracks.json").write_text(json.dumps(_tracks()), encoding="utf-8")
    manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert len(mf["videoClips"]) == 1
    assert mf["videoClips"][0]["clipId"] == "c1"
    by_sid = {s["prefix"]: s for s in mf["scenes"]}
    assert "video" not in by_sid["S01_"]                   # 덮인 씬 — 억제
    assert by_sid["S03_"]["video"].endswith("v_sid3_h3.mp4")    # 트랙 밖 — 유지


def test_save_detects_revision_conflict(tmp_path):
    d = _proj(tmp_path)
    assert video_tracks.save(d, _tracks(), expect_revision=0)["ok"]
    stale = video_tracks.save(d, _tracks(), expect_revision=0)
    assert "error" in stale and stale["revision"] == 1


def test_jsx_places_clip_once_and_replaces_by_clip_id():
    """AE — 클립은 씬 접두사와 분리된 「클립_<clipId>」 이름으로 한 번 배치,
    재빌드 시 같은 clipId 를 교체한다. 새것을 먼저 얹고 옛것을 지운다."""
    src = (JSX_DIR / "build_scene.jsx").read_text(encoding="utf-8")
    block = src.split("m.videoClips")[1].split("// 말자막")[0]
    assert '"클립_" + cv.clipId' in block
    assert ".remove()" in block                        # clipId 교체
    assert "audioEnabled = false" in block             # TTS 와 겹치지 않게
    assert "cv.start - (cv.sourceIn || 0)" in block    # 원본 offset → startTime
    assert block.index("comp.layers.add") < block.index(".remove()")
    # 자막 최상단 올리기가 클립 배치 **뒤**에 와야 자막이 클립 위에 남는다
    assert src.index("m.videoClips") < src.index('=== "말자막"')


def test_jsx_premiere_places_clip_on_v2_and_strips_audio():
    src = (JSX_DIR / "build_sequence.jsx").read_text(encoding="utf-8")
    block = src.split("M.videoClips")[1].split("자막은 빈에")[0]
    assert "vt2.overwriteClip" in block                # V2 한 번 배치
    assert "audioTracks" in block and "remove(false, false)" in block   # 내장 오디오 제거
    assert "setInPoint" in block                       # 원본 in 적용
