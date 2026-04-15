"""
Source Ingest Module — ResearchAgent 기반 소스 수집

파이프라인 step_1_ingest에서 실행:
1. vault 02-research에 이미 해당 topic_slug 위키가 있으면 스킵 (resume)
2. ResearchAgent prepare-session → Claude CLI 에이전트 수집 → ingest-bundle → finalize-session
3. 출력: $KAIROS_VAULT_DIR/02-research/wiki/<slug>/, manifests/<slug>/
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_CLAUDE_MODEL = "sonnet"


def _get_claude_model() -> str:
    return (
        os.environ.get("AUTO_KAIROS_CLAUDE_MODEL")
        or os.environ.get("CLAUDE_MODEL")
        or DEFAULT_CLAUDE_MODEL
    )

from auto_agent.modules.research_entity_hub import resolve_existing_entity_slug

def _candidate_research_agent_dirs() -> list[Path]:
    """ResearchAgent 설치 후보 경로를 우선순위대로 반환."""
    repo_projects_dir = Path(__file__).resolve().parents[3]
    env_dir = os.environ.get("RESEARCH_AGENT_DIR", "").strip()
    candidates = []
    if env_dir:
        candidates.append(Path(env_dir).expanduser())
    candidates.extend(
        [
            repo_projects_dir / "ResearchAgent",
            repo_projects_dir / "researchagent",
            Path("/Users/jleavens_macmini/Projects/ResearchAgent"),
            Path("/Users/jleavens_macmini/Projects/researchagent"),
        ]
    )
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def _resolve_research_agent_paths(candidate_dirs: list[Path] | tuple[Path, ...] | None = None) -> tuple[Path, Path, Path]:
    """ResearchAgent 디렉터리와 launcher/vault script 경로를 해석."""
    checked: list[str] = []
    for research_agent_dir in candidate_dirs or _candidate_research_agent_dirs():
        launcher = research_agent_dir / "scripts" / "research_launcher.py"
        vault_script = research_agent_dir / "scripts" / "research_vault.py"
        checked.append(str(launcher))
        if launcher.exists() and vault_script.exists():
            return research_agent_dir.resolve(), launcher.resolve(), vault_script.resolve()
    checked_block = "\n  - ".join(checked) if checked else "(none)"
    raise FileNotFoundError(
        "ResearchAgent launcher를 찾지 못했습니다. 확인한 경로:\n"
        f"  - {checked_block}"
    )


def _get_research_root(project_dir: Path) -> Path:
    """리서치 데이터 저장 경로: output/<uuid>/research/ (볼트가 아님)."""
    root = project_dir / "research"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _get_vault_research_root() -> Path:
    """볼트 02-research 경로 (seed/sync 전용)."""
    vault_dir = os.environ.get("KAIROS_VAULT_DIR", "")
    if vault_dir:
        return Path(vault_dir) / "02-research"
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("KAIROS_VAULT_DIR="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return Path(val) / "02-research"
    raise RuntimeError("KAIROS_VAULT_DIR 환경변수가 설정되어 있지 않습니다.")


def _seed_from_vault(output_research_root: Path, vault_research_root: Path, slugs: list[str]) -> None:
    """볼트 wiki/manifests → output/research 로 seed 복사. 실패 시 경고만."""
    import shutil
    for subdir in ("wiki", "manifests"):
        for slug in slugs:
            if not slug:
                continue
            src = vault_research_root / subdir / slug
            if not src.exists():
                continue
            dst = output_research_root / subdir / slug
            try:
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"[source_ingest] seed: {src} → {dst}", flush=True)
            except Exception as e:
                print(f"[source_ingest] seed 복사 실패 (무시): {src} → {e}", flush=True)


def _slug(text: str) -> str:
    """topic 텍스트 → URL-safe slug."""
    import re
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:60].strip("-")




def _run_launcher(args: list, research_root: Path, research_agent_dir: Path, launcher: Path) -> dict:
    """research_launcher.py 호출 → JSON 결과 파싱."""
    env = os.environ.copy()
    env["LLM_WIKI_RESEARCH_DIR"] = str(research_root)
    env["RESEARCH_AGENT_DIR"] = str(research_agent_dir)

    cmd = [sys.executable, str(launcher)] + args + ["--vault-dir", str(research_root)]
    print(f"[source_ingest] 실행: {' '.join(cmd[:6])}...", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(research_agent_dir))
    if result.returncode != 0:
        print(f"[source_ingest] STDERR: {result.stderr[-500:]}", flush=True)
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def _count_manifest_records(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _build_chapter_research_slots(chapter: dict[str, Any]) -> list[dict[str, str]]:
    title = _normalize_text(chapter.get("title", ""))
    purpose = _normalize_text(chapter.get("purpose", ""))
    time_period = _normalize_text(chapter.get("time_period", ""))
    research_focus = [
        _normalize_text(item)
        for item in chapter.get("research_focus", [])
        if _normalize_text(item)
    ]
    key_points = [
        _normalize_text(item)
        for item in chapter.get("key_points", [])
        if _normalize_text(item)
    ]
    context_base = purpose or " / ".join(key_points[:2]) or title
    slots = [
        {
            "kind": "transition",
            "prompt": f"{title}에서 서사를 바꾸는 핵심 사건·전환점은 무엇인가? {context_base}".strip(),
        },
        {
            "kind": "date_number",
            "prompt": f"{title}에서 초고에 반드시 넣어야 할 날짜·기간·숫자는 무엇인가? {time_period}".strip(),
        },
        {
            "kind": "actor",
            "prompt": f"{title}를 움직인 핵심 인물·기관·주체는 누구이며 각자의 역할은 무엇인가?".strip(),
        },
        {
            "kind": "why_how",
            "prompt": f"{title}가 왜 중요했고 어떻게 다음 단계로 이어졌는가? {context_base}".strip(),
        },
    ]
    for question in research_focus[:3]:
        slots.append({"kind": "outline_focus", "prompt": question})
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for slot in slots:
        prompt = _normalize_text(slot.get("prompt", ""))
        if not prompt or prompt in seen:
            continue
        seen.add(prompt)
        deduped.append({"kind": slot.get("kind", ""), "prompt": prompt})
    return deduped


def _build_outline_requirements(outline: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(outline, dict):
        return []
    chapters = outline.get("chapters", [])
    requirements: list[dict[str, Any]] = []
    for idx, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            continue
        chapter_number = chapter.get("chapter_number", idx)
        title = _normalize_text(chapter.get("title", f"챕터 {chapter_number}"))
        purpose = _normalize_text(chapter.get("purpose", ""))
        requirements.append(
            {
                "chapter_number": chapter_number,
                "title": title,
                "purpose": purpose,
                "time_period": _normalize_text(chapter.get("time_period", "")),
                "research_focus": [slot["prompt"] for slot in _build_chapter_research_slots(chapter)],
                "required_slot_kinds": [slot["kind"] for slot in _build_chapter_research_slots(chapter)],
            }
        )
    return requirements


def _generate_overview_from_claims(
    wiki_dir: Path,
    claims_path: Path,
    sources_path: Path,
    topic: str,
    topic_slug: str,
) -> None:
    """claims.jsonl + sources.jsonl 에서 overview.md 자동 생성.

    overview.md가 플레이스홀더(300바이트 이하)인 경우에만 실행.
    """
    overview_path = wiki_dir / "overview.md"
    if overview_path.exists() and overview_path.stat().st_size > 300:
        return  # 이미 내용 있음

    claims: list[dict] = []
    if claims_path.exists():
        for line in claims_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                claims.append(json.loads(line))
            except Exception:
                pass

    sources: list[dict] = []
    if sources_path.exists():
        for line in sources_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                sources.append(json.loads(line))
            except Exception:
                pass

    if not claims:
        return

    # 신뢰도별 분류
    high = [c for c in claims if c.get("confidence") == "high"]
    medium = [c for c in claims if c.get("confidence") == "medium"]
    low_conf = [c for c in claims if c.get("confidence") not in ("high", "medium")]

    lines = [
        f"---",
        f'doc_type: "wiki-page"',
        f'topic: "{topic}"',
        f'topic_slug: "{topic_slug}"',
        f'page_type: "overview"',
        f'auto_generated: true',
        f"---",
        f"",
        f"# {topic} Overview",
        f"",
        f"## Summary",
        f"- 총 {len(claims)}개 claim, {len(sources)}개 소스 수집",
        f"- 신뢰도 high: {len(high)}개 / medium: {len(medium)}개 / 기타: {len(low_conf)}개",
        f"",
        f"## Key Claims (High Confidence)",
    ]
    for c in high[:15]:
        lines.append(f"- {c.get('claim', '')}")
    if medium:
        lines.append("")
        lines.append("## Additional Claims (Medium Confidence)")
        for c in medium[:10]:
            lines.append(f"- {c.get('claim', '')}")
    if sources:
        lines.append("")
        lines.append("## Sources")
        for s in sources[:10]:
            title = s.get("title") or s.get("url") or ""
            url = s.get("url") or ""
            if url and title != url:
                lines.append(f"- [{title}]({url})")
            elif title:
                lines.append(f"- {title}")

    wiki_dir.mkdir(parents=True, exist_ok=True)
    overview_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[source_ingest] overview.md 자동 생성 완료 (claims={len(claims)}, sources={len(sources)})", flush=True)


def _validate_ingest_completion(
    *,
    research_root: Path,
    topic_slug: str,
    entity_slug: str = "",
    section_slug: str = "",
    finalize_payload: dict | None = None,
    outline_requirements: list[dict[str, Any]] | None = None,
) -> dict:
    finalized = finalize_payload or {}
    run_state = finalized.get("run_state") or {}
    snapshot = finalized.get("snapshot") or {}
    status = finalized.get("status") or {}

    canonical_slug = resolve_existing_entity_slug(research_root, entity_slug or topic_slug)
    alt_slug = canonical_slug.replace("-", "_") if "-" in canonical_slug else canonical_slug.replace("_", "-")

    def _best_manifest_path(filename: str) -> Path:
        primary = research_root / "manifests" / canonical_slug / filename
        alt = research_root / "manifests" / alt_slug / filename
        return primary if primary.exists() else alt

    claims_path = _best_manifest_path("claims.jsonl")
    sources_path = _best_manifest_path("sources.jsonl")
    claims = _load_jsonl(claims_path)
    sources = _load_jsonl(sources_path)
    claim_count = len(claims)
    source_count = len(sources)

    wiki_dir = research_root / "wiki" / canonical_slug
    if not wiki_dir.exists():
        alt = canonical_slug.replace("-", "_") if "-" in canonical_slug else canonical_slug.replace("_", "-")
        wiki_dir = research_root / "wiki" / alt
    overview = wiki_dir / "overview.md"
    timeline = wiki_dir / "timeline.md"
    entities = wiki_dir / "entities.md"
    claims_md = wiki_dir / "claims.md"
    wiki_usable = overview.exists() and overview.stat().st_size > 300 if overview.exists() else False
    if not wiki_usable and claim_count >= 3:
        wiki_usable = True

    readiness = str(snapshot.get("specialist_readiness") or "")
    run_stage = str(run_state.get("stage") or "")
    run_status = str(run_state.get("status") or "")
    next_step = str(status.get("recommended_next_step") or "")

    outline_requirements = outline_requirements or []
    joined_claim_text = "\n".join(
        _normalize_text(
            " ".join(
                str(item.get(key, ""))
                for key in (
                    "claim",
                    "statement",
                    "claim_text",
                    "evidence",
                    "kind",
                )
            )
        )
        for item in claims
    ).lower()
    joined_source_text = "\n".join(
        _normalize_text(
            " ".join(
                str(item.get(key, ""))
                for key in (
                    "title",
                    "summary",
                    "source_kind",
                    "author",
                    "key_points",
                )
            )
        )
        for item in sources
    ).lower()
    chapter_readiness: list[dict[str, Any]] = []
    critical_unresolved: list[str] = []
    covered_question_count = 0
    total_question_count = 0
    chapter_ready_count = 0
    for requirement in outline_requirements:
        chapter_title = _normalize_text(requirement.get("title", ""))
        prompts = [
            _normalize_text(item)
            for item in requirement.get("research_focus", [])
            if _normalize_text(item)
        ]
        total_question_count += len(prompts)
        chapter_blob = " ".join([chapter_title, _normalize_text(requirement.get("purpose", "")), _normalize_text(requirement.get("time_period", ""))]).lower()
        matched_prompts = 0
        matched_slot_kinds: set[str] = set()
        for prompt in prompts:
            prompt_tokens = [token for token in prompt.lower().replace("?", " ").split() if len(token) >= 2]
            if any(token in joined_claim_text or token in joined_source_text for token in prompt_tokens[:8]):
                matched_prompts += 1
        title_tokens = [token for token in chapter_blob.split() if len(token) >= 2]
        related_claims = []
        for item in claims:
            text = _normalize_text(
                " ".join(
                    str(item.get(key, ""))
                    for key in ("claim", "statement", "claim_text", "evidence")
                )
            ).lower()
            if any(token in text for token in title_tokens[:8]):
                related_claims.append(item)
                continue
            if chapter_blob and chapter_blob in text:
                related_claims.append(item)
        related_source_ids = {
            source_id
            for claim in related_claims
            for source_id in claim.get("source_ids", [])
            if source_id
        }
        joined_related = "\n".join(
            _normalize_text(
                " ".join(
                    str(item.get(key, ""))
                    for key in ("claim", "statement", "claim_text", "evidence")
                )
            )
            for item in related_claims
        ).lower()
        kind_patterns = {
            "transition": ("전환", "분기", "전개", "확장", "변화", "출발"),
            "date_number": ("19", "20", "년", "월", "개", "엔", "%", "점포"),
            "actor": ("창업자", "대표", "회장", "회사", "산업", "주체", "기관"),
            "why_how": ("왜", "어떻게", "전략", "의미", "배경", "이유"),
        }
        for kind, patterns in kind_patterns.items():
            if any(pattern in joined_related for pattern in patterns):
                matched_slot_kinds.add(kind)
        draft_blockers: list[str] = []
        if len(related_claims) < 2:
            draft_blockers.append("관련 claim 부족")
        if len(related_source_ids) < 1:
            draft_blockers.append("관련 source 부족")
        if matched_prompts < max(1, min(2, len(prompts))):
            draft_blockers.append("research_focus coverage 부족")
        if len(matched_slot_kinds) < 3:
            draft_blockers.append("전환점/숫자/인물/WHY-HOW 슬롯 coverage 부족")
        chapter_ready = not draft_blockers and matched_prompts >= max(1, len(prompts) // 2)
        if chapter_ready:
            chapter_ready_count += 1
        else:
            if matched_prompts < max(1, len(prompts) // 2):
                draft_blockers.append("must-answer coverage 부족")
            critical_unresolved.append(f"{chapter_title}: {', '.join(dict.fromkeys(draft_blockers))}")
        covered_question_count += matched_prompts
        chapter_readiness.append(
            {
                "chapter_number": requirement.get("chapter_number"),
                "title": chapter_title,
                "claim_count": len(related_claims),
                "source_count": len(related_source_ids),
                "matched_question_count": matched_prompts,
                "total_question_count": len(prompts),
                "matched_slot_kinds": sorted(matched_slot_kinds),
                "draft_ready": chapter_ready,
                "draft_blockers": draft_blockers,
            }
        )

    must_answer_coverage = round(
        covered_question_count / total_question_count, 4
    ) if total_question_count else 1.0
    required_ready_chapters = len(outline_requirements)
    if len(outline_requirements) >= 5:
        required_ready_chapters = len(outline_requirements) - 1
    draft_ready = bool(outline_requirements) and chapter_ready_count >= required_ready_chapters
    if not outline_requirements:
        draft_ready = claim_count >= 4 and source_count >= 2 and wiki_usable

    issues: list[str] = []
    if claim_count < 4:
        issues.append(f"claim_count={claim_count} < 4")
    if source_count < 2:
        issues.append(f"source_count={source_count} < 2")
    if not wiki_usable:
        issues.append("wiki not usable")
    if not timeline.exists() or timeline.stat().st_size <= 120:
        issues.append("timeline not usable")
    if not entities.exists() or entities.stat().st_size <= 80:
        issues.append("entities not usable")
    if not claims_md.exists() or claims_md.stat().st_size <= 120:
        issues.append("claims wiki not usable")
    if run_stage != "packaging" or run_status != "completed":
        issues.append(f"finalize-session not completed: {run_stage or 'n/a'}/{run_status or 'n/a'}")
    if must_answer_coverage < 0.6:
        issues.append(f"must_answer_coverage={must_answer_coverage:.2f} < 0.60")
    if outline_requirements and not draft_ready:
        issues.append("chapter coverage not draft-ready")

    return {
        "success": not issues,
        "canonical_slug": canonical_slug,
        "claim_count": claim_count,
        "source_count": source_count,
        "wiki_usable": wiki_usable,
        "readiness": readiness,
        "run_stage": run_stage,
        "run_status": run_status,
        "recommended_next_step": next_step,
        "issues": issues,
        "draft_ready": draft_ready,
        "chapter_readiness": chapter_readiness,
        "must_answer_coverage": must_answer_coverage,
        "critical_unresolved": critical_unresolved,
    }


def _build_research_query_with_llm(
    topic: str,
    brief: dict,
    outline: dict,
) -> str | None:
    """Opus를 호출해 outline 기반 최적 검색 쿼리를 생성한다.

    Returns:
        query 문자열 or None (실패 시 fallback)
    """
    core_question = brief.get("core_question", "")
    hook_angle = brief.get("hook_angle", "")
    chapters = outline.get("chapters", []) if isinstance(outline, dict) else []

    chapter_lines = []
    for ch in chapters[:6]:
        title = ch.get("title", "")
        purpose = ch.get("purpose", "")
        focus = ch.get("research_focus", [])
        if title:
            chapter_lines.append(f"- 챕터 {ch.get('chapter_number','')}: {title}")
            if purpose:
                chapter_lines.append(f"  역할: {purpose}")
            for q in focus[:2]:
                chapter_lines.append(f"  질문: {q}")

    chapters_text = "\n".join(chapter_lines)

    prompt = f"""다음 유튜브 영상 기획을 바탕으로, 이 영상의 리서치에 가장 효과적인 검색 쿼리를 만들어주세요.

