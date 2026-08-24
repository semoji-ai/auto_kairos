"""테스트 공용 도구."""
from __future__ import annotations


def es5_code(src: str) -> str:
    """주석을 걷어낸 코드만 돌려준다 — ES5 검사용.

    ExtendScript 는 화살표 함수·템플릿 리터럴·`const`/`let` 을 못 읽으므로
    jsx 파일에 그것이 있으면 안 된다. 그런데 검사가 **파일 전체를 문자열로
    훑고** 있어서, 한글 주석에 적힌 백틱(``explode``)이나 화살표(`A => B`)까지
    위반으로 잡혔다.

    주석은 ExtendScript 에 아무 영향이 없다. 그것 때문에 규칙을 느슨하게 하면
    진짜 위반까지 놓치므로, 반대로 **볼 것만 남기고** 검사한다.

    문자열 리터럴은 남긴다 — 코드에 실린 값이라 검사 대상이다.
    """
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                j += 2 if src[j] == "\\" else 1
            out.append(src[i:j + 1]); i = j + 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        elif src.startswith("/*", i):
            j = src.find("*/", i)
            i = n if j < 0 else j + 2
        else:
            out.append(c); i += 1
    return "".join(out)
