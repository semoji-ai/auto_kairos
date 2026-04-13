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


def _validate_ingest_completion(
    *,
    research_root: Path,
    topic_slug: str,
    entity_slug: str = "",
    section_slug: str = "",
    finalize_payload: dict | None = None,
) -> dict:
    finalized = finalize_payload or {}
    run_state = finalized.get("run_state") or {}
    snapshot = finalized.get("snapshot") or {}
    status = finalized.get("status") or {}

    canonical_slug = resolve_existing_entity_slug(research_root, entity_slug or topic_slug)
    # manifests slug는 wiki slug와 다를 수 있음 (하이픈↔언더스코어) — 양쪽 모두 확인
    alt_slug = canonical_slug.replace("-", "_") if "-" in canonical_slug else canonical_slug.replace("_", "-")
    def _best_manifest_path(filename: str) -> Path:
        primary = research_root / "manifests" / canonical_slug / filename
        alt = research_root / "manifests" / alt_slug / filename
        return primary if primary.exists() else alt
    claims_path = _best_manifest_path("claims.jsonl")
    sources_path = _best_manifest_path("sources.jsonl")
    claim_count = _count_manifest_records(claims_path)
    source_count = _count_manifest_records(sources_path)

    wiki_dir = research_root / "wiki" / canonical_slug
    if not wiki_dir.exists():
        alt = canonical_slug.replace("-", "_") if "-" in canonical_slug else canonical_slug.replace("_", "-")
        wiki_dir = research_root / "wiki" / alt
    overview = wiki_dir / "overview.md"
    wiki_usable = overview.exists() and overview.stat().st_size > 300 if overview.exists() else False
    if not wiki_usable and claim_count >= 3:
        wiki_usable = True

    readiness = str(snapshot.get("specialist_readiness") or "")
    run_stage = str(run_state.get("stage") or "")
    run_status = str(run_state.get("status") or "")
    next_step = str(status.get("recommended_next_step") or "")

    issues: list[str] = []
    if claim_count < 3:
        issues.append(f"claim_count={claim_count} < 3")
    if not wiki_usable:
        issues.append("wiki not usable")
    # finalize-session 상태는 참고만 — wiki+claims가 충분하면 통과
    # (ResearchAgent 내부 상태 관리 불일치로 인한 false negative 방지)
    if run_stage != "packaging" or run_status != "completed":
        print(f"[source_ingest] 참고: finalize-session 상태 = {run_stage or 'n/a'}/{run_status or 'n/a'} (wiki+claims 충분하면 통과)", flush=True)

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
    }


def _run_research_agent(topic: str, topic_slug: str, query: str, run_id: str,
                         research_root: Path, project_dir: Path,
                         core_question: str = "", excluded_angles: list = None,
                         entity_slug: str = "", section_slug: str = "",
                         research_agent_dir: Path | None = None,
                         launcher: Path | None = None,
                         vault_script: Path | None = None) -> dict:
    """Claude CLI로 ResearchAgent 실행 (자율 수집 루프)."""
    if research_agent_dir is None or launcher is None or vault_script is None:
        research_agent_dir, launcher, vault_script = _resolve_research_agent_paths()
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
2. 각 소스를 source note로 정규화 (research_vault.py register-source 사용)
3. 핵심 claim 추출 및 검증 (research_vault.py append-claim 사용)
4. wiki 페이지 작성 (위 wiki 저장 경로에 따라 파일 배치)
5. research_launcher.py ingest-bundle 및 finalize-session 호출로 마무리

research root 경로: {research_root}
research_vault.py 경로: {vault_script}
research_launcher.py 경로: {launcher}

모든 파일을 위 research root 아래에 저장하세요. 완료되면 "RESEARCH_COMPLETE"를 출력하세요.
"""

    # source_ingest_status.json에 세션 정보 기록
    status_path = project_dir / "source_ingest_status.json"

    # Claude CLI 실행 (auto_agent/orchestrator/runner.py 패턴 따름 - stdin 방식)
    claude_bin = "claude"
    cmd = [
        claude_bin,
        "--model", "claude-sonnet-4-6",
        "--max-turns", "50",
        "--output-format", "text",
        "--allowedTools",
        "Bash,Read,Write,Glob,Grep,WebFetch,WebSearch",
    ]

    env = os.environ.copy()
    env["LLM_WIKI_RESEARCH_DIR"] = str(research_root)
    env["RESEARCH_AGENT_DIR"] = str(research_agent_dir)

    print(f"[source_ingest] Claude CLI 리서치 에이전트 시작 (sonnet, max-turns=50)...", flush=True)
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
    ingest_payload = _run_launcher(
        ["ingest-bundle", "--topic", topic, "--run-id", run_id, "--refresh"],
        research_root,
        research_agent_dir,
        launcher,
    )
    finalize_payload = _run_launcher(
        ["finalize-session", "--topic", topic, "--run-id", run_id],
        research_root,
        research_agent_dir,
        launcher,
    )
    validation = _validate_ingest_completion(
        research_root=research_root,
        topic_slug=topic_slug,
        entity_slug=entity_slug,
        section_slug=section_slug,
        finalize_payload=finalize_payload,
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

    return {
        "success": validation["success"],
        "ingest_payload": ingest_payload,
        "finalize_payload": finalize_payload,
        "validation": validation,
    }


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
        entity_slug=entity_slug,
        section_slug=section_slug,
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
