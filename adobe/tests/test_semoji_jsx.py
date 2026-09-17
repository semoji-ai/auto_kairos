from pathlib import Path

from conftest import es5_code

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
    src = es5_code(src)
    assert "=>" not in src and "const " not in src and "let " not in src and "`" not in src


TOOLS = PANEL / "jsx" / "tools.jsx"


def test_tools_jsx_exists_and_functions():
    src = TOOLS.read_text(encoding="utf-8")
    for fn in ("function akImportSrt", "function akInsertNull", "function akApplyPreset"):
        assert fn in src


def test_tools_srt_per_cue_layers():
    """SRT도 큐마다 텍스트 레이어 하나씩 — SEMOJI TOOL 자막작업 방식.

    줄별로 고치고 움직일 수 있는 것이 목적이다. 예전에 577레이어 사태로
    단일 키프레임 방식으로 갔다가, 줄별 편집이 안 되어 되돌렸다 — 대신
    shy로 접고, 다시 넣을 때 이전 결과(단일 레이어·줄별 레이어)를 정리한다."""
    src = TOOLS.read_text(encoding="utf-8")
    assert '"가져온자막"' in src                     # 예전 단일 레이어 정리 대상
    assert "akIsSrtLayerName" in src                 # 줄별 레이어 판별 + 재실행 정리
    assert "layers.addText" in src
    assert ".shy = true" in src                      # 타임라인 무게 완화
    assert "setValueAtTime" not in src.split("function akImportSrt")[1].split("\nfunction ")[0]


def test_tools_insert_null_preserves_parent():
    src = TOOLS.read_text(encoding="utf-8")
    body = src.split("function akInsertNull")[1].split("\nfunction ")[0]
    assert "parent" in body and "addNull" in body and "moveAfter" in body


def test_tools_es5_only():
    src = TOOLS.read_text(encoding="utf-8")
    src = es5_code(src)
    assert "=>" not in src and "const " not in src and "let " not in src and "`" not in src


def test_panel_tools_section():
    html = (PANEL / "index.html").read_text(encoding="utf-8")
    assert 'id="toolsSection"' in html
    js = (PANEL / "js" / "storyboard.js").read_text(encoding="utf-8")
    assert "akImportSrt" in js and "akInsertNull" in js and "akApplyPreset" in js
    assert "/api/tools/srt-parse" in js
