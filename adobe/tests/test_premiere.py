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
