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


# ── 「벡터화한 SVG 가 컴프에 안 보인다」— jsx 쪽 3겹 ────────────────────

def test_import_rereads_when_file_changed():
    """파일이 바뀌면 다시 읽는다.

    애프터이펙트는 들여온 시점의 파싱을 쥐고 있다. 이름만 같으면 재사용하도록
    두었더니, 디스크의 SVG 를 고쳐도 프로젝트 안의 옛 것이 계속 얹혔다 —
    창을 고쳤는데 내보내기 로그에 여전히 옛 크기가 찍혔다.
    """
    src = _src()
    assert "akmod=" in src                     # 수정 시각 도장
    assert "f.modified.getTime()" in src
    assert ".replace(f)" in src                # 푸티지는 자리에서 갈아 끼운다
    assert "(구판)" in src                      # 컴프는 비켜 놓고 다시 읽는다


def test_import_fallback_matches_by_name():
    """폴백이 이름 맞는 것만 새 항목으로 인정한다.

    「새 항목은 목록 끝에 있겠지」로 끝에서부터 훑었는데, 프로젝트 항목은
    이름순으로 꽂힌다. 끝에 있던 사람이 붙여 둔 `Untitled-1.ai` 를 집어
    병 자리에 다섯 번 얹었다.
    """
    src = _src()
    seg = src.split("if (!foot) {")[1].split("}")[0]
    assert "f.name" in seg or "want" in seg
    assert "var want = f.name" in src


def test_span_also_stretches_children():
    """널을 펼 때 붙어 있는 자식도 함께 편다.

    페어런팅은 위치만 따라오지 시간은 따라오지 않는다. SVG 는 1프레임짜리
    컴프로 들어오고 `copyToComp` 는 그 구간을 그대로 가져오므로, 널만 펴면
    꺼낸 쉐이프가 타임라인 맨 앞 1프레임에 눌러앉는다.
    """
    src = _src()
    span = src.split("function akSpan(")[1].split("\n    }")[0]
    assert "cl.parent !== il" in span
    assert "cl.outPoint = t1" in span


def test_video_image_layers_all_imported_in_order():
    """셋을 다 올린다 — 아래부터 **그림 → 레이어 → 영상**.

    한때 영상이 있으면 그림·레이어를 건너뛰게 했는데, 그러면 애프터이펙트에서
    고를 수가 없다. 영상을 쓰다가 한 컷만 레이어로 다시 짜는 일이 있고, 그때
    레이어가 없으면 다시 조립해야 한다. 눈 아이콘으로 고르게 한다.

    순서가 핵심이다 — `comp.layers.add` 는 맨 위에 넣으므로 **나중에 넣은 것이
    위**다. 그림을 나중에 넣으면 레이어를 덮어 버린다.
    """
    src = _src()
    body = src.split("function buildSceneGroup(")[1]
    i_bg = body.index("addBgSolid(comp, W, H, TK.colors.bgRgb)")
    i_img = body.index("if (s.image) {")
    i_lay = body.index("if (s.layers && s.layers.length) {")
    i_vid = body.index("if (s.video) {")
    i_txt = body.index("renderLayout(proj, comp, s, W, H)")
    # 아래 → 위: 판바탕 → 그림 → 레이어 → 영상 → 레이아웃 글자
    assert i_bg < i_img < i_lay < i_vid < i_txt
    assert "didVideo" not in body                  # 건너뛰기 게이트는 없앴다


def test_layout_text_is_on_top():
    """레이아웃 글자가 영상·레이어 위에 온다.

    전에는 레이아웃을 맨 처음 그려서, 나중에 얹은 영상이 글자를 통째로 덮었다.
    화면에 하려는 말이 안 뜨는 것이 가장 나쁜 어긋남이다.
    """
    body = _src().split("function buildSceneGroup(")[1]
    assert body.index("if (s.video) {") < body.index("renderLayout(proj, comp, s, W, H)")


def test_scene_image_is_added_once():
    """씬 그림을 까는 자리는 한 곳이다 — 두 곳에서 까서 PNG 가 두 장 들어왔다."""
    src = _src()
    rl = src.split("function renderLayout(")[1].split("\n    function ")[0]
    assert "s.image" not in rl                    # 레이아웃 렌더러는 그림을 안 깐다
    assert "importFile" not in rl
    body = src.split("function buildSceneGroup(")[1]
    assert body.count("if (s.image) {") == 1


def test_short_video_holds_last_frame():
    """영상이 씬보다 짧으면 마지막 프레임을 붙든다 — 그냥 두면 뒤가 빈다."""
    src = _src()
    seg = src.split("if (s.video) {")[1].split("\n        if (!didVideo")[0]
    assert "timeRemapEnabled" in seg
    assert "Time Remap" in seg
    assert "vl.outPoint = t1" in seg          # 길면 잘라 낸다


def test_imports_go_into_folders():
    """프로젝트 창을 종류별로 나눈다.

    한 편을 통째로 넣으면 항목이 300개를 넘는다(그림 142 · 레이어 148 ·
    영상 29 · 음성 46). 평평하게 쏟아지면 무엇이 무엇인지 알 수 없다.

        auto_kairos/
          씬 이미지/
          레이어/ S100 · S101 …     ← 148장이 한 폴더면 못 찾는다
          영상/
          음성/
    """
    src = _src()
    assert 'var AK_BIN = "auto_kairos";' in src
    assert "function akFolder(" in src and "function akPutIn(" in src
    for kind in ("씬 이미지", "레이어", "영상", "음성"):
        assert 'akFolder(proj, [AK_BIN, "%s"' % kind in src, kind
    # 레이어는 씬별 하위 폴더
    assert '(s.prefix || "S00_").replace(/_$/, "")' in src


def test_folder_lookup_is_not_cached():
    """폴더 참조를 들고 있지 않는다.

    항목을 지우면 색인이 밀려 들고 있던 FolderItem 이 무효가 된다 — 전에
    그것 때문에 MOGRT 찍기가 두 번째부터 「FolderItem is not of the correct
    type」 으로 죽었다. 매번 찾는다.
    """
    src = _src()
    seg = src.split("function akFolder(")[1].split("\n    }")[0]
    assert "proj.items.addFolder" in seg
    assert "for (var k = 1; k <= proj.numItems" in seg      # 매번 훑는다
    # id 로 견준다 — 객체 비교는 어긋나는 판이 있다
    assert "akSameItem" in seg


def test_putting_in_a_folder_never_stops_the_build():
    """정리는 덤이다 — 폴더에 못 넣어도 조립은 계속한다."""
    seg = _src().split("function akPutIn(")[1].split("\n    }")[0]
    assert "try {" in seg and "catch" in seg
