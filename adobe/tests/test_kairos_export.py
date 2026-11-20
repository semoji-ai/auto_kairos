"""카이로스 내보내기(scripts/kairos_export.py): 매니페스트 → 올릴 파일 + 타임라인.

작은 가짜 편을 만들어 본다 — 레이어 씬(카메라 줌 + 까딱임), 사진 한 장 씬, 경로 옮기기,
에셋 자리 채우기.
"""
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "kairos_export", Path(__file__).resolve().parents[1] / "scripts" / "kairos_export.py")
ke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ke)


@pytest.fixture
def project(tmp_path):
    p = tmp_path / "abcd1234_demo"
    (p / "layers").mkdir(parents=True)
    (p / "images").mkdir()
    (p / "audio").mkdir()
    Image.new("RGBA", (1660, 948), (10, 20, 30, 255)).save(p / "layers" / "s1__bg.png")
    Image.new("RGBA", (400, 800), (200, 0, 0, 255)).save(p / "layers" / "s1__0_Person_char.png")
    Image.new("RGB", (3000, 2000), (0, 90, 0)).save(p / "images" / "photo.jpg")
    for n in ("s1", "s2"):
        (p / "audio" / f"{n}.mp3").write_bytes(b"ID3" + b"\0" * 64)
    nas = "/Volumes/nas/workspace/output/abcd1234_demo"  # 매니페스트에는 다른 기기의 절대 경로가 적혀 있다
    manifest = {
        "fps": 30, "themeColors": {"bg": "#101820"},
        "scenes": [
            {"ae_comp_name": "S01_s1", "start": 0.0, "duration": 4.0, "audio": f"{nas}/audio/s1.mp3",
             "subtitle": "첫 씬입니다.", "title": "제목",
             "camera": [{"scale": 100}, {"scale": 110}],
             "layers": [
                 {"name": "bg", "aeName": "S01 배경", "path": f"{nas}/layers/s1__bg.png", "scale": 115.66, "position": [960, 540]},
                 {"name": "person", "aeName": "S01 인물", "path": f"{nas}/layers/s1__0_Person_char.png", "scale": 100,
                  "position": [700, 600], "foot": [700, 1000], "moves": [{"type": "bob", "half_frames": 10}]},
             ]},
            {"ae_comp_name": "S02_s2", "start": 4.0, "duration": 2.0, "audio": f"{nas}/audio/s2.mp3",
             "subtitle": "둘째 씬.", "image": f"{nas}/images/photo.jpg", "width": 3000, "height": 2000,
             "imageFit": {"scale": 64, "position": [960, 540]}, "layers": []},
        ],
    }
    (p / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False))
    return p


def clip(tl, cid):
    return next(c for c in tl["clips"] if c["id"] == cid)


def test_plan_builds_files_and_timeline(project, tmp_path):
    out = tmp_path / "out"
    res = ke.build_plan(project, out, "all")
    tl = res["timeline"]
    assert res["frames"] == 180 and tl["fps"] == 30
    assert tl["sequence"] == {"width": 1920, "height": 1080, "background": "#101820"}
    assert [t["id"] for t in tl["tracks"]] == ["T2", "T1", "V2", "V1", "A1"]
    assert set(res["files"]) == {"s1__bg.png", "s1__0_Person_char.png", "s1.mp3", "s2.mp3", "photo.jpg"}
    assert all(Path(f["path"]).is_file() for f in res["files"].values())
    assert (out / "plan.json").is_file()
    # 다른 기기 경로로 적힌 파일도 이 편 폴더에서 찾는다
    assert res["files"]["s1.mp3"]["source"] == str(project / "audio" / "s1.mp3")
    # 큰 사진은 줄여서 올린다
    assert max(res["files"]["photo.jpg"]["width"], res["files"]["photo.jpg"]["height"]) == ke.MAX_PHOTO_EDGE


def test_layer_scene_bakes_camera_and_bob(project, tmp_path):
    tl = ke.build_plan(project, tmp_path / "out", "1")["timeline"]
    bg, person = clip(tl, "s1_0"), clip(tl, "s1_1")
    assert bg["asset"] == "@file:s1__bg.png" and bg["track_id"] == "V1" and person["track_id"] == "V2"
    assert (bg["start"], bg["dur"]) == (0, 120)
    # 카메라 줌: 첫 키와 끝 키, 첫 키에 70:30 가속
    k0, k1 = bg["keyframes"]["scale"]
    assert (k0["t"], k1["t"]) == (0, 119) and k0["ease"] == ke.CAM_EASE and "ease" not in k1
    assert k1["v"][0] == pytest.approx(k0["v"][0] * 1.1, rel=1e-4)
    assert bg["keyframes"]["position"][0]["v"] == [0.0, 0.0]  # 가운데 놓인 배경은 줌에도 가운데
    # 까딱임: 발을 기준점으로, 이지 이즈 두 키를 왕복 반복
    assert person["anchor"] == [0.5, 1.0]
    rot = person["keyframes"]["rotation"]
    assert [k["t"] for k in rot] == [0, 10] and all(k["ease"] == ke.SMOOTH for k in rot)
    assert rot[0]["v"] == -rot[1]["v"]
    assert person["motion"] == {"rotation": {"loop": "pingpong"}}
    # 음성·자막·제목
    assert clip(tl, "s1_vo")["asset"] == "@file:s1.mp3"
    assert clip(tl, "s1_sub")["text"] == "첫 씬입니다."
    assert clip(tl, "s1_title")["start"] == 6


def test_photo_scene_and_scene_range(project, tmp_path):
    res = ke.build_plan(project, tmp_path / "out", "2")
    tl = res["timeline"]
    assert res["scenes"] == [2, 2] and res["frames"] == 60
    photo = clip(tl, "s2_photo")
    assert photo["start"] == 0 and photo["dur"] == 60  # 고른 범위의 첫 씬이 0프레임
    assert photo["transform"]["x"] == 0 and photo["transform"]["scale_x"] == pytest.approx(3000 * 0.64 / 1620, rel=1e-3)  # 줄인 사진의 세로가 정수로 맞춰진다
    assert "s1.mp3" not in res["files"]
    with pytest.raises(ke.ExportError):
        ke.parse_scenes("3", 2)
    with pytest.raises(ke.ExportError):
        ke.parse_scenes("2-1", 2)


def test_finalize_fills_assets(project, tmp_path):
    out = tmp_path / "out"
    res = ke.build_plan(project, out, "all")
    names = list(res["files"])
    (out / "map.txt").write_text("# 주석\n" + "\n".join(f"{n} asset:image:{i}" for i, n in enumerate(names[:-1])))
    with pytest.raises(ke.ExportError, match=names[-1]):
        ke.finalize(out)  # 하나라도 빠지면 쓰지 않는다
    (out / "map.txt").write_text("\n".join(f"{n} asset:image:{i}" for i, n in enumerate(names)))
    tl = ke.finalize(out)
    assets = [c["asset"] for c in tl["clips"] if "asset" in c]
    assert assets and all(a.startswith("asset:image:") for a in assets)
    assert json.loads((out / "timeline.json").read_text()) == tl


def test_missing_file_is_an_error(project, tmp_path):
    (project / "layers" / "s1__bg.png").unlink()
    with pytest.raises(ke.ExportError, match="s1__bg.png"):
        ke.build_plan(project, tmp_path / "out", "1")
