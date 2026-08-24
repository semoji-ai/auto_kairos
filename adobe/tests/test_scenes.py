import json
from pathlib import Path
from backend import scenes


def _proj(tmp_path, scene_list):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(
        json.dumps({"project_id": "p", "scenes": scene_list}, ensure_ascii=False),
        encoding="utf-8")
    return d


def _scene(d, n):
    import json as _j
    data = _j.loads((d / "scenes.json").read_text(encoding="utf-8"))
    return next(s for s in data["scenes"] if s["sceneNumber"] == n)


def test_load_scenes_image_from_imageref(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lnk00001",
                          "imageRef": "images/pick.png", "image_prompt": "x"}])
    (d / "images").mkdir(); (d / "images" / "pick.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "images/pick.png"      # 링크가 가리키는 파일


def test_load_scenes_imageref_missing_file(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lnk00002",
                          "imageRef": "images/gone.png"}])
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] is None                    # 파일 없으면 끊김


def test_load_scenes_backfills_imageref_from_sb(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "bf000001", "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir(); (sb / "sb_bf000001.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["imageRef"] == "storyboard/sb_bf000001.png"   # 백필
    assert s["_image"] == "storyboard/sb_bf000001.png"


def test_set_image_ref_link_and_unlink(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 2, "sceneId": "s2", "image_prompt": "x"}])
    (d / "images").mkdir(); (d / "images" / "a.png").write_bytes(b"\x89PNG")
    assert scenes.set_image_ref(d, 2, "images/a.png")["ok"] is True
    assert _scene(d, 2)["imageRef"] == "images/a.png"
    # 해제
    assert scenes.set_image_ref(d, 2, "")["ok"] is True
    assert _scene(d, 2)["imageRef"] == ""


def test_set_image_ref_rejects_traversal_and_missing(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "s1"}])
    assert "error" in scenes.set_image_ref(d, 1, "../../etc/hosts")
    assert "error" in scenes.set_image_ref(d, 1, "images/nope.png")


def test_new_scene_image_name_unique(tmp_path):
    a = scenes.new_scene_image_name("abc")
    b = scenes.new_scene_image_name("abc")
    assert a.startswith("scene_abc_") and a.endswith(".png") and a != b


def test_load_scenes_enriches_media_and_layers(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa11111", "title": "A",
                          "narration": "가", "image_prompt": "장면1"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_aaa11111.png").write_bytes(b"\x89PNG")
    (d / "layers").mkdir()
    (d / "layers" / "bg_aaa11111.png").write_bytes(b"\x89PNG")
    (d / "layers" / "char_aaa11111.png").write_bytes(b"\x89PNG")
    data = scenes.load_scenes(d)
    s = data["scenes"][0]
    assert s["_image"] == "storyboard/sb_aaa11111.png"
    assert s["_layers"] == ["layers/bg_aaa11111.png", "layers/char_aaa11111.png"]
    assert data["dir"] == str(d)


def test_load_scenes_layers_glob_by_sid(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lyr00001",
                          "imageRef": "storyboard/sb_lyr00001.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_lyr00001.png").write_bytes(b"\x89PNG")
    lay = d / "layers"; lay.mkdir()
    (lay / "lyr00001__0_car.png").write_bytes(b"\x89PNG")
    (lay / "lyr00001__bg.png").write_bytes(b"\x89PNG")
    (lay / "other__x.png").write_bytes(b"\x89PNG")          # 다른 씬 — 제외
    s = scenes.load_scenes(d)["scenes"][0]
    assert "layers/lyr00001__0_car.png" in s["_layers"]
    assert "layers/lyr00001__bg.png" in s["_layers"]
    assert "layers/other__x.png" not in s["_layers"]


def test_load_scenes_picks_latest_image_version(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 2, "sceneId": "bbb22222", "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    (sb / "sb_bbb22222.png").write_bytes(b"\x89PNG")
    (sb / "sb_bbb22222_v2.png").write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "storyboard/sb_bbb22222_v2.png"


def test_load_scenes_latest_version_numeric_sort(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 5, "sceneId": "ccc55555", "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    for nm in ("sb_ccc55555.png", "sb_ccc55555_v2.png", "sb_ccc55555_v3.png", "sb_ccc55555_v10.png"):
        (sb / nm).write_bytes(b"\x89PNG")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] == "storyboard/sb_ccc55555_v10.png"


def test_load_scenes_no_media(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"}])
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_image"] is None and s["_layers"] == []


def test_load_scenes_missing_file(tmp_path):
    assert scenes.load_scenes(tmp_path / "nope") == {"scenes": [], "dir": ""}


def test_update_narration_sets_dirty(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "narration": "옛", "image_prompt": "x"}])
    res = scenes.update_narration(d, 1, "새 나레이션")
    assert res == {"ok": True, "sceneNumber": 1}
    saved = json.loads((d / "scenes.json").read_text(encoding="utf-8"))
    assert saved["scenes"][0]["narration"] == "새 나레이션"
    assert saved["scenes"][0]["narration_dirty"] is True


def test_update_narration_unknown_scene(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"}])
    assert "error" in scenes.update_narration(d, 99, "x")


def test_ensure_scene_ids_assigns_and_persists(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"},
                         {"sceneNumber": 2, "image_prompt": "y"}])
    scenes.ensure_scene_ids(d)
    saved = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    sids = [s["sceneId"] for s in saved]
    assert all(sids) and len(set(sids)) == 2          # 발급 + 고유
    # 멱등: 재호출해도 sceneId 불변
    scenes.ensure_scene_ids(d)
    saved2 = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"]
    assert [s["sceneId"] for s in saved2] == sids


def test_ensure_scene_ids_migrates_number_assets(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "image_prompt": "x"}])
    sb = d / "storyboard"; sb.mkdir()
    (sb / "sb_1.png").write_bytes(b"IMG")
    (sb / "sb_1_v2.png").write_bytes(b"IMG2")
    lay = d / "layers"; lay.mkdir()
    (lay / "bg_1.png").write_bytes(b"BG"); (lay / "char_1.png").write_bytes(b"CH")
    scenes.ensure_scene_ids(d)
    sid = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]["sceneId"]
    # 번호 에셋이 sid 기반으로 복사됨(무삭제 — 원본도 남음)
    assert (sb / f"sb_{sid}.png").read_bytes() == b"IMG"
    assert (sb / f"sb_{sid}_v2.png").read_bytes() == b"IMG2"
    assert (lay / f"bg_{sid}.png").read_bytes() == b"BG"
    assert (lay / f"char_{sid}.png").read_bytes() == b"CH"
    assert (sb / "sb_1.png").exists()   # 원본 보존(무삭제)


