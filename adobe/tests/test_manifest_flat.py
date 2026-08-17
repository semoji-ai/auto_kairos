import json
from pathlib import Path

import pytest

from backend import manifest

SID = "abc123"


def test_fit_16by9ish():
    """1792x1024(1.750)를 1920x1080에 세로 기준으로 — 좌우 15px씩 여백."""
    f, ox = manifest.fit_transform(1792, 1024)
    assert f == pytest.approx(1080 / 1024)
    assert ox == pytest.approx((1920 - 1792 * (1080 / 1024)) / 2)
    assert ox == pytest.approx(15.0, abs=0.1)


def test_fit_3by2():
    f, ox = manifest.fit_transform(1536, 1024)
    assert f == pytest.approx(1.0546875)
    assert ox == pytest.approx(150.0, abs=0.1)


def test_fit_exact_16by9():
    f, ox = manifest.fit_transform(1920, 1080)
    assert f == pytest.approx(1.0)
    assert ox == pytest.approx(0.0)


def test_fit_wider_than_16by9_overflows():
    """2.0 비율은 세로 기준이면 좌우로 넘친다 — ox가 음수."""
    f, ox = manifest.fit_transform(1000, 500)
    assert f == pytest.approx(2.16)
    assert ox < 0


def test_fit_never_crops_vertically():
    """어떤 입력이든 세로는 정확히 컴프 높이를 채운다."""
    for sw, sh in [(1792, 1024), (1536, 1024), (900, 600), (480, 641), (1000, 500)]:
        f, _ = manifest.fit_transform(sw, sh)
        assert sh * f == pytest.approx(1080)


def test_fit_bad_size_falls_back():
    assert manifest.fit_transform(0, 0) == (1.0, 0.0)
    assert manifest.fit_transform(100, -5) == (1.0, 0.0)


# ---- 매니페스트 전체 ----

def _project(tmp_path: Path):
    """씬 2개(1792x1024 이미지 + 레이어 2장)를 갖춘 프로젝트."""
    from PIL import Image
    proj = tmp_path / "p1"
    (proj / "storyboard").mkdir(parents=True)
    (proj / "layers").mkdir()
    scenes_json = {"scenes": []}
    for n, sid in ((1, "aaa111"), (2, "bbb222")):
        img = proj / "storyboard" / f"sb_{sid}.png"
        Image.new("RGBA", (1792, 1024), (10, 10, 10, 255)).save(img)
        Image.new("RGBA", (1792, 1024), (20, 20, 20, 255)).save(proj / "layers" / f"{sid}__bg.png")
        Image.new("RGBA", (200, 400), (0, 0, 0, 255)).save(proj / "layers" / f"{sid}__0_kid_char.png")
        specs = [{"layer": f"{sid}__0_kid_char", "index": 0, "name": "노란옷 아이",
                  "name_en": "kid", "location": "", "kind": "character", "intent": "",
                  "z": 1, "bbox": [100, 200, 300, 600]}]
        (proj / "layers" / f"{sid}__elements.json").write_text(
            json.dumps(specs, ensure_ascii=False), encoding="utf-8")
        scenes_json["scenes"].append({
            "sceneNumber": n, "sceneId": sid, "title": f"t{n}", "narration": "n",
            "imageRef": f"storyboard/sb_{sid}.png", "duration_estimate_sec": 4})
    (proj / "scenes.json").write_text(json.dumps(scenes_json, ensure_ascii=False), encoding="utf-8")
    return proj


def _manifest(proj):
    res = manifest.build_manifest(proj)
    return json.loads(Path(res["path"]).read_text(encoding="utf-8"))


def test_scene_has_start_and_prefix(tmp_path):
    mf = _manifest(_project(tmp_path))
    assert mf["scenes"][0]["start"] == pytest.approx(0.0)
    assert mf["scenes"][1]["start"] == pytest.approx(4.0)
    assert mf["scenes"][0]["prefix"] == "S01_"
    assert mf["scenes"][1]["prefix"] == "S02_"


