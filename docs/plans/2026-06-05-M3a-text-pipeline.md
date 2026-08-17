# M3a — 텍스트 파이프라인 (기획→…→고도화) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 주제 하나로 기획→딥리서치→원고(모션그래픽 연출)→타겟리서치→최종원고→시청자/전문가 평가→고도화를 codex로 순차 실행해, 평가 통과한 최종 원고를 생성한다.

**Architecture:** scene-decompose 전용이던 `/api/skills/run`을 **skill.json 기반 범용 러너**로 일반화. 각 단계는 codex 스킬(SKILL.md + skill.json). 백엔드 `pipeline.py`가 단계를 순차 실행하며 codex 세션(resume)으로 맥락 유지. 출력은 단계별 산출 파일(md/json).

**Tech Stack:** Python 3.12(표준 라이브러리), pytest, codex CLI(exec/resume).

**테스트 파이썬:** `/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest` **repo 루트에서**.

근거: `docs/design/M3_pipeline_contract.md` §2(단계 매핑) §3(구현결정).

---

## File Structure

| 파일 | 책임 |
|------|------|
| `backend/skills_cfg.py` | skill.json 로드 + 프롬프트 빌드(순수) |
| `backend/sessions.py` | 프로젝트별 codex session_id 저장/로드 |
| `backend/router.py` | `/api/skills/run` 범용화 + `/api/pipeline/run` |
| `backend/pipeline.py` | 텍스트 단계 순차 오케스트레이션 |
| `skills/<name>/SKILL.md` + `skill.json` | plan-explore, deep-research, draft-write, target-research, finalize-manuscript, review-refine (+ 기존 scene-decompose에 skill.json 추가) |
| `tests/test_skills_cfg.py` `tests/test_sessions.py` `tests/test_pipeline.py` | 단위 테스트 |

스킬 단계 순서(PIPELINE): `plan-explore → deep-research → draft-write → target-research → finalize-manuscript → review-refine`.

---

## Task 1: skill.json 설정 + 프롬프트 빌더 (skills_cfg.py)

**Files:** Create `backend/skills_cfg.py`, `skills/scene-decompose/skill.json`; Test `tests/test_skills_cfg.py`

- [ ] **Step 1: scene-decompose에 skill.json 추가** — `skills/scene-decompose/skill.json`:
```json
{
  "name": "scene-decompose",
  "inputs": ["final_manuscript.md"],
  "output": "scenes.json",
  "output_kind": "json",
  "schema": "scenes.schema.json"
}
```

- [ ] **Step 2: 실패 테스트** — `tests/test_skills_cfg.py`:
```python
from pathlib import Path
from backend import skills_cfg

SKILLS = Path(__file__).resolve().parents[1] / "skills"


def test_load_config():
    c = skills_cfg.load_config(SKILLS, "scene-decompose")
    assert c["output"] == "scenes.json"
    assert c["inputs"] == ["final_manuscript.md"]
    assert c["output_kind"] == "json"


def test_build_prompt_includes_skill_and_inputs(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    (proj / "final_manuscript.md").write_text("원고내용ABC", encoding="utf-8")
    c = skills_cfg.load_config(SKILLS, "scene-decompose")
    prompt = skills_cfg.build_prompt(SKILLS, "scene-decompose", c, proj)
    assert "원고내용ABC" in prompt           # 입력 파일 본문 포함
    assert "scene-decompose" in prompt        # SKILL.md 포함
    assert "scenes.json" in prompt            # 출력 지시 포함


def test_missing_inputs(tmp_path):
    proj = tmp_path / "p"; proj.mkdir()
    c = skills_cfg.load_config(SKILLS, "scene-decompose")
    missing = skills_cfg.missing_inputs(c, proj)
    assert "final_manuscript.md" in missing
```

- [ ] **Step 3: 실패 확인** — `... -m pytest tests/test_skills_cfg.py -v` → FAIL (ModuleNotFoundError)

