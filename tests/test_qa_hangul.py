import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scripts.qa_hangul import is_problem


def test_brand_only_text_is_allowed():
    brands = ["롯데마트", "이마트", "홈플러스"]
    assert not is_problem("롯데마트", brands)
    assert not is_problem("이마트 홈플러스", brands)
    assert not is_problem("Hello", brands)
    assert is_problem("이마트 매출", brands)
    assert is_problem("가격", brands)
