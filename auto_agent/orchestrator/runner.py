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
    """파이프라인 진행 상황을 대시보드 메신저로 전송. 파일 영속 + HTTP POST."""
    import time as _time
    msg = {
        "agent": agent, "text": text, "phase": phase,
        "project": project, "level": level, "data": data or {},
        "timestamp": _time.time(),
    }
    # 1. 파일 영속 저장 (대시보드 꺼져 있어도 유지)
    try:
        from auto_agent.paths import get_workspace_dir
        persist = get_workspace_dir() / ".auto_agent" / "agent_messages.jsonl"
        persist.parent.mkdir(parents=True, exist_ok=True)
        with open(persist, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # 2. HTTP POST로 실시간 SSE 전달 (대시보드 떠 있으면)
    try:
        import urllib.request
        payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
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

        # 중앙 규칙 관리자 초기화 + fetch
        from auto_agent.rule_manager import RuleManager
        from auto_agent.supabase_client import supabase_enabled
        self.rule_manager = RuleManager()
        if supabase_enabled():
            try:
                changed = self.rule_manager.fetch_all()
                if changed:
                    print(f"[Rules] 중앙 규칙 {changed}개 갱신됨")
            except Exception as e:
                print(f"[Rules] 중앙 규칙 fetch 실패 (로컬 fallback): {e}")

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
        """Supabase 동기화 — 파이프라인 중에는 비활성. 완료 후 프로젝트 단위로 동기화."""
        # 파이프라인 실행 중 매 스텝 동기화 비활성
        return None

    def _load_pipeline(self) -> dict:
        # 로컬 DATA_DIR 우선 (Supabase 캐시보다 로컬 수정 우선)
        path = DATA_DIR / "pipeline.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            return self.rule_manager.load_json("pipeline.json")
        except FileNotFoundError:
            raise FileNotFoundError("pipeline.json not found")

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

        # voice_id 미설정 시 writing_style에서 자동 매핑
        if not config.get("voice_id"):
            STYLE_VOICE_MAP = {
                "semoji": {"voice_id": "W7FnAxJNpD5WGjrF5GLp", "voice_settings": {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "speed": 1.1}},
                "iromism": {"voice_id": "9Sj8ugvpK1DmcAXyvi3a", "voice_settings": {"stability": 1.0, "similarity_boost": 0.6, "style": 0.9, "speed": 1.1}},
                "default": {"voice_id": "4JJwo477JUAx3HV0T7n7", "voice_settings": {"stability": 1.0, "similarity_boost": 0.9, "style": 0.9, "speed": 1.1}},
            }
            ws = config.get("writing_style", "default")
            voice = STYLE_VOICE_MAP.get(ws, STYLE_VOICE_MAP.get("default", {}))
            if voice:
                config["voice_id"] = voice["voice_id"]
                config["voice_settings"] = voice["voice_settings"]
                print(f"    voice_id 자동 설정: {ws} → {voice['voice_id']}")

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

            # blocking step 실패 시 전체 파이프라인 중단
            if self.state.failed_steps:
                blocking_fails = [s for s in self.state.failed_steps
                                  if not any(st.get("blocking") is False
                                             for st in steps if st["id"] == s)]
                if blocking_fails:
                    print(f"\n  *** 파이프라인 중단: {blocking_fails} 실패 ***")
                    break

            # phase 끝나면 checkpoint 확인
            self._check_checkpoint(phase_id, steps)

            if only_step:
                break

        self._finish()

    def _merge_research_outputs(self):
        """Explorer 산출물을 research_report.json으로 기계적 병합.

        2가지 구조 지원:
        1) RESEARCH/{session}/outputs/ + sources/ (deep-research-kit)
        2) 프로젝트 루트에 research_*.md 파일들 (간단 구조)
        """
        # === 최우선: RESEARCH 안에 이미 report가 있으면 루트에 복사 ===
        _research_dir = self.project_dir / "RESEARCH"
        if _research_dir.exists():
            for _sess in sorted([d for d in _research_dir.iterdir() if d.is_dir()], reverse=True):
                _existing = _sess / "research_report.json"
                if _existing.exists() and not (self.project_dir / "research_report.json").exists():
                    import shutil
                    shutil.copy(_existing, self.project_dir / "research_report.json")
                    # .md도 생성
                    _all_md = []
                    _outputs = _sess / "outputs"
                    if _outputs.exists():
                        for _md in sorted(_outputs.rglob("*.md")):
                            _all_md.append(_md.read_text(encoding="utf-8"))
                    if _all_md:
                        (self.project_dir / "research_report.md").write_text(
                            "\n\n---\n\n".join(_all_md), encoding="utf-8")
                    print(f"    [MERGE] RESEARCH 내부 report → 루트 복사 완료 ({len(_all_md)}섹션)")
                    return
                break
        research_dir = self.project_dir / "RESEARCH"
        sources = []
        sections = []
        agent_sections = []
        meta = {}

        # === 구조 1: RESEARCH/{session}/ ===
        if research_dir.exists():
            sessions = [d for d in sorted(research_dir.iterdir(), reverse=True) if d.is_dir()]
            if sessions:
                session = sessions[0]
                src_file = session / "sources" / "sources.jsonl"
                if src_file.exists():
                    for line in src_file.read_text(encoding="utf-8").strip().split("\n"):
                        if line.strip():
                            try: sources.append(json.loads(line))
                            except json.JSONDecodeError: pass
                outputs_dir = session / "outputs"
                if outputs_dir.exists():
                    for md_file in sorted(outputs_dir.glob("*.md")):
                        text = md_file.read_text(encoding="utf-8")
                        title = text.split("\n")[0].lstrip("# ").strip() if text else md_file.stem
                        sections.append({"title": title, "content": text})
                    full_report_dir = outputs_dir / "01_full_report"
                    if full_report_dir.exists():
                        for md_file in sorted(full_report_dir.glob("*.md")):
                            text = md_file.read_text(encoding="utf-8")
                            title = text.split("\n")[0].lstrip("# ").strip() if text else md_file.stem
                            sections.append({"title": title, "content": text})
                agent_results_dir = session / "artifacts" / "agent_results"
                if agent_results_dir.exists():
                    for md_file in sorted(agent_results_dir.glob("*.md")):
                        text = md_file.read_text(encoding="utf-8")
                        title = text.split("\n")[0].lstrip("# ").strip() if text else md_file.stem
                        agent_sections.append({"title": title, "content": text})
                state_file = session / "state.json"
                if state_file.exists():
                    try: meta = json.loads(state_file.read_text(encoding="utf-8"))
                    except json.JSONDecodeError: pass

        # === 구조 2: 루트 + RESEARCH/ 에 있는 .md 파일들 ===
        if not sections:
            seen = set()
            search_dirs = [self.project_dir]
            if research_dir.exists():
                search_dirs.append(research_dir)
            for search_dir_item in search_dirs:
                for pattern in ["research_*.md", "*_research*.md", "research*.md", "*리서치*.md", "deep_research*.md"]:
                    for md_file in sorted(search_dir_item.glob(pattern)):
                        if md_file.name in seen or md_file.name == "research_report.md":
                            continue
                        seen.add(md_file.name)
                        text = md_file.read_text(encoding="utf-8")
                        title = text.split("\n")[0].lstrip("# ").strip() if text else md_file.stem
                        sections.append({"title": title, "content": text})
            # RESEARCH/ 안에 아무 패턴에도 안 걸리는 .md도 포함
            if not sections and research_dir.exists():
                for md_file in sorted(research_dir.glob("*.md")):
                    if md_file.name in seen:
                        continue
                    seen.add(md_file.name)
                    text = md_file.read_text(encoding="utf-8")
                    title = text.split("\n")[0].lstrip("# ").strip() if text else md_file.stem
                    sections.append({"title": title, "content": text})

        # === CLI가 이미 research_report.json을 만들었으면 루트로 복사 ===
        if not sections and research_dir.exists():
            for session_dir in sorted([d for d in research_dir.iterdir() if d.is_dir()], reverse=True):
                existing_report = session_dir / "research_report.json"
                if existing_report.exists():
                    import shutil
                    shutil.copy(existing_report, self.project_dir / "research_report.json")
                    # .md도 생성
                    all_md = []
                    for md in sorted((session_dir / "outputs").rglob("*.md")) if (session_dir / "outputs").exists() else []:
                        all_md.append(md.read_text(encoding="utf-8"))
                    if all_md:
                        (self.project_dir / "research_report.md").write_text(
                            "\n\n---\n\n".join(all_md), encoding="utf-8")
                    print(f"    [MERGE] RESEARCH 내부 report 복사 완료")
                    return
                break

        if not sections:
            print("    [MERGE] 병합할 리서치 파일 없음")
            return

        # === 소스 추출: sections에서 출처/URL 파싱 ===
        if not sources:
            import re
            seen_urls = set()
            link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
            for sec in sections:
                for match in link_pattern.finditer(sec.get("content", "")):
                    title, url = match.group(1), match.group(2)
                    if url not in seen_urls:
                        seen_urls.add(url)
                        sources.append({"title": title, "url": url, "quality_grade": "B"})
            if sources:
                print(f"    [MERGE] .md에서 소스 {len(sources)}개 추출")

        # research_report.json 생성
        report = {
            "topic": meta.get("topic", self.project_slug),
            "summary": sections[0]["content"] if sections else "",
            "sections": sections,
            "agent_results": agent_sections,
            "sources": sources,
            "source_grades": {},
            "agents_deployed": meta.get("agents_deployed", 0),
            "search_mode": meta.get("search_mode", "unknown"),
        }
        # 소스 등급 집계
        for s in sources:
            grade = s.get("quality_grade", "?")
            report["source_grades"][grade] = report["source_grades"].get(grade, 0) + 1

        out_path = self.project_dir / "research_report.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # .md 버전도 생성 (대시보드 fallback용) — 전체 보고서 + Explorer 원본
        md_path = self.project_dir / "research_report.md"
        all_sections = sections + agent_sections
        md_text = "\n\n---\n\n".join(s["content"] for s in all_sections)
        md_path.write_text(md_text, encoding="utf-8")

        print(f"    [MERGE] research_report.json 생성 완료 ({len(sections)}섹션, {len(sources)}소스)")
        _notify("Runner", f"리서치 병합 완료: {len(sections)}섹션, {len(sources)}소스",
                phase=self.state.current_phase, project=self.project_slug, level="success")

    def _validate_step(self, step_id: str, result) -> StepResult:
        """사감독 역할: 단계 완료 후 산출물 검증 + 부족하면 Python 보완."""

        if step_id == "step_1":
            # 1) Python 병합
            report_path = self.project_dir / "research_report.json"
            if not report_path.exists():
                try:
                    self._merge_research_outputs()
                except Exception as e:
                    print(f"    [WARN] 리서치 병합 실패: {e}")

            if not report_path.exists():
                _notify("Director", "리서치 검증 실패: 보고서 없음",
                        phase=self.state.current_phase, project=self.project_slug, level="error")
                return StepResult(step_id=step_id, status="failed", error="research_report.json 미생성")

            # 2) 구조 검증
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
                sections = len(data.get("sections", []))
                sources = len(data.get("sources", []))
                if sections == 0:
                    return StepResult(step_id=step_id, status="failed", error="리서치 섹션 0개")
            except Exception:
                return StepResult(step_id=step_id, status="failed", error="research_report.json 파싱 실패")

            # 3) 내용 검증: 주제와 일치하는지 LLM 판단
            topic = self.state.config.get("topic", self.project_slug)
            summary = data.get("summary", "")[:500]
            section_titles = [s.get("title", "") for s in data.get("sections", [])][:10]

            verify_prompt = (
                f"프로젝트 주제: {topic}\n\n"
                f"리서치 요약:\n{summary}\n\n"
                f"섹션 제목: {', '.join(section_titles)}\n\n"
                f"이 리서치가 프로젝트 주제에 적합한지 판단하세요.\n"
                f"JSON으로만 답하세요: {{\"valid\": true/false, \"reason\": \"한줄 사유\"}}"
            )
            try:
                cli_path = self._find_claude_cli()
                proc = subprocess.run(
                    [cli_path, "--print", "--output-format", "json",
                     "--model", "claude-haiku-4-5-20251001", "--max-turns", "1"],
                    input=verify_prompt, capture_output=True, text=True,
                    cwd=str(self.project_dir), timeout=30,
                    env={**os.environ, "CLAUDECODE": ""},
                )
                verify_result = self._extract_json_from_cli_output(proc.stdout)
                if verify_result and verify_result.get("valid"):
                    reason = verify_result.get("reason", "")
                    print(f"    [검증] 리서치: {sections}섹션, {sources}소스, 주제 일치 ✓ ({reason})")
                    _notify("Director", f"리서치 검증 통과: {sections}섹션, {sources}소스 — {reason}",
                            phase=self.state.current_phase, project=self.project_slug, level="success")
                    # 볼트 기록
                    if self.vault.enabled:
                        try:
                            self._vault_save_research({"agent": "research-orchestrator"}, result)
                        except Exception as ve:
                            print(f"    [WARN] 볼트 축적 실패: {ve}")
                    return StepResult(step_id=step_id, status="completed")
                elif verify_result:
                    reason = verify_result.get("reason", "주제 불일치")
                    print(f"    [검증] 리서치: 주제 불일치 ✗ ({reason})")
                    return StepResult(step_id=step_id, status="failed", error=f"리서치 주제 불일치: {reason}")
            except Exception as e:
                print(f"    [WARN] LLM 검증 실패 ({e}), 구조 검증만 통과")

            # LLM 검증 실패해도 구조 검증 통과면 진행
            print(f"    [검증] 리서치: {sections}섹션, {sources}소스 ✓ (구조 검증)")
            _notify("Director", f"리서치 검증: {sections}섹션, {sources}소스",
                    phase=self.state.current_phase, project=self.project_slug, level="success")
            return StepResult(step_id=step_id, status="completed")

        elif step_id == "step_2":
            # 원고 검증: final_manuscript.md 존재 + 글자 수
            ms_path = self.project_dir / "final_manuscript.md"
            if ms_path.exists():
                text = ms_path.read_text(encoding="utf-8")
                chars = len(text)
                has_scene_marker = "## Scene" in text
                print(f"    [검증] 원고: {chars}자, 씬마커={'있음 ✗' if has_scene_marker else '없음 ✓'}")
                _notify("Director", f"원고 검증: {chars}자",
                        phase=self.state.current_phase, project=self.project_slug, level="success")
            else:
                return StepResult(step_id=step_id, status="failed", error="final_manuscript.md 미생성")

        elif step_id == "step_4":
            # 팩트체크 결과 확인 — adjusted 항목 원고 자동 반영
            report_path = self.project_dir / "factcheck_report.json"
            if report_path.exists():
                try:
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    claims = report.get("claims", report.get("results", []))
                    adjusted = [c for c in claims if c.get("status") == "adjusted" or c.get("action") == "adjust"]

                    if adjusted:
                        print(f"    [팩트체크] 수정 권장 {len(adjusted)}건 발견 — 원고 자동 수정")
                        _notify("Director", f"팩트체크 수정 권장 {len(adjusted)}건 → 원고 자동 반영",
                                phase=self.state.current_phase, project=self.project_slug, level="warning")

                        ms_path = self.project_dir / "final_manuscript.md"
                        if ms_path.exists():
                            text = ms_path.read_text(encoding="utf-8")
                            applied = 0
                            for item in adjusted:
                                original = item.get("original_text", "") or item.get("claim", "")
                                corrected = item.get("corrected_text", "") or item.get("suggestion", "")
                                if original and corrected and original in text:
                                    text = text.replace(original, corrected)
                                    print(f"    [수정] \"{original[:30]}\" → \"{corrected[:30]}\"")
                                    applied += 1
                            ms_path.write_text(text, encoding="utf-8")
                            if applied:
                                _notify("Director", f"원고 수정 완료: {applied}건 반영",
                                        phase=self.state.current_phase, project=self.project_slug, level="success")
                            else:
                                print(f"    [팩트체크] 수정 권장 {len(adjusted)}건 중 원고 내 매칭 없음 — 수동 확인 필요")
                    else:
                        print(f"    [팩트체크] 수정 권장 항목 없음 ✓")
                except Exception as e:
                    print(f"    [WARN] 팩트체크 보고서 파싱 실패: {e}")

        elif step_id == "step_5":
            # 씬 분해 검증: scene_specs.json에 scenes 존재
            specs_path = self.project_dir / "scene_specs.json"
            if specs_path.exists():
                try:
                    data = json.loads(specs_path.read_text(encoding="utf-8"))
                    n_scenes = len(data.get("scenes", []))
                    if n_scenes > 0:
                        print(f"    [검증] 씬 분해: {n_scenes}씬 ✓")
                    else:
                        return StepResult(step_id=step_id, status="failed", error="scene_specs.json에 씬 0개")
                except Exception:
                    return StepResult(step_id=step_id, status="failed", error="scene_specs.json 파싱 실패")

        return result  # 기본: 원래 결과 유지

    def _run_sequential(self, steps: List[dict]):
        """순차 실행 + 사감독 검증."""
        for step in steps:
            result = self._execute_step(step)

            # 사감독 검증 + 보완
            result = self._validate_step(step["id"], result)
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

        # scene_specs 로드 (없으면 scene_decomposition.json에서 폴백)
        specs_path = self.project_dir / "scene_specs.json"
        if not specs_path.exists():
            decomp_path = self.project_dir / "scene_decomposition.json"
            if decomp_path.exists():
                # step_6(creative_direction)은 scene_decomposition → scene_specs 변환
                # decomposition을 scene_specs 초기 구조로 변환
                decomp = json.loads(decomp_path.read_text(encoding="utf-8"))
                original_specs = self._decomp_to_specs(decomp)
                specs_path.write_text(
                    json.dumps(original_specs, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                _notify("Director", f"scene_decomposition → scene_specs 변환 완료 ({len(original_specs.get('scenes', []))}씬)",
                        phase=self.state.current_phase, project=self.project_slug)
            else:
                return StepResult(step_id=step_id, status="failed",
                                  error="scene_specs.json 및 scene_decomposition.json 모두 없음")
        else:
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
            _notify("Director", f"DB 업데이트: scene_count={total_scenes}",
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

            # ── creative 빈 씬 검증 + 자동 수정 (creative_direction 완료 후) ──
            if step_name == "creative_direction":
                specs_path_check = self.project_dir / "scene_specs.json"
                if specs_path_check.exists():
                    specs_check = json.loads(specs_path_check.read_text(encoding="utf-8"))
                    fixed = 0
                    for scene in specs_check.get("scenes", []):
                        creative = scene.get("visualization", {}).get("creative", {})
                        if not creative.get("layout"):
                            if "visualization" not in scene:
                                scene["visualization"] = {}
                            if "creative" not in scene["visualization"]:
                                scene["visualization"]["creative"] = {}
                            scene["visualization"]["creative"]["layout"] = "cinematic"
                            scene["visualization"]["creative"]["reveal"] = "fade_in"
                            scene["visualization"]["creative"]["emphasis"] = "none"
                            scene["visualization"]["creative"]["mood"] = "informative"
                            scene["visualization"]["creative"]["headline"] = ""
                            scene["visualization"]["creative"]["concept"] = scene.get("narration", "")[:50]
                            if not scene.get("imageAsset"):
                                scene["imageAsset"] = {"source": "generate", "placement": "fullscreen"}
                            fixed += 1
                    if fixed:
                        specs_path_check.write_text(
                            json.dumps(specs_check, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
                        print(f"    [검증] creative 빈 씬 {fixed}개 → cinematic 자동 할당")
                        _notify("Director", f"creative 빈 씬 {fixed}개 발견 → cinematic 자동 할당",
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

        # 3. Claude CLI agent 모드 (Write 도구 허용, multi-turn)
        model = step.get("single_call_model", "claude-opus-4-6")
        timeout_sec = self._get_agent_timeout(agent_name)

        # 프롬프트에 파일 저장 지시 추가
        prompt += f"""

<output_format>
결과를 scene_specs와 동일한 JSON 구조로, scenes 배열에 이 챕터의 씬들만 포함하여 작성하세요.
**반드시 Write 도구를 사용하여** 아래 경로에 저장하세요:
{tmp_path}

특히 imageAsset의 searchQuery 필드를 반드시 채워주세요.
모든 씬에 적절한 이미지 검색어를 영어로 작성해야 합니다.
</output_format>"""

        cli_path = self._find_claude_cli()
        cmd = [
            cli_path, "--print", "--output-format", "json",
            "--model", model, "--max-turns", "5",
            "--allowedTools", "Read", "--allowedTools", "Write",
        ]

        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        env["SEARCH_ENGINE"] = self.state.config.get("search_engine", "")
        env.pop("CLAUDECODE", None)

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

        elapsed = time.time() - t0
        cost_info = self._parse_claude_cost(stdout, stderr)

        if proc.returncode != 0:
            error = stderr[:300] or stdout[:300]
            return ChapterResult(
                chapter=chapter_num, status="failed",
                error=f"CLI exit {proc.returncode}: {error}",
                cost_info=cost_info, duration_sec=elapsed,
            )

        # 4. 결과 파싱: 파일 우선 → stdout 폴백
        updated_scenes = chapter_scenes  # 기본값
        try:
            if tmp_path.exists() and tmp_path.stat().st_size > 100:
                updated = json.loads(tmp_path.read_text(encoding="utf-8"))
                llm_scenes = updated.get("scenes", [])
                if llm_scenes:
                    updated_scenes = self._merge_llm_response(chapter_scenes, llm_scenes)
                    print(f"    [Ch{chapter_num}] 파일에서 읽기 성공 ({len(llm_scenes)}씬)")
        except Exception as e:
            print(f"    [Ch{chapter_num}] 파일 읽기 실패: {e}")

        if updated_scenes is chapter_scenes:
            # 파일에서 못 읽었으면 stdout에서 시도
            content = self._extract_json_from_cli_output(stdout)
            if content:
                llm_scenes = content.get("scenes", [])
                if llm_scenes:
                    updated_scenes = self._merge_llm_response(chapter_scenes, llm_scenes)

        _notify(agent_name,
                f"{label} 완료 (Ch{chapter_num}, {elapsed:.1f}s)",
                phase=self.state.current_phase, project=self.project_slug,
                level="success")

        return ChapterResult(
            chapter=chapter_num, status="completed",
            scenes=updated_scenes,
            cost_info=cost_info, duration_sec=elapsed,
        )

    # 1턴 전용 프롬프트 파일 매핑 (step_name → 프롬프트 파일명)
    SINGLE_CALL_PROMPTS = {
        "creative_direction": "creative-direction.md",
        "asset_advisory": "asset-advisory.md",
        "data_enrichment": "data-enrichment.md",
        "motion_planning": "motion-planning.md",
        "tts_preprocess": "tts-preprocess.md",
    }

    def _build_chapter_prompt(self, step: dict, chapter_specs: dict) -> str:
        """챕터별 병렬 처리용 프롬프트 빌드."""
        step_name = step.get("name", "")

        # 1턴 전용 프롬프트 파일이 있으면 사용
        prompt_file = self.SINGLE_CALL_PROMPTS.get(step_name)
        if prompt_file:
            return self._build_from_prompt_file(step, chapter_specs, prompt_file)

        return self._build_chapter_prompt_generic(step, chapter_specs)

    def _build_from_prompt_file(self, step: dict, chapter_specs: dict, prompt_file: str) -> str:
        """1턴 전용 프롬프트 파일 로드 + 변수 치환 + 아트스타일 오버라이드."""
        chapter_num = step.get("_chapter_num", 0)

        # 프롬프트 템플릿 로드 (중앙 규칙 → 로컬 fallback)
        prompt_key = f"prompts/single-call/{prompt_file}"
        template = self.rule_manager.load(prompt_key)

        # 컨텍스트 파일 빌드
        context_block = ""
        for fname in ["research_report.json", "outline.json"]:
            fpath = self.project_dir / fname
            if fpath.exists():
                context_block += f"\n<file name=\"{fname}\">\n{fpath.read_text(encoding='utf-8')[:50000]}\n</file>\n"

        manuscript_path = self.project_dir / "final_manuscript.md"
        if manuscript_path.exists():
            full_ms = manuscript_path.read_text(encoding="utf-8")
            chapter_ms = self._extract_chapter_manuscript(full_ms, chapter_num)
            context_block += f"\n<file name=\"final_manuscript.md (챕터 {chapter_num})\">\n{chapter_ms}\n</file>\n"

        # 아트스타일 오버라이드 로드
        art_style_override = self._load_art_style_override(step.get("name", ""))

        # 변수 치환
        chapter_specs_json = json.dumps(chapter_specs, ensure_ascii=False, indent=2)
        prompt = template.replace("{context_block}", context_block)
        prompt = prompt.replace("{chapter_specs_json}", chapter_specs_json)
        prompt = prompt.replace("{art_style_override}", art_style_override)

        return prompt

    def _load_art_style_override(self, step_name: str) -> str:
        """아트스타일 JSON에서 prompt_overrides를 로드. 중앙 참조."""
        config = self.state.config
        art_style_rel = config.get("art_style", "")
        if not art_style_rel:
            return ""

        from auto_agent.db.project_manager import resolve_art_style_path
        art_path = resolve_art_style_path(art_style_rel)
        if not art_path:
            return ""

        try:
            art_data = json.loads(art_path.read_text(encoding="utf-8"))
            overrides = art_data.get("prompt_overrides", {})
            # step_name에서 언더스코어를 하이픈으로 변환하여 매칭
            override_key = step_name.replace("_", "-")
            override_text = overrides.get(override_key, "")
            if override_text:
                return f"\n<art_style_override>\n아트스타일: {art_data.get('name', '')}\n{override_text}\n</art_style_override>"
        except Exception:
            pass
        return ""

    def _load_skill_file(self, key: str) -> str:
        """스킬 파일 1개 로드. 로컬 DATA_DIR 우선 → 중앙 규칙 fallback. 없으면 빈 문자열."""
        # 로컬 파일 우선 (Supabase 캐시보다 로컬 수정 우선)
        local_path = DATA_DIR / key
        if local_path.exists():
            try:
                return local_path.read_text(encoding="utf-8")
            except Exception:
                pass
        # 중앙 규칙 fallback
        try:
            return self.rule_manager.load(key)
        except (FileNotFoundError, AttributeError):
            return ""

    def _load_shared_skill(self, skill_name: str, refs_to_load=None) -> str:
        """공유 스킬 로드. 디렉토리 스킬(SKILL.md + references/) 또는 플랫 파일."""
        # 1) 디렉토리 스킬
        skill_key = f"skills/shared/{skill_name}/SKILL.md"
        content = self._load_skill_file(skill_key)
        if content:
            # references 로드
            if refs_to_load is not None:
                for ref_name in refs_to_load:
                    ref_key = f"skills/shared/{skill_name}/references/{ref_name}.md"
                    ref_content = self._load_skill_file(ref_key)
                    if ref_content:
                        content += f"\n\n{ref_content}"
            else:
                # 전체 references — 로컬 디렉토리에서 glob (캐시에선 파일 목록 불가)
                ref_dir = DATA_DIR / "skills" / "shared" / skill_name / "references"
                if ref_dir.exists():
                    for ref_file in sorted(ref_dir.glob("*.md")):
                        ref_key = f"skills/shared/{skill_name}/references/{ref_file.name}"
                        ref_content = self._load_skill_file(ref_key)
                        if ref_content:
                            content += f"\n\n{ref_content}"
            return content

        # 2) 플랫 파일
        flat_key = f"skills/shared/{skill_name}.md"
        content = self._load_skill_file(flat_key)
        if content:
            return content

        # 3) 루트 레벨 (레거시)
        root_key = f"skills/{skill_name}.md"
        return self._load_skill_file(root_key)

    def _build_chapter_prompt_generic(self, step: dict, chapter_specs: dict) -> str:
        """범용 챕터별 병렬 처리 프롬프트 (기존 로직)."""
        agent_name = step["agent"]
        chapter_num = step.get("_chapter_num", 0)
        chapter_specs_path = step.get("_chapter_specs_path", "")

        # 에이전트 스킬 (중앙 규칙 → 로컬 fallback)
        agent_skill = self._load_skill_file(f"skills/agents/{agent_name}/SKILL.md")

        # 공유 스킬 수집
        skill_names = list(step.get("skills", []))
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        for s in agent_def.get("skills", []):
            if s not in skill_names:
                skill_names.append(s)

        skill_refs = agent_def.get("skill_refs", {})
        shared_skills_text = ""
        for skill_name in skill_names:
            content = self._load_shared_skill(skill_name, skill_refs.get(skill_name))
            if content:
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"

        # 공통 컨텍스트 파일
        context_block = ""
        for fname in ["research_report.json", "outline.json"]:
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

각 씬의 visualization.creative, items, values, imageAsset, mapScene을 설계하세요.
narration, chapter, durationFrames 등 기존 필드는 수정하지 마세요.
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

    @staticmethod
    def _decomp_to_specs(decomp: dict) -> dict:
        """scene_decomposition.json → scene_specs.json 초기 구조 변환."""
        scenes = []
        for s in decomp.get("scenes", []):
            scene = {
                "sceneNumber": s.get("scene_number", s.get("sceneNumber", 0)),
                "chapter": s.get("chapter", 0),
                "title": s.get("title", ""),
                "narration": s.get("narration", ""),
                "narration_tts": s.get("narration", ""),
                "durationFrames": int((s.get("estimated_duration_sec", 8)) * 30),
                "visualization": {
                    "title": s.get("title", ""),
                    "items": [],
                    "values": [],
                    "creative": {},
                },
                "transition": {"type": "fade", "durationFrames": 15},
                "imageAsset": None,
                "mapScene": None,
            }
            # decomposition에서 이미지/맵 힌트가 있으면 전달
            if s.get("has_image_asset"):
                ia = s.get("image_asset") or {}
                scene["imageAsset"] = {
                    "source": ia.get("source", "search"),
                    "query": ia.get("query", s.get("title", "")),
                    "placement": ia.get("placement", "background"),
                    "opacity": ia.get("opacity", 0.3),
                }
            scenes.append(scene)

        return {
            "version": "4.0",
            "topic": decomp.get("topic", ""),
            "theme": "simple",
            "total_scenes": len(scenes),
            "scenes": scenes,
        }

    @staticmethod
    def _merge_llm_response(original_scenes: list, llm_scenes: list) -> list:
        """LLM 응답의 creative/visualization을 원본 씬에 머지.

        LLM은 visualization.creative, items, values, imageAsset, mapScene 등만 출력.
        원본의 narration, durationFrames, chapter 등은 유지.
        """
        llm_by_num = {}
        for s in llm_scenes:
            num = s.get("sceneNumber") or s.get("scene_number", 0)
            llm_by_num[num] = s

        merged = []
        for orig in original_scenes:
            num = orig.get("sceneNumber", 0)
            llm = llm_by_num.get(num)
            if llm:
                result = dict(orig)
                # visualization 머지 (creative, items, values 등)
                if llm.get("visualization"):
                    orig_viz = result.get("visualization") or {}
                    llm_viz = llm["visualization"]
                    merged_viz = {**orig_viz, **llm_viz}
                    # creative는 깊은 머지
                    if llm_viz.get("creative"):
                        orig_cr = orig_viz.get("creative") or {}
                        merged_viz["creative"] = {**orig_cr, **llm_viz["creative"]}
                    result["visualization"] = merged_viz
                # imageAsset 머지
                if "imageAsset" in llm:
                    result["imageAsset"] = llm["imageAsset"]
                # mapScene 머지
                if "mapScene" in llm:
                    result["mapScene"] = llm["mapScene"]
                # vizAnimation 머지
                if "vizAnimation" in llm:
                    result["vizAnimation"] = llm["vizAnimation"]
                # transition 머지
                if "transition" in llm:
                    result["transition"] = llm["transition"]
                # enrichment 머지
                if "enrichment" in llm:
                    result["enrichment"] = llm["enrichment"]
                merged.append(result)
            else:
                merged.append(orig)
        return merged

    def _auto_build_and_capture(self, chapter_results: dict, chapters: dict):
        """병합 완료 후 자동 매니페스트 빌드. (썸네일 캡처 비활성화)"""
        _notify("Director", "매니페스트 빌드 시작합니다",
                phase=self.state.current_phase, project=self.project_slug)

        # 1. 매니페스트 빌드
        try:
            pid = str(self.project.get("id", self.project_slug))
            storage_key = self.sync.storage_key if self.sync else self.project_slug
            result = subprocess.run(
                [sys.executable, "-m", "auto_agent.scripts.build_manifest",
                 pid, storage_key, str(self.project_dir)],
                cwd=str(get_workspace_dir()),
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode == 0:
                print("    [AUTO] 매니페스트 빌드 완료")
            else:
                print(f"    [WARN] 매니페스트 빌드 실패: {result.stderr[:200]}")
                return
        except Exception as e:
            print(f"    [WARN] 매니페스트 빌드 에러: {e}")
            return

        # 썸네일 캡처 비활성화 — 필요 시 대시보드에서 수동 실행
        return

        # [비활성화] 2. 변경된 씬의 기존 썸네일 무효화
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

        # [비활성화] 3. 썸네일 캡처 (generate-thumbnails.mjs)
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
                ws / "remotion" / "public" / "manifests" / f"{self.sync.storage_key if self.sync else Path(self.project_dir).name}.json",
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
        """아트스타일 존재 확인 (중앙 참조, 복제 안 함). config 미설정 시 경고만."""
        config = self.state.config
        art_style_rel = config.get("art_style")

        if not art_style_rel:
            _notify("System", "아트스타일 미설정 — config에 art_style을 설정해주세요",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="error")
            print("    [PREFLIGHT] 아트스타일 config 미설정")
            return

        # 중앙 참조: 복제하지 않고 원본 경로만 확인
        from auto_agent.db.project_manager import resolve_art_style_path
        resolved = resolve_art_style_path(art_style_rel)

        if resolved:
            style_name = config.get("style_name", resolved.stem)
            _notify("System", f"아트스타일 '{style_name}' 확인 완료: {resolved}",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="info")
            print(f"    [PREFLIGHT] 아트스타일 '{style_name}' → {resolved}")
        else:
            _notify("System", f"아트스타일 파일 없음: {art_style_rel}",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="error")
            print(f"    [PREFLIGHT] 아트스타일 파일 없음: {art_style_rel}")

        # 2. character_casting.json 기반 기준 캐릭터 이미지 확인
        casting_path = self.project_dir / "character_casting.json"
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

        # skip 플래그 체크
        if step.get("skip"):
            print(f"  [SKIP] {step_id}: skip=true")
            return StepResult(step_id=step_id, status="skipped")

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
        """단일 호출 step — CLI 1턴 모드 (도구 없음, stdout JSON 파싱).

        입력 파일을 프롬프트에 인라인 주입 → LLM 1턴 → stdout에서 JSON 파싱 → 파일 저장.
        도구(Read/Write) 없이 실행하므로 multi-turn 오버헤드 제거.
        """
        step_id = step["id"]
        step_name = step.get("name", step_id)
        agent = step.get("agent", "")
        target_model = step.get("single_call_model", "claude-opus-4-6")
        outputs = step.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]

        # 출력 파일 이미 존재하면 스킵 (resume)
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        input_set = set(inputs)
        has_inplace = any(out in input_set for out in outputs)
        if not has_inplace and outputs:
            all_exist = all(
                self._resolve_output_path(out).exists()
                for out in outputs
                if "{" not in out
            )
            if all_exist:
                return StepResult(
                    step_id=step_id, status="completed",
                    output_files=[str(self._resolve_output_path(o)) for o in outputs],
                )

        # 프롬프트 빌드 — 1턴 전용 프롬프트가 있으면 사용
        step_name = step.get("name", "")
        prompt_file = self.SINGLE_CALL_PROMPTS.get(step_name)
        if prompt_file:
            # 1턴 전용 프롬프트 (컨텍스트 + 입력 파일 인라인 주입)
            context_block = ""
            for inp in inputs:
                inp_path = self._resolve_output_path(inp)
                if inp_path.exists():
                    context_block += f"\n<file name=\"{inp}\">\n{inp_path.read_text(encoding='utf-8')[:80000]}\n</file>\n"

            template = self.rule_manager.load(f"prompts/single-call/{prompt_file}")
            art_style_override = self._load_art_style_override(step_name)
            # chapter_specs_json — motion_planning은 축약 데이터만 필요
            specs_path = self._resolve_output_path("scene_specs.json")
            if specs_path.exists():
                if step_name == "motion_planning":
                    # 씬별 sceneNumber, chapter, title, durationFrames, creative.reveal/mood만 추출
                    full = json.loads(specs_path.read_text(encoding="utf-8"))
                    compact_scenes = []
                    for s in full.get("scenes", []):
                        cr = s.get("visualization", {}).get("creative", {})
                        compact_scenes.append({
                            "sceneNumber": s.get("sceneNumber"),
                            "chapter": s.get("chapter"),
                            "title": s.get("title", ""),
                            "durationFrames": s.get("durationFrames", 150),
                            "reveal": cr.get("reveal", ""),
                            "emphasis": cr.get("emphasis", ""),
                            "mood": cr.get("mood", ""),
                            "hasChart": bool(s.get("visualization", {}).get("chartConfig")),
                            "hasImage": bool(s.get("imageAsset")),
                            "hasMap": bool(s.get("mapScene")),
                            "itemCount": len(s.get("visualization", {}).get("items", [])),
                        })
                    chapter_specs_json = json.dumps({"scenes": compact_scenes}, ensure_ascii=False, indent=2)
                else:
                    chapter_specs_json = specs_path.read_text(encoding="utf-8")[:80000]
            else:
                chapter_specs_json = "{}"

            prompt = template.replace("{context_block}", context_block)
            prompt = prompt.replace("{chapter_specs_json}", chapter_specs_json)
            prompt = prompt.replace("{art_style_override}", art_style_override)
        else:
            prompt = self._build_agent_prompt(step)

        # 출력 파일 정보를 프롬프트에 추가 (1턴 전용 프롬프트가 없을 때만)
        output_names = [Path(o).name for o in outputs if "{" not in o]
        if not prompt_file and len(output_names) == 1:
            prompt += f"""

<output_format>
결과를 순수 JSON으로 직접 출력하세요.
마크다운 코드 블록(```)으로 감싸도 괜찮습니다.
설명, 서론, 부연은 절대 하지 마세요. JSON만 출력하세요.
출력 파일: {output_names[0]}
</output_format>"""
        elif len(output_names) >= 2:
            prompt += f"""

<output_format>
여러 파일을 출력해야 합니다. 아래 JSON 형식으로 출력하세요. 설명이나 마크다운 없이 순수 JSON만:
{{
  "files": {{
    "{output_names[0]}": {{ ... 파일 내용 ... }},
    "{output_names[1]}": {{ ... 파일 내용 ... }}
  }}
}}
</output_format>"""

        # CLI 실행 (도구 비활성, 3턴 — stdout으로 JSON 직접 출력)
        cli_path = self._find_claude_cli()
        cmd = [
            cli_path, "--print",
            "--output-format", "json",
            "--model", target_model,
            "--max-turns", "3",
            "--tools", "",
        ]

        timeout_sec = self._get_agent_timeout(agent) if agent else 900
        print(f"[single_call 1턴] model={target_model}", flush=True)

        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        env.pop("CLAUDECODE", None)

        t0 = time.time()
        try:
            proc = subprocess.Popen(
                cmd, cwd=str(self.project_dir), env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout_sec)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return StepResult(step_id=step_id, status="failed",
                              error=f"타임아웃 ({timeout_sec}s)")
        except FileNotFoundError:
            return StepResult(step_id=step_id, status="failed",
                              error="Claude CLI를 찾을 수 없습니다")

        elapsed = time.time() - t0
        cost_info = self._parse_claude_cost(stdout, stderr)

        if proc.returncode != 0:
            error = stderr[:300] or stdout[:300]
            return StepResult(step_id=step_id, status="failed",
                              error=f"CLI exit {proc.returncode}: {error}",
                              cost_info=cost_info, duration_sec=elapsed)

        # stdout에서 JSON 추출
        content = self._extract_json_from_cli_output(stdout)
        if not content:
            # 파일이 이미 존재하면 (이전 실행 등) 성공 처리
            all_exist = all(
                self._resolve_output_path(out).exists()
                for out in outputs if "{" not in out
            ) if outputs else False
            if all_exist:
                return StepResult(step_id=step_id, status="completed",
                                  output_files=[str(self._resolve_output_path(o)) for o in outputs],
                                  cost_info=cost_info, duration_sec=elapsed)
            # 디버그: stdout 첫 500자 출력
            print(f"    [single_call] JSON 파싱 실패. stdout 시작: {stdout[:500]}", flush=True)
            return StepResult(step_id=step_id, status="failed",
                              error="stdout에서 JSON 파싱 실패",
                              cost_info=cost_info, duration_sec=elapsed)

        # 파일 저장
        try:
            if len(output_names) == 1:
                out_path = self._resolve_output_path(outputs[0])
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(
                    json.dumps(content, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            elif len(output_names) >= 2:
                files = content.get("files", content)
                for out in outputs:
                    fname = Path(out).name
                    if fname in files:
                        out_path = self._resolve_output_path(out)
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_text(
                            json.dumps(files[fname], ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )
        except Exception as e:
            return StepResult(step_id=step_id, status="failed",
                              error=f"파일 저장 실패: {e}",
                              cost_info=cost_info, duration_sec=elapsed)

        return StepResult(
            step_id=step_id, status="completed",
            output_files=[str(self._resolve_output_path(o)) for o in outputs],
            cost_info=cost_info, duration_sec=elapsed,
        )

    @staticmethod
    def _extract_json_from_cli_output(stdout: str) -> dict:
        """Claude CLI --output-format json 출력에서 실제 JSON 콘텐츠 추출."""
        import re

        # --output-format json일 때 CLI는 {"type":"result","result":...} 형태 출력
        text = ""
        try:
            cli_output = json.loads(stdout)
            if isinstance(cli_output, dict):
                # CLI 메타데이터 감지 — "type":"result" + "subtype" 존재하면 래퍼
                if cli_output.get("type") == "result" and "subtype" in cli_output:
                    # result 필드에서 실제 텍스트 추출
                    result = cli_output.get("result", "")
                    if isinstance(result, str):
                        text = result
                    elif isinstance(result, list):
                        text = " ".join(
                            b.get("text", "") for b in result
                            if isinstance(b, dict) and b.get("type") == "text"
                        )
                    else:
                        text = ""
                    # result가 비어있으면 → LLM이 도구만 사용하고 텍스트 출력 안 한 것
                    if not text.strip():
                        return None
                else:
                    # CLI 래퍼가 아닌 순수 JSON → 그대로 반환
                    return cli_output
            elif isinstance(cli_output, str):
                text = cli_output
        except json.JSONDecodeError:
            text = stdout

        if not text or not text.strip():
            return None

        # 마크다운 코드 블록 제거
        md_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if md_match:
            text = md_match.group(1)

        # 최외곽 { ... } 또는 [ ... ] 찾기
        text = text.strip()
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start = text.find(start_char)
            if start >= 0:
                end = text.rfind(end_char)
                if end > start:
                    try:
                        parsed = json.loads(text[start:end + 1])
                        # CLI 메타데이터를 실수로 파싱한 건 아닌지 검증
                        if isinstance(parsed, dict) and parsed.get("type") == "result" and "duration_ms" in parsed:
                            return None  # CLI 메타데이터 → 실패
                        return parsed
                    except json.JSONDecodeError:
                        continue
        return None

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
        # 단, 디렉토리 경로(images/ 등)는 해당 디렉토리 안에 실제 파일이 있어야 스킵
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        input_set = set(inputs)
        has_inplace_output = any(out in input_set for out in outputs)

        if not has_inplace_output:
            all_exist = True
            for out in outputs:
                out_path = self._resolve_output_path(out)
                if out.endswith("/"):
                    # 디렉토리 출력 → 해당 디렉토리 자체가 존재하고 안에 파일이 있어야
                    if not (out_path.exists() and out_path.is_dir() and any(out_path.iterdir())):
                        all_exist = False
                        break
                elif "{" in out:
                    # 패턴 경로 → 해당 디렉토리 안에 파일이 있어야
                    if not (out_path.parent.exists() and out_path.parent.is_dir() and any(out_path.parent.glob(out_path.name.replace("{", "*").replace("}", "*")))):
                        all_exist = False
                        break
                elif not out_path.exists():
                    all_exist = False
                    break

            if all_exist and outputs:
                print(f"[resume] 출력 파일 존재 → 스킵", flush=True)
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

        # 분량별 리서치 스케일링 (duration_minutes 기반)
        duration_min = self.state.config.get("duration_minutes", 10)
        if agent in ("research-orchestrator",):
            scale = {1: (20, 1200), 3: (35, 1200), 5: (50, 1200)}
            if duration_min in scale:
                max_turns, timeout_sec = scale[duration_min]
            elif duration_min < 3:
                max_turns, timeout_sec = 20, 1200
            # 10분 이상은 agents.json 기본값 + 넉넉한 타임아웃
            else:
                timeout_sec = max(timeout_sec, 1500)
        elif agent in ("write-manuscript",):
            if duration_min <= 1:
                max_turns = min(max_turns, 25)
                timeout_sec = min(timeout_sec, 600)
            elif duration_min <= 3:
                max_turns = min(max_turns, 35)
                timeout_sec = min(timeout_sec, 900)

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
        env = os.environ.copy()
        env["PROJECT_NAME"] = self.project_slug
        # uuid 마이그레이션 후 프로젝트 디렉토리명이 {uuid}_{slug}이므로 직접 전달
        env["PROJECT_DIR"] = str(self.project_dir)
        env["SEARCH_ENGINE"] = self.state.config.get("search_engine", "")

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
            # "image-sourcer": "scripts/source_images.py",  # 제거 — image-searcher/image-painter 에이전트로 분리
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

        # manifest-builder는 project_id + storage_key 인자 필요
        cmd = [sys.executable, str(script_path)]
        if module_name == "manifest-builder":
            pid = str(self.project.get("id", self.project_slug))
            sk = str(self.sync.storage_key) if self.sync and self.sync.storage_key else self.project_slug
            if pid and sk:
                cmd.extend([pid, sk])

        # PYTHONPATH에 워크스페이스 추가 (auto_agent 패키지 import 보장)
        ws = str(get_workspace_dir())
        existing_pypath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{ws}:{existing_pypath}" if existing_pypath else ws

        try:
            result = subprocess.run(
                cmd,
                cwd=ws,
                env=env,
                capture_output=True,
                text=True,
                timeout=1800,  # 30분 타임아웃
            )

            if result.returncode == 0:
                return StepResult(step_id=step_id, status="completed")
            else:
                error = result.stderr or result.stdout[-2000:]
                # 전체 에러를 로그 파일에 기록
                print(f"\n    [ERROR] {module_name} 전체 stderr:\n{result.stderr}", flush=True)
                if result.stdout:
                    print(f"    [ERROR] {module_name} stdout 끝:\n{result.stdout[-500:]}", flush=True)
                return StepResult(
                    step_id=step_id, status="failed",
                    error=f"Exit code {result.returncode}: {error[:1000]}",
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

        # 플레이스홀더 치환 — {project}는 디렉토리명(uuid_slug) 사용
        project_dir_name = Path(self.project_dir).name
        command = command.replace("{project}", project_dir_name)
        command = command.replace("{composition}", self._resolve_composition())

        # Node.js PATH 보장 (npx, node 등)
        node_dir = Path.home() / "local/nodejs/node-v22.14.0-darwin-x64/bin"
        if node_dir.exists() and str(node_dir) not in env.get("PATH", ""):
            env["PATH"] = f"{node_dir}:{env.get('PATH', '')}"

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

        # 1. Agent SKILL.md 읽기 (중앙 규칙 → 로컬 fallback)
        agent_skill = self._load_skill_file(f"skills/agents/{agent_name}/SKILL.md")

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
            content = self._load_shared_skill(skill_name, skill_refs.get(skill_name))
            if content:
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
                if vault_block:
                    vault_chars = len(vault_block)
                    print(f"    [VaultRAG] 리서치용 볼트 지식 주입: {vault_chars}자", flush=True)
                    _notify("System", f"볼트에서 기존 리서치 {vault_chars}자 발견 → 프롬프트에 주입",
                            phase=self.state.current_phase, project=self.project_slug, level="info")
                else:
                    print("    [VaultRAG] 리서치용 볼트 지식 없음", flush=True)
            elif agent_name in ("write-manuscript",):
                vault_block = self.vault.search_for_manuscript(topic, category)
                if vault_block:
                    print(f"    [VaultRAG] 원고용 볼트 지식 주입: {len(vault_block)}자", flush=True)
                    _notify("System", f"볼트에서 관련 원고 패턴 발견 → 프롬프트에 주입",
                            phase=self.state.current_phase, project=self.project_slug, level="info")

        # 7. 프로젝트 config 주입
        config = self.state.config or {}
        # duration_minutes (숫자) 또는 duration_target ("1min", "10min") 양쪽 지원
        duration_min = config.get("duration_minutes")
        if not duration_min:
            dt = config.get("duration_target", "10min")
            import re as _re
            m = _re.search(r'(\d+)', str(dt))
            duration_min = int(m.group(1)) if m else 10
        art_style = config.get("art_style", "")
        writing_style = config.get("writing_style", "")
        # 분량별 글자 수 가이드 (한국어 기준, 약 3~4자/초)
        target_chars = {1: 400, 3: 1200, 5: 2000, 10: 4000}.get(duration_min, duration_min * 400)

        # 8. 프롬프트 조립
        prompt = f"""<system_context>
프로젝트: {self.project_slug}
작업 디렉토리: {self.project_dir}
워크스페이스: {get_workspace_dir()}
</system_context>

<project_config>
영상 분량: {duration_min}분
목표 나레이션 글자 수: 약 {target_chars}자 (±10%)
아트스타일: {art_style}
문체 스타일: {writing_style}
{"**이로미즘 문체 필수 적용** — writing-style-iromism 스킬의 규칙을 반드시 따르세요." if writing_style == "iromism" else ""}
{"**세모지 문체 필수 적용** — writing-style-semoji 스킬의 규칙을 반드시 따르세요." if writing_style == "semoji" else ""}
</project_config>

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
2. 병렬 태스크 배포 시 → 각 에이전트가 무엇을 조사할지 개별 선언 필수:
   예: {{"agent": "Explorer-1", "text": "테슬라 초기 반도체 역사 조사 시작합니다", "level": "info"}}
   예: {{"agent": "Explorer-2", "text": "글로벌 반도체 시장 동향 조사 시작합니다", "level": "info"}}
   — 배포 후 즉시 각 Explorer별 시작 메시지를 기록하세요
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
        """agents.json 로드 (캐시). 중앙 규칙 → 로컬 fallback."""
        if not hasattr(self, "_agents_cache"):
            try:
                self._agents_cache = self.rule_manager.load_json("agents.json")
            except (FileNotFoundError, AttributeError):
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
        """output 경로 템플릿 해석. {project} → 디렉토리명(uuid_slug) 치환.

        경로 조합 기준:
        - 절대경로 → 그대로 사용
        - output/{dir_name}/... → project_dir 기준으로 dir_name 이후 부분만 추출
        - output/... (dir_name 없음) → PROJECT_ROOT 기준 (레거시 경로)
        - 그 외 상대경로 → project_dir 기준
        """
        # {project} 플레이스홀더는 실제 디렉토리명(uuid_slug) 기준으로 치환
        dir_name = Path(self.project_dir).name
        resolved = output_template.replace("{project}", dir_name)
        path = Path(resolved)
        if not path.is_absolute():
            # output/{dir_name}/... 형태 → project_dir 기준으로 변환 (DB 경로 지원)
            prefix = f"output/{dir_name}/"
            if resolved.startswith(prefix):
                return self.project_dir / resolved[len(prefix):]
            # 레거시: output/{slug}/... (dir_name과 다를 수 있음)
            legacy_prefix = f"output/{self.project_slug}/"
            if resolved.startswith(legacy_prefix):
                return self.project_dir / resolved[len(legacy_prefix):]
            # output/ 접두사가 있으나 slug 불포함 → 워크스페이스 루트 기준 (레거시)
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
