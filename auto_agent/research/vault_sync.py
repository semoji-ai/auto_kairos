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
    ledger: dict = field(default_factory=dict)  # {entity_slug: appended_count}
    ledger_unmatched: int = 0
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


def _merge_entities_md(old: str, new: str) -> str:
    """`### Header` 단위로 dedup + description 통합 (결정적)."""
    def _split(text: str) -> tuple[str, dict[str, str]]:
        # frontmatter 분리
        fm = ""
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                fm = text[: end + 4]
                text = text[end + 4:].lstrip("\n")
        sections: dict[str, str] = {}
        cur_key = "_pre"
        cur_lines: list[str] = []
        for line in text.split("\n"):
            if line.startswith("### "):
                if cur_lines or cur_key != "_pre":
                    sections[cur_key] = "\n".join(cur_lines).rstrip()
                cur_key = line[4:].strip()
                cur_lines = [line]
            else:
                cur_lines.append(line)
        if cur_lines:
            sections[cur_key] = "\n".join(cur_lines).rstrip()
        return fm, sections

    fm_old, sec_old = _split(old or "")
    fm_new, sec_new = _split(new or "")

    # 같은 키(### 헤더)면 더 긴 본문 채택 (정보량 보존)
    merged: dict[str, str] = {}
    for key in list(sec_old.keys()) + [k for k in sec_new if k not in sec_old]:
        old_v = sec_old.get(key, "")
        new_v = sec_new.get(key, "")
        merged[key] = old_v if len(old_v) >= len(new_v) else new_v

    # frontmatter는 새 것 우선 (updated_at 등 최신)
    fm = fm_new or fm_old
    out_parts = [fm] if fm else []
    if "_pre" in merged:
        out_parts.append(merged.pop("_pre"))
    for key, body in merged.items():
        out_parts.append(body)
    return "\n\n".join(p for p in out_parts if p).rstrip() + "\n"


def _merge_timeline_md(old: str, new: str) -> str:
    """`**YYYY** —` 패턴 dedup + 연도순 정렬 (결정적)."""
    fm = ""
    body_parts: list[str] = []

    for text in (old or "", new or ""):
        if text.startswith("---") and not fm:
            end = text.find("\n---", 3)
            if end != -1:
                fm = text[: end + 4]
                text = text[end + 4:].lstrip("\n")
        body_parts.append(text)

    # **YYYY** 또는 **YYYY년** 추출 → entry dict
    # dedup 규칙: 같은 연도이고 한 줄이 다른 줄의 substring이면 더 긴 줄 채택
    year_entries: dict[str, list[str]] = {}  # year → 줄 리스트
    headers: list[str] = []
    for body in body_parts:
        for line in body.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            m = re.match(r"^[\-\*]?\s*\*\*(\d{4})", stripped)
            if m:
                year = m.group(1)
                arr = year_entries.setdefault(year, [])
                # substring 매칭 dedup
                merged = False
                norm_new = re.sub(r"\s+", " ", stripped.lower())
                for i, existing in enumerate(arr):
                    norm_ex = re.sub(r"\s+", " ", existing.lower())
                    if norm_new in norm_ex:
                        merged = True  # 새 줄이 기존 줄의 부분 — 무시
                        break
                    if norm_ex in norm_new:
                        arr[i] = stripped  # 새 줄이 더 길음 — 교체
                        merged = True
                        break
                if not merged:
                    arr.append(stripped)
            elif stripped.startswith("#"):
                if stripped not in headers:
                    headers.append(stripped)

    # 평탄화 + 연도순 정렬 (같은 연도 내 원순)
    entries: dict[str, str] = {}
    counter = 0
    for year in sorted(year_entries.keys()):
        for line in year_entries[year]:
            entries[f"{year}_{counter}"] = line
            counter += 1

    # 연도순 정렬
    def _year_key(k: str) -> int:
        try: return int(k.split("_")[0])
        except: return 9999
    sorted_entries = sorted(entries.items(), key=lambda x: _year_key(x[0]))

    out_parts: list[str] = []
    if fm:
        out_parts.append(fm)
    out_parts.extend(headers)
    for _, line in sorted_entries:
        out_parts.append(line)
    return "\n\n".join(out_parts).rstrip() + "\n"


def _merge_log_md(old: str, new: str, project_slug: str) -> str:
    """log.md에 영상 sync 항목 append (날짜별 누적)."""
    base = old if old else new
    if not base:
        base = "# Log\n\n## Sync Events\n"
    entry = f"- [{_now_iso()}] vault_sync from project `{project_slug}`"
    if entry not in base:
        if not base.endswith("\n"):
            base += "\n"
        base += entry + "\n"
    return base


