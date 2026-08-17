"""결정적 리서치 수집 — 쿼리 리스트를 받아 4레인 병렬 호출 → 정규화 → 적재.
v3 fresh_collector_module 이식. 진행 로그는 on_event 콜백(PROGRESS_FILE env 제거).
입력은 쿼리 리스트(브리프/LLM은 상위 단계)."""
from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.research.lanes import (
    search_crossref,
    search_news,
    search_openlibrary,
    search_wikipedia,
)


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


def collect_lanes_parallel(query: str, *, limit_per_lane: int = 8,
                           max_workers: int = 4) -> dict[str, list[dict]]:
    """4레인 병렬 호출, lane명→결과. 한 레인 실패는 error 엔트리로 격리."""
    lane_funcs = {           # 람다가 모듈 전역 함수를 호출 시점에 해석 → 테스트 monkeypatch 가능
        "wikipedia": lambda q, lim: search_wikipedia(q, limit=lim),
        "news": lambda q, lim: search_news(q, limit=lim),
        "crossref": lambda q, lim: search_crossref(q, limit=lim),
        "openlibrary": lambda q, lim: search_openlibrary(q, limit=lim),
    }
    out: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fn, query, limit_per_lane): name
                   for name, fn in lane_funcs.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                out[name] = fut.result()
            except Exception as exc:
                out[name] = [{"error": str(exc), "lane": name, "query": query}]
    return out


def _normalize_source(item: dict, *, run_id: str, topic_slug: str) -> dict[str, Any] | None:
    """레인 결과를 공통 source 스키마로. error/불완전 엔트리는 None."""
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


def _write_source_note(research_dir: Path, source: dict) -> None:
    note_path = research_dir / source["raw_path"]
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


def collect_topic(proj_dir: Path, *, topic_slug: str, query: str,
                  limit_per_lane: int = 8, on_event=None) -> dict[str, Any]:
    """단일 토픽(=쿼리) 수집 → research/raw + manifests 적재. run_record 반환."""
    research_dir = Path(proj_dir) / "research"
    run_id = _run_id()
    manifests_dir = research_dir / "manifests" / topic_slug
    sources_jsonl = manifests_dir / "sources.jsonl"
    runs_jsonl = manifests_dir / "runs.jsonl"

    if on_event:
        on_event(f"리서치 '{topic_slug}' 수집 시작 (query={query})")
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
        "run_id": run_id, "topic_slug": topic_slug, "query": query,
        "started_at": _now_iso(), "lanes": list(lane_results.keys()),
        "saved": saved, "errors": errors,
        "tier_counts": tier_counts, "lane_counts": lane_counts,
    }
    _append_jsonl(runs_jsonl, run_record)
    if on_event:
        on_event(f"리서치 '{topic_slug}' 완료 — {saved}개 source, errors={len(errors)}")
    return run_record


def collect_queries(proj_dir, queries: list, *, limit_per_lane: int = 8,
                    on_event=None) -> dict[str, Any]:
    """쿼리 리스트(각 str 또는 {'query':...})를 토픽별 수집. 진입점.
    반환: {'runs': [run_record...], 'sources': 총 적재수, 'manifest': 마지막 sources.jsonl 경로}."""
    proj_dir = Path(proj_dir)
    runs: list[dict] = []
    total = 0
    last_manifest = ""
    for q in queries:
        query = (q.get("query") if isinstance(q, dict) else str(q or "")).strip()
        if not query:
            continue
        topic_slug = _slug(query)
        rec = collect_topic(proj_dir, topic_slug=topic_slug, query=query,
                            limit_per_lane=limit_per_lane, on_event=on_event)
        runs.append(rec)
        total += rec.get("saved", 0)
        last_manifest = str(proj_dir / "research" / "manifests" / topic_slug / "sources.jsonl")
    return {"runs": runs, "sources": total, "manifest": last_manifest}
