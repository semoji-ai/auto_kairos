# adobe Stage1-2 P3 — 리서치 오케스트레이션 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** editorial_brief.json에서 검색 쿼리를 생성하고, P1 결정적 레인 수집 + claude 웹리서치 fan-out(병렬)을 수행한 뒤 종합해 `research_report.json`을 산출한다. 런타임 v3 의존 0.

**Architecture:** v3 query_planner를 이식하고, claude 웹리서치 러너(`claude -p --allowedTools WebSearch,WebFetch`, 2026-06-17 동작 검증)를 신규 추가하며, `orchestrator.run_research`가 쿼리→레인(P1 `collect_queries`)→웹 fan-out(ThreadPool)→LLM 종합을 지휘하는 단순 Python 파이프라인으로 구성한다.

**Tech Stack:** Python stdlib + `backend.llm` + claude CLI(웹 도구). 테스트는 pytest + monkeypatch(invoker/subprocess/모듈함수, 실 LLM·웹 0).

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트).

**기존 자산:** P1 `backend/research/collector.py`의 `collect_queries(proj_dir, queries, *, on_event=None) -> {runs, sources, manifest}`; P2 `backend/brief.py`의 `parse_plan(proj_dir) -> {topic, writing_style, duration, tone}`.

**계약(전 태스크 고정):**
- `plan_queries(brief: dict, *, project_slug="", invoker=None) -> list[{query, rationale, lang}]`
- `run_web_research(cwd, prompt, *, on_line=None, timeout=600) -> str` (실패→"")
- `run_research(proj_dir, *, max_workers=3, on_event=None) -> {report, queries, sources, web_notes}` 또는 `{error}`
- orchestrator는 **모듈 전역** `query_planner.plan_queries` / `collector.collect_queries` / `web_agent.run_web_research` / `_synthesize` 를 호출(테스트 monkeypatch 지점).

---

## Task 1: query_planner 이식

**Files:**
- Create: `backend/research/query_planner.py`
- Test: `tests/test_research_query_planner.py`

- [ ] **Step 1: Write the failing test** — `tests/test_research_query_planner.py`:

```python
from backend.research import query_planner


def test_plan_queries_parses(monkeypatch):
    brief = {"real_topic": "유한양행", "core_question": "왜?"}
    raw = '{"queries":[{"query":"유한양행","rationale":"본 entity","lang":"ko"},' \
          '{"query":"유일한 박사","rationale":"창업자","lang":"ko"}]}'
    out = query_planner.plan_queries(brief, invoker=lambda p: raw)
    assert [q["query"] for q in out] == ["유한양행", "유일한 박사"]
    assert out[0]["lang"] == "ko"


def test_plan_queries_drops_overlong(monkeypatch):
    brief = {"real_topic": "x"}
    raw = '{"queries":[{"query":"' + "가" * 90 + '","rationale":"too long","lang":"ko"},' \
          '{"query":"짧은쿼리","rationale":"ok","lang":"ko"}]}'
    out = query_planner.plan_queries(brief, invoker=lambda p: raw)
    assert [q["query"] for q in out] == ["짧은쿼리"]   # 80자 초과 폐기


def test_plan_queries_fallback_on_bad_json(monkeypatch):
    brief = {"real_topic": "유한양행"}
    out = query_planner.plan_queries(brief, invoker=lambda p: "not json")
    assert out and out[0]["query"] == "유한양행"        # real_topic 폴백


def test_plan_queries_fallback_uses_slug(monkeypatch):
    brief = {}
    out = query_planner.plan_queries(brief, project_slug="tesla_story",
                                     invoker=lambda p: "boom")
    assert out and out[0]["query"] == "tesla"           # slug 첫 토큰
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_query_planner.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `backend/research/query_planner.py`** with EXACTLY:

```python
"""브리프→검색 쿼리 분해(5~10). LLM 실패 시 결정적 폴백. v3 query_planner 이식.
기본 invoker는 claude CLI(중첩 env 제거). 테스트는 invoker 주입."""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Callable

PLANNER_PROMPT = """당신은 리서치 쿼리 플래너입니다. editorial_brief를 읽고
**5~10개의 검색 쿼리**로 분해하세요. 각 쿼리는 위키피디아/뉴스/학술/도서
4개 lane에 모두 던져집니다.

# 출력 규칙
- JSON 객체 한 개. 다른 텍스트 일체 금지.
- 스키마: {"queries": [{"query": "...", "rationale": "...", "lang": "ko|en|auto"}]}
- 5~10개. 통문장 금지 (10어절 이하).
- 각 쿼리는 독립적으로 의미 있는 entity/event/concept이어야 함.
- 한국 주제는 ko + 글로벌 맥락 1~2건 en도 포함.

# 피해야 할 것
- "X에 대한 모든 것" 같은 추상 쿼리
- 너무 길고 구체적인 통문장
- "역사", "이야기" 같은 단독 검색어(오염 위험)
"""

