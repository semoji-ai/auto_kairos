from pathlib import Path

PANEL = Path(__file__).resolve().parents[1] / "cep" / "com.autokairos.pd"
JSX = PANEL / "jsx" / "build_scene.jsx"


def _src():
    return JSX.read_text(encoding="utf-8")


def test_stamp_branch():
    src = _src()
    assert 'mv.type === "stamp"' in src
    # 5프레임 내리찍기 — 스케일 시작 배율은 amount(기본 300)
    assert "300" in src


def test_wiggle_branch():
    src = _src()
    assert 'mv.type === "wiggle"' in src
    assert "wiggle(" in src


def test_source_caption_function():
    src = _src()
    assert "function addSourceCaption" in src
    assert '"출처"' in src and '"출처판"' in src


def test_source_caption_not_parented_to_guide():
    """출처 자막은 카메라 줌에 딸려가면 안 된다 — 가이드 미페어런팅.
    addSourceCaption 함수 본문에 guide/parent 참조가 없어야 한다."""
    src = _src()
    body = src.split("function addSourceCaption")[1].split("\n    function ")[0]
    assert "parent = guide" not in body
    assert "plate.parent" not in body
    assert "guide" not in body


def test_source_caption_called_in_build():
    src = _src()
    assert "addSourceCaption(comp, s" in src


def test_es5_only():
    src = _src()
    assert "=>" not in src and "const " not in src and "let " not in src and "`" not in src


TOOLS = PANEL / "jsx" / "tools.jsx"


def test_tools_jsx_exists_and_functions():
    src = TOOLS.read_text(encoding="utf-8")
    for fn in ("function akImportSrt", "function akInsertNull", "function akApplyPreset"):
        assert fn in src


def test_tools_srt_single_text_layer():
    """SRT도 1레이어 + Source Text 키프레임 — 줄별 레이어 금지(577레이어 사태의 교훈)."""
    src = TOOLS.read_text(encoding="utf-8")
    assert '"가져온자막"' in src
    assert "setValueAtTime" in src
    # 큐마다 addText를 부르는 구조가 아니어야 한다
    assert src.count("layers.addText") == 1


def test_tools_insert_null_preserves_parent():
    src = TOOLS.read_text(encoding="utf-8")
    body = src.split("function akInsertNull")[1].split("\nfunction ")[0]
    assert "parent" in body and "addNull" in body and "moveAfter" in body


def test_tools_es5_only():
    src = TOOLS.read_text(encoding="utf-8")
    assert "=>" not in src and "const " not in src and "let " not in src and "`" not in src


def test_panel_tools_section():
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert 'id="toolsSection"' in html
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "akImportSrt" in js and "akInsertNull" in js and "akApplyPreset" in js
    assert "/api/tools/srt-parse" in js
