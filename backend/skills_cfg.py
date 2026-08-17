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


REPO_ROOT = Path(__file__).resolve().parents[1]
# 원고를 쓰거나 다듬는 단계 — 채널 문체·목표 분량을 주입할 대상
WRITING_SKILLS = {"draft-write", "target-research", "finalize-manuscript", "review-refine"}
CHARS_PER_MIN = (250, 300)   # 한국어 나레이션 분당 글자수 밴드


def parse_plan_fields(proj_dir: Path) -> dict:
    """plan.md 의 '키: 값' 헤더 필드(채널/분량/톤)를 dict 로 파싱."""
    fp = proj_dir / "plan.md"
    fields = {}
    if fp.exists():
        for line in fp.read_text(encoding="utf-8").splitlines():
            if ":" in line and not line.startswith("#"):
                k, _, v = line.partition(":")
                if k.strip() and v.strip():
                    fields[k.strip()] = v.strip()
    return fields


def _voice_pack(channel: str) -> str | None:
    """채널명 → data/artstyle/{채널}-voice.md 문체 가이드(없으면 None — 실패 아님)."""
    if not channel:
        return None
    fp = REPO_ROOT / "data" / "artstyle" / f"{channel}-voice.md"
    return fp.read_text(encoding="utf-8") if fp.exists() else None


def _duration_target(duration: str) -> str | None:
    """'5분'/'5' → 목표 글자수 문구. 파싱 실패 시 None."""
    import re
    m = re.search(r"(\d+(?:\.\d+)?)", duration or "")
    if not m:
        return None
    minutes = float(m.group(1))
    lo, hi = (int(minutes * c) for c in CHARS_PER_MIN)
    return (f"목표 분량: {duration} — 나레이션(메타라인 제외) 한국어 {lo:,}~{hi:,}자. "
            f"이 범위를 반드시 지킬 것(분당 {CHARS_PER_MIN[0]}~{CHARS_PER_MIN[1]}자 기준).")


def build_prompt(skills_dir: Path, name: str, config: dict, proj_dir: Path) -> str:
    skill_md = skills_dir / name / "SKILL.md"
    parts = [skill_md.read_text(encoding="utf-8") if skill_md.exists() else f"skill: {name}"]
    for fname in config.get("inputs", []):
        fp = proj_dir / fname
        if fp.exists():
            parts.append(f"\n\n## 입력: {fname}\n{fp.read_text(encoding='utf-8')}")
    if name in WRITING_SKILLS:
        plan = parse_plan_fields(proj_dir)
        pack = _voice_pack(plan.get("채널", ""))
        if pack:
            parts.append(f"\n\n## 문체 가이드(채널: {plan['채널']}) — 반드시 준수\n{pack}")
        dur = _duration_target(plan.get("분량", ""))
        if dur:
            parts.append(f"\n\n## 분량 지시\n{dur}")
    # 사용자가 패널에서 직접 고친 내역 — 오케스트레이터가 인지·존중하도록 주입
    from backend import edits
    recent = edits.recent_edits_text(proj_dir)
    if recent:
        parts.append("\n\n" + recent)
    out = config["output"]
    if config.get("output_kind") == "json":
        parts.append(f"\n\nproject_id={proj_dir.name}. {out} 내용(JSON)만 출력.")
    else:
        parts.append(f"\n\nproject_id={proj_dir.name}. {out} 에 들어갈 본문(마크다운)만 출력.")
    return "".join(parts)
