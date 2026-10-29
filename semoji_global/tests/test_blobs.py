import numpy as np
from sg.blobs import track_blobs


def frame(points):
    a = np.zeros((200, 300, 4), np.uint8)
    for x, y in points:
        a[y - 8:y + 9, x - 8:x + 9] = (40, 40, 160, 255)   # 17px: 중심이 정확히 (x, y)
    return a


def test_two_blobs_tracked_across_motion():
    fr = [frame([(50, 50), (200, 100)]), frame([(55, 52), (196, 104)]), frame([(60, 54), (192, 108)])]
    tr = track_blobs(fr)
    assert len(tr) == 2
    a = [s for s in tr if s[0]["cx"] < 100][0]
    assert [round(s["cx"]) for s in a] == [50, 55, 60]


def test_blob_disappears_and_returns_on_same_track():
    fr = [frame([(50, 50)]), frame([]), frame([(53, 51)])]
    tr = track_blobs(fr)
    assert len(tr) == 1 and tr[0][1] is None and round(tr[0][2]["cx"]) == 53
