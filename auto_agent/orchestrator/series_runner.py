"""
series_runner.py
----------------
장편 시리즈 전편 Stage 1~2 순차 실행 오케스트레이터.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auto_agent.modules.series_planner_module import (
    episode_to_editorial_brief,
    save_series_plan,
    validate_series_plan,
)


def build_episode_run_order(series_plan: dict[str, Any]) -> list[dict[str, Any]]:
    """에피소드를 episode_number 오름차순으로 정렬하여 반환."""
    return sorted(series_plan["episodes"], key=lambda ep: ep["episode_number"])


def build_episode_project_slug(series_id: str, episode_number: int) -> str:
    """시리즈 + 편번호 → 프로젝트 slug. 예: lg_brand_encyclopedia_ep03"""
    return f"{series_id}_ep{episode_number:02d}"


def run_single_episode(
    project: dict[str, Any],
    stop_after_step: str = "step_2b",
    **kwargs,
) -> dict[str, Any]:
    """단일 에피소드 Runner 실행 (테스트 모킹 진입점)."""
    from auto_agent.orchestrator.runner import PipelineRunner
    runner = PipelineRunner()
    return runner.run(project, stop_after_step=stop_after_step)


def series_run(
    series_plan: dict[str, Any],
    output_base: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    """시리즈 전편을 Stage 2까지 순차 실행."""
    errors = validate_series_plan(series_plan)
    if errors:
        raise ValueError(f"series_plan 검증 실패: {errors}")

    output_base = Path(output_base)
    series_id = series_plan["series_id"]
    episodes_completed = 0
    episodes_failed: list[int] = []

    for episode in build_episode_run_order(series_plan):
        ep_num = episode["episode_number"]
        slug = build_episode_project_slug(series_id, ep_num)
        ep_dir = output_base / slug

        # episode_brief.json 생성
        brief = episode_to_editorial_brief(episode, series_plan)
        ep_dir.mkdir(parents=True, exist_ok=True)
        brief_path = ep_dir / "episode_brief.json"
        brief_path.write_text(
            json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        episode["episode_brief_path"] = str(brief_path)
        episode["project_slug"] = slug

        # editorial_brief_module은 editorial_brief.json이 이미 존재하면 스킵한다.
        # episode_brief를 미리 복사해두면 runner.py 수정 없이 scope/do_not_cover가 반영된다.
        editorial_brief_path = ep_dir / "editorial_brief.json"
        if not editorial_brief_path.exists():
            editorial_brief_path.write_text(
                json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        if dry_run:
            print(f"[series_runner] DRY RUN — EP{ep_num:02d}: {slug}", flush=True)
            episodes_completed += 1
            continue

        project = {
            "slug": slug,
            "output_dir": str(ep_dir),
            "topic": f"{series_plan['title']} {ep_num}편 — {episode['title']}",
            "writing_style": series_plan.get("writing_style", ""),
            "episode_brief_path": str(brief_path),
        }

        try:
            print(f"[series_runner] EP{ep_num:02d} 시작: {slug}", flush=True)
            run_single_episode(project, stop_after_step="step_2b")
            episodes_completed += 1
            print(f"[series_runner] EP{ep_num:02d} 완료", flush=True)
        except Exception as e:
            print(f"[series_runner] EP{ep_num:02d} 실패: {e}", flush=True)
            episodes_failed.append(ep_num)

    save_series_plan(series_plan, output_base / "series_plan.json")

    return {
        "series_id": series_id,
        "episodes_completed": episodes_completed,
        "episodes_failed": episodes_failed,
        "series_review_path": None,
    }
