"""Vault Sync — 프로젝트 wiki/claims를 볼트(NAS 02-research)로 push.

파이프라인 외부에서 manual trigger. NAS 단절 시 큐 보관.

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 4)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from auto_agent.research.vault_lookup import get_vault_root, list_vault_topics


# ─────────────────────────────────────────────
# Slug 정규화
# ─────────────────────────────────────────────

NORMALIZER_PROMPT = """당신은 토픽 슬러그 정규화기입니다. 긴 프로젝트 슬러그를
표준 entity 슬러그로 정규화하세요.

입력:
- 프로젝트 슬러그 (예: "유한양행_100주년_1부터_100까지_숫자로_읽는_유한양행")
- 볼트 기존 토픽 슬러그 목록 (예: ["유한양행", "유일한", "바세린"])

출력 규칙:
- JSON 객체 한 개. 다른 텍스트 일체 금지.
- 스키마: {"entity_slug": "...", "match_type": "exact|fuzzy|new", "confidence": 0.0~1.0, "rationale": "..."}
- 볼트에 있으면 해당 슬러그 사용 (match_type: exact 또는 fuzzy, confidence ≥ 0.7)
- 볼트에 없으면 신규 entity slug 제안 (match_type: new, confidence: 0.9)
- 슬러그는 한국어 가능, 공백·특수문자 제외, 50자 이하

