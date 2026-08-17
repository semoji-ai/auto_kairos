# adobe Stage1-2 P2 — editorial brief + 평가·개선 래칫 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** plan.md에서 editorial brief를 생성하고 100점 루브릭 평가·개선 래칫(90점 게이트, 최대 3라운드, 최고점 채택, 점수 단조증가)을 거쳐 잠긴 `editorial_brief.json`을 산출한다. 런타임 v3 의존 0.

**Architecture:** v3 brief-interviewer-auto/brief-reviewer 프롬프트 + brief-dna 레버 정의를 adobe 스킬·데이터로 이식하고, `backend/brief.py`가 `llm.run_orchestrator`(기본 claude)로 생성·채점을 호출하는 단순 Python 래칫 루프로 오케스트레이션한다(v3 거대 러너 미사용).

**Tech Stack:** Python stdlib + `backend.llm`(claude/codex CLI 추상화). 테스트는 pytest + monkeypatch(`llm.run_orchestrator` 또는 `brief.generate_brief`/`review_brief` 대체, 실 LLM 0).

**테스트 실행:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` (worktree 루트에서).

**이식 원본(읽기 전용, 런타임 비의존):**
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/brief-interviewer-auto/SKILL.md`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/brief-reviewer/SKILL.md`
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/shared/brief-dna.md`

**핵심 계약(전 태스크 고정):**
- `parse_plan(proj_dir) -> {topic, writing_style, duration, tone}`
- `generate_brief(proj_dir, *, version:int, prev_brief:Path|None=None, revisions:list|None=None, on_event=None) -> Path|None` → `editorial_brief.v{version}.json`
- `review_brief(proj_dir, brief_path, *, prev_path:Path|None=None, on_event=None) -> {score:int, verdict:str, spine_blocking:dict|None, revision_instructions:list}` (`brief_review_feedback.v{N}.json` 기록)
- `run_brief_ratchet(proj_dir, *, threshold:int=90, max_rounds:int=3, on_event=None) -> {brief:str, score:int, verdict:str, rounds:int, history:list}` — 채택본을 `editorial_brief.json`으로 잠금
- run_brief_ratchet은 **모듈 전역** `generate_brief`/`review_brief`를 호출(테스트 monkeypatch 지점).

---

## Task 1: 스키마 + brief-dna 데이터 이식

**Files:**
- Create: `data/brief-dna.md`
- Create: `backend/schemas/editorial_brief.schema.json`, `backend/schemas/brief_review.schema.json`
- Test: `tests/test_brief_assets.py`

- [ ] **Step 1: `data/brief-dna.md` 이식(verbatim 복사)**

`/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/shared/brief-dna.md` 를 그대로 `data/brief-dna.md` 로 복사한다(레버 정의 참조 문서 — 5대 품질 레버: narrative_arc, human_truth, hidden_truth, present_connection, evidence_anchors). 내용 수정 없음.

- [ ] **Step 2: `backend/schemas/editorial_brief.schema.json` 작성**

LLM 출력이 거부되지 않도록 핵심 키만 required, 중첩은 유연(additionalProperties true):

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["real_topic", "core_question", "narrative_arc", "human_truth", "hidden_truth"],
  "properties": {
    "real_topic": { "type": "string" },
    "core_question": { "type": "string" },
    "hook_angle": { "type": "string" },
    "hidden_truth": { "type": "string" },
    "narrative_arc": { "type": "object", "additionalProperties": true },
    "human_truth": { "type": "object", "additionalProperties": true },
    "present_connection": { "type": "object", "additionalProperties": true },
    "evidence_anchors": {},
    "coherence_spine": { "type": "object", "additionalProperties": true },
    "must_cover": {},
    "excluded_angles": {},
    "audience": {}
  }
}
```

- [ ] **Step 3: `backend/schemas/brief_review.schema.json` 작성**

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["score_total", "verdict", "revision_instructions"],
  "properties": {
    "score_total": { "type": "number" },
    "verdict": { "type": "string", "enum": ["PASS", "REVISE", "FAIL"] },
    "revision_instructions": { "type": "array", "items": { "type": "string" } },
    "score_breakdown": { "type": "object", "additionalProperties": true },
    "field_feedback": { "type": "object", "additionalProperties": true },
    "antipatterns_detected": { "type": "array" },
    "previous_score": { "type": "number" },
    "next_action": { "type": "string" }
  }
}
```

