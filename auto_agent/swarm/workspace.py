"""SwarmWorkspace — multi-agent swarm의 공유 파일 시스템.

핵심 원칙:
1. **Section ownership**: 각 파일은 단일 owner. 다른 agent는 read-only.
2. **Append-only**: queue/findings/claims/log/episodes는 append-only (race-free).
3. **Atomic rename**: status.json/meta.json/manuscript.md는 atomic (write to tmp + rename).
4. **No global lock**: 위 두 원칙으로 lock 자체를 회피.

파일 구조 (각 영상 프로젝트의 swarm/ 디렉토리):

    swarm/
    ├── meta.json               (orchestrator만 write, atomic rename)
    ├── manuscript.md           (writer만 write, atomic rename)
    ├── outline.json            (skeleton+identify만 write, write-once)
    ├── research_targets.json   (skeleton+identify만 write, write-once)
    ├── character_register.json (skeleton 초기화 + writer append, atomic rename)
    ├── outline_state.json      (writer만 write, atomic rename — 진행 추적)
    ├── research_queue.jsonl    (writer가 append, researcher는 read+claim)
    ├── findings.jsonl          (researcher가 append, 모두 read)
    ├── claims.jsonl            (researcher가 append, ground-truth fact pool)
    ├── episodes.jsonl          (episode_miner가 append)
    ├── log.jsonl               (모든 agent append, audit log)
    └── status.json             (supervisor/orchestrator write, heartbeat)

claim 매칭: writer가 manuscript.md에 [claim:cXXX] inline 태그 사용.
validator가 모든 [claim:cXXX]가 claims.jsonl에 존재하는지 검증.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


# ── 파일 권한 매핑 ──────────────────────────────────────
# (filename, owner_role, mode)
#   mode = "append" | "atomic_rename" | "write_once"
FILE_OWNERSHIP: Dict[str, tuple[str, str]] = {
    "meta.json":              ("orchestrator",       "atomic_rename"),
    "manuscript.md":          ("writer",             "atomic_rename"),
    "outline.json":           ("skeleton_identify",  "write_once"),
    "research_targets.json":  ("skeleton_identify",  "write_once"),
    "character_register.json":("writer_or_skeleton", "atomic_rename"),  # skeleton 초기화 + writer append
    "outline_state.json":     ("writer",             "atomic_rename"),
    "research_queue.jsonl":   ("writer",             "append"),  # writer만 add
    "findings.jsonl":         ("researcher",         "append"),  # 여러 researcher가 append (race-free, append는 atomic)
    "claims.jsonl":           ("researcher",         "append"),
    "episodes.jsonl":         ("episode_miner",      "append"),
    "log.jsonl":              ("any",                "append"),  # 모든 agent
    "status.json":            ("supervisor",         "atomic_rename"),
}


def _utcnow_iso() -> str:
    """UTC ISO 8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


