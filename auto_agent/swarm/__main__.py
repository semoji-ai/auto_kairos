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

logger = logging.getLogger(__name__)


# 옵션 A — swarm + pipeline 자동 통합용 helper들 ────────────────────────

# 프로젝트 자동 생성 시 기본 config (iromism, quirky_cartoon)
DEFAULT_PROJECT_CONFIG = {
    "art_style": "quirky_cartoon",
    "writing_style": "iromism",
    "voice_id": "9Sj8ugvpK1DmcAXyvi3a",
    "voice_settings": {
        "stability": 1.0,
        "similarity_boost": 0.6,
        "style": 0.9,
        "use_speaker_boost": True,
        "speed": 1.1,
    },
}


def _resolve_or_create_project(slug: str, topic: str, duration_min: int, writing_style: str) -> dict:
    """slug로 프로젝트 조회. 없으면 기본 config로 생성. dict 반환."""
    from auto_agent.db.project_manager import ProjectManager
    pm = ProjectManager()
    existing = pm.get_project(slug=slug)
    if existing:
        return existing
    config = dict(DEFAULT_PROJECT_CONFIG)
    config["writing_style"] = writing_style
    config["duration_minutes"] = duration_min
    pm.create_project(
        name=slug,
        slug=slug,
        topic=topic,
        theme="simple",
        config=config,
        channel=config.get("channel", "이로미즘"),
    )
    return pm.get_project(slug=slug)


_SWARM_PROMOTION_MAP = {
    # swarm_* → 정식 파일명. 이미 정식 파일이 있으면 덮어쓰지 않음 (안전).
    "swarm_final_manuscript.md": "final_manuscript.md",
    "swarm_research_report.json": "research_report.json",
    "swarm_outline.json": "outline.json",
    "swarm_claims.json": "claims.json",
    "swarm_character_register.json": "character_register.json",
}