- [ ] **Step 4: Write the failing test** — `tests/test_brief_assets.py`:

```python
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_brief_dna_present_with_levers():
    txt = (ROOT / "data" / "brief-dna.md").read_text(encoding="utf-8")
    for lever in ("narrative_arc", "human_truth", "hidden_truth"):
        assert lever in txt


def test_editorial_brief_schema_valid():
    s = json.loads((ROOT / "backend" / "schemas" / "editorial_brief.schema.json").read_text(encoding="utf-8"))
    assert s["type"] == "object"
    for k in ("real_topic", "core_question", "narrative_arc", "human_truth", "hidden_truth"):
        assert k in s["required"]


def test_brief_review_schema_valid():
    s = json.loads((ROOT / "backend" / "schemas" / "brief_review.schema.json").read_text(encoding="utf-8"))
    assert set(["score_total", "verdict", "revision_instructions"]).issubset(set(s["required"]))
    assert s["properties"]["verdict"]["enum"] == ["PASS", "REVISE", "FAIL"]
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_assets.py -v`
Expected: 3 passed (실패 먼저 확인 후 자산 추가).
Full suite: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q` → all pass.

- [ ] **Step 6: Commit**

```bash
git add data/brief-dna.md backend/schemas/editorial_brief.schema.json backend/schemas/brief_review.schema.json tests/test_brief_assets.py
git commit -m "feat(brief): DNA 레버 데이터 + brief/review JSON 스키마"
```

---

## Task 2: plan.md 파싱

**Files:**
- Create: `backend/brief.py`
- Test: `tests/test_brief_parse_plan.py`

- [ ] **Step 1: Write the failing test** — `tests/test_brief_parse_plan.py`:

```python
import pytest
from backend import brief


def test_parse_plan_full(tmp_path):
    (tmp_path / "plan.md").write_text(
        "# 타이레놀 페이스리프트\n채널: semoji\n분량: 1분\n톤: 흥미로운 다큐\n",
        encoding="utf-8")
    p = brief.parse_plan(tmp_path)
    assert p["topic"] == "타이레놀 페이스리프트"
    assert p["writing_style"] == "semoji"
    assert p["duration"] == "1분"
    assert p["tone"] == "흥미로운 다큐"


def test_parse_plan_defaults_style_semoji(tmp_path):
    (tmp_path / "plan.md").write_text("# 주제만 있음\n", encoding="utf-8")
    p = brief.parse_plan(tmp_path)
    assert p["topic"] == "주제만 있음"
    assert p["writing_style"] == "semoji"   # 채널 없으면 기본


def test_parse_plan_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        brief.parse_plan(tmp_path)
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_parse_plan.py -v`
Expected: FAIL — `ModuleNotFoundError: backend.brief`.

- [ ] **Step 3: `backend/brief.py` 작성(parse_plan + 상수)**

```python
"""editorial brief 생성 + 평가·개선 래칫 (adobe 독립 Stage1-2 P2).
v3 brief-interviewer-auto/brief-reviewer 프롬프트를 adobe 스킬로 이식, llm.run_orchestrator로 호출.
런타임 v3 의존 없음."""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from backend import llm

_ROOT = Path(__file__).resolve().parents[1]
_SKILLS = _ROOT / "skills"
_SCHEMAS = Path(__file__).resolve().parent / "schemas"
_BRIEF_SCHEMA = _SCHEMAS / "editorial_brief.schema.json"
_REVIEW_SCHEMA = _SCHEMAS / "brief_review.schema.json"


