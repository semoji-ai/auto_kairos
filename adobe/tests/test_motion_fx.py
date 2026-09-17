"""거는 모션(motion_fx.jsx) — 익스프레션 + 이펙트 컨트롤 + 마커.

AE 없이 검사할 수 있는 것만 본다.
  · ExtendScript 가 읽을 수 있는 문법인가(ES5)
  · 컨트롤 읽기가 **전부** 기본값과 함께 감싸여 있는가 (지워도 안 죽어야 한다)
  · 남의 식·마커를 건드리지 않는가
  · shape() 가 실측 곡선을 재현하는가 — 파이썬으로 옮겨 수치 대조
"""
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import es5_code

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
JSX = PANEL / "jsx" / "motion_fx.jsx"


def _src():
    return JSX.read_text(encoding="utf-8")


def test_es5_only():
    """ExtendScript 는 let/const/화살표/템플릿을 못 읽는다."""
    code = es5_code(_src())
    for bad in ("=>", "`", " let ", " const "):
        assert bad not in code, f"ES5 위반: {bad!r}"


def test_every_control_read_has_a_default():
    """컨트롤을 지워도 식이 죽으면 안 된다 — 읽기는 전부 기본값을 함께 넘긴다.

    애니메이션 컴포저가 `acSliderValP(fx, prop, 기본값)` 로 감싸는 이유다.
    감싸지 않으면 사용자가 슬라이더 하나를 지웠을 때 레이어가 통째로 사라진다.
    """
    src = _src()
    # 익스프레션 안의 읽기 헬퍼는 S/C/D 세 개뿐이고, 모두 인자 2개를 받는다
    for name in ("function S(n, dv)", "function C(n, dv)", "function D(n, dv)"):
        assert name in src
    for call in re.findall(r"\bS\('([^']+)'([^)]*)\)", src):
        assert "," in call[1], f"S('{call[0]}') 에 기본값이 없습니다"
    for call in re.findall(r"\bC\('([^']+)'([^)]*)\)", src):
        assert "," in call[1], f"C('{call[0]}') 에 기본값이 없습니다"
    for call in re.findall(r"\bD\('([^']+)'([^)]*)\)", src):
        assert "," in call[1], f"D('{call[0]}') 에 기본값이 없습니다"


def test_master_switch_is_the_effect_toggle():
    """끄고 켜기는 이펙트의 fx 토글로 — 체크박스를 따로 두지 않는다."""
    src = _src()
    assert ".active ? 1 : 0" in src
    assert "function EN()" in src


def test_marker_role_lives_in_parameters_not_comment():
    """마커 주석 칸은 사용자 것이다 — 역할은 parameters 에 적는다."""
    src = _src()
    assert 'AK_PARAM = "zzz_AK역할"' in src          # z 로 시작해야 목록 맨 아래로 밀린다
    assert "setParameters" in src
    assert "marker.key(i).parameters" in src
    assert "return marker.key(cmt).time" in src      # 그래도 주석 폴백은 남긴다


def test_clear_only_touches_own_work():
    """AK 가 건 것만 걷어낸다 — 손으로 쓴 식과 남의 마커는 남긴다."""
    src = _src()
    assert 'p.expression.indexOf(AK_TAG) === 0' in src
    assert 'nm.substring(0, AK_FX.length) === AK_FX' in src


def test_apply_clears_before_reapplying():
    """두 번 누르면 컨트롤이 겹쳐 쌓인다 — 걸기 전에 먼저 걷어낸다."""
    src = _src()
    body = src.split("function akFxApplyOne")[1]
    assert "akFxClearOne(il);" in body.split("akFxCheck")[0]


def test_every_kind_has_defaults():
    """버튼이 부르는 이름과 기본값 표가 어긋나면 'ERROR: 모르는 방식' 이 뜬다."""
    src = _src()
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    for kind in re.findall(r'data-fx="([a-z_]+)"', html):
        assert re.search(rf"^\s+{kind}:\s*{{", src, re.M), f"{kind} 기본값 없음"


def test_bake_reads_only_own_expressions():
    src = _src()
    assert 'p.expression.indexOf(AK_TAG) !== 0' in src


# ── shape() 수치 대조 ────────────────────────────────────────────────
# jsx 안의 식을 파이썬으로 옮긴 것. 양쪽이 갈리면 이 테스트가 먼저 깨진다.

def _shape(x, s0, ov, pk, bk, pw):
    if x <= 0:
        return s0
    if x >= 1:
        return 1.0
    if ov <= 0:
        y = s0 + (1 - s0) * (1 - (1 - x) ** pw)
    elif x < pk:
        y = s0 + (1 + ov - s0) * (1 - (1 - x / pk) ** pw)
    else:
        v = (x - pk) / (1 - pk)
        y = 1 + ov * math.exp(-4 * v) * math.cos(v * math.pi * (0.5 + bk))
    if x > 0.8:
        y = 1 + (y - 1) * (1 - (x - 0.8) / 0.2)
    return y


BANDS = json.loads((Path(__file__).resolve().parents[1] / "data"
                    / "motion-bands.json").read_text(encoding="utf-8"))["families"]


def _defaults(kind):
    src = _src()
    line = re.search(rf"^\s+{kind}:\s*{{(.+?)}}", src, re.M | re.S).group(1)
    return {k: float(v) for k, v in re.findall(r"(\w+):\s*([\d.]+)", line)}


