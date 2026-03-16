"""
파이프라인 오케스트레이터 (Python Runner — No LLM)

pipeline.json을 읽고 순차/병렬 실행.
정상 흐름은 100% 규칙 기반. 에러 시 Haiku 판단 위임.

프로젝트 config에서 주입되는 변수:
  - art_style: 아트스타일 JSON 경로 (artstyle/styles/*.json)
  - voice_id: ElevenLabs voice ID
  - voice_settings: TTS 설정 (stability, similarity_boost, speed 등)

사용법:
  python -m orchestrator.runner --project <slug>
  python -m orchestrator.runner --project <slug> --from step_7
  python -m orchestrator.runner --project <slug> --only step_8b
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_workspace_dir, get_data_dir, PACKAGE_DIR, DATA_DIR
from auto_agent.orchestrator.context_memory import ContextMemory
from auto_agent.orchestrator.vault_rag import VaultRAG

# ── Agent Messenger 브릿지 ──
_MESSENGER_URL = "http://localhost:8080/api/agent-messages/send"

def _notify(agent: str, text: str, phase: str = "", project: str = "", level: str = "info", data: dict = None):
    """파이프라인 진행 상황을 대시보드 메신저로 HTTP POST 전송."""
    try:
        import urllib.request
        payload = json.dumps({
            "agent": agent, "text": text, "phase": phase,
            "project": project, "level": level, "data": data or {},
        }, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            _MESSENGER_URL, data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=2)
    except Exception:
        pass


# ── 메신저 한글 메시지 매핑 ──
_MSG_MAP = {
    # phase_0
    "environment_check":          ("환경 검증",           "환경 검증 통과"),
    # phase_1
    "deep_research_and_synthesis":("심층 리서치",          "심층 리서치 완료"),
    "outline_and_manuscript":     ("아웃라인/원고 작성",    "아웃라인/원고 작성 완료"),
    # phase_2
    "duplicate_check":            ("중복 감지",            "중복 감지 완료"),
    "fact_check":                 ("팩트 체크",            "팩트 체크 완료"),
    # phase_3
    "scene_decomposition":        ("씬 분할",              "씬 분할 완료"),
    "character_planning":         ("캐릭터 플래닝",         "캐릭터 플래닝 완료"),
    "creative_direction":         ("창의적 연출",           "창의적 연출 완료"),
    "asset_advisory":             ("에셋 심의",            "에셋 심의 완료"),
    "data_enrichment_and_motion": ("데이터 보강/모션 설계",  "데이터 보강/모션 설계 완료"),
    # phase_4
    "tts_preprocess":             ("TTS 전처리",           "TTS 전처리 완료"),
    "tts_generation":             ("음성 생성",            "음성 생성 완료"),
    "image_asset_sourcing":       ("이미지 소싱",           "이미지 소싱 완료"),
    "subtitle_sync":              ("자막 동기화",           "자막 동기화 완료"),
    "tts_verification":           ("TTS 발음 검증",         "TTS 발음 검증 완료"),
    # phase_5
    "data_validation":            ("데이터 정합성 검증",     "데이터 검증 통과"),
    "manifest_building":          ("매니페스트 빌드",        "매니페스트 빌드 완료"),
    "still_capture":              ("스틸 프레임 캡처",       "스틸 프레임 캡처 완료"),
    "qa_pre_render":              ("사전 QA 검수",          "사전 QA 검수 통과"),
    "video_assembly":             ("영상 렌더링",           "영상 렌더링 완료"),
    "qa_post_render":             ("사후 QA 검수",          "사후 QA 검수 완료"),
}


def _step_label(step_name: str, event: str = "start") -> str:
    """step_name → 한글 메시지 변환. event: 'start' | 'done' | 'fail'"""
    labels = _MSG_MAP.get(step_name)
    if not labels:
        return step_name
    start_label, done_label = labels
    if event == "start":
        return f"{start_label} 시작합니다"
    elif event == "done":
        return done_label
    else:  # fail
        return f"{start_label} 실패"


class ProgressFileMonitor:
    """에이전트가 기록하는 .progress.jsonl 파일을 감시하여 메신저로 중계."""

    def __init__(self, progress_path: Path, project_slug: str, phase: str):
        self.path = progress_path
        self.project_slug = project_slug
        self.phase = phase
        self._stop = threading.Event()
        self._thread = None
        self._pos = 0

    def start(self):
        # 기존 파일 초기화
        self.path.write_text("", encoding="utf-8")
        self._pos = 0
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        # 남은 줄 flush
        self._flush_remaining()
        # 임시 파일 정리
        self.path.unlink(missing_ok=True)

    def _watch(self):
        while not self._stop.is_set():
            self._flush_remaining()
            self._stop.wait(0.5)

    def _flush_remaining(self):
        try:
            if not self.path.exists():
                return
            with open(self.path, "r", encoding="utf-8") as f:
                f.seek(self._pos)
                new_lines = f.readlines()
                self._pos = f.tell()
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    _notify(
                        agent=msg.get("agent", "System"),
                        text=msg.get("text", ""),
                        phase=msg.get("phase", self.phase),
                        project=self.project_slug,
                        level=msg.get("level", "info"),
                        data=msg.get("data"),
                    )
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

PROJECT_ROOT = get_workspace_dir()  # 하위 호환


# ═══════════════════════════════════════
# 데이터 모델
# ═══════════════════════════════════════

@dataclass
class StepResult:
    step_id: str
    status: str  # "completed", "failed", "skipped"
    duration_sec: float = 0.0
    error: str = ""
    output_files: List[str] = field(default_factory=list)
    cost_info: dict = field(default_factory=dict)


@dataclass
class ChapterResult:
    chapter: int
    status: str  # "completed", "failed"
    scenes: list = field(default_factory=list)
    error: str = ""
    cost_info: dict = field(default_factory=dict)
    duration_sec: float = 0.0


@dataclass
class PipelineState:
    project_id: int
    project_slug: str
    current_phase: str = ""
    current_step: str = ""
    completed_steps: List[str] = field(default_factory=list)
    failed_steps: List[str] = field(default_factory=list)
    skipped_steps: List[str] = field(default_factory=list)
    results: Dict[str, dict] = field(default_factory=dict)
    started_at: str = ""
    config: dict = field(default_factory=dict)


# ═══════════════════════════════════════
# 오케스트레이터
# ═══════════════════════════════════════

class PipelineRunner:
    """pipeline.json 기반 파이프라인 실행기."""

    def __init__(self, project_slug: str):
        # 워크스페이스 .env 로드
        try:
            from dotenv import load_dotenv
            load_dotenv(get_workspace_dir() / ".env")
        except ImportError:
            pass

        self.project_slug = project_slug
        self.pipeline = self._load_pipeline()
        self.pm = self._get_project_manager()
        self.project = self._resolve_project()
        self.state = PipelineState(
            project_id=self.project["id"],
            project_slug=project_slug,
            started_at=datetime.now().isoformat(),
            config=self._load_project_config(),
        )
        output_dir = self.project["output_dir"]
        if not output_dir:
            output_dir = str(get_workspace_dir() / "output" / project_slug)
        self.project_dir = Path(output_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.context_memory = ContextMemory(self.project_dir)
        self.vault = VaultRAG()
        self.sync = self._init_sync()

    def _init_sync(self):
        """Supabase 동기화 매니저 초기화. 환경변수 미설정 시 None."""
        from auto_agent.supabase_client import supabase_enabled
        if not supabase_enabled():
            return None
        from auto_agent.sync import SyncManager
        return SyncManager(
            project_slug=self.project_slug,
            project_dir=self.project_dir,
            local_project_id=self.project["id"],
        )

    def _load_pipeline(self) -> dict:
        path = DATA_DIR / "pipeline.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_project_manager(self):
        from auto_agent.dashboard.supabase_data import SupabaseProjectManager
        return SupabaseProjectManager()

    def _resolve_project(self) -> dict:
        project = self.pm.get_project(slug=self.project_slug)
        if not project:
            print(f"ERROR: Project '{self.project_slug}' not found in DB")
            print("Available projects:")
            for p in self.pm.list_projects():
                print(f"  - {p['slug']} ({p['status']})")
            sys.exit(1)
        return project

    def _load_project_config(self) -> dict:
        """프로젝트 config 로드. art_style, voice_id 등."""
        config = self.pm.get_config(self.project["id"])
        # config 검증
        if not config.get("art_style"):
            print("WARNING: project config에 art_style 미설정")
        if not config.get("voice_id"):
            print("WARNING: project config에 voice_id 미설정 → .env 폴백")
        return config

    # ─────────────────────────────────────
    # 실행 엔진
    # ─────────────────────────────────────

    def run(
        self,
        from_step: str = None,
        only_step: str = None,
        dry_run: bool = False,
    ):
        """파이프라인 전체 또는 부분 실행."""
        phases = self.pipeline.get("phases", [])
        skip_until = from_step
        found_start = from_step is None

        print(f"{'=' * 60}")
        print(f"Pipeline Runner — {self.project_slug}")
        print(f"Config: art_style={self.state.config.get('art_style', 'N/A')}")
        print(f"        voice_id={self.state.config.get('voice_id', 'N/A')}")
        print(f"{'=' * 60}\n")
        _notify("Director", "파이프라인 시작합니다", phase="pipeline", project=self.project_slug, level="info")

        # 프로젝트 상태 업데이트
        self.pm.update_project(self.project["id"], status="in_progress")

        for phase in phases:
            phase_id = phase["id"]
            phase_name = phase.get("name", phase_id)
            execution = phase.get("execution", "sequential")
            steps = phase.get("steps", [])

            # --only 모드: 해당 step만 실행
            if only_step:
                target = [s for s in steps if s["id"] == only_step]
                if not target:
                    continue
                steps = target
                found_start = True

            # --from 모드: 시작점까지 스킵
            if not found_start:
                remaining = []
                for s in steps:
                    if s["id"] == skip_until:
                        found_start = True
                    if found_start:
                        remaining.append(s)
                steps = remaining
                if not steps:
                    continue

            if not steps:
                continue

            print(f"\n{'─' * 40}")
            print(f"Phase: {phase_name} ({phase_id})")
            print(f"Execution: {execution}")
            print(f"Steps: {len(steps)}")
            print(f"{'─' * 40}\n")

            self.state.current_phase = phase_id
            _notify("Director", f"{phase_name} 시작합니다 ({len(steps)}개 스텝)", phase=phase_id, project=self.project_slug)

            if dry_run:
                for step in steps:
                    print(f"  [DRY] {step['id']}: {step.get('name', '')} "
                          f"({step.get('agent') or step.get('module', 'unknown')})")
                continue

            if "parallel" in execution:
                self._run_parallel(steps)
            else:
                self._run_sequential(steps)

            # phase 끝나면 checkpoint 확인
            self._check_checkpoint(phase_id, steps)

            if only_step:
                break

        self._finish()

    def _run_sequential(self, steps: List[dict]):
        """순차 실행."""
        for step in steps:
            result = self._execute_step(step)
            self.state.results[step["id"]] = result.__dict__

            if result.status == "failed":
                step_name = step.get("name", step["id"])
                # gate step이면 파이프라인 중단
                if step.get("gate"):
                    print(f"\n  GATE FAILED: {step['id']} — 파이프라인 중단")
                    _notify("Director", f"파이프라인 중단 — {_step_label(step_name, 'fail')}", phase=self.state.current_phase, project=self.project_slug, level="error")
                    self.state.failed_steps.append(step["id"])
                    return
                # non-blocking이면 계속
                if step.get("blocking") is False:
                    print(f"  [WARN] {step['id']} failed (non-blocking) — 계속 진행")
                    _notify("Director", f"{_step_label(step_name, 'fail')} (non-blocking) — 계속 진행", phase=self.state.current_phase, project=self.project_slug, level="warning")
                    self.state.failed_steps.append(step["id"])
                else:
                    print(f"\n  STEP FAILED: {step['id']} — 파이프라인 중단")
                    _notify("Director", f"{_step_label(step_name, 'fail')} — 파이프라인 중단", phase=self.state.current_phase, project=self.project_slug, level="error")
                    self.state.failed_steps.append(step["id"])
                    return
            else:
                self.state.completed_steps.append(step["id"])

    def _detect_cycles(self, dependent: Dict[str, tuple]) -> List[str]:
        """순환 의존성 탐지. 순환에 포함된 step ID 리스트 반환."""
        # 간단한 DFS 기반 순환 탐지
        visiting = set()
        visited = set()
        cycle_nodes = []

        def dfs(node_id: str) -> bool:
            if node_id in visiting:
                cycle_nodes.append(node_id)
                return True
            if node_id in visited:
                return False
            visiting.add(node_id)
            if node_id in dependent:
                _, deps = dependent[node_id]
                for dep in deps:
                    if dep in dependent and dfs(dep):
                        cycle_nodes.append(node_id)
                        return True
            visiting.discard(node_id)
            visited.add(node_id)
            return False

        for step_id in dependent:
            if step_id not in visited:
                dfs(step_id)

        return cycle_nodes

    def _run_parallel(self, steps: List[dict]):
        """병렬 실행. depends_on이 있는 step은 의존성 해소 후 실행."""
        # 의존성 그래프 분석
        independent = []
        dependent = {}
        for step in steps:
            deps = step.get("depends_on")
            if deps:
                dep_list = [deps] if isinstance(deps, str) else deps
                dependent[step["id"]] = (step, dep_list)
            else:
                independent.append(step)

        # 순환 의존성 감지
        cycle_nodes = self._detect_cycles(dependent)
        if cycle_nodes:
            print(f"\n  [ERROR] 순환 의존성 감지: {cycle_nodes}")
            for node_id in set(cycle_nodes):
                self.state.failed_steps.append(node_id)
                self.state.results[node_id] = StepResult(
                    step_id=node_id, status="failed",
                    error=f"Circular dependency detected: {cycle_nodes}",
                ).__dict__
            # 순환에 포함되지 않은 independent step만 실행
            if not independent:
                return

        # 1차: 독립 step 병렬 실행
        completed_ids = set(self.state.completed_steps)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(self._execute_step, step): step
                for step in independent
            }
            for fut in as_completed(futures):
                step = futures[fut]
                result = fut.result()
                self.state.results[step["id"]] = result.__dict__
                if result.status == "completed":
                    completed_ids.add(step["id"])
                    self.state.completed_steps.append(step["id"])
                elif step.get("blocking") is not False:
                    self.state.failed_steps.append(step["id"])

        # 2차: 의존성 해소된 step 위상 정렬 실행 (다단계 의존성 지원)
        remaining = {
            sid: (step, deps)
            for sid, (step, deps) in dependent.items()
            if sid not in set(cycle_nodes)
        }
        progress = True
        while remaining and progress:
            progress = False
            resolved = []
            for step_id, (step, deps) in remaining.items():
                if all(d in completed_ids for d in deps):
                    resolved.append(step_id)
            for step_id in resolved:
                step, deps = remaining.pop(step_id)
                result = self._execute_step(step)
                self.state.results[step_id] = result.__dict__
                if result.status == "completed":
                    completed_ids.add(step_id)
                    self.state.completed_steps.append(step_id)
                    progress = True
                else:
                    self.state.failed_steps.append(step_id)
                    progress = True  # 실패해도 다음 라운드 시도

        # 해소 불가 step 처리
        for step_id, (step, deps) in remaining.items():
            unmet = [d for d in deps if d not in completed_ids]
            print(f"  [SKIP] {step_id}: 의존성 미충족 ({unmet})")
            self.state.skipped_steps.append(step_id)
            self.state.results[step_id] = StepResult(
                step_id=step_id, status="skipped",
                error=f"Dependencies not met: {unmet}",
            ).__dict__

    def _split_by_chapter(self, scene_specs: dict) -> Optional[dict]:
        """scene_specs의 scenes를 chapter 필드로 그룹핑.

        Returns:
            {chapter_num: [scene_dict, ...], ...} 또는
            chapter 필드 없으면 None (폴백 신호)
        """
        scenes = scene_specs.get("scenes", [])
        if not scenes:
            return None

        has_chapter = any(s.get("chapter") for s in scenes)
        if not has_chapter:
            return None

        from collections import defaultdict
        chapters = defaultdict(list)
        for scene in scenes:
            ch = scene.get("chapter", 0)
            chapters[ch].append(scene)

        return dict(sorted(chapters.items()))

    def _merge_chapter_results(
        self,
        original_specs: dict,
        chapter_results: dict,
    ) -> dict:
        """챕터별 결과를 원본 scene_specs에 병합.

        Args:
            original_specs: 원본 scene_specs 전체
            chapter_results: {chapter_num: ChapterResult}

        Returns:
            병합된 scene_specs dict
        """
        # 원본 씬을 챕터별로 그룹핑
        from collections import defaultdict
        original_by_chapter = defaultdict(list)
        for s in original_specs.get("scenes", []):
            original_by_chapter[s.get("chapter", 0)].append(s)

        merged_scenes = []

        # 모든 챕터를 순회 (결과가 없는 챕터는 원본 유지)
        all_chapters = set(original_by_chapter.keys()) | set(chapter_results.keys())
        for ch_num in sorted(all_chapters):
            ch_result = chapter_results.get(ch_num)
            if ch_result and ch_result.status == "completed" and ch_result.scenes:
                merged_scenes.extend(ch_result.scenes)
            else:
                merged_scenes.extend(original_by_chapter.get(ch_num, []))

        merged_scenes.sort(key=lambda s: s.get("sceneNumber", 0))

        result = dict(original_specs)
        result["scenes"] = merged_scenes
        return result

    # ─────────────────────────────────────
    # 챕터별 병렬 처리
    # ─────────────────────────────────────

    def _run_chunked_parallel(self, step: dict) -> StepResult:
        """챕터별 병렬 처리. scene_specs.json을 챕터로 분할 → 병렬 LLM 호출 → 병합."""
        step_id = step["id"]
        step_name = step.get("name", step_id)
        agent_name = step.get("agent", "visual-composer")
        label = _step_label(step_name, "start").replace(" 시작합니다", "")

        # scene_specs 로드
        specs_path = self.project_dir / "scene_specs.json"
        if not specs_path.exists():
            return StepResult(step_id=step_id, status="failed",
                              error="scene_specs.json 없음")

        original_specs = json.loads(specs_path.read_text(encoding="utf-8"))
        chapters = self._split_by_chapter(original_specs)

        # chapter 필드 없으면 폴백 (agent step으로 위임)
        if chapters is None:
            _notify(agent_name, "chapter 필드 없음 → 단일 호출로 전환합니다",
                    phase=self.state.current_phase, project=self.project_slug, level="warning")
            return self._run_agent_step(step)

        n_chapters = len(chapters)
        total_scenes = len(original_specs.get("scenes", []))

        # ── 중간 동기화 ① scene_count 업데이트 ──
        try:
            self.pm.update_project(self.project["id"], scene_count=total_scenes)
            _notify("Director", f"Supabase 동기화: scene_count={total_scenes}",
                    phase=self.state.current_phase, project=self.project_slug, level="info")
        except Exception:
            pass

        _notify(agent_name, f"{label} 시작합니다 ({n_chapters} 챕터 병렬)",
                phase=self.state.current_phase, project=self.project_slug)

        self.state.current_step = step_id
        print(f"  [{step_id}] {step_name} ({n_chapters} 챕터 병렬) ... ", flush=True)

        # DB 파이프라인 기록
        run_id = self.pm.start_pipeline_run(
            project_id=self.project["id"],
            phase=self.state.current_phase,
            step=step_id,
            step_name=step_name,
            agent_or_module=agent_name,
        )

        t0 = time.time()
        chapter_results = {}
        total_cost = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

        # 1차 병렬 실행 (챕터 수에 따라 최대 10 워커)
        workers = min(n_chapters, 10)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for ch_num, ch_scenes in chapters.items():
                fut = pool.submit(
                    self._execute_chapter,
                    step, ch_num, ch_scenes, original_specs,
                )
                futures[fut] = ch_num

            for fut in as_completed(futures):
                ch_num = futures[fut]
                try:
                    ch_result = fut.result()
                except Exception as e:
                    ch_result = ChapterResult(
                        chapter=ch_num, status="failed",
                        error=str(e),
                    )
                chapter_results[ch_num] = ch_result

                # ── 중간 동기화 ② 챕터 완료 시 부분 업로드 ──
                if ch_result.status == "completed" and self.sync:
                    try:
                        partial = self._merge_chapter_results(original_specs, chapter_results)
                        self.sync.upload_json("scene_specs.json", partial)
                        done_count = sum(1 for r in chapter_results.values() if r.status == "completed")
                        _notify("Director", f"Supabase 동기화: scene_specs 업데이트 ({done_count}/{n_chapters} 챕터)",
                                phase=self.state.current_phase, project=self.project_slug, level="info")
                    except Exception:
                        pass

        # 실패 챕터 재시도 (max 2회)
        failed_chapters = {
            ch: r for ch, r in chapter_results.items()
            if r.status == "failed"
        }
        for retry in range(1, 3):
            if not failed_chapters:
                break
            for ch_num in list(failed_chapters.keys()):
                _notify(agent_name,
                        f"{label} Ch{ch_num} 재시도합니다 ({retry}/2)",
                        phase=self.state.current_phase, project=self.project_slug)
                time.sleep(5)
                try:
                    ch_result = self._execute_chapter(
                        step, ch_num, chapters[ch_num], original_specs,
                    )
                    if ch_result.status == "completed":
                        chapter_results[ch_num] = ch_result
                        del failed_chapters[ch_num]
                        _notify(agent_name,
                                f"{label} Ch{ch_num} 재시도 완료 ({ch_result.duration_sec:.1f}s)",
                                phase=self.state.current_phase, project=self.project_slug,
                                level="success")
                except Exception:
                    pass

        # 최종 실패 챕터 → 볼트 에러 기록
        for ch_num, ch_result in failed_chapters.items():
            ch_scenes = chapters[ch_num]
            scene_nums = [s.get("sceneNumber", 0) for s in ch_scenes]
            scene_range = (min(scene_nums), max(scene_nums)) if scene_nums else (0, 0)
            self.vault.record_pipeline_error(
                step_name=step_name,
                chapter=ch_num,
                scene_range=scene_range,
                error_message=ch_result.error[:300],
                project_slug=self.project_slug,
                agent=agent_name,
                label=label,
            )
            _notify(agent_name,
                    f"Ch{ch_num} 실패 원인을 볼트에 기록했습니다",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="warning")

        # 비용 합산
        for ch_result in chapter_results.values():
            for k in ("tokens_in", "tokens_out", "cost_usd"):
                total_cost[k] += ch_result.cost_info.get(k, 0)

        # 병합
        merged = self._merge_chapter_results(original_specs, chapter_results)
        specs_path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 임시 파일 정리
        for ch_num in chapters:
            tmp = self.project_dir / f".scene_specs_ch{ch_num}_{step_name}.json"
            tmp.unlink(missing_ok=True)
            progress = self.project_dir / f".progress_{step_id}_ch{ch_num}.jsonl"
            progress.unlink(missing_ok=True)

        elapsed = time.time() - t0
        succeeded = sum(1 for r in chapter_results.values() if r.status == "completed")
        failed_count = n_chapters - succeeded

        # 메신저 보고
        if failed_count == 0:
            msg = f"{label} 병합 완료 ({succeeded}/{n_chapters} 챕터, {elapsed:.1f}s)"
            level = "success"
        elif succeeded > 0:
            msg = f"{label} 병합 완료 ({succeeded}/{n_chapters} 챕터, {failed_count} 실패 — 이전 데이터 유지)"
            level = "warning"
        else:
            msg = f"{label} 전체 실패 ({n_chapters} 챕터)"
            level = "error"

        _notify(agent_name, msg, phase=self.state.current_phase,
                project=self.project_slug, level=level)
        print(f"    {msg}")

        # DB 기록
        if succeeded > 0:
            self.pm.complete_pipeline_run(
                run_id,
                cost_tokens_in=total_cost.get("tokens_in", 0),
                cost_tokens_out=total_cost.get("tokens_out", 0),
                cost_usd=total_cost.get("cost_usd", 0.0),
            )
            # Supabase 동기화
            if self.sync:
                try:
                    self.sync.sync_step(
                        step=step, phase=self.state.current_phase,
                        status="completed",
                        output_files=[str(specs_path)],
                        cost_info=total_cost,
                        project_data=dict(self.project),
                        duration_sec=elapsed,
                    )
                    _notify("Director", "Supabase 동기화 완료",
                            phase=self.state.current_phase, project=self.project_slug, level="success")
                except Exception as sync_err:
                    print(f"    [WARN] Supabase 동기화 실패: {sync_err}")
                    _notify("Director", f"Supabase 동기화 실패: {str(sync_err)[:50]}",
                            phase=self.state.current_phase, project=self.project_slug, level="warning")

            # ── 자동 매니페스트 빌드 + 썸네일 캡처 ──
            self._auto_build_and_capture(chapter_results, chapters)

            return StepResult(
                step_id=step_id, status="completed",
                duration_sec=elapsed,
                output_files=[str(specs_path)],
                cost_info=total_cost,
            )
        else:
            self.pm.fail_pipeline_run(run_id, "전체 챕터 실패")
            return StepResult(
                step_id=step_id, status="failed",
                duration_sec=elapsed,
                error=f"전체 {n_chapters} 챕터 실패",
                cost_info=total_cost,
            )

    def _execute_chapter(
        self,
        step: dict,
        chapter_num: int,
        chapter_scenes: list,
        full_specs: dict,
    ) -> ChapterResult:
        """단일 챕터의 씬들에 대해 Claude CLI 호출.

        병렬 실행 시 race condition 방지를 위해
        CLI는 scene_specs.json이 아닌 챕터 전용 임시 파일에만 쓴다.
        임시 파일은 _run_chunked_parallel에서 병합 후 일괄 정리.
        """
        step_id = step["id"]
        step_name = step.get("name", step_id)
        agent_name = step.get("agent", "visual-composer")
        label = _step_label(step_name, "start").replace(" 시작합니다", "")

        n_scenes = len(chapter_scenes)
        _notify(agent_name,
                f"{label} 시작합니다 (Ch{chapter_num}, {n_scenes}씬)",
                phase=self.state.current_phase, project=self.project_slug)

        t0 = time.time()

        # 1. 챕터 전용 축소 scene_specs 임시 파일 생성
        chapter_specs = dict(full_specs)
        chapter_specs["scenes"] = chapter_scenes
        chapter_specs["_chapter_filter"] = chapter_num

        tmp_filename = f".scene_specs_ch{chapter_num}_{step_name}.json"
        tmp_path = self.project_dir / tmp_filename
        tmp_path.write_text(
            json.dumps(chapter_specs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 2. 프롬프트 빌드
        chapter_step = dict(step)
        chapter_step["_chapter_num"] = chapter_num
        chapter_step["_chapter_specs_path"] = str(tmp_path)

        prompt = self._build_chapter_prompt(chapter_step, chapter_specs)

        # 3. Claude CLI 실행
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        model = step.get("single_call_model", agent_def.get("model", "claude-opus-4-6"))
        max_turns = agent_def.get("max_turns", 30)
        allowed_tools = agent_def.get("allowed_tools", ["Read", "Write", "Glob"])
        timeout_sec = self._get_agent_timeout(agent_name)

        cli_path = self._find_claude_cli()
        cmd = [
            cli_path, "--print", "--output-format", "json",
            "--model", model, "--max-turns", str(max_turns),
        ]
        for tool in allowed_tools:
            cmd.extend(["--allowedTools", tool])

        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        env.pop("CLAUDECODE", None)

        progress_path = self.project_dir / f".progress_{step_id}_ch{chapter_num}.jsonl"
        env["PROGRESS_FILE"] = str(progress_path)
        monitor = ProgressFileMonitor(progress_path, self.project_slug, self.state.current_phase)
        monitor.start()

        try:
            proc = subprocess.Popen(
                cmd, cwd=str(self.project_dir), env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            try:
                stdout, stderr = proc.communicate(input=prompt, timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return ChapterResult(
                    chapter=chapter_num, status="failed",
                    error=f"CLI 타임아웃 ({timeout_sec}s)",
                )
        except FileNotFoundError:
            return ChapterResult(
                chapter=chapter_num, status="failed",
                error="Claude CLI를 찾을 수 없습니다",
            )
        finally:
            monitor.stop()
            # 주의: tmp_path는 여기서 삭제하지 않음 — 결과 읽기 필요

        elapsed = time.time() - t0
        cost_info = self._parse_claude_cost(stdout, stderr)

        if proc.returncode != 0:
            error = stderr[:300] or stdout[:300]
            return ChapterResult(
                chapter=chapter_num, status="failed",
                error=f"CLI exit {proc.returncode}: {error}",
                cost_info=cost_info, duration_sec=elapsed,
            )

        # 4. 결과 파싱: 챕터 전용 임시 파일에서 읽기
        try:
            if tmp_path.exists():
                updated = json.loads(tmp_path.read_text(encoding="utf-8"))
                updated_scenes = updated.get("scenes", chapter_scenes)
            else:
                updated_scenes = chapter_scenes
        except Exception:
            updated_scenes = chapter_scenes

        _notify(agent_name,
                f"{label} 완료 (Ch{chapter_num}, {elapsed:.1f}s)",
                phase=self.state.current_phase, project=self.project_slug,
                level="success")

        return ChapterResult(
            chapter=chapter_num, status="completed",
            scenes=updated_scenes,
            cost_info=cost_info, duration_sec=elapsed,
        )

    def _build_chapter_prompt(self, step: dict, chapter_specs: dict) -> str:
        """챕터별 병렬 처리용 프롬프트 빌드."""
        agent_name = step["agent"]
        chapter_num = step.get("_chapter_num", 0)
        chapter_specs_path = step.get("_chapter_specs_path", "")

        # 에이전트 스킬
        skill_path = DATA_DIR / "skills" / "agents" / agent_name / "SKILL.md"
        agent_skill = ""
        if skill_path.exists():
            agent_skill = skill_path.read_text(encoding="utf-8")

        # 공유 스킬 수집 (기존 _build_agent_prompt 로직 재사용)
        skill_names = list(step.get("skills", []))
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        for s in agent_def.get("skills", []):
            if s not in skill_names:
                skill_names.append(s)

        skill_refs = agent_def.get("skill_refs", {})
        shared_skills_text = ""
        for skill_name in skill_names:
            skill_dir = DATA_DIR / "skills" / "shared" / skill_name
            if (skill_dir / "SKILL.md").exists():
                content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                refs_to_load = skill_refs.get(skill_name)
                ref_dir = skill_dir / "references"
                if ref_dir.exists():
                    if refs_to_load is not None:
                        for ref_name in refs_to_load:
                            ref_file = ref_dir / f"{ref_name}.md"
                            if ref_file.exists():
                                content += f"\n\n{ref_file.read_text(encoding='utf-8')}"
                    else:
                        for ref_file in sorted(ref_dir.glob("*.md")):
                            content += f"\n\n{ref_file.read_text(encoding='utf-8')}"
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"
                continue
            skill_file = DATA_DIR / "skills" / "shared" / f"{skill_name}.md"
            if skill_file.exists():
                shared_skills_text += f"\n\n## {skill_name}\n\n{skill_file.read_text(encoding='utf-8')}"

        # 공통 컨텍스트 파일
        context_block = ""
        for fname in ["research_report.json", "outline.json", "character_plan.json"]:
            fpath = self.project_dir / fname
            if fpath.exists():
                context_block += f"\n<file name=\"{fname}\">\n{fpath.read_text(encoding='utf-8')[:50000]}\n</file>\n"

        # final_manuscript.md — 해당 챕터 구간만 추출
        manuscript_path = self.project_dir / "final_manuscript.md"
        if manuscript_path.exists():
            full_ms = manuscript_path.read_text(encoding="utf-8")
            chapter_ms = self._extract_chapter_manuscript(full_ms, chapter_num)
            context_block += f"\n<file name=\"final_manuscript.md (챕터 {chapter_num} 구간)\">\n{chapter_ms}\n</file>\n"

        # 챕터 전용 scene_specs 인라인
        chapter_specs_json = json.dumps(chapter_specs, ensure_ascii=False, indent=2)

        # 컨텍스트 메모리
        context_memory_block = self.context_memory.build_context_prompt(step.get("id", ""))

        prompt = f"""<system_context>