- [ ] **Step 4: 구현** — `backend/skills_cfg.py`:
```python
"""스킬 설정(skill.json) 로드 + codex 프롬프트 빌드 (순수)."""
from __future__ import annotations

import json
from pathlib import Path


def load_config(skills_dir: Path, name: str) -> dict:
    cfg = skills_dir / name / "skill.json"
    data = json.loads(cfg.read_text(encoding="utf-8"))
    data.setdefault("inputs", [])
    data.setdefault("output_kind", "md")
    data.setdefault("schema", None)
    return data


def missing_inputs(config: dict, proj_dir: Path) -> list[str]:
    return [f for f in config.get("inputs", []) if not (proj_dir / f).exists()]


def build_prompt(skills_dir: Path, name: str, config: dict, proj_dir: Path) -> str:
    skill_md = skills_dir / name / "SKILL.md"
    parts = [skill_md.read_text(encoding="utf-8") if skill_md.exists() else f"skill: {name}"]
    for fname in config.get("inputs", []):
        fp = proj_dir / fname
        if fp.exists():
            parts.append(f"\n\n## 입력: {fname}\n{fp.read_text(encoding='utf-8')}")
    out = config["output"]
    if config.get("output_kind") == "json":
        parts.append(f"\n\nproject_id={proj_dir.name}. {out} 내용(JSON)만 출력.")
    else:
        parts.append(f"\n\nproject_id={proj_dir.name}. {out} 에 들어갈 본문(마크다운)만 출력.")
    return "".join(parts)
```

- [ ] **Step 5: 통과** — `... -m pytest tests/test_skills_cfg.py -v` → PASS (3 passed)

- [ ] **Step 6: 커밋**
```bash
git add backend/skills_cfg.py skills/scene-decompose/skill.json tests/test_skills_cfg.py
git commit -m "feat(backend): skill.json 설정 + 범용 프롬프트 빌더"
```

---

## Task 2: 세션 저장 (sessions.py)

**Files:** Create `backend/sessions.py`; Test `tests/test_sessions.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_sessions.py`:
```python
from backend import sessions


def test_roundtrip(tmp_path):
    assert sessions.load_session(tmp_path) is None
    sessions.save_session(tmp_path, "sess-abc")
    assert sessions.load_session(tmp_path) == "sess-abc"


def test_overwrite(tmp_path):
    sessions.save_session(tmp_path, "s1")
    sessions.save_session(tmp_path, "s2")
    assert sessions.load_session(tmp_path) == "s2"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_sessions.py -v` → FAIL

- [ ] **Step 3: 구현** — `backend/sessions.py`:
```python
"""프로젝트별 codex 세션 id 저장/로드 (.codex_session 사이드카)."""
from __future__ import annotations

from pathlib import Path

_FILE = ".codex_session"


def load_session(proj_dir: Path) -> str | None:
    fp = proj_dir / _FILE
    if not fp.exists():
        return None
    val = fp.read_text(encoding="utf-8").strip()
    return val or None


def save_session(proj_dir: Path, session_id: str) -> None:
    (proj_dir / _FILE).write_text(session_id, encoding="utf-8")
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_sessions.py -v` → PASS (2 passed)

- [ ] **Step 5: gitignore** — `.gitignore`에 `projects/*/.codex_session` 추가(세션은 커밋 안 함).

- [ ] **Step 6: 커밋**
```bash
git add backend/sessions.py tests/test_sessions.py .gitignore
git commit -m "feat(backend): 프로젝트별 codex 세션 저장(멀티턴 resume용)"
```

---

## Task 3: /api/skills/run 범용화 (router.py)

**Files:** Modify `backend/router.py`; Test `tests/test_router.py`

- [ ] **Step 1: 기존 동작 보존 테스트 확인** — `tests/test_router.py`의 `test_skills_run_returns_job_id`(monkeypatch), `test_skills_run_missing_manuscript_422`가 범용화 후에도 통과해야 함. 먼저 현 상태 PASS 확인: `... -m pytest tests/test_router.py -v`

