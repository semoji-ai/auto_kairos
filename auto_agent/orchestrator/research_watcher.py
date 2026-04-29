"""Research manifest watcher.

외부 ResearchAgent가 append-only로 기록하는 manifests/<topic>/claims.jsonl을
폴링하여 새 클레임을 doc_update 이벤트(SSE)로 변환합니다.

내부화 없이 ResearchAgent 결과를 라이브 스트림으로 노출하기 위한 어댑터.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Callable, Optional


class ResearchManifestWatcher:
    def __init__(
        self,
        project_dir: Path,
        project_slug: str,
        notifier: Callable,
        phase: str = "stage_1",
        poll_interval: float = 2.0,
    ):
        self.research_dir = Path(project_dir) / "research"
        self.manifests_dir = self.research_dir / "manifests"
        self.ledger_path = self.research_dir / "claims_ledger.jsonl"
        self.project_slug = project_slug
        self.notifier = notifier
        self.phase = phase
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._offsets: dict[str, int] = {}
        self._seen_claims: set[str] = set()

    def start(self) -> None:
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        self._scan_once()

    def _watch(self) -> None:
        while not self._stop.is_set():
            self._scan_once()
            self._stop.wait(self.poll_interval)

    def _scan_once(self) -> None:
        # 1. manifests/<topic>/claims.jsonl (Phase 1 흐름)
        if self.manifests_dir.exists():
            try:
                topic_dirs = list(self.manifests_dir.iterdir())
            except Exception:
                topic_dirs = []
            for topic_dir in topic_dirs:
                if not topic_dir.is_dir():
                    continue
                self._scan_file(topic_dir / "claims.jsonl", topic=topic_dir.name)

        # 2. research/claims_ledger.jsonl (Phase 3 — script-director 누적)
        if self.ledger_path.exists():
            self._scan_file(self.ledger_path, topic="_ledger")

    def _scan_file(self, path: Path, topic: str) -> None:
        if not path.exists():
            return
        key = str(path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                f.seek(self._offsets.get(key, 0))
                new_lines = f.readlines()
                self._offsets[key] = f.tell()
        except Exception:
            return
        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                claim = json.loads(line)
            except json.JSONDecodeError:
                continue
            claim_id = claim.get("claim_id")
            if not claim_id or claim_id in self._seen_claims:
                continue
            self._seen_claims.add(claim_id)
            self._emit_claim(claim, topic=topic)

    def _emit_claim(self, claim: dict, topic: str) -> None:
        try:
            self.notifier(
                agent="research-agent",
                text=str(claim.get("claim", ""))[:120],
                phase=self.phase,
                project=self.project_slug,
                level="info",
                kind="doc_update",
                data={
                    "doc_type": "research",
                    "doc_id": "stage1-claims",
                    "op": "upsert",
                    "path": f"claims.{claim.get('claim_id')}",
                    "value": claim,
                    "meta": {"topic": topic, "kind": claim.get("kind")},
                },
            )
        except Exception:
            pass