def parse_plan(proj_dir) -> dict:
    """plan.md → {topic, writing_style, duration, tone}. 제목은 첫 '# ' 헤더 또는 '제목:'.
    채널 없으면 writing_style='semoji'."""
    plan = Path(proj_dir) / "plan.md"
    if not plan.is_file():
        raise FileNotFoundError(f"plan.md 필요: {plan}")
    text = plan.read_text(encoding="utf-8")
    topic = ""
    fields = {"채널": "", "분량": "", "톤": ""}
    for line in text.splitlines():
        s = line.strip()
        if not topic and s.startswith("# "):
            topic = s[2:].strip()
        if not topic and s.startswith("제목:"):
            topic = s.split(":", 1)[1].strip()
        for key in fields:
            if s.startswith(key + ":"):
                fields[key] = s.split(":", 1)[1].strip()
    return {
        "topic": topic,
        "writing_style": fields["채널"] or "semoji",
        "duration": fields["분량"],
        "tone": fields["톤"],
    }
```

- [ ] **Step 4: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_parse_plan.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/brief.py tests/test_brief_parse_plan.py
git commit -m "feat(brief): plan.md 파싱(parse_plan)"
```

---

## Task 3: brief-interview 스킬 + generate_brief

**Files:**
- Create: `skills/brief-interview/SKILL.md`, `skills/brief-interview/skill.json`
- Modify: `backend/brief.py` (`_run_brief_skill`, `generate_brief` 추가)
- Test: `tests/test_brief_generate.py`

- [ ] **Step 1: brief-interview 스킬 이식**

`skills/brief-interview/SKILL.md` 를 작성: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/brief-interviewer-auto/SKILL.md` 의 내용을 이식하되, v3 전용 참조를 adobe식으로 치환:
- `shared/brief-dna.md` 참조 → `data/brief-dna.md` (프롬프트에 그 내용이 함께 주입됨을 전제로 문구 정리)
- `auto-agent plan ...` 등 v3 CLI 언급 제거
- 출력 지시를 "editorial_brief JSON만 출력"으로 명확화(스키마는 호출 측이 강제)
- semoji 기본, 스타일은 입력의 writing_style 사용

`skills/brief-interview/skill.json`:
```json
{ "name": "brief-interview", "inputs": ["plan.md"], "output": "editorial_brief.v1.json", "output_kind": "json" }
```

- [ ] **Step 2: Write the failing test** — `tests/test_brief_generate.py`:

```python
import json
from pathlib import Path
from backend import brief, llm


