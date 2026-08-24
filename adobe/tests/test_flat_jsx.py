from pathlib import Path

from conftest import es5_code

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
JSX = PANEL / "jsx" / "build_scene.jsx"


def _src():
    return JSX.read_text(encoding="utf-8")


def test_no_per_scene_comp():
    """씬마다 컴프를 만들지 않는다 — 평면 컴프 하나."""
    src = _src()
    assert "proj.items.addComp" in src            # Final은 만든다
    assert src.count("proj.items.addComp") == 1   # 그 한 번뿐


def test_flat_helpers_exist():
    src = _src()
    for fn in ("function akFindOrMakeComp", "function akSnapshot",
               "function akAddedSince", "function akGroupAnchor",
               "function buildSceneGroup"):
        assert fn in src


def test_guide_null_created_and_named():
    src = _src()
    assert 's.prefix + "가이드"' in src
    assert "addNull" in src


def test_camera_targets_guide():
    """카메라는 가이드 널을 잡는다 — 씬 컴프 레이어가 아니다."""
    src = _src()
    assert "applyCamera(guide, s.camera, t0)" in src
    assert "fc.layers.add(comps[" not in src


def test_camera_is_baked_keyframes():
    """jsx는 카메라 좌표를 계산하지 않는다 — 매니페스트가 구운 키를 찍기만 한다."""
    src = _src()
    assert "cam.type" not in src                      # 구형 type 분기 제거
    assert "k.scale" in src and "k.position" in src
    assert "function akCamEase" in src
    # 70:30 기본 이징 — 카메라가 툭 출발하고 툭 멈추면 싸구려로 보인다
    assert "70" in src and "30" in src
    assert "nearestKeyIndex" in src


def test_layers_use_baked_coords_only():
    """jsx가 채움 스케일을 계산하지 않는다 — 좌표는 매니페스트가 굽는다."""
    src = _src()
    assert "Math.max(W / sw, H / sh)" not in src
    assert "layer.position" in src and "layer.scale" in src


def test_scene_time_applied():
    src = _src()
    assert "inPoint" in src and "outPoint" in src
    assert "startTime" in src            # 오디오


def test_bob_null_stays_in_group():
    """까딱까딱 널은 이름에 접두사가 붙고 레이어 바로 아래로 옮겨진다."""
    src = _src()
    assert "moveAfter" in src
    assert '"_피벗"' in src


def test_target_comp_is_final():
    src = _src()
    assert '"Final"' in src
    assert "app.project.activeItem" not in src


def test_no_skip_final():
    assert "skipFinal" not in _src()


def test_es5_only():
    src = _src()
    src = es5_code(src)
    assert "=>" not in src
    assert "const " not in src and "let " not in src
    assert "`" not in src


def test_layout_group_tagged():
    """레이아웃 씬이 만든 셰이프·텍스트도 접두사가 붙고 가이드에 묶인다."""
    src = _src()
    assert "function akTagGroup" in src
    assert "akTagGroup(comp" in src


def test_layout_image_uses_image_fit():
    """레이아웃 씬의 배경 이미지도 구운 좌표를 쓴다."""
    src = _src()
    assert "s.imageFit" in src
    assert "Math.max(W / isw, H / ish)" not in src


def test_map_overlay_still_called():
    src = _src()
    assert "renderMapOverlay" in src


def test_place_on_timeline_removed():
    """씬 컴프를 얹던 스크립트는 평면에서 성립하지 않는다."""
    assert not (PANEL / "jsx" / "place_on_timeline.jsx").exists()
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert "place_on_timeline.jsx" not in html
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "akPlaceOnTimeline" not in js


def test_rebuild_never_deletes_old_layers():
    """다시 빌드해도 **옛 레이어를 지우지 않는다.** 위에 얹고, 얹었다고 말한다.

    전에는 `akRemoveSceneGroup` 으로 옛 그룹을 지우고 다시 넣었다. 그 방식은
    손으로 고친 것까지 함께 지운다 — 애프터이펙트에서 다듬어 놓은 씬이 재빌드
    한 번에 사라진다. 지우는 것은 되돌릴 수 없고 쌓이는 것은 되돌릴 수 있다.

    대신 겹쳤다는 사실을 로그로 알린다 — 모르고 쌓이면 왜 무거운지 알 수 없다.
    """
    src = _src()
    assert "akRemoveSceneGroup" not in src
    assert "akSnapshot(comp)" in src
    assert "akAddedSince(comp, snap)" in src
    assert "장을 얹었습니다" in src


def test_subtitle_moved_above_scene_groups():
    """말자막은 씬 그룹 재배치가 끝난 뒤 항상 컴프 최상단으로 올린다.

    그룹 재배치는 다음 씬 그룹이 있을 때만 그 위로 옮기므로, 부분 빌드나
    마지막 씬의 그룹은 컴프 맨 위에 남는다 — 그 아래로 자막이 깔리면
    씬 그룹의 불투명 배경에 가려 안 보인다."""
    src = _src()
    assert 'name === "말자막"' in src
    assert "moveToBeginning" in src


def test_failed_build_keeps_old_and_rolls_back_the_half():
    """빌드가 실패하면 **옛것은 지키고 만들다 만 것만 되돌린다.**

    이 둘을 함께 해야 한다. 옛것을 지우면 실패했는데 화면이 비고, 만들다 만
    것을 남기면 옛것과 겹쳐 두 벌이 된다. 되돌릴 대상은 이번에 새로 생긴 것
    뿐이므로 개수가 아니라 **찍어 둔 목록과의 차이**로 찾는다.
    """
    src = _src()
    catch_block = src.split("catch (eB)")[1].split("continue;")[0]
    assert "옛 레이어를 그대로 둡니다" in catch_block
    assert "akAddedSince(comp, snap)" in catch_block
    assert ".remove()" in catch_block
