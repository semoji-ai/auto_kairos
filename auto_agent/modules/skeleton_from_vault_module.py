"""
Skeleton From Vault Module — brief/topic → skeleton.json / outline.json

파이프라인 step_1a에서 실행:
1. editorial_brief.json + project_config.json 로드
2. ingest 이전의 조사 프레임(skeleton/outline) 생성
3. vault 02-research/wiki/<slug>/ + manifests/<slug>/claims.jsonl 이 있으면 선택적으로 참고
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
from auto_agent.tools.wikipedia_lane import search_wikipedia, fetch_article_content
from auto_agent.tools.news_rss_lane import search_news
from auto_agent.tools.crossref_lane import search_academic

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


def _is_seed_noise_line(line: str) -> bool:
    lowered = (line or "").lower()
    if not line:
        return True
    if lowered.startswith("title:") or lowered.startswith("url source:") or lowered.startswith("published time:"):
        return True
    if "upload.wikimedia.org" in lowered or "http://" in lowered or "https://" in lowered:
        return True
    if line.startswith("![") or line.startswith("[") or line.startswith("("):
        return True
    if "px-" in lowered or ".jpg" in lowered or ".png" in lowered or ".svg" in lowered:
        return True
    return False


def _extract_seed_timeline_from_wiki_content(text: str) -> list[dict]:
    entries: list[dict] = []
    fallback_entries: list[dict] = []
    seen: set[str] = set()
    event_keywords = ("창립", "설립", "출점", "확장", "진출", "합작", "전환", "성장", "출발", "운영", "개점", "전개")
    metric_keywords = ("매출액", "종업원", "자본금", "점포", "정규직", "임시직원", "본사 소재지")
    for raw_line in text.splitlines():
        line = _clean_sentence(raw_line)
        if _is_seed_noise_line(line):
            continue
        if any(keyword in line for keyword in metric_keywords):
            continue
        year_match = re.search(r"(19\d{2}|20\d{2})(?:년)?", line)
        if not year_match or len(line) < 18:
            continue
        event = line[:140].lstrip("* ").strip()
        if event in seen:
            continue
        seen.add(event)
        item = {
            "year": year_match.group(1),
            "event": event,
            "significance": event,
        }
        if any(keyword in line for keyword in event_keywords):
            entries.append(item)
        elif year_match.group(1) < "2020":
            fallback_entries.append(item)
        if len(entries) >= 6:
            break
    return (entries + fallback_entries)[:6]


def _extract_seed_figures_from_wiki_content(text: str) -> list[dict]:
    figures: list[dict] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = _clean_sentence(raw_line)
        if _is_seed_noise_line(line):
            continue
        if "창립자" in line or "회장" in line or "대표이사" in line or "핵심 인물" in line:
            parts = re.split(r"창립자|회장|대표이사|핵심 인물", line, maxsplit=1)
            if len(parts) < 2:
                continue
            name = _clean_sentence(parts[-1])[:80]
            name = re.sub(r"\s*\([^)]*\)", "", name).strip()
            if not name or name in seen or len(name) < 2:
                continue
            seen.add(name)
            figures.append({
                "name": name,
                "name_en": "",
                "role": "핵심 인물",
                "period": "",
                "significance": line[:160],
            })
        if len(figures) >= 4:
            break
    return figures


def _build_seed_research(topic: str, core_question: str) -> tuple[list[str], list[dict], list[dict], list[dict]]:
    query = core_question or topic
    summary_bullets: list[str] = []
    timeline: list[dict] = []
    source_rows: list[dict] = []
    key_figures: list[dict] = []

    wiki_results = search_wikipedia(query, limit=2)
    wiki_top = wiki_results[0] if wiki_results else {}
    wiki_url = wiki_top.get("url", "") if isinstance(wiki_top, dict) else ""
    wiki_content = fetch_article_content(wiki_url, char_limit=5000) if wiki_url else ""
    if wiki_top and not wiki_top.get("error"):
        source_rows.append({
            "title": wiki_top.get("title", topic),
            "url": wiki_url,
            "reliability": "reference",
        })
        snippet = _clean_sentence(wiki_top.get("snippet", ""))
        if snippet:
            summary_bullets.append(snippet)

    timeline.extend(_extract_seed_timeline_from_wiki_content(wiki_content))
    key_figures.extend(_extract_seed_figures_from_wiki_content(wiki_content))

    for line in wiki_content.splitlines():
        line = _clean_sentence(line)
        if _is_seed_noise_line(line):
            continue
        if len(summary_bullets) < 4 and 40 < len(line) < 220:
            if line not in summary_bullets:
                summary_bullets.append(line[:200])
        if len(summary_bullets) >= 4:
            break

    news_results = search_news(topic, limit=3, ko_only=True)
    for item in news_results[:2]:
        title = _clean_sentence(item.get("title", ""))
        if title:
            timeline.append({"year": "", "event": title, "significance": item.get("snippet", "")[:160] or title})
            source_rows.append({
                "title": item.get("title", title),
                "url": item.get("url", ""),
                "reliability": item.get("confidence", "medium"),
            })

    academic_results = search_academic(query, limit=2, papers_only=True)
    for item in academic_results[:1]:
        title = _clean_sentence(item.get("title", ""))
        if title and title not in summary_bullets:
            summary_bullets.append(title)
            source_rows.append({
                "title": item.get("title", title),
                "url": item.get("url", ""),
                "reliability": item.get("source", "paper"),
            })

    dedup_timeline = []
    seen_events = set()
    metric_keywords = ("매출액", "종업원", "자본금", "점포", "정규직", "임시직원")
    for item in timeline:
        event = item.get("event", "")
        if not event or event in seen_events:
            continue
        if any(keyword in event for keyword in metric_keywords):
            continue
        seen_events.add(event)
        dedup_timeline.append(item)

    dedup_figures = []
    seen_figures = set()
    for item in key_figures:
        name = item.get("name", "")
        if not name or name in seen_figures:
            continue
        seen_figures.add(name)
        dedup_figures.append(item)

    return summary_bullets[:6], dedup_timeline[:6], source_rows[:6], dedup_figures[:4]


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


def _build_outline_with_llm(
    topic: str,
    brief: dict,
    skeleton: dict,
    duration_minutes: int,
) -> dict | None:
    """Opus LLM을 호출해 editorial_brief + skeleton 기반 outline을 생성한다.

    Returns:
        outline dict (chapters 포함) or None (실패 시 fallback)
    """
    import subprocess
    chapter_count = _chapter_count_for_duration(duration_minutes)
    core_question = brief.get("core_question", "")
    hook_angle = brief.get("hook_angle", "").strip()
    audience_takeaway = brief.get("audience_takeaway", "")
    excluded_angles = brief.get("excluded_angles", [])
    tone_goal = brief.get("tone_goal", "해설형")

    timeline = skeleton.get("timeline", [])
    key_figures = skeleton.get("key_figures", [])
    key_episodes = skeleton.get("key_episodes", [])
    summary_bullets = skeleton.get("summary_bullets", [])

    timeline_text = "\n".join(
        f"- {item.get('year', '')} {item.get('event', '')}".strip()
        for item in timeline[:10]
        if item.get("event")
    )
    figures_text = "\n".join(
        f"- {item.get('name', '')} ({item.get('role', '')})".strip()
        for item in key_figures[:6]
        if item.get("name")
    )
    episodes_text = "\n".join(
        f"- {item.get('title', '')}: {item.get('narrative_role', '')}".strip()
        for item in key_episodes[:8]
        if item.get("title")
    )

    prompt = f"""당신은 유튜브 영상 아웃라인 설계자입니다.

