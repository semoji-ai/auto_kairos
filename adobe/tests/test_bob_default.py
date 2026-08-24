"""까딱임 기본값이 렌더러마다 갈리지 않는지 — 반주기 10프레임 · 100 → 101 · easy ease.

같은 인물이 애프터이펙트와 리모션에서 다르게 까딱이면 안 된다. 실제로 갈려
있었다 — AE 는 반주기 0.6초(18프레임), `build_layered_props` 는 폭·주기가
모두 무작위, `SemojiLayerScene` 만 10프레임/101% 였다.

정본은 `motion.py` 의 `BOB_*` 하나다. 여기서는 **그 값이 각 렌더러까지
실제로 닿는지**를 본다 — 상수만 검사하면 아무도 안 쓰는 상수도 통과한다.
"""
import importlib.util
import re
from pathlib import Path

from backend import motion

ROOT = Path(__file__).resolve().parents[2]
PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"


def test_canonical_values():
    assert motion.BOB_HALF_FRAMES == 10
    assert motion.BOB_AMOUNT == 1                      # 100 → 101


def test_manifest_move_carries_the_numbers():
    """jsx 가 숫자를 직접 적지 않도록 매니페스트가 실어 보낸다."""
    mv = motion.bob_move(0, 5.0)
    assert mv["type"] == "bob"
    assert mv["half_frames"] == 10 and mv["amount"] == 1


def test_ae_reads_the_manifest_not_a_hardcoded_second():
    """AE 는 프레임으로 센다 — 초로 적으면 fps 가 바뀔 때 어긋난다."""
    jsx = (PANEL / "jsx" / "build_scene.jsx").read_text(encoding="utf-8")
    assert "mv.half_frames" in jsx
    assert "comp.frameDuration" in jsx
    assert "var half = 0.6;" not in jsx                 # 옛 하드코딩


def test_ae_manual_preset_matches():
    """손으로 거는 프리셋도 조립할 때와 같은 값이어야 한다."""
    jsx = (PANEL / "jsx" / "tools.jsx").read_text(encoding="utf-8")
    assert "var half = 10 * comp.frameDuration;" in jsx
    assert "var bAmt = amt || 1;" in jsx                # 전에는 3 이었다
    assert "var half = 0.6;" not in jsx


def test_remotion_period_is_the_same_motion():
    """초당 주기(Hz)로 환산해도 한 바퀴가 20프레임이어야 한다."""
    b = motion.bob_remotion(fps=30.0)
    assert b["amp"] == 0.01
    assert round(1.0 / b["period"] * 30.0) == 20        # 20프레임 한 바퀴


def _blp():
    s = importlib.util.spec_from_file_location(
        "blp", ROOT / "scripts" / "build_layered_props.py")
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


def test_layered_props_bob_is_no_longer_random():
    """폭과 주기는 모두 같고 **위상만** 흩는다.

    전에는 셋 다 무작위라 같은 인물이 씬마다 다르게 까딱였다.
    """
    m = _blp()
    got = [m.bob(n, i) for i, n in enumerate(["가", "나", "다"])]
    assert {g["amp"] for g in got} == {0.01}
    assert {g["period"] for g in got} == {motion.bob_remotion()["period"]}
    assert len({g["phase"] for g in got}) == 3         # 시작 시점만 다르다


def test_semoji_layer_scene_defaults_agree():
    """리모션 쪽 기준 렌더러도 같은 값이어야 한다."""
    src = (ROOT / "auto_agent" / "remotion_template" / "src"
           / "SemojiLayerScene.tsx").read_text(encoding="utf-8")
    assert "motion.period_frames || 20" in src          # 한 바퀴 20프레임
    assert "motion.max_scale || 1.01" in src            # 100 → 101
    assert "Easing.inOut(Easing.ease)" in src           # easy ease


def test_feet_bob_emitters_use_the_names_the_renderer_reads():
    """읽히지 않는 이름으로 적으면 조용히 기본값으로 떨어진다."""
    for rel in ("scripts/split_characters.py", "scripts/scene_layer_v2.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        for m in re.finditer(r'"type":\s*"feet_bob"(.{0,220})', src, re.S):
            blk = m.group(1)
            assert "period_frames" in blk and "max_scale" in blk, rel
            assert "period_s" not in blk and "amplitude_pct" not in blk, rel
