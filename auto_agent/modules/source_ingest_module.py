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


def _topic_wiki_usable(research_root: Path, topic_slug: str) -> bool:
    """vault에 이미 usable한 wiki가 있는지 확인."""
    wiki_overview = research_root / "wiki" / topic_slug / "overview.md"
    claims_file = research_root / "manifests" / topic_slug / "claims.jsonl"
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
                         core_question: str = "", excluded_angles: list = None) -> bool:
    """Claude CLI로 ResearchAgent 실행 (자율 수집 루프)."""
    must_answer = core_question or f"{topic}의 핵심 구조와 맥락"
    exclude_str = "; ".join(excluded_angles or [])

    # 세션 번들 읽기
    session_brief_path = research_root / "raw" / topic_slug / run_id / "artifacts" / "session_bundle" / "session_brief.md"
    if not session_brief_path.exists():
        print(f"[source_ingest] session_brief.md 없음: {session_brief_path}", flush=True)
        return False

    session_brief = session_brief_path.read_text(encoding="utf-8")

    # ResearchAgent SKILL.md 읽기
    skill_path = RESEARCH_AGENT_DIR / "SKILL.md"
    skill_content = skill_path.read_text(encoding="utf-8") if skill_path.exists() else ""

    # 프로젝트 루트에서 lane 도구 경로 확인
    package_dir = Path(__file__).parent.parent
    lane_note = ""
    if (package_dir / "tools" / "news_rss_lane.py").exists():
        lane_note = f"""
**토큰 절약 우선 수집 도구 (WebSearch 전에 먼저 사용):**
```bash
# 뉴스 RSS (Naver, 연합뉴스, Google News)
python3 {package_dir}/tools/news_rss_lane.py "{{query}}" --limit 10 --ko-only

# Wikipedia
python3 {package_dir}/tools/wikipedia_lane.py "{{query}}" --limit 5 --content

# 학술 논문 (CrossRef)
python3 {package_dir}/tools/crossref_lane.py "{{query}}" --limit 5
```
위 도구들을 먼저 사용하고, 커버되지 않는 부분만 WebSearch/WebFetch로 보완하세요.
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

{lane_note}

**작업:**
1. 위 lane 도구 우선 → 부족한 부분만 WebSearch/WebFetch fallback
2. 각 소스를 source note로 정규화 (research_vault.py register-source 사용)
3. 핵심 claim 추출 및 검증 (research_vault.py append-claim 사용)
4. wiki 페이지 작성 (overview.md, claims.md, entities.md, timeline.md)
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

    if brief_path.exists():
        try:
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            real_topic = brief.get("real_topic", "")
            topic = real_topic or brief.get("_topic", "")
            core_question = brief.get("core_question", "")
            excluded_angles = brief.get("excluded_angles", [])
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

    # 2. research root 확인
    try:
        research_root = _get_research_root()
    except RuntimeError as e:
        print(f"[source_ingest] 오류: {e}", flush=True)
        sys.exit(1)

    print(f"[source_ingest] research root: {research_root}", flush=True)

    # 3. 이미 usable한 wiki가 있으면 스킵
    if _topic_wiki_usable(research_root, topic_slug):
        print(f"[source_ingest] vault에 이미 usable wiki 존재 — 스킵: {topic_slug}", flush=True)
        # 어떤 run을 사용할지 source_ingest_status.json에 기록
        latest_run_file = research_root / "manifests" / topic_slug / "latest_run.txt"
        run_id = latest_run_file.read_text(encoding="utf-8").strip() if latest_run_file.exists() else "unknown"
        status = {
            "topic": topic,
            "topic_slug": topic_slug,
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
    )

    # 6. 완료 상태 기록
    status["status"] = "completed" if success else "partial"
    (project_dir / "source_ingest_status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[source_ingest] 완료 — vault: {research_root / 'wiki' / topic_slug}", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
