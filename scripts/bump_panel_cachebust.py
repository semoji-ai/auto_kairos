#!/usr/bin/env python3
"""어도비 패널 스크립트의 `?v=` 를 커밋 수로 맞춘다.

CEP(Chromium)는 `js/*.js` 를 캐시한다. 값을 안 바꾸면 고쳐도 패널이 옛
코드를 계속 쓰고, **고친 사람은 반영된 줄 안다** — 후보 띠를 넣고도 안 보여
한참 찾은 적이 있다.

커밋할 때마다 자동으로 맞춘다(pre-commit). 손으로 올리면 반드시 잊는다.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "adobe" / "cep" / "com.autokairos.pd" / "index.html"


def main() -> int:
    if not HTML.is_file():
        return 0
    try:
        ver = subprocess.run(["git", "rev-list", "--count", "HEAD"],
                             capture_output=True, text=True, cwd=ROOT).stdout.strip()
    except Exception:
        return 0
    if not ver:
        return 0
    ver = str(int(ver) + 1)          # 지금 만드는 커밋까지 센다
    t = HTML.read_text(encoding="utf-8")
    new = re.sub(r'(<script src="js/[^"?]+)(\?v=\d+)?"', rf'\1?v={ver}"', t)
    if new != t:
        HTML.write_text(new, encoding="utf-8")
        subprocess.run(["git", "add", str(HTML)], cwd=ROOT)
        print(f"[panel] 캐시버스터 ?v={ver}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
