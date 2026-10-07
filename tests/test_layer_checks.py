"""레이어 분리 점검 — 이름 목록 누락, 응답 누락, 배경판 잔상(합성 그림)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from auto_agent.tools.layer_checks import (check_layer_dir, covers, missing_expected,
                                           missing_returned, residue_score)

ROOT = Path(__file__).resolve().parent.parent


def test_name_list_completeness():
    names = ["golden 63 Building model with sparkles", "white descending stair podium"]
    assert covers("63 Building model", names[0])
    assert missing_expected(["63 building", "stair podium", "2026 text block",
                             {"name": "connector arrow"}], names) == ["2026 text block", "connector arrow"]
    assert missing_expected(None, names) == []


def test_missing_returned_layers():
    assert missing_returned(["A", "B", "C"], [None, "a", "C"]) == ["B"]


def _scene(size=(400, 300), seed=0):
    rng = np.random.default_rng(seed)
    base = np.full((size[1], size[0], 3), 200, np.uint8)
    base += rng.integers(0, 6, base.shape, dtype=np.uint8)       # 거의 민무늬 벽
    return base


def _textured_box(img, box, seed=1):
    rng = np.random.default_rng(seed)
    l, t, r, b = box
    img[t:b, l:r] = rng.integers(0, 255, (b - t, r - l, 3), dtype=np.uint8)
    return img


def _element(box, scale=2):
    l, t, r, b = box
    el = Image.new("RGBA", ((r - l) * scale, (b - t) * scale), (0, 0, 0, 0))
    ImageDraw.Draw(el).rectangle([0, 0, el.width, el.height], fill=(10, 10, 10, 255))
    return el


BOX = (100, 80, 220, 200)


def test_residue_flags_element_left_in_plate():
    orig = _textured_box(_scene(), BOX)
    plate_kept = orig.copy()                        # 요소를 안 지운 판
    r = residue_score(Image.fromarray(orig), Image.fromarray(plate_kept), _element(BOX), BOX)
    assert r["level"] == "flag" and r["score"] > 0.9


def test_residue_ok_when_element_removed_even_if_colors_similar():
    orig = _scene()
    # 밝은 벽 위 밝은 간판 + 진한 글씨 줄 — 색 차이만 보면 잔상으로 오판하던 경우(한화 S158)
    l, t, r, b = BOX
    orig[t:b, l:r] = 190
    orig[t + 40:t + 50, l + 10:r - 10] = 60
    plate = _scene(seed=5)                          # 지워져 벽만 남은 판
    res = residue_score(Image.fromarray(orig), Image.fromarray(plate), _element(BOX), BOX)
    assert res["level"] == "ok"


def test_residue_handles_plate_size_mismatch_and_flat_elements():
    orig = _textured_box(_scene(), BOX)
    plate = Image.fromarray(orig).resize((800, 600))
    assert residue_score(Image.fromarray(orig), plate, _element(BOX), BOX)["level"] == "flag"
    flat = _scene()
    assert residue_score(Image.fromarray(flat), Image.fromarray(flat), _element(BOX), BOX)["level"] == "flat"


def _layer_dir(tmp_path, keep=True):
    orig = _textured_box(_scene(), BOX)
    src = tmp_path / "scene.png"
    Image.fromarray(orig).save(src)
    d = tmp_path / "S001"
    d.mkdir()
    Image.fromarray(orig if keep else _scene(seed=9)).save(d / "z00_background.png")
    _element(BOX).save(d / "z01_box.png")
    (d / "elements.json").write_text(json.dumps({"key": "S001", "source": str(src), "names": ["box"], "elements": [
        {"layer": "z00_background.png", "name": "background", "z": 0, "bbox": None, "kind": "background"},
        {"layer": "z01_box.png", "name": "box", "z": 1, "bbox": list(BOX), "kind": "object"}]}), encoding="utf-8")
    return d, src


def test_check_layer_dir_writes_flag_into_elements_json(tmp_path):
    d, _ = _layer_dir(tmp_path, keep=True)
    issues = check_layer_dir(d)
    assert [i["name"] for i in issues] == ["box"] and issues[0]["level"] == "flag"
    m = json.loads((d / "elements.json").read_text(encoding="utf-8"))
    assert m["elements"][1]["bg_residue"]["level"] == "flag"


def test_layerize_recheck_cli_reports_without_calling_fal(tmp_path):
    d, src = _layer_dir(tmp_path, keep=True)
    names = tmp_path / "names.json"
    names.write_text(json.dumps({"S001": {"image": str(src), "names": ["box"],
                                          "expected": ["box", "arrow to box"]}}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "layerize_scenes.py"), str(names),
                        "-o", str(tmp_path), "--recheck"], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    rep = json.loads((tmp_path / "layer_report.json").read_text(encoding="utf-8"))
    assert rep["name_gaps"] == {"S001": ["arrow to box"]}
    assert rep["residue"][0]["name"] == "box"


def test_codex_matte_refuses_without_approval(tmp_path):
    jobs = tmp_path / "jobs.json"
    jobs.write_text("{}", encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "codex_matte_layers.py"), str(jobs),
                        "-o", str(tmp_path)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2 and "폐기" in r.stderr


@pytest.mark.parametrize("keep,level", [(0.35, "flag"), (0.15, "ok")])
def test_single_cutoff_025_flags_faint_residue(keep, level):
    # 판에 원본 무늬가 keep 비율만큼 희미하게 남은 경우 — 0.25 이상이면 flag 하나뿐(warn 없음)
    orig = _textured_box(_scene(), BOX).astype(np.float32)
    wall = _scene(seed=3).astype(np.float32)
    plate = wall.copy()
    l, t, r, b = BOX
    plate[t:b, l:r] = wall[t:b, l:r] + keep * (orig[t:b, l:r] - wall[t:b, l:r])
    res = residue_score(Image.fromarray(orig.astype(np.uint8)), Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8)),
                        _element(BOX), BOX)
    assert res["level"] == level