- [ ] **Step 2: router.py의 /api/skills/run 블록 교체** — 기존 scene-decompose 하드코딩 블록을 skills_cfg 기반으로:
```python
    if method == "POST" and p == "/api/skills/run":
        b = body or {}
        pid, skill = b.get("project_id", ""), b.get("skill_name", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        try:
            cfg = skills_cfg.load_config(SKILLS_DIR, skill)
        except FileNotFoundError:
            return 404, {"error": f"skill not found: {skill}"}
        miss = skills_cfg.missing_inputs(cfg, proj_dir)
        if miss:
            return 422, {"error": f"입력 누락: {', '.join(miss)}"}
        jobs = ctx["jobs"]
        jid = jobs.create(skill, pid)
        prompt = skills_cfg.build_prompt(SKILLS_DIR, skill, cfg, proj_dir)
        out = proj_dir / cfg["output"]
        out.parent.mkdir(parents=True, exist_ok=True)
        schema = (SKILLS_DIR / skill / cfg["schema"]) if cfg.get("schema") else None
        sid = sessions.load_session(proj_dir)
        result = run_skill(
            prompt, proj_dir,
            session_id=sid,
            output_schema=str(schema) if schema else None,
            output_last=str(out),
            on_line=lambda ln: jobs.append_log(jid, ln),
        )
        if result.get("session_id"):
            sessions.save_session(proj_dir, result["session_id"])
        if result["returncode"] == 0 and out.exists():
            jobs.set_status(jid, "completed", artifact_paths=[str(out)])
        else:
            jobs.set_status(jid, "failed", error=f"rc={result['returncode']}")
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"]}
```
그리고 router.py 상단 import에 추가: `from backend import skills_cfg, sessions`.
(`run_skill`, `SKILLS_DIR`는 이미 존재. `final_manuscript.md` 전용 422 가드는 skill.json inputs 기반 missing 가드로 대체됨 — scene-decompose의 inputs=["final_manuscript.md"]라 동작 동일.)

- [ ] **Step 3: 422 테스트 갱신** — `tests/test_router.py`의 `test_skills_run_missing_manuscript_422`가 여전히 통과하는지 확인(scene-decompose inputs에 final_manuscript.md 있으므로 누락 시 422). 통과하면 수정 불필요.

- [ ] **Step 4: 통과 확인 (멱등 2회)** — `... -m pytest tests/ -q` 두 번 → 전체 PASS, git status 클린.

- [ ] **Step 5: 커밋**
```bash
git add backend/router.py tests/test_router.py
git commit -m "feat(backend): /api/skills/run 범용화 — skill.json 기반 + 세션 resume"
```

---

## Task 4: 텍스트 스킬 6종 작성

각 스킬 = `skills/<name>/SKILL.md` + `skills/<name>/skill.json`. 모두 codex 텍스트 스킬. 한국어 규칙(가타카나/히라가나/한자 금지) 명시.