def test_every_layer_has_position_and_scale(tmp_path):
    mf = _manifest(_project(tmp_path))
    for sc in mf["scenes"]:
        assert sc["layers"]
        for L in sc["layers"]:
            assert "position" in L and "scale" in L
            assert isinstance(L["position"], list) and len(L["position"]) == 2


def test_layer_ae_names(tmp_path):
    mf = _manifest(_project(tmp_path))
    names = [L["aeName"] for L in mf["scenes"][0]["layers"]]
    assert names[0] == "S01_배경"                 # 배경이 배열 맨 앞
    assert names[1] == "S01_01_노란옷아이"          # 요소는 z 순번 2자리 + 공백 제거한 한글 이름


def test_element_coords_are_comp_space(tmp_path):
    """bbox [100,200,300,600] × f=1.0547 + ox=15 → 중심 x=(100+300)/2*1.0547+15."""
    mf = _manifest(_project(tmp_path))
    el = mf["scenes"][0]["layers"][1]
    f = 1080 / 1024
    ox = (1920 - 1792 * f) / 2
    assert el["position"][0] == pytest.approx(200 * f + ox)
    assert el["position"][1] == pytest.approx(400 * f)
    assert el["foot"][0] == pytest.approx(200 * f + ox)
    assert el["foot"][1] == pytest.approx(600 * f)
    assert el["scale"] == pytest.approx((300 - 100) / 200 * 100 * f)


def test_background_fills_scene_rect(tmp_path):
    """배경판(풀프레임)은 씬 사각형 중앙에 놓이고 f배로 커진다."""
    mf = _manifest(_project(tmp_path))
    bg = mf["scenes"][0]["layers"][0]
    f = 1080 / 1024
    ox = (1920 - 1792 * f) / 2
    assert bg["position"] == pytest.approx([1792 * f / 2 + ox, 540.0])
    assert bg["scale"] == pytest.approx(f * 100)


def test_bg_fill_flag(tmp_path):
    """좌우 여백이 있으면 bgFill이 참."""
    mf = _manifest(_project(tmp_path))
    assert mf["scenes"][0]["bgFill"] is True


def test_fit_block_present(tmp_path):
    mf = _manifest(_project(tmp_path))
    fit = mf["scenes"][0]["fit"]
    assert fit["w"] == 1792 and fit["h"] == 1024
    assert fit["f"] == pytest.approx(1080 / 1024)
    assert fit["ox"] == pytest.approx(15.0, abs=0.1)


def test_image_fit_present(tmp_path):
    """씬 이미지도 같은 변환 — 레이아웃 씬의 배경 이미지가 이것을 쓴다."""
    mf = _manifest(_project(tmp_path))
    imf = mf["scenes"][0]["imageFit"]
    f = 1080 / 1024
    ox = (1920 - 1792 * f) / 2
    assert imf["position"] == pytest.approx([1792 * f / 2 + ox, 540.0])
    assert imf["scale"] == pytest.approx(f * 100)


def test_no_skip_final_key(tmp_path):
    """평면에서는 Final이 유일한 컴프 — 부분 빌드도 같은 컴프에 넣는다."""
    proj = _project(tmp_path)
    manifest.build_manifest(proj)
    res = manifest.build_manifest(proj, only_scene=2)
    mf = json.loads(Path(res["path"]).read_text(encoding="utf-8"))
    assert "skipFinal" not in mf
    assert len(mf["scenes"]) == 1
    assert mf["scenes"][0]["start"] == pytest.approx(4.0)   # 전체 기준 시작 시각 유지


