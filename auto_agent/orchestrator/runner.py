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
import platform
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
from zoneinfo import ZoneInfo

# Windows cp949 인코딩 문제 — 모든 출력을 UTF-8로 강제
if platform.system() == "Windows":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from auto_agent.paths import get_workspace_dir, get_data_dir, PACKAGE_DIR, DATA_DIR
from auto_agent.orchestrator.context_memory import ContextMemory
from auto_agent.orchestrator.vault_rag import VaultRAG
from auto_agent.orchestrator.claude_client import CachingClaudeClient
from auto_agent.orchestrator.local_tools import LOCAL_TOOL_SCHEMAS, handle_local_tool
from auto_agent.utils.platform import get_env_with_node, subprocess_kwargs

# ── Agent Messenger 브릿지 ──
_MESSENGER_URL = "http://localhost:8080/api/agent-messages/send"

# 에이전트 별명 매핑 — 대시보드 메신저에서 사용
AGENT_NICKNAMES = {
    "Director": "봉감독",
    "research-orchestrator": "홍탐정",
    "script-director": "한작가",
    "script-reviewer": "심사관",
    "data-mapper": "데이터팀",
    "fact-verifier": "팩트체커",
    "assembly-director": "조피디",
    "upload-info-generator": "업로드팀",
    "multiformat-director": "멀티팀",
    "System": "시스템",
    "Runner": "봉감독",
}

