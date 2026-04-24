"""
brief_review_module.py
----------------------
editorial_brief.v{N}.json 래칫 리뷰 모듈.

5개 DNA 레버 기반 채점(100점) + verdict(PASS/REVISE/FAIL) + field_feedback 생성.
brief-reviewer 에이전트 SKILL.md를 참조하는 Claude CLI 호출로 동작하며,
Claude CLI 없거나 실패하면 휴리스틱 기반 폴백 채점을 수행한다.

출력: brief_review_feedback.v{N}.json

사용:
    from auto_agent.modules.brief_review_module import review_brief
    feedback = review_brief(project_dir, version="v1")
    if feedback["verdict"] == "PASS":
        ...
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# DNA 레버 정의 공용 참조
SHARED_DNA_REL = "auto_agent/data/skills/shared/brief-dna.md"

# 판정 임계값
PASS_THRESHOLD = 90
REVISE_THRESHOLD = 75

# 추상 표현 안티패턴 (감점 대상)
ABSTRACT_MARKERS = [
    "수동 입력 필요", "TBD", "확인 필요", "(수동", "(확인",
    "많은 사람이 모르는", "알고 보면", "숨겨진 이야기",
    "어려웠다", "힘들었다", "고민이 많았다",
]


def _find_brief_versions(project_dir: Path) -> list[tuple[str, Path]]:
    """프로젝트 디렉토리에서 editorial_brief.v*.json 목록 반환, 버전 오름차순."""
    project_dir = Path(project_dir)
    versions: list[tuple[int, Path]] = []
    for p in project_dir.glob("editorial_brief.v*.json"):
        m = re.match(r"editorial_brief\.v(\d+)\.json$", p.name)
        if m:
            versions.append((int(m.group(1)), p))
    versions.sort(key=lambda x: x[0])
    return [(f"v{n}", p) for n, p in versions]


def _latest_version(project_dir: Path) -> tuple[str, Path] | None:
    versions = _find_brief_versions(project_dir)
    return versions[-1] if versions else None


def _load_brief(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _detect_antipatterns(brief: dict[str, Any]) -> list[dict[str, str]]:
    """brief 전체에서 추상 플레이스홀더/안티패턴 탐지."""
    detected: list[dict[str, str]] = []

    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
        elif isinstance(obj, str):
            for marker in ABSTRACT_MARKERS:
                if marker in obj:
                    detected.append({"field": path, "marker": marker, "snippet": obj[:80]})
    walk(brief)
    return detected


def _heuristic_score(brief: dict[str, Any]) -> dict[str, Any]:
    """Claude CLI 없을 때 사용하는 휴리스틱 채점. 엄격한 폴백."""
    A = {"narrative_arc": 0, "human_truth": 0, "hidden_truth": 0}
    B = {"must_cover": 0, "evidence_anchors": 0, "hook_separation": 0}
    C = {"3단서사": 0, "이면의진실": 0, "현재연결": 0}

    # [A] 기획 구체성
    arc = brief.get("narrative_arc") or {}
    if isinstance(arc, dict):
        filled = sum(1 for k in ("entry_trend", "deep_knowledge", "present_insight")
                     if isinstance(arc.get(k), str) and len(arc[k]) > 20)
        A["narrative_arc"] = min(15, filled * 5)

    human = brief.get("human_truth") or {}
    if isinstance(human, dict):
        filled = sum(1 for k in ("success", "failure", "inner_conflict")
                     if isinstance(human.get(k), str) and len(human[k]) > 20)
        A["human_truth"] = min(15, filled * 5)

    hidden = brief.get("hidden_truth") or ""
    if isinstance(hidden, str) and len(hidden) > 40:
        # 안티패턴 힌트 감점
        base = 10
        if any(m in hidden for m in ("알고 보면", "숨겨진", "많은 사람이 모르는")):
            base -= 5
        A["hidden_truth"] = max(0, base)

    # [B] 실행 가능성
    must_cover = brief.get("must_cover") or []
    if isinstance(must_cover, list) and must_cover:
        concrete = sum(1 for m in must_cover
                       if isinstance(m, str) and (
                           re.search(r"\d{4}", m) or "년" in m or len(m) > 30
                       ))
        B["must_cover"] = min(10, round((concrete / max(1, len(must_cover))) * 10))

    anchors = brief.get("evidence_anchors") or []
    if isinstance(anchors, list) and anchors:
        available = sum(1 for a in anchors
                        if isinstance(a, dict) and a.get("status") == "available")
        ratio = available / max(1, len(anchors))
        B["evidence_anchors"] = min(10, round(ratio * 10))

    hook = brief.get("hook_angle") or ""
    real = brief.get("real_topic") or ""
    if hook and real and hook != real:
        overlap = sum(1 for w in real.split() if len(w) > 1 and w in hook)
        if overlap < max(1, len(real.split()) // 2):
            B["hook_separation"] = 10
        else:
            B["hook_separation"] = 5

    # [C] 세모지 DNA 부합도
    if A["narrative_arc"] >= 10:
        C["3단서사"] = 10
    elif A["narrative_arc"] >= 5:
        C["3단서사"] = 5

    if A["hidden_truth"] >= 8:
        C["이면의진실"] = 10
    elif A["hidden_truth"] >= 4:
        C["이면의진실"] = 5

    pc = brief.get("present_connection") or ""
    if isinstance(pc, str) and len(pc) > 30:
        C["현재연결"] = 10 if re.search(r"\d{4}|오늘|현재|지금", pc) else 7

    a_total = sum(A.values())
    b_total = sum(B.values())
    c_total = sum(C.values())
    total = a_total + b_total + c_total

    # 안티패턴 감점 (최대 -15)
    anti = _detect_antipatterns(brief)
    penalty = min(15, len(anti) * 3)
    total = max(0, total - penalty)

    # verdict 판정
    if total >= PASS_THRESHOLD:
        verdict = "PASS"
    elif total >= REVISE_THRESHOLD:
        verdict = "REVISE"
    else:
        verdict = "FAIL"

    # 필드 피드백 자동 생성
    field_feedback: dict[str, Any] = {}
    if A["narrative_arc"] < 12:
        field_feedback["narrative_arc"] = {
            "score": A["narrative_arc"], "max": 15,
            "issue": "3단 서사(entry_trend/deep_knowledge/present_insight) 중 일부가 비거나 추상적",
            "suggestion": "각 단계를 검증 가능한 사실/사건 단위로 구체화",
            "action": "fill_concrete",
        }
    if A["human_truth"] < 12:
        field_feedback["human_truth"] = {
            "score": A["human_truth"], "max": 15,
            "issue": "성공/실패/내면갈등 3요소 중 일부 부족",
            "suggestion": "failure는 시점·사건·원인 단위, inner_conflict는 회고록 인용 힌트 추가",
            "action": "deepen_episode",
        }
    if A["hidden_truth"] < 8:
        field_feedback["hidden_truth"] = {
            "score": A["hidden_truth"], "max": 10,
            "issue": "반전이 약하거나 추상적 — 기존 인식 → 반전 내용 → 검증 가능성 3요건 미달",
            "suggestion": "시청자가 이미 알고 있는 '공식 기록'을 명시하고 그것과 다른 구체적 사실 제시",
            "action": "sharpen_reversal",
        }
    if B["must_cover"] < 8:
        field_feedback["must_cover"] = {
            "score": B["must_cover"], "max": 10,
            "issue": "막연한 키워드 다수 — 연도/수치/사건명이 부족",
            "suggestion": "각 항목을 'YYYY년 X사건' 형식으로 구체화",
            "action": "concretize_items",
        }
    if B["evidence_anchors"] < 8:
        field_feedback["evidence_anchors"] = {
            "score": B["evidence_anchors"], "max": 10,
            "issue": "needs_research 비율이 높거나 앵커 부재",
            "suggestion": "핵심 주장(hidden_truth, present_connection)에 대한 출처를 우선 확보",
            "action": "add_sources",
        }
    if C["현재연결"] < 8:
        field_feedback["present_connection"] = {
            "score": C["현재연결"], "max": 10,
            "issue": "과거→현재 연결이 추상적 또는 부재",
            "suggestion": "'~이 오늘날 ~로 이어진다' 형태로 구체 인과 서술",
            "action": "add_link",
        }

    return {
        "score_total": total,
        "score_breakdown": {
            "A_기획구체성": {"total": a_total, "max": 40, **A},
            "B_실행가능성": {"total": b_total, "max": 30, **B},
            "C_세모지DNA": {"total": c_total, "max": 30, **C},
        },
        "verdict": verdict,
        "antipatterns_detected": anti,
        "antipattern_penalty": penalty,
        "field_feedback": field_feedback,
        "scorer": "heuristic",
    }


def _llm_score(
    brief: dict[str, Any],
    version: str,
    project_dir: Path,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Claude CLI로 엄격한 LLM 채점 시도. 실패 시 None 반환 (폴백 트리거)."""
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    try:
        subprocess.run([claude_bin, "--version"], capture_output=True, timeout=5, check=True)
    except Exception:
        return None

    dna_md = Path(__file__).parent.parent / "data" / "skills" / "shared" / "brief-dna.md"
    skill_md = (Path(__file__).parent.parent / "data" / "skills"
                / "agents" / "brief-reviewer" / "SKILL.md")

    dna_text = dna_md.read_text(encoding="utf-8") if dna_md.exists() else ""
    skill_text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""

    brief_text = json.dumps(brief, ensure_ascii=False, indent=2)
    prev_block = ""
    if previous:
        prev_block = f"\n<previous_score>\n{previous.get('score_total', 0)}점 (직전 라운드)\n</previous_score>"

    prompt = f"""당신은 brief-reviewer 에이전트입니다. 아래 SKILL.md와 DNA 레버 정의를 읽고,
editorial_brief.{version}.json을 **엄격히 채점**하세요.

<skill>
{skill_text}
</skill>

<brief_dna>
{dna_text}
</brief_dna>
{prev_block}

<brief_to_review version="{version}">
{brief_text}
</brief_to_review>

## 요구사항

1. 루브릭 100점(40+30+30)으로 **엄격히 채점**. 추상 표현/플레이스홀더는 감점.
2. 점수 단조 증가 원칙 — previous_score보다 낮으면 `next_action: revert_to_previous`
3. JSON만 반환 (설명 없이):

{{
  "score_total": 87,
  "score_breakdown": {{
    "A_기획구체성": {{"total": N, "max": 40, "narrative_arc": N, "human_truth": N, "hidden_truth": N}},
    "B_실행가능성": {{"total": N, "max": 30, "must_cover": N, "evidence_anchors": N, "hook_separation": N}},
    "C_세모지DNA": {{"total": N, "max": 30, "3단서사": N, "이면의진실": N, "현재연결": N}}
  }},
  "verdict": "PASS|REVISE|FAIL",
  "antipatterns_detected": [...],
  "field_feedback": {{...}},
  "revision_instructions": [...]
}}
"""
    try:
        result = subprocess.run(
            [claude_bin, "-p", "--output-format", "text"],
            input=prompt, capture_output=True, text=True,
            timeout=180, encoding="utf-8",
        )
        if result.returncode != 0:
            return None
        raw = result.stdout.strip()
        # JSON 블록 추출
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        parsed = json.loads(m.group(0))
        parsed["scorer"] = "llm"
        return parsed
    except Exception as e:
        print(f"[brief_review] LLM 채점 실패: {e}", flush=True)
        return None