- [ ] **Step 1: plan-explore** — `skills/plan-explore/skill.json`:
```json
{"name":"plan-explore","inputs":["plan.md"],"output":"strategy/options.md","output_kind":"md","schema":null}
```
`skills/plan-explore/SKILL.md`:
```markdown
---
name: plan-explore
description: 주제를 영상 기획 각도/훅/구조 옵션으로 탐색. 추천 조합 제시.
---
# plan-explore
주제(plan.md)를 받아 1분 영상 기획 옵션을 만든다.
## 출력(strategy/options.md, 마크다운만)
- 후보 각도 2~3개(각 한 줄 핵심 + 훅 문장)
- 추천 구조(도입–전개–마무리, 1분 ≈ 한국어 400자 기준)
- 추천 조합 1개 + 이유
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 2: deep-research** — `skills/deep-research/skill.json`:
```json
{"name":"deep-research","inputs":["plan.md","strategy/options.md"],"output":"research_reports/deep.md","output_kind":"md","schema":null}
```
`skills/deep-research/SKILL.md`:
```markdown
---
name: deep-research
description: 주제의 역사·구조·핵심 사실을 수집해 보고서로 정리. codex 웹 검색 사용.
---
# deep-research
주제의 깊은 맥락을 조사한다. **codex의 웹 검색 도구가 가능하면 사용**해 최신·정확한 사실을 모으고, 불가하면 보유 지식으로 작성하되 불확실한 부분을 표시한다.
## 출력(research_reports/deep.md, 마크다운만)
- 역사·타임라인 / 핵심 인물·사건 / 숫자·근거 / (가능시)출처
## 금지
- 추측을 사실처럼 단정. 불확실은 "추정"으로 표기.
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 3: draft-write** — `skills/draft-write/skill.json`:
```json
{"name":"draft-write","inputs":["plan.md","strategy/options.md","research_reports/deep.md"],"output":"drafts/v1.md","output_kind":"md","schema":null}
```
`skills/draft-write/SKILL.md`:
```markdown
---
name: draft-write
description: 리서치 기반 1분 영상 원고/시나리오 작성. 모션그래픽 연출 메타라인 포함.
---
# draft-write
research + 기획을 바탕으로 1분(한국어 약 400자) 원고를 쓴다.
## 작성 규칙
- 도입 훅으로 시작(메타 도입 "지금부터 ~할게요" 금지)
- 내레이션 본문 + 모션그래픽 연출은 **메타라인**으로: `[B-roll: ...]`, `(연출: ...)`
- 연출 메타라인은 내레이션과 별도 줄(낭독 대상 아님)
## 출력(drafts/v1.md, 마크다운만)
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 4: target-research** — `skills/target-research/skill.json`:
```json
{"name":"target-research","inputs":["drafts/v1.md","research_reports/deep.md"],"output":"research_targeted/targeted.md","output_kind":"md","schema":null}
```
`skills/target-research/SKILL.md`:
```markdown
---
name: target-research
description: 원고에서 더 흥미로울 포인트의 타겟 쿼리를 뽑아 정밀 리서치.
---
# target-research
draft에서 "더 구체적이면 강해질" 지점 3개 내외를 골라 쿼리화하고 조사한다(가능시 codex 웹 검색).
## 출력(research_targeted/targeted.md, 마크다운만)
- 쿼리별: 질문 → 핵심 답 → (가능시)출처
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 5: finalize-manuscript** — `skills/finalize-manuscript/skill.json`:
```json
{"name":"finalize-manuscript","inputs":["drafts/v1.md","research_targeted/targeted.md"],"output":"final_manuscript.md","output_kind":"md","schema":null}
```
`skills/finalize-manuscript/SKILL.md`:
```markdown
---
name: finalize-manuscript
description: draft + 타겟리서치를 반영해 최종 원고 확정. 모션그래픽 메타라인 보존.
---
# finalize-manuscript
draft에 타겟리서치 사실을 녹여 최종본을 만든다. 분량 1분(한국어 약 400자) 유지.
## 출력(final_manuscript.md, 마크다운만)
- 내레이션 + `[B-roll:]`/`(연출:)` 메타라인 보존
## 금지
- 새로운 미검증 주장 추가. 분량 과다.
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 6: review-refine** — `skills/review-refine/skill.json`:
```json
{"name":"review-refine","inputs":["final_manuscript.md","research_reports/deep.md","research_targeted/targeted.md"],"output":"final_manuscript.md","output_kind":"md","schema":null}
```
`skills/review-refine/SKILL.md`:
```markdown
---
name: review-refine
description: 시청자/전문가 관점으로 최종 원고를 평가하고 약점을 고쳐 개선본을 출력.
---
# review-refine
final_manuscript.md를 두 관점으로 평가하고 개선한다(오토리서치+고도화).
## 평가
- **시청자 관점**: 도입 흡인력·이해도·재미 (0~10 점수 + 한 줄 사유)
- **전문가 관점**: 사실 정확성·논리 (PASS/CONDITIONAL/REVISION + 핵심 이슈)
## 개선
- 사실 정확성·안전성 이슈 우선 반영. 시청자 약점(도입/흐름) 보강.
- narration 분량 1분 유지. 모션그래픽 메타라인 보존.
## 출력(final_manuscript.md, 마크다운만)
- **개선된 최종 원고 본문만** 출력(평가 코멘트는 본문에 넣지 말 것).
## 한국어 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 7: 스킬 설정 검증 테스트** — `tests/test_skills_cfg.py`에 추가:
```python
import pytest

PIPELINE = ["plan-explore", "deep-research", "draft-write",
            "target-research", "finalize-manuscript", "review-refine"]


@pytest.mark.parametrize("name", PIPELINE)
def test_pipeline_skill_configs_load(name):
    c = skills_cfg.load_config(SKILLS, name)
    assert c["name"] == name
    assert c["output"]
    assert (SKILLS / name / "SKILL.md").exists()
```

- [ ] **Step 8: 통과 + 커밋**
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/test_skills_cfg.py -v
git add skills/plan-explore skills/deep-research skills/draft-write skills/target-research skills/finalize-manuscript skills/review-refine tests/test_skills_cfg.py
git commit -m "feat(skills): 텍스트 파이프라인 6스킬 (기획~고도화) SKILL.md + skill.json"
```

---

## Task 5: 파이프라인 오케스트레이션 (pipeline.py + /api/pipeline/run)

**Files:** Create `backend/pipeline.py`; Modify `backend/router.py`; Test `tests/test_pipeline.py`

- [ ] **Step 1: 실패 테스트** — `tests/test_pipeline.py`:
```python
from pathlib import Path
from backend import pipeline


def test_pipeline_order():
    assert pipeline.PIPELINE == [
        "plan-explore", "deep-research", "draft-write",
        "target-research", "finalize-manuscript", "review-refine",
    ]


