from sg.budget import char_budget, fit_status


def test_char_budget_rounds_down():
    assert char_budget(4.0, 14) == 56
    assert char_budget(0.5, 14) == 7


def test_fit_status_bounds_are_inclusive():
    assert fit_status(4.0, 3.0) == "ok"        # 0.75
    assert fit_status(4.0, 5.4) == "ok"        # 1.35
    assert fit_status(4.0, 2.9) == "short"
    assert fit_status(4.0, 5.5) == "long"
