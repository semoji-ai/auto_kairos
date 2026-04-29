"""Targeted Sources Register — targeted_claims.json의 sources를 manifests/_targeted/sources.jsonl에 등록.

step_2_target이 web search로 가져온 출처들이 fresh_collector sources.jsonl과 분리돼
script-director ledger의 source_id 매칭률이 떨어지는 문제 해결.

이 모듈이 step_2_target 직후 실행되어 targeted sources를 통합 sources 풀에 추가.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _progress(msg: str, level: str = "info") -> None:
    print(f"[targeted_sources_register] {msg}", flush=True)
    pf = os.environ.get("PROGRESS_FILE")
    if pf:
        try:
            with open(pf, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "agent": "targeted-sources-register",
                    "text": msg,
                    "level": level,
                    "phase": "stage_2",
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w\s가-힣-]", "", str(text or "").strip().lower())
    s = re.sub(r"[\s_]+", "-", s)
    return s[:max_len].strip("-") or "untitled"


def _hash_short(text: str, n: int = 10) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def _make_source_id(title: str, url: str) -> str:
    base = _slugify(title)
    h = _hash_short(url or title)
    return f"src_{base}_{h}"


def _reliability_to_tier(reliability: str) -> str:
    """targeted-researcher의 reliability → fresh_collector tier_hint 변환."""
    r = (reliability or "").lower()
    if r == "high":
        return "A"
    if r == "medium":
        return "B"
    if r == "low":
        return "C"
    return "unknown"


def _normalize_targeted_source(src: dict) -> dict | None:
    """targeted_claims.json의 source 항목을 fresh_collector source schema로 변환."""
    if not isinstance(src, dict):
        return None
    title = str(src.get("title") or "").strip()
    url = str(src.get("url") or "").strip()
    if not url and not title:
        return None
    return {
        "source_id": _make_source_id(title, url),
        "title": title,
        "url": url,
        "publisher": str(src.get("publisher") or ""),
        "published_at": str(src.get("published_at") or ""),
        "retrieved_at": _now_iso(),
        "source_type": "targeted",
        "lane": "targeted_research",
        "tier_hint": _reliability_to_tier(src.get("reliability", "")),
        "snippet": str(src.get("snippet") or src.get("excerpt") or ""),
        "topic_slug": "_targeted",
        "raw_path": "",  # targeted-researcher는 raw markdown 안 남김
        "from_targeted": True,
    }


def _load_targeted_sources(targeted_path: Path) -> list[dict]:
    """targeted_claims.json에서 모든 sources 추출 (claim별 sources 펼치기)."""
    if not targeted_path.exists():
        return []
    try:
        data = json.loads(targeted_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data if isinstance(data, list) else data.get("claims") or data.get("targeted_claims") or []
    out: list[dict] = []
    seen_urls: set = set()
    for c in items:
        if not isinstance(c, dict):
            continue
        for src in (c.get("sources") or []):
            normalized = _normalize_targeted_source(src)
            if not normalized:
                continue
            url = normalized.get("url", "")
            # url 기반 dedup (같은 출처 여러 claim에서 인용 가능)
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            out.append(normalized)
    return out


def main() -> int:
    project_dir = Path(os.environ.get("PROJECT_DIR", "")).resolve()
    if not project_dir or not project_dir.exists():
        _progress("PROJECT_DIR 환경변수 없음", level="error")
        return 1

    targeted_path = project_dir / "targeted_claims.json"
    if not targeted_path.exists():
        _progress("targeted_claims.json 없음 — 스킵", level="warning")
        return 0  # non-blocking

    sources = _load_targeted_sources(targeted_path)
    if not sources:
        _progress("targeted_claims.json에 sources 없음 — 스킵")
        return 0

    # _targeted 토픽으로 등록 (fresh_collector 풀과 분리하되 같은 manifests 디렉토리 트리)
    manifests_dir = project_dir / "research" / "manifests" / "_targeted"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    sources_jsonl = manifests_dir / "sources.jsonl"

    # 기존 등록된 url 수집해서 dedup
    existing_urls: set = set()
    if sources_jsonl.exists():
        for line in sources_jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("url"):
                    existing_urls.add(d["url"])
            except Exception:
                continue

    new_count = 0
    with open(sources_jsonl, "a", encoding="utf-8") as f:
        for s in sources:
            if s.get("url") and s["url"] in existing_urls:
                continue
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            existing_urls.add(s.get("url", ""))
            new_count += 1

    # 등록 결과 요약
    summary = {
        "completed_at": _now_iso(),
        "targeted_sources_extracted": len(sources),
        "new_added": new_count,
        "skipped_dup": len(sources) - new_count,
        "registered_to": str(sources_jsonl),
    }
    summary_path = project_dir / "research" / "targeted_sources_register.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    _progress(f"완료 — 신규 {new_count}건 등록 (중복 {len(sources) - new_count}건 스킵)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