프로젝트: {self.project_slug}
작업 디렉토리: {self.project_dir}
워크스페이스: {get_workspace_dir()}
챕터: {chapter_num} (챕터별 병렬 처리 모드)
</system_context>

<agent_skill>
{agent_skill}
</agent_skill>

<shared_skills>
{shared_skills_text}
</shared_skills>

{context_block}

<chapter_scene_specs>
아래는 챕터 {chapter_num}의 씬들만 포함된 scene_specs입니다.
이 씬들에 대해서만 작업하세요.

{chapter_specs_json}
</chapter_scene_specs>

<task>
Step: {step.get("id", "")} — {step.get("name", "")}
{step.get("description", "")}
{step.get("notes", "")}

중요: 결과를 아래 파일에 저장하세요 (scene_specs.json이 아닌 챕터 전용 파일):
출력 파일: {chapter_specs_path}

JSON 구조는 기존 scene_specs와 동일하되, scenes 배열에는 챕터 {chapter_num}의 씬들만 포함합니다.
절대 scene_specs.json에 직접 쓰지 마세요. 반드시 위의 출력 파일 경로에 저장하세요.
</task>

{context_memory_block}"""
        return prompt

    def _extract_chapter_manuscript(self, full_text: str, chapter_num: int) -> str:
        """원고에서 해당 챕터 구간만 추출."""
        # 챕터 헤딩 패턴
        pattern = re.compile(
            rf"^(#{{1,3}})\s*(챕터|Chapter|장)\s*{chapter_num}\b",
            re.MULTILINE | re.IGNORECASE,
        )
        match = pattern.search(full_text)
        if not match:
            return full_text[:10000]

        start = match.start()
        next_pattern = re.compile(
            rf"^(#{{1,3}})\s*(챕터|Chapter|장)\s*{chapter_num + 1}\b",
            re.MULTILINE | re.IGNORECASE,
        )
        next_match = next_pattern.search(full_text, start + 1)
        end = next_match.start() if next_match else len(full_text)

        return full_text[start:end][:15000]

    def _auto_build_and_capture(self, chapter_results: dict, chapters: dict):
        """병합 완료 후 자동 매니페스트 빌드 + 변경 씬 썸네일 캡처."""
        _notify("Director", "매니페스트 빌드 + 썸네일 캡처 시작합니다",
                phase=self.state.current_phase, project=self.project_slug)

        # 1. 매니페스트 빌드
        try:
            pid = self.project["id"]
            storage_key = self.sync.storage_key if self.sync else None
            if storage_key:
                result = subprocess.run(
                    [sys.executable, "-m", "auto_agent.scripts.build_manifest",
                     pid, storage_key],
                    cwd=str(get_workspace_dir()),
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0:
                    print("    [AUTO] 매니페스트 빌드 완료")
                else:
                    print(f"    [WARN] 매니페스트 빌드 실패: {result.stderr[:200]}")
                    return
            else:
                print("    [SKIP] Supabase 미연결 — 매니페스트 빌드 스킵")
                return
        except Exception as e:
            print(f"    [WARN] 매니페스트 빌드 에러: {e}")
            return

        # 2. 변경된 씬의 기존 썸네일 무효화
        thumb_dir = self.project_dir / "thumbnails"
        invalidated = 0
        for ch_num, ch_result in chapter_results.items():
            if ch_result.status == "completed":
                for scene in chapters.get(ch_num, []):
                    sn = scene.get("sceneNumber", 0)
                    thumb = thumb_dir / f"scene_{sn:03d}.png"
                    if thumb.exists():
                        thumb.unlink(missing_ok=True)
                        invalidated += 1

        # 3. 썸네일 캡처 (generate-thumbnails.mjs)
        try:
            node = shutil.which("node")
            if not node:
                node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"
                if node_dir.exists():
                    os.environ["PATH"] = str(node_dir) + ":" + os.environ.get("PATH", "")
                    node = shutil.which("node")
            if not node:
                print("    [SKIP] Node.js 없음 — 썸네일 캡처 스킵")
                return

            script = get_workspace_dir() / "remotion" / "generate-thumbnails.mjs"
            if not script.exists():
                print(f"    [SKIP] {script} 없음")
                return

            # 매니페스트 경로 탐색
            ws = get_workspace_dir()
            manifest_path = None
            for p in [
                self.project_dir / "manifest.json",
                ws / "remotion" / "public" / "manifests" / f"{self.sync.storage_key}.json" if self.sync else None,
                ws / "remotion" / "public" / "manifest.json",
            ]:
                if p and p.exists():
                    manifest_path = p
                    break

            if not manifest_path:
                print("    [SKIP] 매니페스트 없음 — 썸네일 캡처 스킵")
                return

            _notify("Director", f"썸네일 캡처 시작합니다 ({invalidated}씬 무효화됨)",
                    phase=self.state.current_phase, project=self.project_slug)

            result = subprocess.run(
                [node, str(script), str(manifest_path), str(self.project_dir),
                 "--width=480"],
                cwd=str(script.parent),
                capture_output=True, text=True,
                timeout=300,
            )
            if result.returncode == 0:
                # 생성된 썸네일 수 파악
                count = len(list(thumb_dir.glob("scene_*.png"))) if thumb_dir.exists() else 0
                _notify("Director", f"썸네일 캡처 완료 ({count}씬)",
                        phase=self.state.current_phase, project=self.project_slug, level="success")
                print(f"    [AUTO] 썸네일 캡처 완료: {count}씬")
            else:
                print(f"    [WARN] 썸네일 캡처 실패: {result.stderr[:200]}")
                _notify("Director", f"썸네일 캡처 실패: {result.stderr[:60]}",
                        phase=self.state.current_phase, project=self.project_slug, level="warning")
        except subprocess.TimeoutExpired:
            print("    [WARN] 썸네일 캡처 타임아웃 (300s)")
        except Exception as e:
            print(f"    [WARN] 썸네일 캡처 에러: {e}")

    def _ensure_art_style_and_characters(self):
        """아트스타일 JSON + reference image + 기준 캐릭터 이미지 존재 확인.
        config에 지정된 스타일을 패키지에서 복제. config 미설정 시 경고만."""
        config = self.state.config
        art_style_rel = config.get("art_style")

        if not art_style_rel:
            _notify("System", "아트스타일 미설정 — config에 art_style을 설정해주세요",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="error")
            print("    [PREFLIGHT] 아트스타일 config 미설정")
            return

        # 1. 프로젝트 디렉토리에서 확인
        art_path = self.project_dir / art_style_rel
        if art_path.exists():
            return  # 이미 존재

        # 2. 패키지 디렉토리에서 복제
        pkg_path = PACKAGE_DIR / "data" / art_style_rel
        if pkg_path.exists():
            target_dir = art_path.parent
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(pkg_path, art_path)
            # 같은 디렉토리의 관련 파일(reference image 등) 복제
            style_stem = pkg_path.stem  # e.g. "quirky_cartoon"
            for f in pkg_path.parent.glob(f"{style_stem}*"):
                if f != pkg_path:
                    shutil.copy(f, target_dir / f.name)
            style_name = config.get("style_name", style_stem)
            _notify("System", f"아트스타일 '{style_name}' 패키지에서 복제했습니다",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="info")
            print(f"    [PREFLIGHT] 아트스타일 '{style_name}' 복제 완료")
        else:
            _notify("System", f"아트스타일 파일 없음: {art_style_rel}",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="error")
            print(f"    [PREFLIGHT] 아트스타일 파일 없음: {art_style_rel}")

        # 2. character_casting.json 기반 기준 캐릭터 이미지 확인
        casting_path = self.project_dir / "output" / self.project_slug / "character_casting.json"
        if not casting_path.exists():
            return

        try:
            casting = json.loads(casting_path.read_text(encoding="utf-8"))
        except Exception:
            return

        for char_id, info in casting.items():
            img_rel = info.get("image_path", "")
            if not img_rel:
                continue
            img_path = self.project_dir / img_rel
            if img_path.exists():
                continue

            # Supabase Storage에서 다운로드 시도
            storage_url = info.get("storage_url")
            if storage_url:
                try:
                    import urllib.request
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    urllib.request.urlretrieve(storage_url, str(img_path))
                    _notify("System", f"기준 캐릭터 '{char_id}' 이미지 복원했습니다",
                            phase=self.state.current_phase, project=self.project_slug,
                            level="warning")
                except Exception:
                    _notify("System", f"기준 캐릭터 '{char_id}' 복원 실패 — 이미지 재생성 필요",
                            phase=self.state.current_phase, project=self.project_slug,
                            level="error")

    # ─────────────────────────────────────
    # Step 실행
    # ─────────────────────────────────────

    def _execute_step(self, step: dict) -> StepResult:
        """단일 step 실행. 타입에 따라 에이전트 or 모듈 호출."""
        step_id = step["id"]
        step_name = step.get("name", step_id)
        step_type = step.get("type", "agent" if "agent" in step else "module")

        # conditional 체크
        if step.get("conditional"):
            if not self._check_condition(step):
                print(f"  [SKIP] {step_id}: 조건 미충족")
                return StepResult(step_id=step_id, status="skipped")

        # chunked_parallel 분기
        if step.get("chunked_parallel"):
            return self._run_chunked_parallel(step)

        # 이미지 소싱 전 아트스타일/캐릭터 프리플라이트
        if step_name == "image_asset_sourcing":
            self._ensure_art_style_and_characters()

        self.state.current_step = step_id
        print(f"  [{step_id}] {step_name} ... ", end="", flush=True)
        _agent_label = step.get("agent") or step.get("module", "System")
        _notify(_agent_label, _step_label(step_name, "start"), phase=self.state.current_phase, project=self.project_slug)

        # DB 파이프라인 기록 시작
        run_id = self.pm.start_pipeline_run(
            project_id=self.project["id"],
            phase=self.state.current_phase,
            step=step_id,
            step_name=step_name,
            agent_or_module=step.get("agent") or step.get("module"),
        )

        t0 = time.time()
        try:
            if step_type == "single_call":
                result = self._run_single_call_step(step)
            elif step.get("agent"):
                result = self._run_agent_step(step)
            elif step.get("module"):
                result = self._run_module_step(step)
            else:
                result = StepResult(step_id=step_id, status="skipped",
                                    error="Unknown step type")

            elapsed = time.time() - t0
            result.duration_sec = elapsed

            if result.status == "completed":
                cost = result.cost_info
                self.pm.complete_pipeline_run(
                    run_id,
                    cost_tokens_in=cost.get("tokens_in", 0),
                    cost_tokens_out=cost.get("tokens_out", 0),
                    cost_usd=cost.get("cost_usd", 0.0),
                )
                cost_str = f" ${cost['cost_usd']:.4f}" if cost.get("cost_usd") else ""
                print(f"OK ({elapsed:.1f}s{cost_str})")
                _notify(_agent_label, f"{_step_label(step_name, 'done')} ({elapsed:.1f}s{cost_str})", phase=self.state.current_phase, project=self.project_slug, level="success")

                # 컨텍스트 메모리 수집 (에이전트 step만)
                if step.get("agent") and result.output_files:
                    try:
                        self.context_memory.collect_after_step(
                            step_id=step_id,
                            agent_name=step["agent"],
                            output_files=result.output_files,
                        )
                    except Exception as mem_err:
                        print(f"    [WARN] 컨텍스트 메모리 수집 실패: {mem_err}")

                # 볼트 축적 (리서치 완료 후 자동 저장)
                if step.get("agent") == "research-orchestrator" and self.vault.enabled:
                    try:
                        self._vault_save_research(step, result)
                    except Exception as vault_err:
                        print(f"    [WARN] 볼트 축적 실패: {vault_err}")

                # Supabase 동기화
                if self.sync:
                    try:
                        self.sync.sync_step(
                            step=step,
                            phase=self.state.current_phase,
                            status="completed",
                            output_files=result.output_files or [],
                            cost_info=cost,
                            project_data=dict(self.project),
                            duration_sec=elapsed,
                        )
                        print(f"    [SYNC] Supabase 동기화 완료")
                    except Exception as sync_err:
                        print(f"    [WARN] Supabase 동기화 실패: {sync_err}")
            else:
                self.pm.fail_pipeline_run(run_id, result.error)
                print(f"FAIL ({elapsed:.1f}s) — {result.error[:80]}")
                _notify(_agent_label, f"{_step_label(step_name, 'fail')}: {result.error[:60]}", phase=self.state.current_phase, project=self.project_slug, level="error")

            return result

        except Exception as e:
            elapsed = time.time() - t0
            self.pm.fail_pipeline_run(run_id, str(e))
            print(f"ERROR ({elapsed:.1f}s) — {e}")
            _notify(_agent_label, f"{_step_label(step_name, 'fail')}: {str(e)[:60]}", phase=self.state.current_phase, project=self.project_slug, level="error")
            return StepResult(step_id=step_id, status="failed",
                              duration_sec=elapsed, error=str(e))

    def _run_single_call_step(self, step: dict) -> StepResult:
        """단일 호출 step → 향후 Anthropic API 직접 호출로 전환.

        설계 의도:
          - 입력 파일을 Python이 읽어서 프롬프트에 주입
          - LLM 1회 호출로 결과 JSON 생성
          - Python이 결과를 파싱하여 파일 저장
          - 에이전트 루프(Read/Write 도구) 오버헤드 제거

        현재(초안): CLI 에이전트로 폴백 실행.
        최적화 시: _run_single_call_api() 구현 후 전환.

        single_call_model 필드:
          - claude-opus-4-6: 창작/판단이 필요한 복잡한 작업
          - claude-sonnet-4-5-20250929: 구조화된 추출/검증 작업
        """
        step_id = step["id"]
        target_model = step.get("single_call_model", "claude-opus-4-6")

        # TODO: API 직접 호출 구현 시 여기서 분기
        # if self._api_mode_enabled():
        #     return self._run_single_call_api(step, target_model)

        # 초안: CLI 에이전트로 폴백 (model은 agent 정의를 따름)
        print(f"[single_call→CLI] ", end="", flush=True)
        return self._run_agent_step(step)

    def _run_agent_step(self, step: dict) -> StepResult:
        """에이전트 step → Claude CLI 서브프로세스 호출.

        기본 실행 방식은 CLI (`claude` 바이너리).
        에이전트 루프(multi-turn tool_use)가 필요한 작업은 CLI에서 처리.
        웹 대시보드의 단순 수정만 Anthropic API 단일 호출 사용.
        """
        step_id = step["id"]
        agent = step["agent"]
        outputs = step.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        # 출력 파일이 이미 존재하면 스킵 (resume 지원)
        # 단, 입력과 출력이 동일한 파일인 경우(in-place 업데이트)는 스킵하지 않음
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        input_set = set(inputs)
        has_inplace_output = any(out in input_set for out in outputs)

        if not has_inplace_output:
            all_exist = True
            for out in outputs:
                out_path = self._resolve_output_path(out)
                if "{" in out:
                    parent = out_path.parent
                    if not (parent.exists() and any(parent.iterdir())):
                        all_exist = False
                        break
                elif not out_path.exists():
                    all_exist = False
                    break

            if all_exist and outputs:
                return StepResult(
                    step_id=step_id, status="completed",
                    output_files=[str(self._resolve_output_path(o)) for o in outputs],
                )

        # ── Claude CLI 서브프로세스 실행 ──

        # 1. 에이전트 설정
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent, {})
        if not agent_def:
            return StepResult(
                step_id=step_id, status="failed",
                error=f"agents.json에 '{agent}' 정의 없음",
            )

        model = agent_def.get("model", "claude-sonnet-4-5-20250929")
        max_turns = agent_def.get("max_turns", 30)
        allowed_tools = agent_def.get("allowed_tools", ["Read", "Write", "Glob"])
        budget = self._get_agent_budget(agent)
        timeout_sec = self._get_agent_timeout(agent)

        # 2. 프롬프트 빌드 (컨텍스트 메모리 포함)
        prompt = self._build_agent_prompt(step)

        # 3. 프롬프트를 임시 파일에 저장 (긴 프롬프트 대비)
        prompt_file = self.project_dir / f".prompt_{step_id}.md"
        prompt_file.write_text(prompt, encoding="utf-8")

        # 4. Claude CLI 명령 구성
        cli_path = self._find_claude_cli()
        cmd = [
            cli_path,
            "--print",
            "--output-format", "json",
            "--model", model,
            "--max-turns", str(max_turns),
        ]

        # 허용 도구 설정
        for tool in allowed_tools:
            cmd.extend(["--allowedTools", tool])

        print(f"\n    → CLI {agent} (model={model}, max_turns={max_turns}, "
              f"budget=${budget})", flush=True)

        # 5. 서브프로세스 실행 (Popen + 프로그레스 모니터링)
        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        # Claude Code 중첩 세션 방지 해제
        env.pop("CLAUDECODE", None)

        progress_path = self.project_dir / f".progress_{step_id}.jsonl"
        env["PROGRESS_FILE"] = str(progress_path)
        monitor = ProgressFileMonitor(progress_path, self.project_slug, self.state.current_phase)
        monitor.start()

        # 프롬프트를 stdin으로 전달
        prompt_text = prompt_file.read_text(encoding="utf-8")

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(input=prompt_text, timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return StepResult(
                    step_id=step_id, status="failed",
                    error=f"Claude CLI 타임아웃 ({timeout_sec}s)",
                )

            # subprocess.run 호환 객체 생성
            class _Result:
                pass
            result = _Result()
            result.stdout = stdout
            result.stderr = stderr
            result.returncode = proc.returncode

        except FileNotFoundError:
            return StepResult(
                step_id=step_id, status="failed",
                error="Claude CLI를 찾을 수 없습니다.",
            )
        finally:
            monitor.stop()
            prompt_file.unlink(missing_ok=True)

        # 6. 비용 정보 파싱
        cost_info = self._parse_claude_cost(result.stdout, result.stderr)

        # 7. 출력 파일 확인
        missing = []
        found = []
        for out in outputs:
            out_path = self._resolve_output_path(out)
            if "{" in out:
                parent = out_path.parent
                if parent.exists() and any(parent.iterdir()):
                    found.append(str(parent))
                else:
                    missing.append(out)
            elif out_path.exists():
                found.append(str(out_path))
            else:
                missing.append(out)

        if result.returncode == 0 and not missing:
            return StepResult(
                step_id=step_id, status="completed",
                output_files=found, cost_info=cost_info,
            )
        elif missing:
            detail = result.stderr[:300] if result.stderr else result.stdout[:300] if result.stdout else ""
            return StepResult(
                step_id=step_id, status="failed",
                error=f"출력 파일 미생성: {missing}. "
                      f"exit_code={result.returncode}. {detail}",
                cost_info=cost_info,
            )
        else:
            error = result.stderr[:500] or result.stdout[-500:]
            return StepResult(
                step_id=step_id, status="failed",
                error=f"CLI exit {result.returncode}: {error}",
                cost_info=cost_info,
            )

    def _run_module_step(self, step: dict) -> StepResult:
        """모듈 step → Python 스크립트 또는 shell 명령 실행."""
        step_id = step["id"]
        module_name = step["module"]

        # 환경변수로 프로젝트 config 주입
        # 스크립트들은 PROJECT_NAME → DB 조회로 config를 읽지만,
        # voice_id는 .env 폴백도 있으므로 env로도 주입
        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug

        config = self.state.config
        if config.get("voice_id"):
            env["ELEVENLABS_VOICE_ID"] = config["voice_id"]
        if config.get("voice_settings"):
            env["ELEVENLABS_VOICE_SETTINGS"] = json.dumps(config["voice_settings"])

        # 모듈별 스크립트 매핑 (PACKAGE_DIR 기준)
        script_map = {
            "preflight": "scripts/preflight_check.py",
            "duplicate-checker": "scripts/duplicate_check.py",
            "tts-preprocess": "tools/korean_tts_preprocessor.py",
            "tts-generator": "scripts/generate_tts.py",
            "image-generator": "scripts/generate_images.py",
            "subtitle-sync": "scripts/generate_subtitles.py",
            "tts-verifier": "scripts/verify_tts.py",
            "data-validator": "scripts/validate_data.py",
            "manifest-builder": "scripts/build_manifest.py",
            "layout-check": "scripts/layout_check.py",
            "video-assembler": None,  # shell command
        }

        if module_name == "video-assembler":
            return self._run_shell_command(step, env)

        script = script_map.get(module_name)
        if not script:
            return StepResult(
                step_id=step_id, status="failed",
                error=f"Unknown module: {module_name}",
            )

        script_path = PACKAGE_DIR / script
        if not script_path.exists():
            return StepResult(
                step_id=step_id, status="failed",
                error=f"Script not found: {script_path}",
            )

        # 프로그레스 모니터 설정
        progress_path = self.project_dir / f".progress_{step_id}.jsonl"
        env["PROGRESS_FILE"] = str(progress_path)
        monitor = ProgressFileMonitor(progress_path, self.project_slug, self.state.current_phase)
        monitor.start()

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(get_workspace_dir()),
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10분 타임아웃
            )

            if result.returncode == 0:
                return StepResult(step_id=step_id, status="completed")
            else:
                error = result.stderr[:500] or result.stdout[-500:]
                return StepResult(
                    step_id=step_id, status="failed",
                    error=f"Exit code {result.returncode}: {error}",
                )
        except subprocess.TimeoutExpired:
            return StepResult(
                step_id=step_id, status="failed",
                error="Timeout (600s)",
            )
        finally:
            monitor.stop()

    def _run_shell_command(self, step: dict, env: dict) -> StepResult:
        """shell 명령 실행 (video-assembler 등)."""
        step_id = step["id"]
        command = step.get("command", "")
        if not command:
            return StepResult(step_id=step_id, status="failed",
                              error="No command specified")

        # 플레이스홀더 치환
        command = command.replace("{project}", self.project_slug)
        command = command.replace("{composition}", self._resolve_composition())

        try:
            result = subprocess.run(
                command, shell=True,
                cwd=str(get_workspace_dir()),
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,  # 30분 (렌더링)
            )

            if result.returncode == 0:
                return StepResult(step_id=step_id, status="completed")
            else:
                error = result.stderr[:500] or result.stdout[-500:]
                return StepResult(
                    step_id=step_id, status="failed",
                    error=f"Exit code {result.returncode}: {error}",
                )
        except subprocess.TimeoutExpired:
            return StepResult(
                step_id=step_id, status="failed",
                error="Timeout (1800s)",
            )

    # ─────────────────────────────────────
    # 헬퍼
    # ─────────────────────────────────────

    def _vault_save_research(self, step: dict, result) -> None:
        """리서치 완료 후 research_report.json에서 핵심 데이터를 볼트에 축적."""
        report_path = self.project_dir / "research_report.json"
        if not report_path.exists():
            return

        report = json.loads(report_path.read_text(encoding="utf-8"))
        topic = report.get("topic", self.project_slug)
        category = self.vault._detect_category(topic)

        # 요약 추출
        summary = report.get("summary", "")[:500]

        # 핵심 팩트 추출
        key_facts = []
        for ep in report.get("episodes", [])[:10]:
            for fact in ep.get("must_include", [])[:3]:
                key_facts.append(fact)
        # 통계
        for stat in report.get("statistics", [])[:5]:
            key_facts.append(f"{stat.get('label', '')}: {stat.get('value', '')}")

        # 소스 추출
        sources = []
        for src in report.get("sources", [])[:10]:
            sources.append(f"[{src.get('grade', '')}] {src.get('title', '')} — {src.get('url', '')}")

        self.vault.save_research_result(
            topic=topic,
            category=category,
            summary=summary,
            key_facts=key_facts,
            sources=sources,
        )
        print(f"    [VaultRAG] 리서치 결과 볼트 축적 완료: {topic}")

    def _find_claude_cli(self) -> str:
        """Claude CLI 바이너리 경로 탐색."""
        # 1. 환경변수 오버라이드
        env_cli = os.environ.get("CLAUDE_CLI")
        if env_cli and Path(env_cli).exists():
            return env_cli
        # 2. PATH에서 탐색
        result = shutil.which("claude")
        if result:
            return result
        raise FileNotFoundError(
            "Claude CLI를 찾을 수 없습니다. "
            "PATH에 claude가 있는지 확인하거나 CLAUDE_CLI 환경변수를 설정하세요."
        )

    def _build_agent_prompt(self, step: dict) -> str:
        """에이전트 호출용 자기 완결적 프롬프트 구성.

        SKILL.md + 공유 스킬 + 입출력 경로 + 프로젝트 컨텍스트를 결합.
        """
        agent_name = step["agent"]

        # 1. Agent SKILL.md 읽기
        skill_path = DATA_DIR / "skills" / "agents" / agent_name / "SKILL.md"
        agent_skill = ""
        if skill_path.exists():
            agent_skill = skill_path.read_text(encoding="utf-8")

        # 2. 공유 스킬 수집 (step + agents.json 병합, 중복 제거)
        skill_names = list(step.get("skills", []))
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        for s in agent_def.get("skills", []):
            if s not in skill_names:
                skill_names.append(s)

        # skill_refs: 에이전트별 필요한 references만 선택 로드
        skill_refs = agent_def.get("skill_refs", {})

        shared_skills_text = ""
        for skill_name in skill_names:
            # 1) 디렉토리 스킬 (shared/{name}/SKILL.md + references/)
            skill_dir = DATA_DIR / "skills" / "shared" / skill_name
            if (skill_dir / "SKILL.md").exists():
                content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
                # skill_refs에 지정된 references만 로드 (없으면 전체)
                refs_to_load = skill_refs.get(skill_name)
                ref_dir = skill_dir / "references"
                if ref_dir.exists():
                    if refs_to_load is not None:
                        # 지정된 파일만
                        for ref_name in refs_to_load:
                            ref_file = ref_dir / f"{ref_name}.md"
                            if ref_file.exists():
                                content += f"\n\n{ref_file.read_text(encoding='utf-8')}"
                    else:
                        # 전체 references 로드 (하위 호환)
                        for ref_file in sorted(ref_dir.glob("*.md")):
                            content += f"\n\n{ref_file.read_text(encoding='utf-8')}"
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"
                continue

            # 2) 플랫 파일 (shared/{name}.md — 레거시)
            skill_file = DATA_DIR / "skills" / "shared" / f"{skill_name}.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"
                continue

            # 3) 루트 레벨 (skills/{name}.md — 레거시 호환)
            skill_file_root = DATA_DIR / "skills" / f"{skill_name}.md"
            if skill_file_root.exists():
                content = skill_file_root.read_text(encoding="utf-8")
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"

        # 3. 입력 파일 경로
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        # 선택적 입력도 포함
        optional_inputs = step.get("input_optional", [])
        if isinstance(optional_inputs, str):
            optional_inputs = [optional_inputs]

        input_lines = []
        for inp in inputs:
            resolved = self._resolve_output_path(inp)
            tag = "✓" if resolved.exists() else "✗ MISSING"
            input_lines.append(f"- {inp}: {resolved} [{tag}]")
        for inp in optional_inputs:
            resolved = self._resolve_output_path(inp)
            tag = "✓" if resolved.exists() else "없음 (선택)"
            input_lines.append(f"- {inp}: {resolved} [{tag}]")

        # 4. 출력 파일 경로
        outputs = step.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]
        output_lines = []
        for out in outputs:
            resolved = self._resolve_output_path(out)
            output_lines.append(f"- {out}: {resolved}")

        # 5. 컨텍스트 메모리 주입
        context_memory_block = self.context_memory.build_context_prompt(
            step.get("id", "")
        )

        # 6. 볼트 지식 주입 (Vault RAG)
        vault_block = ""
        if self.vault.enabled:
            topic = self.state.config.get("topic", self.project_slug)
            category = self.vault._detect_category(topic)
            if agent_name in ("research-orchestrator",):
                vault_block = self.vault.search_for_research(topic, category)
            elif agent_name in ("write-manuscript",):
                vault_block = self.vault.search_for_manuscript(topic, category)

        # 7. 프롬프트 조립
        prompt = f"""<system_context>
