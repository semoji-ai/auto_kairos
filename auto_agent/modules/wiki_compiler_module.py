"""Wiki Compiler Module — 파이프라인 step_1d_wiki_compile 진입점.

step_1_vault_lookup 직후, step_1b 직전에 실행.
프로젝트의 모든 토픽에 대해 wiki/<topic>/{overview,claims,entities,timeline,index}.md 생성.

LLM 합성(synthesis) 실패해도 claims/index는 결정적으로 항상 생성 → 파이프라인 진행.

spec: docs/superpowers/specs/2026-04-28-research-redesign.md (Phase 3)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from auto_agent.research.wiki_compiler import compile_topic


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _progress(msg: str, level: str = "info") -> None:
    print(f"[wiki_compiler] {msg}", flush=True)
    pf = os.environ.get("PROGRESS_FILE")
    if pf:
        try:
            with open(pf, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "agent": "wiki-compiler",
                    "text": msg,
                    "level": level,
                    "phase": "stage_1",
                }, ensure_ascii=False) + "\n")
        except Exception:
            pass


def _list_topics(research_dir: Path) -> list[str]:
    """manifests/<topic>/ 디렉토리 목록 → 토픽 슬러그."""
    manifests_dir = research_dir / "manifests"
    if not manifests_dir.exists():
        return []
    try:
        return sorted([d.name for d in manifests_dir.iterdir() if d.is_dir()])
    except Exception:
        return []


def main() -> int:
    project_dir = Path(os.environ.get("PROJECT_DIR", "")).resolve()
    if not project_dir or not project_dir.exists():
        _progress("PROJECT_DIR 환경변수가 없거나 존재하지 않음", level="error")
        return 1

    research_dir = project_dir / "research"
    research_dir.mkdir(parents=True, exist_ok=True)

    topics = _list_topics(research_dir)
    if not topics:
        _progress("토픽 없음 (manifests 비어있음) — wiki 컴파일 스킵", level="warning")
        _write_summary(research_dir, {
            "completed_at": _now_iso(),
            "topics": [],
            "total_files_written": 0,
            "skipped": True,
            "skip_reason": "no topics",
        })
        return 0  # non-blocking

    _progress(f"wiki 컴파일 시작 — 토픽 {len(topics)}개")

    # SKIP_WIKI_SYNTHESIS=1 환경변수로 LLM 합성 건너뛰기 (빠른 검증용)
    skip_synth = os.environ.get("SKIP_WIKI_SYNTHESIS", "").strip() == "1"
    if skip_synth:
        _progress("SKIP_WIKI_SYNTHESIS=1 — LLM 합성 건너뜀, claims/index만 생성")

    results: list[dict] = []
    total_written = 0
    for slug in topics:
        try:
            r = compile_topic(slug, research_dir, skip_synthesis=skip_synth)
        except Exception as exc:
            _progress(f"토픽 '{slug}' 컴파일 실패: {exc}", level="error")
            results.append({"topic_slug": slug, "error": str(exc)})
            continue
        results.append(r)
        total_written += len(r.get("written", []))
        if r.get("errors"):
            _progress(
                f"토픽 '{slug}' 부분 완료 — written={len(r['written'])}, errors={len(r['errors'])}",
                level="warning",
            )
        else:
            _progress(f"토픽 '{slug}' 완료 — {len(r['written'])}개 파일")

    summary = {
        "completed_at": _now_iso(),
        "topics": results,
        "total_files_written": total_written,
        "synthesis_skipped": skip_synth,
    }
    _write_summary(research_dir, summary)
    _progress(f"완료 — {len(topics)}개 토픽, 총 {total_written}개 파일 작성")
    return 0


def _write_summary(research_dir: Path, summary: dict) -> None:
    out = research_dir / "wiki_compiler_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
