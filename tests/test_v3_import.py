import json
from pathlib import Path
from backend import v3_import


def _mk_v3(tmp_path, scenes, manuscript="원고 본문"):
    v3 = tmp_path / "uuid1234_slug"; v3.mkdir()
    (v3 / "scene_specs.json").write_text(json.dumps({"scenes": scenes}, ensure_ascii=False), encoding="utf-8")
    (v3 / "final_manuscript.md").write_text(manuscript, encoding="utf-8")
    return v3


def test_import_v3_flat_schema(tmp_path):
    root = tmp_path / "projects"; root.mkdir()
    v3 = _mk_v3(tmp_path, [{
        "sceneNumber": 1, "title": "기원", "narration": "내레이션",
        "narration_tts": "발음 교정본", "durationFrames": 150,
        "headline": "헤드라인", "imageAsset": {"source": "generate", "prompt": "전기차 작업실"}}])
    res = v3_import.import_v3(root, v3)
    pid = res["project_id"]
    d = root / pid
    sc = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["narration"] == "내레이션" and sc["narration_tts"] == "발음 교정본"
    assert sc["image_prompt"] == "전기차 작업실"
    assert sc["duration_estimate_sec"] == 5.0          # 150/30
    assert sc["sceneId"]                               # ensure_scene_ids 적용
    assert (d / "final_manuscript.md").read_text(encoding="utf-8") == "원고 본문"
    assert res["scenes"] == 1


def test_import_v3_nested_creative(tmp_path):
    root = tmp_path / "projects"; root.mkdir()
    v3 = _mk_v3(tmp_path, [{
        "sceneNumber": 1, "title": "t", "narration": "n",
        "visualization": {"creative": {"concept": "콘셉트 요약"}},
        "imageAsset": {"source": "search", "query": "tesla factory"}}])
    res = v3_import.import_v3(root, v3)
    sc = json.loads((root / res["project_id"] / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["visual_summary"] == "콘셉트 요약"
    assert sc["image_prompt"] == "tesla factory"        # search query도 프롬프트로


def test_import_v3_missing_specs(tmp_path):
    root = tmp_path / "projects"; root.mkdir()
    empty = tmp_path / "none"; empty.mkdir()
    res = v3_import.import_v3(root, empty)
    assert "error" in res


def test_import_v3_reuses_images(tmp_path):
    root = tmp_path / "projects"; root.mkdir()
    v3 = _mk_v3(tmp_path, [{"sceneNumber": 1, "title": "t", "narration": "n"}])
    img_dir = v3 / "images"; img_dir.mkdir()
    # 최소 유효 PNG 생성
    import struct, zlib
    raw = b"\x00\xff\x00\x00"
    png = (b"\x89PNG\r\n\x1a\n"
           + struct.pack(">I", 13) + b"IHDR" + struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    import binascii
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    chunks = b"\x89PNG\r\n\x1a\n"
    for tag, payload in ((b"IHDR", ihdr), (b"IDAT", zlib.compress(raw)), (b"IEND", b"")):
        chunks += struct.pack(">I", len(payload)) + tag + payload
        chunks += struct.pack(">I", binascii.crc32(tag + payload) & 0xFFFFFFFF)
    (img_dir / "scene_001.png").write_bytes(chunks)
    res = v3_import.import_v3(root, v3)
    assert res["images"] == 1
    d = root / res["project_id"]
    sc = json.loads((d / "scenes.json").read_text(encoding="utf-8"))["scenes"][0]
    assert sc["imageRef"].startswith("storyboard/sb_")
    assert (d / sc["imageRef"]).is_file()


def test_map_scene_ports_layout_from_creative():
    """v3 신형: creative.layout에 레이아웃 이름이 있다."""
    out = v3_import._map_scene({
        "sceneNumber": 1, "narration": "말",
        "visualization": {"title": "제목", "items": ["가", "나"], "values": [1, 2],
                          "creative": {"concept": "개념", "layout": "headline_only",
                                       "headline": "헤드라인"}}})
    assert out["layout"] == "headline_only"
    assert out["headline"] == "제목"
    assert out["items"] == ["가", "나"] and out["values"] == [1, 2]


def test_map_scene_prefers_viztype_over_creative_layout():
    """v3 구형 매니페스트는 vizType을 갖는다 — 있으면 그것이 우선."""
    out = v3_import._map_scene({
        "sceneNumber": 1,
        "visualization": {"vizType": "slide_ranking", "title": "t",
                          "creative": {"layout": "headline_only"}}})
    assert out["layout"] == "slide_ranking"


def test_map_scene_ports_all_v3_data_fields():
    out = v3_import._map_scene({
        "sceneNumber": 1,
        "visualization": {"title": "t", "items": ["a"], "values": [1],
                          "descriptions": ["d"], "unit": "%", "source": "출처",
                          "left": {"title": "L"}, "right": {"title": "R"},
                          "relations": ["a>b"], "profileName": "이름",
                          "profileSubtitle": "직함", "vizType": "compare"}})
    for k in ("descriptions", "unit", "source", "left", "right",
              "relations", "profileName", "profileSubtitle"):
        assert k in out, k


def test_map_scene_falls_back_to_chart_unit(tmp_path=None):
    """v3 차트는 unit을 visualization.chart.unit에 둔다 — viz-level unit이 없으면 거기서 가져온다(회귀: 발견6)."""
    out = v3_import._map_scene({
        "sceneNumber": 1,
        "visualization": {"title": "t", "vizType": "bar_chart",
                          "chart": {"labels": ["a"], "values": [40], "unit": "%"}}})
    assert out["unit"] == "%"


def test_map_scene_prefers_viz_level_unit_over_chart(tmp_path=None):
    out = v3_import._map_scene({
        "sceneNumber": 1,
        "visualization": {"title": "t", "unit": "명",
                          "chart": {"labels": ["a"], "values": [1], "unit": "%"}}})
    assert out["unit"] == "명"


def test_map_scene_map_scene_becomes_map_layout():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"center": [1, 2]}})
    assert out["layout"] == "map"