프로젝트: {self.project_slug}
작업 디렉토리: {self.project_dir}
워크스페이스: {get_workspace_dir()}
</system_context>

<agent_skill>
{agent_skill}
</agent_skill>

<shared_skills>
{shared_skills_text}
</shared_skills>

{vault_block}

<task>
Step: {step.get("id", "")} — {step.get("name", "")}
{step.get("description", "")}
{step.get("notes", "")}

입력 파일:
{chr(10).join(input_lines) if input_lines else "- 없음"}

출력 파일 (반드시 아래 경로에 저장):
{chr(10).join(output_lines)}

모든 출력 파일을 성공적으로 생성하면 작업 완료입니다.
</task>

<progress_reporting>
작업 진행 상황을 아래 파일에 기록하세요. 대시보드 메신저에 실시간으로 표시됩니다.
파일 경로: {self.project_dir / f".progress_{step.get('id', '')}.jsonl"}

Write 도구로 기록하되, 기존 내용 뒤에 append하세요 (기존 내용을 지우지 마세요).
한 줄에 하나의 JSON:
{{"agent": "에이전트이름", "text": "자연어 메시지", "level": "info"}}

level: "info" (일반), "success" (완료/성과), "warning" (주의사항)

보고 시점과 내용:
1. 작업 시작 → 무엇을 하려는지 ("코카콜라 초기 역사 리서치 시작")
2. 병렬 태스크 배포 시 → 몇 개를 어떤 주제로 배포했는지
3. 병렬 태스크가 하나씩 완료될 때마다 → 해당 태스크의 핵심 발견 서머리
   예: {{"agent": "Explorer-1", "text": "초기 역사: 1886년 존 펨버턴이 발명, 약국에서 5센트에 판매 — 에피소드 3개", "level": "success"}}
   예: {{"agent": "Explorer-3", "text": "마케팅: 산타클로스 캠페인(1931), I'd Like to Buy the World a Coke(1971) — 에피소드 4개", "level": "success"}}