def review_brief(
    project_dir: Path | str,
    version: str | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """editorial_brief.v{N}.json을 평가해 brief_review_feedback.v{N}.json 저장.

    Parameters
    ----------
    project_dir : 프로젝트 output_dir
    version     : 리뷰할 버전 (예: "v1"). None이면 최신
    use_llm     : True면 Claude CLI 시도 후 실패 시 휴리스틱 폴백

    Returns
    -------
    feedback dict (verdict, score_total, field_feedback 등)
    """
    project_dir = Path(project_dir)
    if version is None:
        latest = _latest_version(project_dir)
        if latest is None:
            raise FileNotFoundError(
                f"editorial_brief.v*.json 을 찾을 수 없음: {project_dir}"
            )
        version, brief_path = latest
    else:
        brief_path = project_dir / f"editorial_brief.{version}.json"
        if not brief_path.exists():
            raise FileNotFoundError(f"{brief_path} 없음")

    brief = _load_brief(brief_path)

    # 직전 리뷰 로드 (점수 단조 증가 감시)
    previous: dict[str, Any] | None = None
    prev_num = int(version.lstrip("v")) - 1
    if prev_num >= 1:
        prev_review = project_dir / f"brief_review_feedback.v{prev_num}.json"
        if prev_review.exists():
            try:
                previous = json.loads(prev_review.read_text(encoding="utf-8"))
            except Exception:
                previous = None

    # 채점: LLM 시도 → 실패 시 휴리스틱
    score = None
    if use_llm:
        score = _llm_score(brief, version, project_dir, previous)
    if score is None:
        score = _heuristic_score(brief)

    # 점수 단조 증가 체크
    prev_score = previous.get("score_total", 0) if previous else 0
    score["previous_score"] = prev_score
    score["score_delta"] = score.get("score_total", 0) - prev_score
    if prev_score and score.get("score_total", 0) < prev_score:
        score["next_action"] = "revert_to_previous"
        # 강제 verdict 변경
        score["verdict"] = "REVISE"
        score.setdefault("revision_instructions", []).insert(
            0, f"⚠️ 점수 하락({prev_score}→{score['score_total']}) — v{prev_num} 복원 권장"
        )
    else:
        verdict = score.get("verdict", "REVISE")
        if verdict == "PASS":
            score["next_action"] = "lock_version"
        elif verdict == "REVISE":
            score["next_action"] = "rewrite_brief"
        else:
            score["next_action"] = "full_restart"

    # 라운드 번호 계산
    feedback_path = project_dir / f"brief_review_feedback.{version}.json"
    round_num = 1
    if feedback_path.exists():
        try:
            existing = json.loads(feedback_path.read_text(encoding="utf-8"))
            round_num = existing.get("round", 1) + 1
        except Exception:
            pass

    score["version"] = version
    score["round"] = round_num
    score["reviewed_at"] = datetime.now().isoformat(timespec="seconds")

    feedback_path.write_text(
        json.dumps(score, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[brief_review] {version} 채점 완료 → {score.get('score_total')}점 "
          f"({score.get('verdict')}, scorer={score.get('scorer')})", flush=True)
    return score


def main():
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    version = os.environ.get("BRIEF_VERSION") or None
    use_llm = os.environ.get("BRIEF_REVIEW_USE_LLM", "1") == "1"

    try:
        feedback = review_brief(project_dir, version=version, use_llm=use_llm)
    except FileNotFoundError as e:
        print(f"[brief_review] {e}", flush=True)
        sys.exit(1)

    print(f"  score: {feedback.get('score_total')}/100", flush=True)
    print(f"  verdict: {feedback.get('verdict')}", flush=True)
    print(f"  next_action: {feedback.get('next_action')}", flush=True)
    sys.exit(0 if feedback.get("verdict") == "PASS" else 2)


if __name__ == "__main__":
    main()
