"""말자막 줄 나누기 — 세모지 통합보고 §2-1 규칙.

    1. 쉼표·절 경계에서 끊는다. 다음 절 앞부분이 앞 줄 끝에 딸리면 안 된다
       ("둘러보시면, 이 회사가 / 만든…" ✕ → "둘러보시면," / "이 회사가 만든…").
    2. 마지막 조각은 두 어절 이상. 서술어 한 단어만 넘기지 않는다
       ("…성장 방식을 / 선택합니다." ✕).
    3. 목적어는 서술어 줄로 ("~로 몸집을 / 점점 불려" ✕ → "~로 / 몸집을 점점 불려").
    4. 날짜+쉼표로 시작하는 문장은 날짜만 첫 자막 ("1975년," / "작업장은…").
    5. 따옴표·괄호로 묶인 이름은 조사까지 한 줄에 — 묶음 안에서는 끊지 않는다.
    6. 숫자는 원고 표기 그대로 — 어절 안에서는 끊지 않는다("3,500여명").

끊는 자리는 항상 어절 경계(공백)다. 후보마다 점수를 매겨 가장 좋은 자리를 고르고,
남은 부분을 같은 방식으로 다시 나눈다. 단위 테스트: tests/test_subtitle_linebreak.py
"""
from __future__ import annotations

import re

MAX_CHARS = 30
SLACK = 3            # 좋은 경계를 지키려고 한 줄이 이만큼 넘는 것은 허용(감점)

_OPEN = "([{「『“‘《〈"
_CLOSE = ")]}」』”’》〉"
_TOGGLE = "'\""

DATE_LEAD = re.compile(
    r"^((?:\d{1,4}년(?:\s*\d{1,2}월)?(?:\s*\d{1,2}일)?|\d{1,2}월(?:\s*\d{1,2}일)?)"
    r"(?:\s*(?:초|말|봄|여름|가을|겨울|무렵|당시))?),\s+")

_SENT_END = re.compile(r"[.!?…][\"'”’)\]」』]*$")
_CLAUSE_LONG = re.compile(r"(지만|는데|인데|한데|던데|면서|어서|아서|니까|으니|때문에|위해서?|도록|듯이|다가|려고|으며|으면|"
                          r"다면|라면|더라도|라도|거나|든지|더니|자마자|면서도|지만서도)$")
_CLAUSE_SHORT = re.compile(r"[가-힣](고|며|면|자|서)$")
_TOPIC = re.compile(r"[가-힣](은|는|이|가|께서)$")
_ADVERBIAL = re.compile(r"[가-힣](에서|에게|으로|로|와|과|에|까지|부터|보다|처럼|만큼|에는|에서는|으로는|로는)$")
_OBJECT = re.compile(r"[가-힣](을|를)$")
_GENITIVE = re.compile(r"[가-힣]의$")


def _strip_tail_punct(w: str) -> str:
    return w.rstrip("\"'”’)]}」』》〉")


def _protected_spaces(text: str, max_chars: int = MAX_CHARS) -> set[int]:
    """따옴표·괄호 묶음 안의 공백 위치 — 여기서는 끊지 않는다.

    이름·한 호흡 구절('드라이버만 있으면 되는 조립')처럼 한 줄에 들어가는 묶음만 지킨다.
    한 줄을 넘는 긴 인용 대사는 지키면 줄이 넘치므로 안에서도 끊는다."""
    spans, stack, open_tog = [], [], {}
    for i, c in enumerate(text):
        if c in _OPEN:
            stack.append(i)
        elif c in _CLOSE and stack:
            spans.append((stack.pop(), i))
        elif c in _TOGGLE:
            if c in open_tog:
                spans.append((open_tog.pop(c), i))
            else:
                open_tog[c] = i
    prot = set()
    for a, b in spans:
        if b - a + 1 <= max_chars:
            prot.update(i for i in range(a, b) if text[i] == " ")
    return prot


