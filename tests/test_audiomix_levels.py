from sg.audiomix import flatten
from tests.test_audiomix import tl


def test_flatten_keeps_each_level_gain_and_keys():
    t = tl()
    t[0]["tracks"][0]["items"][1]["gain_keys"] = [[9.0, 1.0], [10.0, 0.0]]   # 바깥(중첩) 클립 페이드
    p = flatten(t, "M", [2])[1]
    assert [(L["clip_start"], L["clip_in"], L["keys"]) for L in p["levels"]] == [(50.0, 0.0, [[9.0, 1.0], [10.0, 0.0]]), (52.0, 30.0, [])]
    assert [L["gain"] for L in p["levels"]] == [1.0, 0.25]


def test_nested_clip_with_zero_out_uses_its_timeline_length():
    # 실제 프리미어: 중첩 시퀀스 클립은 in/out이 0으로 저장됨 → 보이는 길이 = end - start
    t = tl()
    nest = t[0]["tracks"][0]["items"][1]
    nest["in"], nest["out"] = 0.0, 0.0
    p = flatten(t, "M", [2])
    assert [(x["name"], x["pr_in"], x["pr_out"]) for x in p] == [("a.mp3", 10.0, 20.0), ("b.mp3", 52.0, 58.0)]
