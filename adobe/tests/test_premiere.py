"""프리미어 1단계 — 시퀀스 조립.

**같은 매니페스트를 읽는다.** 씬마다 `start`·`duration` 이 이미 프레임 단위로
구워져 있으므로(timeline.py) 프리미어 쪽은 계산하지 않고 그 자리에 놓기만 한다.

프리미어는 쉐이프·텍스트 레이어를 스크립트로 만들 수 없어 연출을 그대로 옮길
수 없다. 그래서 1단계는 **거친 편집본을 까는 데까지**만 한다 — 영상(없으면
그림)·음성·씬 마커. 연출은 애프터이펙트가 맡는다.
"""
from pathlib import Path

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"


def _seq():
    return (PANEL / "jsx" / "build_sequence.jsx").read_text(encoding="utf-8")


def test_premiere_registered_as_host():
    x = (PANEL / "CSXS" / "manifest.xml").read_text(encoding="utf-8")
    assert 'Host Name="PPRO"' in x
    assert 'Host Name="AEFT"' in x          # 둘 다 뜬다


def test_sequence_script_is_es5():
    """ExtendScript 는 화살표 함수·템플릿 리터럴을 못 읽는다."""
    from conftest import es5_code
    src = es5_code(_seq())
    for bad in ("=>", "`", "const ", "let "):
        assert bad not in src, bad


def test_sequence_uses_manifest_timings():
    """자리는 매니페스트가 정한다 — 여기서 다시 계산하지 않는다."""
    src = _seq()
    assert "s.start" in src and "s.duration" in src
    assert "overwriteClip" in src


def test_image_and_video_on_separate_tracks():
    """V1 그림 · V2 영상 — **둘 다 깐다.** 애프터이펙트와 같은 쌓임이다.

    처음에는 「영상이 있으면 그림은 건너뛴다」로 했는데, 그러면 영상이 있는
    29씬(99번부터)에 그림이 아예 안 깔린다. 편집하다 한 컷만 정지로 되돌리고
    싶을 때 밑에 그림이 없으면 다시 조립해야 한다.
    """
    src = _seq()
    body = src.split("function akBuildSequence(")[1]
    assert 'akTrack(seq, "video", 0' in body and 'akTrack(seq, "video", 1' in body
    assert body.index("if (s.image) {") < body.index("if (s.video) {")   # 그림이 아래
    assert "s.video || s.image" not in body        # 둘 중 하나 고르지 않는다
    assert "쓸 그림도 영상도 없습니다" in src


def test_missing_track_is_created():
    """새 시퀀스는 V1·A1 뿐이다. 없는 트랙을 집으면 그 자리부터 조용히 빈다."""
    src = _seq()
    assert "function akTrack(" in src
    assert "addTracks(1)" in src


def test_still_duration_is_extended_before_placing():
    """스틸 기본 길이(보통 5초)보다 긴 씬이 있다 — 놓기 전에 늘린다."""
    body = _seq().split("function akPlace(")[1]
    assert "setOutPoint(" in body
    assert body.index("setOutPoint(") < body.index("overwriteClip(")


def test_audio_and_markers():
    src = _seq()
    assert 'akTrack(seq, "audio", 0' in src
    assert "markers.createMarker" in src


def test_import_is_deduped():
    """같은 파일을 두 번 들여오지 않는다 — 142씬이면 프로젝트 창이 사본으로 찬다."""
    src = _seq()
    assert "function akImportOnce(" in src
    assert "akFindItem(bin" in src


def test_rebuild_clears_tracks_not_assets():
    """다시 깔 때 트랙만 비운다 — 자산까지 지우면 사람이 넣어 둔 것이 날아간다."""
    src = _seq()
    body = src.split("function akClearTracks(")[1]
    assert "clips[c].remove(false, false)" in body
    assert "deleteAsset" not in body and "rootItem.delete" not in body


