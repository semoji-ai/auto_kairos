"""image_generate._infer_web_search 단위 테스트."""
import pytest
from datetime import datetime
from auto_agent.tools.image_generate import _infer_web_search


CURRENT_YEAR = str(datetime.now().year)
PREV_YEAR = str(datetime.now().year - 1)


def _scene(prompt: str) -> dict:
    return {"imageAsset": {"prompt": prompt}}


class TestInferWebSearch:
    def test_search_fallback_always_true(self):
        """search→generate fallback은 항상 True."""
        assert _infer_web_search(_scene("순수 일러스트 배경"), is_search_fallback=True) is True

    def test_current_year_in_prompt_true(self):
        """현재 연도 포함 프롬프트 → True."""
        assert _infer_web_search(_scene(f"{CURRENT_YEAR}년 이란 핵시설 공습 현장"), is_search_fallback=False) is True

    def test_prev_year_in_prompt_true(self):
        """전년도 포함 프롬프트 → True."""
        assert _infer_web_search(_scene(f"{PREV_YEAR}년 우크라이나 전쟁 장면"), is_search_fallback=False) is True

    def test_no_year_no_fallback_false(self):
        """연도 없고 fallback도 아니면 → False."""
        assert _infer_web_search(_scene("만화풍 캐릭터가 숲속을 걷는 장면"), is_search_fallback=False) is False

    def test_empty_prompt_false(self):
        """빈 프롬프트 → False."""
        assert _infer_web_search(_scene(""), is_search_fallback=False) is False

    def test_missing_image_asset_false(self):
        """imageAsset 필드 없음 → False."""
        assert _infer_web_search({}, is_search_fallback=False) is False

    def test_search_fallback_overrides_no_year(self):
        """fallback=True이면 연도 없어도 True."""
        assert _infer_web_search(_scene("데이터 차트 배경"), is_search_fallback=True) is True