좋은 예시:
- 입력 슬러그 "유한양행_100주년_..." + 볼트 ["유한양행"] → {"entity_slug": "유한양행", "match_type": "exact", "confidence": 0.98}
- 입력 "펩시콜라_역사" + 볼트 ["pepsi"] → {"entity_slug": "pepsi", "match_type": "fuzzy", "confidence": 0.85}
- 입력 "신규_주제" + 볼트 [...] → {"entity_slug": "신규-주제", "match_type": "new", "confidence": 0.9}
"""


def _build_normalizer_prompt(project_slug: str, vault_slugs: list[str]) -> str:
    body = {"project_slug": project_slug, "vault_topics": vault_slugs}
    return f"{NORMALIZER_PROMPT}\n\n<input>\n{json.dumps(body, ensure_ascii=False, indent=2)}\n</input>\n"


def _parse_normalizer_response(raw: str) -> dict:
    raw = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("응답에 JSON 블록 없음")
    payload = json.loads(m.group(0))
    if not isinstance(payload, dict):
        raise ValueError("응답이 dict가 아님")
    slug = str(payload.get("entity_slug") or "").strip()
    if not slug:
        raise ValueError("entity_slug 누락")
    try:
        confidence = float(payload.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "entity_slug": slug[:50],
        "match_type": str(payload.get("match_type") or "new"),
        "confidence": round(confidence, 2),
        "rationale": str(payload.get("rationale") or ""),
    }


def _call_claude_cli(prompt: str, *, timeout: int = 60) -> str:
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    result = subprocess.run(
        [claude_bin, "-p", "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
    return result.stdout


def _fallback_slug(project_slug: str) -> str:
    """LLM 실패 시 — 프로젝트 슬러그 첫 토큰 사용."""
    cleaned = re.sub(r"[^\w가-힣-]", "_", project_slug).strip("_")
    return cleaned.split("_")[0][:50] or "unknown"


def normalize_to_entity_slug(
    project_slug: str,
    vault_slugs: list[str] | None = None,
    *,
    invoker: Callable[[str], str] | None = None,
) -> dict:
    """긴 프로젝트 슬러그를 표준 entity slug로 정규화.

    Returns:
        {entity_slug, match_type, confidence, rationale}.
        LLM 실패 시 fallback (slug 첫 토큰, match_type='new', confidence=0.5).
    """
    invoke = invoker or _call_claude_cli
    slugs = vault_slugs if vault_slugs is not None else list_vault_topics()
    prompt = _build_normalizer_prompt(project_slug, slugs)
    try:
        raw = invoke(prompt)
        return _parse_normalizer_response(raw)
    except Exception as exc:
        return {
            "entity_slug": _fallback_slug(project_slug),
            "match_type": "fallback",
            "confidence": 0.5,
            "rationale": f"LLM 실패: {exc}",
        }


# ─────────────────────────────────────────────
# Sync 핵심 로직
# ─────────────────────────────────────────────

@dataclass
class SyncOptions:
    dry_run: bool = False
    force: bool = False
    queue_only: bool = False


@dataclass
class SyncResult:
    project_slug: str
    started_at: str = ""
    completed_at: str = ""
    vault_root: str = ""
    topics: list[dict] = field(default_factory=list)
    queued: bool = False
    queue_reason: Optional[str] = None
    errors: list[dict] = field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _list_project_topics(project_research_dir: Path) -> list[str]:
    manifests = project_research_dir / "manifests"
    if not manifests.exists():
        return []
    try:
        return sorted([d.name for d in manifests.iterdir() if d.is_dir()])
    except Exception:
        return []


def _dedup_claims_append(
    project_claims: list[dict],
    vault_claims_path: Path,
) -> tuple[int, int]:
    """vault claims.jsonl에 dedup-append. claim_id 중복은 무시.

    Returns:
        (appended_count, skipped_count)
    """
    existing_ids: set[str] = set()
    for c in _read_jsonl(vault_claims_path):
        cid = str(c.get("claim_id") or c.get("id") or "")
        if cid:
            existing_ids.add(cid)

    appended = 0
    skipped = 0
    if not project_claims:
        return 0, 0
    vault_claims_path.parent.mkdir(parents=True, exist_ok=True)
    with open(vault_claims_path, "a", encoding="utf-8") as f:
        for c in project_claims:
            cid = str(c.get("claim_id") or c.get("id") or "")
            if cid and cid in existing_ids:
                skipped += 1
                continue
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
            existing_ids.add(cid)
            appended += 1
    return appended, skipped


def _copy_wiki_pages(
    src_dir: Path,
    dst_dir: Path,
    *,
    dry_run: bool = False,
) -> list[str]:
    """프로젝트 wiki 페이지를 볼트로 복사. 충돌 시 .synced.md 접미사."""
    if not src_dir.exists():
        return []
    copied: list[str] = []
    pages = ("overview.md", "claims.md", "entities.md", "timeline.md", "images.md", "log.md", "index.md")
    for page in pages:
        src = src_dir / page
        if not src.exists():
            continue
        dst = dst_dir / page
        if dst.exists():
            # 충돌 — .synced 접미사로 보존
            dst = dst_dir / f"{page.rsplit('.', 1)[0]}.synced.md"
        if dry_run:
            copied.append(f"[dry-run] {page} → {dst.name}")
            continue
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst.name)
    return copied


def sync_topic(
    project_research_dir: Path,
    project_topic_slug: str,
    vault_root: Path,
    *,
    invoker: Callable[[str], str] | None = None,
    options: SyncOptions = SyncOptions(),
) -> dict:
    """한 토픽을 볼트로 sync. 슬러그 정규화 + dedup-append + wiki copy."""
    record: dict = {
        "project_topic_slug": project_topic_slug,
        "vault_entity_slug": None,
        "match_type": None,
        "confidence": 0.0,
        "claims_appended": 0,
        "claims_skipped": 0,
        "wiki_pages": [],
        "raw_runs_copied": 0,
        "errors": [],
    }

    # 1. 정규화
    vault_slugs = list_vault_topics()
    norm = normalize_to_entity_slug(project_topic_slug, vault_slugs, invoker=invoker)
    record["vault_entity_slug"] = norm["entity_slug"]
    record["match_type"] = norm["match_type"]
    record["confidence"] = norm["confidence"]

    if not options.force and norm["confidence"] < 0.7 and norm["match_type"] != "new":
        record["errors"].append({"phase": "normalize", "reason": f"confidence {norm['confidence']} < 0.7"})
        return record

    entity_slug = norm["entity_slug"]

    # 2. claims dedup-append
    project_claims = _read_jsonl(
        project_research_dir / "manifests" / project_topic_slug / "claims.jsonl"
    )
    if project_claims:
        vault_claims_path = vault_root / "manifests" / entity_slug / "claims.jsonl"
        if options.dry_run:
            existing = _read_jsonl(vault_claims_path) if vault_claims_path.exists() else []
            existing_ids = {str(c.get("claim_id", "")) for c in existing}
            new_ids = [c for c in project_claims if str(c.get("claim_id", "")) not in existing_ids]
            record["claims_appended"] = len(new_ids)
            record["claims_skipped"] = len(project_claims) - len(new_ids)
        else:
            appended, skipped = _dedup_claims_append(project_claims, vault_claims_path)
            record["claims_appended"] = appended
            record["claims_skipped"] = skipped

    # 3. wiki 페이지 복사
    src_wiki = project_research_dir / "wiki" / project_topic_slug
    dst_wiki = vault_root / "wiki" / entity_slug
    record["wiki_pages"] = _copy_wiki_pages(src_wiki, dst_wiki, dry_run=options.dry_run)

    # 4. raw run 복사 (immutable)
    src_raw = project_research_dir / "raw" / project_topic_slug
    if src_raw.exists():
        try:
            run_dirs = sorted([d for d in src_raw.iterdir() if d.is_dir()])
        except Exception:
            run_dirs = []
        for run_dir in run_dirs:
            dst_run = vault_root / "raw" / entity_slug / run_dir.name
            if dst_run.exists():
                continue  # immutable — 이미 있으면 건너뜀
            if options.dry_run:
                record["raw_runs_copied"] += 1
                continue
            try:
                shutil.copytree(run_dir, dst_run)
                record["raw_runs_copied"] += 1
            except Exception as exc:
                record["errors"].append({"phase": "raw_copy", "run": run_dir.name, "reason": str(exc)})

    return record


def sync_project_to_vault(
    project_dir: Path,
    *,
    invoker: Callable[[str], str] | None = None,
    options: SyncOptions = SyncOptions(),
) -> SyncResult:
    """프로젝트 전체 토픽을 볼트로 sync."""
    project_dir = Path(project_dir)
    project_slug = project_dir.name.split("_", 1)[1] if "_" in project_dir.name else project_dir.name
    research_dir = project_dir / "research"

    result = SyncResult(project_slug=project_slug, started_at=_now_iso())

    vault_root = get_vault_root()
    if vault_root is None:
        result.queued = True
        result.queue_reason = "vault unavailable (NAS 미마운트)"
        result.completed_at = _now_iso()
        return result
    result.vault_root = str(vault_root)

    if options.queue_only:
        result.queued = True
        result.queue_reason = "queue_only 옵션"
        result.completed_at = _now_iso()
        return result

    topics = _list_project_topics(research_dir)
    if not topics:
        result.errors.append({"reason": "프로젝트 토픽 없음"})
        result.completed_at = _now_iso()
        return result

    for topic in topics:
        try:
            r = sync_topic(research_dir, topic, vault_root, invoker=invoker, options=options)
            result.topics.append(r)
        except Exception as exc:
            result.errors.append({"topic": topic, "reason": str(exc)})

    result.completed_at = _now_iso()
    return result
