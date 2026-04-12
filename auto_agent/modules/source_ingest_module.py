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

# ResearchAgent 경로 (Codex에서 만든 기존 프로젝트)
RESEARCH_AGENT_DIR = Path(os.environ.get("RESEARCH_AGENT_DIR", "/Users/jleavens_macmini/Projects/researchagent"))
LAUNCHER = RESEARCH_AGENT_DIR / "scripts" / "research_launcher.py"
VAULT_SCRIPT = RESEARCH_AGENT_DIR / "scripts" / "research_vault.py"


def _get_research_root() -> Path:
    """LLM Wiki Research 저장 경로: vault 02-research."""
    vault_dir = os.environ.get("KAIROS_VAULT_DIR", "")
    if vault_dir:
        return Path(vault_dir) / "02-research"
    # .env 파일에서 직접 읽기 시도
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("KAIROS_VAULT_DIR="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                return Path(val) / "02-research"
    raise RuntimeError("KAIROS_VAULT_DIR 환경변수가 설정되어 있지 않습니다.")


def _slug(text: str) -> str:
    """topic 텍스트 → URL-safe slug."""
    import re
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s[:60].strip("-")


def _resolve_slug(research_root: Path, topic_slug: str) -> str:
    """vault에서 실제로 존재하는 slug 반환. 하이픈↔언더스코어 둘 다 확인."""
    alt_slug = topic_slug.replace("-", "_") if "-" in topic_slug else topic_slug.replace("_", "-")
    for candidate in [topic_slug, alt_slug]:
        if (research_root / "wiki" / candidate).exists():
            return candidate
    return topic_slug  # 없으면 원본 반환


def _section_wiki_usable(research_root: Path, entity_slug: str, section_slug: str) -> bool:
    """Wikipedia 스타일 wiki에서 해당 섹션 파일이 이미 usable한지 확인."""
    # entity_slug 폴더 존재 + section 파일 또는 overview.md 확인
    entity_dir = research_root / "wiki" / entity_slug
    if not entity_dir.exists():
        # 하이픈↔언더스코어 변형도 확인
        alt_entity = entity_slug.replace("-", "_") if "-" in entity_slug else entity_slug.replace("_", "-")
        entity_dir = research_root / "wiki" / alt_entity
        if not entity_dir.exists():
            return False
        entity_slug = alt_entity

    # 섹션 파일: {section_slug}.md 또는 overview.md
    section_file = entity_dir / f"{section_slug}.md"
    overview_file = entity_dir / "overview.md"
    target_file = section_file if section_file.exists() else overview_file

    if not target_file.exists():
        return False

    content = target_file.read_text(encoding="utf-8")
    if len(content) < 300:
        return False

    # claims도 확인
    claims_file = research_root / "manifests" / entity_slug / "claims.jsonl"
    if claims_file.exists():
        lines = [l for l in claims_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        return len(lines) >= 3

    return len(content) >= 500


def _topic_wiki_usable(research_root: Path, topic_slug: str) -> bool:
    """vault에 이미 usable한 wiki가 있는지 확인. 하이픈↔언더스코어 둘 다 체크. (레거시 호환)"""
    slug = _resolve_slug(research_root, topic_slug)
    wiki_overview = research_root / "wiki" / slug / "overview.md"
    claims_file = research_root / "manifests" / slug / "claims.jsonl"
    if not wiki_overview.exists():
        return False
    # claims.jsonl에 최소 3개 이상의 claim이 있으면 usable
    if claims_file.exists():
        lines = [l for l in claims_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(lines) >= 3:
            return True
    # overview가 있고 내용이 500자 이상이면 usable
    content = wiki_overview.read_text(encoding="utf-8")
    return len(content) >= 500


def _run_launcher(args: list, research_root: Path) -> dict:
    """research_launcher.py 호출 → JSON 결과 파싱."""
    env = os.environ.copy()
    env["LLM_WIKI_RESEARCH_DIR"] = str(research_root)

    cmd = [sys.executable, str(LAUNCHER)] + args + ["--vault-dir", str(research_root)]
    print(f"[source_ingest] 실행: {' '.join(cmd[:6])}...", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=str(RESEARCH_AGENT_DIR))
    if result.returncode != 0:
        print(f"[source_ingest] STDERR: {result.stderr[-500:]}", flush=True)
    try:
        return json.loads(result.stdout)
    except Exception:
        return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def _run_research_agent(topic: str, topic_slug: str, query: str, run_id: str,
                         research_root: Path, project_dir: Path,
                         core_question: str = "", excluded_angles: list = None,
                         entity_slug: str = "", section_slug: str = "") -> bool:
    """Claude CLI로 ResearchAgent 실행 (자율 수집 루프)."""
    must_answer = core_question or f"{topic}의 핵심 구조와 맥락"
    exclude_str = "; ".join(excluded_angles or [])

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

    # ResearchAgent SKILL.md 읽기
    skill_path = RESEARCH_AGENT_DIR / "SKILL.md"
    skill_content = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    # 프로젝트 루트에서 lane 도구 경로 확인
    package_dir = Path(__file__).parent.parent
    lane_note = ""
    if (package_dir / "tools" / "news_rss_lane.py").exists():
        lane_note = f"""
**토큰 절약 우선 수집 도구 (WebSearch 전에 먼저 사용):**

### 뉴스 RSS 수집 규칙 (중요)
주제를 그대로 쿼리로 쓰지 말고 **반드시 3종으로 분해**하여 각각 호출:
1. **브랜드명/인물명**: 핵심 고유명사 (예: "바세린", "Chesebrough")
2. **현재 시장 관련**: 기업·카테고리 키워드 (예: "유니레버 바세린", "석유젤리 시장")
3. **영문 버전**: 한국어 주제의 영문 병행 (예: "Vaseline Unilever")

"바세린의 역사"처럼 주제 전체를 그대로 쿼리로 넣으면 뉴스 결과가 거의 없습니다.

```bash
# 뉴스 RSS — 쿼리 분해 후 각각 호출 (ko/en 분리)
python3 {package_dir}/tools/news_rss_lane.py "브랜드명또는인물명" --limit 10 --ko-only
python3 {package_dir}/tools/news_rss_lane.py "현재시장관련단어" --limit 10 --ko-only
python3 {package_dir}/tools/news_rss_lane.py "EnglishKeyword" --limit 10 --en-only

# Wikipedia
python3 {package_dir}/tools/wikipedia_lane.py "{{query}}" --limit 5 --content

# 학술 논문 (CrossRef)
python3 {package_dir}/tools/crossref_lane.py "{{query}}" --limit 5
```

### 뉴스 소스 처리 규칙
- `confidence: blocked` 항목은 제외 (유튜브, 블로그, SNS 등 저신뢰 소스)
- 동일 이벤트를 다룬 유사 제목 기사는 1건만 유지 (중복 제거)
- 뉴스 소스는 **총 15건 이하**만 chapter_facts에 포함 (컨텍스트 과적재 방지)
- 위 도구들로 커버되지 않는 부분만 WebSearch/WebFetch로 보완하세요.
"""

    # Claude CLI 프롬프트 구성
    prompt = f"""당신은 LLM Wiki Research 에이전트입니다.

아래 ResearchAgent SKILL 지침에 따라 리서치 세션을 완료하세요:

<skill>
{skill_content}
</skill>

<session_brief>
{session_brief}
</session_brief>

**중요 지침:**
- research root: {research_root}
- topic: {topic}
- topic_slug: {topic_slug}
- run_id: {run_id}
- must_answer: {must_answer}
- excluded_angles: {exclude_str}

{wiki_path_note}

{lane_note}

**작업:**
1. 위 lane 도구 우선 → 부족한 부분만 WebSearch/WebFetch fallback
2. 각 소스를 source note로 정규화 (research_vault.py register-source 사용)
3. 핵심 claim 추출 및 검증 (research_vault.py append-claim 사용)
4. wiki 페이지 작성 (위 wiki 저장 경로에 따라 파일 배치)
5. research_launcher.py ingest-bundle 및 finalize-session 호출로 마무리

research root 경로: {research_root}
research_vault.py 경로: {VAULT_SCRIPT}
research_launcher.py 경로: {LAUNCHER}

모든 파일을 위 research root 아래에 저장하세요. 완료되면 "RESEARCH_COMPLETE"를 출력하세요.
"""

    # source_ingest_status.json에 세션 정보 기록
    status_path = project_dir / "source_ingest_status.json"

    # Claude CLI 실행 (auto_agent/orchestrator/runner.py 패턴 따름 - stdin 방식)
    claude_bin = "claude"
    cmd = [
        claude_bin,
        "--model", "claude-opus-4-6",
        "--max-turns", "30",
        "--output-format", "text",
        "--allowedTools",
        "Bash,Read,Write,Glob,Grep,WebFetch,WebSearch",
    ]

    env = os.environ.copy()
    env["LLM_WIKI_RESEARCH_DIR"] = str(research_root)
    env["RESEARCH_AGENT_DIR"] = str(RESEARCH_AGENT_DIR)

    print(f"[source_ingest] Claude CLI 리서치 에이전트 시작 (max-turns=30)...", flush=True)
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
    _run_launcher(["ingest-bundle", "--topic", topic, "--run-id", run_id, "--refresh"], research_root)
    _run_launcher(["finalize-session", "--topic", topic, "--run-id", run_id], research_root)

    return True


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
    query = core_question or topic

    print(f"[source_ingest] 주제: {topic}", flush=True)
    print(f"[source_ingest] slug: {topic_slug}", flush=True)
    if entity_slug:
        print(f"[source_ingest] entity_slug: {entity_slug}, section_slug: {section_slug}", flush=True)

    # 2. research root 확인
    try:
        research_root = _get_research_root()
    except RuntimeError as e:
        print(f"[source_ingest] 오류: {e}", flush=True)
        sys.exit(1)

    print(f"[source_ingest] research root: {research_root}", flush=True)

    # 3. 이미 usable한 wiki가 있으면 스킵
    # Wikipedia 스타일(entity_slug/section_slug) 우선 체크, 없으면 레거시 topic_slug 체크
    wiki_exists = False
    skip_entity_slug = entity_slug
    skip_section_slug = section_slug

    if entity_slug and section_slug:
        wiki_exists = _section_wiki_usable(research_root, entity_slug, section_slug)
        if wiki_exists:
            print(f"[source_ingest] vault에 이미 usable wiki 존재 (Wikipedia 스타일) — 스킵: {entity_slug}/{section_slug}", flush=True)
    if not wiki_exists:
        wiki_exists = _topic_wiki_usable(research_root, topic_slug)
        if wiki_exists:
            skip_entity_slug = _resolve_slug(research_root, topic_slug)
            skip_section_slug = ""
            print(f"[source_ingest] vault에 이미 usable wiki 존재 (레거시) — 스킵: {skip_entity_slug}", flush=True)

    if wiki_exists:
        # 어떤 run을 사용할지 source_ingest_status.json에 기록
        manifest_slug = skip_entity_slug or topic_slug
        latest_run_file = research_root / "manifests" / manifest_slug / "latest_run.txt"
        run_id = latest_run_file.read_text(encoding="utf-8").strip() if latest_run_file.exists() else "unknown"
        status = {
            "topic": topic,
            "topic_slug": topic_slug,
            "entity_slug": skip_entity_slug,
            "section_slug": skip_section_slug,
            "run_id": run_id,
            "research_root": str(research_root),
            "status": "skipped_existing",
        }
        (project_dir / "source_ingest_status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        sys.exit(0)

    # 4. ResearchAgent launcher — prepare-session
    if not LAUNCHER.exists():
        print(f"[source_ingest] ResearchAgent launcher 없음: {LAUNCHER}", flush=True)
        sys.exit(1)

    excluded_str = "; ".join(excluded_angles) if excluded_angles else ""
    prepare_args = [
        "prepare-session",
        "--topic", topic,
        "--query", query,
    ]
    if excluded_str:
        prepare_args += ["--exclude", excluded_str]
    if core_question:
        prepare_args += ["--must-answer", core_question]
    prepare_args += ["--downstream-use", "youtube-script"]

    result = _run_launcher(prepare_args, research_root)
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
    success = _run_research_agent(
        topic=topic,
        topic_slug=topic_slug,
        query=query,
        run_id=run_id,
        research_root=research_root,
        project_dir=project_dir,
        core_question=core_question,
        excluded_angles=excluded_angles,
        entity_slug=entity_slug,
        section_slug=section_slug,
    )

    # 6. 완료 상태 기록 (실제 vault slug 보정)
    if entity_slug:
        # Wikipedia 스타일: entity_slug 기반 실제 경로 확인
        actual_entity = entity_slug
        alt = entity_slug.replace("-", "_") if "-" in entity_slug else entity_slug.replace("_", "-")
        if (research_root / "wiki" / alt).exists() and not (research_root / "wiki" / entity_slug).exists():
            actual_entity = alt
        status["entity_slug"] = actual_entity
    else:
        actual_slug = _resolve_slug(research_root, topic_slug)
        if actual_slug != topic_slug:
            print(f"[source_ingest] vault slug 보정: {topic_slug} → {actual_slug}", flush=True)
        status["topic_slug"] = actual_slug
    status["status"] = "completed" if success else "partial"
    (project_dir / "source_ingest_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[source_ingest] 완료 — vault: {research_root / 'wiki' / topic_slug}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