@pytest.mark.parametrize("kind", sorted(k for k in BANDS if "peak_pct" in BANDS[k]))
def test_defaults_match_the_measured_median(kind):
    """jsx 의 기본값은 밴드 파일의 p50 을 옮겨 적은 것이다 — 갈리면 여기서 잡는다.

    정본은 `adobe/data/motion-bands.json`(프리뷰 8,273편 실측)이고
    jsx 는 사본이다. 사본을 손으로 고치면 근거를 잃는다.
    """
    d, b = _defaults(kind), BANDS[kind]
    pairs = [("start", "start_pct"), ("over", "overshoot_pct"),
             ("inF", "in_frames"), ("outF", "out_frames")]
    if "move_pct" in b:
        pairs = [("move", "move_pct")] + pairs[1:]
    for key, band in pairs:
        if key in d:                              # 계열이 안 쓰는 칸은 건너뛴다
            assert abs(d[key] - b[band][1]) < 0.6, \
                f"{kind}.{key}={d[key]} 인데 실측 p50 는 {b[band][1]}"
    if d.get("over"):                             # 오버슛이 없으면 정점은 뜻이 없다
        assert abs(d["peak"] - b["peak_pct"]) < 0.6
    assert abs(d["smooth"] - b["smooth"]) < 0.6


# 크기를 실제로 움직이는 계열만. **`position`·`fade` 는 여기서 제외한다** —
# 측정이 낸 「크기 곡선」은 bbox 대각을 잰 것이라, 화면 밖에서 들어오는 동안
# 가장자리에서 **잘려서** 작아 보인 흔적이지 프리셋이 크기를 움직인 게 아니다.
# 그걸 크기 애니메이션으로 알고 재다가 position 이 RMSE 0.073 으로 틀렸다.
SCALE_FAMILIES = ["bounce_scale", "overshoot_scale", "scale"]


@pytest.mark.parametrize("kind", SCALE_FAMILIES)
def test_defaults_reproduce_the_family_median_curve(kind):
    """기본값으로 그린 곡선이 그 계열의 중앙 곡선을 따라가야 한다.

    처음엔 **대표 곡선 한 편**에 맞췄다(정점 62·부드러움 83). 그 한 편은
    RMSE 0.017 로 잘 맞았지만 계열 전체와는 0.052 로 어긋났다.
    기준은 한 편이 아니라 분포다.
    """
    d, med = _defaults(kind), BANDS[kind]["median_curve"]
    if not med:
        pytest.skip("중앙 곡선 없음")
    pw = 1 + 3 * d["smooth"] / 100
    s0 = med[0]                       # 시작값은 곡선이 정한다(계열 p50 과 같다)
    n = len(med)
    err = [_shape(i / (n - 1), s0, d["over"] / 100, d["peak"] / 100,
                  d["back"], pw) - v for i, v in enumerate(med)]
    rmse = math.sqrt(sum(e * e for e in err) / n)
    assert rmse < 0.05, f"{kind} 중앙 곡선과 어긋납니다 RMSE={rmse:.4f}"


def test_shape_settles_exactly_at_one():
    """끝에서 정확히 제 크기로 와야 한다.

    감쇠식만 쓰면 잔차가 남아 레이어가 미묘하게 큰 채로 멈춘다.
    끝 20% 를 선형으로 깎는 처리가 그래서 있다(애니메이션 컴포저도 같다).
    """
    for kind in ("overshoot_scale", "bounce_scale", "scale"):
        d = _defaults(kind)
        pw = 1 + 3 * d["smooth"] / 100
        assert abs(_shape(1.0, d["start"] / 100, d["over"] / 100,
                          d["peak"] / 100, d["back"], pw) - 1.0) < 1e-9
        near = _shape(0.98, d["start"] / 100, d["over"] / 100,
                      d["peak"] / 100, d["back"], pw)
        assert abs(near - 1.0) < 0.01, f"{kind}: 끝에서 {near:.4f} 로 멈춥니다"


def test_shape_starts_at_start_scale():
    d = _defaults("overshoot_scale")
    pw = 1 + 3 * d["smooth"] / 100
    assert _shape(0.0, d["start"] / 100, d["over"] / 100,
                  d["peak"] / 100, d["back"], pw) == d["start"] / 100


def test_generated_expression_runs():
    """만들어진 식을 실제로 돌려 본다 — 문법·NaN·정착값.

    파이썬 쪽은 shape() 를 옮겨 적은 사본을 재는 것이라 **식 문자열 자체가
    깨졌는지는 모른다.** 따옴표 하나가 어긋나면 AE 는 「Expression Disabled」
    라고만 하고 이유를 안 알려주므로, node 로 미리 돌려 본다.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("node 없음")
    r = subprocess.run([node, str(Path(__file__).parent / "check_motion_expr.js")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_bounce_actually_bounces():
    """되돌림이 있으면 정점 뒤에 부호가 여러 번 바뀌어야 한다."""
    d = _defaults("bounce_scale")
    pw = 1 + 3 * d["smooth"] / 100
    ys = [_shape(i / 60, d["start"] / 100, d["over"] / 100,
                 d["peak"] / 100, d["back"], pw) for i in range(61)]
    crossings = sum(1 for a, b in zip(ys, ys[1:])
                    if (a - 1) * (b - 1) < 0)
    assert crossings >= 2, f"되돌림 {d['back']} 인데 교차가 {crossings}번뿐"
