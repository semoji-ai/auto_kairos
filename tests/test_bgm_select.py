"""BGM 선곡·정리(scripts/bgm_select.py) — 합성 레벨·합성 곡(ffmpeg 있을 때)."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bgm_select", ROOT / "scripts" / "bgm_select.py")
bgm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bgm)

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg 없음")


def test_bpm_from_filename():
    assert bgm.bpm_from_name("deep-house_warm_124_03.mp3") == 124
    assert bgm.bpm_from_name("choir_epic_07.mp3") == 120          # 번호(7)는 BPM 이 아니다
    assert bgm.bpm_from_name("noname.mp3") == 120


def test_detect_breaks_at_0_1s_resolution():
    lv = np.full(400, -20.0)              # 40초, 0.1초 단위
    lv[150:170] = -32.0                   # 15.0~17.0초 12dB 빠짐 — 120BPM 한 마디(2초)
    lv[250:253] = -40.0                   # 0.3초 짧은 틈 — 브레이크 아님(마디보다 짧다)
    assert bgm.detect_breaks(lv, 120) == [(15.0, 17.0)]


def test_detect_breaks_ignores_small_dips_long_sections_and_edges():
    lv = np.full(400, -20.0)
    lv[100:120] = -26.0                   # 6dB — 기준(8dB) 미만
    lv[200:300] = -35.0                   # 10초 — 마디 수(2.25마디) 초과, 곡 구성(섹션)이다
    lv[2:20] = -40.0                      # 처음 3초 안 — 인트로
    assert bgm.detect_breaks(lv, 120) == []


def test_choose_one_track_per_chapter_no_reuse_mood_first():
    lib = [{"track": "/l/rock_hard_120_01.mp3", "usable": 200, "breaks": []},
           {"track": "/l/cinematic_calm_90_02.mp3", "usable": 130, "breaks": [(10, 12)]},
           {"track": "/l/downtempo_calm_80_03.mp3", "usable": 125, "breaks": []},
           {"track": "/l/short_60_04.mp3", "usable": 30, "breaks": []}]
    plan = bgm.choose([{"chapter": 1, "duration": 120, "mood": "cinematic"},
                       {"chapter": 2, "duration": 120, "mood": None},
                       {"chapter": 3, "duration": 190, "mood": None},
                       {"chapter": 4, "duration": 100, "mood": None}], lib)
    picks = [p["pick"] and Path(p["pick"]["track"]).name for p in plan]
    assert picks[0] == "cinematic_calm_90_02.mp3"            # 분위기 우선
    assert picks[1] == "downtempo_calm_80_03.mp3"            # 남은 것 중 브레이크 적고 길이 가까운 곡
    assert picks[2] == "rock_hard_120_01.mp3"
    assert picks[3] is None                                   # 남은 곡이 짧다 — 이어 붙이지 않는다


def _make_track(path: Path, dur: float, dip=None):
    vol = "1"
    if dip:
        vol = f"if(between(t,{dip[0]},{dip[1]}),0.1,1)"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"anoisesrc=d={dur}:c=pink:a=0.3:seed=7", "-af", f"volume='{vol}':eval=frame",
                    "-ar", "44100", str(path)], check=True)


@needs_ffmpeg
def test_end_to_end_cut_break_trim_fade_and_normalize(tmp_path):
    lib = tmp_path / "lib"
    lib.mkdir()
    _make_track(lib / "cinematic_calm_120_01.wav", 30.0, dip=(12.0, 14.0))   # 2초(1마디) 20dB 빠짐
    _make_track(lib / "short_120_02.wav", 10.0)
    timing = tmp_path / "timing.json"
    timing.write_text(json.dumps({"chapters": [{"chapter": 1, "duration": 20.0}]}), encoding="utf-8")
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "bgm_select.py"), "--library", str(lib),
                        "--timing", str(timing), "-o", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    man = json.loads((out / "bgm_manifest.json").read_text(encoding="utf-8"))
    row = man["chapters"][0]
    assert Path(row["track"]).name == "cinematic_calm_120_01.wav"
    assert len(row["cuts"]) == 1 and abs(row["cuts"][0][0] - 12.0) <= 0.2 and abs(row["cuts"][0][1] - 14.0) <= 0.2
    assert abs(row["lufs_after"] - (-14.4)) <= 0.6 and row["lufs_ok"]
    assert row["layer_gain_db"] == -25.0
    x = bgm.decode_mono(Path(row["out"]))
    assert abs(len(x) / bgm.SR - 20.0) < 0.1
    # 잘라 낸 뒤에는 (페이드 구간 밖에서) 브레이크가 없다
    assert bgm.detect_breaks(bgm.levels_db(x), 120) == []
