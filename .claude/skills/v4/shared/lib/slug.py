"""슬러그 생성기. 한글/영문/숫자 보존, 그 외는 하이픈으로."""
from __future__ import annotations
import re
import unicodedata

_SAFE = re.compile(r"[^0-9A-Za-z가-힣]+")


def slugify(text: str, *, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFC", text).strip().lower()
    text = _SAFE.sub("-", text).strip("-")
    if not text:
        text = "untitled"
    return text[:max_len].rstrip("-")
