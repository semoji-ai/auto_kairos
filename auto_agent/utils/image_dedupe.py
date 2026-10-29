"""내용이 같은 그림을 가려낸다.

왜 생기나 (2026-09-30 실측)
  codex `$imagegen` 생성물은 `$CODEX_HOME/generated_images/` 에서 「가장 최근 PNG」를
  타깃 경로로 복사한다. 생성이 실패하거나 늦으면 **직전 그림이 새 버전 이름으로 복사**되고,
  병렬로 돌리면 **다른 씬의 그림**이 복사된다. 파일 이름은 달라도 내용이 같아서
  씬 후보 목록에 같은 그림이 4~7장씩 쌓였다(LG 1편 씬 55: 28항목 중 고유 그림 10장).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_cache: dict = {}


def file_hash(p: Path) -> str | None:
    p = Path(p)
    try:
        st = p.stat()
    except OSError:
        return None
    key = (str(p), st.st_size, st.st_mtime)
    if key not in _cache:
        h = hashlib.md5()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _cache[key] = h.hexdigest()
    return _cache[key]


def reject_if_duplicate(out: Path, others: list) -> bool:
    """out 이 others 중 하나와 내용이 같으면 `.dup_rejected` 로 이름을 바꿔 치우고 True.

    지우지 않는다(이미지 삭제 금지) — 확장자만 바꿔 후보·최신 버전 탐색에서 빠지게 한다.
    """
    out = Path(out)
    h = file_hash(out)
    if not h:
        return False
    for o in others:
        if Path(o) != out and file_hash(o) == h:
            out.rename(out.with_name(out.name + ".dup_rejected"))
            return True
    return False
