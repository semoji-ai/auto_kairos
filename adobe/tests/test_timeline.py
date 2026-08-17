import json
from pathlib import Path

from backend import timeline


def _proj(tmp_path, scenes_list):
    proj = tmp_path / "p"
    (proj / "audio").mkdir(parents=True)
    (proj / "scenes.json").write_text(json.dumps(
        {"project_id": "p", "scenes": scenes_list}, ensure_ascii=False), encoding="utf-8")
    return proj


def test_scene_timings_accumulate_tts_duration(tmp_path, monkeypatch):
    proj = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "aaa", "narration": "첫 씬"},
        {"sceneNumber": 2, "sceneId": "bbb", "narration": "둘째 씬"},   # 오디오 없음 → 5초
        {"sceneNumber": 3, "sceneId": "ccc", "narration": "셋째 씬"},
    ])
    (proj / "audio" / "tts_aaa.mp3").write_bytes(b"x")
    (proj / "audio" / "tts_ccc.mp3").write_bytes(b"x")
    monkeypatch.setattr(timeline._tts, "audio_duration", lambda p: 2.0)

    from backend import scenes as _scenes
    data = _scenes.load_scenes(proj)
    timings = timeline.scene_timings(proj, data)
    starts = [start for _s, start, _dur in timings]
    durs = [dur for _s, _start, dur in timings]
    assert durs == [2.0, timeline.DEFAULT_DUR, 2.0]
    assert starts == [0.0, 2.0, 7.0]
    assert timeline.comp_name(timings[0][0]) == "S01_aaa"


def test_comp_name_prefers_existing():
    assert timeline.comp_name({"sceneNumber": 7, "sceneId": "zz"}) == "S07_zz"
    assert timeline.comp_name({"sceneNumber": 7, "sceneId": "zz", "ae_comp_name": "Custom"}) == "Custom"


def test_comp_num_handles_inserted_scene():
    assert timeline.comp_num(3) == "03"
    assert timeline.comp_num(25.0) == "25"
    assert timeline.comp_num(25.25) == "25-25"      # 점은 컴프 이름에 부적합, 밑줄도 접두사 충돌 위험
    assert timeline.comp_num(None) == "00"


def test_comp_num_fractional_prefix_does_not_collide_with_integer_prefix():
    """씬 25와 삽입 씬 25.25가 함께 있을 때, 어느 쪽 레이어 접두사도
    다른 쪽 레이어 이름의 접두사가 되면 안 된다.

    밑줄 구분자였다면 "S25_25_배경".indexOf("S25_") === 0 이라 akRemoveSceneGroup("S25_")가
    25.25 씬의 레이어까지 지워버렸다(회귀 재현 방지)."""
    prefix_25 = f"S{timeline.comp_num(25)}_"
    prefix_25_25 = f"S{timeline.comp_num(25.25)}_"
    layer_name_25 = prefix_25 + "배경"
    layer_name_25_25 = prefix_25_25 + "배경"
    assert not layer_name_25_25.startswith(prefix_25)
    assert not layer_name_25.startswith(prefix_25_25)


def test_scene_duration_uses_estimate_before_default(tmp_path):
    assert timeline.scene_duration(tmp_path, {"duration_estimate_sec": 7}) == 7.0
    assert timeline.scene_duration(tmp_path, {}) == timeline.DEFAULT_DUR


def test_manifest_and_timeline_agree_on_name_and_length(tmp_path, monkeypatch):
    """컴프·자막·타임라인이 같은 이름·같은 길이를 봐야 한다(어긋나면 배치가 씬을 못 찾음)."""
    import json as _j
    from backend import manifest, subtitles
    proj = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "가"},
                            {"sceneNumber": 1.5, "sceneId": "b", "narration": "나"}])
    (proj / "audio" / "tts_a.mp3").write_bytes(b"x")
    monkeypatch.setattr(timeline._tts, "audio_duration", lambda p: 7.802)

    data = timeline._scenes.load_scenes(proj)
    timings = timeline.scene_timings(proj, data)
    mf = _j.loads(Path(manifest.build_manifest(proj)["path"]).read_text(encoding="utf-8"))
    assert [timeline.comp_name(s) for s, _start, _dur in timings] == [s["ae_comp_name"] for s in mf["scenes"]]
    assert [dur for _s, _start, dur in timings] == [s["duration"] for s in mf["scenes"]]
    # 자막 오프셋도 같은 누적을 쓴다
    subtitles.build_subtitles(proj)
    cues = _j.loads((proj / "subtitles.json").read_text(encoding="utf-8"))["cues"]
    assert cues[-1]["start"] >= 7.802           # 둘째 씬은 첫 씬 음성 길이 뒤에서 시작
