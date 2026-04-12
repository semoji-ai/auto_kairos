"""
Skeleton From Vault Module — vault wiki/claims → skeleton.json / outline.json

파이프라인 step_1a에서 실행:
1. source_ingest_status.json 완료 상태 확인
2. vault 02-research/wiki/<slug>/ + manifests/<slug>/claims.jsonl 로드
3. timeline / key_figures / key_episodes를 deterministic하게 구조화
4. skeleton.json, outline.json 저장
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from auto_agent.modules.research_entity_hub import (
    resolve_existing_entity_slug,
    resolve_topic_to_entity_section,
)

_PROGRESS_FILE: Path | None = None


def _progress(message: str, level: str = "info") -> None:
    print(f"[skeleton_from_vault] {message}", flush=True)
    if not _PROGRESS_FILE:
        return
    record = {"message": message, "level": level}
    with _PROGRESS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _slug(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (text or "").lower().strip())
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:60].strip("-")


def _get_research_root(status: dict | None = None) -> Path:
    if status and status.get("research_root"):
        return Path(status["research_root"])
    vault_dir = os.environ.get("KAIROS_VAULT_DIR", "")
    if vault_dir:
        return Path(vault_dir) / "02-research"
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("KAIROS_VAULT_DIR="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                return Path(value) / "02-research"
    raise RuntimeError("KAIROS_VAULT_DIR 환경변수가 설정되어 있지 않습니다.")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strip_front_matter(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1]
    return text


def _load_wiki_pages(research_root: Path, vault_slug: str) -> dict[str, str]:
    wiki_dir = research_root / "wiki" / resolve_existing_entity_slug(research_root, vault_slug)
    pages: dict[str, str] = {}
    if not wiki_dir.exists():
        return pages
    for md_file in wiki_dir.glob("*.md"):
        pages[md_file.name] = _strip_front_matter(md_file.read_text(encoding="utf-8"))
    return pages


def _load_jsonl(path: Path) -> list[dict]:
    items: list[dict] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def _load_claims_and_sources(research_root: Path, vault_slug: str) -> tuple[list[dict], list[dict]]:
    slug = resolve_existing_entity_slug(research_root, vault_slug)
    manifest_dir = research_root / "manifests" / slug
    claims = _load_jsonl(manifest_dir / "claims.jsonl")
    sources = _load_jsonl(manifest_dir / "sources.jsonl")
    return claims, sources


def _extract_summary_bullets(overview_text: str) -> list[str]:
    bullets: list[str] = []
    in_summary = False
    for raw_line in overview_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_summary = line.lower().startswith("## summary")
            continue
        if not in_summary:
            continue
        if line.startswith("- "):
            bullets.append(line[2:].strip())
        elif bullets and line:
            bullets[-1] = f"{bullets[-1]} {line}"
    return bullets


def _extract_timeline_entries(timeline_text: str, claims: list[dict]) -> list[dict]:
    entries: list[dict] = []
    for raw_line in timeline_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("- **"):
            continue
        match = re.match(r"- \*\*(.+?)\*\*\s*[—-]\s*(.+)", line)
        if not match:
            continue
        year = match.group(1).strip()
        body = match.group(2).strip()
        event = body
        significance = ""
        if ". " in body:
            event, significance = body.split(". ", 1)
        entries.append(
            {
                "year": year,
                "event": event.strip(),
                "significance": significance.strip() or body.strip(),
            }
        )
    if entries:
        return entries[:16]

    fallback: list[dict] = []
    for claim in claims:
        claim_text = claim.get("claim", "")
        year_match = re.search(r"(1[0-9]{3}|20[0-9]{2}|[0-9]{4}년(?:대)?(?:\s*[~–-]\s*[0-9]{4}년?)?)", claim_text)
        if not year_match:
            continue
        fallback.append(
            {
                "year": year_match.group(1),
                "event": claim_text[:120],
                "significance": claim.get("kind", "historical"),
            }
        )
    return fallback[:16]


def _extract_key_figures(entities_text: str, claims: list[dict]) -> list[dict]:
    figures: list[dict] = []
    in_people = False
    current: dict | None = None
    for raw_line in entities_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_people = line == "## 인물"
            continue
        if not in_people:
            continue
        if line.startswith("### "):
            if current:
                figures.append(current)
            name_line = line[4:].strip()
            name = re.sub(r"\s*\([^)]*\)$", "", name_line).strip()
            period_match = re.search(r"\(([^)]*)\)", name_line)
            current = {
                "name": name,
                "name_en": "",
                "role": "",
                "period": period_match.group(1).strip() if period_match else "",
                "significance": "",
            }
            continue
        if not current or not line.startswith("- "):
            continue
        payload = line[2:].strip()
        if payload.startswith("**역할**:"):
            current["role"] = payload.split(":", 1)[1].strip()
        elif payload.startswith("**의의**:") or payload.startswith("**경력 요약**:"):
            current["significance"] = payload.split(":", 1)[1].strip()
    if current:
        figures.append(current)
    if figures:
        return figures[:8]

    derived: list[dict] = []
    for claim in claims:
        text = claim.get("claim", "")
        names = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text)
        for name in names:
            derived.append(
                {
                    "name": name,
                    "name_en": name,
                    "role": claim.get("kind", ""),
                    "period": "",
                    "significance": text[:160],
                }
            )
    deduped = []
    seen = set()
    for item in derived:
        key = item["name"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:8]


def _extract_key_episodes(timeline: list[dict], claims: list[dict]) -> list[dict]:
    episodes: list[dict] = []
    for entry in timeline:
        hook = entry.get("significance") or entry.get("event", "")
        episodes.append(
            {
                "title": entry.get("event", "")[:100],
                "period": entry.get("year", ""),
                "narrative_role": entry.get("significance", "")[:160],
                "emotional_hook": hook[:160],
            }
        )
    preferred_kinds = {"marketing-history", "corporate-history", "anecdote", "historical", "ownership"}
    for claim in claims:
        if claim.get("kind") not in preferred_kinds:
            continue
        text = claim.get("claim", "")
        episodes.append(
            {
                "title": text[:80],
                "period": "",
                "narrative_role": claim.get("kind", ""),
                "emotional_hook": claim.get("evidence", "")[:160] or text[:160],
            }
        )
    deduped = []
    seen = set()
    for item in episodes:
        key = item["title"]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:8]


def _extract_sources(sources: list[dict]) -> list[dict]:
    extracted = []
    for source in sources[:10]:
        extracted.append(
            {
                "title": source.get("title", source.get("id", "source")),
                "url": source.get("url", ""),
                "reliability": source.get("quality_grade", source.get("reliability", "")),
            }
        )
    return extracted


def _chapter_count_for_duration(duration_minutes: int) -> int:
    if duration_minutes <= 2:
        return 3
    if duration_minutes <= 5:
        return 4
    if duration_minutes <= 10:
        return 5
    return 6


def _chunk_list(items: list, chunk_count: int) -> list[list]:
    if not items:
        return [[] for _ in range(chunk_count)]
    chunk_count = max(1, chunk_count)
    base, extra = divmod(len(items), chunk_count)
    chunks = []
    index = 0
    for chunk_idx in range(chunk_count):
        size = base + (1 if chunk_idx < extra else 0)
        chunks.append(items[index:index + size])
        index += size
    return chunks


def _clean_sentence(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", "", text or "")
    return re.sub(r"\s+", " ", text).strip(" -")


def _build_outline(
    topic: str,
    core_question: str,
    duration_minutes: int,
    summary_bullets: list[str],
    timeline: list[dict],
    key_figures: list[dict],
    key_episodes: list[dict],
) -> dict:
    chapter_count = _chapter_count_for_duration(duration_minutes)
    chapter_chunks = _chunk_list(timeline or key_episodes, chapter_count)
    if not any(chapter_chunks):
        chapter_chunks = _chunk_list(summary_bullets, chapter_count)

    title = topic
    duration_sec = max(60, duration_minutes * 60)
    total_scenes_estimate = max(4, min(100, chapter_count * 2))
    ratios = []
    for idx in range(chapter_count):
        if idx == 0:
            ratios.append(0.18)
        elif idx == chapter_count - 1:
            ratios.append(0.20)
        else:
            ratios.append(round((1.0 - 0.38) / max(1, chapter_count - 2), 4))
    ratio_sum = sum(ratios)
    ratios = [round(r / ratio_sum, 4) for r in ratios]

    chapters = []
    for idx, chunk in enumerate(chapter_chunks, start=1):
        act = 1 if idx == 1 else 3 if idx == chapter_count else 2
        key_points = []
        time_periods = []
        episode_titles = []
        for item in chunk:
            if isinstance(item, dict):
                event = _clean_sentence(item.get("event") or item.get("title") or item.get("narrative_role") or "")
                year = _clean_sentence(item.get("year") or item.get("period") or "")
                if event:
                    key_points.append(event)
                if year:
                    time_periods.append(year)
                if item.get("title"):
                    episode_titles.append(_clean_sentence(item["title"]))
            else:
                key_points.append(_clean_sentence(str(item)))
        if not key_points:
            key_points = summary_bullets[:2] or [f"{topic}의 핵심 구조 정리"]
        chapter_title = key_points[0][:50]
        purpose = key_points[1] if len(key_points) > 1 else key_points[0]
        scene_hints = [
            {
                "type": "title_card" if idx == 1 else "text_highlight",
                "note": chapter_title,
            }
        ]
        if time_periods:
            scene_hints.append({"type": "text_highlight", "note": f"시기: {time_periods[0]}"})
        if idx != 1 and time_periods:
            scene_hints.append({"type": "timeline", "note": "핵심 전환점 정리"})
        chapters.append(
            {
                "chapter_number": idx,
                "title": chapter_title,
                "act": act,
                "purpose": purpose[:180],
                "duration_ratio": ratios[idx - 1],
                "key_points": key_points[:5],
                "episodes": episode_titles[:3],
                "scene_hints": scene_hints[:3],
                "image_scenes": [],
                "research_focus": [
                    f"{chapter_title}의 핵심 맥락을 한 문장으로 정리할 수 있는가?",
                    f"{chapter_title}에서 반드시 보존해야 할 수치/연도는 무엇인가?",
                ],
                "emotional_arc": "도입" if idx == 1 else "확장" if idx < chapter_count else "정리",
                "time_period": " ~ ".join(dict.fromkeys(time_periods))[:80],
            }
        )

    if key_figures:
        chapters[0]["key_points"].append(f"핵심 인물: {key_figures[0]['name']}")
    flow_notes = {
        "hooks": summary_bullets[0] if summary_bullets else topic,
        "pacing": core_question or f"{topic}의 구조를 단계적으로 설명",
        "transitions": "도입 → 전개 → 전환점 → 결론 구조를 유지",
    }
    return {
        "title": title,
        "estimated_duration_sec": duration_sec,
        "total_scenes_estimate": total_scenes_estimate,
        "structure": {
            "act_1": "도입 — 왜 이 주제를 지금 봐야 하는지 제시",
            "act_2": "전개 — 핵심 전환점과 구조 설명",
            "act_3": "결말 — 현재적 의미와 takeaway 정리",
        },
        "chapters": chapters,
        "flow_notes": flow_notes,
    }


def build_skeleton_and_outline(project_dir: Path) -> tuple[dict, dict]:
    status_path = project_dir / "source_ingest_status.json"
    if not status_path.exists():
        raise RuntimeError("source_ingest_status.json이 없습니다.")

    _progress("ingest 결과 로드 중")
    status = _load_json(status_path)
    if status.get("status") != "completed" and status.get("status") != "skipped_existing":
        raise RuntimeError(f"source_ingest_status.json.status={status.get('status')} — completed 필요")

    brief = {}
    brief_path = project_dir / "editorial_brief.json"
    if brief_path.exists():
        brief = _load_json(brief_path)

    config = {}
    config_path = project_dir / "project_config.json"
    if config_path.exists():
        config = _load_json(config_path)

    research_root = _get_research_root(status)
    topic = brief.get("real_topic") or status.get("topic") or config.get("topic") or os.environ.get("PROJECT_NAME", "unknown")
    topic_slug = status.get("topic_slug") or _slug(topic)
    entity_slug = brief.get("entity_slug") or status.get("entity_slug", "")
    section_slug = brief.get("section_slug") or status.get("section_slug", "")
    resolved = resolve_topic_to_entity_section(research_root, topic_slug=topic_slug, entity_slug=entity_slug, section_slug=section_slug)
    vault_slug = resolved.entity_slug or topic_slug

    _progress("wiki overview 파싱 중")
    wiki_pages = _load_wiki_pages(research_root, vault_slug)
    _progress("claims manifest 읽는 중")
    claims, sources = _load_claims_and_sources(research_root, vault_slug)
    if not wiki_pages and not claims:
        raise RuntimeError(f"vault wiki/claims가 비어 있습니다: {vault_slug}")

    overview_text = wiki_pages.get("overview.md", "")
    timeline_text = wiki_pages.get("timeline.md", "")
    entities_text = wiki_pages.get("entities.md", "")
    summary_bullets = _extract_summary_bullets(overview_text)

    _progress("timeline 정리 중")
    timeline = _extract_timeline_entries(timeline_text, claims)
    _progress("key figures 추출 중")
    key_figures = _extract_key_figures(entities_text, claims)
    key_episodes = _extract_key_episodes(timeline, claims)

    skeleton = {
        "topic": topic,
        "topic_slug": topic_slug,
        "entity_slug": vault_slug,
        "section_slug": resolved.section_slug or section_slug,
        "timeline": timeline,
        "key_figures": key_figures,
        "key_episodes": key_episodes,
        "sources": _extract_sources(sources),
        "summary_bullets": summary_bullets[:6],
    }

    duration_minutes = int(config.get("duration_minutes") or 10)
    _progress("outline 생성 중")
    outline = _build_outline(
        topic=topic,
        core_question=brief.get("core_question", ""),
        duration_minutes=duration_minutes,
        summary_bullets=summary_bullets,
        timeline=timeline,
        key_figures=key_figures,
        key_episodes=key_episodes,
    )
    return skeleton, outline


def main() -> None:
    global _PROGRESS_FILE
    progress_path = os.environ.get("PROGRESS_FILE", "").strip()
    if progress_path:
        _PROGRESS_FILE = Path(progress_path)

    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    skeleton_path = project_dir / "skeleton.json"
    outline_path = project_dir / "outline.json"

    if skeleton_path.exists() and outline_path.exists():
        _progress("skeleton.json / outline.json 이미 존재 — 스킵")
        sys.exit(0)

    try:
        skeleton, outline = build_skeleton_and_outline(project_dir)
    except Exception as exc:
        _progress(str(exc), level="error")
        sys.exit(1)

    skeleton_path.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8")
    outline_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
    _progress("skeleton 저장 완료")
    _progress("outline 저장 완료")
    sys.exit(0)


if __name__ == "__main__":
    main()