## 주제
{topic}

## 핵심 질문
{core_question}

## 후크 앵글
{hook_angle}

## 챕터 구조
{chapters_text}

## 요구사항
- 검색 엔진/Wikipedia/뉴스에서 이 영상에 필요한 사실·수치·전환점을 가장 잘 찾을 수 있는 쿼리
- 너무 포괄적이지 않고, 챕터 구조에서 공통으로 필요한 핵심 키워드 중심
- 한국어 또는 영어 중 더 효과적인 언어 선택
- 쿼리 하나만 출력 (설명 없이 쿼리 텍스트만)

쿼리:"""

    try:
        cmd = [
            "claude",
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
            timeout=60,
        )
        output = (proc.stdout or "").strip()
        # 앞뒤 불필요한 텍스트 제거 (첫 줄만 사용)
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        query = lines[0] if lines else ""
        # 너무 길거나 너무 짧으면 fallback
        if 5 <= len(query) <= 200:
            print(f"[source_ingest] Opus 쿼리 생성: {query}", flush=True)
            return query
        print(f"[source_ingest] Opus 쿼리 부적절 (len={len(query)}) — fallback 사용", flush=True)
    except subprocess.TimeoutExpired:
        print("[source_ingest] Opus 쿼리 생성 타임아웃 — fallback 사용", flush=True)
    except Exception as e:
        print(f"[source_ingest] Opus 쿼리 생성 오류: {e} — fallback 사용", flush=True)
    return None


def _supplement_weak_chapters(
    topic: str,
    topic_slug: str,
    critical_unresolved: list[str],
    chapter_map: dict,
    research_root: Path,
    research_agent_dir: Path,
    vault_script: Path,
    launcher: Path,
    run_id: str,
    entity_slug: str = "",
) -> bool:
    """약한 챕터만 타겟으로 LLM 보강 리서치를 실행하고 claim/source를 추가한다.

    Returns:
        True  — 보강 실행 완료 (claim 추가 여부와 무관)
        False — 실행 자체 실패
    """
    # 챕터별 미해결 질문 수집
    target_chapters = []
    for entry in critical_unresolved:
        # entry 형식: "챕터제목: blocker1, blocker2"
        chapter_title = entry.split(":")[0].strip()
        req = chapter_map.get(chapter_title, {})
        questions = req.get("research_focus", [])
        target_chapters.append({
            "title": chapter_title,
            "purpose": req.get("purpose", ""),
            "questions": questions[:6],
            "blockers": entry,
        })

    chapter_lines = []
    for ch in target_chapters:
        chapter_lines.append(f"\n### {ch['title']}")
        if ch["purpose"]:
            chapter_lines.append(f"목적: {ch['purpose']}")
        chapter_lines.append(f"부족한 항목: {ch['blockers']}")
        if ch["questions"]:
            chapter_lines.append("반드시 답해야 할 질문:")
            for q in ch["questions"]:
                chapter_lines.append(f"  - {q}")

    chapters_text = "\n".join(chapter_lines)

    prompt = f"""당신은 리서치 보강 에이전트입니다.

