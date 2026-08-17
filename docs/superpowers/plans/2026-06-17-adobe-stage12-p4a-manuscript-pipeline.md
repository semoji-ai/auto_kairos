# adobe Stage1-2 P4a — 원고 파이프라인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** research_report.json + editorial_brief.json에서 초안→타겟 쿼리→타겟 웹리서치→타겟 적용 원고→점수 게이트 래칫을 거쳐 잠긴 `final_manuscript.md`를 산출한다. 런타임 v3 의존 0.

**Architecture:** v3 draft-writer/script-director(manuscript)/script-reviewer 프롬프트를 adobe 스킬로 이식하고, `backend/manuscript.py`가 `llm.run_orchestrator`(claude)로 생성·채점을 호출하며 P3 `web_agent`로 타겟 웹리서치를 병렬 수행하는 단순 Python 파이프라인. 원고 래칫은 P2 `run_brief_ratchet`와 동일 구조(write/review 일반화).

**Tech Stack:** Python stdlib + `backend.llm` + `backend.research.web_agent`(P3). 테스트는 pytest + monkeypatch(하위 함수/llm/web_agent 대체, 실 LLM·웹 0).

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트).

**기존 자산 재사용:** P3 `backend/research/web_agent.run_web_research(cwd, prompt, *, on_line, timeout) -> str`; `backend.llm.run_orchestrator(prompt, cwd, *, output_schema=None, output_last=None, on_line=None) -> {returncode, output_last}`.

**계약(전 태스크 고정):**
- `generate_draft(proj_dir, *, on_event=None) -> tuple[Path|None, list[str]]`
- `targeted_research(proj_dir, questions, *, max_workers=3, on_event=None) -> list[dict]`
- `write_manuscript(proj_dir, *, version:int, prev=None, revisions=None, on_event=None) -> Path|None`
- `review_manuscript(proj_dir, ms_path, *, prev_path=None, on_event=None) -> {score:int, verdict:str, revision_instructions:list}`
- `run_manuscript_pipeline(proj_dir, *, threshold=90, max_rounds=3, max_workers=3, on_event=None) -> {manuscript, score, verdict, rounds, history, claims} | {error}`
- run_manuscript_pipeline은 **모듈 전역** `write_manuscript`/`review_manuscript`/`generate_draft`/`targeted_research`를 호출(테스트 monkeypatch 지점).

**이식 원본(읽기 전용):** `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/{draft-writer,script-director,script-reviewer}/SKILL.md`. 이식 시 `shared/...` 참조는 인라인 주입 전제로 정리, v3 CLI/Task 언급 제거, 출력은 지정 JSON/마크다운만.

---

## Task 1: 스키마 (manuscript_draft, manuscript_review)

**Files:**
- Create: `backend/schemas/manuscript_draft.schema.json`, `backend/schemas/manuscript_review.schema.json`
- Test: `tests/test_manuscript_assets.py`

- [ ] **Step 1: Create `backend/schemas/manuscript_draft.schema.json`** EXACTLY:

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["draft_markdown", "questions"],
  "properties": {
    "draft_markdown": { "type": "string" },
    "questions": { "type": "array", "items": { "type": "string" } }
  }
}
```

- [ ] **Step 2: Create `backend/schemas/manuscript_review.schema.json`** EXACTLY:

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["score_total", "verdict", "revision_instructions"],
  "properties": {
    "score_total": { "type": "number" },
    "verdict": { "type": "string", "enum": ["PASS", "REVISE", "FAIL"] },
    "revision_instructions": { "type": "array", "items": { "type": "string" } },
    "viewer_score": { "type": "number" },
    "expert_score": { "type": "number" },
    "field_feedback": { "type": "object", "additionalProperties": true }
  }
}
```

