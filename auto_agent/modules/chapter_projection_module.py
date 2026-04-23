"""
Chapter Projection Module — vault wiki/claims → chapter_facts 변환

파이프라인 step_1b에서 실행 (flesh_research 대체):
1. outline.json + source_ingest_status.json 읽기
2. vault 02-research/wiki/<slug>/ + manifests/<slug>/claims.jsonl 로드
3. Claude API로 각 챕터에 필요한 claims/wiki 내용 투영
4. chapter_facts/chapter_{N}.json 생성 (claim_ids, source_ids 필드 포함)

vault wiki가 없으면 기존 flesh-researcher 에이전트 방식으로 fallback.
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


def _get_research_root() -> Path | None:
    """LLM Wiki research root 경로 반환. 없으면 None.

    우선순위:
    1. PROJECT_DIR/source_ingest_status.json의 research_root 필드
    2. KAIROS_VAULT_DIR/02-research (vault fallback)
    """
    # 1순위: source_ingest가 기록한 실제 research_root
    project_dir_env = os.environ.get("PROJECT_DIR", "")
    if project_dir_env:
        status_path = Path(project_dir_env) / "source_ingest_status.json"
        if status_path.exists():
            try:
                status = json.loads(status_path.read_text(encoding="utf-8"))
                rr = status.get("research_root", "")
                if rr and Path(rr).exists():
                    return Path(rr)
            except Exception:
                pass

    # 2순위: vault fallback
    vault_dir = os.environ.get("KAIROS_VAULT_DIR", "")
    if not vault_dir:
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("KAIROS_VAULT_DIR="):
                    vault_dir = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if vault_dir:
        return Path(vault_dir) / "02-research"
    return None


def _slug(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:60].strip("-")


def _resolve_slug(research_root: Path, topic_slug: str) -> str:
    """vault에서 실제로 존재하는 slug 반환. 하이픈↔언더스코어 둘 다 확인."""
    return resolve_existing_entity_slug(research_root, topic_slug)


def _load_wiki(research_root: Path, topic_slug: str) -> dict[str, str]:
    """vault wiki 페이지 로드 → {filename: content}. 하이픈↔언더스코어 둘 다 체크."""
    slug = _resolve_slug(research_root, topic_slug)
    wiki_dir = research_root / "wiki" / slug
    pages = {}
    if not wiki_dir.exists():
        return pages
    for md_file in wiki_dir.glob("*.md"):
        pages[md_file.name] = md_file.read_text(encoding="utf-8")
    return pages


def _load_claims(research_root: Path, topic_slug: str) -> list[dict]:
    """vault claims.jsonl 로드 → list of claim dicts. 하이픈↔언더스코어 둘 다 체크."""
    slug = _resolve_slug(research_root, topic_slug)
    claims_file = research_root / "manifests" / slug / "claims.jsonl"
    if not claims_file.exists():
        return []
    claims = []
    for line in claims_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                claims.append(json.loads(line))
            except Exception:
                pass
    return claims


def _load_sources(research_root: Path, topic_slug: str) -> list[dict]:
    """vault sources.jsonl 로드 → list of source dicts. 하이픈↔언더스코어 둘 다 체크."""
    slug = _resolve_slug(research_root, topic_slug)
    sources_file = research_root / "manifests" / slug / "sources.jsonl"
    if not sources_file.exists():
        return []
    sources = []
    for line in sources_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                sources.append(json.loads(line))
            except Exception:
                pass
    return sources


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _chapter_research_slots(chapter: dict) -> list[str]:
    title = _normalize_text(chapter.get("title", ""))
    purpose = _normalize_text(chapter.get("purpose", ""))
    focus = [
        _normalize_text(item)
        for item in chapter.get("research_focus", [])
        if _normalize_text(item)
    ]
    slots = [
        f"{title}에서 서사를 바꾸는 핵심 전환점은 무엇인가?",
        f"{title}에서 꼭 넣어야 할 날짜·기간·수치는 무엇인가?",
        f"{title}의 핵심 인물·기관은 누구이며 어떤 역할을 했는가?",
        f"{title}가 왜 중요했고 어떻게 다음 단계로 이어졌는가? {purpose}".strip(),
    ]
    slots.extend(focus[:3])
    deduped = []
    seen = set()
    for item in slots:
        normalized = _normalize_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def _generate_chapter_facts_via_api(
    chapter: dict,
    wiki_pages: dict[str, str],
    claims: list[dict],
    sources: list[dict],
    topic: str,
    real_topic: str,
    core_question: str,
) -> dict:
    """Claude API로 단일 챕터의 chapter_facts 생성."""
    try:
        import anthropic
    except ImportError:
        return _fallback_chapter_facts(chapter, claims)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return _fallback_chapter_facts(chapter, claims)

    chapter_title = chapter.get("title", "")
    chapter_focus = chapter.get("focus", chapter.get("description", ""))
    chapter_idx = chapter.get("index", chapter.get("chapter_number", 1))

    # wiki 내용 합치기 (overview + claims 우선)
    wiki_text = ""
    for key in ["overview.md", "claims.md", "entities.md", "timeline.md"]:
        if key in wiki_pages:
            wiki_text += f"\n## {key}\n{wiki_pages[key][:3000]}\n"
    # 나머지 페이지
    for key, content in wiki_pages.items():
        if key not in ["overview.md", "claims.md", "entities.md", "timeline.md"]:
            wiki_text += f"\n## {key}\n{content[:1000]}\n"

    # 관련 claims 필터링 (title/focus 키워드 기준)
    keywords = set((chapter_title + " " + chapter_focus).lower().split())
    relevant_claims = []
    for c in claims:
        statement = c.get("statement", c.get("claim_text", "")).lower()
        if any(kw in statement for kw in keywords if len(kw) > 2):
            relevant_claims.append(c)
    # 최대 15개
    relevant_claims = relevant_claims[:15]
    if not relevant_claims:
        relevant_claims = claims[:10]

    claims_text = json.dumps(relevant_claims, ensure_ascii=False, indent=2)[:4000]

    # source_ids 목록
    source_ids = [s.get("source_id", "") for s in sources[:20]]

    chapter_slots = _chapter_research_slots(chapter)
    prompt = f"""리서치 자료를 바탕으로 아래 챕터의 writer-facing evidence pack을 정리해주세요.