_NEST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")


def _build_prompt(brief: dict) -> str:
    keep = ("real_topic", "core_question", "hook_angle", "hook_episode",
            "must_include_episodes", "excluded_angles", "audience",
            "key_entities", "entities", "keywords")
    slim = {k: v for k, v in brief.items() if k in keep and v}
    return f"{PLANNER_PROMPT}\n\n<brief>\n{json.dumps(slim, ensure_ascii=False, indent=2)}\n</brief>\n"


def _parse_response(raw: str) -> list[dict]:
    raw = (raw or "").strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        raise ValueError("응답에 JSON 블록 없음")
    payload = json.loads(m.group(0))
    queries = payload.get("queries") if isinstance(payload, dict) else None
    if not isinstance(queries, list) or not queries:
        raise ValueError("queries 배열 비어 있음")
    out = []
    for q in queries:
        if not isinstance(q, dict):
            continue
        text = str(q.get("query") or "").strip()
        if not text or len(text) > 80:
            continue
        out.append({"query": text, "rationale": str(q.get("rationale") or ""),
                    "lang": str(q.get("lang") or "auto")})
    if not out:
        raise ValueError("유효 쿼리 없음")
    return out


def _call_claude_cli(prompt: str, *, timeout: int = 120) -> str:
    env = {k: v for k, v in os.environ.items() if k not in _NEST_ENV}
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    r = subprocess.run([claude_bin, "-p", "--output-format", "text"],
                       input=prompt, capture_output=True, text=True,
                       timeout=timeout, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI exit {r.returncode}: {(r.stderr or '')[:200]}")
    return r.stdout


def _fallback_queries(brief: dict, project_slug: str = "") -> list[dict]:
    real = (brief.get("real_topic") or "").strip()
    if real and len(real.split()) <= 8:
        return [{"query": real, "rationale": "fallback (LLM 실패)", "lang": "auto"}]
    if project_slug:
        first = project_slug.replace("_", " ").split()[0]
        return [{"query": first, "rationale": "fallback — slug 첫 토큰", "lang": "auto"}]
    return []


def plan_queries(brief: dict, *, project_slug: str = "",
                 invoker: Callable[[str], str] | None = None) -> list[dict]:
    """브리프를 5~10개 쿼리로 분해. invoker 미지정 시 claude CLI. 실패 시 폴백."""
    invoke = invoker or _call_claude_cli
    prompt = _build_prompt(brief)
    try:
        return _parse_response(invoke(prompt))
    except Exception as exc:
        print(f"[query_planner] LLM 실패, fallback: {exc}", flush=True)
        return _fallback_queries(brief, project_slug=project_slug)
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_query_planner.py -v`
Expected: 4 passed. Full suite → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/research/query_planner.py tests/test_research_query_planner.py
git commit -m "feat(research): query_planner 이식 — 브리프→쿼리 분해+폴백"
```

---

## Task 2: web_agent — claude 웹리서치 러너

**Files:**
- Create: `backend/research/web_agent.py`
- Test: `tests/test_research_web_agent.py`

- [ ] **Step 1: Write the failing test** — `tests/test_research_web_agent.py`:

```python
import subprocess
from backend.research import web_agent


def test_run_web_research_returns_note(tmp_path, monkeypatch):
    def fake_run(cmd, *, input=None, capture_output=None, text=None, timeout=None, env=None):
        assert "--allowedTools" in cmd
        class R:
            returncode = 0
            stdout = "WEBSEARCH_OK: fact https://x"
            stderr = ""
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    note = web_agent.run_web_research(tmp_path, "research tesla")
    assert "WEBSEARCH_OK" in note


def test_run_web_research_strips_nesting_env(tmp_path, monkeypatch):
    seen = {}
    def fake_run(cmd, *, input=None, capture_output=None, text=None, timeout=None, env=None):
        seen["env"] = env
        class R:
            returncode = 0; stdout = "ok"; stderr = ""
        return R()
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setattr(subprocess, "run", fake_run)
    web_agent.run_web_research(tmp_path, "q")
    assert "CLAUDECODE" not in seen["env"]   # 중첩 env 제거


def test_run_web_research_failure_returns_empty(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)
    monkeypatch.setattr(subprocess, "run", boom)
    assert web_agent.run_web_research(tmp_path, "q") == ""


def test_run_web_research_nonzero_returns_empty(tmp_path, monkeypatch):
    def fake_run(*a, **k):
        class R:
            returncode = 1; stdout = ""; stderr = "err"
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert web_agent.run_web_research(tmp_path, "q") == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_web_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Create `backend/research/web_agent.py`** with EXACTLY:

```python
"""claude 웹리서치 러너 — `claude -p --allowedTools WebSearch,WebFetch`로 웹 노트 생성.
중첩 env 제거(안 하면 claude -p 행). 실패/타임아웃 → "" (부분 실패 격리)."""
from __future__ import annotations

import os
import subprocess

_NEST_ENV = ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT")


def run_web_research(cwd, prompt: str, *, on_line=None, timeout: int = 600) -> str:
    """프롬프트로 claude 웹리서치 1회 → 노트 텍스트. 실패 시 ""."""
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    env = {k: v for k, v in os.environ.items() if k not in _NEST_ENV}
    cmd = [claude_bin, "-p", "--output-format", "text",
           "--allowedTools", "WebSearch,WebFetch"]
    try:
        r = subprocess.run(cmd, input=prompt, cwd=str(cwd), capture_output=True,
                           text=True, timeout=timeout, env=env)
    except Exception as e:  # noqa: BLE001 — 타임아웃/실행오류 모두 격리
        if on_line:
            on_line(f"웹리서치 실패: {e}")
        return ""
    if r.returncode != 0:
        if on_line:
            on_line(f"웹리서치 rc={r.returncode}: {(r.stderr or '')[:150]}")
        return ""
    return (r.stdout or "").strip()
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_web_agent.py -v`
Expected: 4 passed. Full suite → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/research/web_agent.py tests/test_research_web_agent.py
git commit -m "feat(research): claude 웹리서치 러너(web_agent) — WebSearch/WebFetch"
```

---

## Task 3: research_report 스키마 + orchestrator 유틸(스케일·digest)

**Files:**
- Create: `backend/schemas/research_report.schema.json`
- Create: `backend/research/orchestrator.py` (유틸 + 상수, run_research는 Task 4)
- Test: `tests/test_research_orchestrator_utils.py`

- [ ] **Step 1: Create `backend/schemas/research_report.schema.json`** with EXACTLY:

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["topic", "sources", "digest"],
  "properties": {
    "topic": { "type": "string" },
    "queries": { "type": "array", "items": { "type": "string" } },
    "sources": { "type": "array" },
    "web_findings": { "type": "array" },
    "digest": { "type": "object", "additionalProperties": true }
  }
}
```

- [ ] **Step 2: Write the failing test** — `tests/test_research_orchestrator_utils.py`:

```python
from backend.research import orchestrator