주제: {topic}

아래 챕터들이 초고를 쓰기에 부족한 리서치 상태입니다.
해당 챕터에 필요한 정보만 집중적으로 조사하여 claim과 source를 추가하세요.

{chapters_text}

**작업 지침:**
1. WebSearch / WebFetch로 각 챕터의 질문에 답하는 정보를 수집합니다.
2. 수집한 내용을 research_vault.py append-claim으로 claim에 추가합니다.
   - claim에는 chapter_title, evidence, source_url을 포함하세요.
3. 출처는 research_vault.py register-source로 등록합니다.
4. 각 챕터당 최소 전환점/날짜·수치/인물·기관/WHY·HOW 중 부족한 슬롯 1개 이상을 채우세요.
5. 정보를 찾지 못한 경우는 그냥 넘어가고 찾은 것만 추가하세요.

research root: {research_root}
research_vault.py: {vault_script}
topic_slug: {topic_slug}
entity_slug: {entity_slug or topic_slug}

완료 후 "SUPPLEMENT_COMPLETE"를 출력하세요.
"""

    claude_bin = "claude"
    claude_model = _get_claude_model()
    cmd = [
        claude_bin,
        "--model", claude_model,
        "--max-turns", "20",
        "--output-format", "text",
        "--allowedTools",
        "Bash,Read,Write,WebFetch,WebSearch,mcp__lane__wikipedia_search,mcp__lane__news_search",
    ]
    env = os.environ.copy()
    env["LLM_WIKI_RESEARCH_DIR"] = str(research_root)
    env["RESEARCH_AGENT_DIR"] = str(research_agent_dir)

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,  # 10분
        )
        output = proc.stdout or ""
        if "SUPPLEMENT_COMPLETE" in output:
            print("[source_ingest] 보강 에이전트 완료 신호 확인", flush=True)
        else:
            print(f"[source_ingest] 보강 에이전트 마지막 300자: {output[-300:]}", flush=True)
        return True
    except subprocess.TimeoutExpired:
        print("[source_ingest] 보강 에이전트 타임아웃 (10분)", flush=True)
        return False
    except Exception as e:
        print(f"[source_ingest] 보강 에이전트 오류: {e}", flush=True)
        return False


def _run_research_agent(topic: str, topic_slug: str, query: str, run_id: str,
                         research_root: Path, project_dir: Path,
                         core_question: str = "", excluded_angles: list = None,
                         outline: dict | None = None,
                         entity_slug: str = "", section_slug: str = "",
                         raw_slug: str = "",
                         research_agent_dir: Path | None = None,
                         launcher: Path | None = None,
                         vault_script: Path | None = None) -> dict:
    """Claude CLI로 ResearchAgent 실행 (자율 수집 루프)."""
    if research_agent_dir is None or launcher is None or vault_script is None:
        research_agent_dir, launcher, vault_script = _resolve_research_agent_paths()
    must_answer = core_question or f"{topic}의 핵심 구조와 맥락"
    exclude_str = "; ".join(excluded_angles or [])
    outline = outline or {}
    outline_chapters = outline.get("chapters", []) if isinstance(outline, dict) else []
    outline_lines = []
    outline_questions = []
    chapter_requirements = _build_outline_requirements(outline)
    chapter_contract_lines = []
    for chapter in outline_chapters[:6]:
        title = chapter.get("title", "")
        purpose = chapter.get("purpose", "")
        if title:
            outline_lines.append(f"- {title}: {purpose}".strip())
    for requirement in chapter_requirements[:6]:
        title = requirement.get("title", "")
        chapter_contract_lines.append(f"- {title}: 초고 2~4문단을 쓸 수 있도록 전환점·숫자·주체·WHY/HOW 근거를 확보")
        for question in requirement.get("research_focus", [])[:4]:
            outline_questions.append(question)

    # Wikipedia 스타일 wiki 경로 결정
    if entity_slug and section_slug:
        wiki_save_path = research_root / "wiki" / entity_slug
        wiki_path_note = f"""