def test_scene_id_for(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 5, "image_prompt": "x"}])
    scenes.ensure_scene_ids(d)
    sid = scenes.scene_id_for(d, 5)
    assert sid and scenes.scene_id_for(d, 99) is None


def test_add_scene_appends_with_new_sid(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa", "narration": "첫째"}])
    data = scenes.add_scene(d, after_number=1, narration="둘째", title="새 씬")
    ss = data["scenes"]
    assert [s["sceneNumber"] for s in ss] == [1, 2]
    assert ss[0]["sceneId"] == "aaa"                 # 기존 유지
    assert ss[1]["sceneId"] and ss[1]["sceneId"] != "aaa"   # 신규 발급
    assert ss[1]["narration"] == "둘째" and ss[1]["title"] == "새 씬"
    assert ss[1]["imageRef"] == ""


def test_add_scene_at_end_when_no_after(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"}])
    data = scenes.add_scene(d)
    assert [s["sceneNumber"] for s in data["scenes"]] == [1, 2]


def test_remove_scene_renumbers_keeps_files(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"},
                         {"sceneNumber": 2, "sceneId": "bbb"},
                         {"sceneNumber": 3, "sceneId": "ccc"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_bbb.png").write_bytes(b"\x89PNG")
    data = scenes.remove_scene(d, 2)
    assert [s["sceneId"] for s in data["scenes"]] == ["aaa", "ccc"]
    assert [s["sceneNumber"] for s in data["scenes"]] == [1, 2]
    assert (d / "storyboard" / "sb_bbb.png").exists()       # 무삭제


def test_split_scene_keeps_sid_first_new_sid_second(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa",
                          "narration": "첫 문장이다. 둘째 문장이다.", "imageRef": "x.png"}])
    data = scenes.split_scene(d, 1)
    ss = data["scenes"]
    assert len(ss) == 2 and ss[0]["sceneId"] == "aaa"
    assert ss[1]["sceneId"] != "aaa" and ss[1]["imageRef"] == ""
    assert ss[0]["narration"] and ss[1]["narration"]        # 양쪽 비어있지 않음
    assert ss[0]["imageRef"] == "x.png"                     # 원본 이미지는 첫 씬에 유지


def test_split_scene_explicit_parts(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa", "narration": "원본"}])
    data = scenes.split_scene(d, 1, first="앞", second="뒤")
    assert data["scenes"][0]["narration"] == "앞" and data["scenes"][1]["narration"] == "뒤"


def test_merge_scenes_concat_keeps_first_sid(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa", "narration": "앞", "imageRef": "a.png"},
                         {"sceneNumber": 2, "sceneId": "bbb", "narration": "뒤", "imageRef": "b.png"}])
    data = scenes.merge_scenes(d, 1)
    ss = data["scenes"]
    assert len(ss) == 1 and ss[0]["sceneId"] == "aaa"
    assert "앞" in ss[0]["narration"] and "뒤" in ss[0]["narration"]
    assert ss[0]["imageRef"] == "a.png"


def test_merge_last_scene_noop(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa"}])
    data = scenes.merge_scenes(d, 1)            # 다음 씬 없음
    assert len(data["scenes"]) == 1


def test_load_scenes_audio_ref(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aud1", "narration": "n"}])
    (d / "audio").mkdir(); (d / "audio" / "tts_aud1.wav").write_bytes(b"x")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_audio"] == "audio/tts_aud1.wav" and s["_status"]["tts"] is True


def test_load_scenes_audio_ignores_timestamp_sidecar(tmp_path):
    # tts_{sid}.timestamps.json(사이드카)이 더 최신이어도 _audio로 선택되면 안 됨
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aud2", "narration": "n"}])
    (d / "audio").mkdir(); (d / "audio" / "tts_aud2.mp3").write_bytes(b"x")
    (d / "audio" / "tts_aud2.timestamps.json").write_text("{}", encoding="utf-8")
    s = scenes.load_scenes(d)["scenes"][0]
    assert s["_audio"] == "audio/tts_aud2.mp3"


def test_load_scenes_status_flags(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "aaa",
                          "narration": "내용", "imageRef": "storyboard/sb_aaa.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_aaa.png").write_bytes(b"\x89PNG")
    (d / "layers").mkdir(); (d / "layers" / "aaa__0_x.png").write_bytes(b"\x89PNG")
    st = scenes.load_scenes(d)["scenes"][0]["_status"]
    assert st["narration"] is True and st["image"] is True and st["layers"] is True
    assert st["tts"] is False


def test_concurrent_mutations_consistent(tmp_path):
    import threading
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "c0", "narration": "기준"}])
    def add_many():
        for _ in range(5):
            scenes.add_scene(d, narration="동시")
    ts = [threading.Thread(target=add_many) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    data = scenes.load_scenes(d)
    assert len(data["scenes"]) == 21                       # 1 + 4*5 (유실 없음)
    nums = [s["sceneNumber"] for s in data["scenes"]]
    assert nums == list(range(1, 22))                      # 재번호 일관


def test_load_scenes_exposes_chart_spec(tmp_path):
    """bar 씬 — chart_{sid}.spec.json 사이드카를 load_scenes가 chartSpec으로 노출(시트 미리보기용)."""
    import json
    from backend import scenes
    d = tmp_path
    (d / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "bs", "layout": "bar", "narration": "x",
         "chart": {"labels": ["a"], "values": [1]}}]}), encoding="utf-8")
    (d / "chart_bs.spec.json").write_text(json.dumps(
        {"patternKind": "crosshatch_light", "outlineWidth": 2.4}), encoding="utf-8")
    data = scenes.load_scenes(d)
    bar = data["scenes"][0]
    assert bar["chartSpec"]["patternKind"] == "crosshatch_light"