def test_run_pipeline_calls_each_stage(tmp_path, monkeypatch):
    import backend.pipeline as p
    proj = tmp_path / "proj"; proj.mkdir()
    (proj / "plan.md").write_text("# 테스트 주제", encoding="utf-8")
    called = []

    def fake_run_one(skills_dir, proj_dir, name, on_line=None):
        called.append(name)
        # 각 스킬의 출력 파일을 생성해 다음 단계 입력 충족
        from backend import skills_cfg
        cfg = skills_cfg.load_config(skills_dir, name)
        out = proj_dir / cfg["output"]
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("산출", encoding="utf-8")
        return {"status": "completed", "output": str(out)}

    monkeypatch.setattr(p, "run_one", fake_run_one)
    result = p.run_pipeline(Path(__file__).resolve().parents[1] / "skills", proj)
    assert called == p.PIPELINE
    assert result["status"] == "completed"
```

- [ ] **Step 2: 실패 확인** — `... -m pytest tests/test_pipeline.py -v` → FAIL

- [ ] **Step 3: 구현** — `backend/pipeline.py`:
```python
"""텍스트 파이프라인 순차 오케스트레이션."""
from __future__ import annotations

from pathlib import Path

from backend import skills_cfg, sessions
from backend.codex_runner import run_skill

PIPELINE = [
    "plan-explore", "deep-research", "draft-write",
    "target-research", "finalize-manuscript", "review-refine",
]