def test_fractional_scene_prefix(tmp_path):
    """삽입 씬 25.25 → S25-25_ (하이픈 — 밑줄이면 씬 25의 접두사 S25_와 충돌한다)."""
    proj = _project(tmp_path)
    data = json.loads((proj / "scenes.json").read_text(encoding="utf-8"))
    data["scenes"][1]["sceneNumber"] = 25.25
    (proj / "scenes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    mf = _manifest(proj)
    assert mf["scenes"][1]["prefix"] == "S25-25_"


def test_motion_sidecar_stamp_filtered_for_character(tmp_path):
    """옛 모션 사이드카가 캐릭터 레이어에 stamp를 얹혀도 매니페스트가 걸러낸다(2차 방어)."""
    proj = _project(tmp_path)
    sid = "aaa111"
    (proj / f"motion_{sid}.json").write_text(json.dumps({
        "layers": [{"layer": f"{sid}__0_kid_char", "moves": [
            {"type": "stamp", "start": 0, "duration": 0.5},
            {"type": "bob", "start": 0, "duration": 4},
        ]}],
    }, ensure_ascii=False), encoding="utf-8")
    mf = _manifest(proj)
    char = [L for L in mf["scenes"][0]["layers"] if L["name"] == f"{sid}__0_kid_char"][0]
    types = [m["type"] for m in char.get("moves", [])]
    assert "stamp" not in types
    assert "bob" in types


def test_motion_sidecar_bob_filtered_for_object(tmp_path):
    """사물 레이어의 bob은 ALLOWED_BY_KIND에 없다 — 옛 사이드카가 얹혀도 매니페스트가 걸러낸다."""
    from PIL import Image
    proj = _project(tmp_path)
    sid = "aaa111"
    Image.new("RGBA", (100, 100), (0, 0, 0, 255)).save(proj / "layers" / f"{sid}__1_box.png")
    specs = json.loads((proj / "layers" / f"{sid}__elements.json").read_text(encoding="utf-8"))
    specs.append({"layer": f"{sid}__1_box", "index": 1, "name": "상자",
                  "name_en": "box", "location": "", "kind": "object", "intent": "",
                  "z": 2, "bbox": [10, 10, 90, 90]})
    (proj / "layers" / f"{sid}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    (proj / f"motion_{sid}.json").write_text(json.dumps({
        "layers": [{"layer": f"{sid}__1_box", "moves": [
            {"type": "bob", "start": 0, "duration": 4},
            {"type": "pop", "start": 0, "duration": 0.5},
        ]}],
    }, ensure_ascii=False), encoding="utf-8")
    mf = _manifest(proj)
    obj = [L for L in mf["scenes"][0]["layers"] if L["name"] == f"{sid}__1_box"][0]
    types = [m["type"] for m in obj.get("moves", [])]
    assert "bob" not in types
    assert "pop" in types


def test_source_field_passed(tmp_path):
    proj = _project(tmp_path)
    data = json.loads((proj / "scenes.json").read_text(encoding="utf-8"))
    data["scenes"][0]["source"] = "자료: 국토부 2025"
    data["scenes"][1]["source"] = "   "          # 공백뿐 — 실리면 안 된다
    (proj / "scenes.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    mf = _manifest(proj)
    assert mf["scenes"][0]["source"] == "자료: 국토부 2025"
    assert "source" not in mf["scenes"][1]


def test_ae_name_numbering_topmost_first(tmp_path):
    """순번 01 = 최상위(z 큰) 레이어 — 프롬프트·파일명·AE 이름이 같은 방향을 본다."""
    proj = _project(tmp_path)
    from PIL import Image
    sid = "aaa111"
    Image.new("RGBA", (100, 100), (0, 0, 0, 255)).save(proj / "layers" / f"{sid}__1_desk.png")
    specs = [
        {"layer": f"{sid}__0_kid_char", "index": 0, "name": "노란옷 아이", "name_en": "kid",
         "location": "", "kind": "character", "intent": "", "z": 1, "bbox": [100, 200, 300, 600]},
        {"layer": f"{sid}__1_desk", "index": 1, "name": "책상", "name_en": "desk",
         "location": "", "kind": "object", "intent": "", "z": 2, "bbox": [50, 500, 900, 900]},
    ]
    (proj / "layers" / f"{sid}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    mf = _manifest(proj)
    names = [L["aeName"] for L in mf["scenes"][0]["layers"]]
    # 배열은 뒤→앞(스택 순서: 먼저 추가 = 최하단)이지만 순번은 앞이 01
    assert names[0] == "S01_배경"
    assert names[1] == "S01_02_노란옷아이"    # z=1, 뒤쪽 → 02
    assert names[2] == "S01_01_책상"          # z=2, 최상위 → 01