**주제:** {topic}
**실제 설명 주제(real_topic):** {real_topic or topic}
**핵심 질문(core_question):** {core_question}

**챕터 {chapter_idx}: {chapter_title}**
챕터 포커스: {chapter_focus}

**이 챕터에서 커버해야 할 질문 슬롯:**
{"".join(f"- {slot}\n" for slot in chapter_slots[:6])}

**Wiki 자료:**
{wiki_text[:4000]}

**관련 Claim 목록:**
{claims_text}

위 자료를 바탕으로 이 챕터를 2~4문단으로 쓸 수 있게 JSON을 구성하세요.
- key_facts는 초고에 바로 쓸 수 있는 사실 앵커를 최소 3개 시도
- timeline_anchors는 시간 순서상 전환점 정리
- supporting_claims는 이 챕터와 직접 연결되는 claim_id 목록
- chapter_question_coverage는 위 질문 슬롯 중 무엇이 커버됐는지 기록
- 아직 비는 부분은 evidence_gaps에, 초고를 막는 공백은 draft_blockers에 분리

반드시 아래 형식으로만 응답하세요 (JSON만, 설명 없이):
{{
  "chapter": {chapter_idx},
  "title": "{chapter_title}",
  "key_facts": [
    {{
      "fact": "핵심 사실 1 (한 문장)",
      "detail": "구체적 수치나 맥락",
      "claim_ids": ["claim_id_1"],
      "source_ids": ["source_id_1"]
    }}
  ],
  "timeline_anchors": ["시간순 전환점 1"],
  "key_entities": ["주요 인물/기관/사건"],
  "key_numbers": ["중요 수치/날짜"],
  "supporting_claims": ["claim_id_1"],
  "chapter_question_coverage": [
    {{"question": "질문 슬롯", "covered": true, "evidence": "근거 요약"}}
  ],
  "evidence_gaps": ["추가 보강이 필요하지만 초고는 가능한 공백"],
  "draft_blockers": ["초고를 쓰기 어렵게 만드는 핵심 공백"],
  "narrative_role": "이 챕터가 전체 이야기에서 하는 역할",
  "claim_ids": [],
  "source_ids": []
}}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        if "```" in text:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if m:
                text = m.group(1)
        result = json.loads(text)
        # claim_ids, source_ids 집계
        all_claim_ids = list({c["claim_id"] for c in relevant_claims if "claim_id" in c})
        result["claim_ids"] = result.get("claim_ids") or all_claim_ids[:10]
        result["source_ids"] = result.get("source_ids") or source_ids[:10]
        return result
    except Exception as e:
        print(f"[chapter_projection] 챕터 {chapter_idx} API 실패: {e}", flush=True)
        return _fallback_chapter_facts(chapter, claims)


