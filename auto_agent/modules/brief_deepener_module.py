"""
brief_deepener_module.py
------------------------
editorial_brief.v{N-1}.json → editorial_brief.v{N}.json 심화 모듈.

Stage 1 후 (v1→v2): skeleton + outline + chapter_facts/ 반영
Stage 2_target 후 (v2→v3): draft.md + targeted_claims.json 반영

핵심 원칙:
- 잠금 필드(core_question/real_topic/hook_angle/excluded_angles/tone_goal) 변경 금지
- narrative_arc/human_truth/hidden_truth/present_connection/evidence_anchors 구체화
- 점수 단조 증가: v{N}은 반드시 v{N-1}과 같거나 높은 리뷰 점수

사용:
    from auto_agent.modules.brief_deepener_module import deepen_brief
    new_path = deepen_brief(project_dir, to_version="v2")
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

LOCKED_FIELDS = (
    "core_question", "real_topic", "hook_angle",
    "excluded_angles", "tone_goal", "entity_slug", "section_slug",
)


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_chapter_facts(project_dir: Path) -> list[dict[str, Any]]:
    """chapter_facts/ 디렉토리에서 모든 챕터 facts 로드."""
    facts_dir = project_dir / "chapter_facts"
    if not facts_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(facts_dir.glob("chapter_*.json")):
        data = _load_json(p)
        if data:
            data["_file"] = p.name
            out.append(data)
    return out


def _find_version(project_dir: Path, version: str) -> Path | None:
    p = project_dir / f"editorial_brief.{version}.json"
    if p.exists():
        return p
    # fallback: legacy editorial_brief.json as v1
    if version == "v1":
        legacy = project_dir / "editorial_brief.json"
        if legacy.exists():
            return legacy
    return None


def _llm_deepen(
    prev_brief: dict[str, Any],
    context_blocks: list[tuple[str, str]],
    from_version: str,
    to_version: str,
) -> dict[str, Any] | None:
    """Claude CLI로 심화된 brief 생성. 실패 시 None."""
    claude_bin = os.environ.get("CLAUDE_CLI_BIN", "claude")
    try:
        subprocess.run([claude_bin, "--version"], capture_output=True, timeout=5, check=True)
    except Exception:
        return None

    skill_md = (Path(__file__).parent.parent / "data" / "skills"
                / "agents" / "brief-deepener" / "SKILL.md")
    dna_md = (Path(__file__).parent.parent / "data" / "skills"
              / "shared" / "brief-dna.md")

    skill_text = skill_md.read_text(encoding="utf-8") if skill_md.exists() else ""
    dna_text = dna_md.read_text(encoding="utf-8") if dna_md.exists() else ""

    ctx_text = "\n\n".join(f"<{tag}>\n{body}\n</{tag}>" for tag, body in context_blocks)

    prompt = f"""당신은 brief-deepener 에이전트입니다. 아래 SKILL.md와 DNA 레버 정의를 읽고,
editorial_brief.{from_version}.json을 리서치 결과로 심화하여 editorial_brief.{to_version}.json을 생성하세요.

<skill>
{skill_text}
</skill>

<brief_dna>
{dna_text}
</brief_dna>

<prev_brief version="{from_version}">
{json.dumps(prev_brief, ensure_ascii=False, indent=2)}
</prev_brief>

{ctx_text}

## 요구사항

1. **잠금 필드는 그대로 유지**: core_question, real_topic, hook_angle, excluded_angles, tone_goal, entity_slug, section_slug
2. 나머지 필드는 위 리서치 컨텍스트 기반으로 **구체성 증가** 방향으로 수정
3. evidence_anchors의 needs_research 항목을 리서치에서 확인되면 available로 승격
4. JSON만 반환 (설명 없이):

