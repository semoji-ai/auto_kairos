"""CompilerAgent — swarm Phase 3 (sequential finalization).

swarm의 모든 산출물을 기존 파이프라인 형식으로 변환:
- workspace/manuscript.md → output/<slug>/final_manuscript.md
- workspace/claims.jsonl + findings.jsonl → output/<slug>/research_report.json
- workspace/outline.json → output/<slug>/outline.json (그대로 복사)
- workspace/episodes.jsonl → output/<slug>/episodes.json (보존)
- workspace 전체 → output/<slug>/swarm/ (audit/디버깅용)

이 agent는 LLM 호출 없음 — 순수 Python 변환.
swarm orchestrator가 done condition 충족 후 마지막에 실행.
"""
from __future__ import annotations

import json
import logging
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from ..workspace import SwarmWorkspace

logger = logging.getLogger(__name__)


# manuscript.md의 [claim:cXXX] / [char:id] 태그 추출용 정규식
# claim id는 R1_c001 같이 instance prefix가 있고, 여러 id가 콤마로 묶일 수 있음
# 예: [claim:R1_c001], [claim:R3_c001,R3_c003], [char:pemberton]
CLAIM_TAG_RE = re.compile(r'\[claim:([^\]]+)\]')
CHAR_TAG_RE = re.compile(r'\[char:([^\]]+)\]')


def strip_claim_tags(text: str) -> str:
    """manuscript.md에서 [claim:cXXX] + [char:id] 태그 제거 → 깨끗한 prose."""
    cleaned = CLAIM_TAG_RE.sub('', text)
    cleaned = CHAR_TAG_RE.sub('', cleaned)
    # 연속 공백 정리 (여러 변형)
    cleaned = re.sub(r'  +', ' ', cleaned)  # 다중 공백 → 1
    cleaned = re.sub(r' \.', '.', cleaned)  # 마침표 앞 공백
    cleaned = re.sub(r' ,', ',', cleaned)
    return cleaned


def extract_used_claims(text: str) -> List[str]:
    """manuscript에서 사용된 claim_id 목록 추출.

    [claim:R1_c001,R1_c002] 같이 콤마로 묶인 id들도 분리해서 모두 반환.
    """
    used: List[str] = []
    for tag_content in CLAIM_TAG_RE.findall(text):
        for cid in tag_content.split(','):
            cid = cid.strip()
            if cid:
                used.append(cid)
    return list(set(used))


def extract_used_characters(text: str) -> List[str]:
    """manuscript에서 사용된 char_id 목록 추출."""
    used: List[str] = []
    for tag_content in CHAR_TAG_RE.findall(text):
        for cid in tag_content.split(','):
            cid = cid.strip()
            if cid:
                used.append(cid)
    return list(set(used))