def test_map_scene_without_visualization_is_unchanged():
    """레이아웃 정보가 없으면 layout 키를 만들지 않는다(이미지 씬)."""
    out = v3_import._map_scene({"sceneNumber": 1, "narration": "말", "title": "제목"})
    assert "layout" not in out
    assert out["narration"] == "말"


# --- 지도 씬 임포트 ---
# 실제 v3 데이터(이란 공습 씬)의 값으로 고정한다.
MAP_SCENE = {
    "mapType": "location_reveal",
    "mapStyle": "dark_cyber",
    "title": "동시 타격",
    "source": "최소 9개 도시",
    "camera": {
        "easing": "easeOut",
        "keyframes": [
            {"frame": 0, "center": [53, 30], "zoom": 3.5, "bearing": 0, "pitch": 0},
            {"frame": 45, "center": [53, 32], "zoom": 5.0, "bearing": 0, "pitch": 0},
        ],
    },
    "markers": [
        {"coordinates": [51.39, 35.69], "label": "테헤란", "style": "pulse", "appearAtFrame": 15},
        {"coordinates": [51.68, 32.65], "label": "이스파한", "style": "pulse", "appearAtFrame": 25},
    ],
}


def test_lonlat_swapped_to_latlon():
    """v3는 [경도, 위도], 어도비는 [위도, 경도] — 안 뒤집으면 조용히 엉뚱한 곳이 렌더된다."""
    assert v3_import._lonlat_to_latlon([51.39, 35.69]) == [35.69, 51.39]
    assert v3_import._lonlat_to_latlon([53, 30]) == [30, 53]
    for bad in ([1], [1, 2, 3], ["a", 2], None, "51,35", [None, 1], {}):
        assert v3_import._lonlat_to_latlon(bad) is None, bad


def test_map_center_and_zoom_come_from_first_keyframe():
    """첫 키프레임이 가장 넓어 마커가 다 들어온다. 어도비가 slow_zoom_in을 걸어 밀어들어감이 재현된다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": MAP_SCENE})
    assert out["map_center"] == [30, 53]        # [53, 30] 뒤집힘
    assert out["map_zoom"] == 3.5               # 둘째 키프레임의 5.0이 아니다


def test_markers_translated_with_labels():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": MAP_SCENE})
    assert out["map_markers"] == [
        {"coord": [35.69, 51.39], "name": "테헤란"},
        {"coord": [32.65, 51.68], "name": "이스파한"},
    ]


def test_map_title_and_source_go_to_layout_fields():
    """씬의 title(시트에 보이는 이름)은 건드리지 않는다."""
    out = v3_import._map_scene({"sceneNumber": 1, "title": "씬 이름", "mapScene": MAP_SCENE})
    assert out["headline"] == "동시 타격"
    assert out["source"] == "최소 9개 도시"
    assert out["title"] == "씬 이름"
    assert out["layout"] == "map"


def test_original_mapscene_preserved_for_later():
    """대응 없는 정보(mapStyle·mapType·bearing·appearAtFrame 등)를 다시 임포트하지 않아도 되게."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": MAP_SCENE})
    assert out["map_v3"] == MAP_SCENE
    assert "mapScene" not in out                # 옛 키 이름은 쓰지 않는다


