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


def test_ocr_noise_patterns():
    from scripts.qa_hangul import is_noise
    assert is_noise("Walmart엚", 0.5)            # 영어 끝에 한글 한 글자(오독)
    assert is_noise("ㅂㅂㅂㅂ===", 0.5)          # 자모만
    assert is_noise("팔 수 있다니!", 0.3)         # 낮은 신뢰도
    assert not is_noise("회비", 1.0)
    assert not is_noise("코스트코 회원 혜택", 1.0)
