import json
from pathlib import Path

import pytest

from backend import manifest


def _proj(tmp_path, scenes_arr):
    d = tmp_path / "p"; d.mkdir()
    (d / "scenes.json").write_text(json.dumps({"scenes": scenes_arr}, ensure_ascii=False), encoding="utf-8")
    return d


def test_build_manifest_image_only(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "narration": "내레이션",
                          "imageRef": "storyboard/sb_a.png", "duration_estimate_sec": 4}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    res = manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    assert res["scenes"] == 1 and Path(res["path"]).name == "manifest.json"
    sc = mf["scenes"][0]
    assert sc["image"].endswith("storyboard/sb_a.png") and Path(sc["image"]).is_absolute()
    assert sc["subtitle"] == "내레이션" and sc["duration"] == 4
    assert sc["layers"] == [] and sc["audio"] is None


def test_build_manifest_layers_bg_first(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "b", "imageRef": "storyboard/sb_b.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_b.png").write_bytes(b"\x89PNG")
    lay = d / "layers"; lay.mkdir()
    (lay / "b__0_car.png").write_bytes(b"\x89PNG")
    (lay / "b__1_kid.png").write_bytes(b"\x89PNG")
    (lay / "b__bg.png").write_bytes(b"\x89PNG")
    sc = manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    names = [Path(l["path"]).name for l in mf["layers"]]
    assert names[0] == "b__bg.png"                  # 배경이 배열 맨 앞(=AE 최하단)
    assert mf["layers"][0]["kind"] == "bg"
    assert set(names[1:]) == {"b__0_car.png", "b__1_kid.png"}


def test_build_manifest_audio_duration(tmp_path, monkeypatch):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "c", "narration": "n"}])
    (d / "audio").mkdir(); (d / "audio" / "tts_c.wav").write_bytes(b"x")
    monkeypatch.setattr(manifest.timeline._tts, "audio_duration", lambda p: 5.5)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8")) if manifest.build_manifest(d) else {}
    sc = mf["scenes"][0]
    assert sc["audio"].endswith("audio/tts_c.wav") and sc["duration"] == 5.5


def test_build_manifest_duration_fallback(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "e"}])     # 오디오·duration 없음
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["duration"] == manifest.DEFAULT_DUR   # timeline과 같은 기본값


def test_build_manifest_only_scene(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a"},
                         {"sceneNumber": 2, "sceneId": "b"},
                         {"sceneNumber": 3, "sceneId": "c"}])
    res = manifest.build_manifest(d, only_scene=2)
    assert res["scenes"] == 1 and Path(res["path"]).name == "manifest_scene_2.json"
    mf = json.loads(Path(res["path"]).read_text(encoding="utf-8"))
    assert len(mf["scenes"]) == 1 and "_b" in mf["scenes"][0]["ae_comp_name"]
    # 전체 manifest.json은 건드리지 않음
    assert not (d / "manifest.json").exists()


def test_manifest_merges_motion(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "mo", "imageRef": "storyboard/sb.png"}])
    (d / "storyboard").mkdir()
    from PIL import Image
    Image.new("RGB", (100, 100)).save(d / "storyboard" / "sb.png")
    lay = d / "layers"; lay.mkdir()
    Image.new("RGBA", (100, 100)).save(lay / "mo__0_차.png")
    Image.new("RGBA", (100, 100)).save(lay / "mo__bg.png")
    (d / "motion_mo.json").write_text(json.dumps({
        "layers": [{"layer": "mo__0_차", "moves": [
            {"type": "pop", "start": 0.2, "duration": 0.6}]}],
        "camera": {"type": "pan_left", "amount": 40}}), encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    car = next(L for L in sc["layers"] if "차" in L["name"])
    assert car["moves"][0]["type"] == "pop"
    bg = next(L for L in sc["layers"] if L["kind"] == "bg")
    assert "moves" not in bg
    # 카메라는 널 키프레임 배열로 구워진다 — pan_left 40px = 널 x가 +20에서 -20으로
    cam = sc["camera"]
    assert isinstance(cam, list) and len(cam) == 2
    assert cam[0]["position"] == [980.0, 540.0]
    assert cam[1]["position"] == [940.0, 540.0]
    assert cam[1]["ease"] == "70:30"


def test_manifest_no_motion_file_ok(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "nm"}])
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert "camera" not in sc                          # 모션 없으면 필드 자체 없음(하위호환)