def compile_swarm(
    workspace: SwarmWorkspace,
    output_dir: Path,
    *,
    safe_mode: bool = False,
) -> Dict[str, Any]:
    """swarm 결과를 기존 파이프라인 호환 형식으로 변환.

    Args:
      workspace: swarm workspace
      output_dir: 산출물 디렉토리
      safe_mode: True면 기존 파이프라인 파일(final_manuscript.md, outline.json,
                 research_report.json)을 덮어쓰지 않고 swarm_* prefix로 저장.
                 dashboard에서 manuscript 탭 통합 시 레거시 프로젝트 보호용.
                 False (기본)면 기존 위치에 직접 저장 (CLI/standalone 사용).

    Returns: 변환 결과 summary (counts + status)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # safe_mode 파일명 결정
    manuscript_filename = "swarm_final_manuscript.md" if safe_mode else "final_manuscript.md"
    outline_filename = "swarm_outline.json" if safe_mode else "outline.json"
    report_filename = "swarm_research_report.json" if safe_mode else "research_report.json"

    workspace.emit_event("compiler", "started")

    summary: Dict[str, Any] = {
        "manuscript_chars": 0,
        "manuscript_clean_chars": 0,
        "claims_total": 0,
        "claims_used": 0,
        "characters_total": 0,
        "characters_used": 0,
        "findings_count": 0,
        "episodes_count": 0,
        "queries_count": 0,
        "outputs": [],
    }

    # 1. final_manuscript.md (claim + char 태그 제거 버전)
    manuscript_raw = workspace.read_text("manuscript.md")
    if manuscript_raw:
        manuscript_clean = strip_claim_tags(manuscript_raw)
        used_claims = extract_used_claims(manuscript_raw)
        used_characters = extract_used_characters(manuscript_raw)
        target_path = output_dir / manuscript_filename
        target_path.write_text(manuscript_clean, encoding="utf-8")
        summary["manuscript_chars"] = len(manuscript_raw)
        summary["manuscript_clean_chars"] = len(manuscript_clean)
        summary["claims_used"] = len(used_claims)
        summary["characters_used"] = len(used_characters)
        summary["outputs"].append(str(target_path))
        # 원본도 보존
        (output_dir / "swarm_manuscript_with_tags.md").write_text(manuscript_raw, encoding="utf-8")

    # 2. outline.json — workspace에서 그대로 복사
    outline = workspace.read_json("outline.json")
    if outline:
        target_path = output_dir / outline_filename
        target_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["outputs"].append(str(target_path))

    # 3. claims.jsonl → claims.json (정리된 dict)
    claims = workspace.all_jsonl("claims.jsonl")
    summary["claims_total"] = len(claims)
    if claims:
        claims_dict = {c.get("id", f"c{i:03d}"): c for i, c in enumerate(claims)}
        (output_dir / "swarm_claims.json").write_text(
            json.dumps({"claims": claims_dict, "total": len(claims)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 4. findings.jsonl → 전체 dump
    findings = workspace.all_jsonl("findings.jsonl")
    summary["findings_count"] = len(findings)
    if findings:
        (output_dir / "swarm_findings.json").write_text(
            json.dumps({"findings": findings, "total": len(findings)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 5. episodes.jsonl → 전체 dump
    episodes = workspace.all_jsonl("episodes.jsonl")
    summary["episodes_count"] = len(episodes)
    if episodes:
        (output_dir / "swarm_episodes.json").write_text(
            json.dumps({"episodes": episodes, "total": len(episodes)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 5b. character_register.json — 그대로 복사 + 사용 횟수 카운트
    register = workspace.read_json("character_register.json", default={"characters": []})
    characters = register.get("characters", []) if isinstance(register, dict) else []
    summary["characters_total"] = len(characters)
    if characters:
        # manuscript에서 각 char_id 등장 횟수
        char_counts: Dict[str, int] = {}
        if manuscript_raw:
            for tag_content in CHAR_TAG_RE.findall(manuscript_raw):
                for cid in tag_content.split(','):
                    cid = cid.strip()
                    if cid:
                        char_counts[cid] = char_counts.get(cid, 0) + 1
        # register에 mention_count 주입
        for c in characters:
            cid = c.get("id", "")
            c["mention_count"] = char_counts.get(cid, 0)

        (output_dir / "swarm_character_register.json").write_text(
            json.dumps({"characters": characters, "total": len(characters)},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # 6. research_report.json — 기존 파이프라인 호환 (script-director chapters 모드가 input으로 사용)
    # claims를 sources/episodes/key_facts 형식으로 변환
    # 새 schema: source_urls (list), legacy: source_url (string) — 둘 다 처리
    def _claim_urls(c):
        urls = c.get("source_urls")
        if isinstance(urls, list) and urls:
            return urls
        legacy = c.get("source_url")
        if legacy:
            return [legacy] if isinstance(legacy, str) else list(legacy)
        return []

    if claims or findings or episodes or characters:
        sources_seen = set()
        sources_list = []
        for c in claims:
            for src_url in _claim_urls(c):
                if src_url and src_url not in sources_seen:
                    sources_seen.add(src_url)
                    sources_list.append({
                        "title": c.get("source_title", c.get("text", "")[:60]),
                        "url": src_url,
                        "grade": "primary" if c.get("confidence") == "high" else "secondary",
                    })

        report = {
            "topic": outline.get("topic", "") if outline else "",
            "summary": outline.get("core_thesis", "") if outline else "",
            "sources": sources_list,
            "key_facts": [
                {
                    "id": c.get("id", ""),
                    "text": c.get("text", ""),
                    "sources": _claim_urls(c),       # 새 schema (list)
                    "source": (_claim_urls(c) or [""])[0],  # legacy 호환 (1번째)
                    "confidence": c.get("confidence", "medium"),
                    "cross_checked": bool(c.get("cross_checked")),
                    "image_candidates": c.get("image_candidates") or [],
                }
                for c in claims
            ],
            "episodes": [
                {
                    "beat": ep.get("beat_id", ""),
                    "scene": ep.get("scene", ""),
                    "characters": ep.get("characters", []),
                    "atmosphere": ep.get("atmosphere", ""),
                }
                for ep in episodes
            ],
            "characters": characters,  # mention_count 포함된 character_register
            "compiled_from": "swarm",
        }
        (output_dir / report_filename).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary["outputs"].append(str(output_dir / report_filename))

    # 7. research_queue 통계
    queries = workspace.all_jsonl("research_queue.jsonl")
    summary["queries_count"] = len(queries)

    # 8. 전체 swarm 디렉토리를 output/<slug>/swarm/에 복사 (audit)
    audit_dir = output_dir / "swarm"
    if audit_dir.exists():
        shutil.rmtree(audit_dir)
    shutil.copytree(workspace.dir, audit_dir)
    summary["outputs"].append(str(audit_dir))

    # 9. meta 업데이트
    meta = workspace.read_json("meta.json", default={})
    meta["status"] = "compiled"
    meta["compiled_at"] = datetime.now(timezone.utc).isoformat()
    meta["summary"] = {k: v for k, v in summary.items() if k != "outputs"}
    workspace.write_json_atomic("meta.json", meta)

    workspace.emit_event(
        "compiler", "completed", level="success",
        manuscript_chars=summary["manuscript_chars"],
        claims_total=summary["claims_total"],
        claims_used=summary["claims_used"],
        characters_total=summary["characters_total"],
        characters_used=summary["characters_used"],
        outputs_count=len(summary["outputs"]),
    )

    return summary