def _fallback_chapter_facts(chapter: dict, claims: list[dict]) -> dict:
    """API 실패 시 기본 chapter_facts 구조."""
    chapter_idx = chapter.get("index", chapter.get("chapter_number", 1))
    chapter_title = chapter.get("title", f"챕터 {chapter_idx}")
    slots = _chapter_research_slots(chapter)
    related_claims = []
    title_tokens = [token for token in _normalize_text(chapter_title).lower().split() if len(token) >= 2]
    for claim in claims[:12]:
        text = _normalize_text(
            " ".join(
                str(claim.get(key, ""))
                for key in ("claim", "statement", "claim_text", "evidence")
            )
        ).lower()
        if any(token in text for token in title_tokens[:6]):
            related_claims.append(claim)
    supporting_claim_ids = [claim.get("claim_id", "") for claim in related_claims if claim.get("claim_id")]
    key_facts = []
    for claim in related_claims[:3]:
        fact = _normalize_text(claim.get("claim") or claim.get("statement") or claim.get("claim_text") or "")
        if not fact:
            continue
        key_facts.append(
            {
                "fact": fact,
                "detail": _normalize_text(claim.get("evidence", "")),
                "claim_ids": [claim.get("claim_id", "")] if claim.get("claim_id") else [],
                "source_ids": [source_id for source_id in claim.get("source_ids", []) if source_id],
            }
        )
    draft_blockers = []
    if len(key_facts) < 2:
        draft_blockers.append("관련 claim이 부족해 초고 factual anchor가 얕음")
    if len(slots) >= 3:
        draft_blockers.append("질문 슬롯 커버 여부를 후속 리서치로 다시 확인 필요")
    return {
        "chapter": chapter_idx,
        "title": chapter_title,
        "key_facts": key_facts,
        "timeline_anchors": [item["fact"] for item in key_facts[:2]],
        "key_entities": [],
        "key_numbers": [],
        "supporting_claims": supporting_claim_ids[:8],
        "chapter_question_coverage": [
            {"question": slot, "covered": False, "evidence": "fallback only"}
            for slot in slots[:4]
        ],
        "evidence_gaps": slots[:4],
        "draft_blockers": draft_blockers,
        "narrative_role": chapter.get("description", chapter.get("purpose", "")),
        "claim_ids": supporting_claim_ids[:10],
        "source_ids": [],
        "_source": "fallback",
    }


