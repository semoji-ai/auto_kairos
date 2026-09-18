import copy
import json
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from auto_agent import video_tracks as vt
from auto_agent.dashboard import video_tracks as api


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "video_sources").mkdir()
    (tmp_path / "video_sources/clip.mp4").write_bytes(b"fixture")
    scenes = [{"sceneNumber": i, "sceneId": f"s{i}", "durationFrames": 60, "narration": f"line{i}"}
              for i in [1, 2, 3]]
    (tmp_path / "scene_specs.json").write_text(json.dumps({"scenes": scenes}))
    monkeypatch.setattr(vt, "media_duration", lambda _: 12)
    return tmp_path


def tracks(**kw):
    clip = dict(clipId="test", enabled=True, sourcePath="video_sources/clip.mp4",
                sceneIds=["s1", "s2"], anchor={"sceneId": "s1", "offsetFrames": 0},
                sourceInSec=1, sourceOutSec=5, playbackRate=1, audioPolicy="mute")
    clip.update(kw)
    return dict(schemaVersion=1, revision=0, tracks=[dict(trackId="main", enabled=True, clips=[clip])])


def test_no_file_legacy_unchanged(project):
    manifest = {"meta": {"fps": 30}, "scenes": [{"sceneNumber": 1, "audioDurationSec": 2}]}
    original = copy.deepcopy(manifest)
    vt.attach_manifest(project, manifest)
    assert manifest == original


def test_manifest_clip_once_and_preview_offset(project):
    assert vt.save(project, tracks(), expect_revision=0)["ok"]
    manifest = {"meta": {"fps": 30}, "scenes": [{"sceneNumber": i} for i in [1, 2, 3]]}
    vt.attach_manifest(project, manifest)
    assert len(manifest["videoClips"]) == 1
    assert manifest["videoClips"][0]["timelineDurationFrames"] == 120
    assert manifest["scenes"][0]["videoTrackSlices"][0]["sourceIn"] == 1
    assert manifest["scenes"][1]["videoTrackSlices"][0]["sourceIn"] == 3
    assert manifest["scenes"][2]["videoTrackSlices"] == []
    vt.web_paths(manifest, "/output/p/")
    assert manifest["videoClips"][0]["sourcePath"] == "/output/p/video_sources/clip.mp4"


@pytest.mark.parametrize("change", [
    {"sourcePath": "../outside.mp4"}, {"sourcePath": "/tmp/clip.mp4"},
    {"sceneIds": ["s2", "s1"]}, {"sceneIds": ["s1", "s3"]},
    {"sceneIds": ["s1", "missing"]}, {"sceneIds": ["s1", "s1"]},
    {"sourceOutSec": 13}, {"sourceInSec": -1}, {"sourceOutSec": float("nan")},
    {"anchor": {"sceneId": "s1", "offsetFrames": -1}}, {"sourceOutSec": 1},
    {"playbackRate": 2}, {"audioPolicy": "keep"},
])
def test_bad_clip_rejected_without_write(project, change):
    r = vt.save(project, tracks(**change), expect_revision=0)
    assert r["error"] and r["errors"]
    assert not (project / vt.FILE_NAME).exists()


def test_short_clip_keeps_partial_fallback(project):
    r = vt.resolve(project, tracks(sourceOutSec=4))
    assert r["covered"] == {"s1"}
    assert r["clips"][0]["warnings"]
    assert r["clips"][0]["timelineDurationFrames"] == 90


def test_overlap_across_tracks_and_duplicate_ids(project):
    d = tracks()
    d["tracks"].append(dict(trackId="other", clips=[{**d["tracks"][0]["clips"][0], "clipId": "two"}]))
    assert "겹침" in vt.resolve(project, d)["errors"][0]
    d["tracks"][1]["clips"][0]["clipId"] = "test"
    assert "clipId" in vt.resolve(project, d)["errors"][0]


def test_stale_script_or_duration_blocks_activation(project):
    vt.save(project, tracks(), expect_revision=0)
    path = project / "scene_specs.json"
    specs = json.loads(path.read_text())
    specs["scenes"][1]["narration"] = "changed"
    path.write_text(json.dumps(specs))
    r = vt.resolve(project, vt.load(project))
    assert not r["clips"] and "재검토" in r["errors"][0]


def test_revision_cross_thread_lock(project):
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: vt.save(project, tracks(), expect_revision=0), range(2)))
    assert sum(bool(r.get("ok")) for r in results) == 1
    assert vt.load(project)["revision"] == 1


def test_api_roundtrip_and_no_mutation_on_bad_data(project, monkeypatch):
    monkeypatch.setattr(api, "project_root", lambda _: project)
    app = FastAPI(); app.include_router(api.router)
    client = TestClient(app)
    url = "/api/p/p/video-tracks"
    assert client.get(url).json()["data"]["revision"] == 0
    assert client.post(url, json={"revision": 0, "data": tracks()}).status_code == 200
    assert client.post(url, json={"revision": 0, "data": tracks()}).status_code == 409
    assert client.post(url, json={"revision": 1, "data": tracks(sourceOutSec=99)}).status_code == 422
    assert vt.load(project)["revision"] == 1
    assert client.get(url).json()["resolved"]["clips"][0]["url"].endswith("/video_sources/clip.mp4")


def test_real_probe_24fps_source(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg unavailable")
    p = tmp_path / "probe.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=red:s=64x64:r=24",
                    "-t", "1", "-c:v", "libx264", str(p)], check=True)
    assert vt.media_duration(p) == pytest.approx(1, abs=0.01)


def test_symlink_escape(project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside") / "x.mp4"; outside.write_bytes(b"video")
    (project / "video_sources/link.mp4").symlink_to(outside)
    assert vt.resolve(project, tracks(sourcePath="video_sources/link.mp4"))["errors"]


def test_corrupt_contract_never_overwritten(project):
    path = project / vt.FILE_NAME; path.write_text("{broken")
    assert vt.save(project, tracks(), expect_revision=0)["error"]
    assert path.read_text() == "{broken"


def test_adobe_specs_drift_blocks_track_not_silently_retargets(project):
    from backend import video_tracks as adobe
    (project / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "a1", "duration_estimate_sec": 2}]}))
    r = adobe.resolve(project, tracks())
    assert not r["clips"] and "순서 불일치" in r["errors"][0]


def test_adobe_aliases_use_same_clock(project):
    from backend import video_tracks as adobe
    (project / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": i, "sceneId": f"a{i}", "duration_estimate_sec": 99}
        for i in [1, 2, 3]]}))
    r = adobe.resolve(project, tracks())
    assert r["covered"] == {"s1", "s2", "a1", "a2"}
    assert r["clips"][0]["duration"] == 4


def test_prepare_is_disabled_and_does_not_write(project):
    from auto_agent.scripts.prepare_video_tracks import prepare
    cutlist = {"units": [{"id": "c", "shots": [
        {"sceneNumber": 1, "sceneId": "s1", "narration": "line1"},
        {"sceneNumber": 2, "sceneId": "s2", "narration": "line2"}]}]}
    ledger = [{"id": "c", "path": "/another-machine/video_sources/clip.mp4"}]
    result = prepare(project, cutlist, ledger)
    assert result["data"]["tracks"][0]["clips"][0]["enabled"] is False
    assert not result["audit"][0]["errors"]
    assert not (project / vt.FILE_NAME).exists()