def run_one(skills_dir: Path, proj_dir: Path, name: str, on_line=None) -> dict:
    """단일 스킬 실행(세션 resume + 출력 캡처)."""
    cfg = skills_cfg.load_config(skills_dir, name)
    miss = skills_cfg.missing_inputs(cfg, proj_dir)
    if miss:
        return {"status": "failed", "error": f"입력 누락: {miss}"}
    prompt = skills_cfg.build_prompt(skills_dir, name, cfg, proj_dir)
    out = proj_dir / cfg["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = (skills_dir / name / cfg["schema"]) if cfg.get("schema") else None
    sid = sessions.load_session(proj_dir)
    res = run_skill(
        prompt, proj_dir, session_id=sid,
        output_schema=str(schema) if schema else None,
        output_last=str(out), on_line=on_line,
    )
    if res.get("session_id"):
        sessions.save_session(proj_dir, res["session_id"])
    if res["returncode"] == 0 and out.exists():
        return {"status": "completed", "output": str(out)}
    return {"status": "failed", "error": f"rc={res['returncode']}", "stage": name}


def run_pipeline(skills_dir: Path, proj_dir: Path, on_line=None) -> dict:
    """PIPELINE 순차 실행. 한 단계 실패 시 중단."""
    done = []
    for name in PIPELINE:
        if on_line:
            on_line(f"[stage] {name}")
        r = run_one(skills_dir, proj_dir, name, on_line=on_line)
        if r["status"] != "completed":
            return {"status": "failed", "stage": name, "error": r.get("error"),
                    "completed": done}
        done.append(name)
    return {"status": "completed", "completed": done,
            "final": str(proj_dir / "final_manuscript.md")}
```

- [ ] **Step 4: 통과** — `... -m pytest tests/test_pipeline.py -v` → PASS (2 passed)

- [ ] **Step 5: /api/pipeline/run 라우트 추가** — `backend/router.py`에 `from backend import pipeline` 추가, `/api/skills/run` 블록 다음에:
```python
    if method == "POST" and p == "/api/pipeline/run":
        b = body or {}
        pid = b.get("project_id", "")
        proj_dir = root / pid
        if not proj_dir.is_dir():
            return 404, {"error": f"project not found: {pid}"}
        jobs = ctx["jobs"]
        jid = jobs.create("pipeline", pid)
        res = pipeline.run_pipeline(SKILLS_DIR, proj_dir,
                                    on_line=lambda ln: jobs.append_log(jid, ln))
        if res["status"] == "completed":
            jobs.set_status(jid, "completed", artifact_paths=[res["final"]])
        else:
            jobs.set_status(jid, "failed", error=f"{res.get('stage')}: {res.get('error')}")
        return 200, {"job_id": jid, "status": jobs.get(jid)["status"],
                     "completed": res.get("completed", [])}
```

- [ ] **Step 6: 전체 테스트 (멱등 2회) + 커밋**
```bash
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m pytest tests/ -q   # 2회
git add backend/pipeline.py backend/router.py tests/test_pipeline.py
git commit -m "feat(backend): 텍스트 파이프라인 오케스트레이션 + /api/pipeline/run"
```

---

## Task 6: codex 웹 검색 PoC (deep-research 전제 검증)

**Files:** (검증만, 커밋 없음 가능)

- [ ] **Step 1: codex 웹 검색 가능 여부 확인** — repo 루트에서:
```bash
cd /tmp && codex exec --skip-git-repo-check -o /tmp/web_poc.txt - <<'EOF'
2024년 이후 사실을 한 줄로: 일론 머스크가 트위터(X)를 인수한 연도는? 모르면 "웹검색 불가"라고만 답해.
EOF
cat /tmp/web_poc.txt
```
Expected: 정확한 연도(2022)면 codex가 지식/웹으로 답 가능. "웹검색 불가"면 deep-research를 보유지식+불확실표기 모드로 운용(스킬에 이미 명시됨).

- [ ] **Step 2: 결과 기록** — `docs/poc/POC_codex_web.md`에 한 줄 결과(웹검색 가능/지식기반) 기록 후 커밋:
```bash
git add docs/poc/POC_codex_web.md
git commit -m "poc(codex): 웹 검색 가능 여부 확인 — deep-research 운용 모드 결정"
```

---

## Task 7: 라이브 e2e — 테슬라 1분 (사용자 확인 항목)

**Files:** `projects/tesla/plan.md` (신규 프로젝트)

> ⚠️ 실제 codex를 6단계 호출 — 시간/크레딧 소요. **사용자 합의 후 실행.**

- [ ] **Step 1: 테스트 프로젝트 생성** — `projects/tesla/plan.md`:
```markdown
# 테슬라의 역사

채널: semoji
분량: 1분
톤: 흥미로운 다큐
```

- [ ] **Step 2: 백엔드 기동 + 파이프라인 실행**
```bash
cd /Users/jleavens_macmini/LocalProjects/auto_kairos_adobe
/Users/jleavens_macmini/Projects/auto_kairos_v3/.venv/bin/python -m backend.app &
sleep 2
curl -s -X POST http://127.0.0.1:8765/api/pipeline/run -H 'Content-Type: application/json' \
  -d '{"project_id":"tesla"}'
```
Expected: `{"status":"completed","completed":[6단계]}` (수 분 소요).

- [ ] **Step 3: 산출물 확인**
```bash
ls projects/tesla/{strategy,research_reports,drafts,research_targeted}/ projects/tesla/final_manuscript.md
cat projects/tesla/final_manuscript.md
```
Expected: 최종 원고(한국어 ≈400자, `[B-roll]`/`(연출)` 메타라인 포함, 시청자/전문가 평가 반영본).

- [ ] **Step 4: 정리** — 생성 산출물은 gitignore(scenes.json 등) 외 원고/리서치는 보고용. `.codex_session`은 커밋 안 됨 확인. pkill backend.

---

## Task 8: 통합 검증

- [ ] **Step 1: 전체 단위 테스트 (멱등 2회)** — `... -m pytest tests/ -q` 두 번 → 전체 PASS, git status 클린.
- [ ] **Step 2: import 확인** — `... -c "from backend import app, router, skills_cfg, sessions, pipeline; print('ok')"`
- [ ] **Step 3: 스킬 6종 + scene-decompose skill.json 로드 확인** — `... -m pytest tests/test_skills_cfg.py -v`

---

## Self-Review (작성자 체크)

- **계약 커버리지**: ① plan-explore ② deep-research ③ draft-write(모션그래픽 메타라인) ④ target-research ⑤ finalize-manuscript ⑥⑦ review-refine(시청자/전문가). §2 매핑 전부 스킬로. 범용 러너(T1·T3)·세션(T2)·오케스트레이션(T5)·웹 PoC(T6)·e2e(T7).
- **Placeholder**: 없음 — 모든 코드/스킬 본문 포함.
- **타입 일관성**: `load_config/build_prompt/missing_inputs`, `load_session/save_session`, `run_one/run_pipeline/PIPELINE`, `run_skill(prompt,cwd,session_id,output_schema,output_last,on_line)` — Task 간 일치. scene-decompose 후방호환(skill.json + 범용 러너로 M2 테스트 유지).
- **미반영(의도)**: 이미지/스토리보드(⑧⑨⑩)는 M3b/M3c. 비동기/스트리밍 폴링은 동기 유지(긴 파이프라인 시 후속).