def test_panel_branches_by_host():
    """같은 패널, 다른 스크립트. 프리미어에서는 AE 전용 단추를 감춘다."""
    js = (PANEL / "js" / "main.js").read_text(encoding="utf-8")
    assert "function isPremiere()" in js
    assert "build_sequence.jsx" in js and "build_scene.jsx" in js
    assert "function applyHostUI()" in js
    # 버튼만 눌러 보고 안 되는 것이 가장 나쁘다
    for b in ("btnQueueRender", "btnSubtitles", "btnDecompose"):
        assert b in js.split("function applyHostUI()")[1].split("\n}")[0]


# ── MOGRT — 프리미어에서 고칠 수 있게 ──────────────────────────────────

def _mog():
    return (PANEL / "jsx" / "make_mogrt.jsx").read_text(encoding="utf-8")


def test_mogrt_reuses_layouts_jsx():
    """**디자인 소스를 둘로 만들지 않는다.**

    MOGRT 를 손으로 만들면 같은 디자인이 두 벌이 된다 — `layouts.jsx` 한 벌,
    MOGRT 한 벌. 하나를 고치면 갈린다. 그래서 찍을 때도 `akRenderLayout` 을
    부른다. 디자인은 계속 layouts.jsx 하나가 정한다.
    """
    src = _mog()
    assert "akRenderLayout(comp," in src
    # 여기서 직접 레이아웃을 그리면 그 순간 두 벌이 된다
    assert "function akLayout_" not in src


def test_mogrt_exposes_text_color_place_size():
    """글자·색·자리·크기 넷을 다 노출한다.

    색은 Fill 이펙트로 준다 — 텍스트 색은 `Source Text` 안의 TextDocument 에
    들어 있어 따로 노출할 수 없다.
    """
    src = _mog()
    for x in ('"Source Text"', '" 색"', '" 자리"', '" 크기"'):
        assert x in src, x
    assert "ADBE Fill" in src
    assert "addToMotionGraphicsTemplateAs" in src
    assert "canAddToMotionGraphicsTemplate" in src


def test_mogrt_cleans_up_after_itself():
    """사람이 쓰던 프로젝트에 임시 컴프를 남기지 않는다."""
    src = _mog()
    assert "beginUndoGroup" in src and "endUndoGroup" in src
    assert "folder.remove()" in src


def test_mogrt_is_es5():
    from conftest import es5_code
    src = es5_code(_mog())
    for bad in ("=>", "`", "const ", "let "):
        assert bad not in src, bad


def test_mogrt_button_is_ae_only():
    """찍는 쪽은 애프터이펙트다 — 프리미어에서는 감춘다."""
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    js = (PANEL / "js" / "main.js").read_text(encoding="utf-8")
    assert 'id="btnMogrt"' in html
    assert "function makeMogrt()" in js
    assert "btnMogrt" in js.split("function applyHostUI()")[1].split("\n}")[0]


def test_mogrt_folder_is_made_by_backend():
    """폴더는 파이썬이 만든다.

    `Folder.create()` 가 애프터이펙트의 「스크립트가 파일을 쓰고 네트워크에
    접근하도록 허용」 설정에 걸려 permission denied 로 죽었다. 그 설정은 사람이
    켜야 하는 보안 설정이고, 폴더 하나 만들자고 켜게 할 이유가 없다.
    """
    src = _mog()
    assert "d.create()" not in src
    assert "백엔드가 만들어야 합니다" in src
    js = (PANEL / "js" / "main.js").read_text(encoding="utf-8")
    assert "/api/mogrt/prepare" in js
    router = (Path(__file__).resolve().parents[1] / "backend" / "router.py").read_text(encoding="utf-8")
    assert "/api/mogrt/prepare" in router


def test_mogrt_prepare_makes_the_dir(tmp_path):
    from backend.router import handle_request
    from backend.jobs import JobRegistry
    (tmp_path / "p").mkdir()
    code, body = handle_request("POST", "/api/mogrt/prepare", {}, {"project_id": "p"},
                                {"root": tmp_path, "jobs": JobRegistry()})
    assert code == 200
    assert (tmp_path / "p" / "mogrt").is_dir()
    assert body["path"].endswith("mogrt")