아래 editorial brief와 skeleton 리서치를 바탕으로, {duration_minutes}분 분량 영상의 아웃라인을 설계하세요.

## Editorial Brief
- 주제: {topic}
- 핵심 질문: {core_question}
- 후크 앵글: {hook_angle}
- 시청자 takeaway: {audience_takeaway}
- 톤/목표: {tone_goal}
- 제외할 관점: {', '.join(excluded_angles) if excluded_angles else '없음'}

## Skeleton 리서치 결과
### 타임라인
{timeline_text or '(아직 없음)'}

### 핵심 인물/기관
{figures_text or '(아직 없음)'}

### 핵심 에피소드
{episodes_text or '(아직 없음)'}

### 요약
{chr(10).join(f'- {b}' for b in summary_bullets[:5]) if summary_bullets else '(아직 없음)'}

## 요구사항
- 챕터 수: {chapter_count}개
- 각 챕터는 서사 흐름(도입 → 전개 → 전환 → 결론)에 맞게 설계
- 챕터 제목은 구체적이고 짧게 (20자 이내, 주제/내용 중심)
- research_focus: 다음 리서치 단계에서 반드시 찾아야 할 사실 기반 질문 3개
  - 전환점/사건 질문 1개
  - 날짜·수치·규모 질문 1개
  - 인물·기관·WHY/HOW 질문 1개
