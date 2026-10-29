"""음성 인식 대조용 정규화: 영어는 단어, 중국어(cjk)는 번체→간체 후 글자 단위(영문·숫자 묶음은 하나)."""
import re


def tokens(s, cjk=False):
    if not cjk:
        return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()
    from opencc import OpenCC
    s = OpenCC("t2s").convert(s).lower()
    return re.findall(r"[a-z0-9]+|[一-鿿]", s)