4. 전체 완료 시 → 통합 결과 요약 ("리서치 완료: 에피소드 12개, 통계 8건, 주요인물 5명")
5. 실패/재시도 시 → 무슨 문제인지, 어떻게 대응하는지

중요: 병렬 서브태스크(Task 도구)를 사용할 때, 각 태스크가 완료되면 즉시 해당 결과를 progress 파일에 기록하세요.
톤: 자연어로 간결하게. 기술적 명령어나 파일 경로 대신 사람이 읽을 수 있는 내용 위주.
</progress_reporting>

{context_memory_block}"""
        return prompt

    def _load_agents_config(self) -> dict:
        """agents.json 로드 (캐시)."""
        if not hasattr(self, "_agents_cache"):
            path = DATA_DIR / "agents.json"
            with open(path, "r", encoding="utf-8") as f:
                self._agents_cache = json.load(f)
        return self._agents_cache

    def _get_agent_budget(self, agent_name: str) -> float:
        """pipeline.json에서 에이전트 예산 한도(USD) 조회."""
        limits = self.pipeline.get("gateway", {}).get("agent_limits", {})
        return limits.get(agent_name, {}).get("budget_usd", 3.0)

    def _get_agent_timeout(self, agent_name: str) -> int:
        """pipeline.json에서 에이전트 타임아웃(초) 조회."""
        limits = self.pipeline.get("gateway", {}).get("agent_limits", {})
        max_min = limits.get(agent_name, {}).get("max_duration_min", 15)
        return max_min * 60

    def _resolve_composition(self) -> str:
        """프로젝트 theme에 따른 Remotion Composition ID 반환."""
        theme = self.project.get("theme", "simple")
        return {"simple": "SimpleVideo", "kairos": "KairosVideo"}.get(
            theme, "SimpleVideo"
        )

    def _parse_claude_cost(self, stdout: str, stderr: str) -> dict:
        """Claude CLI 출력에서 비용 정보 파싱."""
        cost_info = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

        # JSON 모드 (--output-format json)
        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                usage = data.get("usage", {})
                cost_info["tokens_in"] = usage.get("input_tokens", 0)
                cost_info["tokens_out"] = usage.get("output_tokens", 0)
                cost_info["cost_usd"] = data.get("cost_usd", 0.0)
                model = data.get("model", "")
                if cost_info["cost_usd"] == 0 and cost_info["tokens_in"] > 0:
                    cost_info["cost_usd"] = self._estimate_cost(
                        cost_info["tokens_in"], cost_info["tokens_out"], model
                    )
                return cost_info
        except (json.JSONDecodeError, TypeError):
            pass

        # Text 모드 폴백: stderr/stdout에서 정규식 파싱
        combined = stdout + "\n" + stderr
        m_in = re.search(r"[Ii]nput\s+tokens?[:\s]+(\d[\d,]*)", combined)
        if m_in:
            cost_info["tokens_in"] = int(m_in.group(1).replace(",", ""))
        m_out = re.search(r"[Oo]utput\s+tokens?[:\s]+(\d[\d,]*)", combined)
        if m_out:
            cost_info["tokens_out"] = int(m_out.group(1).replace(",", ""))
        m_cost = re.search(r"[Cc]ost[:\s]+\$?([\d.]+)", combined)
        if m_cost:
            cost_info["cost_usd"] = float(m_cost.group(1))
        elif cost_info["tokens_in"] > 0:
            cost_info["cost_usd"] = self._estimate_cost(
                cost_info["tokens_in"], cost_info["tokens_out"], ""
            )
        return cost_info

    # 모델별 토큰 가격 (USD per 1M tokens)
    _PRICING = {
        "claude-sonnet-4-5-20250929": (3.0, 15.0),
        "claude-haiku-4-5-20251001": (0.80, 4.0),
        "claude-opus-4-5-20250514": (15.0, 75.0),
    }

    @staticmethod
    def _estimate_cost(tokens_in: int, tokens_out: int, model: str) -> float:
        """모델별 토큰 가격으로 비용 추정 (USD)."""
        price_in, price_out = PipelineRunner._PRICING.get(
            model, (3.0, 15.0)  # Sonnet 기본값
        )
        return (tokens_in * price_in + tokens_out * price_out) / 1_000_000

    def _resolve_output_path(self, output_template: str) -> Path:
        """output 경로 템플릿 해석. {project} → slug 치환."""
        resolved = output_template.replace("{project}", self.project_slug)
        path = Path(resolved)
        if not path.is_absolute():
            # output/ 접두사가 있으면 프로젝트 루트 기준
            if resolved.startswith("output/"):
                return PROJECT_ROOT / resolved
            # 그 외는 프로젝트 디렉토리 기준
            return self.project_dir / resolved
        return path

    def _check_condition(self, step: dict) -> bool:
        """conditional step의 실행 조건 확인.

        pipeline.json의 condition_check 필드를 사용:
          - {"type": "file_exists", "path": "final_manuscript.md"}
          - {"type": "json_field_exists", "path": "scene_specs.json",
             "field": "scenes[].imageAsset"}

        condition_check가 없으면 입력 파일 존재 여부로 판단.
        """
        check = step.get("condition_check")

        if check:
            check_type = check.get("type", "")

            if check_type == "file_exists":
                target = self.project_dir / check["path"]
                return target.exists()

            if check_type == "json_field_exists":
                target = self.project_dir / check["path"]
                if not target.exists():
                    return False
                data = json.loads(target.read_text(encoding="utf-8"))
                field = check.get("field", "")
                # "scenes[].imageAsset" → scenes 배열 내 아무 원소에 imageAsset이 있으면 True
                if "[]." in field:
                    array_key, item_key = field.split("[].", 1)
                    items = data.get(array_key, [])
                    return any(item.get(item_key) for item in items)
                # 단순 키
                return bool(data.get(field))

        # condition_check 미정의 → 입력 파일 존재 여부로 폴백
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        for inp in inputs:
            resolved = self._resolve_output_path(inp)
            if resolved.exists():
                return True

        return True  # 입력 정보도 없으면 실행

    def _check_checkpoint(self, phase_id: str, steps: List[dict]):
        """checkpoint 확인. 인터랙티브 모드에서 사용자 검토 유도."""
        checkpoints = self.pipeline.get("checkpoints", {}).get("points", [])
        for cp in checkpoints:
            after_step = cp.get("after_step", "")
            if any(s["id"] == after_step for s in steps):
                if after_step in self.state.completed_steps:
                    print(f"\n  ★ CHECKPOINT: {cp['name']}")
                    print(f"    {cp['description']}")
                    print()

    def _finish(self):
        """파이프라인 완료 처리."""
        completed = len(self.state.completed_steps)
        failed = len(self.state.failed_steps)
        skipped = len(self.state.skipped_steps)
        total = completed + failed + skipped

        # 비용 요약
        cost_summary = self.pm.get_cost_summary(self.project["id"])
        total_usd = cost_summary.get("total_usd") or 0

        print(f"\n{'=' * 60}")
        print(f"Pipeline Complete")
        print(f"  Completed: {completed}/{total}")
        print(f"  Failed:    {failed}")
        print(f"  Skipped:   {skipped}")
        if total_usd > 0:
            print(f"  Cost:      ${total_usd:.4f}")
            print(f"  Tokens In: {cost_summary.get('total_tokens_in', 0):,}")
            print(f"  Tokens Out:{cost_summary.get('total_tokens_out', 0):,}")
        print(f"{'=' * 60}")

        # 메신저 알림
        level = "success" if failed == 0 else "warning"
        cost_str = f" (${total_usd:.4f})" if total_usd > 0 else ""
        _notify("Director", f"파이프라인 완료 — {completed}/{total} 성공{cost_str}", phase="pipeline", project=self.project_slug, level=level)

        # 상태 파일 저장
        state_path = self.project_dir / "pipeline_state.json"
        state_data = {
            "project_slug": self.project_slug,
            "started_at": self.state.started_at,
            "finished_at": datetime.now().isoformat(),
            "config": self.state.config,
            "completed_steps": self.state.completed_steps,
            "failed_steps": self.state.failed_steps,
            "skipped_steps": self.state.skipped_steps,
            "results": self.state.results,
        }
        state_path.write_text(
            json.dumps(state_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\nState saved: {state_path}")

        # 프로젝트 상태 업데이트
        if failed == 0:
            self.pm.update_project(self.project["id"], status="completed")
        else:
            self.pm.update_project(self.project["id"], status="failed")


# ═══════════════════════════════════════
# CLI 진입점
# ═══════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline Orchestrator Runner")
    parser.add_argument("--project", required=True, help="프로젝트 slug")
    parser.add_argument("--from", dest="from_step", help="이 step부터 실행")
    parser.add_argument("--only", dest="only_step", help="이 step만 실행")
    parser.add_argument("--dry-run", action="store_true", help="실행하지 않고 계획만 출력")
    args = parser.parse_args()

    runner = PipelineRunner(args.project)
    runner.run(
        from_step=args.from_step,
        only_step=args.only_step,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