- [ ] **Step 3: Write the failing test** — `tests/test_manuscript_assets.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manuscript_draft_schema_valid():
    s = json.loads((ROOT / "backend/schemas/manuscript_draft.schema.json").read_text(encoding="utf-8"))
    assert "draft_markdown" in s["required"] and "questions" in s["required"]


def test_manuscript_review_schema_valid():
    s = json.loads((ROOT / "backend/schemas/manuscript_review.schema.json").read_text(encoding="utf-8"))
    assert set(["score_total", "verdict", "revision_instructions"]).issubset(set(s["required"]))
    assert s["properties"]["verdict"]["enum"] == ["PASS", "REVISE", "FAIL"]
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_assets.py -v`
Expected: 2 passed. Full suite → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/manuscript_draft.schema.json backend/schemas/manuscript_review.schema.json tests/test_manuscript_assets.py
git commit -m "feat(manuscript): draft/review JSON 스키마"
```

---

## Task 2: manuscript.py 골격 + generate_draft + manuscript-draft 스킬

**Files:**
- Create: `skills/manuscript-draft/SKILL.md`, `skills/manuscript-draft/skill.json`
- Create: `backend/manuscript.py`
- Test: `tests/test_manuscript_draft.py`

- [ ] **Step 1: manuscript-draft 스킬 이식** — Create `skills/manuscript-draft/SKILL.md` porting `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/draft-writer/SKILL.md`, 적응: 입력(research_report.json + editorial_brief.json)은 프롬프트에 주입됨을 전제, v3 파일읽기/CLI 언급 제거, **출력은 단일 JSON `{draft_markdown, questions}`만**(draft_markdown=초고 마크다운 전체, questions=초고 작성 중 생긴 "왜?/어떻게?" 타겟 쿼리 배열). 한국어 규칙(가나·한자 금지) 유지.

`skills/manuscript-draft/skill.json`:
```json
{ "name": "manuscript-draft", "inputs": ["research_report.json", "editorial_brief.json"], "output": "manuscript_draft.json", "output_kind": "json" }
```

- [ ] **Step 2: Write the failing test** — `tests/test_manuscript_draft.py`:

```python
import json
from pathlib import Path
from backend import manuscript, llm


