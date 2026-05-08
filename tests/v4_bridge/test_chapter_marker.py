"""chapter_marker 테스트.

unit 테스트: _validate_substring 직접 검증 (LLM 호출 없음)
integration 테스트: 실제 insert_markers 호출 (@pytest.mark.integration)
"""
import json
import textwrap
from pathlib import Path

import pytest

from auto_agent.modules.v4_bridge.chapter_marker import _validate_substring, insert_markers


# ── fixtures ──────────────────────────────────────────────────────────────────

FIXTURE_DIR = Path(__file__).parent / "fixtures"
MANUSCRIPT = (FIXTURE_DIR / "final_manuscript.md").read_text(encoding="utf-8")

OUTLINE_2CH = {
    "chapters": [
        {"id": "ch1", "title": "균일가의 비밀", "summary": "다이소 가격 정책과 직매입 전략"},
        {"id": "ch2", "title": "회전율의 마법", "summary": "진열 교체와 효율 경영"},
    ]
}


# ── unit tests: _validate_substring ───────────────────────────────────────────

class TestValidateSubstring:
    def test_passes_with_only_markers_added(self):
        """마커만 추가된 경우 통과."""
        original = "다이소가 1500원짜리 물건을 팝니다.\n하루 세 번 진열을 바꿉니다."
        marked = (
            "# Ch 1. 균일가의 비밀\n\n"
            "다이소가 1500원짜리 물건을 팝니다.\n"
            "\n---\n\n"
            "# Ch 2. 회전율\n\n"
            "하루 세 번 진열을 바꿉니다."
        )
        _validate_substring(original, marked)  # 예외 없어야 함

    def test_passes_with_char_comment(self):
        """<!-- chars: N --> 주석 포함해도 통과."""
        original = "원본 텍스트입니다."
        marked = "# Ch 1. 제목\n\n원본 텍스트입니다.\n<!-- chars: 9 -->"
        _validate_substring(original, marked)

    def test_fails_when_narration_changed(self):
        """narration 본문이 변경되면 ValueError."""
        original = "다이소가 1500원짜리 물건을 팝니다."
        marked = "# Ch 1. 제목\n\n다이소가 2000원짜리 물건을 팝니다."  # 변경됨
        with pytest.raises(ValueError, match="narration을 변경"):
            _validate_substring(original, marked)

    def test_fails_when_sentence_deleted(self):
        """원본 문장이 통째로 삭제되면 ValueError."""
        original = "첫 번째 문장.\n두 번째 문장."
        marked = "# Ch 1. 제목\n\n첫 번째 문장."  # 두 번째 삭제됨
        with pytest.raises(ValueError):
            _validate_substring(original, marked)

    def test_handles_extra_whitespace(self):
        """공백 정규화 후 비교 — 줄바꿈/공백 차이는 허용."""
        original = "문장 하나.\n\n문장 둘."
        # 마커 사이에 빈 줄이 추가되어도 norm() 후에는 같아야 함
        marked = "# Ch 1. 제목\n\n문장 하나.\n\n\n---\n\n# Ch 2. 제목\n\n문장 둘."
        _validate_substring(original, marked)

    def test_full_fixture_passes(self):
        """fixtures/final_manuscript.md 전문이 마커 추가된 버전에 포함되어야 함."""
        marked = (
            "# Ch 1. 균일가의 비밀\n\n"
            + MANUSCRIPT
        )
        _validate_substring(MANUSCRIPT, marked)


# ── integration tests ──────────────────────────────────────────────────────────

@pytest.mark.integration
def test_insert_markers_integration(tmp_path):
    """실제 Claude CLI를 호출해 마커 삽입 결과를 검증.

    실행: pytest tests/v4_bridge/test_chapter_marker.py -v -m integration
    """
    marked = insert_markers(MANUSCRIPT, OUTLINE_2CH, tmp_path)

    # 챕터 헤더 존재 확인
    assert "# Ch 1." in marked, "챕터 1 헤더 없음"
    assert "# Ch 2." in marked, "챕터 2 헤더 없음"

    # 씬 구분선 존재 확인
    assert "---" in marked, "씬 구분선(---) 없음"

    # narration substring 보존 확인 (validate는 insert_markers 내부에서도 호출됨)
    _validate_substring(MANUSCRIPT, marked)