def test_explorer_count_scales_by_duration():
    assert orchestrator._explorer_count("1분") == 3
    assert orchestrator._explorer_count("3분") == 4
    assert orchestrator._explorer_count("5분") == 5
    assert orchestrator._explorer_count("10분") == 6
    assert orchestrator._explorer_count("") == 3        # 미지정 기본


def test_digest_counts_sources_and_notes():
    sources = [{"title": "A", "lane": "wikipedia", "tier_hint": "A"},
               {"title": "B", "lane": "crossref", "tier_hint": "B"}]
    notes = ["note1", "", "note3"]
    d = orchestrator._digest(sources, notes)
    assert d["source_count"] == 2
    assert d["web_note_count"] == 2                     # 빈 노트 제외
    assert d["lanes"]["wikipedia"] == 1


def test_load_sources_reads_manifests(tmp_path):
    man = tmp_path / "research" / "manifests" / "t" 
    man.mkdir(parents=True)
    (man / "sources.jsonl").write_text(
        '{"title":"A","url":"u","lane":"wikipedia","tier_hint":"A","snippet":"s"}\n',
        encoding="utf-8")
    src = orchestrator._load_sources(tmp_path)
    assert len(src) == 1 and src[0]["title"] == "A"
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_orchestrator_utils.py -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Create `backend/research/orchestrator.py`** (유틸 부분만) with EXACTLY:

```python
"""리서치 오케스트레이션 — 브리프→쿼리→레인(P1)+웹 fan-out→종합 research_report.
run_research는 Task 4. 여기는 유틸·상수."""
from __future__ import annotations

import json
import re
from pathlib import Path

_SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"
_REPORT_SCHEMA = _SCHEMAS / "research_report.schema.json"


def _explorer_count(duration: str) -> int:
    """분량(예 '1분','10분')에 따른 웹리서치 에이전트 수. v3 스케일."""
    m = re.search(r"(\d+)", str(duration or ""))
    mins = int(m.group(1)) if m else 0
    if mins <= 1:
        return 3
    if mins <= 3:
        return 4
    if mins <= 5:
        return 5
    return 6


def _digest(sources: list, web_notes: list) -> dict:
    """결정적 통계(LLM 무관). 소스/노트 카운트 + lane/tier 분포."""
    lanes: dict[str, int] = {}
    tiers: dict[str, int] = {}
    for s in sources:
        lanes[s.get("lane", "")] = lanes.get(s.get("lane", ""), 0) + 1
        tiers[s.get("tier_hint", "")] = tiers.get(s.get("tier_hint", ""), 0) + 1
    return {
        "source_count": len(sources),
        "web_note_count": len([n for n in web_notes if n]),
        "lanes": lanes,
        "tiers": tiers,
    }


def _load_sources(proj_dir: Path) -> list[dict]:
    """research/manifests/**/sources.jsonl 의 모든 소스 dict 로드."""
    out: list[dict] = []
    base = Path(proj_dir) / "research" / "manifests"
    if not base.is_dir():
        return out
    for jsonl in base.rglob("sources.jsonl"):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_orchestrator_utils.py -v`
Expected: 3 passed. Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/schemas/research_report.schema.json backend/research/orchestrator.py tests/test_research_orchestrator_utils.py
git commit -m "feat(research): research_report 스키마 + orchestrator 유틸(스케일·digest·소스로드)"
```

---

## Task 4: orchestrator run_research (지휘)

**Files:**
- Modify: `backend/research/orchestrator.py` (add `_angles`, `_synthesize`, `run_research`)
- Test: `tests/test_research_run_research.py`

- [ ] **Step 1: Write the failing test** — `tests/test_research_run_research.py`:

```python
import json
from pathlib import Path
from backend.research import orchestrator