**Wikipedia 스타일 wiki 저장 경로:**
- entity 폴더: {wiki_save_path}/
- 이 콘텐츠 섹션 파일: {wiki_save_path}/{section_slug}.md
- 공통 파일: {wiki_save_path}/overview.md, claims.md, entities.md, timeline.md
- manifests: {research_root}/manifests/{entity_slug}/claims.jsonl

**중요:** wiki 파일을 `{research_root}/wiki/{entity_slug}/` 아래에 저장하세요.
기존 섹션 파일({wiki_save_path}/*.md)이 있으면 내용을 보완하세요 (덮어쓰기 금지).
"""
    else:
        wiki_save_path = research_root / "wiki" / topic_slug
        wiki_path_note = f"wiki 저장 경로: {wiki_save_path}/"

    # 세션 번들 읽기 (없으면 빈 문자열로 계속 진행)
    session_brief_path = research_root / "raw" / topic_slug / run_id / "artifacts" / "session_bundle" / "session_brief.md"
    if session_brief_path.exists():
        session_brief = session_brief_path.read_text(encoding="utf-8")
    else:
        print(f"[source_ingest] session_brief.md 없음 — 기본 프롬프트로 수집 진행: {session_brief_path}", flush=True)
        session_brief = f"# Research Session Brief\ntopic: {topic}\nquery: {query}\nmust_answer: {must_answer}"

    outline_brief = ""
    if outline_lines or outline_questions or chapter_contract_lines:
        outline_brief = "\n<outline_brief>\n"
        if outline_lines:
            outline_brief += "## 초기 아웃라인\n" + "\n".join(outline_lines[:6]) + "\n"
        if chapter_contract_lines:
            outline_brief += "## 챕터별 수집 계약\n" + "\n".join(chapter_contract_lines[:6]) + "\n"
        if outline_questions:
            outline_brief += "## 이 리서치에서 반드시 답해야 할 질문\n" + "\n".join(f"- {q}" for q in outline_questions[:18]) + "\n"
        outline_brief += "</outline_brief>\n"

    # ResearchAgent SKILL.md 읽기
    skill_path = research_agent_dir / "SKILL.md"
    skill_content = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    # shared/search-tools 스킬 읽기 (lane 도구 사용 규칙 단일 소스)
    package_dir = Path(__file__).parent.parent
    search_tools_skill_path = package_dir / "data" / "skills" / "shared" / "search-tools.md"
    search_tools_content = search_tools_skill_path.read_text(encoding="utf-8") if search_tools_skill_path.exists() else ""

    # Claude CLI 프롬프트 구성
    prompt = f"""당신은 LLM Wiki Research 에이전트입니다.

아래 ResearchAgent SKILL 지침에 따라 리서치 세션을 완료하세요:

<skill>
{skill_content}
</skill>

<search_tools_skill>
{search_tools_content}
</search_tools_skill>

<session_brief>
{session_brief}
</session_brief>
{outline_brief}
**중요 지침:**
- research root: {research_root}
- topic: {topic}
- topic_slug: {topic_slug}
- run_id: {run_id}
- must_answer: {must_answer}
- excluded_angles: {exclude_str}

{wiki_path_note}

**작업:**
1. search_tools_skill 우선순위에 따라 lane 도구 먼저 사용 → 부족한 부분만 WebSearch/WebFetch fallback
2. 초기 outline의 chapter/research_focus를 조사 가이드로 사용하되, 각 챕터마다 초고 2~4문단을 쓸 수 있는 factual anchors를 확보합니다.
3. 각 챕터마다 최소한 전환점/사건, 날짜·기간·숫자, 핵심 인물·기관, WHY/HOW(원인·전략·의미) 근거를 1개 이상 확보하려고 시도합니다.
4. 찾지 못한 슬롯은 그냥 넘기지 말고 source note나 wiki/questions에 unresolved로 남겨서 나중 단계가 좁은 후속 리서치만 하게 만듭니다.
5. 각 소스를 source note로 정규화 (research_vault.py register-source 사용)
6. 핵심 claim 추출 및 검증 (research_vault.py append-claim 사용)
7. wiki 페이지 작성 (위 wiki 저장 경로에 따라 파일 배치)
8. research_launcher.py ingest-bundle 및 finalize-session 호출로 마무리

research root 경로: {research_root}
research_vault.py 경로: {vault_script}
research_launcher.py 경로: {launcher}

모든 파일을 위 research root 아래에 저장하세요. 완료되면 "RESEARCH_COMPLETE"를 출력하세요.
"""

    # source_ingest_status.json에 세션 정보 기록
    status_path = project_dir / "source_ingest_status.json"

    # Claude CLI 실행 (auto_agent/orchestrator/runner.py 패턴 따름 - stdin 방식)
    claude_bin = "claude"
    claude_model = _get_claude_model()
    cmd = [
        claude_bin,
        "--model", claude_model,
        "--max-turns", "50",
        "--output-format", "text",
        "--allowedTools",
        "Bash,Read,Write,Glob,Grep,WebFetch,WebSearch,Task,mcp__lane__wikipedia_search,mcp__lane__news_search,mcp__lane__academic_search",
    ]

    env = os.environ.copy()
    env["LLM_WIKI_RESEARCH_DIR"] = str(research_root)
    env["RESEARCH_AGENT_DIR"] = str(research_agent_dir)

    print(f"[source_ingest] Claude CLI 리서치 에이전트 시작 ({claude_model}, max-turns=50)...", flush=True)
    proc = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        env=env,
        timeout=1200,  # 20분
    )

    output = proc.stdout or ""
    if "RESEARCH_COMPLETE" in output:
        print("[source_ingest] 리서치 에이전트 완료 신호 확인", flush=True)
    else:
        print(f"[source_ingest] 에이전트 출력 마지막 500자: {output[-500:]}", flush=True)

    # 완료 여부와 관계없이 ingest-bundle + finalize-session 호출
    # raw_slug: entity_slug(pokemon) 우선 — run 디렉토리가 raw/{raw_slug}/{run_id}/로 저장됨
    _bundle_topic = raw_slug or entity_slug or topic
    ingest_payload = _run_launcher(
        ["ingest-bundle", "--topic", _bundle_topic, "--run-id", run_id, "--refresh"],
        research_root,
        research_agent_dir,
        launcher,
    )
    finalize_payload = _run_launcher(
        ["finalize-session", "--topic", _bundle_topic, "--run-id", run_id],
        research_root,
        research_agent_dir,
        launcher,
    )
    # overview.md 자동 생성 (플레이스홀더인 경우)
    canonical_slug = resolve_existing_entity_slug(research_root, entity_slug or topic_slug)
    _wiki_dir = research_root / "wiki" / canonical_slug
    if not _wiki_dir.exists():
        _alt = canonical_slug.replace("-", "_") if "-" in canonical_slug else canonical_slug.replace("_", "-")
        _wiki_dir = research_root / "wiki" / _alt
    _alt_slug = canonical_slug.replace("-", "_") if "-" in canonical_slug else canonical_slug.replace("_", "-")
    _claims_p = research_root / "manifests" / canonical_slug / "claims.jsonl"
    if not _claims_p.exists():
        _claims_p = research_root / "manifests" / _alt_slug / "claims.jsonl"
    _sources_p = research_root / "manifests" / canonical_slug / "sources.jsonl"
    if not _sources_p.exists():
        _sources_p = research_root / "manifests" / _alt_slug / "sources.jsonl"
    _generate_overview_from_claims(_wiki_dir, _claims_p, _sources_p, topic, topic_slug)

    validation = _validate_ingest_completion(
        research_root=research_root,
        topic_slug=topic_slug,
        entity_slug=entity_slug,
        section_slug=section_slug,
        finalize_payload=finalize_payload,
        outline_requirements=chapter_requirements,
    )
    if validation["success"]:
        print(
            f"[source_ingest] post-check 통과: claims={validation['claim_count']}, "
            f"sources={validation['source_count']}, readiness={validation['readiness']}",
            flush=True,
        )
    else:
        print(
            "[source_ingest] post-check 실패: " + "; ".join(validation["issues"]),
            flush=True,
        )
        # 약한 챕터만 LLM 보강 (최대 2라운드)
        critical = validation.get("critical_unresolved", [])
        chapter_map = {r.get("title", ""): r for r in chapter_requirements}
        for round_num in range(1, 3):
            if not critical:
                break
            print(f"[source_ingest] 보강 라운드 {round_num}: {len(critical)}개 챕터 타겟 리서치", flush=True)
            supplement_ok = _supplement_weak_chapters(
                topic=topic,
                topic_slug=topic_slug,
                critical_unresolved=critical,
                chapter_map=chapter_map,
                research_root=research_root,
                research_agent_dir=research_agent_dir,
                vault_script=vault_script,
                launcher=launcher,
                run_id=run_id,
                entity_slug=entity_slug,
            )
            if not supplement_ok:
                print(f"[source_ingest] 보강 라운드 {round_num} 실패 — 중단", flush=True)
                break
            # ingest-bundle + finalize-session 재실행 후 재검증
            ingest_payload = _run_launcher(
                ["ingest-bundle", "--topic", _bundle_topic, "--run-id", run_id, "--refresh"],
                research_root, research_agent_dir, launcher,
            )
            finalize_payload = _run_launcher(
                ["finalize-session", "--topic", _bundle_topic, "--run-id", run_id],
                research_root, research_agent_dir, launcher,
            )
            validation = _validate_ingest_completion(
                research_root=research_root,
                topic_slug=topic_slug,
                entity_slug=entity_slug,
                section_slug=section_slug,
                finalize_payload=finalize_payload,
                outline_requirements=chapter_requirements,
            )
            if validation["success"]:
                print(
                    f"[source_ingest] 보강 후 통과 (라운드 {round_num}): "
                    f"claims={validation['claim_count']}, sources={validation['source_count']}",
                    flush=True,
                )
                break
            critical = validation.get("critical_unresolved", [])
            print(
                f"[source_ingest] 보강 라운드 {round_num} 후에도 미통과: {'; '.join(validation['issues'])}",
                flush=True,
            )

    # 이미지 URL 수집 + 중복 제거 → image_manifest.jsonl
    _collect_research_images(
        research_root=research_root,
        run_id=run_id,
        topic_slug=topic_slug,
        entity_slug=entity_slug,
    )

    return {
        "success": validation["success"],
        "ingest_payload": ingest_payload,
        "finalize_payload": finalize_payload,
        "validation": validation,
    }


def _collect_research_images(
    research_root: Path,
    run_id: str,
    topic_slug: str,
    entity_slug: str = "",
) -> None:
    """
    수집된 sources.jsonl + claims.jsonl에서 image_url 필드를 긁어
    image_manifest.jsonl로 저장 (pHash 기반 중복 제거 포함).
    """
    try:
        from auto_agent.tools.image_dedup import collect_and_dedup
    except ImportError as e:
        print(f"[source_ingest] image_dedup 모듈 로드 실패 — 이미지 수집 건너뜀: {e}", flush=True)
        return

    slug = entity_slug or topic_slug
    alt_slug = slug.replace("-", "_") if "-" in slug else slug.replace("_", "-")

    # 이미지 URL 수집 대상 파일들
    candidate_files: list[Path] = []

    # 1. run 폴더의 source_manifest.jsonl
    run_dir = research_root / "raw" / (entity_slug or topic_slug) / run_id
    for fname in ("source_manifest.jsonl", "image_manifest.jsonl"):
        p = run_dir / fname
        if p.exists():
            candidate_files.append(p)

    # 2. manifests/<slug>/sources.jsonl
    for s in (slug, alt_slug):
        p = research_root / "manifests" / s / "sources.jsonl"
        if p.exists():
            candidate_files.append(p)
            break

    image_records: list[dict] = []
    seen_urls: set[str] = set()

    for fpath in candidate_files:
        try:
            with fpath.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rec = json.loads(line)
                    url = (rec.get("image_url") or rec.get("thumbnail_url") or "").strip()
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    image_records.append({
                        "image_url": url,
                        "title": rec.get("title", ""),
                        "source_url": rec.get("url", ""),
                        "image_source": rec.get("image_source", "unknown"),
                        "image_license": rec.get("image_license", ""),
                        "publisher": rec.get("publisher", ""),
                        "kind": rec.get("kind", ""),
                    })
        except Exception as e:
            print(f"[source_ingest] 이미지 레코드 파싱 실패 ({fpath.name}): {e}", flush=True)

    if not image_records:
        print("[source_ingest] 수집된 이미지 URL 없음 — image_manifest.jsonl 생성 건너뜀", flush=True)
        return

    print(f"[source_ingest] 이미지 URL {len(image_records)}개 수집 → 중복 제거 중...", flush=True)

    try:
        unique = collect_and_dedup(
            image_records,
            hamming_threshold=8,
            download_hash=True,
            verbose=False,
        )
    except Exception as e:
        print(f"[source_ingest] 이미지 중복 제거 실패: {e} — 원본 그대로 저장", flush=True)
        unique = image_records

    # image_manifest.jsonl 저장 (run 폴더 + manifests 폴더 양쪽)
    out_path = run_dir / "image_manifest.jsonl"
    try:
        with out_path.open("w", encoding="utf-8") as f:
            for rec in unique:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(
            f"[source_ingest] image_manifest.jsonl 저장: {len(unique)}개 "
            f"(중복 {len(image_records) - len(unique)}개 제거) → {out_path}",
            flush=True,
        )
    except Exception as e:
        print(f"[source_ingest] image_manifest.jsonl 저장 실패: {e}", flush=True)

    # manifests/<slug>/images.jsonl 에도 동기화
    for s in (slug, alt_slug):
        manifest_dir = research_root / "manifests" / s
        if manifest_dir.exists():
            images_p = manifest_dir / "images.jsonl"
            try:
                with images_p.open("w", encoding="utf-8") as f:
                    for rec in unique:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                print(f"[source_ingest] manifests/{s}/images.jsonl 동기화 완료", flush=True)
            except Exception as e:
                print(f"[source_ingest] images.jsonl 동기화 실패: {e}", flush=True)
            break


def main():
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    project_name = os.environ.get("PROJECT_NAME", "")

    # 1. editorial_brief.json에서 topic 정보 읽기
    brief_path = project_dir / "editorial_brief.json"
    config_path = project_dir / "project_config.json"

    topic = ""
    core_question = ""
    excluded_angles = []
    real_topic = ""
    entity_slug = ""
    section_slug = ""

    if brief_path.exists():
        try:
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            real_topic = brief.get("real_topic", "")
            topic = real_topic or brief.get("_topic", "")
            core_question = brief.get("core_question", "")
            excluded_angles = brief.get("excluded_angles", [])
            entity_slug = brief.get("entity_slug", "")
            section_slug = brief.get("section_slug", "")
        except Exception as e:
            print(f"[source_ingest] editorial_brief 로드 실패: {e}", flush=True)

    if not topic and config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            topic = cfg.get("topic", "")
        except Exception:
            pass

    if not topic:
        topic = project_name or "unknown-topic"

    topic_slug = _slug(topic)

    # research_queries.json에서 메인 쿼리 읽기 (step_1_strategy 산출물)
    query = None
    _queries_path = project_dir / "research_queries.json"
    if _queries_path.exists():
        try:
            _rq = json.loads(_queries_path.read_text(encoding="utf-8"))
            query = _rq.get("main_query", "")
            if query:
                print(f"[source_ingest] 전략가 쿼리 사용: {query}", flush=True)
        except Exception:
            pass
    if not query:
        query = core_question or topic

    print(f"[source_ingest] 주제: {topic}", flush=True)
    print(f"[source_ingest] slug: {topic_slug}", flush=True)
    if entity_slug:
        print(f"[source_ingest] entity_slug: {entity_slug}, section_slug: {section_slug}", flush=True)

    # 2. research root = output/<uuid>/research/ (볼트 아님)
    research_root = _get_research_root(project_dir)
    print(f"[source_ingest] research root: {research_root}", flush=True)

    # 3. 볼트에서 기존 wiki/manifests seed 복사 (없으면 graceful skip)
    try:
        vault_research_root = _get_vault_research_root()
        seed_slugs = [s for s in [entity_slug, topic_slug] if s]
        _seed_from_vault(research_root, vault_research_root, seed_slugs)
    except RuntimeError as e:
        print(f"[source_ingest] 볼트 seed 스킵 (KAIROS_VAULT_DIR 없음): {e}", flush=True)

    # 4. ResearchAgent launcher — prepare-session
    try:
        research_agent_dir, launcher, vault_script = _resolve_research_agent_paths()
    except FileNotFoundError as exc:
        print(f"[source_ingest] {exc}", flush=True)
        sys.exit(1)

    outline = {}
    outline_path = project_dir / "outline.json"
    if outline_path.exists():
        try:
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[source_ingest] outline.json 로드 실패 (무시): {e}", flush=True)

    excluded_str = "; ".join(excluded_angles) if excluded_angles else ""
    prepare_args = [
        "prepare-session",
        "--topic", topic,
        "--query", query,
    ]
    if entity_slug:
        prepare_args += ["--entity-slug", entity_slug]
    if section_slug:
        prepare_args += ["--section-slug", section_slug]
    if excluded_str:
        prepare_args += ["--exclude", excluded_str]
    must_answers = []
    if core_question:
        must_answers.append(core_question)
    hook_angle = brief.get("hook_angle", "") if brief_path.exists() else ""
    if hook_angle:
        must_answers.append(f"이 주제를 어떤 관점으로 해석해야 하는가? {hook_angle}")
    outline_requirements = _build_outline_requirements(outline)
    for requirement in outline_requirements[:6]:
        for question in requirement.get("research_focus", [])[:5]:
            must_answers.append(question)
    deduped_must_answers = []
    seen_must_answers: set[str] = set()
    for item in must_answers:
        normalized = _normalize_text(item)
        if not normalized or normalized in seen_must_answers:
            continue
        seen_must_answers.add(normalized)
        deduped_must_answers.append(normalized)
    for item in deduped_must_answers[:24]:
        prepare_args += ["--must-answer", item]
    prepare_args += ["--downstream-use", "youtube-script-outline-guided"]

    result = _run_launcher(prepare_args, research_root, research_agent_dir, launcher)
    run_id = result.get("run_id", "")

    if not run_id:
        # stdout에서 run_id 추출 시도
        stdout_text = result.get("stdout", "")
        import re
        m = re.search(r'"run_id":\s*"([^"]+)"', stdout_text)
        if m:
            run_id = m.group(1)

    if not run_id:
        print(f"[source_ingest] prepare-session 실패 — run_id 없음", flush=True)
        print(f"[source_ingest] 결과: {result}", flush=True)
        sys.exit(1)

    print(f"[source_ingest] 세션 준비 완료: run_id={run_id}", flush=True)

    # run_id로 실제 run 디렉토리를 직접 찾음 — topic/entity slug 불일치 문제 원천 차단
    # raw/*/{run_id}/ 패턴으로 glob해서 실제 부모 slug를 사용
    raw_slug = entity_slug or topic_slug  # fallback
    _run_dirs = list(research_root.glob(f"raw/*/{run_id}"))
    if _run_dirs:
        raw_slug = _run_dirs[0].parent.name
        print(f"[source_ingest] run 디렉토리 확인: raw/{raw_slug}/{run_id}", flush=True)
    else:
        print(f"[source_ingest] run 디렉토리 미발견 — fallback: raw/{raw_slug}/{run_id}", flush=True)

    # source_ingest_status.json 초기 기록
    status = {
        "topic": topic,
        "topic_slug": topic_slug,
        "entity_slug": entity_slug,
        "section_slug": section_slug,
        "run_id": run_id,
        "research_root": str(research_root),
        "status": "collecting",
    }
    (project_dir / "source_ingest_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 5. Claude CLI 에이전트로 실제 수집 실행
    outcome = _run_research_agent(
        topic=topic,
        topic_slug=topic_slug,
        query=query,
        run_id=run_id,
        research_root=research_root,
        project_dir=project_dir,
        core_question=core_question,
        excluded_angles=excluded_angles,
        outline=outline,
        entity_slug=entity_slug,
        section_slug=section_slug,
        raw_slug=raw_slug,
        research_agent_dir=research_agent_dir,
        launcher=launcher,
        vault_script=vault_script,
    )
    success = bool(outcome.get("success"))
    validation = outcome.get("validation") or {}

    # 6. 완료 상태 기록
    status["status"] = "completed" if success else "partial"
    if validation:
        status["validation"] = validation
    (project_dir / "source_ingest_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[source_ingest] 완료 — research: {research_root / 'wiki' / topic_slug}", flush=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