def test_manifest_element_foot_point(tmp_path):
    """요소 레이어의 foot = 불투명 영역 하단 중앙(까딱 피벗) — 컴프 공간으로 굽는다."""
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ft", "imageRef": "storyboard/sb.png"}])
    (d / "storyboard").mkdir(); Image.new("RGB", (200, 200)).save(d / "storyboard" / "sb.png")
    lay = d / "layers"; lay.mkdir()
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for y in range(40, 160):                              # 인물: x 60~120, y 40~160
        for x in range(60, 120):
            im.putpixel((x, y), (200, 30, 40, 255))
    im.save(lay / "ft__0_인물.png")
    Image.new("RGBA", (200, 200), (10, 10, 10, 255)).save(lay / "ft__bg.png")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    el = next(L for L in sc["layers"] if L["kind"] == "element")
    f = 1080 / 200
    ox = (1920 - 200 * f) / 2
    assert el["foot"] == pytest.approx([90.0 * f + ox, 160.0 * f])   # bbox(60,40,120,160) 하단 중앙, 컴프 좌표
    bg = next(L for L in sc["layers"] if L["kind"] == "bg")
    assert "foot" not in bg


def test_char_layer_auto_bob_without_plan(tmp_path):
    """_char 접미사(또는 kinds=character) 레이어는 모션 플랜 없이도 결정적 bob 부여."""
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "imageRef": "storyboard/sb.png",
                          "duration_estimate_sec": 5}])
    (d / "storyboard").mkdir(); Image.new("RGB", (200, 200)).save(d / "storyboard" / "sb.png")
    lay = d / "layers"; lay.mkdir()
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for y in range(50, 150):
        for x in range(80, 120):
            im.putpixel((x, y), (200, 30, 40, 255))
    im.save(lay / "ab__0_남자_char.png")                  # _char 접미사
    im.save(lay / "ab__1_책상.png")                       # 사물
    Image.new("RGBA", (200, 200), (9, 9, 9, 255)).save(lay / "ab__bg.png")
    manifest.build_manifest(d)                            # 모션 플랜 파일 없음
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    char = next(L for L in sc["layers"] if "_char" in L["name"])
    # 까딱임 값은 매니페스트가 실어 보낸다 — jsx 가 숫자를 적지 않는다.
    from backend import motion
    assert char["moves"] == [motion.bob_move(0, 5.0)]
    assert char["moves"][0]["half_frames"] == 10      # 반주기 10프레임
    assert char["moves"][0]["amount"] == 1            # 100 → 101
    desk = next(L for L in sc["layers"] if "책상" in L["name"])
    assert "moves" not in desk                            # 사물은 모션 없음


def test_char_auto_bob_not_duplicated_with_plan(tmp_path):
    """플랜에 이미 모션 있으면 자동 bob 중복 부여 안 함."""
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "nb", "imageRef": "storyboard/sb.png"}])
    (d / "storyboard").mkdir(); Image.new("RGB", (100, 100)).save(d / "storyboard" / "sb.png")
    lay = d / "layers"; lay.mkdir()
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    im.putpixel((50, 50), (255, 0, 0, 255))
    im.save(lay / "nb__0_여자_char.png")
    (d / "motion_nb.json").write_text(json.dumps({
        "layers": [{"layer": "nb__0_여자_char", "moves": [
            {"type": "fade_in", "start": 0, "duration": 1},
            {"type": "bob", "start": 1, "duration": 2}]}],
        "camera": {"type": "none"}}), encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    char = next(L for L in sc["layers"] if "_char" in L["name"])
    # 캐릭터는 오퍼시티 금지 — fade_in 제거되고 bob만(중복 부여 없음), noFade 플래그
    assert [m["type"] for m in char["moves"]] == ["bob"]
    assert all(m.get("noFade") for m in char["moves"])


def test_manifest_layout_passthrough(tmp_path):
    """layout+데이터 통과, 비이미지 레이아웃 씬은 1920x1080 기본 컴프 + image None."""
    d = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "h", "narration": "n1", "layout": "headline_only",
         "headline": "큰 제목", "sub": "부제", "duration_estimate_sec": 4},
        {"sceneNumber": 2, "sceneId": "b", "narration": "n2", "layout": "bar",
         "headline": "비교", "chart": {"labels": ["A", "B"], "values": [10, 40], "unit": "%"}},
    ])
    manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    s1, s2 = mf["scenes"]
    assert s1["layout"] == "headline_only" and s1["title"] == "큰 제목" and s1["descriptions"] == ["부제"]
    assert s1["image"] is None and s1["layers"] == []
    assert s1["width"] == 1920 and s1["height"] == 1080
    assert s2["layout"] == "bar" and s2["values"] == [10, 40]
    assert s2["unit"] == "%"          # chart.unit → 최상위 unit으로 정규화(막대 값 단위 유지)
    assert "value" not in s2 and "quote_text" not in s2     # None 필드는 미포함
    assert Path(mf["ae_tokens"]).name == "ae_tokens.json" and Path(mf["ae_tokens"]).is_absolute()


