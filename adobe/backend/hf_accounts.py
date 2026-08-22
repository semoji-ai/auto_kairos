"""힉스필드 계정 여러 개를 한 자리에서 쓴다.

구독을 셋 두면 크레딧이 매달 셋으로 나뉘어 들어온다(9,000 × 3 = 27,000).
그런데 CLI 는 계정을 하나만 기억한다 — `~/.config/higgsfield/credentials.json`
한 벌뿐이라, 쓰다가 잔액이 떨어지면 사람이 로그아웃하고 다시 로그인해야 했다.

**`HOME` 을 바꾸면 계정이 통째로 갈린다.** CLI 는 `$HOME/.config/higgsfield`
를 보므로, 계정마다 집을 따로 두면 서로 건드리지 않는다. 인증 파일을
바꿔치기하는 것보다 안전하다 — 동시에 두 개를 돌려도 섞이지 않는다.

    ~/.hf_accounts/<이름>/.config/higgsfield/{credentials,config}.json

`XDG_CONFIG_HOME` 은 안 통한다(실측). CLI 가 경로를 직접 짓는다.

    python3 -m backend.hf_accounts list          계정과 잔액
    python3 -m backend.hf_accounts add <이름>     지금 로그인된 계정을 등록
    python3 -m backend.hf_accounts login <이름>   그 집에서 새로 로그인
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("AK_HF_ACCOUNTS") or (Path.home() / ".hf_accounts"))
LIVE = Path.home() / ".config" / "higgsfield"


def home_of(name: str) -> Path:
    return ROOT / name


def env_for(name: str | None) -> dict:
    """그 계정으로 CLI 를 돌릴 환경. name 이 없으면 지금 로그인된 계정 그대로."""
    env = dict(os.environ)
    if name:
        env["HOME"] = str(home_of(name))
    return env


def names() -> list:
    if not ROOT.is_dir():
        return []
    return sorted(p.name for p in ROOT.iterdir()
                  if (p / ".config" / "higgsfield" / "credentials.json").is_file())


def _run(args: list, name: str | None = None, timeout: int = 60) -> str:
    exe = shutil.which("higgsfield") or shutil.which("hf")
    if not exe:
        return ""
    try:
        p = subprocess.run([exe] + args, capture_output=True, text=True,
                           env=env_for(name), stdin=subprocess.DEVNULL, timeout=timeout)
    except Exception:
        return ""
    return (p.stdout or "") + (p.stderr or "")


def status(name: str | None = None) -> dict:
    """{email, plan, credits} — 못 읽으면 credits 는 None."""
    import re
    out = _run(["account", "status"], name).strip()
    m = re.search(r"([\w.+-]+@[\w.-]+)\s*—\s*(\S+)\s*plan,\s*([\d.]+)\s*credits", out)
    if not m:
        return {"name": name, "email": None, "plan": None, "credits": None, "raw": out[:120]}
    return {"name": name, "email": m.group(1), "plan": m.group(2),
            "credits": float(m.group(3))}


def add(name: str) -> dict:
    """지금 로그인된 계정을 그 이름으로 등록한다(복사 — 원본은 그대로)."""
    src = LIVE / "credentials.json"
    if not src.is_file():
        return {"error": "지금 로그인된 계정이 없습니다 — higgsfield auth login"}
    dst = home_of(name) / ".config" / "higgsfield"
    dst.mkdir(parents=True, exist_ok=True)
    for f in ("credentials.json", "config.json"):
        if (LIVE / f).is_file():
            shutil.copy2(LIVE / f, dst / f)
    return {"ok": True, "name": name, **status(name)}


def pick(need: float, *, exclude: set | None = None) -> str | None:
    """크레딧이 `need` 이상 남은 계정 하나. 많이 남은 쪽부터 고른다."""
    got = []
    for n in names():
        if exclude and n in exclude:
            continue
        c = status(n).get("credits")
        if c is not None and c >= need:
            got.append((c, n))
    if not got:
        return None
    got.sort(reverse=True)
    return got[0][1]


def total() -> float:
    return sum((status(n).get("credits") or 0.0) for n in names())


def _main(argv: list) -> int:
    cmd = argv[1] if len(argv) > 1 else "list"
    if cmd == "list":
        ns = names()
        if not ns:
            print(f"등록된 계정이 없습니다. `add <이름>` 으로 지금 계정을 등록하세요.")
            print(f"보관 위치: {ROOT}")
            return 0
        for n in ns:
            s = status(n)
            c = s.get("credits")
            print(f"  {n:<12} {s.get('email') or '?':<32} "
                  f"{'' if c is None else f'{c:>10,.1f} 크레딧'}"
                  f"{'  ← 읽기 실패' if c is None else ''}")
        print(f"  {'합계':<12} {'':<32} {total():>10,.1f} 크레딧")
        return 0
    if cmd == "add" and len(argv) > 2:
        print(add(argv[2]))
        return 0
    if cmd == "login" and len(argv) > 2:
        name = argv[2]
        home_of(name).mkdir(parents=True, exist_ok=True)
        print(f"{name} 계정으로 로그인합니다 (브라우저가 열립니다)")
        print(_run(["auth", "login"], name, timeout=300))
        print(status(name))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