def test_set_project_and_scene_theme(tmp_path):
    """프로젝트 전역 theme + 씬별 themeOverride 설정/해제."""
    import json
    from backend import scenes
    (tmp_path / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "a"}]}), encoding="utf-8")
    scenes.set_project_theme(tmp_path, "semoji")
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert d["theme"] == "semoji"
    scenes.set_scene_theme(tmp_path, 1, "dark_broadcast")
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert d["scenes"][0]["themeOverride"] == "dark_broadcast"
    scenes.set_scene_theme(tmp_path, 1, None)   # 해제
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert "themeOverride" not in d["scenes"][0]


def test_load_scenes_exposes_resolved_theme(tmp_path, monkeypatch):
    """load_scenes — 프로젝트 _theme(전역) + 각 씬 _theme(override 반영)."""
    import json
    from backend import scenes, themes
    td = tmp_path / "cat"; td.mkdir()
    (td / "semoji.json").write_text(json.dumps({"id": "semoji", "label": "세모지",
        "colors": {"accentRgb": [1, 2, 3]}, "chart": {"theme_set": "gallery_infographic"},
        "map": {"tile": "bright", "overrides": []}}), encoding="utf-8")
    (td / "dark_broadcast.json").write_text(json.dumps({"id": "dark_broadcast", "label": "다크방송",
        "colors": {"accentRgb": [9, 9, 9]}, "chart": {"theme_set": "broadcast_signal"},
        "map": {"tile": "dark", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    (tmp_path / "scenes.json").write_text(json.dumps({"theme": "semoji", "scenes": [
        {"sceneNumber": 1, "sceneId": "a"},
        {"sceneNumber": 2, "sceneId": "b", "themeOverride": "dark_broadcast"}]}), encoding="utf-8")
    data = scenes.load_scenes(tmp_path)
    assert data["_theme"]["id"] == "semoji"
    assert data["scenes"][0]["_theme"]["id"] == "semoji"
    assert data["scenes"][1]["_theme"]["id"] == "dark_broadcast"


def test_text_accessors_fallback_to_narration():
    from backend import scenes
    s = {"narration": "원고 (지문) 입니다"}
    assert scenes.subtitle_text(s) == "원고 (지문) 입니다"
    assert scenes.tts_text(s) == "원고 입니다"          # 지문 제거된 정리본
    s2 = {"narration": "원고", "narration_tts": "발음", "subtitle_text": "자막"}
    assert scenes.tts_text(s2) == "발음"
    assert scenes.subtitle_text(s2) == "자막"


def test_update_texts_saves_and_clears(tmp_path):
    import json
    from backend import scenes
    (tmp_path / "scenes.json").write_text(json.dumps(
        {"scenes": [{"sceneNumber": 1, "sceneId": "a", "narration": "원고"}]}), encoding="utf-8")
    res = scenes.update_texts(tmp_path, 1, narration_tts="발음", subtitle_text="자막")
    assert res["ok"] and res["narration_tts"] == "발음"
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert d["scenes"][0]["subtitle_text"] == "자막"
    # 빈 문자열 = 필드 제거(원고 폴백 복귀), None = 건드리지 않음
    scenes.update_texts(tmp_path, 1, subtitle_text="")
    d = json.loads((tmp_path / "scenes.json").read_text())
    assert "subtitle_text" not in d["scenes"][0]
    assert d["scenes"][0]["narration_tts"] == "발음"
    assert scenes.update_texts(tmp_path, 9, narration_tts="x")["error"]


def test_load_scenes_exposes_effective_texts(tmp_path):
    import json
    from backend import scenes
    (tmp_path / "scenes.json").write_text(json.dumps(
        {"scenes": [{"sceneNumber": 1, "sceneId": "a", "narration": "원고입니다"}]}), encoding="utf-8")
    s = scenes.load_scenes(tmp_path)["scenes"][0]
    assert s["_tts_text"] == "원고입니다" and s["_subtitle_text"] == "원고입니다"


# ── 원고 삭제 사고 (디아지오 142씬) ────────────────────────────────────────
#
# 통합 뒤 백엔드는 v3 `output/` 폴더를 바로 여는데, v3 프로젝트에는
# `scenes.json` 이 없다 — 원고는 `scene_specs.json` 이다. 그러면 어도비 쪽이
# 0씬이 되고, `mirror_structure` 가 그것을 「전부 지워졌다」로 읽어 광고주
# 컨펌본을 통째로 비웠다. 방아쇠는 패널에서 씬 구성을 한 번 만진 것뿐이었다.

def _specs(d, n):
    (d / "scene_specs.json").write_text(json.dumps(
        {"scenes": [{"sceneNumber": i, "narration": f"나레이션 {i}",
                     "layout": "cinematic", "imageAsset": {"source": "generate"}}
                    for i in range(1, n + 1)]}, ensure_ascii=False), encoding="utf-8")


def _count(d):
    return len(json.loads((d / "scene_specs.json").read_text(encoding="utf-8"))["scenes"])


def test_empty_adobe_never_wipes_manuscript(tmp_path):
    """어도비가 0씬이면 원고를 건드리지 않는다 — 빈 것과 지워진 것은 다르다."""
    d = _proj(tmp_path, [])
    _specs(d, 142)
    assert scenes.mirror_structure(d, {"scenes": []}) is False
    assert _count(d) == 142


def test_real_structure_change_still_mirrors(tmp_path):
    """가드가 정상 동작까지 막지는 않는다 — 실제로 지운 씬은 반영된다."""
    d = _proj(tmp_path, [])
    _specs(d, 3)
    ok = scenes.mirror_structure(d, {"scenes": [
        {"sceneNumber": 1, "_specs_num": 1, "narration": "나레이션 1"},
        {"sceneNumber": 2, "_specs_num": 3, "narration": "나레이션 3"}]})
    assert ok is True
    rows = json.loads((d / "scene_specs.json").read_text(encoding="utf-8"))["scenes"]
    assert [s["narration"] for s in rows] == ["나레이션 1", "나레이션 3"]
    assert rows[1]["layout"] == "cinematic"      # v3 전용 필드는 살아 있다


def test_big_shrink_leaves_a_backup(tmp_path):
    """반 넘게 줄면 덮어쓰기 전에 한 벌 남긴다 — 0씬 가드는 공백만 막는다."""
    d = _proj(tmp_path, [])
    _specs(d, 142)
    scenes.mirror_structure(d, {"scenes": [{"sceneNumber": 1, "_specs_num": 1}]})
    assert _count(d) == 1
    bak = d / "scene_specs.bak_142scenes.json"
    assert bak.is_file()
    assert len(json.loads(bak.read_text(encoding="utf-8"))["scenes"]) == 142