def test_generate_brief_writes_versioned(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# 유한양행\n채널: semoji\n분량: 10분\n톤: 다큐\n", encoding="utf-8")
    captured = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        captured["prompt"] = prompt
        captured["schema"] = output_schema
        Path(output_last).write_text(json.dumps({
            "real_topic": "유한양행", "core_question": "왜?", "hidden_truth": "사실은",
            "narrative_arc": {}, "human_truth": {}}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    out = brief.generate_brief(tmp_path, version=1)
    assert out == tmp_path / "editorial_brief.v1.json"
    assert out.is_file()
    assert "유한양행" in captured["prompt"]          # plan 주입
    assert captured["schema"].endswith("editorial_brief.schema.json")


def test_generate_brief_with_revisions_injects_prev(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# 주제\n", encoding="utf-8")
    prev = tmp_path / "editorial_brief.v1.json"
    prev.write_text(json.dumps({"real_topic": "X"}), encoding="utf-8")
    seen = {}

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        seen["prompt"] = prompt
        Path(output_last).write_text("{}", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    brief.generate_brief(tmp_path, version=2, prev_brief=prev,
                         revisions=["hidden_truth를 구체화"])
    assert "hidden_truth를 구체화" in seen["prompt"]   # REVISE 지시 주입
    assert "\"X\"" in seen["prompt"] or "X" in seen["prompt"]   # 이전 brief 주입


def test_generate_brief_failure_returns_none(tmp_path, monkeypatch):
    (tmp_path / "plan.md").write_text("# 주제\n", encoding="utf-8")
    monkeypatch.setattr(llm, "run_orchestrator",
                        lambda *a, **k: {"returncode": 1, "output_last": k.get("output_last")})
    assert brief.generate_brief(tmp_path, version=1) is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_generate.py -v`
Expected: FAIL — `generate_brief` 부재.

- [ ] **Step 4: `backend/brief.py`에 `_load_skill`, `generate_brief` 추가**

```python
def _load_skill(name: str) -> str:
    md = _SKILLS / name / "SKILL.md"
    return md.read_text(encoding="utf-8") if md.is_file() else f"skill: {name}"


def _dna_text() -> str:
    p = _ROOT / "data" / "brief-dna.md"
    return p.read_text(encoding="utf-8") if p.is_file() else ""


def generate_brief(proj_dir, *, version: int, prev_brief=None, revisions=None,
                   on_event=None) -> Path | None:
    """brief-interview 스킬로 editorial_brief.v{version}.json 생성. 실패 시 None."""
    proj_dir = Path(proj_dir)
    plan = parse_plan(proj_dir)
    out = proj_dir / f"editorial_brief.v{version}.json"
    parts = [
        _load_skill("brief-interview"),
        "\n\n## DNA 레버 정의\n" + _dna_text(),
        f"\n\n## 기획 입력\ntopic: {plan['topic']}\nwriting_style: {plan['writing_style']}\n"
        f"duration: {plan['duration']}\ntone: {plan['tone']}\n",
    ]
    if prev_brief and Path(prev_brief).is_file():
        parts.append("\n\n## 직전 brief(개선 대상)\n" + Path(prev_brief).read_text(encoding="utf-8"))
    if revisions:
        parts.append("\n\n## REVISE 지시(반드시 반영)\n" + "\n".join(f"- {r}" for r in revisions))
    parts.append(f"\n\neditorial_brief JSON만 출력. project_id={proj_dir.name}.")
    prompt = "".join(parts)
    if on_event:
        on_event(f"브리프 생성 v{version}")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_BRIEF_SCHEMA),
                               output_last=str(out), on_line=on_event)
    if res.get("returncode") == 0 and out.is_file():
        return out
    return None
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_generate.py -v`
Expected: 3 passed.
Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/brief-interview/SKILL.md skills/brief-interview/skill.json backend/brief.py tests/test_brief_generate.py
git commit -m "feat(brief): brief-interview 스킬 이식 + generate_brief"
```

---

## Task 4: brief-review 스킬 + review_brief

**Files:**
- Create: `skills/brief-review/SKILL.md`, `skills/brief-review/skill.json`
- Modify: `backend/brief.py` (`review_brief` 추가)
- Test: `tests/test_brief_review.py`

- [ ] **Step 1: brief-review 스킬 이식**

`skills/brief-review/SKILL.md` 작성: `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/brief-reviewer/SKILL.md` 이식, `shared/brief-dna.md` 참조 → 프롬프트에 주입되는 `data/brief-dna.md` 전제로 정리. 100점 루브릭·사전 블로킹 게이트(spine G1~G5)·판정(90↑ PASS)·점수 단조증가 규칙·`brief_review_feedback` JSON 출력 구조 유지. 출력은 review JSON만.

`skills/brief-review/skill.json`:
```json
{ "name": "brief-review", "inputs": [], "output": "brief_review_feedback.v1.json", "output_kind": "json" }
```

- [ ] **Step 2: Write the failing test** — `tests/test_brief_review.py`:

```python
import json
from pathlib import Path
from backend import brief, llm


def _brief_file(tmp_path):
    p = tmp_path / "editorial_brief.v1.json"
    p.write_text(json.dumps({"real_topic": "유한양행", "hidden_truth": "사실은"}), encoding="utf-8")
    return p


def test_review_brief_parses_score_verdict(tmp_path, monkeypatch):
    bf = _brief_file(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 92, "verdict": "PASS",
            "revision_instructions": []}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = brief.review_brief(tmp_path, bf)
    assert r["score"] == 92
    assert r["verdict"] == "PASS"
    assert r["revision_instructions"] == []


def test_review_brief_revise_with_instructions(tmp_path, monkeypatch):
    bf = _brief_file(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text(json.dumps({
            "score_total": 80, "verdict": "REVISE",
            "spine_blocking": {"failed_gates": ["G1"], "reasons": ["spine 없음"]},
            "revision_instructions": ["spine_question 작성", "hidden_truth 구체화"]}), encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = brief.review_brief(tmp_path, bf)
    assert r["score"] == 80 and r["verdict"] == "REVISE"
    assert r["spine_blocking"]["failed_gates"] == ["G1"]
    assert "spine_question 작성" in r["revision_instructions"]


def test_review_brief_parse_failure_is_revise_zero(tmp_path, monkeypatch):
    bf = _brief_file(tmp_path)

    def fake_orch(prompt, cwd, *, output_schema=None, output_last=None, **k):
        Path(output_last).write_text("not json", encoding="utf-8")
        return {"returncode": 0, "output_last": output_last}
    monkeypatch.setattr(llm, "run_orchestrator", fake_orch)

    r = brief.review_brief(tmp_path, bf)
    assert r["score"] == 0 and r["verdict"] == "REVISE"
```

- [ ] **Step 3: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_review.py -v`
Expected: FAIL — `review_brief` 부재.

- [ ] **Step 4: `backend/brief.py`에 `review_brief` 추가**

```python
def review_brief(proj_dir, brief_path, *, prev_path=None, on_event=None) -> dict:
    """brief-review 스킬로 채점. 반환 {score:int, verdict, spine_blocking, revision_instructions}.
    파싱 실패/스킬 실패 시 score=0, verdict='REVISE'."""
    proj_dir = Path(proj_dir)
    brief_path = Path(brief_path)
    m = re.search(r"\.v(\d+)\.json$", brief_path.name)
    ver = m.group(1) if m else "1"
    out = proj_dir / f"brief_review_feedback.v{ver}.json"
    parts = [
        _load_skill("brief-review"),
        "\n\n## DNA 레버 정의\n" + _dna_text(),
        "\n\n## 평가 대상 brief\n" + brief_path.read_text(encoding="utf-8"),
    ]
    if prev_path and Path(prev_path).is_file():
        parts.append("\n\n## 직전 버전(점수 하락 감시용)\n" + Path(prev_path).read_text(encoding="utf-8"))
    parts.append(f"\n\nbrief_review_feedback JSON만 출력. project_id={proj_dir.name}.")
    prompt = "".join(parts)
    if on_event:
        on_event(f"브리프 채점 v{ver}")
    res = llm.run_orchestrator(prompt, proj_dir, output_schema=str(_REVIEW_SCHEMA),
                               output_last=str(out), on_line=on_event)
    fail = {"score": 0, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": []}
    if res.get("returncode") != 0 or not out.is_file():
        return fail
    try:
        data = json.loads(out.read_text(encoding="utf-8"))
    except Exception:
        return fail
    return {
        "score": int(data.get("score_total") or 0),
        "verdict": str(data.get("verdict") or "REVISE"),
        "spine_blocking": data.get("spine_blocking"),
        "revision_instructions": list(data.get("revision_instructions") or []),
    }
```

- [ ] **Step 5: Run tests**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_review.py -v`
Expected: 3 passed.
Full suite → all pass.

- [ ] **Step 6: Commit**

```bash
git add skills/brief-review/SKILL.md skills/brief-review/skill.json backend/brief.py tests/test_brief_review.py
git commit -m "feat(brief): brief-review 스킬 이식 + review_brief"
```

---

## Task 5: run_brief_ratchet (래칫 루프)

**Files:**
- Modify: `backend/brief.py` (`run_brief_ratchet` 추가)
- Test: `tests/test_brief_ratchet.py`

- [ ] **Step 1: Write the failing test** — `tests/test_brief_ratchet.py`:

```python
import json
from pathlib import Path
from backend import brief


def _setup(tmp_path):
    (tmp_path / "plan.md").write_text("# 주제\n채널: semoji\n", encoding="utf-8")


def _fake_generate(tmp_path):
    """generate_brief 대체 — v{version}.json 생성하고 경로 반환."""
    def gen(proj_dir, *, version, prev_brief=None, revisions=None, on_event=None):
        p = Path(proj_dir) / f"editorial_brief.v{version}.json"
        p.write_text(json.dumps({"v": version}), encoding="utf-8")
        return p
    return gen


def test_round1_pass_locks(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    monkeypatch.setattr(brief, "review_brief",
                        lambda pd, bp, **k: {"score": 95, "verdict": "PASS",
                                             "spine_blocking": None, "revision_instructions": []})
    r = brief.run_brief_ratchet(tmp_path)
    assert r["rounds"] == 1 and r["score"] == 95 and r["verdict"] == "PASS"
    locked = json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))
    assert locked["v"] == 1


def test_revise_then_pass(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    scores = iter([{"score": 80, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["x"]},
                   {"score": 92, "verdict": "PASS", "spine_blocking": None, "revision_instructions": []}])
    monkeypatch.setattr(brief, "review_brief", lambda pd, bp, **k: next(scores))
    r = brief.run_brief_ratchet(tmp_path)
    assert r["rounds"] == 2 and r["verdict"] == "PASS"
    assert json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))["v"] == 2


def test_no_pass_locks_best(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    scores = iter([{"score": 80, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["a"]},
                   {"score": 88, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["b"]},
                   {"score": 85, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["c"]}])
    monkeypatch.setattr(brief, "review_brief", lambda pd, bp, **k: next(scores))
    r = brief.run_brief_ratchet(tmp_path)
    assert r["rounds"] == 3 and r["verdict"] == "REVISE"
    assert r["score"] == 88   # 최고점
    assert json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))["v"] == 2


def test_monotonic_keeps_best_on_drop(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    scores = iter([{"score": 85, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["a"]},
                   {"score": 70, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["b"]},
                   {"score": 75, "verdict": "REVISE", "spine_blocking": None, "revision_instructions": ["c"]}])
    monkeypatch.setattr(brief, "review_brief", lambda pd, bp, **k: next(scores))
    r = brief.run_brief_ratchet(tmp_path)
    assert r["score"] == 85   # v1 유지(하락분 폐기)
    assert json.loads((tmp_path / "editorial_brief.json").read_text(encoding="utf-8"))["v"] == 1


def test_spine_blocking_forbids_pass(tmp_path, monkeypatch):
    _setup(tmp_path)
    monkeypatch.setattr(brief, "generate_brief", _fake_generate(tmp_path))
    # 점수 95라도 verdict REVISE(스킬이 게이트로 강제) → PASS 안 됨
    monkeypatch.setattr(brief, "review_brief",
                        lambda pd, bp, **k: {"score": 95, "verdict": "REVISE",
                                             "spine_blocking": {"failed_gates": ["G1"], "reasons": ["no spine"]},
                                             "revision_instructions": ["spine 작성"]})
    r = brief.run_brief_ratchet(tmp_path, max_rounds=2)
    assert r["verdict"] != "PASS"        # 게이트로 PASS 차단
    assert r["rounds"] == 2


def test_generate_failure_locks_best_or_errors(tmp_path, monkeypatch):
    _setup(tmp_path)
    # 1라운드부터 생성 실패 → best 없음 → error
    monkeypatch.setattr(brief, "generate_brief", lambda *a, **k: None)
    monkeypatch.setattr(brief, "review_brief", lambda *a, **k: {"score": 0, "verdict": "REVISE",
                                                               "spine_blocking": None, "revision_instructions": []})
    r = brief.run_brief_ratchet(tmp_path)
    assert r.get("error")
```

- [ ] **Step 2: Run to verify it fails**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_ratchet.py -v`
Expected: FAIL — `run_brief_ratchet` 부재.

- [ ] **Step 3: `backend/brief.py`에 `run_brief_ratchet` 추가**

```python
def run_brief_ratchet(proj_dir, *, threshold: int = 90, max_rounds: int = 3,
                      on_event=None) -> dict:
    """기획 brief 평가·개선 래칫. 90점↑+PASS면 잠금·종료, 미달은 REVISE로 다음 버전.
    최대 max_rounds. 점수 단조증가(하락 버전 폐기). 미PASS면 최고점 채택(비블로킹).
    채택본을 editorial_brief.json으로 잠금. 반환 {brief, score, verdict, rounds, history}."""
    proj_dir = Path(proj_dir)
    history: list[dict] = []
    best = None                      # (path, score, verdict)
    last_revisions = None

    for n in range(1, max_rounds + 1):
        prev_path = best[0] if best else None
        out = generate_brief(proj_dir, version=n, prev_brief=prev_path,
                             revisions=last_revisions, on_event=on_event)
        if out is None:              # 생성 실패 — best 있으면 잠그고 종료, 없으면 error
            if best:
                break
            return {"error": "브리프 생성 실패", "rounds": n, "history": history}
        rv = review_brief(proj_dir, out, prev_path=prev_path, on_event=on_event)
        history.append({"version": n, "score": rv["score"], "verdict": rv["verdict"]})
        last_revisions = rv["revision_instructions"]
        passed = rv["score"] >= threshold and rv["verdict"] == "PASS"
        if best is None or rv["score"] > best[1]:    # 단조증가 — 더 높을 때만 채택
            best = (out, rv["score"], rv["verdict"])
        if passed:
            break

    rounds = len(history)
    locked = proj_dir / "editorial_brief.json"
    shutil.copy(best[0], locked)     # 무삭제: v{N} 원본 보존, json은 채택본 복사
    if on_event:
        on_event(f"브리프 확정 — {best[1]}점 {best[2]} ({rounds}라운드)")
    return {"brief": str(locked), "score": best[1], "verdict": best[2],
            "rounds": rounds, "history": history}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_brief_ratchet.py -v`
Expected: 6 passed.

Note: `test_spine_blocking_forbids_pass`는 verdict가 REVISE이므로 passed=False → 2라운드 모두 REVISE, best는 첫 95점(둘째도 95지만 > 아니라 첫째 유지), verdict 'REVISE'. PASS 아님 확인.
Note: `test_no_pass_locks_best`는 80→88→85, best=88(v2), 단조증가로 85(v3)는 폐기, verdict REVISE.

- [ ] **Step 5: 전체 회귀**

Run: `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest -q`
Expected: 기존(P1 포함) + 신규(약 18) 전부 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/brief.py tests/test_brief_ratchet.py
git commit -m "feat(brief): run_brief_ratchet — 점수 게이트 평가·개선 래칫"
```

---

## Self-Review 결과

**Spec coverage:**
- 엔진=llm.run_orchestrator → Task 3·4 ✓
- 래칫(90/3/최고점/단조증가) → Task 5 ✓
- 브리프 생성(brief-interview 이식, DNA 레버, prev+revisions 주입) → Task 3 ✓
- 채점(brief-review 이식, score/verdict/spine_blocking/revisions 파싱, 파싱실패→0/REVISE) → Task 4 ✓
- plan.md 파싱(제목/채널/분량/톤, 기본 semoji) → Task 2 ✓
- 스키마·brief-dna 이식 → Task 1 ✓
- 잠금(editorial_brief.json 복사, 무삭제) → Task 5 ✓
- spine 블로킹 게이트(verdict REVISE 강제, brief.py는 verdict 신뢰) → Task 4 스킬 + Task 5 테스트 ✓
- 에러 처리(생성 실패→best/error, 파싱 실패→REVISE) → Task 4·5 ✓
- 테스트 6 시나리오 + 자산 검증 → Task 1·5 ✓
- 범위 밖(P3 리서치 쿼리/수집, P4 원고) 미포함 ✓

**Placeholder scan:** 프롬프트 이식 태스크(3·4 Step1)는 "원본 경로 + 치환 규칙"으로 구체적. 그 외 코드·테스트 전부 완전. ✓

**Type consistency:** `generate_brief`/`review_brief`/`run_brief_ratchet` 시그니처가 계약·Task 간 일치. review_brief 반환 키(`score`,`verdict`,`spine_blocking`,`revision_instructions`)가 ratchet 사용과 일치. run_brief_ratchet이 모듈 전역 generate_brief/review_brief 호출 → Task 5 테스트 monkeypatch 지점과 일치. ✓

**알려진 설계 결정:** brief.py는 brief 내용을 깊이 파싱하지 않고 reviewer verdict를 신뢰(spine 게이트 판정은 LLM 스킬 내부). 스키마는 LLM 출력 거부 방지 위해 핵심 키만 required + additionalProperties.