OVERVIEW_MERGE_PROMPT = """당신은 위키 페이지 통합 에디터입니다. 같은 토픽의 두 overview.md를
**중복 제거 + 모든 유의 정보 보존 + 일관된 톤**으로 단일 통합본 작성.

# 절대 규칙
- 출력은 markdown 본문만 (frontmatter 제외 — 시스템이 별도 추가).
- 옛/새 어느 한 쪽에만 있는 사실 정보는 모두 보존.
- 동일 사실 중복 표현은 더 정확한 쪽 선택.
- 톤 일관 — 한 사람이 쓴 것처럼.
- 추측·없는 사실 추가 절대 금지.

# 출력 형식
markdown 본문 (frontmatter 제외). 다른 설명·메타 텍스트 없이 본문만.
"""


def _merge_overview_md(
    old: str,
    new: str,
    *,
    invoker: Callable[[str], str] | None = None,
) -> str:
    """LLM이 두 overview를 통합. 실패 시 새 버전 우선 + 옛 unique 섹션 append fallback."""
    if not old.strip():
        return new
    if not new.strip():
        return old

    # frontmatter 분리
    def _split_fm(text: str) -> tuple[str, str]:
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                return text[: end + 4], text[end + 4:].lstrip("\n")
        return "", text

    fm_old, body_old = _split_fm(old)
    fm_new, body_new = _split_fm(new)
    fm = fm_new or fm_old

    invoke = invoker or _call_claude_cli
    prompt = (
        f"{OVERVIEW_MERGE_PROMPT}\n\n"
        f"<old_overview>\n{body_old[:6000]}\n</old_overview>\n\n"
        f"<new_overview>\n{body_new[:6000]}\n</new_overview>\n"
    )
    try:
        merged_body = invoke(prompt).strip()
        # 응답에 frontmatter 들어왔으면 제거
        if merged_body.startswith("---"):
            end = merged_body.find("\n---", 3)
            if end != -1:
                merged_body = merged_body[end + 4:].lstrip("\n")
        if not merged_body:
            raise ValueError("LLM 응답 비어있음")
        return (fm + "\n\n" + merged_body if fm else merged_body).rstrip() + "\n"
    except Exception as exc:
        print(f"[vault_sync] overview LLM merge 실패, fallback: {exc}", flush=True)
        # fallback: 새 본문 + 옛 본문 끝에 "## (이전 버전 — 보존용)" 섹션
        return (
            (fm + "\n\n" if fm else "")
            + body_new
            + "\n\n## (이전 버전 — 통합 실패로 보존)\n\n"
            + body_old
        ).rstrip() + "\n"


def _merge_wiki_page(
    page: str,
    old_path: Path,
    new_path: Path,
    *,
    project_slug: str = "",
    invoker: Callable[[str], str] | None = None,
) -> str:
    """페이지 타입별 통합 dispatcher."""
    old = old_path.read_text(encoding="utf-8") if old_path.exists() else ""
    new = new_path.read_text(encoding="utf-8") if new_path.exists() else ""
    if page == "entities.md":
        return _merge_entities_md(old, new)
    if page == "timeline.md":
        return _merge_timeline_md(old, new)
    if page == "overview.md":
        return _merge_overview_md(old, new, invoker=invoker)
    if page == "log.md":
        return _merge_log_md(old, new, project_slug)
    # claims.md / index.md / images.md: 새 버전 그대로 (manifests/sources에서 재생성된 것)
    return new if new else old