def test_missing_camera_leaves_center_absent():
    """좌표를 만들어내는 것보다 없는 편이 낫다 — 없으면 패널 기본값으로 가고 사람이 알아챈다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"markers": []}})
    assert out["layout"] == "map"
    assert "map_center" not in out and "map_zoom" not in out


def test_bad_center_or_zoom_are_skipped_individually():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "camera": {"keyframes": [{"center": ["a", "b"], "zoom": "가까이"}]}}})
    assert "map_center" not in out and "map_zoom" not in out
    ok_zoom = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "camera": {"keyframes": [{"center": [1], "zoom": 4}]}}})
    assert "map_center" not in ok_zoom and ok_zoom["map_zoom"] == 4


def test_broken_marker_skipped_not_whole_scene():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"markers": [
        {"coordinates": [51.39, 35.69], "label": "테헤란"},
        {"coordinates": "이상함", "label": "깨짐"},
        {"coordinates": [51.68, 32.65], "label": "이스파한"},
    ]}})
    assert [m["name"] for m in out["map_markers"]] == ["테헤란", "이스파한"]


def test_route_translated_when_present():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "route": [[53, 30], [51.39, 35.69], ["나쁨", 1]]}})
    assert out["map_route"] == [[30, 53], [35.69, 51.39]]


def test_non_map_scene_gets_no_map_fields():
    out = v3_import._map_scene({"sceneNumber": 1, "narration": "말",
                                "visualization": {"creative": {"layout": "headline_only"}}})
    assert not [k for k in out if k.startswith("map_")]


def test_markers_from_lat_lng_shape_not_swapped():
    """scene_specs.json의 실제 형태 — 이미 위도·경도 이름이 붙어 있어 뒤집으면 안 된다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"markers": [
        {"label": "알레포", "lat": 36.20, "lng": 37.13},
        {"label": "키이우", "lat": 50.45, "lng": 30.52}]}})
    assert out["map_markers"] == [
        {"coord": [36.20, 37.13], "name": "알레포"},
        {"coord": [50.45, 30.52], "name": "키이우"}]


def test_flat_center_without_camera():
    """지도 씬 다수가 camera 없이 평평한 center/zoom만 갖는다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"center": [120.0, 35.0], "zoom": 3}})
    assert out["map_center"] == [35.0, 120.0]      # 경도 먼저 → 뒤집힘
    assert out["map_zoom"] == 3


def test_flat_center_already_latitude_first_is_not_swapped():
    """[35.18, 128.1076]은 진주 — 둘째 값이 90을 넘으므로 위도가 앞이다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "mode": "locate", "center": [35.18, 128.1076], "zoom": 9}})
    assert out["map_center"] == [35.18, 128.1076]


def test_route_at_pairs_are_latitude_first():
    """at은 이미 위도 먼저 — 뒤집으면 경로가 인도양으로 간다."""
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"route": [
        {"label": "진주", "at": [35.18, 128.1076]},
        {"label": "서울", "at": [37.5665, 126.978]}]}})
    assert out["map_route"] == [[35.18, 128.1076], [37.5665, 126.978]]


def test_route_empty_object_yields_nothing():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {"route": {}}})
    assert "map_route" not in out


def test_keyframe_center_still_preferred_over_flat():
    out = v3_import._map_scene({"sceneNumber": 1, "mapScene": {
        "center": [1, 2], "zoom": 9,
        "camera": {"keyframes": [{"center": [53, 30], "zoom": 3.5}]}}})
    assert out["map_center"] == [30, 53] and out["map_zoom"] == 3.5


def test_real_v3_corpus_map_scene_produces_markers():
    """손으로 쓴 픽스처가 실제 스키마와 어긋나 있던 것이 이 작업의 근본 원인이었다."""
    import glob, json as _j
    import pytest as _p
    files = sorted(glob.glob(str(Path.home() / "LocalProjects" / "auto_kairos_v3"
                                 / "output" / "*" / "scene_specs.json")))
    scenes = []
    for f in files:
        try:
            scenes += [s for s in _j.loads(Path(f).read_text(encoding="utf-8")).get("scenes", [])
                       if s.get("mapScene")]
        except Exception:
            continue
    if not scenes:
        _p.skip("v3 코퍼스 없음")
    outs = [v3_import._map_scene(s) for s in scenes]
    assert any(o.get("map_markers") for o in outs), "실제 코퍼스에서 마커가 하나도 안 나온다"
    assert any(o.get("map_center") for o in outs), "실제 코퍼스에서 중심 좌표가 하나도 안 나온다"
