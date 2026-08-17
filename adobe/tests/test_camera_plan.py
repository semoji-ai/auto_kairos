"""camera_plan — 나레이션 기반 결정적 카메라 플랜(인수인계 문서 규칙 이식)."""
import json
from pathlib import Path

import pytest

from backend import camera_plan

SID = "abc123"


# ---- rect_for_bbox: v3 rect_of 클램프 이식 ----

def test_full_rect_is_16by9_centered():
    r = camera_plan.full_rect(1792, 1024)
    assert r[2] / r[3] == pytest.approx(camera_plan.AR, abs=0.01)
    assert r[2] <= 1792 and r[3] <= 1024
    assert r[0] == pytest.approx((1792 - r[2]) / 2, abs=0.1)


def test_rect_small_subject_full_body():
    """작은 인물 — 전신을 tight 비율로 잡는다."""
    r = camera_plan.rect_for_bbox([800, 300, 900, 600], 1792, 1024)   # 높이 300
    assert r[3] == pytest.approx(300 / 0.6, abs=0.5)                   # h = bh/tight
    assert r[2] / r[3] == pytest.approx(camera_plan.AR, abs=0.01)


def test_rect_tall_subject_upper_body():
    """큰 인물(전신 화각이 캔버스 초과) — 상반신으로 바꾼다. 박정희 626px 실측 규칙."""
    r = camera_plan.rect_for_bbox([600, 100, 900, 950], 1792, 1024)   # 높이 850
    # 850/0.6=1417 > 1024 → h = 850*0.72 = 612
    assert r[3] == pytest.approx(850 * 0.72, abs=0.5)
    # 중심 y = 100 + 850*0.30 = 355 → y = 355 - 612/2 = 49
    assert r[1] == pytest.approx(49.0, abs=0.5)


def test_rect_clamped_inside_canvas():
    r = camera_plan.rect_for_bbox([1700, 900, 1790, 1020], 1792, 1024)  # 우하단 구석
    assert r[0] >= 0 and r[1] >= 0
    assert r[0] + r[2] <= 1792.01 and r[1] + r[3] <= 1024.01


def test_rect_invalid_bbox():
    assert camera_plan.rect_for_bbox([10, 10, 10, 10], 1792, 1024) is None
    assert camera_plan.rect_for_bbox(None, 1792, 1024) is None


# ---- first_mention: 타임스탬프 큐 ----

def _ts(text):
    chars = list(text)
    starts = [round(i * 0.1, 2) for i in range(len(chars))]
    return chars, starts


def test_first_mention_basic():
    chars, starts = _ts("옛날에 노란옷 아이가 있었다")
    t = camera_plan.first_mention(chars, starts, "노란옷 아이")
    assert t == pytest.approx(0.4)                 # "노"의 시각


def test_first_mention_ignores_spacing():
    chars, starts = _ts("노란옷아이가 걸어간다")
    assert camera_plan.first_mention(chars, starts, "노란옷 아이") == pytest.approx(0.0)


def test_first_mention_absent():
    chars, starts = _ts("아무 상관 없는 문장")
    assert camera_plan.first_mention(chars, starts, "전기차") is None


# ---- plan_scene_camera: 씬 플랜 ----

def _proj(tmp_path: Path, text: str, specs: list, img=(1792, 1024)):
    from PIL import Image
    proj = tmp_path / "p"
    (proj / "audio").mkdir(parents=True)
    (proj / "layers").mkdir()
    (proj / "storyboard").mkdir()
    Image.new("RGB", img).save(proj / "storyboard" / f"sb_{SID}.png")
    chars = list(text)
    (proj / "audio" / f"tts_{SID}.timestamps.json").write_text(json.dumps({
        "text": text, "characters": chars,
        "starts": [round(i * 0.1, 2) for i in range(len(chars))],
        "ends": [round(i * 0.1 + 0.1, 2) for i in range(len(chars))],
    }, ensure_ascii=False), encoding="utf-8")
    (proj / "layers" / f"{SID}__elements.json").write_text(
        json.dumps(specs, ensure_ascii=False), encoding="utf-8")
    return proj


def _scene():
    return {"sceneId": SID, "_image": f"storyboard/sb_{SID}.png"}


def _spec(i, name, kind="character", bbox=None):
    return {"layer": f"{SID}__{i}_{name}", "index": i, "name": name, "name_en": name,
            "location": "", "kind": kind, "intent": "", "z": i + 1,
            "bbox": bbox or [700, 300, 900, 700]}


def test_plan_arrival_leads_cue(tmp_path):
    """동작의 끝은 발음보다 LEAD(0.3초) 앞이다 — 눈이 귀보다 먼저."""
    text = "한참을 걷다가 마침내 소년이 나타났다 그리고 오래 이야기했다"
    proj = _proj(tmp_path, text, [_spec(0, "소년")])
    keys = camera_plan.plan_scene_camera(proj, _scene(), duration=10.0)
    cue = text.replace(" ", "").find("소년")  # 압축 인덱스 → 시각은 원문 기준이라 직접 계산
    t_cue = text.find("소년") * 0.1
    arrive = keys[-1]["t"]
    assert arrive == pytest.approx(t_cue - 0.3, abs=0.01)
    assert keys[-1]["ease"] == "70:30"


