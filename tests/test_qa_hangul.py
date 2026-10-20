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
    assert is_noise("COSTC유", 0.3)
    assert not is_noise("회비", 1.0)
    assert not is_noise("코스트코 회원 혜택", 1.0)


def test_real_short_hangul_is_never_noise():
    from scripts.qa_hangul import is_noise
    assert not is_noise("1998년", 1.0)          # 숫자+단위(완성형 1자)
    assert not is_noise("6.5조", 0.5)
    assert not is_noise("상", 1.0)              # 신뢰도 1은 잡음으로 치지 않음
    assert not is_noise("구독", 0.3)            # 낮은 신뢰도라도 한글 2자 이상은 사람이 본다