def _boundary_score(left: str) -> float:
    """왼쪽 줄 끝 어절로 본 경계 점수 — 낮을수록 좋은 자리."""
    last = left.split()[-1]
    if _SENT_END.search(last):
        return 0.0
    if last.endswith(","):
        return 1.0
    w = _strip_tail_punct(last)
    if w in ("건", "게", "건데"):          # 것은·것이 준말 — "확인시켜준 건 / 뜻밖에도…"
        return 3.0
    if w == "걸":                         # 것을 — 목적어
        return 8.0
    if _CLAUSE_LONG.search(w):
        return 2.0
    if _TOPIC.search(w):
        # "덩치를 키우는 / 성장 방식" — 목적어 바로 뒤의 -는/-은 은 주제 조사가 아니라
        # 꾸밈말(관형형)이다. 꾸밈말만 줄 끝에 남기지 않는다.
        words = left.split()
        if w.endswith(("는", "은")) and len(words) >= 2 and _OBJECT.search(_strip_tail_punct(words[-2])):
            return 9.0
        return 3.0
    if _ADVERBIAL.search(w):
        return 3.0
    if _CLAUSE_SHORT.search(w):
        return 3.5
    if _OBJECT.search(w):
        return 8.0           # 목적어는 서술어와 같은 줄로
    if _GENITIVE.search(w):
        return 9.0           # 꾸밈말만 남기지 않는다
    return 5.0


def _eojeol(s: str) -> int:
    return len(s.split())


def _choose(text: str, max_chars: int) -> int | None:
    """끊을 공백 위치(그 공백 인덱스). 마땅한 자리가 없으면 None."""
    prot = _protected_spaces(text, max_chars)
    best, best_key = None, None
    for i, c in enumerate(text):
        if c != " " or i in prot:
            continue
        left, right = text[:i].strip(), text[i + 1:].strip()
        if not left or not right:
            continue
        score = _boundary_score(left)
        over = len(left) - max_chars
        if over > SLACK:
            continue
        if over > 0:
            score += 1.5
        # 마지막 조각(한 줄에 들어가는 나머지)은 두 어절 이상 — 앞이 문장 끝이면 예외
        if len(right) <= max_chars and _eojeol(right) < 2 and score > 0:
            continue
        # 나머지가 길어 또 나눠야 하면 최소 세 어절은 있어야 마지막 조각 규칙을 지킬 수 있다
        if len(right) > max_chars:
            score += 1.0          # 한 번 더 나눠야 하는 자리 — 줄 수가 느는 쪽은 덜 좋다
            if _eojeol(right) < 3:
                score += 4
        # 첫 줄이 한 어절뿐이면 감점(날짜·쉼표·문장 끝은 예외)
        if _eojeol(left) < 2 and score > 1.0:
            score += 2
        # 남는 줄도 한 줄 길이를 크게 넘으면 감점 — 균형
        key = (score, abs(len(left) - min(len(right), max_chars)) / max_chars)
        if best_key is None or key < best_key:
            best, best_key = i, key
    return best


def break_lines(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    """말자막 한 덩어리(씬 나레이션)를 줄 목록으로 나눈다."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    m = DATE_LEAD.match(text)
    if m:
        rest = text[m.end():].strip()
        if _eojeol(rest) >= 2:
            return [m.group(1) + ","] + break_lines(rest, max_chars)
    if len(text) <= max_chars:
        return [text]
    pos = _choose(text, max_chars)
    if pos is None:
        if " " not in text:
            # 띄어쓰기 없는 긴 덩어리 — 예전 동작대로 글자 수로 자른다
            return [text[:max_chars]] + break_lines(text[max_chars:], max_chars)
        # 규칙을 다 지키는 자리가 없다 — 한 줄 길이 안의 마지막 공백(보호 구간 제외)
        prot = _protected_spaces(text, max_chars)
        cands = [i for i, c in enumerate(text) if c == " " and i not in prot and i <= max_chars + SLACK]
        if not cands:
            cands = [i for i, c in enumerate(text) if c == " " and i not in prot]
        if not cands:
            return [text]
        pos = cands[-1] if cands[-1] <= max_chars + SLACK else cands[0]
    return [text[:pos].strip()] + break_lines(text[pos + 1:], max_chars)