def test_plan_has_explicit_hold(tmp_path):
    """출발 직전에 같은 rect 정지 키가 있다 — 없으면 AE가 처음부터 보간한다."""
    text = "한참을 걷다가 마침내 소년이 나타났다 그리고 오래 이야기했다"
    proj = _proj(tmp_path, text, [_spec(0, "소년")])
    keys = camera_plan.plan_scene_camera(proj, _scene(), duration=10.0)
    assert len(keys) == 3
    assert keys[0]["rect"] == keys[1]["rect"]          # 전체 화각 정지 구간
    expect_start = max(keys[2]["t"] - camera_plan.MOVE, 0.2)
    assert keys[1]["t"] == pytest.approx(expect_start, abs=0.01)


def test_plan_respects_end_hold(tmp_path):
    """씬 끝 직전 언급 — 도착이 dur-0.4를 넘지 않는다."""
    text = "오래오래 아무 일도 없다가 끝에 소년"
    proj = _proj(tmp_path, text, [_spec(0, "소년")])
    dur = len(text) * 0.1
    keys = camera_plan.plan_scene_camera(proj, _scene(), duration=dur)
    if keys:
        assert keys[-1]["t"] <= dur - 0.4 + 0.001


def test_plan_max_two_moves(tmp_path):
    text = ("소년이 나오고 한참 지나 전기차가 나오고 또 한참 지나 충전기가 나오고 "
            "다시 한참 지나 간판이 보였다 그 뒤로도 이야기는 오래 이어졌다")
    specs = [_spec(0, "소년", bbox=[100, 300, 300, 700]),
             _spec(1, "전기차", "object", bbox=[600, 400, 1100, 800]),
             _spec(2, "충전기", "object", bbox=[1200, 300, 1400, 800]),
             _spec(3, "간판", "object", bbox=[1500, 100, 1750, 400])]
    proj = _proj(tmp_path, text, specs)
    keys = camera_plan.plan_scene_camera(proj, _scene(), duration=len(text) * 0.1)
    moves = sum(1 for k in keys if k.get("ease"))
    assert moves <= camera_plan.MAX_MOVES


def test_plan_no_mention_no_camera(tmp_path):
    proj = _proj(tmp_path, "아무 관련 없는 이야기가 흘러간다", [_spec(0, "소년")])
    assert camera_plan.plan_scene_camera(proj, _scene(), duration=5.0) == []


def test_plan_no_timestamps_no_camera(tmp_path):
    proj = _proj(tmp_path, "소년이 나타났다", [_spec(0, "소년")])
    (proj / "audio" / f"tts_{SID}.timestamps.json").unlink()
    assert camera_plan.plan_scene_camera(proj, _scene(), duration=5.0) == []


def test_plan_removed_layer_ignored(tmp_path):
    sp = _spec(0, "소년")
    sp["removed"] = True
    proj = _proj(tmp_path, "소년이 나타났다 그리고 오래 이야기했다", [sp])
    assert camera_plan.plan_scene_camera(proj, _scene(), duration=8.0) == []


# ---- 모션 플랜 결선 ----

def test_motion_plan_carries_camera_keys(tmp_path, monkeypatch):
    """모션 버튼 한 번으로 화각 키가 사이드카에 실린다 — LLM 카메라 type을 대체."""
    from backend import motion
    text = "한참을 걷다가 마침내 소년이 나타났다 그리고 오래 이야기했다"
    proj = _proj(tmp_path, text, [_spec(0, "소년")])
    (proj / "scenes.json").write_text(json.dumps({"scenes": [
        {"sceneNumber": 1, "sceneId": SID, "title": "t", "narration": text,
         "imageRef": f"storyboard/sb_{SID}.png", "duration_estimate_sec": 10}]},
        ensure_ascii=False), encoding="utf-8")
    (proj / "layers" / f"{SID}__0_소년.png").write_bytes(b"png")

    def fake_run(prompt, proj_dir, **kw):
        Path(kw["output_last"]).write_text(json.dumps({
            "layers": [{"layer": f"{SID}__0_소년", "moves": [
                {"type": "bob", "start": 0, "duration": 5, "direction": None, "amount": None}]}],
            "camera": {"type": "slow_zoom_in", "amount": 6}}), encoding="utf-8")
        return {"returncode": 0}

    monkeypatch.setattr(motion.llm, "run_orchestrator", fake_run)
    plan = motion.plan_scene_motion(proj, 1)
    assert isinstance(plan["camera"], list)            # type 대신 화각 키
    assert plan["camera"][-1]["ease"] == "70:30"
    side = json.loads((proj / f"motion_{SID}.json").read_text(encoding="utf-8"))
    assert isinstance(side["camera"], list)


def test_clamp_skips_camera_key_list():
    from backend import motion
    plan = {"layers": [], "camera": [{"t": 0, "rect": [0, 0, 100, 56]}]}
    out = motion._clamp_plan(plan, 5.0)
    assert out["camera"][0]["rect"] == [0, 0, 100, 56]
