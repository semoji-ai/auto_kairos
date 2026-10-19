import json, subprocess, sys
from pathlib import Path


def make_ep(tmp):
    ep = Path(tmp) / "EP"
    (ep / "master").mkdir(parents=True)
    edl = {"parts": [{"id": "a", "clip": "A", "pr_in": 0, "src_in": 0, "dur": 10},
                     {"id": "b", "clip": "B", "pr_in": 10, "src_in": 0, "dur": 10}],
           "cuts": [], "outro": None, "pr_length": 20, "length": 20}
    src = {"segments": [{"id": "n001", "part": "a", "in": 1, "out": 4, "ko": "x", "subs": []},
                        {"id": "n002", "part": "b", "in": 12, "out": 16, "ko": "y", "subs": []}], "strings": []}
    json.dump(edl, open(ep / "master/edl.json", "w"))
    json.dump(src, open(ep / "master/source.json", "w"))
    json.dump({"parts": {"a": {"comp": "CA", "narration": "na.wav"}, "b": {"comp": "CB", "narration": "nb.wav"}}},
              open(ep / "master_config.json", "w"))
    return ep


def test_test_pattern_writes_warp(tmp_path):
    ep = make_ep(tmp_path)
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/timewarp.py"), str(ep), "t1", "--test-pattern",
                    "--job", str(tmp_path / "job.json")], check=True)
    w = json.load(open(ep / "build/t1/warp.json"))
    # n001 3초 ×0.9(홀수 순번=1) = 2.7, n002 4초 ×1.15 = 4.6 → 전체 20 - 0.3 + 0.6
    assert abs(w["length_new"] - 20.3) < 1e-6
    assert abs(w["parts"]["a"]["dur_new"] - 9.7) < 1e-6
    assert w["parts"]["b"]["comp"] == "CB"
    job = json.load(open(tmp_path / "job.json"))
    assert job["mute_sources"] == ["na.wav", "nb.wav"]


def test_keep_subs_disables_subtitle_hiding_for_verification(tmp_path):
    ep = make_ep(tmp_path)
    root = Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable, str(root / "scripts/timewarp.py"), str(ep), "t2", "--test-pattern", "--keep-subs",
                    "--job", str(tmp_path / "job.json")], check=True)
    assert json.load(open(tmp_path / "job.json"))["hide_comp_prefix"] is None
