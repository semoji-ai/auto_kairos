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


def test_inline_preview_offsets_and_partial_tail(project):
    assert vt.save(project, tracks(sourceOutSec=4), expect_revision=0)["ok"]
    previews = vt.project_previews(project)
    assert previews[1][0]["sourceIn"] == 1
    assert previews[1][0]["sourceOut"] == 3
    assert previews[2][0]["sourceIn"] == 3
    assert previews[2][0]["sourceOut"] == 4
    assert previews[2][0]["sceneDuration"] == 2
    assert 3 not in previews


def test_inline_preview_anchor_and_disabled(project):
    assert vt.save(project, tracks(anchor={"sceneId": "s1", "offsetFrames": 15}),
                   expect_revision=0)["ok"]
    previews = vt.project_previews(project)
    assert previews[1][0]["sceneOffset"] == 0.5
    assert previews[2][0]["sourceIn"] == 2.5
    assert vt.save(project, tracks(enabled=False), expect_revision=1)["ok"]
    assert vt.project_previews(project) == {}


def test_inline_preview_stale_fingerprint_hidden(project):
    assert vt.save(project, tracks(), expect_revision=0)["ok"]
    path = project / "scene_specs.json"
    data = json.loads(path.read_text())
    data["scenes"][0]["narration"] = "changed"
    path.write_text(json.dumps(data))
    assert vt.project_previews(project) == {}
    assert vt.project_previews(project, include_candidates=True) == {}


def test_disabled_clip_preview_does_not_activate_or_write(project):
    assert vt.save(project, tracks(enabled=False), expect_revision=0)["ok"]
    path = project / vt.FILE_NAME
    before = path.read_bytes()
    previews = vt.project_previews(project, include_candidates=True)
    assert previews[2][0]["sourceIn"] == 3
    assert previews[2][0]["previewOnly"] is True
    assert path.read_bytes() == before
    assert vt.resolve(project, vt.load(project))["clips"] == []


def test_mapping_draft_preview_without_import(project):
    folder = project / "video_sources/planning/test"
    folder.mkdir(parents=True)
    draft = folder / "video_tracks.draft.json"
    draft.write_text(json.dumps({"data": tracks(enabled=False)}))
    before = draft.read_bytes()
    previews = vt.project_previews(project, include_candidates=True)
    assert len(previews) == 2
    assert previews[1][0]["previewOnly"] is True
    assert previews[2][0]["sourceIn"] == 3
    assert not (project / vt.FILE_NAME).exists()
    assert draft.read_bytes() == before
    # An explicit saved contract, even empty, supersedes older mapping drafts.
    (project / vt.FILE_NAME).write_text(json.dumps({"schemaVersion": 1, "tracks": []}))
    assert vt.project_previews(project, include_candidates=True) == {}


def test_draft_invalid_path_not_previewed(project):
    folder = project / "video_sources/planning/test"
    folder.mkdir(parents=True)
    (folder / "video_tracks.draft.json").write_text(json.dumps({
        "data": tracks(enabled=False, sourcePath="../outside.mp4")}))
    assert vt.project_previews(project, include_candidates=True) == {}


def test_inline_template_and_shared_player():
    from jinja2 import Environment, FileSystemLoader
    root = Path(__file__).resolve().parents[1]
    env = Environment(loader=FileSystemLoader(root / "auto_agent/dashboard/templates"), autoescape=True)
    html = env.get_template("partials/_scene_switch.html").render(scene={
        "sceneNumber": 2, "_video_url": "/clip.mp4", "_layers": [],
        "_track_previews": [{"url": '/clip.mp4?a="b"', "sourceIn": 3, "sourceOut": 4,
                             "sceneOffset": 0, "clipId": "<unsafe>"}],
    })
    assert 'data-mode="video"' in html
    assert 'data-in="3"' in html and 'data-out="4"' in html
    assert "&lt;unsafe&gt;" in html and "<unsafe>" not in html
    global_html = env.get_template("partials/_scene_switch.html").render(
        global_preview=True, scene={"sceneNumber": 1, "_video_url": "/clip.mp4", "_layers": []})
    assert 'class="svb' not in global_html
    assert '<video ' in global_html
    assert (root / "auto_agent/dashboard/static/track-preview.js").read_bytes() == (
        root / "adobe/cep/com.autokairos.pd/js/track-preview.js").read_bytes()


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