{{
  "core_question": "...",   // 잠금 필드 그대로
  "real_topic": "...",      // 잠금 필드 그대로
  ...
  "narrative_arc": {{...}}, // 심화
  "human_truth": {{...}},   // 심화
  ...
}}
"""
    try:
        result = subprocess.run(
            [claude_bin, "-p", "--output-format", "text"],
            input=prompt, capture_output=True, text=True,
            timeout=300, encoding="utf-8",
        )
        if result.returncode != 0:
            print(f"[brief_deepener] Claude CLI 실패: {result.stderr[:200]}", flush=True)
            return None
        raw = result.stdout.strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        return json.loads(m.group(0))
    except Exception as e:
        print(f"[brief_deepener] LLM 호출 실패: {e}", flush=True)
        return None


def _heuristic_deepen(
    prev_brief: dict[str, Any],
    context_blocks: list[tuple[str, str]],
) -> dict[str, Any]:
    """LLM 실패 시 폴백: 잠금 필드 유지 + evidence_anchors 상태만 기계적 승격.

    주: 실질적 심화는 LLM 없이는 불가능. 이 폴백은 파이프라인 중단 방지용.
    """
    new_brief = dict(prev_brief)

    # evidence_anchors: 리서치 컨텍스트에 앵커의 claim 키워드가 나타나면 available 승격
    ctx_all = "\n".join(body for _, body in context_blocks)
    anchors = new_brief.get("evidence_anchors") or []
    new_anchors: list[dict[str, Any]] = []
    for a in anchors:
        if not isinstance(a, dict):
            new_anchors.append(a)
            continue
        claim = a.get("claim", "")
        status = a.get("status", "needs_research")
        if status == "needs_research" and claim:
            # 키워드 3개 이상 컨텍스트에 나타나면 승격
            keywords = [w for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", claim)
                        if len(w) > 1]
            hits = sum(1 for kw in keywords if kw in ctx_all)
            if hits >= max(2, len(keywords) // 3):
                a = dict(a)
                a["status"] = "available"
                a["source"] = a.get("source") or "(auto-matched from research context)"
        new_anchors.append(a)
    if new_anchors:
        new_brief["evidence_anchors"] = new_anchors

    return new_brief


def deepen_brief(
    project_dir: Path | str,
    to_version: str,
    use_llm: bool = True,
) -> Path:
    """editorial_brief.v{N-1}.json → editorial_brief.v{N}.json 심화.

    Parameters
    ----------
    project_dir : 프로젝트 output_dir
    to_version  : 목표 버전 ("v2" 또는 "v3")
    use_llm     : LLM 시도 후 실패 시 휴리스틱 폴백

    Returns
    -------
    저장된 editorial_brief.v{N}.json 경로
    """
    project_dir = Path(project_dir)
    to_num = int(to_version.lstrip("v"))
    if to_num < 2:
        raise ValueError(f"to_version must be v2 or higher, got {to_version}")
    from_version = f"v{to_num - 1}"

    prev_path = _find_version(project_dir, from_version)
    if prev_path is None:
        raise FileNotFoundError(f"이전 버전 없음: {from_version}")
    prev_brief = _load_json(prev_path) or {}

    # 컨텍스트 수집
    context_blocks: list[tuple[str, str]] = []
    if to_version == "v2":
        skel = _load_json(project_dir / "skeleton.json")
        if skel:
            context_blocks.append(("skeleton", json.dumps(skel, ensure_ascii=False)[:4000]))
        outl = _load_json(project_dir / "outline.json")
        if outl:
            context_blocks.append(("outline", json.dumps(outl, ensure_ascii=False)[:4000]))
        for ch in _read_chapter_facts(project_dir):
            context_blocks.append((
                f"chapter_facts_{ch.get('_file', 'unknown')}",
                json.dumps(ch, ensure_ascii=False)[:3000],
            ))
    elif to_version == "v3":
        draft_path = project_dir / "draft.md"
        if draft_path.exists():
            context_blocks.append(("draft_md", draft_path.read_text(encoding="utf-8")[:8000]))
        claims = _load_json(project_dir / "targeted_claims.json")
        if claims:
            context_blocks.append(("targeted_claims",
                                   json.dumps(claims, ensure_ascii=False)[:6000]))
    else:
        # v4+ 대비
        manuscript = project_dir / "final_manuscript.md"
        if manuscript.exists():
            context_blocks.append(("final_manuscript",
                                   manuscript.read_text(encoding="utf-8")[:8000]))

    # 심화 시도
    new_brief = None
    if use_llm:
        new_brief = _llm_deepen(prev_brief, context_blocks, from_version, to_version)
    if new_brief is None:
        print("[brief_deepener] LLM 사용 불가 — 휴리스틱 폴백", flush=True)
        new_brief = _heuristic_deepen(prev_brief, context_blocks)

    # 잠금 필드 강제 보존 (LLM이 실수로 수정해도 원복)
    for lf in LOCKED_FIELDS:
        if lf in prev_brief:
            new_brief[lf] = prev_brief[lf]

    # 메타데이터
    new_brief["_version"] = to_version
    new_brief["_deepened_from"] = from_version
    new_brief["_deepened_at"] = datetime.now().isoformat(timespec="seconds")

    # 변경 로그 작성
    changes: list[dict[str, Any]] = []
    for k in new_brief:
        if k.startswith("_") or k in LOCKED_FIELDS:
            continue
        if k not in prev_brief:
            changes.append({"field": k, "action": "added"})
        elif json.dumps(prev_brief[k], ensure_ascii=False, sort_keys=True) != \
             json.dumps(new_brief[k], ensure_ascii=False, sort_keys=True):
            changes.append({"field": k, "action": "modified"})

    log = {
        "from_version": from_version,
        "to_version": to_version,
        "deepened_at": new_brief["_deepened_at"],
        "retained_fields": list(LOCKED_FIELDS),
        "changes": changes,
        "context_used": [tag for tag, _ in context_blocks],
    }
    log_path = project_dir / f"brief_deepen_log.{to_version}.json"
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")

    # 저장
    out_path = project_dir / f"editorial_brief.{to_version}.json"
    out_path.write_text(json.dumps(new_brief, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[brief_deepener] {from_version} → {to_version} 심화 완료 → {out_path.name}",
          flush=True)
    print(f"  변경 필드 {len(changes)}개: "
          f"{[c['field'] for c in changes[:5]]}", flush=True)
    return out_path


def deepen_and_review(
    project_dir: Path | str,
    to_version: str,
    use_llm: bool = True,
    auto_revert: bool = True,
) -> dict[str, Any]:
    """심화 → 리뷰 → 점수 하락 시 이전 버전 복원 (atomic operation).

    Returns
    -------
    리뷰 feedback dict (score_total, verdict, reverted 포함)
    """
    from auto_agent.modules.brief_review_module import review_brief  # lazy import

    project_dir = Path(project_dir)
    deepen_brief(project_dir, to_version=to_version, use_llm=use_llm)

    try:
        feedback = review_brief(project_dir, version=to_version, use_llm=use_llm)
    except Exception as e:
        print(f"[deepen_and_review] 리뷰 실패: {e}", flush=True)
        return {"verdict": "FAIL", "reverted": False, "error": str(e)}

    feedback["reverted"] = False
    if auto_revert and feedback.get("next_action") == "revert_to_previous":
        # v{N}을 이전 버전으로 복원 (삭제 대신 이전 내용으로 덮어쓰기)
        to_num = int(to_version.lstrip("v"))
        prev_version = f"v{to_num - 1}"
        prev_path = project_dir / f"editorial_brief.{prev_version}.json"
        curr_path = project_dir / f"editorial_brief.{to_version}.json"
        if prev_path.exists() and curr_path.exists():
            prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
            prev_data["_version"] = to_version  # 버전 태그는 유지
            prev_data["_reverted_from_failed_deepen"] = True
            curr_path.write_text(
                json.dumps(prev_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            feedback["reverted"] = True
            print(f"[deepen_and_review] ⚠️ 점수 하락 감지 — {to_version}을 "
                  f"{prev_version} 내용으로 복원", flush=True)

    return feedback


def main():
    project_dir = Path(os.environ.get("PROJECT_DIR", "."))
    to_version = os.environ.get("TO_VERSION", "v2")
    use_llm = os.environ.get("BRIEF_DEEPEN_USE_LLM", "1") == "1"
    auto_revert = os.environ.get("BRIEF_DEEPEN_AUTO_REVERT", "1") == "1"

    # to_version이 명시되지 않았으면 기존 버전 + 1 자동 결정
    if to_version in ("", "auto"):
        existing = sorted(project_dir.glob("editorial_brief.v*.json"))
        if not existing:
            print("[brief_deepener] 이전 버전 없음 — 스킵 (editorial_brief.v1.json 필요)",
                  flush=True)
            sys.exit(0)
        last = existing[-1].stem.split(".")[-1]
        try:
            num = int(last.lstrip("v"))
        except ValueError:
            num = 1
        to_version = f"v{num + 1}"

    print(f"[brief_deepener] 목표 버전: {to_version}", flush=True)

    try:
        feedback = deepen_and_review(
            project_dir, to_version=to_version,
            use_llm=use_llm, auto_revert=auto_revert,
        )
    except Exception as e:
        print(f"[brief_deepener] 실패: {e}", flush=True)
        sys.exit(1)

    print(f"  score: {feedback.get('score_total', 0)}/100", flush=True)
    print(f"  verdict: {feedback.get('verdict', '?')}", flush=True)
    if feedback.get("reverted"):
        print(f"  ⚠️ 점수 하락 — 이전 버전 복원됨", flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
