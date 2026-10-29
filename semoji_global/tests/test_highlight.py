from sg.highlight import is_sweep, bar_span, to_local, ko_span, fit_bar

BAR = {"anchor": [0.0, 5.4], "pos": [286.3, 282.9], "scale": [0, 613],
       "keys": [["ADBE Scale", 1.0, [0, 613, 100]], ["ADBE Scale", 1.6, [612, 613, 100]]]}
TXT = {"anchor": [146.94, 57.92], "pos": [952.37, 520.42], "scale": [613, 613]}


def test_is_sweep_detects_scale_x_growing_from_zero():
    assert is_sweep(BAR)
    assert not is_sweep({**BAR, "keys": [["ADBE Scale", 1.0, [100, 100, 100]], ["ADBE Scale", 2.0, [120, 120, 100]]]})


def test_bar_span_uses_final_scale():
    x0, x1, y0, y1 = bar_span(BAR, 219, 11)
    assert abs(x0 - 286.3) < 1e-6 and abs(x1 - (286.3 + 219 * 6.12)) < 1e-6
    assert abs((y0 + y1) / 2 - 282.9 - (11 / 2 - 5.4) * 6.13) < 1e-6


def test_to_local_inverts_text_layer_transform():
    u, v = to_local(952.37, 520.42, TXT)
    assert abs(u - 146.94) < 1e-6 and abs(v - 57.92) < 1e-6


def test_ko_span_by_horizontal_fraction():
    # 줄 상자 x 10~110(글자 10개), 강조 x 10~45 → 앞 3.5글자 → [0, 4)
    assert ko_span("가나다라마바사아자차", 10, 110, 10, 45) == (0, 4)


def test_fit_bar_moves_left_edge_and_sets_final_width():
    pos_x, sx = fit_bar(BAR, 219, 500.0, 900.0)
    assert abs(pos_x - 500.0) < 1e-6 and abs(219 * sx / 100 - 400.0) < 1e-6