def test_manifest_layout_defaults_cinematic(tmp_path):
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "imageRef": "storyboard/sb_a.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_a.png").write_bytes(b"\x89PNG")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "cinematic"
    assert sc["image"].endswith("sb_a.png")


def test_layout_scene_keeps_image_but_not_layers(tmp_path):
    """v3 임포트 씬처럼 layout과 _image가 함께 있으면 image는 유지, layers만 억제한다(회귀: 발견1)."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "lv", "narration": "n",
                          "layout": "headline_only", "headline": "제목", "imageRef": "storyboard/sb_lv.png"}])
    (d / "storyboard").mkdir(); (d / "storyboard" / "sb_lv.png").write_bytes(b"\x89PNG")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "headline_only"
    assert sc["image"] is not None and sc["image"].endswith("sb_lv.png")
    assert sc["layers"] == []


def test_map_scene_becomes_image_scene_with_default_camera(tmp_path):
    """지도 씬 — 이미지 링크되면 cinematic 취급 + 기본 slow_zoom_in 카메라."""
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "mp", "layout": "map",
                          "narration": "지도", "imageRef": "storyboard/map_mp_abc.png",
                          "map_center": [37.5, 127.0]}])
    (d / "storyboard").mkdir()
    Image.new("RGB", (1920, 1080)).save(d / "storyboard" / "map_mp_abc.png")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "cinematic" and sc["image"]
    cam = sc["camera"]
    assert isinstance(cam, list) and len(cam) == 2
    assert cam[0]["scale"] == 100.0
    assert cam[1]["scale"] == 106.0        # 기본 slow_zoom_in 6%
    assert cam[1]["ease"] == "70:30"


def test_map_scene_without_image_stays_layout(tmp_path):
    """지도 씬 — 이미지 미생성 시 layout=map 유지(빈 컴프, 카메라 없음)."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "mp", "layout": "map", "narration": "지도"}])
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "map" and sc["image"] is None


