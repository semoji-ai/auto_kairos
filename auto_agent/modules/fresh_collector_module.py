"""Fresh Collector — 검증 게이트 없는 가벼운 lane 호출 모듈.

input  : editorial_brief.json + project_config.json (PROJECT_DIR 환경변수)
output : output/<proj>/research/raw/<topic_slug>/<run_id>/source_notes/*.md
         output/<proj>/research/manifests/<topic_slug>/sources.jsonl
         output/<proj>/research/manifests/<topic_slug>/runs.jsonl

동작 원칙:
- lane 4종(wikipedia/news/crossref/openlibrary) 병렬 호출
- 결과는 모두 기록 (검증 게이트 없음). tier_hint만 도메인 룩업으로 표시.
- C(블로그/SNS) 도메인은 lane 단계에서 이미 필터링됨.
- 실패한 lane은 error 엔트리로 manifest에 기록 후 계속 진행.

spec: docs/superpowers/specs/2026-04-28-research-redesign.md
plan: docs/superpowers/plans/2026-04-28-fresh-collector-phase1.md
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from auto_agent.research.lanes import (
    search_crossref,
    search_news,
    search_openlibrary,
    search_wikipedia,
)
from auto_agent.research.query_planner import plan_queries


# ─────────────────────────────────────────────
# 유틸
# ─────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _slug(text: str, *, max_len: int = 60) -> str:
    s = re.sub(r"[^\w\s가-힣-]", "", str(text or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:max_len] or "topic"


def _hash_short(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _source_id(item: dict) -> str:
    title = str(item.get("title") or "").strip()
    url = str(item.get("url") or "").strip()
    base = f"{_slug(title, max_len=40)}_{_hash_short(url or title)}"
    return f"src_{base}"


def _progress(msg: str, level: str = "info") -> None:
    print(f"[fresh_collector] {msg}", flush=True)
    pf = os.environ.get("PROGRESS_FILE")
    if pf:
        try:
            with open(pf, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "agent": "fresh-collector",
                    "text": msg,
                    "level": level,
                    "phase": "stage_1",
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


# ─────────────────────────────────────────────
# Lane 호출
# ─────────────────────────────────────────────

LANE_FUNCS = {
    "wikipedia": lambda q, lim: search_wikipedia(q, limit=lim),
    "news":      lambda q, lim: search_news(q, limit=lim),
    "crossref":  lambda q, lim: search_crossref(q, limit=lim),
    "openlibrary": lambda q, lim: search_openlibrary(q, limit=lim),
}


def collect_lanes_parallel(
    query: str,
    *,
    limit_per_lane: int = 8,
    max_workers: int = 4,
) -> dict[str, list[dict]]:
    """4 lane 병렬 호출, lane명 → 결과 dict 반환."""
    out: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(fn, query, limit_per_lane): name
            for name, fn in LANE_FUNCS.items()
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                out[name] = fut.result()
            except Exception as exc:
                out[name] = [{"error": str(exc), "lane": name, "query": query}]
    return out


# ─────────────────────────────────────────────
# Source 정규화 + 저장
# ─────────────────────────────────────────────

def _normalize_source(item: dict, *, run_id: str, topic_slug: str) -> dict[str, Any] | None:
    """lane 결과를 공통 source 스키마로 변환. error 엔트리는 None 반환."""
    if item.get("error"):
        return None
    url = str(item.get("url") or "").strip()
    title = str(item.get("title") or "").strip()
    if not url or not title:
        return None
    sid = _source_id(item)
    return {
        "source_id": sid,
        "title": title,
        "url": url,
        "publisher": str(item.get("publisher") or ""),
        "published_at": str(item.get("published_at") or ""),
        "retrieved_at": _now_iso(),
        "source_type": str(item.get("kind") or "reference"),
        "lane": str(item.get("lane") or ""),
        "tier_hint": str(item.get("tier_hint") or "unknown"),
        "snippet": str(item.get("snippet") or ""),
        "lang": str(item.get("lang") or ""),
        "doi": str(item.get("doi") or ""),
        "author": str(item.get("author") or ""),
        "topic_slug": topic_slug,
        "run_id": run_id,
        "raw_path": f"raw/{topic_slug}/{run_id}/source_notes/{sid}.md",
    }


def _write_source_note(out_dir: Path, source: dict) -> None:
    note_path = out_dir / source["raw_path"]
    note_path.parent.mkdir(parents=True, exist_ok=True)
    front = (
        f"---\n"
        f"source_id: {source['source_id']}\n"
        f"title: {json.dumps(source['title'], ensure_ascii=False)}\n"
        f"url: {source['url']}\n"
        f"publisher: {json.dumps(source.get('publisher', ''), ensure_ascii=False)}\n"
        f"published_at: {source.get('published_at', '')}\n"
        f"retrieved_at: {source['retrieved_at']}\n"
        f"lane: {source['lane']}\n"
        f"tier_hint: {source['tier_hint']}\n"
        f"topic_slug: {source['topic_slug']}\n"
        f"run_id: {source['run_id']}\n"
        f"---\n\n"
        f"# {source['title']}\n\n"
        f"- URL: {source['url']}\n"
    )
    if source.get("author"):
        front += f"- Author: {source['author']}\n"
    if source.get("publisher"):
        front += f"- Publisher: {source['publisher']}\n"
    if source.get("snippet"):
        front += f"\n## Snippet\n\n{source['snippet']}\n"
    note_path.write_text(front, encoding="utf-8")


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ─────────────────────────────────────────────
# 메인 수집 함수
# ─────────────────────────────────────────────

def collect_topic(
    output_dir: Path,
    *,
    topic_slug: str,
    query: str,
    limit_per_lane: int = 8,
) -> dict[str, Any]:
    """하나의 토픽에 대해 lane 4종 호출 → raw + manifests 적재."""
    output_dir = Path(output_dir)
    research_dir = output_dir / "research"
    run_id = _run_id()
    raw_dir = research_dir / "raw" / topic_slug / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir = research_dir / "manifests" / topic_slug
    sources_jsonl = manifests_dir / "sources.jsonl"
    runs_jsonl = manifests_dir / "runs.jsonl"

    _progress(f"토픽 '{topic_slug}' 수집 시작 (query={query})")
    lane_results = collect_lanes_parallel(query, limit_per_lane=limit_per_lane)

    saved = 0
    errors: list[dict] = []
    tier_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}

    for lane_name, items in lane_results.items():
        for item in items:
            if item.get("error"):
                errors.append({"lane": lane_name, "error": item["error"]})
                continue
            source = _normalize_source(item, run_id=run_id, topic_slug=topic_slug)
            if not source:
                continue
            _write_source_note(research_dir, source)
            _append_jsonl(sources_jsonl, source)
            tier_counts[source["tier_hint"]] = tier_counts.get(source["tier_hint"], 0) + 1
            lane_counts[source["lane"]] = lane_counts.get(source["lane"], 0) + 1
            saved += 1

    run_record = {
        "run_id": run_id,
        "topic_slug": topic_slug,
        "query": query,
        "started_at": _now_iso(),
        "lanes": list(lane_results.keys()),
        "saved": saved,
        "errors": errors,
        "tier_counts": tier_counts,
        "lane_counts": lane_counts,
    }
    _append_jsonl(runs_jsonl, run_record)
    _progress(f"토픽 '{topic_slug}' 완료 — {saved}개 source, errors={len(errors)}, tiers={tier_counts}")
    return run_record


# ─────────────────────────────────────────────
# 파이프라인 진입점
# ─────────────────────────────────────────────

def _read_brief(project_dir: Path) -> dict:
    brief_path = project_dir / "editorial_brief.json"
    if not brief_path.exists():
        # v1/v2 등 버전 파일 시도
        for v in ("editorial_brief.v2.json", "editorial_brief.v1.json"):
            p = project_dir / v
            if p.exists():
                brief_path = p
                break
    if not brief_path.exists():
        return {}
    try:
        return json.loads(brief_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _extract_topics_from_brief(
    brief: dict,
    project_slug: str,
    *,
    planner: Any | None = None,
) -> list[dict]:
    """brief를 LLM이 5~10개 쿼리로 분해. 기계적 추출은 쿼리 오염을 일으켜 사용 안 함.

    planner: 테스트용. None이면 query_planner.plan_queries 사용.
    """
    plan_fn = planner or plan_queries
    queries = plan_fn(brief, project_slug=project_slug) or []

    topics: list[dict] = []
    seen_slugs: set[str] = set()
    for q in queries:
        text = str(q.get("query") or "").strip()
        if not text:
            continue
        slug = _slug(text)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        topics.append({
            "slug": slug,
            "query": text,
            "rationale": str(q.get("rationale") or ""),
            "lang": str(q.get("lang") or "auto"),
        })

    # planner가 비어 있으면 최후 fallback — slug 첫 토큰
    if not topics and project_slug:
        first = project_slug.replace("_", " ").split()[0]
        topics.append({"slug": _slug(first), "query": first})
    return topics


def main() -> int:
    project_dir = Path(os.environ.get("PROJECT_DIR", "")).resolve()
    if not project_dir or not project_dir.exists():
        _progress("PROJECT_DIR 환경변수가 없거나 존재하지 않음", level="error")
        return 1

    brief = _read_brief(project_dir)
    project_slug = project_dir.name.split("_", 1)[1] if "_" in project_dir.name else project_dir.name
    topics = _extract_topics_from_brief(brief, project_slug)

    _progress(f"수집 토픽 {len(topics)}개: {[t['slug'] for t in topics]}")

    runs: list[dict] = []
    for topic in topics:
        try:
            runs.append(collect_topic(
                project_dir,
                topic_slug=topic["slug"],
                query=topic["query"],
            ))
        except Exception as exc:
            _progress(f"토픽 '{topic['slug']}' 실패: {exc}", level="error")
            runs.append({"topic_slug": topic["slug"], "error": str(exc)})

    summary = {
        "completed_at": _now_iso(),
        "topics": runs,
        "total_saved": sum(r.get("saved", 0) for r in runs),
    }
    summary_path = project_dir / "research" / "fresh_collector_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _progress(f"완료. 총 {summary['total_saved']}개 source 적재.")
    return 0 if summary["total_saved"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