def main():
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))

    # 1. outline.json 읽기
    outline_path = project_dir / "outline.json"
    if not outline_path.exists():
        print("[chapter_projection] outline.json 없음 — 스킵", flush=True)
        sys.exit(1)

    try:
        outline = json.loads(outline_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[chapter_projection] outline.json 파싱 실패: {e}", flush=True)
        sys.exit(1)

    # 2. editorial_brief에서 topic 정보
    brief_path = project_dir / "editorial_brief.json"
    topic = ""
    real_topic = ""
    core_question = ""
    if brief_path.exists():
        try:
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            topic = brief.get("real_topic") or brief.get("_topic", "")
            real_topic = brief.get("real_topic", "")
            core_question = brief.get("core_question", "")
        except Exception:
            pass

    if not topic:
        config_path = project_dir / "project_config.json"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text(encoding="utf-8"))
                topic = cfg.get("topic", "")
            except Exception:
                pass
    if not topic:
        topic = os.environ.get("PROJECT_NAME", "unknown")

    topic_slug = _slug(topic)
    entity_slug = ""

    # 3. source_ingest_status.json에서 실제 slug 읽기 (더 정확)
    status_path = project_dir / "source_ingest_status.json"
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            topic_slug = status.get("topic_slug", topic_slug)
            topic = status.get("topic", topic)
            entity_slug = status.get("entity_slug", "")
        except Exception:
            pass

    # editorial_brief.json에서도 entity_slug 읽기 (status.json보다 우선)
    brief_path = project_dir / "editorial_brief.json"
    if brief_path.exists():
        try:
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            entity_slug = brief.get("entity_slug", entity_slug)
        except Exception:
            pass

    # vault 검색에 사용할 slug 결정 (entity_slug 우선, 없으면 topic_slug)
    research_root = _get_research_root()
    resolved = resolve_topic_to_entity_section(
        research_root,
        topic_slug=topic_slug,
        entity_slug=entity_slug,
        section_slug="",
    ) if research_root else None
    if resolved and resolved.entity_slug:
        entity_slug = resolved.entity_slug

    vault_slug = entity_slug if entity_slug else topic_slug
    print(f"[chapter_projection] 주제: {topic} (vault_slug: {vault_slug})", flush=True)

    # 4. vault wiki/claims 로드
    wiki_pages: dict[str, str] = {}
    claims: list[dict] = []
    sources: list[dict] = []

    if research_root:
        wiki_pages = _load_wiki(research_root, vault_slug)
        claims = _load_claims(research_root, vault_slug)
        sources = _load_sources(research_root, vault_slug)
        print(f"[chapter_projection] vault wiki: {len(wiki_pages)}페이지, claims: {len(claims)}개", flush=True)
    else:
        print("[chapter_projection] vault 없음 — wiki 없이 진행", flush=True)

    # 5. chapter_facts/ 디렉토리 생성
    chapter_facts_dir = project_dir / "chapter_facts"
    chapter_facts_dir.mkdir(exist_ok=True)

    # 6. outline에서 챕터 목록 추출
    chapters = outline.get("chapters", [])
    if not chapters:
        # 다양한 outline 구조 대응
        if isinstance(outline, list):
            chapters = outline
        elif "outline" in outline:
            chapters = outline["outline"]

    if not chapters:
        print("[chapter_projection] outline에서 챕터를 찾을 수 없음", flush=True)
        sys.exit(1)

    print(f"[chapter_projection] 총 {len(chapters)}개 챕터 처리", flush=True)

    # 7. 챕터별 projection
    generated = 0
    skipped = 0
    for i, chapter in enumerate(chapters):
        # 챕터 인덱스 결정
        chapter_idx = chapter.get("index", chapter.get("chapter_number", i + 1))
        if isinstance(chapter_idx, str):
            try:
                chapter_idx = int(chapter_idx)
            except ValueError:
                chapter_idx = i + 1

        out_path = chapter_facts_dir / f"chapter_{chapter_idx:02d}.json"

        # resume: 이미 존재하면 스킵
        if out_path.exists():
            print(f"  [스킵] chapter_{chapter_idx:02d}.json 이미 존재", flush=True)
            skipped += 1
            continue

        print(f"  [생성] chapter_{chapter_idx:02d}: {chapter.get('title', '')}...", flush=True)

        if wiki_pages or claims:
            facts = _generate_chapter_facts_via_api(
                chapter=chapter,
                wiki_pages=wiki_pages,
                claims=claims,
                sources=sources,
                topic=topic,
                real_topic=real_topic,
                core_question=core_question,
            )
        else:
            facts = _fallback_chapter_facts(chapter, [])

        # chapter 인덱스 정규화
        facts["chapter"] = chapter_idx
        if "title" not in facts or not facts["title"]:
            facts["title"] = chapter.get("title", f"챕터 {chapter_idx}")

        out_path.write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
        generated += 1

    print(f"[chapter_projection] 완료 — 생성: {generated}개, 스킵: {skipped}개", flush=True)

    # 생성된 chapter_facts가 모두 빈 상태면 실패로 처리
    if generated > 0:
        facts_dir = project_dir / "chapter_facts"
        all_empty = all(
            not json.loads(p.read_text(encoding="utf-8")).get("key_facts")
            for p in facts_dir.glob("chapter_*.json")
        )
        if all_empty:
            print("[chapter_projection] FATAL: 모든 챕터 key_facts 비어 있음 — 리서치 데이터 없음", flush=True)
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