def _notify(agent: str, text: str, phase: str = "", project: str = "", level: str = "info", data: dict = None):
    """파이프라인 진행 상황을 대시보드 메신저로 전송. 파일 영속 + HTTP POST.
    agent 이름은 자동으로 별명으로 변환됩니다."""
    import time as _time
    nickname = AGENT_NICKNAMES.get(agent, agent)
    msg = {
        "agent": nickname, "text": text, "phase": phase,
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
    "data_mapping":               ("데이터 매핑",           "데이터 매핑 완료"),
    "fact_check":                 ("팩트 체크",            "팩트 체크 완료"),
    # stage_3
    "image_batch":                ("이미지 배치 생성",      "이미지 배치 완료"),
    "scene_decomposition":        ("씬 분할",              "씬 분할 완료"),
    "creative_direction":         ("창의적 연출 + 에셋 설계", "창의적 연출 + 에셋 설계 완료"),
    "data_enrichment_and_motion": ("데이터 보강/모션 설계",  "데이터 보강/모션 설계 완료"),
    # stage_3 내부 (assembly-director 서브태스크)
    "tts_generation":             ("음성 생성",            "음성 생성 완료"),
    "image_asset_sourcing":       ("이미지 소싱",           "이미지 소싱 완료"),
    "subtitle_sync":              ("자막 동기화",           "자막 동기화 완료"),
    "tts_verification":           ("TTS 발음 검증",         "TTS 발음 검증 완료"),
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
# Hook Manager — 코드 레벨 가드레일
# ═══════════════════════════════════════

class HookManager:
    """파이프라인 단계별 pre/post 훅 관리.

    settings.json 훅 대신 코드 레벨에서 직접 실행.
    가드 훅은 위반 시 ValueError를 raise.
    """

    def __init__(self):
        self._pre_step: dict[str, list] = {}
        self._post_step: dict[str, list] = {}
        self._pre_tool: dict[str, list] = {}  # tool_name → [guard_fn, ...]

    def register_pre_step(self, step_id: str, fn):
        self._pre_step.setdefault(step_id, []).append(fn)

    def register_post_step(self, step_id: str, fn):
        self._post_step.setdefault(step_id, []).append(fn)

    def register_pre_tool(self, tool_name: str, fn):
        self._pre_tool.setdefault(tool_name, []).append(fn)

    def run_pre_step(self, step_id: str, context: dict):
        for fn in self._pre_step.get(step_id, []):
            fn(context)

    def run_post_step(self, step_id: str, context: dict):
        for fn in self._post_step.get(step_id, []):
            fn(context)

    def run_pre_tool(self, tool_name: str, tool_input: dict):
        for fn in self._pre_tool.get(tool_name, []):
            fn(tool_input)


def _build_default_hooks() -> HookManager:
    """기본 가드레일 훅 등록."""
    hm = HookManager()

    # ── guard: 이미지 삭제 차단 (CLAUDE.md §9) ──
    def guard_image_delete(tool_input: dict):
        cmd = tool_input.get("command", "")
        if re.search(r"\brm\b", cmd):
            img_patterns = [r"scene_\d+", r"\.png\b", r"\.jpg\b", r"\.webp\b", r"_gen_\d+"]
            for p in img_patterns:
                if re.search(p, cmd, re.IGNORECASE):
                    raise ValueError(f"이미지 삭제 차단: {cmd[:100]}")
    hm.register_pre_tool("Bash", guard_image_delete)

    # ── guard: scene_specs 중첩 구조 차단 ──
    def guard_scene_specs_schema(tool_input: dict):
        content = tool_input.get("content", "")
        if '"visualization"' in content and '"creative"' in content:
            raise ValueError("scene_specs에 visualization.creative 중첩 구조 사용 금지 — 플랫 스키마 사용")
    hm.register_pre_tool("Write", guard_scene_specs_schema)

    # ── guard: 이미지 프롬프트 규칙 (아트스타일 키워드 금지) ──
    def guard_image_prompt(tool_input: dict):
        content = json.dumps(tool_input, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input)
        # imageAsset.prompt에 아트스타일 키워드 삽입 금지
        blocked = ["semoji style", "quirky cartoon", "flat staging", "2D illustration"]
        lower = content.lower()
        for kw in blocked:
            if kw in lower and "imageAsset" in content:
                raise ValueError(f"이미지 프롬프트에 아트스타일 키워드 금지: {kw}")
    hm.register_pre_tool("Write", guard_image_prompt)

    # ── guard: 이미지 버저닝 (덮어쓰기 금지) ──
    def guard_image_versioning(tool_input: dict):
        cmd = tool_input.get("command", "")
        # cp 또는 mv로 기존 이미지 덮어쓰기 감지
        if re.search(r"\b(cp|mv)\b.*scene_\d+.*_gen_01\.png", cmd):
            raise ValueError("기존 이미지 덮어쓰기 금지 — 새 버전 번호 사용 (_gen_02, _gen_03)")
    hm.register_pre_tool("Bash", guard_image_versioning)

    # ── post-step: 캐릭터 이름 규칙 검증 (step_2 완료 후) ──
    def post_validate_characters(context: dict):
        project_dir = Path(context.get("project_dir", ""))
        specs_path = project_dir / "scene_specs.json"
        if not specs_path.exists():
            return

        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        scenes = specs.get("scenes", [])

        # 캐릭터 이름 수집 및 검증
        all_chars = {}  # {char_name: [scene_numbers]}
        issues = []

        for scene in scenes:
            sn = scene.get("sceneNumber", 0)
            for char in scene.get("characters", []):
                if not isinstance(char, str):
                    continue
                all_chars.setdefault(char, []).append(sn)

                # 규칙 1: 괄호 안에 역할/시대/국적 정보 필수
                if "(" not in char or ")" not in char:
                    issues.append(
                        f"씬{sn} 캐릭터 '{char}' — 역할 정보 누락. "
                        f"형식: '이름(역할/시대)' 예: '천주혁(구다이글로벌 대표)'"
                    )

        # 규칙 2: 동일 인물 동일 문자열 확인
        name_base = {}  # {이름부분: [전체문자열들]}
        for char in all_chars:
            base = char.split("(")[0].strip()
            name_base.setdefault(base, set()).add(char)
        for base, variants in name_base.items():
            if len(variants) > 1:
                issues.append(
                    f"캐릭터 '{base}' 불일치: {variants} — 동일 인물은 동일 문자열 필수"
                )

        if issues:
            print(f"\n    ❌ [캐릭터 훅] {len(issues)}건 위반 — 래칫 리뷰에서 수정 필요:", flush=True)
            for issue in issues[:5]:
                print(f"      - {issue}", flush=True)
            _notify("System", f"캐릭터 규칙 위반 {len(issues)}건:\n" + "\n".join(issues[:3]),
                    phase=context.get("phase", ""), project=context.get("project", ""),
                    level="warning")
        elif all_chars:
            print(f"    ✓ [캐릭터 훅] {len(all_chars)}명 검증 통과", flush=True)

    hm.register_post_step("step_2", post_validate_characters)

    # ── post-step: imageAsset 누락 검증 (step_2 완료 후) ──
    def post_validate_image_assets(context: dict):
        project_dir = Path(context.get("project_dir", ""))
        specs_path = project_dir / "scene_specs.json"
        if not specs_path.exists():
            return

        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        scenes = specs.get("scenes", [])
        total = len(scenes)
        with_image = sum(1 for s in scenes if s.get("imageAsset") and s["imageAsset"].get("source"))
        ratio = with_image / total * 100 if total else 0

        # imageAsset.prompt는 100% 필수 (장면 연출)
        with_prompt = sum(1 for s in scenes if (s.get("imageAsset") or {}).get("prompt"))
        prompt_ratio = with_prompt / total * 100 if total else 0

        if prompt_ratio < 100:
            missing = [str(s.get("sceneNumber", "?")) for s in scenes
                       if not (s.get("imageAsset") or {}).get("prompt")]
            print(f"\n    ❌ [이미지 훅] 장면 연출(prompt) 미작성: {len(missing)}씬 — 씬{','.join(missing[:10])}", flush=True)
            _notify("System",
                    f"장면 연출 미작성 {len(missing)}씬 (100% 필수): 씬{','.join(missing[:10])}",
                    phase=context.get("phase", ""), project=context.get("project", ""),
                    level="warning")
        else:
            print(f"    ✓ [이미지 훅] 장면 연출 100% ({with_prompt}/{total}씬)", flush=True)

        # source 배정 비율 (참고용)
        print(f"    ℹ️ [이미지 훅] source 배정: {with_image}/{total}씬 ({ratio:.0f}%)", flush=True)

    hm.register_post_step("step_2", post_validate_image_assets)

    # ── post-step: 캐릭터 이미지 생성 검증 (step_3b 완료 후) ──
    def post_validate_character_images(context: dict):
        project_dir = Path(context.get("project_dir", ""))
        specs_path = project_dir / "scene_specs.json"
        if not specs_path.exists():
            return

        specs = json.loads(specs_path.read_text(encoding="utf-8"))
        scenes = specs.get("scenes", [])

        # 2씬+ 등장 캐릭터 추출
        char_counts = {}
        for scene in scenes:
            for char in scene.get("characters", []):
                if isinstance(char, str):
                    char_counts[char] = char_counts.get(char, 0) + 1
        recurring = {c: n for c, n in char_counts.items() if n >= 2}

        if not recurring:
            return

        # 캐릭터 이미지 파일 확인
        char_dir = project_dir / "images" / "characters"
        missing = []
        found = []
        for char_name in recurring:
            # 이름에서 괄호 앞부분 추출 → 파일명
            base_name = char_name.split("(")[0].strip()
            matches = list(char_dir.glob(f"*{base_name}*")) if char_dir.exists() else []
            if matches:
                found.append(char_name)
            else:
                missing.append(f"{char_name} ({recurring[char_name]}씬)")

        if missing:
            print(f"\n    ⚠️ [캐릭터 이미지 훅] 2씬+ 캐릭터 중 이미지 미생성: {len(missing)}명", flush=True)
            for m in missing[:5]:
                print(f"      - {m}", flush=True)
            _notify("System",
                    f"캐릭터 이미지 미생성 {len(missing)}명:\n" + "\n".join(missing[:5]) +
                    "\n→ assembly-director가 Phase B-1에서 생성해야 합니다",
                    phase=context.get("phase", ""), project=context.get("project", ""),
                    level="warning")
        if found:
            print(f"    ✓ [캐릭터 이미지 훅] {len(found)}명 생성 확인: {', '.join(found[:5])}", flush=True)

    hm.register_post_step("step_3b", post_validate_character_images)

    # ── pre-step: upload_info는 manifest 필요 ──
    def pre_upload_info(context: dict):
        project_dir = Path(context.get("project_dir", ""))
        if project_dir.exists():
            has_manifest = (
                (project_dir / "manifest.json").exists()
                or (project_dir / "remotion" / "public" / "manifest.json").exists()
            )
            if not has_manifest:
                raise ValueError("upload_info 생성에 manifest.json 필요 — step_3b 완료 후 실행")
    hm.register_pre_step("step_3c", pre_upload_info)

    return hm


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

        # 중앙 규칙 관리자 초기화
        from auto_agent.rule_manager import RuleManager
        self.rule_manager = RuleManager()

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
        self.hooks = _build_default_hooks()

    def _load_pipeline(self) -> dict:
        # 로컬 DATA_DIR 우선
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
        # 볼트 인덱스 자동 빌드 — 변경된 .md 파일만 재인덱싱 (해시 캐시 활용)
        # 매 실행마다 보장: 새 노트가 추가되면 다음 파이프라인에서 즉시 검색 가능
        if self.vault.enabled:
            try:
                from auto_agent.orchestrator.vault_indexer import VaultIndexer
                indexer = VaultIndexer()
                stats = indexer.index_all(self.vault.vault_dir, force=False)
                if stats.get("indexed", 0) > 0:
                    print(
                        f"[VaultIndexer] 변경분 인덱싱: +{stats['indexed']} 파일, "
                        f"총 {stats.get('total_chunks', 0)} 청크",
                        flush=True,
                    )
            except Exception as e:
                print(f"[VaultIndexer] 자동 빌드 실패 (무시): {e}", flush=True)

        phases = self.pipeline.get("phases", [])
        skip_until = from_step
        found_start = from_step is None

        print(f"{'=' * 60}")
        print(f"Pipeline Runner — {self.project_slug}")
        print(f"Config: art_style={self.state.config.get('art_style', 'N/A')}")
        print(f"        voice_id={self.state.config.get('voice_id', 'N/A')}")
        print(f"{'=' * 60}\n")
        config = self.state.config or {}
        topic = config.get("topic", self.project_slug)
        art_style = config.get("art_style", "N/A")
        writing_style = config.get("writing_style", "N/A")
        duration = config.get("duration_minutes", "?")
        brief_loaded = "✅" if self._load_creative_brief() else "❌"

        # baseTheme 확인
        art_style_path = self.project_dir / "art_style.json"
        base_theme = "N/A"
        if art_style_path.exists():
            try:
                ast = json.loads(art_style_path.read_text(encoding="utf-8"))
                base_theme = ast.get("design_tokens", {}).get("baseTheme", "❌ 미설정")
            except Exception:
                pass

        start_msg = (
            f"🎬 **파이프라인 시작**\n\n"
            f"**주제:** {topic}\n"
            f"**아트스타일:** {art_style}\n"
            f"**베이스테마:** {base_theme}\n"
            f"**문체:** {writing_style}\n"
            f"**분량:** {duration}분\n"
            f"**기획안:** {brief_loaded}"
        )
        _notify("Director", start_msg, phase="pipeline", project=self.project_slug, level="info")

        # 볼트 동기화: NAS 재연결 시 로컬 폴백 → NAS 자동 동기화
        try:
            sync_result = self.vault.sync_local_to_vault()
            if sync_result.get("synced", 0) > 0:
                self.vault.cleanup_local_vault()
        except Exception:
            pass

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
                    # 이 phase에 없으면 다음 phase에서 찾기
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

            # stage_1 시작 전 editorial_brief.json 자동 생성 (없을 경우)
            if phase_id == "stage_1" and not only_step:
                brief_path = Path(self.project_dir) / "editorial_brief.json"
                if not brief_path.exists():
                    print(f"\n  [editorial_brief] editorial_brief.json 없음 — step_0b 자동 실행", flush=True)
                    step_0b_def = None
                    for ph in self.pipeline.get("phases", []):
                        for s in ph.get("steps", []):
                            if s["id"] == "step_0b":
                                step_0b_def = s
                                break
                        if step_0b_def:
                            break
                    if step_0b_def:
                        self._execute_step(step_0b_def)
                    else:
                        print("  [editorial_brief] step_0b 정의를 찾을 수 없음 — 스킵", flush=True)

            print(f"\n{'─' * 40}")
            print(f"Phase: {phase_name} ({phase_id})")
            print(f"Execution: {execution}")
            print(f"Steps: {len(steps)}")
            print(f"{'─' * 40}\n")

            self.state.current_phase = phase_id
            _notify("Director", f"{phase_name} 들어갑니다! ({len(steps)}개 스텝)", phase=phase_id, project=self.project_slug)

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

            # stage_1 완료 후 editorial_brief alignment 검증
            if phase_id == "stage_1":
                self._check_brief_alignment()

            # stage_2 완료 후 매니페스트 자동 빌드 (대시보드 스토리보드용)
            if phase_id == "stage_2" and "step_2" in self.state.completed_steps:
                try:
                    pid = str(self.project.get("id", self.project_slug))
                    dir_name = Path(self.project_dir).name if self.project_dir else self.project_slug
                    storage_key = dir_name
                    result = subprocess.run(
                        [sys.executable, "-m", "auto_agent.scripts.build_manifest",
                         pid, storage_key, str(self.project_dir)],
                        cwd=str(get_workspace_dir()),
                        capture_output=True, text=True, encoding="utf-8", timeout=120,
                        **subprocess_kwargs(),
                    )
                    if result.returncode == 0:
                        print("    [AUTO] Stage 2 완료 → 매니페스트 빌드 완료")
                    else:
                        print(f"    [WARN] 매니페스트 빌드 실패: {result.stderr[:200]}")
                except Exception as e:
                    print(f"    [WARN] 매니페스트 빌드 에러: {e}")

            if only_step:
                break

        # --only/--from으로 지정한 step이 없으면 경고
        if only_step and not found_start:
            all_ids = []
            for ph in self.pipeline.get("phases", []):
                for s in ph.get("steps", []):
                    all_ids.append(s["id"])
            print(f"\n  [ERROR] step '{only_step}'를 찾을 수 없습니다.", flush=True)
            print(f"  사용 가능한 step ID: {', '.join(all_ids)}", flush=True)

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

    def _generate_research_digest(self):
        """research_report.json → research_digest.json 축약본 생성 (Python 추출).

        LLM 없이 구조화된 데이터에서 핵심 팩트/수치/출처만 추출.
        토큰 최적화를 위해 서사 텍스트는 제거하고 데이터만 보존.
        """
        import re

        report_path = self.project_dir / "research_report.json"
        digest_path = self.project_dir / "research_digest.json"
        print(f"    [DIGEST] report_path={report_path}, exists={report_path.exists()}", flush=True)

        if not report_path.exists():
            print("    [DIGEST] research_report.json 없음 → 스킵", flush=True)
            return

        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    [DIGEST] JSON 파싱 실패: {e}", flush=True)
            return

        # 숫자/통계 패턴
        stat_pattern = re.compile(r'\d+[\d,.]*\s*(%|명|원|달러|조|억|만|배|위|년|개|건|시간|분|초|kg|km|톤|대|편)')

        topic = data.get("topic", self.project_slug)
        summary = data.get("summary", "")

        # 1) key_facts: 각 섹션에서 핵심 내용 추출
        key_facts = []
        for section in data.get("sections", []):
            title = section.get("title", "")
            content = section.get("content", "")
            # 섹션 제목 + 첫 2문장을 fact로 추출
            sentences = [s.strip() for s in re.split(r'[.。]\s*', content) if len(s.strip()) > 20]
            for sent in sentences[:3]:
                key_facts.append({
                    "fact": sent[:200],
                    "section": title,
                    "confidence": "high",
                })

        # 2) statistics: 숫자가 포함된 문장 추출
        statistics = []
        all_text = summary + " " + " ".join(
            s.get("content", "") for s in data.get("sections", [])
        )
        for sentence in re.split(r'[.。]\s*', all_text):
            matches = stat_pattern.findall(sentence)
            if matches and len(sentence.strip()) > 10:
                statistics.append({
                    "text": sentence.strip()[:200],
                    "values": matches[:5],
                })
        # 중복 제거 + 상위 30개
        seen = set()
        unique_stats = []
        for s in statistics:
            key = s["text"][:50]
            if key not in seen:
                seen.add(key)
                unique_stats.append(s)
        statistics = unique_stats[:30]

        # 3) sources: 그대로 복사 (URL, 제목 보존)
        sources = []
        for src in data.get("sources", []):
            sources.append({
                "title": src.get("title", ""),
                "url": src.get("url", ""),
                "reliability": src.get("reliability", "medium"),
            })

        # 4) digest 조립
        digest = {
            "topic": topic,
            "core_thesis": summary[:500] if summary else "",
            "key_facts": key_facts[:30],
            "statistics": statistics,
            "sources": sources,
            "section_titles": [s.get("title", "") for s in data.get("sections", [])],
            "total_sections": len(data.get("sections", [])),
            "total_sources": len(sources),
        }

        digest_path.write_text(
            json.dumps(digest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report_size = report_path.stat().st_size
        digest_size = digest_path.stat().st_size
        ratio = round(digest_size / report_size * 100, 1) if report_size > 0 else 0
        print(f"    [DIGEST] research_digest.json 생성 완료 "
              f"(facts: {len(key_facts)}, stats: {len(statistics)}, "
              f"sources: {len(sources)}, 축약률: {ratio}%)", flush=True)

    def _supplement_research(self, report_path: Path, topic: str, gap_reason: str) -> bool:
        """리서치 보충: 검증 실패 시 누락된 부분만 타겟으로 단일 Claude 호출 후 병합.

        Returns:
            True  — 보충 성공 (report_path 업데이트됨)
            False — 보충 실패 (report_path 변경 없음)
        """
        _notify("research-orchestrator", f"빠진 부분 있어! 보충 조사 나가 — {gap_reason[:60]}",
                phase=self.state.current_phase, project=self.project_slug, level="info")
        print(f"    [보충] 리서치 보충 시작: {gap_reason[:80]}", flush=True)

        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    [WARN] 보충 실패 — 리포트 읽기 오류: {e}")
            return False

        supplement_prompt = (
            f"다음 주제에 대한 리서치 보고서가 있는데, 아래 내용이 누락되어 있습니다.\n\n"
            f"전체 주제: {topic}\n\n"
            f"누락된 내용: {gap_reason}\n\n"
            f"누락된 내용만 집중적으로 조사하여 아래 JSON 형식으로 답하세요.\n"
            f"실제로 알고 있는 정보만 포함하고, 불확실하면 omit하세요.\n\n"
            f"JSON으로만 답하세요:\n"
            f"{{\n"
            f'  "sections": [\n'
            f'    {{"title": "섹션제목", "content": "상세 내용 (500자 이상)"}}\n'
            f"  ],\n"
            f'  "sources": [\n'
            f'    {{"title": "출처명", "url": "https://...", "summary": "요약"}}\n'
            f"  ]\n"
            f"}}"
        )

        try:
            cli_path = self._find_claude_cli()
            proc = subprocess.run(
                [cli_path, "--print", "--output-format", "json",
                 "--model", "claude-sonnet-4-6", "--max-turns", "1"],
                input=supplement_prompt, capture_output=True, text=True, encoding="utf-8",
                cwd=str(self.project_dir), timeout=180,
                env={**os.environ, "CLAUDECODE": ""},
                **subprocess_kwargs(),
            )
            supplement = self._extract_json_from_cli_output(proc.stdout)
            if not supplement:
                print(f"    [WARN] 보충 응답 파싱 실패. stdout: {proc.stdout[:200]}")
                return False

            new_sections = supplement.get("sections", [])
            new_sources = supplement.get("sources", [])
            if not new_sections:
                print(f"    [WARN] 보충 섹션 없음")
                return False

            # 기존 리포트에 병합
            data.setdefault("sections", []).extend(new_sections)
            data.setdefault("sources", []).extend(new_sources)

            report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

            secs = len(data["sections"])
            srcs = len(data["sources"])
            print(f"    [보충] 완료 — {len(new_sections)}섹션 추가 → 총 {secs}섹션, {srcs}소스", flush=True)
            _notify("Director", f"리서치 보충 완료: +{len(new_sections)}섹션 추가",
                    phase=self.state.current_phase, project=self.project_slug, level="success")
            return True

        except Exception as e:
            print(f"    [WARN] 보충 실패: {e}")
            return False

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
                _notify("research-orchestrator", "보고서가 없잖아! 리서치 검증 실패",
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
            topic = self.project.get("topic") or self.state.config.get("topic", self.project_slug)
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
                    input=verify_prompt, capture_output=True, text=True, encoding="utf-8",
                    cwd=str(self.project_dir), timeout=30,
                    env={**os.environ, "CLAUDECODE": ""},
                    **subprocess_kwargs(),
                )
                verify_result = self._extract_json_from_cli_output(proc.stdout)
                if verify_result and verify_result.get("valid"):
                    reason = verify_result.get("reason", "")
                    print(f"    [검증] 리서치: {sections}섹션, {sources}소스, 주제 일치 ✓ ({reason})")
                    _notify("research-orchestrator", f"리서치 완료! {sections}섹션, {sources}소스 확보 — {reason}",
                            phase=self.state.current_phase, project=self.project_slug, level="success")
                    # 볼트 기록
                    if self.vault.enabled:
                        try:
                            self._vault_save_research({"agent": "research-orchestrator"}, result)
                        except Exception as ve:
                            print(f"    [WARN] 볼트 축적 실패: {ve}")
                    # digest 생성 (토큰 최적화)
                    try:
                        self._generate_research_digest()
                    except Exception as e:
                        print(f"    [WARN] digest 생성 실패: {e}", flush=True)
                    return StepResult(step_id=step_id, status="completed")
                elif verify_result:
                    reason = verify_result.get("reason", "주제 불일치")
                    print(f"    [검증] 리서치: 주제 불일치 ✗ ({reason})")
                    # ── 보충 리서치 시도 (최대 1회) ──────────────────────────
                    supplement_ok = self._supplement_research(
                        report_path=report_path,
                        topic=topic,
                        gap_reason=reason,
                    )
                    if supplement_ok:
                        # 재검증
                        data2 = json.loads(report_path.read_text(encoding="utf-8"))
                        summary2 = data2.get("summary", "")[:500]
                        titles2 = [s.get("title", "") for s in data2.get("sections", [])][:10]
                        verify2_prompt = (
                            f"프로젝트 주제: {topic}\n\n"
                            f"리서치 요약:\n{summary2}\n\n"
                            f"섹션 제목: {', '.join(titles2)}\n\n"
                            f"이 리서치가 프로젝트 주제에 적합한지 판단하세요.\n"
                            f"JSON으로만 답하세요: {{\"valid\": true/false, \"reason\": \"한줄 사유\"}}"
                        )
                        try:
                            proc2 = subprocess.run(
                                [cli_path, "--print", "--output-format", "json",
                                 "--model", "claude-haiku-4-5-20251001", "--max-turns", "1"],
                                input=verify2_prompt, capture_output=True, text=True, encoding="utf-8",
                                cwd=str(self.project_dir), timeout=30,
                                env={**os.environ, "CLAUDECODE": ""},
                                **subprocess_kwargs(),
                            )
                            verify2 = self._extract_json_from_cli_output(proc2.stdout)
                            if verify2 and verify2.get("valid"):
                                r2 = verify2.get("reason", "")
                                secs2 = len(data2.get("sections", []))
                                srcs2 = len(data2.get("sources", []))
                                print(f"    [검증] 보충 후 재검증 ✓ ({r2})")
                                _notify("Director", f"리서치 보충 완료: {secs2}섹션, {srcs2}소스 — {r2}",
                                        phase=self.state.current_phase, project=self.project_slug, level="success")
                                if self.vault.enabled:
                                    try:
                                        self._vault_save_research({"agent": "research-orchestrator"}, result)
                                    except Exception as ve:
                                        print(f"    [WARN] 볼트 축적 실패: {ve}")
                                # digest 생성 (토큰 최적화)
                                try:
                                    self._generate_research_digest()
                                except Exception as e:
                                    print(f"    [WARN] digest 생성 실패: {e}")
                                return StepResult(step_id=step_id, status="completed")
                            else:
                                r2 = (verify2 or {}).get("reason", "보충 후에도 불일치")
                                print(f"    [검증] 보충 후 재검증 ✗ ({r2})")
                        except Exception as e2:
                            print(f"    [WARN] 보충 재검증 실패 ({e2})")
                    return StepResult(step_id=step_id, status="failed", error=f"리서치 주제 불일치: {reason}")
            except Exception as e:
                print(f"    [WARN] LLM 검증 실패 ({e}), 구조 검증만 통과")

            # LLM 검증 실패해도 구조 검증 통과면 진행
            print(f"    [검증] 리서치: {sections}섹션, {sources}소스 ✓ (구조 검증)")
            _notify("research-orchestrator", f"보고서 확인! {sections}섹션, {sources}소스",
                    phase=self.state.current_phase, project=self.project_slug, level="success")
            # digest 생성 (토큰 최적화)
            try:
                self._generate_research_digest()
            except Exception as e:
                print(f"    [WARN] digest 생성 실패: {e}")
            return StepResult(step_id=step_id, status="completed")

        elif step_id == "step_2":
            # script-director → scene_specs.json 직접 출력
            specs_path = self.project_dir / "scene_specs.json"
            ms_path = self.project_dir / "final_manuscript.md"
            if specs_path.exists():
                try:
                    data = json.loads(specs_path.read_text(encoding="utf-8"))
                    n_scenes = len(data.get("scenes", []))
                    version = data.get("version", "?")
                    if n_scenes > 0:
                        # 플랫 스키마 검증: narration + layout + motion 필드 존재 확인
                        sample = data["scenes"][0]
                        has_flat = all(k in sample for k in ("narration", "layout", "motion"))
                        schema_tag = f"v{version} 플랫" if has_flat else f"v{version}"
                        print(f"    [검증] 원고+연출: {n_scenes}씬, {schema_tag} 스키마 ✓")
                        _notify("script-director", f"원고 완성! {n_scenes}씬 완성, {schema_tag}",
                                phase=self.state.current_phase, project=self.project_slug, level="success")
                    else:
                        return StepResult(step_id=step_id, status="failed", error="scene_specs.json에 씬 0개")
                except Exception as e:
                    return StepResult(step_id=step_id, status="failed", error=f"scene_specs.json 파싱 실패: {e}")
            elif ms_path.exists():
                # fallback: final_manuscript.md 기반 검증
                text = ms_path.read_text(encoding="utf-8")
                chars = len(text)
                print(f"    [검증] 원고: {chars}자")
                _notify("Director", f"원고 검증: {chars}자",
                        phase=self.state.current_phase, project=self.project_slug, level="success")
            else:
                return StepResult(step_id=step_id, status="failed", error="scene_specs.json 또는 final_manuscript.md 미생성")

        elif step_id in ("step_4", "step_2b"):
            # 팩트체크 결과 확인 — adjusted 항목 원고 자동 반영
            report_path = self.project_dir / "factcheck_report.json"
            if report_path.exists():
                try:
                    report = json.loads(report_path.read_text(encoding="utf-8"))
                    claims = report.get("claims", report.get("results", []))
                    adjusted = [c for c in claims if c.get("status") == "adjusted" or c.get("action") == "adjust"]

                    if adjusted:
                        print(f"    [팩트체크] 수정 권장 {len(adjusted)}건 발견 — 원고 자동 수정")
                        _notify("Director", f"백팩트가 {len(adjusted)}건 잡았어! 원고 자동 수정 들어간다",
                                phase=self.state.current_phase, project=self.project_slug, level="warning")

                        # scene_specs.json의 narration에서 매칭+치환
                        specs_path = self.project_dir / "scene_specs.json"
                        if specs_path.exists():
                            specs = json.loads(specs_path.read_text(encoding="utf-8"))
                            applied = 0
                            for item in adjusted:
                                original = item.get("original_text", "") or item.get("claim", "")
                                corrected = item.get("corrected_text", "") or item.get("suggestion", "")
                                if not original or not corrected:
                                    continue
                                for scene in specs.get("scenes", []):
                                    narr = scene.get("narration", "")
                                    if original in narr:
                                        scene["narration"] = narr.replace(original, corrected)
                                        print(f"    [수정] 씬#{scene.get('sceneNumber')}: \"{original[:30]}\" → \"{corrected[:30]}\"")
                                        applied += 1
                            specs_path.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
                            if applied:
                                _notify("script-director", f"원고 수정 완료! {applied}건 반영됨",
                                        phase=self.state.current_phase, project=self.project_slug, level="success")
                            else:
                                print(f"    [팩트체크] 수정 권장 {len(adjusted)}건 중 원고 내 매칭 없음 — 수동 확인 필요")
                    else:
                        print(f"    [팩트체크] 수정 권장 항목 없음 ✓")
                except Exception as e:
                    print(f"    [WARN] 팩트체크 보고서 파싱 실패: {e}")


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
                    _notify("Director", f"이런... {_step_label(step_name, 'fail')} 문제 발생. 파이프라인 중단!", phase=self.state.current_phase, project=self.project_slug, level="error")
                    self.state.failed_steps.append(step["id"])
                    return
                # non-blocking이면 계속
                if step.get("blocking") is False:
                    print(f"  [WARN] {step['id']} failed (non-blocking) — 계속 진행")
                    _notify("Director", f"{_step_label(step_name, 'fail')} 실패했지만 괜찮아, 계속 간다!", phase=self.state.current_phase, project=self.project_slug, level="warning")
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

        # sceneNumber 중복 검증
        seen = set()
        for scene in merged_scenes:
            sn = scene.get("sceneNumber")
            if sn in seen:
                logger.warning("sceneNumber %s 중복 발견 — 첫 번째만 유지", sn)
            seen.add(sn)
        # 중복 제거 (첫 번째 유지)
        deduped = []
        seen.clear()
        for scene in merged_scenes:
            sn = scene.get("sceneNumber")
            if sn not in seen:
                deduped.append(scene)
                seen.add(sn)
        merged_scenes = deduped

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
        agent_name = step.get("agent", "script-director")
        label = _step_label(step_name, "start").replace(" 시작합니다", "")

        # scene_specs 로드 (없으면 scene_decomposition.json에서 폴백)
        # scene_specs가 아직 없는 생성 단계(script-director 등)는 단일 agent로 전환
        specs_path = self.project_dir / "scene_specs.json"
        if not specs_path.exists():
            decomp_path = self.project_dir / "scene_decomposition.json"
            if decomp_path.exists():
                # step_6(creative_direction)은 scene_decomposition → scene_specs 변환
                decomp = json.loads(decomp_path.read_text(encoding="utf-8"))
                original_specs = self._decomp_to_specs(decomp)
                specs_path.write_text(
                    json.dumps(original_specs, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            else:
                # scene_specs 생성 단계 (script-director 첫 호출) — 자연스러운 시작 알림
                _notify(agent_name, "Stage 2 시작",
                        phase=self.state.current_phase, project=self.project_slug, level="info")
                return self._run_agent_step(step)
        else:
            original_specs = json.loads(specs_path.read_text(encoding="utf-8"))
        chapters = self._split_by_chapter(original_specs)

        # chapter 필드 없으면 단일 instance로 진행 (정상 흐름)
        if chapters is None:
            _notify(agent_name, "Stage 2 시작",
                    phase=self.state.current_phase, project=self.project_slug, level="info")
            return self._run_agent_step(step)

        n_chapters = len(chapters)
        total_scenes = len(original_specs.get("scenes", []))

        try:
            self.pm.update_project(self.project["id"], scene_count=total_scenes)
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
                                scene["imageAsset"] = {
                                    "source": "generate",
                                    "placement": "fullscreen",
                                    "query": scene.get("narration", "")[:200],
                                }
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
        agent_name = step.get("agent", "script-director")
        label = _step_label(step_name, "start").replace(" 시작합니다", "")

        n_scenes = len(chapter_scenes)
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
        # 스텝의 mode 필드를 에이전트에 전달 (예: script-director의 outline/chapters/consistency)
        _mode = step.get("mode")
        if _mode and agent_name == "script-director":
            env["SCRIPT_DIRECTOR_MODE"] = _mode
            env["SCRIPT_DIRECTOR_CHAPTER"] = str(chapter_num)
        env.pop("CLAUDECODE", None)

        _popen_flags = subprocess_kwargs()
        try:
            proc = subprocess.Popen(
                cmd, cwd=str(self.project_dir), env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8",
                **_popen_flags,
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

        return ChapterResult(
            chapter=chapter_num, status="completed",
            scenes=updated_scenes,
            cost_info=cost_info, duration_sec=elapsed,
        )

    # 스텝별 전용 프롬프트 파일 매핑 (step_name → 프롬프트 파일명)
    # single_call 및 chunked_parallel agent 스텝 모두에서 사용
    # (step_6 creative_direction은 agent 타입이지만 동일한 프롬프트 로딩 경로 사용)
    SINGLE_CALL_PROMPTS = {
        "data_enrichment": "data-enrichment.md",
    }

    _WRITING_STYLE_SKILLS = frozenset({"writing-style-semoji", "writing-style-iromism"})

    def _filter_writing_style_skills(self, skill_names: list) -> list:
        """비활성 writing style 스킬 제거 + 활성 스킬 자동 주입."""
        writing_style = (self.state.config or {}).get("writing_style", "")
        active = f"writing-style-{writing_style}" if writing_style else None
        filtered = [
            s for s in skill_names
            if s not in self._WRITING_STYLE_SKILLS or s == active
        ]
        if active and active not in filtered:
            filtered.append(active)
        return filtered

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

        # 컨텍스트 파일 빌드 (챕터 스코프)
        context_block = ""
        # 리서치: 챕터별 facts 우선 (compact), 없으면 digest fallback
        chapter_facts_path = self.project_dir / "chapter_facts" / f"chapter_{chapter_num}.json"
        if chapter_facts_path.exists():
            context_block += f'\n<file name="chapter_facts/chapter_{chapter_num}.json">\n{chapter_facts_path.read_text(encoding="utf-8")[:10000]}\n</file>\n'
        else:
            for fname in ["research_digest.json", "research_report.json"]:
                fpath = self.project_dir / fname
                if fpath.exists():
                    context_block += f"\n<file name=\"{fname}\">\n{fpath.read_text(encoding='utf-8')[:20000]}\n</file>\n"
                    break
        # outline: 해당 챕터 슬라이스만 추출
        outline_path = self.project_dir / "outline.json"
        if outline_path.exists():
            try:
                outline_data = json.loads(outline_path.read_text(encoding="utf-8"))
                chapters = outline_data.get("chapters", [])
                chapter_entry = next((c for c in chapters if c.get("id") == chapter_num), None)
                if chapter_entry:
                    context_block += f'\n<file name="outline.json (챕터 {chapter_num} 슬라이스)">\n{json.dumps(chapter_entry, ensure_ascii=False, indent=2)}\n</file>\n'
                else:
                    context_block += f'\n<file name="outline.json">\n{json.dumps(outline_data, ensure_ascii=False, indent=2)[:8000]}\n</file>\n'
            except Exception:
                context_block += f'\n<file name="outline.json">\n{outline_path.read_text(encoding="utf-8")[:8000]}\n</file>\n'

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
        # 로컬 파일 우선
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

        skill_names = self._filter_writing_style_skills(skill_names)
        skill_refs = agent_def.get("skill_refs", {})
        skill_limits = agent_def.get("skill_limits", {})
        shared_skills_text = ""
        for skill_name in skill_names:
            content = self._load_shared_skill(skill_name, skill_refs.get(skill_name))
            if content:
                limit = skill_limits.get(skill_name)
                if limit and len(content) > limit:
                    content = content[:limit]
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"

        # 공통 컨텍스트 파일 (챕터 스코프 — 글로벌 전체 반복 금지)
        context_block = ""
        # 리서치: 챕터별 facts 우선 (compact), 없으면 digest fallback
        chapter_facts_path = self.project_dir / "chapter_facts" / f"chapter_{chapter_num}.json"
        if chapter_facts_path.exists():
            context_block += f'\n<file name="chapter_facts/chapter_{chapter_num}.json">\n{chapter_facts_path.read_text(encoding="utf-8")[:10000]}\n</file>\n'
        else:
            for fname in ["research_digest.json", "research_report.json"]:
                fpath = self.project_dir / fname
                if fpath.exists():
                    context_block += f"\n<file name=\"{fname}\">\n{fpath.read_text(encoding='utf-8')[:20000]}\n</file>\n"
                    break
        # outline: 해당 챕터 슬라이스만 추출
        outline_path = self.project_dir / "outline.json"
        if outline_path.exists():
            try:
                outline_data = json.loads(outline_path.read_text(encoding="utf-8"))
                chapters = outline_data.get("chapters", [])
                chapter_entry = next((c for c in chapters if c.get("id") == chapter_num), None)
                if chapter_entry:
                    context_block += f'\n<file name="outline.json (챕터 {chapter_num} 슬라이스)">\n{json.dumps(chapter_entry, ensure_ascii=False, indent=2)}\n</file>\n'
                else:
                    context_block += f'\n<file name="outline.json">\n{json.dumps(outline_data, ensure_ascii=False, indent=2)[:8000]}\n</file>\n'
            except Exception:
                context_block += f'\n<file name="outline.json">\n{outline_path.read_text(encoding="utf-8")[:8000]}\n</file>\n'

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

        _mode_line = ""
        _step_mode = step.get("mode")
        if _step_mode:
            _mode_line = f"\nSCRIPT_DIRECTOR_MODE: {_step_mode}\nSCRIPT_DIRECTOR_CHAPTER: {chapter_num}"

        prompt = f"""<system_context>
프로젝트: {self.project_slug}
작업 디렉토리: {self.project_dir}
워크스페이스: {get_workspace_dir()}
챕터: {chapter_num} (챕터별 병렬 처리 모드){_mode_line}
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
                "mapScene": None,
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
                # imageAsset 머지 (top-level 우선, visualization에서 승격 fallback)
                if "imageAsset" in llm and llm["imageAsset"]:
                    result["imageAsset"] = llm["imageAsset"]
                elif llm.get("visualization", {}).get("imageAsset"):
                    result["imageAsset"] = llm["visualization"]["imageAsset"]
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

        # cinematic 씬 검증: placement=fullscreen 강제
        for scene in merged:
            creative = (scene.get("visualization") or {}).get("creative") or {}
            if creative.get("layout") == "cinematic":
                if not scene.get("imageAsset"):
                    scene["imageAsset"] = {"source": "generate", "placement": "fullscreen"}
                else:
                    scene["imageAsset"]["placement"] = "fullscreen"
                    if "opacity" in scene["imageAsset"]:
                        del scene["imageAsset"]["opacity"]

        return merged

    def _auto_build_and_capture(self, chapter_results: dict, chapters: dict):
        """병합 완료 후 자동 매니페스트 빌드. (썸네일 캡처 비활성화)"""
        _notify("assembly-director", "매니페스트 조립 시작해",
                phase=self.state.current_phase, project=self.project_slug)

        # 1. 매니페스트 빌드
        try:
            pid = str(self.project.get("id", self.project_slug))
            storage_key = self.sync.storage_key if self.sync else self.project_slug
            result = subprocess.run(
                [sys.executable, "-m", "auto_agent.scripts.build_manifest",
                 pid, storage_key, str(self.project_dir)],
                cwd=str(get_workspace_dir()),
                capture_output=True, text=True, encoding="utf-8", timeout=120,
                **subprocess_kwargs(),
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
            _thumb_env = get_env_with_node()
            node = shutil.which("node", path=_thumb_env.get("PATH"))
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
                capture_output=True, text=True, encoding="utf-8",
                timeout=300,
                **subprocess_kwargs(),
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

            _notify("System", f"기준 캐릭터 '{char_id}' 이미지 없음 — 재생성 필요",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="warning")

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

        # ── Pre-step 훅 실행 ──
        try:
            self.hooks.run_pre_step(step_id, {
                "project_dir": str(self.project_dir),
                "step_id": step_id,
                "step_name": step_name,
            })
        except ValueError as e:
            print(f"  [HOOK] {step_id} pre-step 차단: {e}")
            return StepResult(step_id=step_id, status="failed", error=f"Hook 차단: {e}")

        # 이미지 소싱 전 아트스타일/캐릭터 프리플라이트
        if step_name == "image_asset_sourcing":
            self._ensure_art_style_and_characters()

        self.state.current_step = step_id
        print(f"  [{step_id}] {step_name} ... ", end="", flush=True)
        _agent_label = step.get("agent") or step.get("module", "System")
        _notify(_agent_label, _step_label(step_name, "start"), phase=self.state.current_phase, project=self.project_slug)
        self._emit_pipeline_event("step_started", {"step_name": step_name, "agent": _agent_label})

        # DB 파이프라인 기록 시작
        run_id = self.pm.start_pipeline_run(
            project_id=self.project["id"],
            phase=self.state.current_phase,
            step=step_id,
            step_name=step_name,
            agent_or_module=step.get("agent") or step.get("module"),
        )

        t0 = time.time()
        max_attempts = self._get_step_max_attempts(step)
        result = StepResult(step_id=step_id, status="failed", error="Unknown step type")
        _prev_timeout = False

        try:
            # 래칫 루프 타입은 별도 처리
            if step_type == "ratchet_loop":
                result = self._run_ratchet_loop(step)
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
                else:
                    self.pm.fail_pipeline_run(run_id, result.error or "ratchet loop failed")
                    print(f"FAIL ({result.error})")
                return result

            for _attempt in range(max_attempts):
                if step_type == "single_call":
                    result = self._run_single_call_step(step)
                elif step.get("agent"):
                    result = self._run_agent_step(step)
                elif step.get("module"):
                    result = self._run_module_step(step)
                else:
                    result = StepResult(step_id=step_id, status="skipped",
                                        error="Unknown step type")
                    break

                if result.status == "completed":
                    break

                # ── 재시도 여부 판단 ──
                _is_timeout = "타임아웃" in (result.error or "")
                _retryable  = self._is_retryable_error(result.error)
                _consec_timeout = _is_timeout and _prev_timeout  # 연속 타임아웃 → 중단

                if not _retryable or _consec_timeout or _attempt >= max_attempts - 1:
                    break  # 더 이상 재시도 없음

                # 재시도 대기: 타임아웃은 즉시, rate-limit은 reset 시각 반영
                _wait = self._compute_retry_wait(result.error or "", _attempt, _is_timeout)
                _retry_label = (
                    f"재시도 {_attempt + 1}/{max_attempts - 1} — "
                    f"{(result.error or '')[:50]} "
                    f"({'즉시' if _wait == 0 else f'{_wait}초 후'})"
                )
                print(f"\n    ↻ {_retry_label}", flush=True)
                _notify(
                    _agent_label, _retry_label,
                    phase=self.state.current_phase, project=self.project_slug,
                    level="warning",
                )
                if _wait > 0:
                    time.sleep(_wait)
                _prev_timeout = _is_timeout

            elapsed = time.time() - t0
            result.duration_sec = elapsed

            if result.status == "completed":
                # ── Post-step 훅 실행 ──
                try:
                    self.hooks.run_post_step(step_id, {
                        "project_dir": str(self.project_dir),
                        "step_id": step_id,
                        "step_name": step_name,
                        "duration_sec": elapsed,
                    })
                except ValueError as hook_err:
                    print(f"  [HOOK] {step_id} post-step 경고: {hook_err}")

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
                self._emit_pipeline_event("step_completed", {
                    "step_name": step_name,
                    "agent": _agent_label,
                    "duration_sec": elapsed,
                    "cost_usd": cost.get("cost_usd", 0.0),
                })

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
            self._emit_pipeline_event("step_failed", {
                "step_name": step_name,
                "agent": _agent_label,
                "duration_sec": elapsed,
                "error": str(e)[:200],
            })
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
                    context_block += f"\n<file name=\"{inp}\">\n{inp_path.read_text(encoding='utf-8')[:30000]}\n</file>\n"

            template = self.rule_manager.load(f"prompts/single-call/{prompt_file}")
            art_style_override = self._load_art_style_override(step_name)
            specs_path = self._resolve_output_path("scene_specs.json")
            if specs_path.exists():
                chapter_specs_json = specs_path.read_text(encoding="utf-8")[:30000]
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

        # SDK 단일 호출 (prompt caching 적용)
        print(f"[single_call SDK] model={target_model}", flush=True)
        t0 = time.time()

        # SKILL.md + shared_skills → static (캐시), 나머지 → dynamic
        agent_skill = self._load_skill_file(f"skills/agents/{agent}/SKILL.md") if agent else ""
        agents_config = self._load_agents_config()
        agent_def_sc = agents_config.get("subagents", {}).get(agent, {})
        skill_names_sc = list(step.get("skills", []))
        for s in agent_def_sc.get("skills", []):
            if s not in skill_names_sc:
                skill_names_sc.append(s)
        shared_skills_sc = ""
        for sn in skill_names_sc:
            c = self._load_shared_skill(sn)
            if c:
                shared_skills_sc += f"\n\n## {sn}\n\n{c}"

        static_system_sc = (
            (f"<agent_skill>\n{agent_skill}\n</agent_skill>" if agent_skill else "")
            + (f"\n\n<shared_skills>{shared_skills_sc}\n</shared_skills>" if shared_skills_sc else "")
        )
        # static이 없으면 빈 dynamic 하나로 처리
        dynamic_system_sc = ""
        user_message_sc = prompt

        try:
            sdk_client = CachingClaudeClient()
            response_text, usage = sdk_client.call_single(
                model=target_model,
                static_system=static_system_sc,
                dynamic_system=dynamic_system_sc,
                user_message=user_message_sc,
                max_tokens=8192,
            )
        except Exception as exc:
            return StepResult(step_id=step_id, status="failed", error=str(exc))

        elapsed = time.time() - t0
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        print(
            f"    [SDK] elapsed={elapsed:.1f}s in={usage['input_tokens']:,} "
            f"out={usage['output_tokens']:,} cache_read={cache_read:,} cache_write={cache_write:,}",
            flush=True,
        )

        # SDK 응답 → 기존 JSON 파싱 로직 재사용
        elapsed = time.time() - t0
        cost_info = {}

        # SDK 텍스트에서 JSON 추출 (마크다운 코드블록 포함 처리)
        content = self._extract_json_from_cli_output(response_text)
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

    # ── SDK 모드 (prompt caching) ─────────────────────────────────────────

    def _build_sdk_prompt_parts(self, step: dict) -> tuple[str, str, str]:
        """프롬프트를 캐시 가능한 세 부분으로 분리.

        Returns:
            (static_system, dynamic_system, user_task)
            - static_system : SKILL.md + shared_skills  → cache_control 적용
            - dynamic_system: system_context + project_config + progress_reporting
            - user_task     : vault_block + task + context_memory
        """
        agent_name = step["agent"]

        # 1. SKILL.md + shared_skills (정적 — 캐시 대상)
        agent_skill = self._load_skill_file(f"skills/agents/{agent_name}/SKILL.md")
        skill_names = list(step.get("skills", []))
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        for s in agent_def.get("skills", []):
            if s not in skill_names:
                skill_names.append(s)
        skill_names = self._filter_writing_style_skills(skill_names)
        skill_refs = agent_def.get("skill_refs", {})
        skill_limits = agent_def.get("skill_limits", {})
        shared_skills_text = ""
        for skill_name in skill_names:
            content = self._load_shared_skill(skill_name, skill_refs.get(skill_name))
            if content:
                limit = skill_limits.get(skill_name)
                if limit and len(content) > limit:
                    content = content[:limit]
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"

        static_system = (
            f"<agent_skill>\n{agent_skill}\n</agent_skill>"
            + (f"\n\n<shared_skills>{shared_skills_text}\n</shared_skills>" if shared_skills_text else "")
        )

        # 2. dynamic system (호출마다 달라지는 컨텍스트)
        config = self.state.config
        duration_min = config.get("duration_minutes", 10)
        target_chars = {1: 400, 3: 1200, 5: 2000, 10: 4000}.get(duration_min, duration_min * 400)
        art_style = config.get("art_style", "")
        writing_style = config.get("writing_style", "")
        _mode_line = f"\nSCRIPT_DIRECTOR_MODE: {step['mode']}" if step.get("mode") else ""

        dynamic_system = f"""<system_context>
프로젝트: {self.project_slug}
작업 디렉토리: {self.project_dir}
워크스페이스: {get_workspace_dir()}{_mode_line}
</system_context>

<project_config>
영상 분량: {duration_min}분
목표 나레이션 글자 수: 약 {target_chars}자 (±10%)
아트스타일: {art_style}
문체 스타일: {writing_style}
{"**이로미즘 문체 필수 적용** — writing-style-iromism 스킬의 규칙을 반드시 따르세요." if writing_style == "iromism" else ""}
{"**세모지 문체 필수 적용** — writing-style-semoji 스킬의 규칙을 반드시 따르세요." if writing_style == "semoji" else ""}
</project_config>

{self._build_progress_block(step.get('id', ''))}"""

        # 3. user task (vault + task + context_memory)
        vault_block = ""
        if self.vault.enabled and agent_name == "research-orchestrator":
            topic = self.state.config.get("topic", self.project_slug)
            category = self.state.config.get("category", "")
            vault_block = self.vault.search_for_research(topic, category)

        _skip_brief_steps = {"data-mapper", "fact-verifier", "assembly-director"}
        # editorial_brief.json 주입 (기획 의도 상위 컨텍스트)
        editorial_brief = self._load_editorial_brief()
        if editorial_brief and agent_name not in _skip_brief_steps:
            vault_block += f"\n\n<editorial_brief>\n{editorial_brief}\n\n⚠️ 이 brief는 모든 리서치·원고·연출 결정의 상위 컨텍스트입니다.\n- real_topic을 중심에 두고, hook_angle은 도입부에만 사용하세요\n- excluded_angles에 해당하는 방향으로 흘러가지 마세요\n- core_question에 대한 답변이 콘텐츠의 핵심이어야 합니다\n</editorial_brief>"

        creative_brief = self.state.config.get("creative_brief", "")
        if creative_brief and agent_name not in _skip_brief_steps:
            vault_block += f"\n\n<creative_brief>\n{creative_brief}\n</creative_brief>"

        # manuscript 모드: 참조 원고 주입
        if agent_name == "script-director" and step.get("mode") == "manuscript":
            ref_block = self._build_manuscript_reference_block()
            if ref_block:
                vault_block += "\n\n" + ref_block

        # 입출력 경로
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        input_lines = []
        for inp in inputs:
            resolved = self._resolve_output_path(inp)
            tag = "✓" if resolved.exists() else "✗ MISSING"
            input_lines.append(f"- {inp}: {resolved} [{tag}]")

        outputs = step.get("output", [])
        if isinstance(outputs, str):
            outputs = [outputs]
        output_lines = [
            f"- {out}: {self._resolve_output_path(out)}" for out in outputs
        ]

        context_memory_block = self.context_memory.build_context_prompt(step.get("id", ""))

        user_task = f"""{vault_block}

<task>
Step: {step.get("id", "")} — {step.get("name", "")}
{step.get("description", "")}
{step.get("notes", "")}

입력 파일:
{chr(10).join(input_lines) if input_lines else "- 없음"}

출력 파일 (반드시 아래 경로에 저장):
{chr(10).join(output_lines)}

{self._build_previous_review_context(step)}
{self._build_revision_instruction(step)}
모든 출력 파일을 성공적으로 생성하면 작업 완료입니다.
</task>

{context_memory_block}"""

        return static_system, dynamic_system, user_task

    def _run_sdk_single_step(
        self,
        step_id: str,
        static_system: str,
        dynamic_system: str,
        user_task: str,
        model: str,
        outputs: list,
        timeout_sec: float = 300,
    ) -> "StepResult":
        """도구 없는 단일 SDK 호출 (fact-verifier, digest 생성 등)."""
        import time as _time
        t0 = _time.time()
        client = CachingClaudeClient()
        try:
            text, usage = client.call_single(
                model=model,
                static_system=static_system,
                dynamic_system=dynamic_system,
                user_message=user_task,
                max_tokens=8192,
            )
        except Exception as exc:
            return StepResult(step_id=step_id, status="failed", error=str(exc))

        elapsed = _time.time() - t0
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        print(
            f"    [SDK single] model={model} elapsed={elapsed:.1f}s "
            f"in={usage['input_tokens']:,} out={usage['output_tokens']:,} "
            f"cache_read={cache_read:,} cache_write={cache_write:,}",
            flush=True,
        )

        output_files = [str(self._resolve_output_path(o)) for o in outputs if "{" not in o]
        return StepResult(
            step_id=step_id,
            status="completed",
            output_files=output_files,
            duration_sec=elapsed,
        )

    def _run_sdk_agent_step(
        self,
        step: dict,
        step_id: str,
        model: str,
        max_turns: int,
        static_system: str,
        dynamic_system: str,
        user_task: str,
        outputs: list,
        timeout_sec: float = 1800,
    ) -> "StepResult":
        """멀티턴 SDK 에이전트 루프 (로컬 파일 도구: Read/Write/Edit/Glob)."""
        import time as _time
        t0 = _time.time()
        client = CachingClaudeClient()

        progress_path = self.project_dir / f".progress_{step_id}.jsonl"
        monitor = ProgressFileMonitor(progress_path, self.project_slug, self.state.current_phase)
        monitor.start()

        def on_tool_call(tool_name: str, tool_input: dict) -> None:
            print(f"      [tool] {tool_name} {str(tool_input)[:80]}", flush=True)

        try:
            _text, usage = client.call_agent(
                model=model,
                static_system=static_system,
                dynamic_system=dynamic_system,
                initial_message=user_task,
                tools=LOCAL_TOOL_SCHEMAS,
                tool_handler=handle_local_tool,
                max_turns=max_turns,
                on_tool_call=on_tool_call,
            )
        except Exception as exc:
            monitor.stop()
            return StepResult(step_id=step_id, status="failed", error=str(exc))
        finally:
            monitor.stop()

        elapsed = _time.time() - t0
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_write = usage.get("cache_creation_input_tokens", 0)
        print(
            f"    [SDK agent] model={model} turns≤{max_turns} elapsed={elapsed:.1f}s "
            f"in={usage['input_tokens']:,} out={usage['output_tokens']:,} "
            f"cache_read={cache_read:,} cache_write={cache_write:,}",
            flush=True,
        )

        # 출력 파일 존재 확인
        all_exist = all(
            self._resolve_output_path(o).exists()
            for o in outputs if "{" not in o
        ) if outputs else True

        if not all_exist:
            missing = [o for o in outputs if not self._resolve_output_path(o).exists()]
            return StepResult(
                step_id=step_id, status="failed",
                error=f"출력 파일 미생성: {missing}",
                duration_sec=elapsed,
            )

        output_files = [str(self._resolve_output_path(o)) for o in outputs if "{" not in o]
        return StepResult(
            step_id=step_id,
            status="completed",
            output_files=output_files,
            duration_sec=elapsed,
        )

    # ── CLI 모드 (기존) ──────────────────────────────────────────────────

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
        # skip_resume=True인 경우 resume 체크 비활성화 (래칫 루프 등)
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        input_set = set(inputs)
        has_inplace_output = any(out in input_set for out in outputs)

        if step.get("skip_resume"):
            pass  # 래칫 루프 등 강제 재실행
        elif not has_inplace_output:
            all_exist = True
            for out in outputs:
                out_path = self._resolve_output_path(out)
                if out.endswith("/") or out.endswith("\\"):
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

        # ── 에이전트 설정 ──

        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent, {})
        if not agent_def:
            return StepResult(
                step_id=step_id, status="failed",
                error=f"agents.json에 '{agent}' 정의 없음",
            )

        model = step.get("model") or agent_def.get("model", "claude-sonnet-4-5-20250929")
        max_turns = agent_def.get("max_turns", 30)
        allowed_tools = agent_def.get("allowed_tools", ["Read", "Write", "Glob"])
        budget = self._get_agent_budget(agent)
        timeout_sec = self._get_agent_timeout(agent)

        # ── SDK 모드 라우팅 (use_sdk: true 에이전트) ──
        if agent_def.get("use_sdk", False):
            static_system, dynamic_system, user_task = self._build_sdk_prompt_parts(step)
            print(f"\n    → SDK {agent} (model={model}, max_turns={max_turns})", flush=True)
            return self._run_sdk_agent_step(
                step=step,
                step_id=step_id,
                model=model,
                max_turns=max_turns,
                static_system=static_system,
                dynamic_system=dynamic_system,
                user_task=user_task,
                outputs=outputs,
                timeout_sec=timeout_sec,
            )

        # ── Claude CLI 서브프로세스 실행 ──

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
        elif agent == "script-director":
            # 분량별 스케일링: 분당 180초 + 베이스 600초
            # 5분→1500s(25분), 10분→2400s(40분), 15분→3300s(55분)
            scaled = 600 + duration_min * 180
            timeout_sec = max(timeout_sec, scaled)
        elif agent == "assembly-director":
            # 씬 수에 비례해 타임아웃 스케일링: 씬당 ~60초 + 베이스 600s
            scene_count = self._count_image_scenes()
            scaled = 600 + scene_count * 60
            timeout_sec = max(timeout_sec, scaled)

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
        # 스텝의 mode 필드를 에이전트에 전달 (script-director 단일 에이전트 다단계 모드)
        _mode = step.get("mode")
        if _mode and agent == "script-director":
            env["SCRIPT_DIRECTOR_MODE"] = _mode
        # Claude Code 중첩 세션 방지 해제
        env.pop("CLAUDECODE", None)

        progress_path = self.project_dir / f".progress_{step_id}.jsonl"
        env["PROGRESS_FILE"] = str(progress_path)
        monitor = ProgressFileMonitor(progress_path, self.project_slug, self.state.current_phase)
        monitor.start()

        # 프롬프트를 stdin으로 전달
        prompt_text = prompt_file.read_text(encoding="utf-8")

        # 원고/씬 생성 스텝은 stream-json 모드로 실시간 스트리밍
        # step_2: json 모드에서 대형 JSON 직렬화 시 exit_code=143 발생 → stream-json으로 전환
        _STREAMING_STEPS = {"step_2_draft", "step_2_manuscript", "step_2"}
        stream_file: Optional[Path] = None
        if step_id in _STREAMING_STEPS:
            # --output-format json → stream-json 으로 교체
            stream_cmd = []
            i = 0
            while i < len(cmd):
                if cmd[i] == "--output-format" and i + 1 < len(cmd) and cmd[i+1] == "json":
                    stream_cmd.extend(["--output-format", "stream-json"])
                    if "--verbose" not in stream_cmd:
                        stream_cmd.append("--verbose")
                    i += 2
                else:
                    stream_cmd.append(cmd[i])
                    i += 1
            cmd = stream_cmd
            stream_file = self.project_dir / ".manuscript_stream.md"
            stream_file.write_text("", encoding="utf-8")  # 초기화

        _popen_flags3 = subprocess_kwargs()
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(self.project_dir),
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding="utf-8",
                **_popen_flags3,
            )

            if stream_file is not None:
                # 스트리밍 모드: 스레드로 stdin/stdout/stderr 동시 처리
                stdout_lines: list[str] = []
                stderr_lines: list[str] = []
                accumulated_text: list[str] = []

                def _write_stdin():
                    try:
                        proc.stdin.write(prompt_text)
                        proc.stdin.close()
                    except Exception:
                        pass

                def _read_stdout():
                    for line in proc.stdout:
                        stdout_lines.append(line)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            if data.get("type") == "assistant":
                                for block in data.get("message", {}).get("content", []):
                                    if block.get("type") == "text":
                                        accumulated_text.append(block["text"])
                                        try:
                                            stream_file.write_text(
                                                "".join(accumulated_text), encoding="utf-8"
                                            )
                                        except Exception:
                                            pass
                        except (json.JSONDecodeError, KeyError):
                            pass

                def _read_stderr():
                    for line in proc.stderr:
                        stderr_lines.append(line)

                t_in = threading.Thread(target=_write_stdin, daemon=True)
                t_out = threading.Thread(target=_read_stdout, daemon=True)
                t_err = threading.Thread(target=_read_stderr, daemon=True)
                t_in.start(); t_out.start(); t_err.start()
                try:
                    proc.wait(timeout=timeout_sec)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    return StepResult(
                        step_id=step_id, status="failed",
                        error=f"Claude CLI 타임아웃 ({timeout_sec}s)",
                    )
                t_in.join(); t_out.join(timeout=5); t_err.join(timeout=5)
                stdout = "".join(stdout_lines)
                stderr = "".join(stderr_lines)
            else:
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
            detail = self._extract_cli_error_message(result.stdout, result.stderr)[:500]
            return StepResult(
                step_id=step_id, status="failed",
                error=f"출력 파일 미생성: {missing}. "
                      f"exit_code={result.returncode}. {detail}",
                cost_info=cost_info,
            )
        else:
            error = self._extract_cli_error_message(result.stdout, result.stderr)[:1000]
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
            "editorial_brief": "modules/editorial_brief_module.py",
            "source_ingest": "modules/source_ingest_module.py",
            "vault_sync": "modules/vault_sync_module.py",
            "skeleton_from_vault": "modules/skeleton_from_vault_module.py",
            "chapter_projection": "modules/chapter_projection_module.py",
            "duplicate-checker": "scripts/duplicate_check.py",
            "tts-generator": "scripts/generate_tts.py",
            "image_batch": "modules/image_batch_module.py",
            "upload_info_generator": "modules/upload_info_generator.py",
            "subtitle-sync": "scripts/generate_subtitles.py",
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
        env["PYTHONPATH"] = (ws + os.path.pathsep + existing_pypath) if existing_pypath else ws

        try:
            result = subprocess.run(
                cmd,
                cwd=ws,
                env=env,
                capture_output=True,
                text=True, encoding="utf-8",
                timeout=1800,  # 30분 타임아웃
                **subprocess_kwargs(),
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
                error="Timeout (1800s)",
            )
        finally:
            monitor.stop()

    def _resolve_video_output_filename(self) -> str:
        """{slug}_final.mp4, 이미 존재하면 _v2, _v3 ... 자동 증가."""
        base = f"{self.project_slug}_final"
        if not (self.project_dir / f"{base}.mp4").exists():
            return f"{base}.mp4"
        v = 2
        while (self.project_dir / f"{base}_v{v}.mp4").exists():
            v += 1
        return f"{base}_v{v}.mp4"

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
        # {output_video}: slug_final.mp4 (버전 관리 포함)
        command = command.replace("{output_video}", self._resolve_video_output_filename())

        # video-assembler: 프로젝트별 manifest를 --props로 주입
        # remotion/public/manifest.json은 공유 파일이므로 다른 프로젝트가 덮어쓸 수 있음
        # --props로 프로젝트 전용 manifest 경로를 명시적으로 전달해 오렌더링 방지
        if "remotion render" in command and "--props" not in command:
            manifest_props = self._resolve_manifest_props()
            if manifest_props:
                command = command.replace(
                    "--output", f"--props={manifest_props} --output"
                )

        # Node.js PATH 보장 (npx, node 등) — get_env_with_node()로 플랫폼 중립적으로 처리
        node_env = get_env_with_node()
        env["PATH"] = node_env.get("PATH", env.get("PATH", ""))

        try:
            result = subprocess.run(
                command, shell=True,
                cwd=str(get_workspace_dir()),
                env=env,
                capture_output=True,
                text=True, encoding="utf-8",
                timeout=1800,  # 30분 (렌더링)
                **subprocess_kwargs(),
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

        # raw notes — RESEARCH/ 디렉토리의 Explorer .md 파일들 (llm-wiki-research-policy)
        raw_notes: list[tuple] = []
        research_dir = self.project_dir / "RESEARCH"
        if research_dir.exists():
            for md_file in sorted(research_dir.glob("*.md")):
                try:
                    body = md_file.read_text(encoding="utf-8")
                    raw_notes.append((md_file.name, body))
                except Exception as e:
                    print(f"    [VaultRAG] raw 노트 읽기 실패 {md_file.name}: {e}")

        self.vault.save_research_result(
            topic=topic,
            category=category,
            summary=summary,
            key_facts=key_facts,
            sources=sources,
            raw_notes=raw_notes if raw_notes else None,
        )
        print(f"    [VaultRAG] 리서치 결과 볼트 축적 완료: {topic} (raw {len(raw_notes)}개)")

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

    def _run_ratchet_loop(self, step: dict) -> StepResult:
        """래칫 리뷰-수정 루프.

        1. reviewer 평가 → review_feedback.json
        2. 점수 < pass_threshold → reviser 수정 → scene_specs.json
        3. 재평가 (래칫: 이전 점수 이하면 이전 버전 복원)
        4. max_rounds까지 반복
        """
        step_id = step["id"]
        ratchet_cfg = step.get("ratchet", {})
        pass_threshold = ratchet_cfg.get("pass_threshold", 90)
        max_rounds = ratchet_cfg.get("max_rounds", 2)
        score_field = ratchet_cfg.get("score_field", "overall.combined_score")

        reviewer_agent = step.get("reviewer_agent")
        reviser_agent = step.get("reviser_agent")
        feedback_path = self.project_dir / "review_feedback.json"
        specs_path = self.project_dir / "scene_specs.json"

        total_cost = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}
        best_score = 0
        best_specs = specs_path.read_text(encoding="utf-8") if specs_path.exists() else ""
        passed = False

        for round_num in range(1, max_rounds + 1):
            print(f"\n    [래칫 R{round_num}/{max_rounds}] 리뷰 시작...", flush=True)

            # ── 1. 리뷰 실행 (skip_resume로 강제 재실행) ──
            # 라운드별 피드백 파일 (히스토리 보존)
            round_feedback = self.project_dir / f"review_feedback_r{round_num}.json"

            # 이전 리뷰 피드백을 입력에 포함 (재심 규칙용)
            review_inputs = list(step.get("input", []))
            prev_review_context = ""
            if round_num > 1 and feedback_path.exists():
                review_inputs.append("review_feedback.json")
                prev_review_context = feedback_path.read_text(encoding="utf-8")

            review_step = {
                "id": f"{step_id}_review_r{round_num}",
                "name": f"review_r{round_num}",
                "agent": reviewer_agent,
                "input": review_inputs,
                "output": [f"review_feedback.json"],
                "skip_resume": True,
            }
            # 재심 컨텍스트를 프롬프트에 주입
            if prev_review_context:
                review_step["_previous_review"] = prev_review_context

            # Delta review: R2+ 에서는 변경 씬만 전달
            if round_num > 1 and best_specs:
                curr_specs = specs_path.read_text(encoding="utf-8") if specs_path.exists() else ""
                if curr_specs:
                    try:
                        delta = self._compute_scene_delta(best_specs, curr_specs)
                        review_step["_scene_delta"] = json.dumps(delta, ensure_ascii=False)
                        # scene_specs.json을 input에서 제거 (delta로 대체)
                        review_step["input"] = [
                            inp for inp in review_step["input"]
                            if inp != "scene_specs.json"
                        ]
                        print(f"    [래칫 R{round_num}] delta 모드: "
                              f"변경 {len(delta['changed_scenes'])}씬, "
                              f"추가 {len(delta['added_scenes'])}씬, "
                              f"삭제 {len(delta['removed_scene_numbers'])}씬")
                    except Exception as e:
                        print(f"    [래칫 R{round_num}] delta 계산 실패 ({e}) → 전체 전달")
            review_result = self._run_agent_step(review_step)
            self._accumulate_cost(total_cost, review_result.cost_info)

            if review_result.status != "completed":
                print(f"    [래칫] R{round_num} 리뷰 실패: {review_result.error}")
                return StepResult(
                    step_id=step_id,
                    status="failed",
                    error=f"리뷰 실패(R{round_num}): {review_result.error}",
                    cost_info=total_cost,
                )

            # 라운드별 히스토리 저장 (review_feedback.json → review_feedback_rN.json 복사)
            if feedback_path.exists():
                import shutil
                shutil.copy2(feedback_path, round_feedback)

            # ── 2. 점수 확인 ──
            score = 0
            verdict = "UNKNOWN"
            if feedback_path.exists():
                feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
                # score_field 파싱 (예: "overall.combined_score")
                obj = feedback
                for key in score_field.split("."):
                    obj = obj.get(key, {}) if isinstance(obj, dict) else 0
                score = obj if isinstance(obj, (int, float)) else 0
                verdict = feedback.get("overall", {}).get("verdict", "UNKNOWN")

            # 씬별 이슈 요약
            issue_summary = ""
            if feedback_path.exists():
                scene_reviews = feedback.get("scene_reviews", [])
                issue_lines = []
                for sr in scene_reviews:
                    issues = sr.get("issues", [])
                    if issues:
                        sn = sr.get("sceneNumber", "?")
                        for iss in issues:
                            issue_lines.append(f"씬{sn}[{iss.get('severity','')}] {iss.get('description','')[:80]}")
                if issue_lines:
                    issue_summary = "\n".join(issue_lines[:6])  # 최대 6건

            overall_summary = feedback.get("overall", {}).get("summary", "") if feedback_path.exists() else ""
            viewer = feedback.get("overall", {}).get("viewer_score", 0) if feedback_path.exists() else 0
            expert = feedback.get("overall", {}).get("expert_score", 0) if feedback_path.exists() else 0

            print(f"    [래칫 R{round_num}] 점수: {score} (시청자:{viewer}/전문가:{expert}) / 목표: {pass_threshold} → {verdict}", flush=True)
            _notify("script-reviewer",
                    f"래칫 R{round_num}: {score}점 (시청자:{viewer} 전문가:{expert}) → {verdict}\n{overall_summary}",
                    phase=self.state.current_phase, project=self.project_slug,
                    level="success" if score >= pass_threshold else "warning",
                    data={"score": score, "viewer": viewer, "expert": expert, "verdict": verdict})
            if issue_summary:
                _notify("script-reviewer", f"이슈:\n{issue_summary}",
                        phase=self.state.current_phase, project=self.project_slug, level="info")

            # ── 3. PASS 체크 ──
            if score >= pass_threshold:
                print(f"    [래칫] PASS! {score}점 ≥ {pass_threshold}", flush=True)
                _notify("script-reviewer", f"✅ PASS! R{round_num}에서 {score}점 달성 (목표 {pass_threshold})",
                        phase=self.state.current_phase, project=self.project_slug, level="success")
                best_score = score
                best_specs = specs_path.read_text(encoding="utf-8") if specs_path.exists() else best_specs
                passed = True
                break

            # ── 4. 래칫 비교 (퇴보 방지 — 채택 안 함 + 계속 진행) ──
            if score < best_score and round_num > 1:
                print(f"    [래칫] 점수 하락 ({score} < {best_score}) → 수정 채택 안 함, 이전 버전 복원 후 계속", flush=True)
                specs_path.write_text(best_specs, encoding="utf-8")
                _notify("System", f"래칫 R{round_num}: {score}점 → {best_score}점 미달, 이전 버전 복원",
                        phase=self.state.current_phase, project=self.project_slug, level="warning")
                # break 하지 않음 — 새 이슈가 나왔으므로 다시 수정 시도
            elif score > best_score:
                best_score = score
                best_specs = specs_path.read_text(encoding="utf-8") if specs_path.exists() else best_specs

            # ── 5. 마지막 라운드면 수정 불필요 ──
            if round_num >= max_rounds:
                print(f"    [래칫] 최대 라운드 도달 ({max_rounds}회). 현재 최고: {best_score}점", flush=True)
                break

            # ── 6. 수정 실행 ──
            print(f"    [래칫 R{round_num}] 수정 시작...", flush=True)
            revise_step = {
                "id": f"{step_id}_revise_r{round_num}",
                "name": f"revise_r{round_num}",
                "agent": reviser_agent,
                "conditional": "review_verdict_revise",
                "input": ["scene_specs.json", "review_feedback.json", "research_digest.json"],
                "output": ["scene_specs.json"],
                "skills": step.get("skills", []),
                "skip_resume": True,
            }
            revise_result = self._run_agent_step(revise_step)
            self._accumulate_cost(total_cost, revise_result.cost_info)

            if revise_result.status != "completed":
                print(f"    [래칫] R{round_num} 수정 실패: {revise_result.error}")
                return StepResult(
                    step_id=step_id,
                    status="failed",
                    error=f"수정 실패(R{round_num}): {revise_result.error}",
                    cost_info=total_cost,
                )

        if not passed and best_specs and specs_path.exists():
            specs_path.write_text(best_specs, encoding="utf-8")

        return StepResult(
            step_id=step_id,
            status="completed",
            cost_info=total_cost,
        )

    @staticmethod
    def _accumulate_cost(total: dict, cost: dict):
        """비용 정보 누적."""
        total["tokens_in"] += cost.get("tokens_in", 0)
        total["tokens_out"] += cost.get("tokens_out", 0)
        total["cost_usd"] += cost.get("cost_usd", 0.0)

    @staticmethod
    def _compute_scene_delta(prev_specs_json: str, curr_specs_json: str) -> dict:
        """이전/현재 scene_specs 비교 → 변경 씬 추출."""
        prev = json.loads(prev_specs_json)
        curr = json.loads(curr_specs_json)

        if isinstance(prev, dict):
            prev = prev.get("scenes", prev.get("data", []))
        if isinstance(curr, dict):
            curr = curr.get("scenes", curr.get("data", []))

        prev_map = {s["sceneNumber"]: s for s in prev}
        curr_map = {s["sceneNumber"]: s for s in curr}

        changed = []
        added = []
        removed = []

        for sn, scene in curr_map.items():
            if sn not in prev_map:
                added.append(scene)
            elif scene != prev_map[sn]:
                changed.append(scene)

        for sn in prev_map:
            if sn not in curr_map:
                removed.append(sn)

        return {
            "changed_scenes": changed,
            "added_scenes": added,
            "removed_scene_numbers": removed,
            "unchanged_count": len(curr_map) - len(changed) - len(added),
        }

    def _build_progress_block(self, step_id: str) -> str:
        """progress_reporting 블록 생성 (프롬프트 공유 템플릿)."""
        path = self.project_dir / f".progress_{step_id}.jsonl"
        return (
            f"<progress_reporting>\n"
            f'5분마다 → {path} | {{"agent":"..","text":"[진행률%] 완료/다음","level":"info"}}\n'
            f"</progress_reporting>"
        )

    @staticmethod
    def _build_previous_review_context(step: dict) -> str:
        """이전 리뷰 피드백을 재심 컨텍스트로 주입 (리뷰어 일관성 보장)."""
        prev_review = step.get("_previous_review", "")
        if not prev_review:
            return ""

        return (
            "<previous_review>\n"
            "⚠️ 재심 규칙: 아래는 이전 라운드의 리뷰입니다.\n"
            "- 수정되지 않은 씬은 이전 viewer_score, expert_score를 그대로 사용하세요.\n"
            "- 수정된 씬만 새로 채점하세요.\n"
            "- 미수정 씬에도 개선 제안(issues)은 새로 추가할 수 있습니다.\n\n"
            f"{prev_review}\n"
            "</previous_review>\n"
        )

    @staticmethod
    def _build_scene_delta_context(step: dict) -> str:
        """R2+ 리뷰에서 변경 씬 delta를 프롬프트에 주입."""
        delta_json = step.get("_scene_delta", "")
        if not delta_json:
            return ""

        delta = json.loads(delta_json)
        lines = [
            "<scene_delta>",
            "⚠️ 이번 라운드는 delta 모드입니다. 아래 변경/추가된 씬만 재평가하세요.",
            f"미변경 씬 {delta['unchanged_count']}개는 이전 점수를 그대로 유지합니다.",
            "",
        ]
        if delta["changed_scenes"]:
            lines.append("## 변경된 씬:")
            lines.append(json.dumps(delta["changed_scenes"], ensure_ascii=False, indent=2))
        if delta["added_scenes"]:
            lines.append("## 추가된 씬:")
            lines.append(json.dumps(delta["added_scenes"], ensure_ascii=False, indent=2))
        if delta["removed_scene_numbers"]:
            lines.append(f"## 삭제된 씬 번호: {delta['removed_scene_numbers']}")

        lines.append("</scene_delta>")
        return "\n".join(lines)

    def _build_revision_instruction(self, step: dict) -> str:
        """리뷰 피드백 기반 수정 모드 지시문 생성."""
        if step.get("conditional") != "review_verdict_revise":
            return ""
        feedback_path = self.project_dir / "review_feedback.json"
        if not feedback_path.exists():
            return ""
        feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
        overall = feedback.get("overall", {})
        revisions = feedback.get("revision_instructions", [])
        scene_reviews = feedback.get("scene_reviews", [])

        specs_path = self.project_dir / "scene_specs.json"

        lines = [
            "⚠️⚠️⚠️ **수정 모드 — Edit 도구로 scene_specs.json의 변경 부분만 수정하세요** ⚠️⚠️⚠️",
            "",
            f"이전 평가: 시청자 {overall.get('viewer_score', '?')}점 / 전문가 {overall.get('expert_score', '?')}점 / 종합 {overall.get('combined_score', '?')}점",
            f"판정: {overall.get('verdict', '?')} — {overall.get('summary', '')}",
            "",
            "**작업 순서 (반드시 따르세요):**",
            f"1. Read 도구로 `{specs_path}` 읽기",
            f"2. Read 도구로 `{feedback_path}` 읽기 (이슈 상세 확인)",
            "3. 아래 수정 지시에 따라 **Edit 도구**로 변경 부분만 수정 (전체 Write 금지!)",
            "",
            "**⚠️ Edit 도구 사용법 (필수):**",
            "- 전체 파일을 Write로 다시 쓰지 마세요 — 토큰 낭비 + 오류 위험",
            "- Edit 도구의 old_string에 변경할 부분의 원본 텍스트를 넣고, new_string에 수정된 텍스트를 넣으세요",
            "- 예시: motion 변경",
            '  old_string: `"motion": "fade_rise"`',
            '  new_string: `"motion": "cinematic_fade"`',
            "- 예시: 나레이션 재작성",
            '  old_string: `"narration": "기존 나레이션 텍스트"`',
            '  new_string: `"narration": "새로운 나레이션 텍스트"`',
            "- 씬 추가(add_scene): 기존 씬 뒤에 새 씬 JSON 블록을 Edit으로 삽입",
            "- 씬 삭제(remove_scene): 해당 씬 JSON 블록 전체를 Edit으로 빈 문자열로 교체",
            "- 씬 분할(split_scene): 기존 씬 JSON 블록을 2개 씬 블록으로 Edit 교체",
            "",
            "**⚠️ 수정 규칙: major 전부 + minor 가능한 만큼.**",
            "- major 이슈는 **전부** Edit으로 수정하세요",
            "- minor 이슈도 가능한 만큼 수정하세요 (특히 반복 지적된 것 우선)",
            "- 한 라운드에 최대한 많이 처리하세요 — 라운드가 적으니까",
            "",
            "**수정 지시 (major 우선):**",
        ]
        # major 이슈 먼저, minor는 참고용으로 표시
        major_revisions = []
        minor_revisions = []
        for rev in revisions:
            # revision에 severity가 없으면 scene_reviews에서 찾기
            sn = rev.get("sceneNumber", 0)
            sr = next((s for s in scene_reviews if s.get("sceneNumber") == sn), {})
            has_major = any(i.get("severity") == "major" for i in sr.get("issues", []))
            if has_major:
                major_revisions.append(rev)
            else:
                minor_revisions.append(rev)

        for rev in major_revisions:
            sn = rev.get("sceneNumber", "?")
            action = rev.get("action", "modify")
            changes = rev.get("changes", {})
            lines.append(f"")
            lines.append(f"### 🔴 씬 {sn}: {action} (major — 이번 라운드 수정)")
            for key, val in changes.items():
                lines.append(f'  - `"{key}"`: `{json.dumps(val, ensure_ascii=False)}`')

        if minor_revisions:
            lines.append("")
            lines.append("**참고 (minor — 다음 라운드):**")
            for rev in minor_revisions:
                sn = rev.get("sceneNumber", "?")
                action = rev.get("action", "modify")
                lines.append(f"- 씬 {sn}: {action} (다음 라운드에서 처리)")

        lines.append("")
        lines.append("**씬별 이슈 (수정 근거):**")
        for sr in scene_reviews:
            issues = sr.get("issues", [])
            if issues:
                sn = sr.get("sceneNumber", "?")
                for issue in issues:
                    marker = "🔴" if issue.get("severity") == "major" else "🟡"
                    lines.append(f"- {marker} 씬 {sn} [{issue.get('severity', '')}]: {issue.get('description', '')}")
                    if issue.get("suggestion"):
                        lines.append(f"  → 제안: {issue['suggestion']}")

        lines.append("")
        lines.append("**필수 규칙:**")
        lines.append("- **Edit 도구**로 변경 부분만 수정. Write로 전체 파일 재작성 금지")
        lines.append("- 문제 씬만 수정하고, 정상 씬은 절대 건드리지 마세요")
        lines.append("- 수정할 때마다 Edit 도구 호출. 여러 씬이면 여러 번 Edit")
        lines.append(f"- 대상 파일: `{specs_path}`")
        lines.append("- Edit을 한 번도 안 하면 작업이 무효입니다")
        return "\n".join(lines)

    def _load_editorial_brief(self) -> str:
        """프로젝트 디렉토리의 editorial_brief.json 로드 → 문자열 변환."""
        try:
            brief_path = self.project_dir / "editorial_brief.json"
            if brief_path.exists():
                data = json.loads(brief_path.read_text(encoding="utf-8"))
                lines = [
                    f"core_question: {data.get('core_question', '')}",
                    f"real_topic: {data.get('real_topic', '')}",
                    f"hook_angle: {data.get('hook_angle', '')}",
                    f"supporting_case: {data.get('supporting_case', '')}",
                    f"excluded_angles: {', '.join(data.get('excluded_angles', []))}",
                    f"audience_takeaway: {data.get('audience_takeaway', '')}",
                    f"tone_goal: {data.get('tone_goal', '')}",
                    f"success_criteria: {'; '.join(data.get('success_criteria', []))}",
                ]
                return "\n".join(lines)
        except Exception as e:
            print(f"[editorial_brief] 로드 실패: {e}", flush=True)
        return ""

    def _load_creative_brief(self) -> str:
        """볼트 insights/planning/에서 프로젝트 주제와 매칭되는 기획안 로드."""
        try:
            vault_dir = self.vault.vault_dir if self.vault.enabled else Path(os.environ.get("KAIROS_VAULT_DIR", ""))
            if not vault_dir.exists():
                return ""
            planning_dir = vault_dir / "insights" / "planning"
            if not planning_dir.exists():
                return ""

            topic = self.project.get("topic") or self.state.config.get("topic", self.project_slug)
            # 채널 감지
            writing_style = self.state.config.get("writing_style", "")
            channel = "세모지" if writing_style == "semoji" else "이로미즘" if writing_style == "iromism" else ""

            # 최신 기획안에서 주제 검색
            best_match = None
            best_score = 0
            for md in sorted(planning_dir.glob("*.md"), reverse=True):
                content = md.read_text(encoding="utf-8")
                # 주제 키워드 매칭
                topic_keywords = set(re.findall(r'[가-힣]{2,}', topic))
                content_keywords = set(re.findall(r'[가-힣]{2,}', content[:2000]))
                overlap = len(topic_keywords & content_keywords)
                # 채널 매칭 보너스
                if channel and channel in content:
                    overlap += 5
                if overlap > best_score:
                    best_score = overlap
                    best_match = content

            if best_match and best_score >= 3:
                # 크리에이티브 브리프 섹션만 추출
                brief_start = best_match.find("크리에이티브 브리프")
                if brief_start == -1:
                    brief_start = best_match.find("### 📋")
                if brief_start == -1:
                    brief_start = best_match.find("왜 지금인가")

                if brief_start >= 0:
                    # 해당 주제의 브리프 블록 추출 (최대 2000자)
                    return best_match[brief_start:brief_start + 2000]
                return best_match[:2000]

        except Exception as e:
            logger.warning(f"기획안 로드 실패: {e}")
        return ""

    def _build_manuscript_reference_block(self) -> str:
        """script-director manuscript 모드 전용 — 매력적인 prose 작성을 위한 강제 reference 블록.

        2개 source를 강하게 주입:
        1. writing-style-iromism.md / writing-style-semoji.md의 "참조 원고" 섹션 통째
        2. vault semantic search로 유사 주제 과거 영상 원고 (1~2편, top match)

        목적: 추상적 규칙이 아닌 실제 예시로 톤/리듬/후킹 패턴을 학습시킨다.
        """
        writing_style = self.state.config.get("writing_style", "")
        if not writing_style:
            return ""

        sections: list[str] = []

        # ── 1. 참조 원고 (writing-style-iromism.md 의 ⭐ 참조 원고 섹션) ──
        try:
            style_skill_path = (
                Path(__file__).parent.parent
                / "data" / "skills" / "shared"
                / f"writing-style-{writing_style}.md"
            )
            if style_skill_path.exists():
                style_text = style_skill_path.read_text(encoding="utf-8")
                # "## ⭐ 참조 원고" 섹션부터 다음 ## 까지 추출
                ref_start = style_text.find("⭐ 참조 원고")
                if ref_start == -1:
                    ref_start = style_text.find("## 참조 원고")
                if ref_start == -1:
                    ref_start = style_text.find("참조 원고")
                if ref_start >= 0:
                    # 다음 ## 헤더까지 (또는 끝까지)
                    next_h = style_text.find("\n## ", ref_start + 10)
                    ref_section = (
                        style_text[ref_start:next_h] if next_h > 0 else style_text[ref_start:]
                    )
                    # 너무 길면 자름 (max 3000자)
                    if len(ref_section) > 3000:
                        ref_section = ref_section[:3000] + "\n\n[... 이하 생략 ...]"
                    sections.append(
                        f"## 참조 원고 ({writing_style} 스타일 — 톤/리듬/후킹 패턴을 그대로 따르세요)\n\n{ref_section}"
                    )
        except Exception as e:
            logger.warning(f"참조 원고 로드 실패: {e}")

        # ── 2. vault semantic search — 유사 주제의 매력적인 과거 영상 원고 ──
        try:
            if self.vault.enabled:
                topic = self.project.get("topic") or self.project_slug
                # 채널별 폴더 매핑 (있으면 해당 채널 우선)
                channel_folder = None
                if writing_style == "iromism":
                    channel_folder = "channels/이로미즘"
                elif writing_style == "semoji":
                    channel_folder = "channels/세모지"
                # 1차: 채널 폴더 + scripts 우선
                similar = self.vault.semantic_search(
                    query=topic,
                    top_k=5,
                    folder_filter=None,  # 채널 폴더 필터는 너무 좁아 일단 전체에서
                )
                # research_role이 raw/wiki/topics인 것만 (분석 노트 우선)
                # 그리고 채널 폴더 또는 02-research/topics 우선
                preferred = []
                fallback = []
                for r in similar:
                    f = r.get("file", "")
                    if channel_folder and channel_folder in f:
                        preferred.append(r)
                    elif "02-research/topics" in f or "channels/" in f:
                        fallback.append(r)
                top_examples = (preferred + fallback)[:1]  # 최대 1개
                if top_examples:
                    examples_md = "## vault 유사 주제 (참고 — 톤/구조 학습용)\n\n"
                    for r in top_examples:
                        snippet = r.get('snippet', '')[:2000]  # 최대 2000자
                        examples_md += (
                            f"### {r.get('file', '?')}  (score={r.get('score', 0):.3f})\n"
                            f"{snippet}\n\n"
                        )
                    sections.append(examples_md)
                    print(
                        f"    [Manuscript] vault 유사 영상 {len(top_examples)}편 주입",
                        flush=True,
                    )
        except Exception as e:
            logger.warning(f"vault 유사 영상 검색 실패: {e}")

        if not sections:
            return ""

        return (
            "<manuscript_references>\n"
            "⚠️ 매력적인 prose 작성을 위한 강제 reference입니다.\n"
            "이 톤/리듬/후킹 패턴을 그대로 따르세요. 추상적 규칙이 아니라 실제 예시입니다.\n\n"
            + "\n".join(sections)
            + "\n</manuscript_references>"
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
        skill_names = self._filter_writing_style_skills(skill_names)
        skill_refs = agent_def.get("skill_refs", {})
        skill_limits = agent_def.get("skill_limits", {})

        shared_skills_text = ""
        for skill_name in skill_names:
            content = self._load_shared_skill(skill_name, skill_refs.get(skill_name))
            if content:
                limit = skill_limits.get(skill_name)
                if limit and len(content) > limit:
                    content = content[:limit]
                shared_skills_text += f"\n\n## {skill_name}\n\n{content}"

        # 3. 입력 파일 경로
        inputs = step.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        # 선택적 입력도 포함
        optional_inputs = step.get("input_optional", [])
        if isinstance(optional_inputs, str):
            optional_inputs = [optional_inputs]

        # context_replaces 체크
        context_replaces = set(step.get("context_replaces", []))

        input_lines = []
        for inp in inputs:
            if inp in context_replaces:
                if self.context_memory.has_entries_for_predecessors(step.get("id", "")):
                    print(f"    [context_replaces] {inp} → context_memory로 대체")
                    continue
            resolved = self._resolve_output_path(inp)
            tag = "✓" if resolved.exists() else "✗ MISSING"
            input_lines.append(f"- {inp}: {resolved} [{tag}]")
        for inp in optional_inputs:
            if inp in context_replaces:
                if self.context_memory.has_entries_for_predecessors(step.get("id", "")):
                    continue
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
        # research-orchestrator만 볼트 리서치 재활용. script-director에 원고 패턴
        # 주입은 사용자가 비활성화하기로 결정 (의도와 다른 문체 영향).
        vault_block = ""
        if self.vault.enabled and agent_name == "research-orchestrator":
            topic = self.project.get("topic") or self.state.config.get("topic", self.project_slug)
            category = self.vault._detect_category(topic)
            vault_block = self.vault.search_for_research(topic, category)
            if vault_block:
                vault_chars = len(vault_block)
                print(f"    [VaultRAG] 리서치용 볼트 지식 주입: {vault_chars}자", flush=True)
            else:
                print("    [VaultRAG] 리서치용 볼트 지식 없음", flush=True)

        # 6.5. editorial_brief.json 주입 (기획 의도 고정)
        # 우선순위: creative_brief보다 editorial_brief가 상위 컨텍스트
        _skip_brief_agents = {"data-mapper", "fact-verifier", "assembly-director"}
        editorial_brief = self._load_editorial_brief()
        if editorial_brief and agent_name not in _skip_brief_agents:
            vault_block += f"\n\n<editorial_brief>\n{editorial_brief}\n\n⚠️ 이 brief는 모든 리서치·원고·연출 결정의 상위 컨텍스트입니다.\n- real_topic을 중심에 두고, hook_angle은 도입부에만 사용하세요\n- excluded_angles에 해당하는 방향으로 흘러가지 마세요\n- core_question에 대한 답변이 콘텐츠의 핵심이어야 합니다\n</editorial_brief>\n"
            print(f"    [기획의도] editorial_brief 주입: core_question={editorial_brief.split(chr(10))[0]}", flush=True)

        # 6.5b. 볼트 기획안(크리에이티브 브리프) 주입 — editorial_brief 이후 보조 컨텍스트
        creative_brief = self._load_creative_brief()
        if creative_brief and agent_name not in _skip_brief_agents:
            vault_block += f"\n\n<creative_brief>\n{creative_brief}\n</creative_brief>\n"
            print(f"    [기획단] 크리에이티브 브리프 주입: {len(creative_brief)}자", flush=True)

        # 6.7. manuscript mode 전용 — 참조 원고 + vault 유사 영상 강제 주입
        # script-director가 manuscript 작성 시 매력적인 prose를 위한 강한 anchor
        if agent_name == "script-director" and step.get("mode") == "manuscript":
            ref_block = self._build_manuscript_reference_block()
            if ref_block:
                vault_block += "\n\n" + ref_block

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
        _mode_line = ""
        _step_mode = step.get("mode")
        if _step_mode:
            _mode_line = f"\nSCRIPT_DIRECTOR_MODE: {_step_mode}"

        prompt = f"""<system_context>
프로젝트: {self.project_slug}
작업 디렉토리: {self.project_dir}
워크스페이스: {get_workspace_dir()}{_mode_line}
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

{self._build_scene_delta_context(step)}
입력 파일:
{chr(10).join(input_lines) if input_lines else "- 없음"}

출력 파일 (반드시 아래 경로에 저장):
{chr(10).join(output_lines)}

{self._build_previous_review_context(step)}
{self._build_revision_instruction(step)}
모든 출력 파일을 성공적으로 생성하면 작업 완료입니다.
</task>

{self._build_progress_block(step.get('id', ''))}

{context_memory_block}"""
        return prompt

    def _load_agents_config(self) -> dict:
        """agents.json 로드 (캐시). 중앙 규칙 → 로컬 fallback.
        v4(agents 키)와 v3(subagents 키) 모두 지원."""
        if not hasattr(self, "_agents_cache"):
            try:
                self._agents_cache = self.rule_manager.load_json("agents.json")
            except (FileNotFoundError, AttributeError):
                path = DATA_DIR / "agents.json"
                with open(path, "r", encoding="utf-8") as f:
                    self._agents_cache = json.load(f)
            # "agents" 키를 "subagents"로도 노출
            cfg = self._agents_cache
            if "agents" in cfg and "subagents" not in cfg:
                cfg["subagents"] = cfg["agents"]
            # shared_skills → skills 호환
            for agent_def in cfg.get("subagents", {}).values():
                if "shared_skills" in agent_def and "skills" not in agent_def:
                    agent_def["skills"] = agent_def["shared_skills"]
        return self._agents_cache

    def _get_agent_budget(self, agent_name: str) -> float:
        """에이전트 예산 한도(USD) 조회. v4: agents.json에서, v3: pipeline gateway에서."""
        # agents.json 직접
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        budget_str = agent_def.get("budget", "")
        if budget_str:
            try:
                return float(str(budget_str).replace("$", ""))
            except ValueError:
                pass
        # fallback
        limits = self.pipeline.get("gateway", {}).get("agent_limits", {})
        return limits.get(agent_name, {}).get("budget_usd", 3.0)

    def _get_agent_timeout(self, agent_name: str) -> int:
        """에이전트 타임아웃(초) 조회. v4: agents.json에서, v3: pipeline gateway에서."""
        # agents.json 직접
        agents_config = self._load_agents_config()
        agent_def = agents_config.get("subagents", {}).get(agent_name, {})
        max_min = agent_def.get("max_duration_minutes", 0)
        if max_min:
            return max_min * 60
        # fallback
        limits = self.pipeline.get("gateway", {}).get("agent_limits", {})
        max_min = limits.get(agent_name, {}).get("max_duration_min", 15)
        return max_min * 60

    def _count_image_scenes(self) -> int:
        """scene_specs.json에서 이미지 에셋이 필요한 씬 수 반환."""
        try:
            spec_path = self.project_dir / "scene_specs.json"
            if not spec_path.exists():
                return 10  # 기본 추정값
            data = json.loads(spec_path.read_text(encoding="utf-8"))
            scenes = data.get("scenes", [])
            return sum(1 for s in scenes if s.get("imageAsset"))
        except Exception:
            return 10

    def _get_step_max_attempts(self, step: dict) -> int:
        """스텝별 최대 실행 횟수 반환 (1 = 재시도 없음).

        우선순위:
          1. step 정의의 max_attempts 필드
          2. 에이전트/스텝 이름 기반 기본값
          3. 기본값 1 (재시도 없음)
        """
        if "max_attempts" in step:
            return max(1, int(step["max_attempts"]))

        agent = step.get("agent", "")
        step_name = step.get("name", "")

        # 네트워크 의존성 높은 스텝: 최초 1회 + 재시도 2회 = 총 3회
        if agent == "assembly-director" or step_name == "assembly":
            return 3
        if step_name in ("tts", "voice_generation", "tts_generation"):
            return 3

        # 렌더링: 환경 문제 가끔 있어서 1회 재시도
        if step_name in ("video_assembly",):
            return 2

        # 일반 LLM 에이전트 / single_call: 1회 재시도
        if step.get("agent") or step.get("type") == "single_call":
            return 2

        # 모듈(환경 체크, ffmpeg 등): 재시도 없음
        return 1

    def _is_retryable_error(self, error: str) -> bool:
        """일시적 오류(재시도 가능) vs 구조적 오류(재시도 불필요) 판별.

        구조적 오류 키워드: API 키 문제, 파일/CLI 없음, 내용 검증 실패,
        JSON 파싱 오류, 설정 오류 — 재시도해도 동일하게 실패할 것들.
        """
        if not error:
            return False
        NON_RETRYABLE = [
            "api키", "api 키", "api key", "api_key",           # 인증
            "찾을 수 없습니다", "not found", "filenotfound",    # 파일/CLI 없음
            "검증 실패", "주제 불일치", "validation",           # 내용 검증
            "json 파싱", "json parse", "jsondecodeerror",       # 형식
            "unknown step",                                     # 설정 오류
            "permission denied",                               # 권한
        ]
        err_lower = error.lower()
        return not any(kw in err_lower for kw in NON_RETRYABLE)

    @staticmethod
    def _parse_cli_result_wrapper(raw: str) -> Optional[dict]:
        """Claude CLI result wrapper 파싱.

        지원 형식:
        - --output-format json: stdout 전체가 단일 JSON
        - --output-format stream-json: 여러 JSON line 중 마지막 result line
        """
        if not raw:
            return None

        text = raw.strip()
        if not text:
            return None

        try:
            data = json.loads(text)
            if isinstance(data, dict) and data.get("type") == "result":
                return data
        except (json.JSONDecodeError, TypeError):
            pass

        last_result = None
        for line in text.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                data = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(data, dict) and data.get("type") == "result":
                last_result = data
        return last_result

    @classmethod
    def _extract_cli_error_message(cls, stdout: str, stderr: str) -> str:
        """Claude CLI wrapper의 result 필드에서 읽을 수 있는 에러 메시지 추출."""
        for raw in (stdout, stderr):
            wrapper = cls._parse_cli_result_wrapper(raw)
            if not wrapper:
                continue
            result = wrapper.get("result", "")
            if isinstance(result, str) and result.strip():
                return result.strip()

        return (stderr or stdout[-1000:] or stdout[:1000]).strip()

    @staticmethod
    def _extract_rate_limit_wait_seconds(error: str) -> Optional[int]:
        """'resets 8pm (Asia/Seoul)' 메시지에서 재시도 대기 시간 추출."""
        if not error:
            return None

        m = re.search(
            r"resets?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)\s*\(([^)]+)\)",
            error,
            re.IGNORECASE,
        )
        if not m:
            return None

        hour = int(m.group(1))
        minute = int(m.group(2) or "0")
        ampm = m.group(3).lower()
        tz_name = m.group(4).strip()

        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0

        try:
            now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            return None

        reset = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        delta = int((reset - now).total_seconds())
        if delta < 0:
            return 5
        if delta <= 3600:
            return delta + 5
        return None

    def _compute_retry_wait(self, error: str, attempt: int, is_timeout: bool) -> int:
        """에러 유형에 따른 재시도 대기 시간 계산."""
        if is_timeout:
            return 0

        err_lower = (error or "").lower()
        if "you've hit your limit" in err_lower or "rate limit" in err_lower:
            parsed = self._extract_rate_limit_wait_seconds(error or "")
            return parsed if parsed is not None else 60

        return 15 * (3 ** attempt)

    def _resolve_composition(self) -> str:
        """프로젝트 theme에 따른 Remotion Composition ID 반환."""
        theme = self.project.get("theme", "simple")
        return {"simple": "SimpleVideo", "kairos": "KairosVideo"}.get(
            theme, "SimpleVideo"
        )

    def _resolve_manifest_props(self) -> Optional[str]:
        """프로젝트 전용 manifest 파일 경로 반환 (remotion/ 기준 상대경로).

        build_manifest.py가 remotion/public/manifests/{fname}.json에 저장하므로
        여기서 찾아 --props 인자로 전달한다.
        없으면 None 반환 → 공유 manifest.json 사용 (기존 동작)
        """
        ws = get_workspace_dir()
        manifests_dir = ws / "remotion" / "public" / "manifests"

        # 1) DB에서 정확한 파일명 조회
        try:
            from auto_agent.db.project_manager import ProjectManager
            pm = ProjectManager()
            manifest_fname = pm.get_manifest_filename(
                project_id=self.project.get("id"),
                slug=self.project_slug,
            )
            if manifest_fname:
                candidate = manifests_dir / manifest_fname
                if candidate.exists():
                    return f"public/manifests/{manifest_fname}"
        except Exception:
            pass

        # 2) slug로 glob 탐색 (UUID_slug 패턴)
        for f in sorted(manifests_dir.glob(f"*{self.project_slug}*.json"),
                        key=lambda p: p.stat().st_mtime, reverse=True):
            return f"public/manifests/{f.name}"

        return None

    def _parse_claude_cost(self, stdout: str, stderr: str) -> dict:
        """Claude CLI 출력에서 비용 정보 파싱."""
        cost_info = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

        for raw in (stdout, stderr):
            wrapper = self._parse_cli_result_wrapper(raw)
            if not wrapper:
                continue
            usage = wrapper.get("usage", {}) or {}
            cost_info["tokens_in"] = usage.get("input_tokens", 0)
            cost_info["tokens_out"] = usage.get("output_tokens", 0)
            cost_info["cost_usd"] = (
                wrapper.get("cost_usd", 0.0) or wrapper.get("total_cost_usd", 0.0)
            )
            model = wrapper.get("model", "")
            if cost_info["cost_usd"] == 0 and cost_info["tokens_in"] > 0:
                cost_info["cost_usd"] = self._estimate_cost(
                    cost_info["tokens_in"], cost_info["tokens_out"], model
                )
            return cost_info

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
        resolved = resolved.replace("{output_video}", self._resolve_video_output_filename())
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
        cond = step.get("conditional", "")

        # 래칫 리뷰 판정 조건: review_feedback.json의 verdict가 REVISE인 경우만 실행
        if cond == "review_verdict_revise":
            feedback_path = self.project_dir / "review_feedback.json"
            if not feedback_path.exists():
                print(f"    [조건] review_feedback.json 없음 → 스킵")
                return False
            feedback = json.loads(feedback_path.read_text(encoding="utf-8"))
            verdict = feedback.get("overall", {}).get("verdict", "")
            if verdict == "REVISE":
                print(f"    [조건] 리뷰 판정 REVISE → 수정 실행")
                return True
            else:
                print(f"    [조건] 리뷰 판정 {verdict} → 스킵 (수정 불필요)")
                return False

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

    def _check_brief_alignment(self):
        """Stage 1 완료 후 outline.json과 editorial_brief.json의 정렬 검증.

        비차단 — 경고만 출력. 심각한 드리프트 시 사용자가 수동 개입 가능.
        """
        brief_path = self.project_dir / "editorial_brief.json"
        outline_path = self.project_dir / "outline.json"

        if not brief_path.exists():
            return  # editorial_brief 없으면 스킵
        if not outline_path.exists():
            return  # outline 없으면 스킵

        try:
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            outline = json.loads(outline_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"    [alignment] 파일 읽기 실패: {e}", flush=True)
            return

        real_topic = brief.get("real_topic", "")
        excluded = brief.get("excluded_angles", [])
        core_q = brief.get("core_question", "")
        chapters = outline.get("chapters", [])

        if not chapters:
            return

        print(f"\n  ★ BRIEF ALIGNMENT CHECK (Stage 1 완료)", flush=True)
        print(f"    core_question: {core_q}", flush=True)
        print(f"    real_topic: {real_topic}", flush=True)

        # 챕터 제목 목록
        chapter_titles = [ch.get("title", "") for ch in chapters]
        print(f"    chapters: {chapter_titles}", flush=True)

        # 간단 키워드 검사 — excluded_angles 키워드가 챕터에 많이 나타나는지
        warnings = []
        real_topic_kw = set(w for w in real_topic.split() if len(w) > 1)
        outline_text = " ".join(chapter_titles + [ch.get("narrative_role", "") for ch in chapters])

        for exc in excluded:
            exc_kw = set(w for w in exc.split() if len(w) > 1)
            if exc_kw and any(kw in outline_text for kw in exc_kw):
                warnings.append(f"⚠️ excluded_angle 감지: '{exc}' → 챕터 제목에 관련 키워드 존재")

        # real_topic 키워드가 outline에 전혀 없으면 경고
        if real_topic_kw and not any(kw in outline_text for kw in real_topic_kw):
            warnings.append(f"⚠️ real_topic '{real_topic}' 키워드가 outline 챕터에서 발견되지 않음 — 드리프트 위험")

        if warnings:
            print(f"\n    [ALIGNMENT WARN] brief와 outline 정렬 이슈:", flush=True)
            for w in warnings:
                print(f"      {w}", flush=True)
            print(f"\n    → Stage 2 진행 전 outline.json 검토 권장", flush=True)
            _notify("System", f"⚠️ Brief alignment 이슈 {len(warnings)}건 — outline 검토 필요",
                    phase="stage_1", project=self.project_slug, level="warning")
        else:
            print(f"    ✅ alignment OK — outline이 editorial_brief 방향과 일치", flush=True)

        print()

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
        _notify("Director", f"촬영 끝! {completed}/{total} 성공{cost_str}", phase="pipeline", project=self.project_slug, level=level)

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

        # 파이프라인 완료 이벤트 emit
        self._emit_pipeline_event("pipeline_finished", {
            "completed": completed,
            "failed": failed,
            "total": total,
        })

        # 프로젝트 상태 업데이트
        if failed == 0:
            self.pm.update_project(self.project["id"], status="completed")
        else:
            self.pm.update_project(self.project["id"], status="failed")

    # ─────────────────────────────────────────────────────────────
    # 실시간 이벤트 emit (dashboard SSE가 tailing)
    # ─────────────────────────────────────────────────────────────

    def _emit_pipeline_event(self, event_type: str, payload: dict) -> None:
        """pipeline_events.jsonl에 이벤트를 append하고 pipeline_live.json을 갱신."""
        try:
            events_path = self.project_dir / "pipeline_events.jsonl"
            live_path = self.project_dir / "pipeline_live.json"

            entry = {
                "ts": datetime.now().isoformat(),
                "event": event_type,
                "step": self.state.current_step,
                "phase": self.state.current_phase,
                "completed": self.state.completed_steps,
                "failed": self.state.failed_steps,
                **payload,
            }

            # JSONL append (atomic enough for single writer)
            with open(events_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            # live state snapshot (overwrite — dashboard polls this)
            live_state = {
                "ts": entry["ts"],
                "current_step": self.state.current_step,
                "current_phase": self.state.current_phase,
                "completed_steps": self.state.completed_steps,
                "failed_steps": self.state.failed_steps,
                "skipped_steps": self.state.skipped_steps,
                "started_at": self.state.started_at,
            }
            live_path.write_text(
                json.dumps(live_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass  # 이벤트 emit 실패는 파이프라인 중단하지 않음


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
