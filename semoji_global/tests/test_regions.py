import numpy as np
from sg.regions import static_from, appear_time


def test_static_from_finds_when_region_stops_changing():
    fr = [np.full((50, 50, 3), v, np.uint8) for v in (0, 40, 80, 120, 120, 120)]
    assert static_from(fr, [10, 10, 20, 20], fps=1.0) == 3.0


def test_appear_time_detects_first_difference_from_background():
    bg = (250, 250, 250)
    fr = [np.full((50, 50, 3), bg, np.uint8) for _ in range(5)]
    fr[3][10:30, 10:30] = (120, 120, 120); fr[4][10:30, 10:30] = (120, 120, 120)
    assert appear_time(fr, [10, 10, 20, 20], bg, fps=1.0) == 3.0