class SwarmWorkspace:
    """공유 파일 시스템 핸들러. 모든 agent가 이 객체를 통해 read/write."""

    def __init__(self, workspace_dir: Path | str):
        self.dir = Path(workspace_dir)
        self.dir.mkdir(parents=True, exist_ok=True)

    # ─────────────────────────────────────
    # 경로 헬퍼
    # ─────────────────────────────────────

    def path(self, filename: str) -> Path:
        return self.dir / filename

    def exists(self, filename: str) -> bool:
        return self.path(filename).exists()

    # ─────────────────────────────────────
    # Atomic write (write_once / atomic_rename)
    # ─────────────────────────────────────

    def write_atomic(self, filename: str, content: str) -> None:
        """tmp 파일에 write 후 rename — POSIX 원자성 보장."""
        target = self.path(filename)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, target)  # atomic on POSIX

    def write_json_atomic(self, filename: str, data: Any, *, indent: int = 2) -> None:
        self.write_atomic(filename, json.dumps(data, ensure_ascii=False, indent=indent))

    def read_text(self, filename: str) -> str:
        p = self.path(filename)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def read_json(self, filename: str, default: Any = None) -> Any:
        p = self.path(filename)
        if not p.exists():
            return default if default is not None else {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return default if default is not None else {}

    # ─────────────────────────────────────
    # Append-only (jsonl)
    # ─────────────────────────────────────

    def append_jsonl(self, filename: str, record: Dict[str, Any]) -> None:
        """JSONL 한 줄 append. 자동으로 ts 추가.

        POSIX append (O_APPEND)는 atomic — 여러 process가 동시 append해도 한 줄씩 끼어듦 없이 기록.
        line size < PIPE_BUF (보통 4KB)면 완전 atomic. JSONL 라인은 보통 충분히 작음.
        """
        if "ts" not in record:
            record["ts"] = _utcnow_iso()
        line = json.dumps(record, ensure_ascii=False) + "\n"
        if len(line) >= 4096:
            # 큰 record는 자르거나 별도 처리. 일단 경고.
            self.append_jsonl("log.jsonl", {
                "agent": "system", "level": "warning",
                "event": "large_record",
                "filename": filename, "size": len(line),
            })
        with open(self.path(filename), "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())  # 디스크 sync (다른 worker가 즉시 볼 수 있게)

    def read_jsonl(self, filename: str, *, since_offset: int = 0) -> tuple[List[Dict[str, Any]], int]:
        """JSONL 파일 읽기 — since_offset 이후 라인만 반환.

        Returns: (records, new_offset)
        """
        p = self.path(filename)
        if not p.exists():
            return [], since_offset
        with open(p, "r", encoding="utf-8") as f:
            f.seek(since_offset)
            records: List[Dict[str, Any]] = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass  # 부분 쓰기 중인 라인일 수 있음. 다음 polling에 다시 시도.
            return records, f.tell()

    def all_jsonl(self, filename: str) -> List[Dict[str, Any]]:
        """전체 JSONL 읽기 (since_offset=0)."""
        records, _ = self.read_jsonl(filename, since_offset=0)
        return records

    # ─────────────────────────────────────
    # 이벤트 로그 (모든 agent의 audit trail)
    # ─────────────────────────────────────

    def emit_event(
        self,
        agent: str,
        event: str,
        *,
        level: str = "info",
        **payload: Any,
    ) -> None:
        """log.jsonl에 이벤트 기록. 모든 agent의 audit trail."""
        record = {
            "ts": _utcnow_iso(),
            "agent": agent,
            "event": event,
            "level": level,
        }
        if payload:
            record["payload"] = payload
        self.append_jsonl("log.jsonl", record)

    # ─────────────────────────────────────
    # Task claim (atomic) — researcher가 query를 claim할 때 사용
    # ─────────────────────────────────────

    def claim_task(
        self,
        queue_filename: str,
        claimer: str,
        *,
        max_retries: int = 2,
    ) -> Optional[Dict[str, Any]]:
        """research_queue.jsonl에서 잡을 수 있는 첫 task를 atomic claim.

        잡을 수 있는 task:
          - 한 번도 claim 안 됨 (pending)
          - failed이지만 retry_count < max_retries (다른 researcher가 다시 시도)

        잡을 수 없는 task:
          - 현재 다른 claimer가 처리 중 (claimed)
          - 이미 성공 (completed)
          - failed인데 retry_count >= max_retries (영구 포기)

        구현: queue 전체를 읽고 → 잡을 수 있는 첫 task 찾고 → status_overrides에 claim append.
        """
        # 1. queue 전체 읽기
        records = self.all_jsonl(queue_filename)
        if not records:
            return None

        # 2. status_overrides에서 각 task의 최신 상태 + retry 카운트 집계
        overrides_file = "status_overrides.jsonl"
        overrides = self.all_jsonl(overrides_file)
        # task_id → 최신 status, fail_count
        task_state: Dict[str, Dict[str, Any]] = {}
        for o in overrides:
            tid = o.get("task_id", "")
            if not tid:
                continue
            if tid not in task_state:
                task_state[tid] = {"status": "pending", "fail_count": 0}
            status = o.get("status", "")
            task_state[tid]["status"] = status  # 최신 status
            if status == "failed" or status == "parse_failed":
                task_state[tid]["fail_count"] += 1

        # 3. 잡을 수 있는 첫 task 찾기
        for task in records:
            tid = task.get("id")
            if not tid:
                continue
            state = task_state.get(tid, {"status": "pending", "fail_count": 0})
            cur_status = state["status"]
            fail_count = state["fail_count"]

            # claimed/completed는 skip
            if cur_status == "claimed":
                continue
            if cur_status == "completed":
                continue
            # failed이지만 retry 가능?
            if cur_status in ("failed", "parse_failed"):
                if fail_count >= max_retries:
                    continue  # 영구 포기
                # else: 잡을 수 있음

            # 4. claim event append (atomic)
            self.append_jsonl(overrides_file, {
                "task_id": tid,
                "status": "claimed",
                "claimer": claimer,
                "retry_attempt": fail_count,
            })
            return task
        return None

    def complete_task(self, task_id: str, completer: str, **payload: Any) -> None:
        """claim한 task를 완료 처리."""
        self.append_jsonl("status_overrides.jsonl", {
            "task_id": task_id,
            "status": "completed",
            "completer": completer,
            **payload,
        })

    def task_status(self, task_id: str) -> str:
        """task의 현재 status (pending | claimed | completed)."""
        overrides = self.all_jsonl("status_overrides.jsonl")
        # 최신 상태 (마지막 record)
        for o in reversed(overrides):
            if o.get("task_id") == task_id:
                return o.get("status", "pending")
        return "pending"

    # ─────────────────────────────────────
    # Character register — atomic append (writer가 새 인물 발견 시)
    # ─────────────────────────────────────

    def append_character(self, character: Dict[str, Any]) -> bool:
        """character_register.json에 atomic append.

        race-free: read → modify → write_atomic (rename).
        같은 id가 이미 있으면 skip하고 False 반환.

        character 필수 필드: id, name_ko
        선택 필드: name_en, role, is_real_person, first_mention_chapter,
                  discovered_by, needs_research
        """
        cid = character.get("id", "").strip()
        if not cid:
            return False
        register = self.read_json("character_register.json", default={"characters": []})
        if not isinstance(register, dict) or "characters" not in register:
            register = {"characters": []}
        existing_ids = {c.get("id", "") for c in register.get("characters", [])}
        if cid in existing_ids:
            return False  # 이미 있음
        # 기본 필드 채우기
        character.setdefault("is_real_person", True)
        character.setdefault("needs_research", False)
        register["characters"].append(character)
        self.write_json_atomic("character_register.json", register)
        return True

    # ─────────────────────────────────────
    # Tail watcher — agent의 polling loop에서 사용
    # ─────────────────────────────────────

    def tail_jsonl(
        self,
        filename: str,
        offset: int,
        *,
        timeout_sec: float = 30,
        poll_interval: float = 0.5,
    ) -> tuple[List[Dict[str, Any]], int]:
        """파일 끝에 새 라인이 추가될 때까지 대기 (혹은 timeout).

        Returns: (new_records, new_offset)
        """
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            records, new_offset = self.read_jsonl(filename, since_offset=offset)
            if records:
                return records, new_offset
            time.sleep(poll_interval)
        return [], offset
