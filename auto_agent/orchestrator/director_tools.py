"""
Director Agent 전용 도구 실행기.

PipelineRunner의 핵심 메서드를 래핑하여 Director Agent가
파이프라인을 동적으로 제어할 수 있는 9개 도구를 제공한다.

크로스플랫폼 규칙:
  - Path() 사용, 문자열 결합 경로 금지
  - open/read_text/write_text에 encoding="utf-8" 필수
  - print()에 유니코드 특수문자 금지 (ASCII만)
  - subprocess 호출 시 encoding="utf-8" 필수
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from auto_agent.orchestrator.runner import PipelineRunner, StepResult


# ---- helper: _notify 모듈 레벨 import ----
def _notify_bridge(
    agent: str,
    text: str,
    phase: str = "",
    project: str = "",
    level: str = "info",
    data: Optional[dict] = None,
):
    """runner.py 의 _notify 를 안전하게 호출."""
    try:
        from auto_agent.orchestrator.runner import _notify
        _notify(agent=agent, text=text, phase=phase, project=project, level=level, data=data)
    except Exception:
        pass


class DirectorToolExecutor:
    """Director Agent 가 사용하는 9개 도구의 실행기.

    PipelineRunner 인스턴스를 주입받아 기존 메서드를 래핑한다.
    모든 public 메서드는 JSON-serializable dict 를 반환한다.
    """

    def __init__(self, runner: "PipelineRunner"):
        self.runner = runner
        self.state = runner.state
        self.project_dir: Path = runner.project_dir
        self.project_slug: str = runner.project_slug
        self.pipeline: dict = runner.pipeline

    # ========================================
    # 라우터
    # ========================================

    def execute(self, tool_name: str, tool_input: dict) -> str:
        """tool_name 에 해당하는 핸들러를 찾아 실행, JSON 문자열 반환."""
        handler = getattr(self, f"_exec_{tool_name}", None)
        if not handler:
            return json.dumps({"error": f"Unknown director tool: {tool_name}"}, ensure_ascii=False)
        try:
            result = handler(tool_input)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)

    # ========================================
    # 1. get_pipeline_state
    # ========================================

    def _exec_get_pipeline_state(self, inp: dict) -> dict:
        """completed / failed / skipped 스텝 목록 + 현재 phase/step 반환."""
        return {
            "current_phase": self.state.current_phase,
            "current_step": self.state.current_step,
            "completed_steps": list(self.state.completed_steps),
            "failed_steps": list(self.state.failed_steps),
            "skipped_steps": list(self.state.skipped_steps),
            "total_results": len(self.state.results),
        }

    # ========================================
    # 2. get_step_info
    # ========================================

    def _exec_get_step_info(self, inp: dict) -> dict:
        """pipeline.json 에서 step_id 에 해당하는 스텝 정의 반환."""
        step_id = inp["step_id"]
        for phase in self.pipeline.get("phases", []):
            for step in phase.get("steps", []):
                if step.get("id") == step_id:
                    return {"found": True, "step": step, "phase": phase.get("id", "")}
        return {"found": False, "error": f"Step '{step_id}' not found in pipeline.json"}

    # ========================================
    # 3. run_step
    # ========================================

    def _exec_run_step(self, inp: dict) -> dict:
        """단일 스텝 실행 (_execute_step + _validate_step) + 상태 업데이트."""
        step_id = inp["step_id"]
        step_def = self._find_step_def(step_id)
        if step_def is None:
            return {"error": f"Step '{step_id}' not found in pipeline.json"}

        # Director feedback 주입
        if inp.get("feedback"):
            step_def["_director_feedback"] = inp["feedback"]

        t0 = time.time()
        result = self.runner._execute_step(step_def)
        result = self.runner._validate_step(step_id, result)
        elapsed = time.time() - t0
        result.duration_sec = elapsed

        # 상태 업데이트
        self.state.results[step_id] = result.__dict__
        self._update_step_lists(step_id, result.status)
        self._save_state()

        return {
            "step_id": step_id,
            "status": result.status,
            "duration_sec": round(elapsed, 2),
            "error": result.error or None,
        }

    # ========================================
    # 4. run_steps_parallel
    # ========================================

    def _exec_run_steps_parallel(self, inp: dict) -> dict:
        """여러 스텝을 ThreadPoolExecutor 로 동시 실행."""
        step_ids: list = inp["step_ids"]
        max_workers = min(len(step_ids), 10)
        results_map: Dict[str, dict] = {}

        def _run_one(sid: str) -> tuple:
            step_def = self._find_step_def(sid)
            if step_def is None:
                return sid, {"status": "failed", "error": f"Step '{sid}' not found"}
            t0 = time.time()
            res = self.runner._execute_step(step_def)
            res = self.runner._validate_step(sid, res)
            elapsed = time.time() - t0
            res.duration_sec = elapsed
            return sid, res

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_run_one, sid): sid for sid in step_ids}
            for future in as_completed(futures):
                sid = futures[future]
                try:
                    sid, res = future.result()
                    if isinstance(res, dict):
                        # step not found case
                        results_map[sid] = res
                    else:
                        self.state.results[sid] = res.__dict__
                        self._update_step_lists(sid, res.status)
                        results_map[sid] = {
                            "status": res.status,
                            "duration_sec": round(res.duration_sec, 2),
                            "error": res.error or None,
                        }
                except Exception as exc:
                    results_map[sid] = {"status": "failed", "error": str(exc)}
                    self._update_step_lists(sid, "failed")

        self._save_state()

        # 요약
        completed = [s for s, r in results_map.items() if r.get("status") == "completed"]
        failed = [s for s, r in results_map.items() if r.get("status") == "failed"]
        skipped = [s for s, r in results_map.items() if r.get("status") == "skipped"]

        return {
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "details": results_map,
        }

    # ========================================
    # 5. retry_step
    # ========================================

    def _exec_retry_step(self, inp: dict) -> dict:
        """실패한 스텝을 재실행. feedback 을 주입하여 에이전트에 전달."""
        step_id = inp["step_id"]
        feedback = inp.get("feedback", "")

        # failed 목록에서 제거
        if step_id in self.state.failed_steps:
            self.state.failed_steps.remove(step_id)

        # 기존 결과 제거
        self.state.results.pop(step_id, None)

        # feedback 주입 후 run_step 재사용
        return self._exec_run_step({"step_id": step_id, "feedback": feedback})

    # ========================================
    # 6. skip_step
    # ========================================

    def _exec_skip_step(self, inp: dict) -> dict:
        """스텝을 건너뛰기 처리."""
        step_id = inp["step_id"]
        reason = inp.get("reason", "Director skip")

        if step_id not in self.state.skipped_steps:
            self.state.skipped_steps.append(step_id)

        # failed 에 있었다면 제거
        if step_id in self.state.failed_steps:
            self.state.failed_steps.remove(step_id)

        self.state.results[step_id] = {
            "step_id": step_id,
            "status": "skipped",
            "error": reason,
            "duration_sec": 0.0,
        }
        self._save_state()

        _notify_bridge(
            "Director",
            f"Step {step_id} skipped: {reason}",
            phase=self.state.current_phase,
            project=self.project_slug,
            level="warning",
        )

        return {"step_id": step_id, "status": "skipped", "reason": reason}

    # ========================================
    # 7. review_output
    # ========================================

    def _exec_review_output(self, inp: dict) -> dict:
        """프로젝트 디렉토리 기준 상대경로 파일 읽기."""
        rel_path = inp["file_path"]
        resolved = (self.project_dir / rel_path).resolve()

        # 경로 traversal 방지
        try:
            resolved.relative_to(self.project_dir.resolve())
        except ValueError:
            return {"error": f"Path traversal denied: {rel_path}"}

        if not resolved.exists():
            return {"error": f"File not found: {rel_path}"}

        if not resolved.is_file():
            return {"error": f"Not a file: {rel_path}"}

        content = resolved.read_text(encoding="utf-8")

        if len(content) > 5000:
            head = content[:2000]
            tail = content[-1000:]
            return {
                "file": rel_path,
                "truncated": True,
                "total_chars": len(content),
                "content": (
                    head
                    + "\n\n... [TRUNCATED: "
                    + str(len(content) - 3000)
                    + " chars omitted] ...\n\n"
                    + tail
                ),
            }

        return {"file": rel_path, "truncated": False, "content": content}

    # ========================================
    # 8. log_preference
    # ========================================

    def _exec_log_preference(self, inp: dict) -> dict:
        """Director 학습 메모를 .vault/preferences/ 에 기록."""
        note = inp["note"]
        preset_id = inp.get("preset_id", "general")

        vault_dir = self.project_dir / ".vault" / "preferences"
        vault_dir.mkdir(parents=True, exist_ok=True)

        pref_path = vault_dir / f"{preset_id}.md"

        if not pref_path.exists():
            header = (
                f"# Director Preferences - {preset_id}\n\n"
                f"Auto-accumulated notes from Director Agent.\n\n---\n\n"
            )
            pref_path.write_text(header, encoding="utf-8")

        today = datetime.now().strftime("%Y-%m-%d")
        entry = f"- [{today}] [{self.project_slug}] {note}\n"

        with open(pref_path, "a", encoding="utf-8") as f:
            f.write(entry)

        return {
            "logged": True,
            "preset_id": preset_id,
            "file": str(pref_path),
        }

    # ========================================
    # 9. send_message
    # ========================================

    def _exec_send_message(self, inp: dict) -> dict:
        """대시보드 메신저에 메시지 전송."""
        text = inp["text"]
        level = inp.get("level", "info")

        _notify_bridge(
            "Director",
            text,
            phase=self.state.current_phase,
            project=self.project_slug,
            level=level,
        )

        return {"sent": True, "text": text, "level": level}

    # ========================================
    # Internal helpers
    # ========================================

    def _find_step_def(self, step_id: str) -> Optional[dict]:
        """pipeline.json 에서 step_id 에 해당하는 step dict 복사본 반환."""
        for phase in self.pipeline.get("phases", []):
            for step in phase.get("steps", []):
                if step.get("id") == step_id:
                    return dict(step)  # shallow copy
        return None

    def _update_step_lists(self, step_id: str, status: str):
        """completed/failed/skipped 리스트를 status 에 맞게 업데이트."""
        # 기존 항목 제거 (중복 방지)
        for lst in (self.state.completed_steps, self.state.failed_steps, self.state.skipped_steps):
            if step_id in lst:
                lst.remove(step_id)

        if status == "completed":
            self.state.completed_steps.append(step_id)
        elif status == "failed":
            self.state.failed_steps.append(step_id)
        elif status == "skipped":
            self.state.skipped_steps.append(step_id)

    def _save_state(self):
        """현재 파이프라인 상태를 project_dir/pipeline_state.json 에 저장."""
        state_path = self.project_dir / "pipeline_state.json"
        state_data = {
            "project_slug": self.project_slug,
            "started_at": self.state.started_at,
            "updated_at": datetime.now().isoformat(),
            "config": self.state.config,
            "completed_steps": list(self.state.completed_steps),
            "failed_steps": list(self.state.failed_steps),
            "skipped_steps": list(self.state.skipped_steps),
            "results": dict(self.state.results),
        }
        state_path.write_text(
            json.dumps(state_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
