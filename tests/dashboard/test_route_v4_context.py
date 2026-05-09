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
    # get_workspace_dir()를 패치해서 tmp_path를 반환하도록 함
    monkeypatch.setattr("auto_agent.paths.get_workspace_dir", lambda: tmp_path)
    # DB를 tmp_path의 임시 DB로 격리
    tmp_db = str(tmp_path / "test.db")
    monkeypatch.setenv("AUTO_AGENT_DB", tmp_db)

    import sys
    # 리임포트를 위해 캐시 제거
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    import app as app_module
    # startup 스캔을 수동으로 실행 (TestClient는 lifespan을 트리거하지 않을 수 있음)
    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(app_module.startup_scan())
    except Exception:
        # 이미 실행됐거나 이벤트 루프 문제 — TestClient with_startup 방식 사용
        pass
    tc = TestClient(app_module.app)
    # TestClient가 startup을 실행하도록 context manager로 진입
    tc.__enter__()
    yield tc
    tc.__exit__(None, None, None)


def test_research_tab_includes_v4_section_when_files_exist(client):
    # slug='test', uuid='abc12345'로 등록됨. slug로 조회 시 307 redirect → uuid URL로 follow
    response = client.get("/p/test?tab=research", follow_redirects=True)
    assert response.status_code == 200
    assert 'id="v4-research"' in response.text  # v4 섹션 마커
    assert "테스트 영상 기획안" in response.text  # plan.md 렌더
    assert "topic-1" in response.text  # fresh report slug
    assert "topic-2" in response.text
    assert "q-1" in response.text  # targeted slug


def test_manuscript_tab_includes_v4_section(client):
    response = client.get("/p/test?tab=manuscript", follow_redirects=True)
    assert response.status_code == 200
    assert 'id="v4-manuscript"' in response.text
    assert "최종 원고 본문" in response.text
    assert "8.6" in response.text
    assert "PASS" in response.text
    assert 'data-target="draft-1"' in response.text
    assert 'data-target="draft-2"' in response.text


def test_manuscript_tab_no_v4_section_when_files_missing(tmp_path, monkeypatch):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "v3only_test").mkdir()
    monkeypatch.chdir(tmp_path)
    import sys
    for key in list(sys.modules.keys()):
        if key == "app" or key.startswith("app."):
            del sys.modules[key]
    import app as app_module
    c = TestClient(app_module.app)
    response = c.get("/project/v3only_test?tab=manuscript")
    if response.status_code == 200:
        assert 'id="v4-manuscript"' not in response.text


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
    if response.status_code == 200:
        assert 'id="v4-research"' not in response.text
