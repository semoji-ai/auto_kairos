import os
import pytest
from backend.research import web_agent

pytestmark = pytest.mark.skipif(
    os.environ.get("AK_RESEARCH_E2E") != "1",
    reason="실제 claude 웹검색 필요 — AK_RESEARCH_E2E=1 로 활성")


def test_web_research_real(tmp_path):
    note = web_agent.run_web_research(
        tmp_path,
        "Use web search to find one verifiable 2026 fact with a source URL. "
        "Report it as a bullet with the URL.")
    assert note and ("http" in note)