- purpose: 이 챕터가 전체 서사에서 하는 역할 (1~2문장)

## 출력 형식 (JSON만, 다른 텍스트 없이)
{{
  "title": "{topic}",
  "core_question": "{core_question}",
  "target_duration_minutes": {duration_minutes},
  "chapters": [
    {{
      "chapter_number": 1,
      "title": "챕터 제목",
      "act": 1,
      "purpose": "이 챕터가 전체 서사에서 하는 역할",
      "duration_ratio": 0.20,
      "research_focus": [
        "전환점/사건 질문",
        "날짜·수치·규모 질문",
        "인물·기관·WHY/HOW 질문"
      ],
      "key_points": []
    }}
  ]
}}
"""

    try:
        claude_bin = "claude"
        cmd = [
            claude_bin,
            "--model", "claude-opus-4-6",
            "--max-turns", "1",
            "--output-format", "text",
        ]
        env = os.environ.copy()
        env.pop("CLAUDECODE", None)
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
        )
        output = proc.stdout or ""
        # JSON 추출
        json_match = re.search(r'\{[\s\S]*\}', output)
        if json_match:
            data = json.loads(json_match.group())
            if data.get("chapters"):
                _progress(f"Opus outline 생성 완료: {len(data['chapters'])}개 챕터")
                return data
        _progress(f"Opus outline 파싱 실패 — fallback 사용. 출력: {output[:200]}", level="warn")
    except subprocess.TimeoutExpired:
        _progress("Opus outline 타임아웃 — fallback 사용", level="warn")
    except Exception as e:
        _progress(f"Opus outline 오류: {e} — fallback 사용", level="warn")
    return None


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
        # summary_bullets(core_question/hook_angle)는 챕터 제목으로 부적합 — topic 기반 기본 챕터 이름 사용
        default_chapter_names = [
            f"{topic}의 배경과 출발점",
            f"{topic}의 성장과 전환점",
            f"{topic}의 현재적 의미",
            f"{topic}의 핵심 사례",
            f"{topic}의 교훈과 전망",
        ]
        chapter_chunks = _chunk_list(
            [{"title": name} for name in default_chapter_names[:chapter_count]],
            chapter_count,
        )

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
        # 짧은 키워드 추출 (챕터 제목 전체를 질문에 반복하면 매칭률 저하)
        _title_keyword = chapter_title.split("의 ")[-1] if "의 " in chapter_title else chapter_title
        _title_keyword = _title_keyword[:20]
        focus_questions = [
            f"{_title_keyword} 관련 서사를 바꾼 핵심 전환점과 사건은?",
            f"{_title_keyword} 관련 초고에 넣어야 할 날짜·기간·수치는?",
        ]
        if purpose and purpose != chapter_title:
            focus_questions.append(f"{_title_keyword}이 왜 중요했고 어떤 전략·배경으로 이어졌는가?")
        elif idx == 1:
            focus_questions.append(f"{_title_keyword}이 이후 전개의 출발점이 된 이유는?")
        elif idx == chapter_count:
            focus_questions.append(f"{_title_keyword}의 현재적 의미와 takeaway는?")
        else:
            focus_questions.append(f"{_title_keyword} 관련 핵심 인물·기관은 누구이며 어떤 역할을 했는가?")
        dedup_focus = []
        seen_focus = set()
        for question in focus_questions:
            normalized = _clean_sentence(question)
            if not normalized or normalized in seen_focus:
                continue
            seen_focus.add(normalized)
            dedup_focus.append(normalized)
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
                "research_focus": dedup_focus[:3],
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
    brief = {}
    brief_path = project_dir / "editorial_brief.json"
    if brief_path.exists():
        brief = _load_json(brief_path)

    config = {}
    config_path = project_dir / "project_config.json"
    if config_path.exists():
        config = _load_json(config_path)

    topic = brief.get("real_topic") or brief.get("_topic") or config.get("topic") or os.environ.get("PROJECT_NAME", "unknown")
    if not topic:
        raise RuntimeError("topic을 결정할 수 없습니다.")

    topic_slug = _slug(topic)
    entity_slug = brief.get("entity_slug", "")
    section_slug = brief.get("section_slug", "")

    summary_bullets = []
    timeline = []
    key_figures = []
    key_episodes = []
    sources = []
    resolved_section_slug = section_slug

    research_root = None
    status_path = project_dir / "source_ingest_status.json"
    status = _load_json(status_path) if status_path.exists() else None
    try:
        research_root = _get_research_root(status)
    except Exception:
        research_root = None

    if research_root:
        resolved = resolve_topic_to_entity_section(
            research_root,
            topic_slug=topic_slug,
            entity_slug=entity_slug,
            section_slug=section_slug,
        )
        vault_slug = resolved.entity_slug or entity_slug or topic_slug
        resolved_section_slug = resolved.section_slug or section_slug

        _progress("기존 wiki/claims 참고 자료 확인 중")
        wiki_pages = _load_wiki_pages(research_root, vault_slug)
        claims, sources = _load_claims_and_sources(research_root, vault_slug)

        if wiki_pages or claims:
            overview_text = wiki_pages.get("overview.md", "")
            timeline_text = wiki_pages.get("timeline.md", "")
            entities_text = wiki_pages.get("entities.md", "")
            summary_bullets = _extract_summary_bullets(overview_text)
            timeline = _extract_timeline_entries(timeline_text, claims)
            key_figures = _extract_key_figures(entities_text, claims)
            key_episodes = _extract_key_episodes(timeline, claims)
    else:
        vault_slug = entity_slug or topic_slug

    if not summary_bullets or not timeline:
        _progress("lane 기반 뼈대 리서치 수행 중")
        seed_summary, seed_timeline, seed_sources, seed_figures = _build_seed_research(
            topic=topic,
            core_question=brief.get("core_question", "").strip(),
        )
        if not summary_bullets:
            summary_bullets = seed_summary
        if not timeline:
            timeline = seed_timeline
        if not sources:
            sources = seed_sources
        if not key_figures:
            key_figures = seed_figures

    if not summary_bullets:
        core_question = brief.get("core_question", "").strip()
        hook_angle = brief.get("hook_angle", "").strip()
        excluded_angles = [a.strip() for a in brief.get("excluded_angles", []) if a and a.strip()]
        summary_bullets = [item for item in [core_question, hook_angle] if item][:4]
        if excluded_angles:
            summary_bullets.append(f"제외할 관점: {', '.join(excluded_angles[:2])}")
        if not summary_bullets:
            summary_bullets = [f"{topic}의 핵심 구조를 먼저 설명", f"{topic}의 전환점을 따라 이야기 구성"]

    if not timeline:
        _progress("brief 기반 뼈대 리서치 프레임 구성 중")
        duration_minutes = int(config.get("duration_minutes") or 10)
        chapter_count = _chapter_count_for_duration(duration_minutes)
        base_prompts = [
            brief.get("core_question", "").strip(),
            brief.get("hook_angle", "").strip(),
            f"{topic}의 배경과 출발점",
            f"{topic}의 성장과 전환점",
            f"{topic}의 현재적 의미",
            f"{topic}에서 꼭 검증할 숫자와 연도",
        ]
        prompts = [p for p in base_prompts if p]
        for idx in range(chapter_count):
            prompt = prompts[idx] if idx < len(prompts) else f"{topic}의 핵심 장면 {idx + 1}"
            timeline.append(
                {
                    "year": "",
                    "event": prompt,
                    "significance": f"초기 뼈대 리서치 질문: {prompt}",
                }
            )

    if not key_episodes:
        key_episodes = [
            {
                "title": item.get("event", "")[:100],
                "period": item.get("year", ""),
                "narrative_role": item.get("significance", "")[:160],
                "emotional_hook": item.get("significance", item.get("event", ""))[:160],
            }
            for item in timeline[:8]
        ]

    skeleton = {
        "topic": topic,
        "topic_slug": topic_slug,
        "entity_slug": vault_slug,
        "section_slug": resolved_section_slug,
        "timeline": timeline,
        "key_figures": key_figures,
        "key_episodes": key_episodes,
        "sources": _extract_sources(sources),
        "summary_bullets": summary_bullets[:6],
        "source_mode": "vault" if sources else "skeleton_research_first",
        "research_seed_questions": [item.get("event", "") for item in timeline[:6] if item.get("event")],
    }

    duration_minutes = int(config.get("duration_minutes") or 10)
    _progress("outline 생성 중 (Opus)")
    outline = _build_outline_with_llm(
        topic=topic,
        brief=brief,
        skeleton=skeleton,
        duration_minutes=duration_minutes,
    )
    if outline is None:
        _progress("Opus outline 실패 — Python fallback 사용")
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
