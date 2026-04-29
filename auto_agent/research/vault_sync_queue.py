"""Vault Sync 재시도 큐 — NAS 단절 시 sync 요청을 큐에 보관 후 재가동 시 재시도.

큐 위치: ~/.auto_agent/vault_sync_queue/<timestamp>_<slug>.json
Lock 위치: ~/.auto_agent/vault_sync.lock (mkdir 기반 atomic lock)
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


def _queue_dir() -> Path:
    home = Path(os.environ.get("HOME", "/tmp"))
    d = home / ".auto_agent" / "vault_sync_queue"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lock_dir() -> Path:
    home = Path(os.environ.get("HOME", "/tmp"))
    return home / ".auto_agent" / "vault_sync.lock"


# ─────────────────────────────────────────────
# 큐 추가/꺼내기
# ─────────────────────────────────────────────

def enqueue(project_slug: str, payload: dict | None = None) -> Path:
    """sync 요청을 큐에 추가. 반환: 작성된 파일 경로."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_slug)[:40]
    fname = f"{ts}_{safe_slug}.json"
    fpath = _queue_dir() / fname
    item = {
        "project_slug": project_slug,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    fpath.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    return fpath


def list_queue() -> list[Path]:
    """큐의 모든 항목 (시간순 정렬)."""
    qd = _queue_dir()
    return sorted([p for p in qd.iterdir() if p.suffix == ".json"])


def pop_next() -> Path | None:
    """가장 오래된 큐 항목 1개 반환. 호출자가 처리 후 dispose() 호출."""
    items = list_queue()
    return items[0] if items else None


def dispose(item_path: Path) -> None:
    """큐 항목 처리 완료 → 파일 삭제."""
    try:
        item_path.unlink()
    except FileNotFoundError:
        pass


def mark_stale(max_age_hours: int = 24) -> list[Path]:
    """24시간 이상 된 항목을 stale 마킹 (이름에 .stale 추가). 반환: 마킹된 파일 목록."""
    cutoff = time.time() - max_age_hours * 3600
    marked: list[Path] = []
    for p in list_queue():
        try:
            if p.stat().st_mtime < cutoff:
                new_path = p.with_suffix(".stale.json")
                p.rename(new_path)
                marked.append(new_path)
        except Exception:
            continue
    return marked


# ─────────────────────────────────────────────
# File Lock (atomic mkdir)
# ─────────────────────────────────────────────

class VaultSyncLock:
    """동시 sync 차단. mkdir의 atomic 특성을 이용한 단순 lock.

    사용:
        with VaultSyncLock(timeout=10) as locked:
            if not locked:
                print("이미 sync 진행 중")
                return
            # ... sync 작업 ...
    """

    def __init__(self, timeout: int = 0):
        self.lock_path = _lock_dir()
        self.timeout = timeout
        self._acquired = False

    def __enter__(self) -> bool:
        deadline = time.time() + self.timeout
        while True:
            try:
                self.lock_path.mkdir(parents=False, exist_ok=False)
                self._acquired = True
                return True
            except FileExistsError:
                if time.time() >= deadline:
                    return False
                time.sleep(0.5)
            except FileNotFoundError:
                # parent 디렉토리 없음
                self.lock_path.parent.mkdir(parents=True, exist_ok=True)
                continue

    def __exit__(self, *args) -> None:
        if self._acquired:
            try:
                self.lock_path.rmdir()
            except Exception:
                pass


def force_clear_lock() -> bool:
    """좀비 lock 강제 해제. 사용자가 명시적으로 호출."""
    try:
        _lock_dir().rmdir()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False
