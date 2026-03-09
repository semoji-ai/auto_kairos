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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from auto_agent.paths import get_workspace_dir, get_data_dir, PACKAGE_DIR, DATA_DIR

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
        self.project_dir = Path(self.project["output_dir"])

    def _load_pipeline(self) -> dict:
        path = DATA_DIR / "pipeline.json"
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _get_project_manager(self):
        from auto_agent.db.project_manager import ProjectManager
        return ProjectManager()

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
                # gate step이면 파이프라인 중단
                if step.get("gate"):
                    print(f"\n  GATE FAILED: {step['id']} — 파이프라인 중단")
                    self.state.failed_steps.append(step["id"])
                    return
                # non-blocking이면 계속
                if step.get("blocking") is False:
                    print(f"  [WARN] {step['id']} failed (non-blocking) — 계속 진행")
                    self.state.failed_steps.append(step["id"])
                else:
                    print(f"\n  STEP FAILED: {step['id']} — 파이프라인 중단")
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

        self.state.current_step = step_id
        print(f"  [{step_id}] {step_name} ... ", end="", flush=True)

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
            if step.get("agent"):
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
            else:
                self.pm.fail_pipeline_run(run_id, result.error)
                print(f"FAIL ({elapsed:.1f}s) — {result.error[:80]}")

            return result

        except Exception as e:
            elapsed = time.time() - t0
            self.pm.fail_pipeline_run(run_id, str(e))
            print(f"ERROR ({elapsed:.1f}s) — {e}")
            return StepResult(step_id=step_id, status="failed",
                              duration_sec=elapsed, error=str(e))

    def _run_agent_step(self, step: dict) -> StepResult:
        """에이전트 step → Claude Code CLI 호출."""
        step_id = step["id"]
        agent = step["agent"]
        outputs = step.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        # 출력 파일이 이미 존재하면 스킵 (resume 지원)
        all_exist = True
        for out in outputs:
            out_path = self._resolve_output_path(out)
            # 와일드카드 패턴 ({N} 등)은 디렉토리 존재로 판단
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

        # ── Claude CLI 실행 ──

        # 1. CLI 경로
        try:
            cli_path = self._find_claude_cli()
        except FileNotFoundError as e:
            return StepResult(step_id=step_id, status="failed", error=str(e))

        # 2. 에이전트 설정
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

        # 3. 프롬프트 빌드
        prompt = self._build_agent_prompt(step)

        # 4. CLI 명령 구성 (항상 stdin pipe 사용 — 셸 인자 길이 제한 회피)
        cmd = [
            cli_path,
            "--model", model,
            "--max-turns", str(max_turns),
            "--output-format", "json",
            "--allowedTools", ",".join(allowed_tools),
            "--dangerously-skip-permissions",
            "-p", "-",
        ]
        if budget > 0:
            cmd.extend(["--max-budget-usd", str(budget)])

        # 5. 환경변수
        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        config = self.state.config
        if config.get("voice_id"):
            env["ELEVENLABS_VOICE_ID"] = config["voice_id"]
        if config.get("voice_settings"):
            env["ELEVENLABS_VOICE_SETTINGS"] = json.dumps(
                config["voice_settings"]
            )

        # 6. 실행
        print(f"\n    → claude {agent} (model={model}, max_turns={max_turns}, "
              f"budget=${budget})", flush=True)

        process = None
        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(get_workspace_dir()),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate(
                input=prompt, timeout=timeout_sec
            )

            # 7. 비용 파싱
            cost_info = self._parse_claude_cost(stdout, stderr)

            # 8. 출력 파일 확인
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

            if process.returncode == 0 and not missing:
                return StepResult(
                    step_id=step_id, status="completed",
                    output_files=found, cost_info=cost_info,
                )
            elif missing:
                return StepResult(
                    step_id=step_id, status="failed",
                    error=f"출력 파일 미생성: {missing}. "
                          f"exit={process.returncode}",
                    cost_info=cost_info,
                )
            else:
                err_tail = stderr[-500:] if stderr else stdout[-500:]
                return StepResult(
                    step_id=step_id, status="failed",
                    error=f"Exit code {process.returncode}: {err_tail}",
                    cost_info=cost_info,
                )

        except subprocess.TimeoutExpired:
            if process:
                process.kill()
                process.wait()
            return StepResult(
                step_id=step_id, status="failed",
                error=f"Timeout ({timeout_sec}s = {timeout_sec // 60}min)",
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

        try:
            # --project argv 대신 PROJECT_NAME env로 통일
            # project_paths.py가 env를 2순위로 읽으므로 안전
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

        shared_skills_text = ""
        for skill_name in skill_names:
            skill_file = DATA_DIR / "skills" / f"{skill_name}.md"
            if skill_file.exists():
                content = skill_file.read_text(encoding="utf-8")
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

        # 5. 프롬프트 조립
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

<task>
Step: {step.get("id", "")} — {step.get("name", "")}
{step.get("description", "")}
{step.get("notes", "")}

입력 파일:
{chr(10).join(input_lines) if input_lines else "- 없음"}

출력 파일 (반드시 아래 경로에 저장):
{chr(10).join(output_lines)}

모든 출력 파일을 성공적으로 생성하면 작업 완료입니다.
</task>"""
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

    def _estimate_cost(
        self, tokens_in: int, tokens_out: int, model: str
    ) -> float:
        """모델별 토큰 가격으로 비용 추정 (USD)."""
        pricing = {
            "opus": {"input": 15.0, "output": 75.0},
            "sonnet": {"input": 3.0, "output": 15.0},
            "haiku": {"input": 0.8, "output": 4.0},
        }
        model_lower = model.lower()
        for key, prices in pricing.items():
            if key in model_lower:
                return (
                    tokens_in * prices["input"]
                    + tokens_out * prices["output"]
                ) / 1_000_000
        # 알 수 없는 모델 → sonnet 기준
        return (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000

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
