from sg.graph import walk, reach_items


def L(i, src, a, b, st=0.0, sx=100, en=True, au=False, tr=False, matte=False, name=""):
    return {"i": i, "name": name, "src": src, "in": a, "out": b, "st": st, "sx": sx,
            "en": en, "au": au, "vid": True, "tr": tr, "matte": matte}


G = {"comps": {
        "1": {"name": "ROOT", "dur": 100, "layers": [L(1, 2, 10, 20, st=10), L(2, None, 0, 5), L(3, 2, 50, 60, st=45, sx=200), L(4, 9, 0, 3, en=False)]},
        "2": {"name": "PRE", "dur": 30, "layers": [L(1, 7, 0, 4), L(2, None, 2, 8)]}},
     "items": {"7": {"name": "pic.png", "file": "/x/pic.png", "missing": False},
               "9": {"name": "off.png", "file": "/x/off.png", "missing": False}}}


def spans(res, comp_id, layer):
    return [r["spans"] for r in res if r["comp_id"] == comp_id and r["layer"] == layer][0]


def test_walk_maps_child_times_to_root():
    res = walk(G, "1", 0, 100)
    assert spans(res, "1", 2) == [[0, 5]]               # 텍스트(소스 없음)도 포함
    # PRE 레이어2(2~8): 첫 사용 st=10 → 12~18, 두 번째 사용 st=45, sx=2 → 49~61 이지만 레이어 50~60으로 잘림
    assert spans(res, "2", 2) == [[12, 18], [50, 60]]


def test_disabled_layers_are_skipped():
    res = walk(G, "1", 0, 100)
    assert not [r for r in res if r["src"] == 9]


def test_reach_items():
    r = reach_items(G, "1", 0, 100)
    assert set(r) == {"7"}
    assert r["7"]["spans"] == [[10, 14], [50, 53]]


def test_walk_records_local_to_root_transform_per_occurrence():
    res = walk(G, "1", 0, 100)
    occ = [r["occ"] for r in res if r["comp_id"] == "2" and r["layer"] == 1][0]
    # 첫 사용: 루트 = 로컬*1 + 10, 두 번째 사용: 루트 = 로컬*2 + 45
    assert sorted((o["k"], o["off"]) for o in occ) == [(1.0, 10.0), (2.0, 45.0)]