def _brief(tmp_path, dur="3분"):
    (tmp_path / "plan.md").write_text(f"# 유한양행\n채널: semoji\n분량: {dur}\n", encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text(
        json.dumps({"real_topic": "유한양행", "core_question": "왜?"}), encoding="utf-8")


def _patch(monkeypatch, *, web=lambda cwd, p, **k: "웹노트: 사실 https://x", synth=True):
    monkeypatch.setattr(orchestrator.query_planner, "plan_queries",
                        lambda b, **k: [{"query": "유한양행", "rationale": "", "lang": "ko"}])
    def fake_collect(proj_dir, queries, **k):
        man = Path(proj_dir) / "research" / "manifests" / "t"
        man.mkdir(parents=True, exist_ok=True)
        (man / "sources.jsonl").write_text(
            '{"title":"위키","url":"u","lane":"wikipedia","tier_hint":"A","snippet":"s"}\n',
            encoding="utf-8")
        return {"runs": [], "sources": 1, "manifest": str(man / "sources.jsonl")}
    monkeypatch.setattr(orchestrator.collector, "collect_queries", fake_collect)
    monkeypatch.setattr(orchestrator.web_agent, "run_web_research", web)
    if synth:
        monkeypatch.setattr(orchestrator, "_synthesize",
                            lambda proj, brief, sources, notes, on_event=None: {
                                "topic": "유한양행", "queries": ["유한양행"],
                                "sources": sources, "web_findings": [{"angle": "a", "claim": "c", "source_url": "x"}],
                                "digest": {}})
    else:
        monkeypatch.setattr(orchestrator, "_synthesize",
                            lambda proj, brief, sources, notes, on_event=None: None)


def test_run_research_full(tmp_path, monkeypatch):
    _brief(tmp_path)
    _patch(monkeypatch)
    r = orchestrator.run_research(tmp_path, max_workers=2)
    rep = Path(r["report"])
    assert rep.name == "research_report.json" and rep.is_file()
    data = json.loads(rep.read_text(encoding="utf-8"))
    assert data["topic"] == "유한양행"
    assert r["sources"] == 1 and r["web_notes"] >= 1
    assert (tmp_path / "research_digest.json").is_file()


def test_run_research_scales_web_agents(tmp_path, monkeypatch):
    _brief(tmp_path, dur="10분")
    calls = {"n": 0}
    def counting_web(cwd, p, **k):
        calls["n"] += 1
        return "노트"
    _patch(monkeypatch, web=counting_web)
    orchestrator.run_research(tmp_path, max_workers=3)
    assert calls["n"] == 6        # 10분 → 6 에이전트


def test_run_research_partial_web_failure(tmp_path, monkeypatch):
    _brief(tmp_path, dur="1분")
    seq = iter(["", "노트2", "노트3"])
    _patch(monkeypatch, web=lambda cwd, p, **k: next(seq, ""))
    r = orchestrator.run_research(tmp_path, max_workers=1)
    assert r["web_notes"] == 2     # 빈 노트 1개 격리, 나머지 반영


def test_run_research_synth_failure_digest_fallback(tmp_path, monkeypatch):
    _brief(tmp_path)
    _patch(monkeypatch, synth=False)
    r = orchestrator.run_research(tmp_path, max_workers=2)
    data = json.loads(Path(r["report"]).read_text(encoding="utf-8"))
    assert data["web_findings"] == []          # 종합 실패 → digest-only 폴백
    assert data["digest"]["source_count"] == 1


def test_run_research_no_brief_errors(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# x\n", encoding="utf-8")
    r = orchestrator.run_research(tmp_path)
    assert r.get("error")
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_run_research.py -v`
Expected: FAIL — `run_research` 부재.

- [ ] **Step 3: Append `_angles`, `_synthesize`, `run_research` to `backend/research/orchestrator.py`** with EXACTLY:

```python
from concurrent.futures import ThreadPoolExecutor

from backend import llm
from backend import brief as brief_mod
from backend.research import query_planner, collector, web_agent


def _angles(brief: dict, queries: list, n: int) -> list[str]:
    """n개 웹리서치 앵글 프롬프트 생성. 쿼리를 라운드로빈으로 분배 + 브리프 맥락."""
    topic = brief.get("real_topic") or brief.get("core_question") or ""
    qs = [q["query"] for q in queries] or [topic]
    out = []
    for i in range(n):
        focus = qs[i % len(qs)]
        out.append(
            f"너는 리서치 탐색가다. 주제 '{topic}' 중 '{focus}'에 집중해 웹을 검색·열람해 "
            f"검증 가능한 사실(수치·연도·사건)과 출처 URL을 수집하라. "
            f"WebSearch/WebFetch를 사용하고, 핵심 발견을 불릿으로 정리해 출처 URL과 함께 보고하라.")
    return out


def _synthesize(proj_dir, brief: dict, sources: list, web_notes: list, on_event=None) -> dict | None:
    """레인 소스 + 웹 노트 → research_report.json (claude+스키마). 실패 시 None."""
    proj_dir = Path(proj_dir)
    out = proj_dir / "research_report.json"
    notes_text = "\n\n---\n".join(n for n in web_notes if n)
    src_text = json.dumps(sources, ensure_ascii=False, indent=2)[:8000]
    prompt = (
        "다음 브리프·수집 소스·웹 노트를 종합해 research_report JSON을 작성하라.\n"
        "필드: topic, queries(검색어 배열), sources(입력 소스 배열 그대로), "
        "web_findings([{angle, claim, source_url}]), digest({key_facts:[...], figures:[...]}).\n"
        "검증 가능한 사실 위주, 출처 URL 보존. JSON만 출력.\n\n"
        f"## 브리프\n{json.dumps(brief, ensure_ascii=False)[:3000]}\n\n"
        f"## 수집 소스(레인)\n{src_text}\n\n## 웹 노트\n{notes_text[:8000]}"
    )
    if on_event:
        on_event("리서치 종합")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_REPORT_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return None
    try:
        return json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return None


def run_research(proj_dir, *, max_workers: int = 3, on_event=None) -> dict:
    """브리프→쿼리→레인(P1)+웹 fan-out→종합 research_report.
    반환 {report, queries, sources, web_notes} 또는 {error}."""
    proj_dir = Path(proj_dir)
    bf = proj_dir / "editorial_brief.json"
    if not bf.is_file():
        return {"error": "editorial_brief.json 필요 (P2 먼저)"}
    brief = json.loads(bf.read_text(encoding="utf-8"))
    duration = brief_mod.parse_plan(proj_dir).get("duration", "")

    queries = query_planner.plan_queries(brief, project_slug=proj_dir.name)
    if not queries:
        return {"error": "쿼리 생성 실패"}
    if on_event:
        on_event(f"쿼리 {len(queries)}개")
    collector.collect_queries(proj_dir, [q["query"] for q in queries], on_event=on_event)

    n = _explorer_count(duration)
    angles = _angles(brief, queries, n)
    web_dir = proj_dir / "research" / "web"
    web_dir.mkdir(parents=True, exist_ok=True)

    def _one(i_angle):
        i, angle = i_angle
        note = web_agent.run_web_research(proj_dir, angle, on_line=on_event)
        if note:
            (web_dir / f"{i}.md").write_text(note, encoding="utf-8")
        return note

    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as ex:
        web_notes = list(ex.map(_one, list(enumerate(angles))))

    sources = _load_sources(proj_dir)
    report = _synthesize(proj_dir, brief, sources, web_notes, on_event=on_event)
    digest = _digest(sources, web_notes)
    (proj_dir / "research_digest.json").write_text(
        json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")

    if report is None:                       # 종합 실패 → digest-only 폴백 리포트
        report = {"topic": brief.get("real_topic", ""), "queries": [q["query"] for q in queries],
                  "sources": sources, "web_findings": [], "digest": digest}
        (proj_dir / "research_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        if on_event:
            on_event("종합 실패 — digest 기반 최소 리포트")

    return {"report": str(proj_dir / "research_report.json"),
            "queries": len(queries), "sources": len(sources),
            "web_notes": len([n for n in web_notes if n])}
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_run_research.py -v`
Expected: 5 passed.

Note: `_synthesize`는 모듈 전역이라 테스트가 `orchestrator._synthesize`를 monkeypatch할 때 `run_research` 내부 `_synthesize(...)` 호출이 대체된다(전역 참조).

- [ ] **Step 5: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존(P1+P2 포함) + 신규(약 16) 전부 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/research/orchestrator.py tests/test_research_run_research.py
git commit -m "feat(research): run_research — 쿼리→레인+웹 fan-out→종합 research_report"
```

---

## Task 5: 옵트인 실제 웹 스모크

**Files:**
- Create: `tests/test_research_web_smoke.py`

- [ ] **Step 1: 옵트인 스모크 작성** — `tests/test_research_web_smoke.py`:

```python
import os
import pytest
from backend.research import web_agent

pytestmark = pytest.mark.skipif(
    os.environ.get("AK_RESEARCH_E2E") != "1",
    reason="실제 claude 웹검색 필요 — AK_RESEARCH_E2E=1 로 활성")


def test_web_research_real(tmp_path):
    note = web_agent.run_web_research(
        tmp_path,
        "Use web search to find one verifiable 2026 fact with a source URL. "
        "Report it as a bullet with the URL.")
    assert note and ("http" in note)
```

- [ ] **Step 2: 기본 skip 확인**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_research_web_smoke.py -v`
Expected: 1 skipped.

- [ ] **Step 3: Commit**

```bash
git add tests/test_research_web_smoke.py
git commit -m "test(research): 옵트인 실제 웹리서치 스모크(AK_RESEARCH_E2E)"
```

---

## Self-Review 결과

**Spec coverage:**
- query_planner 이식(폴백) → Task 1 ✓
- claude 웹 러너(allowedTools, 중첩 env 제거, 실패→"") → Task 2 ✓
- research_report 스키마 + 스케일/digest/소스로드 유틸 → Task 3 ✓
- run_research(브리프→쿼리→레인→웹 fan-out 병렬→종합, 폴백, 부분 실패 격리, 스케일) → Task 4 ✓
- 종합 실패→digest-only 폴백 → Task 4 ✓
- brief 없음→error → Task 4 ✓
- 옵트인 웹 스모크 → Task 5 ✓
- 범위 밖(P4 원고) 미포함 ✓

**Placeholder scan:** 전부 완전 코드/테스트. ✓

**Type consistency:** `plan_queries`/`run_web_research`/`run_research`/`_synthesize`/`_explorer_count`/`_digest`/`_load_sources` 시그니처가 Task 간·계약과 일치. orchestrator가 `query_planner.plan_queries`·`collector.collect_queries`·`web_agent.run_web_research`·전역 `_synthesize` 호출 → Task 4 테스트 monkeypatch 지점과 일치. P1 `collect_queries`·P2 `parse_plan` 시그니처 정확. ✓

**알려진 결정:** 웹 fan-out 엔진은 claude 고정(WebSearch/WebFetch 검증됨). 종합은 llm.run_orchestrator(claude 기본)+스키마. 부분 실패(빈 노트)·종합 실패 모두 비블로킹 폴백.
