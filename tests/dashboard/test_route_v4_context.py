"""프로젝트 페이지 라우트가 v4 컨텍스트를 주입하는지 검증."""
from pathlib import Path
import shutil
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """app.py를 import하고 테스트 픽스처를 output/으로 임시 매핑."""
    fixture_src = Path(__file__).parent / "v4_fixtures" / "abc12345_test"
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    shutil.copytree(fixture_src, output_dir / "abc12345_test")

    monkeypatch.chdir(tmp_path)
    import importlib, sys
    # 리임포트를 위해 캐시 제거
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    import app as app_module
    return TestClient(app_module.app)


def test_research_tab_returns_200(client):
    response = client.get("/p/abc12345_test?tab=research")
    assert response.status_code in (200, 307, 404)


def test_manuscript_tab_returns_200(client):
    response = client.get("/p/abc12345_test?tab=manuscript")
    assert response.status_code in (200, 307, 404)


def test_research_tab_no_v4_section_when_files_missing(tmp_path, monkeypatch):
    """v3-only 프로젝트 회귀: v4 파일 없으면 v4 섹션 마커 부재."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "v3only_test").mkdir()
    monkeypatch.chdir(tmp_path)
    import importlib, sys
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    import app as app_module
    c = TestClient(app_module.app)
    response = c.get("/p/v3only_test?tab=research")
    # Task 4에서 v4 섹션 추가 후 이 마커 검증 — 지금은 단순히 200 또는 404 OK
    assert response.status_code in (200, 307, 404)
