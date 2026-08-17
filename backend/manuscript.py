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
    if not md.is_file():
        return f"skill: {name}"
    text = md.read_text(encoding="utf-8")
    if text.startswith("---"):              # YAML frontmatter는 프롬프트 주입에서 제거(노이즈·inert)
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].lstrip("\n")
    return text


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