def _inputs(tmp_path):
    (tmp_path / "research_report.json").write_text(json.dumps({"topic": "유한양행", "sources": []}), encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text(json.dumps({"real_topic": "유한양행"}), encoding="utf-8")


def test_generate_draft_writes_draft_and_questions(tmp_path, monkeypatch):
    _inputs(tmp_path)
    captured = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        captured["prompt"] = prompt
        Path(output_last).write_text(json.dumps({
            "draft_markdown": "# 초고\n본문...", "questions": ["왜 1933년인가?", "적자 규모는?"]}),
            encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    draft_path, questions = manuscript.generate_draft(tmp_path)
    assert draft_path == tmp_path / "draft.md"
    assert (tmp_path / "draft.md").read_text(encoding="utf-8").startswith("# 초고")
    assert questions == ["왜 1933년인가?", "적자 규모는?"]
    assert (tmp_path / "research_questions.json").is_file()
    assert "유한양행" in captured["prompt"]


def test_generate_draft_failure_returns_none(tmp_path, monkeypatch):
    _inputs(tmp_path)
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    draft_path, questions = manuscript.generate_draft(tmp_path)
    assert draft_path is None and questions == []
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_draft.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.manuscript`.

- [ ] **Step 4: Create `backend/manuscript.py`** EXACTLY:

```python
"""원고 파이프라인 (adobe 독립 Stage1-2 P4a) — 초안→타겟리서치→적용→래칫.
v3 draft-writer/script-director/script-reviewer 프롬프트를 adobe 스킬로 이식,
llm.run_orchestrator(claude)로 호출, P3 web_agent로 타겟 웹리서치. 런타임 v3 의존 없음."""
from __future__ import annotations

import json
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from backend import llm
from backend.research import web_agent

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"
_SCHEMAS = Path(__file__).resolve().parent / "schemas"
_DRAFT_SCHEMA = _SCHEMAS / "manuscript_draft.schema.json"
_REVIEW_SCHEMA = _SCHEMAS / "manuscript_review.schema.json"


def _load_skill(name: str) -> str:
    md = _SKILLS / name / "SKILL.md"
    return md.read_text(encoding="utf-8") if md.is_file() else f"skill: {name}"


def _read(proj_dir: Path, name: str) -> str:
    p = proj_dir / name
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def generate_draft(proj_dir, *, on_event=None):
    """manuscript-draft 스킬 → draft.md + research_questions.json. 반환 (draft_path|None, questions)."""
    proj_dir = Path(proj_dir)
    out = proj_dir / "manuscript_draft.json"
    prompt = (
        _load_skill("manuscript-draft")
        + "\n\n## 리서치 리포트\n" + _read(proj_dir, "research_report.json")
        + "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json")
        + f"\n\nmanuscript_draft JSON({{draft_markdown, questions}})만 출력. project_id={proj_dir.name}."
    )
    if on_event:
        on_event("원고 초안")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_DRAFT_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") != 0 or not out.is_file():
        return None, []
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return None, []
    draft_path = proj_dir / "draft.md"
    draft_path.write_text(str(data.get("draft_markdown") or ""), encoding="utf-8")
    questions = [str(q) for q in (data.get("questions") or []) if str(q).strip()]
    (proj_dir / "research_questions.json").write_text(
        json.dumps({"questions": questions}, ensure_ascii=False, indent=2), encoding="utf-8")
    return draft_path, questions
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_draft.py -v`
Expected: 2 passed. Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/manuscript-draft/SKILL.md skills/manuscript-draft/skill.json backend/manuscript.py tests/test_manuscript_draft.py
git commit -m "feat(manuscript): manuscript-draft 스킬 + generate_draft"
```

---

## Task 3: targeted_research (web_agent fan-out)

**Files:**
- Modify: `backend/manuscript.py` (add `targeted_research`)
- Test: `tests/test_manuscript_targeted.py`

- [ ] **Step 1: Write the failing test** — `tests/test_manuscript_targeted.py`:

```python
import json
from pathlib import Path
from backend import manuscript


def test_targeted_research_builds_claims(tmp_path, monkeypatch):
    monkeypatch.setattr(manuscript.web_agent, "run_web_research",
                        lambda cwd, prompt, **k: f"발견: {prompt[:6]} https://x")
    claims = manuscript.targeted_research(tmp_path, ["왜 1933년?", "적자 규모?"], max_workers=2)
    assert len(claims) == 2
    assert all("claim" in c and "question" in c for c in claims)
    assert (tmp_path / "targeted_claims.json").is_file()


def test_targeted_research_isolates_empty(tmp_path, monkeypatch):
    seq = iter(["", "발견2 https://y"])
    monkeypatch.setattr(manuscript.web_agent, "run_web_research",
                        lambda cwd, prompt, **k: next(seq, ""))
    claims = manuscript.targeted_research(tmp_path, ["q1", "q2"], max_workers=1)
    assert len(claims) == 1            # 빈 결과 격리
    assert claims[0]["question"] == "q2"


def test_targeted_research_empty_questions(tmp_path, monkeypatch):
    claims = manuscript.targeted_research(tmp_path, [])
    assert claims == []
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_targeted.py -v`
Expected: FAIL — `targeted_research` 부재.

- [ ] **Step 3: Add `targeted_research` to `backend/manuscript.py`** EXACTLY:

```python
def targeted_research(proj_dir, questions, *, max_workers: int = 3, on_event=None) -> list:
    """각 타겟 질문을 web_agent로 병렬 웹리서치 → targeted_claims.json. 빈 결과 격리."""
    proj_dir = Path(proj_dir)
    qs = [str(q).strip() for q in (questions or []) if str(q).strip()]
    if not qs:
        return []

    def _one(q):
        prompt = (
            f"너는 리서치 탐색가다. 다음 질문을 웹 검색·열람으로 해결하라: '{q}'. "
            f"WebSearch/WebFetch를 사용하고, 검증된 답을 출처 URL과 함께 1~3문장으로 보고하라.")
        note = web_agent.run_web_research(proj_dir, prompt, on_line=on_event)
        return {"question": q, "claim": note} if note else None

    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as ex:
        results = list(ex.map(_one, qs))
    claims = [c for c in results if c]
    (proj_dir / "targeted_claims.json").write_text(
        json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
    if on_event:
        on_event(f"타겟 리서치 {len(claims)}/{len(qs)}")
    return claims
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_targeted.py -v`
Expected: 3 passed. Full suite → all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/manuscript.py tests/test_manuscript_targeted.py
git commit -m "feat(manuscript): targeted_research — web_agent 병렬 타겟 리서치"
```

---

## Task 4: write_manuscript + manuscript-write 스킬

**Files:**
- Create: `skills/manuscript-write/SKILL.md`, `skills/manuscript-write/skill.json`
- Modify: `backend/manuscript.py` (add `write_manuscript`)
- Test: `tests/test_manuscript_write.py`

- [ ] **Step 1: manuscript-write 스킬 이식** — Create `skills/manuscript-write/SKILL.md` porting `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/script-director/SKILL.md`의 **manuscript 모드**(한 호흡 prose 작성). 적응: 입력(draft.md + targeted_claims.json + editorial_brief.json)은 프롬프트 주입 전제, 다른 모드/씬 분할/Task 언급 제거, **출력은 final_manuscript 마크다운 본문만**(JSON 아님). 한국어 규칙 유지.

`skills/manuscript-write/skill.json`:
```json
{ "name": "manuscript-write", "inputs": ["draft.md", "targeted_claims.json"], "output": "final_manuscript.v1.md", "output_kind": "md" }
```

- [ ] **Step 2: Write the failing test** — `tests/test_manuscript_write.py`:

```python
import json
from pathlib import Path
from backend import manuscript, llm


def test_write_manuscript_versioned(tmp_path, monkeypatch):
    (tmp_path / "draft.md").write_text("# 초고\n본문", encoding="utf-8")
    (tmp_path / "targeted_claims.json").write_text('[{"question":"q","claim":"c https://x"}]', encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")
    seen = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        seen["prompt"] = prompt
        Path(output_last).write_text("# 최종 원고\n완성 본문", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    out = manuscript.write_manuscript(tmp_path, version=1)
    assert out == tmp_path / "final_manuscript.v1.md"
    assert out.read_text(encoding="utf-8").startswith("# 최종 원고")
    assert "초고" in seen["prompt"] and "c https://x" in seen["prompt"]


def test_write_manuscript_with_revisions(tmp_path, monkeypatch):
    (tmp_path / "draft.md").write_text("초고", encoding="utf-8")
    prev = tmp_path / "final_manuscript.v1.md"
    prev.write_text("이전 원고", encoding="utf-8")
    seen = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        seen["prompt"] = prompt
        Path(output_last).write_text("개선 원고", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    manuscript.write_manuscript(tmp_path, version=2, prev=prev, revisions=["hook 강화"])
    assert "hook 강화" in seen["prompt"] and "이전 원고" in seen["prompt"]


def test_write_manuscript_failure_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    assert manuscript.write_manuscript(tmp_path, version=1) is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_write.py -v`
Expected: FAIL — `write_manuscript` 부재.

- [ ] **Step 4: Add `write_manuscript` to `backend/manuscript.py`** EXACTLY:

```python
def write_manuscript(proj_dir, *, version: int, prev=None, revisions=None, on_event=None):
    """manuscript-write 스킬 → final_manuscript.v{version}.md. 실패 시 None."""
    proj_dir = Path(proj_dir)
    out = proj_dir / f"final_manuscript.v{version}.md"
    parts = [
        _load_skill("manuscript-write"),
        "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json"),
        "\n\n## 초안(draft)\n" + _read(proj_dir, "draft.md"),
        "\n\n## 타겟 리서치(targeted_claims)\n" + _read(proj_dir, "targeted_claims.json"),
    ]
    if prev and Path(prev).is_file():
        parts.append("\n\n## 직전 원고(개선 대상)\n" + Path(prev).read_text(encoding="utf-8"))
    if revisions:
        parts.append("\n\n## REVISE 지시(반드시 반영)\n" + "\n".join(f"- {r}" for r in revisions))
    parts.append(f"\n\nfinal_manuscript 마크다운 본문만 출력. project_id={proj_dir.name}.")
    prompt = "".join(parts)
    if on_event:
        on_event(f"원고 작성 v{version}")
    res = llm.run_orchestrator(prompt, proj_dir, output_last=str(out), on_line=on_event)
    if res.get("returncode") == 0 and out.is_file():
        return out
    return None
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_write.py -v`
Expected: 3 passed. Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/manuscript-write/SKILL.md skills/manuscript-write/skill.json backend/manuscript.py tests/test_manuscript_write.py
git commit -m "feat(manuscript): manuscript-write 스킬 + write_manuscript"
```

---

## Task 5: review_manuscript + manuscript-review 스킬

**Files:**
- Create: `skills/manuscript-review/SKILL.md`, `skills/manuscript-review/skill.json`
- Modify: `backend/manuscript.py` (add `review_manuscript`)
- Test: `tests/test_manuscript_review.py`

- [ ] **Step 1: manuscript-review 스킬 이식** — Create `skills/manuscript-review/SKILL.md` porting `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/script-reviewer/SKILL.md`. 적응: 입력(원고 + editorial_brief.json)은 프롬프트 주입 전제, 씬별 점수 로직 대신 **원고 전체를 시청자+전문가 관점 100점으로 채점**(brief DNA 가중), v3 파일읽기/Task 제거. **출력은 JSON `{score_total, verdict('PASS'|'REVISE'|'FAIL'), revision_instructions:[str], viewer_score, expert_score}`만**. 90↑ PASS. 한국어 규칙 유지.

`skills/manuscript-review/skill.json`:
```json
{ "name": "manuscript-review", "inputs": [], "output": "manuscript_review.v1.json", "output_kind": "json" }
```

- [ ] **Step 2: Write the failing test** — `tests/test_manuscript_review.py`:

```python
import json
from pathlib import Path
from backend import manuscript, llm


def _ms(tmp_path):
    p = tmp_path / "final_manuscript.v1.md"
    p.write_text("# 원고\n본문", encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")
    return p


def test_review_manuscript_pass(tmp_path, monkeypatch):
    ms = _ms(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 92, "verdict": "PASS", "revision_instructions": [],
            "viewer_score": 90, "expert_score": 94}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = manuscript.review_manuscript(tmp_path, ms)
    assert r["score"] == 92 and r["verdict"] == "PASS" and r["revision_instructions"] == []


def test_review_manuscript_revise(tmp_path, monkeypatch):
    ms = _ms(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 80, "verdict": "REVISE",
            "revision_instructions": ["hook 강화", "출처 보강"]}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = manuscript.review_manuscript(tmp_path, ms)
    assert r["score"] == 80 and r["verdict"] == "REVISE"
    assert "hook 강화" in r["revision_instructions"]


def test_review_manuscript_parse_failure(tmp_path, monkeypatch):
    ms = _ms(tmp_path)
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda p, c, **k: (Path(k["output_last"]).write_text("nope", encoding="utf-8"),
                                           {"returncode": 0, "output_last": k["output_last"]})[1])
    r = manuscript.review_manuscript(tmp_path, ms)
    assert r["score"] == 0 and r["verdict"] == "REVISE"
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_review.py -v`
Expected: FAIL — `review_manuscript` 부재.

- [ ] **Step 4: Add `review_manuscript` to `backend/manuscript.py`** EXACTLY:

```python
def review_manuscript(proj_dir, ms_path, *, prev_path=None, on_event=None) -> dict:
    """manuscript-review 스킬로 채점. 반환 {score:int, verdict, revision_instructions:list}.
    파싱/실패 시 score=0, verdict='REVISE'."""
    proj_dir = Path(proj_dir)
    ms_path = Path(ms_path)
    m = re.search(r"\.v(\d+)\.md$", ms_path.name)
    ver = m.group(1) if m else "1"
    out = proj_dir / f"manuscript_review.v{ver}.json"
    parts = [
        _load_skill("manuscript-review"),
        "\n\n## editorial brief\n" + _read(proj_dir, "editorial_brief.json"),
        "\n\n## 평가 대상 원고\n" + ms_path.read_text(encoding="utf-8"),
    ]
    if prev_path and Path(prev_path).is_file():
        parts.append("\n\n## 직전 원고(점수 하락 감시용)\n" + Path(prev_path).read_text(encoding="utf-8"))
    parts.append(f"\n\nmanuscript_review JSON만 출력. project_id={proj_dir.name}.")
    prompt = "".join(parts)
    if on_event:
        on_event(f"원고 채점 v{ver}")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_REVIEW_SCHEMA),
                               output_last=str(out), on_line=on_event)
    fail = {"score": 0, "verdict": "REVISE", "revision_instructions": []}
    if res.get("returncode") != 0 or not out.is_file():
        return fail
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
        score = int(float(data.get("score_total") or 0))
    except Exception:
        return fail
    return {"score": score, "verdict": str(data.get("verdict") or "REVISE"),
            "revision_instructions": list(data.get("revision_instructions") or [])}
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_review.py -v`
Expected: 3 passed. Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/manuscript-review/SKILL.md skills/manuscript-review/skill.json backend/manuscript.py tests/test_manuscript_review.py
git commit -m "feat(manuscript): manuscript-review 스킬 + review_manuscript"
```

---

## Task 6: run_manuscript_pipeline (원고 래칫)

**Files:**
- Modify: `backend/manuscript.py` (add `run_manuscript_pipeline`)
- Test: `tests/test_manuscript_pipeline.py`

- [ ] **Step 1: Write the failing test** — `tests/test_manuscript_pipeline.py`:

```python
import json
from pathlib import Path
from backend import manuscript


def _report(tmp_path):
    (tmp_path / "research_report.json").write_text('{"topic":"유한양행"}', encoding="utf-8")
    (tmp_path / "editorial_brief.json").write_text('{"real_topic":"유한양행"}', encoding="utf-8")


def _patch(monkeypatch, tmp_path, reviews, *, questions=("q1",), draft_ok=True):
    def fake_draft(proj_dir, **k):
        if not draft_ok:
            return None, []
        (Path(proj_dir) / "draft.md").write_text("초고", encoding="utf-8")
        return Path(proj_dir) / "draft.md", list(questions)
    monkeypatch.setattr(manuscript, "generate_draft", fake_draft)
    monkeypatch.setattr(manuscript, "targeted_research",
                        lambda proj, qs, **k: [{"question": q, "claim": "c"} for q in qs])
    def fake_write(proj_dir, *, version, prev=None, revisions=None, on_event=None):
        p = Path(proj_dir) / f"final_manuscript.v{version}.md"
        p.write_text(f"원고 v{version}", encoding="utf-8")
        return p
    monkeypatch.setattr(manuscript, "write_manuscript", fake_write)
    it = iter(reviews)
    monkeypatch.setattr(manuscript, "review_manuscript", lambda proj, ms, **k: next(it))


def test_pipeline_round1_pass(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path, [{"score": 95, "verdict": "PASS", "revision_instructions": []}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["rounds"] == 1 and r["score"] == 95 and r["verdict"] == "PASS"
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v1"
    assert r["claims"] == 1


def test_pipeline_revise_then_pass(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path,
           [{"score": 80, "verdict": "REVISE", "revision_instructions": ["x"]},
            {"score": 91, "verdict": "PASS", "revision_instructions": []}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["rounds"] == 2 and r["verdict"] == "PASS"
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v2"


def test_pipeline_no_pass_locks_best(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path,
           [{"score": 80, "verdict": "REVISE", "revision_instructions": ["a"]},
            {"score": 88, "verdict": "REVISE", "revision_instructions": ["b"]},
            {"score": 85, "verdict": "REVISE", "revision_instructions": ["c"]}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["rounds"] == 3 and r["score"] == 88 and r["verdict"] == "REVISE"
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v2"


def test_pipeline_monotonic_keeps_best(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path,
           [{"score": 85, "verdict": "REVISE", "revision_instructions": ["a"]},
            {"score": 70, "verdict": "REVISE", "revision_instructions": ["b"]},
            {"score": 75, "verdict": "REVISE", "revision_instructions": ["c"]}])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r["score"] == 85
    assert (tmp_path / "final_manuscript.md").read_text(encoding="utf-8") == "원고 v1"


def test_pipeline_no_questions_skips_targeted(tmp_path, monkeypatch):
    _report(tmp_path)
    called = {"targeted": False}
    _patch(monkeypatch, tmp_path, [{"score": 95, "verdict": "PASS", "revision_instructions": []}],
           questions=())
    monkeypatch.setattr(manuscript, "targeted_research",
                        lambda *a, **k: called.__setitem__("targeted", True) or [])
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert called["targeted"] is False and r["claims"] == 0


def test_pipeline_no_report_errors(tmp_path, monkeypatch):
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r.get("error")


def test_pipeline_draft_failure_errors(tmp_path, monkeypatch):
    _report(tmp_path)
    _patch(monkeypatch, tmp_path, [], draft_ok=False)
    r = manuscript.run_manuscript_pipeline(tmp_path)
    assert r.get("error")
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_pipeline.py -v`
Expected: FAIL — `run_manuscript_pipeline` 부재.

- [ ] **Step 3: Add `run_manuscript_pipeline` to `backend/manuscript.py`** EXACTLY:

```python
def run_manuscript_pipeline(proj_dir, *, threshold: int = 90, max_rounds: int = 3,
                            max_workers: int = 3, on_event=None) -> dict:
    """초안→타겟리서치→적용→원고 래칫. 채택본을 final_manuscript.md로 잠금.
    반환 {manuscript, score, verdict, rounds, history, claims} 또는 {error}."""
    proj_dir = Path(proj_dir)
    max_rounds = max(1, int(max_rounds))
    if not (proj_dir / "research_report.json").is_file():
        return {"error": "research_report.json 필요 (P3 먼저)"}

    draft_path, questions = generate_draft(proj_dir, on_event=on_event)
    if draft_path is None:
        return {"error": "초안 생성 실패"}
    claims = targeted_research(proj_dir, questions, max_workers=max_workers, on_event=on_event) if questions else []

    history: list[dict] = []
    best = None                      # (path, score, verdict)
    last_revisions = None
    for n in range(1, max_rounds + 1):
        prev_path = best[0] if best else None
        out = write_manuscript(proj_dir, version=n, prev=prev_path,
                               revisions=last_revisions, on_event=on_event)
        if out is None:
            if best:
                break
            return {"error": "원고 작성 실패", "claims": len(claims)}
        rv = review_manuscript(proj_dir, out, prev_path=prev_path, on_event=on_event)
        history.append({"version": n, "score": rv["score"], "verdict": rv["verdict"]})
        last_revisions = rv["revision_instructions"]
        if best is None or rv["score"] > best[1]:
            best = (out, rv["score"], rv["verdict"])
        if rv["score"] >= threshold and rv["verdict"] == "PASS":
            break

    locked = proj_dir / "final_manuscript.md"
    shutil.copy(best[0], locked)
    if on_event:
        on_event(f"원고 확정 — {best[1]}점 {best[2]} ({len(history)}라운드)")
    return {"manuscript": str(locked), "score": best[1], "verdict": best[2],
            "rounds": len(history), "history": history, "claims": len(claims)}
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_manuscript_pipeline.py -v`
Expected: 7 passed.

- [ ] **Step 5: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존(P1-P3 포함) + 신규(약 20) 전부 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/manuscript.py tests/test_manuscript_pipeline.py
git commit -m "feat(manuscript): run_manuscript_pipeline — 초안→타겟→적용→원고 래칫"
```

---

## Self-Review 결과

**Spec coverage:**
- 스키마(draft/review) → Task 1 ✓ (spec의 research_questions.schema는 manuscript_draft.schema로 통합 — draft 출력 {draft_markdown,questions} 단일 LLM 호출이 더 견고)
- generate_draft(초안+타겟쿼리, manuscript-draft 이식) → Task 2 ✓
- targeted_research(web_agent 병렬, 빈 결과 격리) → Task 3 ✓
- write_manuscript(manuscript-write 이식, draft+claims+prev+revisions) → Task 4 ✓
- review_manuscript(manuscript-review 이식, 시청자+전문가, 파싱실패→0/REVISE) → Task 5 ✓
- run_manuscript_pipeline(래칫 P2 패턴, 타겟쿼리0 스킵, report없음/draft실패 에러) → Task 6 ✓
- 잠금(final_manuscript.md 복사, 무삭제) → Task 6 ✓
- 테스트 7 시나리오 + 자산 → Task 1·6 ✓
- 범위 밖(P4b 씬) 미포함 ✓

**Placeholder scan:** 프롬프트 이식 태스크(2·4·5 Step1)는 원본 경로+적응 규칙으로 구체적. 코드·테스트 전부 완전. ✓

**Type consistency:** `generate_draft`(→tuple)·`targeted_research`(→list)·`write_manuscript`(→Path|None)·`review_manuscript`(→{score,verdict,revision_instructions})·`run_manuscript_pipeline` 시그니처가 Task 간·계약 일치. review 반환 키가 래칫 사용과 일치. run_manuscript_pipeline이 모듈 전역 generate_draft/targeted_research/write_manuscript/review_manuscript 호출 → Task 6 테스트 monkeypatch 지점과 일치. 래칫 로직은 P2 `run_brief_ratchet`와 동일 구조(검증된 패턴). ✓

**알려진 결정:** draft는 단일 JSON({draft_markdown,questions}) 출력 후 orchestrator가 draft.md+research_questions.json로 분리(단일 LLM 호출·견고). write는 마크다운 직접 출력(스키마 없음). review는 score_total(combined) 파싱(viewer/expert는 부가).