def _promote_swarm_outputs(output_dir: Path) -> list:
    """safe_mode로 만든 swarm_* 파일을 정식 파일명으로 복사 (덮어쓰지 않음).

    이미 정식 파일이 존재하면 skip — 사용자가 수동으로 만든 결과를 보호.
    """
    promoted = []
    for src_name, dst_name in _SWARM_PROMOTION_MAP.items():
        src = output_dir / src_name
        dst = output_dir / dst_name
        if not src.exists():
            continue
        if dst.exists():
            logger.info("promote skip (이미 존재): %s", dst_name)
            continue
        dst.write_bytes(src.read_bytes())
        promoted.append(dst_name)
    return promoted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Auto Kairos Swarm Manuscript Pipeline",
    )
    parser.add_argument("--topic", required=True, help="영상 주제")
    parser.add_argument("--duration", type=int, default=1, help="영상 분량 (분)")
    parser.add_argument("--writing-style", default="iromism", help="문체 (iromism/semoji)")
    parser.add_argument("--workspace-dir", default="", help="swarm workspace 디렉토리 (--project 사용 시 생략 가능)")
    parser.add_argument("--output-dir", default="", help="최종 산출물 디렉토리 (--project 사용 시 생략 가능)")
    parser.add_argument("--n-researchers", type=int, default=5, help="병렬 researcher 수")
    parser.add_argument("--timeout", type=int, default=1800, help="Phase 2 timeout (초)")
    parser.add_argument("--creative-brief-file", default="", help="creative brief 파일 경로 (선택)")
    parser.add_argument("--reference-file", default="", help="참조 원고 파일 경로 (선택)")
    parser.add_argument("--skeleton-model", default="claude-opus-4-6")
    # 2026-04-08 (저녁): sonnet 복귀 확인 → researcher default를 sonnet으로 되돌림.
    # claude_cli sonnet→opus 자동 fallback 가드가 있어서 다시 overload 와도 안전.
    parser.add_argument("--researcher-model", default="claude-sonnet-4-6")
    parser.add_argument("--writer-model", default="claude-opus-4-6")
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="기존 파이프라인 산출물(final_manuscript.md, outline.json, research_report.json)을 "
             "덮어쓰지 않고 swarm_* prefix로 저장. dashboard 통합 시 레거시 프로젝트 보호용.",
    )
    # 옵션 A — 옵션 A 정식 통합 (swarm + project promote + pipeline)
    parser.add_argument(
        "--project",
        default="",
        help="auto-agent 프로젝트 slug. 지정하면 프로젝트 자동 조회/생성 후 "
             "workspace/output을 프로젝트 디렉토리로 강제. swarm 종료 후 swarm_* 산출물을 "
             "정식 파일명으로 자동 promote. (--workspace-dir/--output-dir 무시)",
    )
    parser.add_argument(
        "--pipeline",
        action="store_true",
        help="swarm 성공 후 PipelineRunner를 자동 호출 (--project 필수). "
             "step_2부터 step_3c까지 실행 (mp4 렌더는 별도). promote → script-director → "
             "review → data-mapper → factcheck → assembly-director → upload-info.",
    )
    parser.add_argument(
        "--pipeline-from",
        default="step_2",
        help="--pipeline 사용 시 시작 step (default: step_2)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    # --pipeline 사용 시 --project 필수
    if args.pipeline and not args.project:
        parser.error("--pipeline은 --project SLUG와 함께 사용해야 합니다.")

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

    # ── 옵션 A — --project 사용 시 workspace/output을 프로젝트 디렉토리로 강제 ──
    project = None
    workspace_dir = Path(args.workspace_dir) if args.workspace_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    safe_mode = args.safe_mode

    if args.project:
        project = _resolve_or_create_project(
            slug=args.project,
            topic=args.topic,
            duration_min=args.duration,
            writing_style=args.writing_style,
        )
        project_out = Path(project["output_dir"])
        project_out.mkdir(parents=True, exist_ok=True)
        output_dir = project_out
        workspace_dir = project_out / "swarm_workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        safe_mode = True  # 프로젝트 모드는 항상 safe (swarm_* prefix → 이후 promote)
        print(f"[옵션 A] 프로젝트 모드: slug={project['slug']}, output={output_dir}")

    if not workspace_dir or not output_dir:
        parser.error("--project 또는 --workspace-dir + --output-dir 중 하나는 필수입니다.")

    result = asyncio.run(run_swarm(
        workspace_dir=workspace_dir,
        output_dir=output_dir,
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
        safe_mode=safe_mode,
    ))

    print(f"\n[Swarm Result] status={result.get('status')}, phase={result.get('phase')}")
    summary = result.get("summary", {})
    if summary:
        for k, v in summary.items():
            if k == "outputs":
                print(f"  {k}: {len(v)} files")
            else:
                print(f"  {k}: {v}")

    swarm_ok = result.get("status") == "success"

    # ── 옵션 A — swarm 성공 + --project이면 swarm_* 산출물 promote ──
    if swarm_ok and project is not None:
        promoted = _promote_swarm_outputs(output_dir)
        if promoted:
            print(f"[옵션 A] swarm 산출물 promote: {', '.join(promoted)}")
        else:
            print("[옵션 A] promote 대상 없음 (이미 정식 파일 존재 또는 swarm_* 미생성)")

    # ── 옵션 A — --pipeline이면 PipelineRunner 자동 호출 ──
    if swarm_ok and args.pipeline:
        print(f"\n[옵션 A] PipelineRunner 시작: project={project['slug']}, from={args.pipeline_from}")
        try:
            from auto_agent.orchestrator.runner import PipelineRunner
            runner = PipelineRunner(project["slug"])
            runner.run(from_step=args.pipeline_from)
            print(f"[옵션 A] PipelineRunner 완료 — 다음: 매니페스트 검토 후 수동 렌더링")
        except Exception as e:
            print(f"[옵션 A] PipelineRunner 실패: {type(e).__name__}: {e}")
            return 1

    return 0 if swarm_ok else 1


if __name__ == "__main__":
    sys.exit(main())
