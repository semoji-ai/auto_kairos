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
        score = int(float(data.get("score_total") or 0))   # 숫자 아닌 값이면 except→fail
    except Exception:
        return fail
    return {
        "score": score,
        "verdict": str(data.get("verdict") or "REVISE"),
        "spine_blocking": data.get("spine_blocking"),
        "revision_instructions": list(data.get("revision_instructions") or []),
    }


def run_brief_ratchet(proj_dir, *, threshold: int = 90, max_rounds: int = 3,
                      on_event=None) -> dict:
    """기획 brief 평가·개선 래칫. 90점↑+PASS면 잠금·종료, 미달은 REVISE로 다음 버전.
    최대 max_rounds. 점수 단조증가(하락 버전 폐기). 미PASS면 최고점 채택(비블로킹).
    채택본을 editorial_brief.json으로 잠금. 반환 {brief, score, verdict, rounds, history}."""
    proj_dir = Path(proj_dir)
    max_rounds = max(1, int(max_rounds))   # 최소 1라운드(0이면 best=None 크래시 방지)
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
            return {"error": "브리프 생성 실패", "rounds": n - 1, "history": history}
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
