"""Vault Lookup Module — 볼트(NAS)에서 매칭 토픽을 프로젝트로 흡수.

step_1_vault_lookup으로 호출됨. NAS 단절 / 매칭 실패 모두 silent skip.

input  : output/<proj>/research/manifests/<topic>/runs.jsonl (fresh_collector 결과)
         또는 editorial_brief의 entity 후보
output : output/<proj>/research/wiki/<absorbed_topic>/*.md (volume copy)
         output/<proj>/research/vault_lookup.json (메타)

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 2)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from auto_agent.research.vault_lookup import (
    absorb_topic,
    list_vault_topics,
    match_vault_topics,
    vault_health_check,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _progress(msg: str, level: str = "info") -> None:
    print(f"[vault_lookup] {msg}", flush=True)
    pf = os.environ.get("PROGRESS_FILE")
    if pf:
        try:
            with open(pf, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "agent": "vault-lookup",
                    "text": msg,
                    "level": level,
                    "phase": "stage_1",
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _gather_queries_from_project(project_dir: Path) -> list[str]:
    """프로젝트의 fresh_collector 결과 또는 brief에서 검색 쿼리 추출."""
    queries: list[str] = []

    # 우선 — fresh_collector 토픽 슬러그/쿼리
    summary_path = project_dir / "research" / "fresh_collector_summary.json"
    if summary_path.exists():
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            for topic in data.get("topics", []):
                q = str(topic.get("query") or topic.get("topic_slug") or "").strip()
                if q and q not in queries:
                    queries.append(q)
        except Exception:
            pass

    # 폴백 — brief의 entity 필드들
    if not queries:
        for fname in ("editorial_brief.v2.json", "editorial_brief.v1.json", "editorial_brief.json"):
            bp = project_dir / fname
            if not bp.exists():
                continue
            try:
                brief = json.loads(bp.read_text(encoding="utf-8"))
            except Exception:
                continue
            real_topic = (brief.get("real_topic") or "").strip()
            if real_topic:
                queries.append(real_topic)
            for key in ("entities", "key_entities", "key_persons"):
                ents = brief.get(key) or []
                if isinstance(ents, list):
                    for e in ents[:5]:
                        if isinstance(e, str) and e.strip():
                            queries.append(e.strip())
            break

    return queries


def main() -> int:
    project_dir = Path(os.environ.get("PROJECT_DIR", "")).resolve()
    if not project_dir or not project_dir.exists():
        _progress("PROJECT_DIR 환경변수가 없거나 존재하지 않음", level="error")
        return 1

    research_dir = project_dir / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "started_at": _now_iso(),
        "vault_health": None,
        "vault_topics_count": 0,
        "queries": [],
        "matches": [],
        "absorbed": [],
        "skipped": False,
        "skip_reason": None,
    }

    # 1. 헬스 체크
    healthy, reason = vault_health_check()
    summary["vault_health"] = {"ok": healthy, "reason": reason}
    if not healthy:
        _progress(f"볼트 단절 — 흡수 스킵 ({reason})", level="warning")
        summary["skipped"] = True
        summary["skip_reason"] = reason
        _write_summary(research_dir, summary)
        return 0  # NAS 단절은 정상 종료 (non-blocking)

    # 2. 볼트 토픽 목록
    vault_slugs = list_vault_topics()
    summary["vault_topics_count"] = len(vault_slugs)
    _progress(f"볼트 토픽 {len(vault_slugs)}개 발견")

    # 3. 프로젝트 검색 쿼리 수집
    queries = _gather_queries_from_project(project_dir)
    summary["queries"] = queries
    if not queries:
        _progress("프로젝트 쿼리 없음 — 흡수 스킵", level="warning")
        summary["skipped"] = True
        summary["skip_reason"] = "no queries"
        _write_summary(research_dir, summary)
        return 0
    _progress(f"매칭 시도: {len(queries)}개 쿼리 vs {len(vault_slugs)}개 볼트 토픽")

    # 4. LLM 매처
    matches = match_vault_topics(queries, vault_slugs)
    summary["matches"] = matches
    _progress(f"매칭 결과: {len(matches)}개 (confidence ≥ 0.7)")

    # 5. 흡수
    for m in matches:
        result = absorb_topic(m["vault_slug"], research_dir)
        result["confidence"] = m["confidence"]
        result["rationale"] = m["rationale"]
        summary["absorbed"].append(result)
        if result["absorbed"]:
            _progress(f"흡수: {m['vault_slug']} ({len(result['files'])}개 파일, conf={m['confidence']})")

    summary["completed_at"] = _now_iso()
    _write_summary(research_dir, summary)

    absorbed_count = sum(1 for a in summary["absorbed"] if a.get("absorbed"))
    _progress(f"완료 — {absorbed_count}/{len(matches)}개 토픽 흡수")
    return 0


def _write_summary(research_dir: Path, summary: dict) -> None:
    out = research_dir / "vault_lookup.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
