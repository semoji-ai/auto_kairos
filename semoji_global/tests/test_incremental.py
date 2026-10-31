"""부분 렌더 계획: 옛·새 파트 시간표가 같은 기울기인 구간은 옛 렌더를 재사용하고, 나머지만 렌더."""
from sg.incremental import plan_parts

FR = 1 / 29.97


def test_unchanged_part_is_one_reuse():
    a = [[0, 0], [100, 100]]
    p = plan_parts(a, a, dur_new=100, dirty_u=[], margin=0.5)
    assert p == [("reuse", 0.0, 100.0, 0.0)]


def test_stretched_segment_is_rendered_and_rest_shifted():
    old = [[0, 0], [10, 10], [20, 20], [100, 100]]
    new = [[0, 0], [10, 10], [20, 25], [100, 105]]          # 10~20초 구간만 1.5배로 늘어남
    p = plan_parts(old, new, dur_new=105, dirty_u=[], margin=0.5)
    assert p[0][0] == "reuse" and p[0][1] == 0.0 and abs(p[0][2] - 9.5) < FR
    assert p[1][0] == "render" and abs(p[1][1] - 9.5) < FR and abs(p[1][2] - 25.5) < FR
    kind, n0, n1, o0 = p[2]
    assert kind == "reuse" and abs(n0 - 25.5) < FR and abs(o0 - 20.5) < FR and n1 == 105.0   # 뒤는 5초 밀린 채 재사용


def test_dirty_source_range_forces_render_even_with_same_timing():
    a = [[0, 0], [100, 100]]
    p = plan_parts(a, a, dur_new=100, dirty_u=[(40, 42)], margin=0.5)
    assert [x[0] for x in p] == ["reuse", "render", "reuse"]
    assert abs(p[1][1] - 39.5) < FR and abs(p[1][2] - 42.5) < FR


def test_close_render_ranges_merge():
    a = [[0, 0], [100, 100]]
    p = plan_parts(a, a, dur_new=100, dirty_u=[(10, 11), (12, 13)], margin=0.5)
    assert [x[0] for x in p] == ["reuse", "render", "reuse"]


def test_boundaries_snap_to_frames():
    old = [[0, 0], [10, 10], [20, 20], [100, 100]]
    new = [[0, 0], [10, 10], [20, 23.3], [100, 103.3]]
    for x in plan_parts(old, new, dur_new=103.3, dirty_u=[], margin=0.5):
        for t in x[1:3]:
            if t not in (0.0, 103.3):
                assert abs(t / FR - round(t / FR)) < 1e-6


def test_changed_range_expands_to_whole_scene_layer():
    old = [[0, 0], [10, 10], [20, 20], [100, 100]]
    new = [[0, 0], [10, 10], [20, 25], [100, 105]]
    # 5~30초에 걸친 장면 레이어(줌 같은 키 애니메이션)는 가운데만 바뀌어도 전체가 달라진다 → 장면 전체를 렌더
    p = plan_parts(old, new, dur_new=105, dirty_u=[], margin=0.5, scenes_u=[(5, 30), (60, 70)])
    r = [x for x in p if x[0] == "render"]
    assert len(r) == 1 and abs(r[0][1] - 4.5) < FR and abs(r[0][2] - 35.5) < FR