def _copy_wiki_pages(
    src_dir: Path,
    dst_dir: Path,
    *,
    dry_run: bool = False,
    project_slug: str = "",
    invoker: Callable[[str], str] | None = None,
) -> list[str]:
    """프로젝트 wiki 페이지를 볼트로 통합 흡수.

    충돌(같은 페이지 이미 존재) 시 페이지 타입별 머지 전략 적용:
    - overview.md: LLM 통합
    - entities.md: 헤더 단위 dedup + 정보량 많은 섹션 채택
    - timeline.md: 연도 dedup + 정렬
    - log.md: append-only
    - claims/index/images: 새 버전으로 교체 (이미 manifests에서 dedup됨)

    이전 옛 .synced.md 잔재가 있으면 그것도 통합 대상에 포함.
    """
    if not src_dir.exists():
        return []
    actions: list[str] = []
    pages = ("overview.md", "claims.md", "entities.md", "timeline.md", "images.md", "log.md", "index.md")

    for page in pages:
        src = src_dir / page
        if not src.exists():
            continue
        dst = dst_dir / page

        # 옛 .synced.md 잔재가 있으면 dst의 옛 파일과 합쳐 흡수 후 잔재 삭제
        synced_legacy = dst_dir / f"{page.rsplit('.', 1)[0]}.synced.md"

        if not dst.exists() and not synced_legacy.exists():
            # 신규 — 그냥 복사
            if dry_run:
                actions.append(f"[new] {page}")
                continue
            dst_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            actions.append(page)
            continue

        # 충돌 — 통합
        if dry_run:
            mode = "merge"
            if page in ("overview.md",):
                mode = "merge (LLM)"
            elif page in ("entities.md", "timeline.md", "log.md"):
                mode = "merge (deterministic)"
            else:
                mode = "replace"
            actions.append(f"[{mode}] {page}")
            continue

        # 옛 .synced.md 잔재가 있으면 dst와 먼저 통합 후 잔재 삭제
        if synced_legacy.exists() and dst.exists():
            try:
                pre_merged = _merge_wiki_page(
                    page, dst, synced_legacy,
                    project_slug=project_slug, invoker=invoker,
                )
                dst.write_text(pre_merged, encoding="utf-8")
                synced_legacy.unlink()
                actions.append(f"{page} (legacy .synced.md 흡수)")
            except Exception as exc:
                actions.append(f"{page} (legacy 흡수 실패: {exc})")

        # 새 src와 통합
        try:
            merged = _merge_wiki_page(
                page, dst, src,
                project_slug=project_slug, invoker=invoker,
            )
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(merged, encoding="utf-8")
            actions.append(page)
        except Exception as exc:
            # 통합 실패 시 옛 .synced.md 방식으로 fallback
            fallback = dst_dir / f"{page.rsplit('.', 1)[0]}.synced.md"
            shutil.copy2(src, fallback)
            actions.append(f"{page} (merge 실패 → {fallback.name})")

    return actions


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

    # 3. wiki 페이지 통합 흡수 (overview LLM 머지 + entities/timeline 결정적 머지)
    src_wiki = project_research_dir / "wiki" / project_topic_slug
    dst_wiki = vault_root / "wiki" / entity_slug
    record["wiki_pages"] = _copy_wiki_pages(
        src_wiki, dst_wiki,
        dry_run=options.dry_run,
        project_slug=project_topic_slug,
        invoker=invoker,
    )

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

    # claims_ledger.jsonl을 entity별로 분배해 vault manifests에 push
    try:
        ledger_stats, unmatched = _sync_ledger(research_dir, vault_root, result.topics, options=options)
        result.ledger = ledger_stats
        result.ledger_unmatched = unmatched
    except Exception as exc:
        result.errors.append({"phase": "ledger_sync", "reason": str(exc)})

    result.completed_at = _now_iso()
    return result


def _sync_ledger(
    research_dir: Path,
    vault_root: Path,
    topic_records: list[dict],
    *,
    options: SyncOptions = SyncOptions(),
) -> tuple[dict[str, int], int]:
    """claims_ledger.jsonl entry를 source_id 매칭 entity_slug로 분배해 vault에 push.

    Returns:
        (entity_slug → appended_count 딕셔너리, 매칭 실패 카운트)
    """
    ledger_path = research_dir / "claims_ledger.jsonl"
    if not ledger_path.exists():
        return {}, 0
    ledger = _read_jsonl(ledger_path)
    if not ledger:
        return {}, 0

    # source_id → vault entity_slug 매핑 빌드 (project sources.jsonl 기반)
    source_to_entity: dict[str, str] = {}
    for record in topic_records:
        project_topic = record.get("project_topic_slug", "")
        entity_slug = record.get("vault_entity_slug", "")
        if not project_topic or not entity_slug:
            continue
        sources_path = research_dir / "manifests" / project_topic / "sources.jsonl"
        if not sources_path.exists():
            continue
        for s in _read_jsonl(sources_path):
            sid = str(s.get("source_id") or "")
            if sid and sid not in source_to_entity:
                source_to_entity[sid] = entity_slug

    # ledger entry를 entity별로 분배
    by_entity: dict[str, list[dict]] = {}
    unmatched = 0
    for c in ledger:
        sid = str(c.get("source_id") or "")
        entity = source_to_entity.get(sid)
        if not entity:
            unmatched += 1
            continue
        by_entity.setdefault(entity, []).append(c)

    # 각 entity의 vault manifests/<entity>/claims.jsonl에 dedup-append
    stats: dict[str, int] = {}
    for entity, claims in by_entity.items():
        vault_claims_path = vault_root / "manifests" / entity / "claims.jsonl"
        if options.dry_run:
            existing = _read_jsonl(vault_claims_path) if vault_claims_path.exists() else []
            existing_ids = {str(c.get("claim_id", "")) for c in existing}
            new_count = sum(1 for c in claims if str(c.get("claim_id", "")) not in existing_ids)
            stats[entity] = new_count
        else:
            appended, _skipped = _dedup_claims_append(claims, vault_claims_path)
            stats[entity] = appended
    return stats, unmatched
