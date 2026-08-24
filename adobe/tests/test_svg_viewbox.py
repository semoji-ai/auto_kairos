"""SVG 창(viewBox)이 그림 좌표를 담는지 — 「벡터화했는데 컴프에 안 보인다」의 뿌리.

한때 SVG 를 선언 크기의 1/10 로 들여오려고 그림을 `<g transform="scale(...)">`
로 감쌌다(좌표를 직접 곱하면 `rgb(245,222,193)` 의 색 값까지 곱해져 무너지기
때문이었다). 렌더러는 그 변환을 따라가지만 **애프터이펙트의 「쉐이프로 펴기」는
따라가지 않는다.** 2048 좌표계의 패스가 77×87 창에 들어가 통째로 창 밖으로
나갔고, 화면에는 배경만 남았다(배경은 펴지 않아 멀쩡했다).

그래서 여기서는 **렌더 결과가 아니라 좌표가 창 안에 있는지**를 본다. 렌더로만
확인하면 그때도 통과했을 검사다 — 실제로 그렇게 통과시켰다.
"""
import re

from backend import vectorize

NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _wrapped(inner_max=2048, declared=87):
    """옛 방식으로 감싼 SVG — 그림은 2048 좌표계, 창은 87."""
    s = declared / inner_max
    return (f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {declared} {declared}" width="{declared}" height="{declared}">'
            f'<g transform="matrix({s:.6g},0,0,{s:.6g},-0,-0)">'
            f'<path fill="rgb(245,222,193)" d="M0 0L{inner_max} 0L{inner_max} {inner_max}Z"/>'
            f'</g></svg>')


def _head(t):
    w = float(re.search(r'\swidth="([\d.]+)"', t).group(1))
    h = float(re.search(r'\sheight="([\d.]+)"', t).group(1))
    return w, h


def test_wrapped_svg_is_unwrapped():
    out, size = vectorize.normalize_svg(_wrapped())
    assert "<g transform=" not in out
    assert size == (2048, 2048)


def test_path_coords_fit_the_canvas():
    """이것이 핵심이다 — 좌표가 창 안에 있어야 AE 가 쉐이프를 제자리에 편다."""
    out, _ = vectorize.normalize_svg(_wrapped())
    w, h = _head(out)
    d = re.search(r'\sd="([^"]+)"', out).group(1)
    assert max(abs(float(x)) for x in NUM.findall(d)) <= max(w, h) * 1.05


def test_colours_survive():
    """좌표를 직접 곱하면 색 값까지 곱해진다 — 그래서 감쌌던 것이다."""
    out, _ = vectorize.normalize_svg(_wrapped())
    assert "rgb(245,222,193)" in out


def test_idempotent():
    """여러 번 돌려도 같아야 한다 — 돌릴 때마다 작아지면 안 된다."""
    a, _ = vectorize.normalize_svg(_wrapped())
    b, _ = vectorize.normalize_svg(a)
    assert a == b


def test_divisor_default_is_one():
    """작게 들여오는 손잡이는 기본으로 꺼 둔다 — 켜면 같은 사고가 난다."""
    assert vectorize.VECTORIZE_DIVISOR == 1


def test_plain_svg_gets_integer_canvas():
    """애프터이펙트 footage 는 정수 픽셀이어야 한다(179.2 는 통째로 안 들어왔다)."""
    src = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 179.2 102.4" '
           'width="179.2" height="102.4"><path d="M0 0L10 10Z"/></svg>')
    out, size = vectorize.normalize_svg(src)
    assert size == (179, 102)
    w, h = _head(out)
    assert w == int(w) and h == int(h)
