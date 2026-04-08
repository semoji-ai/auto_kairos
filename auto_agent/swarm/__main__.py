"""auto_agent.swarm CLI 진입점.

사용:
    python -m auto_agent.swarm \
      --topic "배의 역사" \
      --duration 1 \
      --writing-style iromism \
      --workspace-dir /path/to/workspace \
      --output-dir /path/to/output

또는 runner.py에서 직접 호출:
    from auto_agent.swarm.orchestrator import run_swarm
    asyncio.run(run_swarm(...))
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .orchestrator import run_swarm


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto Kairos Swarm Manuscript Pipeline",
    )
    parser.add_argument("--topic", required=True, help="영상 주제")
    parser.add_argument("--duration", type=int, default=1, help="영상 분량 (분)")
    parser.add_argument("--writing-style", default="iromism", help="문체 (iromism/semoji)")
    parser.add_argument("--workspace-dir", required=True, help="swarm workspace 디렉토리")
    parser.add_argument("--output-dir", required=True, help="최종 산출물 디렉토리")
    parser.add_argument("--n-researchers", type=int, default=5, help="병렬 researcher 수")
    parser.add_argument("--timeout", type=int, default=1800, help="Phase 2 timeout (초)")
    parser.add_argument("--creative-brief-file", default="", help="creative brief 파일 경로 (선택)")
    parser.add_argument("--reference-file", default="", help="참조 원고 파일 경로 (선택)")
    parser.add_argument("--skeleton-model", default="claude-opus-4-6")
    # 2026-04-08: sonnet overloaded → opus
    parser.add_argument("--researcher-model", default="claude-opus-4-6")
    parser.add_argument("--writer-model", default="claude-opus-4-6")
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="기존 파이프라인 산출물(final_manuscript.md, outline.json, research_report.json)을 "
             "덮어쓰지 않고 swarm_* prefix로 저장. dashboard 통합 시 레거시 프로젝트 보호용.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    creative_brief = ""
    if args.creative_brief_file:
        cb_path = Path(args.creative_brief_file)
        if cb_path.exists():
            creative_brief = cb_path.read_text(encoding="utf-8")

    reference_examples = ""
    if args.reference_file:
        ref_path = Path(args.reference_file)
        if ref_path.exists():
            reference_examples = ref_path.read_text(encoding="utf-8")

    result = asyncio.run(run_swarm(
        workspace_dir=Path(args.workspace_dir),
        output_dir=Path(args.output_dir),
        topic=args.topic,
        duration_min=args.duration,
        writing_style=args.writing_style,
        creative_brief=creative_brief,
        reference_examples=reference_examples,
        n_researchers=args.n_researchers,
        timeout_sec=args.timeout,
        skeleton_model=args.skeleton_model,
        researcher_model=args.researcher_model,
        writer_model=args.writer_model,
        safe_mode=args.safe_mode,
    ))

    print(f"\n[Swarm Result] status={result.get('status')}, phase={result.get('phase')}")
    summary = result.get("summary", {})
    if summary:
        for k, v in summary.items():
            if k == "outputs":
                print(f"  {k}: {len(v)} files")
            else:
                print(f"  {k}: {v}")

    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