def test_map_geo_sidecar_passthrough(tmp_path):
    """지도 geo 사이드카({이미지}.geo.json) → manifest mapGeo로 전달."""
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "mg", "layout": "map",
                          "narration": "경로", "imageRef": "storyboard/map_mg_x1.png"}])
    sb = d / "storyboard"; sb.mkdir()
    Image.new("RGB", (1920, 1080)).save(sb / "map_mg_x1.png")
    geo = {"markers": [{"name": "서울", "x": 960, "y": 540}],
           "route": [[100, 200], [960, 540]], "labelRgb": [26, 26, 26]}
    (sb / "map_mg_x1.png.geo.json").write_text(json.dumps(geo), encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["mapGeo"]["markers"][0]["name"] == "서울"
    assert sc["mapGeo"]["route"] == [[100, 200], [960, 540]]


def test_chart_spec_sidecar_passthrough(tmp_path):
    """차트 명세서 사이드카(chart_{sid}.spec.json) → manifest chartSpec(bar 씬만)."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "cc", "layout": "bar", "narration": "x",
                          "headline": "수면 단계", "chart": {"labels": ["a", "b"], "values": [1, 2], "unit": "분"}}])
    (d / "chart_cc.spec.json").write_text(json.dumps({
        "theme_set": "gallery_infographic", "guideLineCount": 3,
        "patternKind": "diagonal_hatch", "outlineWidth": 2.45}), encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["chartSpec"]["guideLineCount"] == 3
    assert sc["chartSpec"]["patternKind"] == "diagonal_hatch"


def test_manifest_injects_theme_colors(tmp_path, monkeypatch):
    """manifest — resolve된 테마 색을 themeColors로 주입(jsx가 ae_tokens 위에 오버라이드)."""
    from backend import themes
    td = tmp_path / "cat"; td.mkdir()
    (td / "dark_broadcast.json").write_text(json.dumps({"id": "dark_broadcast", "label": "다크방송",
        "colors": {"accentRgb": [255, 80, 80]}, "chart": {"theme_set": "broadcast_signal"},
        "map": {"tile": "dark", "overrides": []}}), encoding="utf-8")
    monkeypatch.setattr(themes, "_catalog_dir", lambda: td)
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "headline_only",
                          "headline": "x", "narration": "n"}])
    data = json.loads((d / "scenes.json").read_text()); data["theme"] = "dark_broadcast"
    (d / "scenes.json").write_text(json.dumps(data), encoding="utf-8")
    manifest.build_manifest(d)
    mf = json.loads((d / "manifest.json").read_text())
    assert mf["themeColors"]["accentRgb"] == [255, 80, 80]


def test_scene_manifest_no_skip_final(tmp_path):
    """평면 구조에서는 Final이 유일한 컴프 — 씬별 manifest(only_scene)도 skipFinal을 내지 않는다."""
    d = _proj(tmp_path, [
        {"sceneNumber": 1, "sceneId": "a", "layout": "headline_only", "headline": "x", "narration": "n"},
        {"sceneNumber": 2, "sceneId": "b", "layout": "headline_only", "headline": "y", "narration": "m"}])
    manifest.build_manifest(d, only_scene=1)
    m1 = json.loads((d / "manifest_scene_1.json").read_text())
    assert "skipFinal" not in m1 and len(m1["scenes"]) == 1
    manifest.build_manifest(d)
    m2 = json.loads((d / "manifest.json").read_text())
    assert "skipFinal" not in m2 and len(m2["scenes"]) == 2


def test_build_manifest_only_scenes_subset(tmp_path):
    """체크한 씬 여러 개를 한 번에 — 전체를 돌지 않는다."""
    import json as _j
    from backend import manifest as _m
    (tmp_path / "scenes.json").write_text(_j.dumps({"scenes": [
        {"sceneNumber": i, "sceneId": f"s{i}", "narration": f"씬 {i}"} for i in range(1, 8)
    ]}, ensure_ascii=False), encoding="utf-8")
    res = _m.build_manifest(tmp_path, only_scenes=[2, 4, 6])
    assert res["scenes"] == 3
    assert res["path"].endswith("manifest_subset.json")
    mf = _j.loads(Path(res["path"]).read_text(encoding="utf-8"))
    assert [s["ae_comp_name"] for s in mf["scenes"]] == ["S02_s2", "S04_s4", "S06_s6"]
    assert "skipFinal" not in mf            # 평면 구조 — Final이 유일한 컴프, 부분 빌드도 그대로 들어감
    # 전체 빌드는 그대로
    assert _m.build_manifest(tmp_path)["scenes"] == 7


def test_build_manifest_subtitle_uses_subtitle_text(tmp_path):
    import json as _j
    from backend import manifest as _m
    (tmp_path / "scenes.json").write_text(_j.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": "a", "narration": "1970년대",
         "narration_tts": "천구백칠십 년대"}]}, ensure_ascii=False), encoding="utf-8")
    mf = _j.loads(Path(_m.build_manifest(tmp_path)["path"]).read_text(encoding="utf-8"))
    assert mf["scenes"][0]["subtitle"] == "1970년대"


def test_manifest_normalizes_layout_data(tmp_path):
    """jsx는 정규 이름만 알면 되게 — 별칭은 백엔드에서 정리해 넘긴다."""
    import json as _j
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "headline_only",
                          "headline": "제목", "sub": "부제"}])
    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    sc = mf["scenes"][0]
    assert sc["title"] == "제목"
    assert sc["descriptions"] == ["부제"]
    assert sc["layout"] == "headline_only"


def test_manifest_resolves_unknown_layout_to_generic(tmp_path):
    """모르는 v3 이름이 와도 cinematic으로 떨어뜨리지 않는다."""
    import json as _j
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "slide_qna",
                          "headline": "질문", "items": ["가", "나"]}])
    sc = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "generic"
    assert sc["title"] == "질문" and sc["items"] == ["가", "나"]


def test_manifest_aliases_v3_layout(tmp_path):
    import json as _j
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "a", "layout": "slide_list",
                          "headline": "제목", "items": ["가"]}])
    sc = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] == "items_list"


def test_build_manifest_fractional_scene_number(tmp_path):
    """삽입 씬(25.25)에서 컴프 이름 포맷이 터지지 않고, 부분 빌드 선택도 정확해야 한다."""
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 25, "sceneId": "a"},
                         {"sceneNumber": 25.25, "sceneId": "b"},
                         {"sceneNumber": 26, "sceneId": "c"}])
    mf = json.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    assert [s["ae_comp_name"] for s in mf["scenes"]] == ["S25_a", "S25-25_b", "S26_c"]
    sub = json.loads(Path(_m.build_manifest(d, only_scenes=[25.25])["path"]).read_text(encoding="utf-8"))
    assert [s["ae_comp_name"] for s in sub["scenes"]] == ["S25-25_b"]   # 25번이 섞이지 않음


def test_layer_placement_from_bbox(tmp_path):
    """layerize 레이어는 크롭돼 오므로 bbox로 위치·크기를 되살린다(실측값 고정)."""
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "narration": "n",
                          "imageRef": "storyboard/sb_ab.png"}])
    (d / "storyboard").mkdir()
    Image.new("RGB", (1536, 1024)).save(d / "storyboard" / "sb_ab.png")   # 컴프 폭 = 배경판 폭(스케일 없음)
    lay = d / "layers"; lay.mkdir()
    Image.new("RGBA", (1052, 477)).save(lay / "ab__0_car.png")      # 실측 PNG 크기
    Image.new("RGB", (1536, 1024)).save(lay / "ab__bg.png")
    (lay / "ab__elements.json").write_text(_j.dumps([
        {"layer": "ab__0_car", "index": 0, "name": "차량", "name_en": "car",
         "kind": "object", "bbox": [344, 500, 1254, 912], "z": 3}]), encoding="utf-8")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    car = [L for L in mf["scenes"][0]["layers"] if "car" in L["name"]][0]
    f = 1080 / 1024
    ox = (1920 - 1536 * f) / 2
    assert car["position"] == pytest.approx([799.0 * f + ox, 706.0 * f])   # bbox 중심, 컴프 좌표
    assert round(car["scale"], 1) == round(86.5 * f, 1)   # (1254-344)/1052*100 × f
    assert car["foot"] == pytest.approx([799.0 * f + ox, 912.0 * f])       # bbox 하단 중앙, 컴프 좌표


def test_layers_ordered_by_z(tmp_path):
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    for nm in ("ab__bg.png", "ab__0_front.png", "ab__1_back.png"):
        Image.new("RGBA", (100, 100)).save(lay / nm)
    (lay / "ab__elements.json").write_text(_j.dumps([
        {"layer": "ab__0_front", "index": 0, "name": "앞", "kind": "object",
         "bbox": [0, 0, 50, 50], "z": 5},
        {"layer": "ab__1_back", "index": 1, "name": "뒤", "kind": "object",
         "bbox": [0, 0, 50, 50], "z": 2}]), encoding="utf-8")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    names = [L["name"] for L in mf["scenes"][0]["layers"]]
    assert names[0] == "ab__bg"                     # 배경이 항상 맨 앞(AE 최하단)
    assert names.index("ab__1_back") < names.index("ab__0_front")   # z 오름차순


def test_layer_bbox_scaled_when_plate_smaller_than_comp(tmp_path):
    """발견2 — 배경판 PNG 폭이 씬 이미지(컴프) 폭과 다르면 bbox를 comp_width/plate_width로 보정한다."""
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "sc", "narration": "n",
                          "imageRef": "storyboard/sb_sc.png"}])
    (d / "storyboard").mkdir()
    Image.new("RGB", (2000, 1000)).save(d / "storyboard" / "sb_sc.png")   # 컴프 폭 2000
    lay = d / "layers"; lay.mkdir()
    Image.new("RGBA", (200, 100)).save(lay / "sc__0_car.png")
    Image.new("RGB", (1000, 500)).save(lay / "sc__bg.png")                # 배경판 폭 1000 = 컴프의 절반
    (lay / "sc__elements.json").write_text(_j.dumps([
        {"layer": "sc__0_car", "index": 0, "name": "차량", "name_en": "car",
         "kind": "object", "bbox": [100, 100, 300, 300], "z": 1}]), encoding="utf-8")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    car = [L for L in mf["scenes"][0]["layers"] if "car" in L["name"]][0]
    # factor = 2000/1000 = 2 → bbox [100,100,300,300] * 2 = [200,200,600,600] (씬 이미지 좌표)
    # 그 다음 컴프 좌표로 굽는다: f, ox는 씬 이미지(2000x1000) 기준
    f = 1080 / 1000
    ox = (1920 - 2000 * f) / 2
    assert car["position"] == pytest.approx([400.0 * f + ox, 400.0 * f])
    assert car["foot"] == pytest.approx([400.0 * f + ox, 600.0 * f])


def test_bbox_non_numeric_degrades_to_fullframe_placement(tmp_path):
    """발견6 — 비수치 bbox 값은 예외를 던지지 않고 bbox 없는 것처럼(풀프레임 폴백) 처리한다.
    평면 구조에서는 모든 레이어에 position/scale이 반드시 있어야 하므로, 풀프레임 폴백도
    컴프 좌표를 낸다(그러나 foot은 여전히 alpha_foot으로 실제 인물 위치를 보존)."""
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "bx", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    im = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    for y in range(20, 80):
        for x in range(20, 80):
            im.putpixel((x, y), (200, 30, 40, 255))
    im.save(lay / "bx__0_car.png")
    Image.new("RGB", (100, 100), (9, 9, 9)).save(lay / "bx__bg.png")
    (lay / "bx__elements.json").write_text(_j.dumps([
        {"layer": "bx__0_car", "index": 0, "name": "차량", "name_en": "car",
         "kind": "object", "bbox": ["bad", None, "x", "y"], "z": 1}]), encoding="utf-8")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    car = [L for L in mf["scenes"][0]["layers"] if "car" in L["name"]][0]
    # 이미지 참조가 없으므로 씬은 기본 1920x1080(f=1, ox=0) — 풀프레임 폴백은 씬 사각형(전체 캔버스) 기준
    assert car["position"] == pytest.approx([960.0, 540.0])
    assert car["scale"] == pytest.approx(1920.0)   # sw(1920)/pw(100)*100 — car PNG가 캔버스보다 훨씬 작음
    assert car.get("foot") == [50.0, 80.0]   # alpha_foot 폴백으로 피벗은 보존(f=1, ox=0이라 그대로)


def test_legacy_layers_without_bbox_get_fullframe_comp_coords(tmp_path):
    """기존 프로젝트는 풀프레임 PNG라 bbox가 없다 — 평면 구조에서도 좌표는 반드시 실어야
    하므로 씬 사각형(컴프 좌표)을 채우는 position/scale을 낸다."""
    import json as _j
    from PIL import Image
    from backend import manifest as _m
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "narration": "n"}])
    lay = d / "layers"; lay.mkdir()
    Image.new("RGBA", (1920, 1080)).save(lay / "ab__0_old.png")
    Image.new("RGB", (1920, 1080)).save(lay / "ab__bg.png")

    mf = _j.loads(Path(_m.build_manifest(d)["path"]).read_text(encoding="utf-8"))
    old = [L for L in mf["scenes"][0]["layers"] if "old" in L["name"]][0]
    # 이미지 참조가 없으므로 씬은 기본 1920x1080(f=1, ox=0) — old.png도 1920x1080이라 1:1로 겹침
    assert old["position"] == pytest.approx([960.0, 540.0])
    assert old["scale"] == pytest.approx(100.0)


def test_vector_size_recorded(tmp_path):
    """배율이 무엇을 전제로 계산됐는지 함께 적는다.

    SVG 파일이 나중에 바뀌면(창을 고치거나 다시 벡터화하면) 그 전제가 깨진다.
    매니페스트를 다시 굽지 않으면 아무도 모르는데, 창을 1/10 로 선언하던 시절
    매니페스트로 들여왔더니 쉐이프가 24배로 커지고 자리가 통째로 밀렸다.
    """
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "imageRef": "storyboard/sb.png",
                          "duration_estimate_sec": 5}])
    (d / "storyboard").mkdir(); Image.new("RGB", (200, 200)).save(d / "storyboard" / "sb.png")
    lay = d / "layers"; lay.mkdir()
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for y in range(50, 150):
        for x in range(80, 120):
            im.putpixel((x, y), (200, 30, 40, 255))
    im.save(lay / "ab__0_병.png")
    Image.new("RGBA", (200, 200), (9, 9, 9, 255)).save(lay / "ab__bg.png")
    # 그림 좌표 공간(2048)으로 선언한 SVG — 지금 규격
    (lay / "ab__0_병.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 2048" '
        'width="1024" height="2048"><path d="M0 0L10 10Z"/></svg>', encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    L = next(x for x in sc["layers"] if x["name"] == "ab__0_병")
    assert L["vectorSize"] == [1024.0, 2048.0]
    # 배율은 선언 크기 기준이다 — PNG(200) 가 아니라 SVG(1024)
    assert abs(L["vectorRatio"] - 200 / 1024) < 1e-6


def test_jsx_corrects_when_svg_size_differs():
    """jsx 가 들여온 실제 크기와 대 보고 스스로 맞춘다 — 쉐이프로 펴기 **전에**."""
    from pathlib import Path as _P
    jsx = (_P(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
           / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "layer.vectorSize" in jsx
    assert "layer.scale = layer.scale * corr" in jsx
    # 보정이 explode 보다 앞에 있어야 한다 — 뒤에 있으면 쉐이프가 못 쓴다
    assert jsx.index("layer.vectorSize[0] / realW") < jsx.index("explodeCompLayers(comp, foot")


def test_scene_video_is_carried(tmp_path):
    """영상이 있으면 매니페스트가 싣는다 — 없던 기능이라 99씬이 안 들어왔다."""
    d = _proj(tmp_path, [{"sceneNumber": 99, "sceneId": "ab", "duration_estimate_sec": 5}])
    v = d / "video"; v.mkdir()
    (v / "v_ab_minimax_h3.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["video"].endswith("v_ab_minimax_h3.mp4")


def test_dropped_video_is_carried(tmp_path):
    """끌어다 놓은 영상도 같은 자리에서 쓴다(`video_sources/` + video_assets.json)."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "duration_estimate_sec": 5}])
    vs = d / "video_sources"; vs.mkdir()
    (vs / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (d / "video_assets.json").write_text(json.dumps(
        {"scenes": [{"sceneId": "ab", "sceneNumber": 1, "videoFile": "clip.mp4"}]}),
        encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["video"].endswith("clip.mp4")


def test_generated_video_wins_over_dropped(tmp_path):
    """만든 것이 있으면 그것이 먼저다."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "duration_estimate_sec": 5}])
    (d / "video").mkdir()
    (d / "video" / "v_ab_minimax_h3.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    vs = d / "video_sources"; vs.mkdir()
    (vs / "clip.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42")
    (d / "video_assets.json").write_text(json.dumps(
        {"scenes": [{"sceneId": "ab", "sceneNumber": 1, "videoFile": "clip.mp4"}]}),
        encoding="utf-8")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["video"].endswith("v_ab_minimax_h3.mp4")


def test_no_video_no_key(tmp_path):
    """없으면 키 자체가 없다 — jsx 가 `s.video` 로 판단한다."""
    d = _proj(tmp_path, [{"sceneNumber": 1, "sceneId": "ab", "duration_estimate_sec": 5}])
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert "video" not in sc


def test_layout_scene_keeps_its_layers(tmp_path):
    """레이아웃 씬이어도 나눠 둔 레이어를 싣는다.

    v3 의 flow·items_list·before_after 는 도해만 있는 화면이 아니라 **씬 그림
    위에 항목이 얹히는** 구조다. 그런데 레이아웃 씬이면 레이어를 통째로
    버리고 있었다 — 디아지오편 142씬 중 15씬이 나눠 두고도 못 썼다.
    레이아웃 글자는 조립할 때 맨 위에 그리므로 가려지지 않는다.
    """
    from PIL import Image
    d = _proj(tmp_path, [{"sceneNumber": 128, "sceneId": "ab", "layout": "flow",
                          "imageRef": "storyboard/sb.png", "items": ["가", "나"],
                          "duration_estimate_sec": 5}])
    (d / "storyboard").mkdir(); Image.new("RGB", (200, 200)).save(d / "storyboard" / "sb.png")
    lay = d / "layers"; lay.mkdir()
    im = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for y in range(50, 150):
        for x in range(80, 120):
            im.putpixel((x, y), (200, 30, 40, 255))
    im.save(lay / "ab__0_잔.png")
    Image.new("RGBA", (200, 200), (9, 9, 9, 255)).save(lay / "ab__bg.png")
    manifest.build_manifest(d)
    sc = json.loads((d / "manifest.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["layout"] != "cinematic"        # 레이아웃 씬이다(= 예전엔 버려졌다)
    names = [L["name"] for L in sc["layers"]]
    assert "ab__bg" in names and "ab__0_잔" in names
