# Director Agent Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python runner의 for loop 파이프라인을 Director LLM Agent가 도구를 호출하며 직접 이끌어가는 구조로 전환한다.

**Architecture:** 기존 runner.py의 실행 함수들을 Director용 도구로 래핑하고, Director LLM이 프리셋+볼트+pipeline.json을 컨텍스트로 받아 파이프라인 흐름을 판단한다. `--legacy` 플래그로 기존 방식 롤백 가능.

**Tech Stack:** Claude CLI (Director 세션), 기존 runner.py 인프라, 확장된 아트스타일 프리셋 JSON

**Spec:** `docs/superpowers/specs/2026-03-24-director-agent-phase2-design.md`

---

## Chunk 1: 아트스타일 프리셋 확장

### Task 1: 프리셋 스키마 정의 + 마이그레이션 유틸

**Files:**
- Create: `auto_agent/data/artstyle/preset_schema.py`
- Modify: `auto_agent/data/artstyle/styles/quirky_cartoon.json`
- Modify: `auto_agent/data/artstyle/styles/semoji.json`
- Modify: `auto_agent/data/artstyle/styles/lego.json`
- Modify: `auto_agent/data/artstyle/styles/stickman_cute.json`

- [ ] **Step 1: 프리셋 스키마 검증 모듈 작성**

`preset_schema.py` — 프리셋 JSON의 필수 필드 검증 + 기존 JSON과 하위 호환.

```python
"""아트스타일 프리셋 스키마 검증."""
from pathlib import Path
from typing import Optional
import json

REQUIRED_SECTIONS = ["image", "voice", "creative", "scenes", "guidelines"]
REQUIRED_IMAGE = ["staging", "reference_image", "scene_style_description"]
REQUIRED_VOICE = ["voice_id"]
VALID_STAGING = ["cinematic", "flat"]


def validate_preset(preset: dict) -> list[str]:
    """프리셋 검증. 누락/오류 목록 반환. 빈 리스트면 통과."""
    errors = []
    for section in REQUIRED_SECTIONS:
        if section not in preset:
            errors.append(f"섹션 누락: {section}")

    image = preset.get("image", {})
    for field in REQUIRED_IMAGE:
        if not image.get(field):
            errors.append(f"image.{field} 누락")
    if image.get("staging") and image["staging"] not in VALID_STAGING:
        errors.append(f"image.staging 유효하지 않음: {image['staging']} (허용: {VALID_STAGING})")

    voice = preset.get("voice", {})
    for field in REQUIRED_VOICE:
        if not voice.get(field):
            errors.append(f"voice.{field} 누락")

    if not preset.get("guidelines"):
        errors.append("guidelines 비어있음")

    return errors


def load_preset(path: str | Path) -> dict:
    """프리셋 JSON 로드. 기존 형식이면 자동 래핑."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # 기존 형식 감지: image 섹션 없으면 레거시
    if "image" not in data and "style" in data:
        data = _migrate_legacy(data)
    return data


def _migrate_legacy(legacy: dict) -> dict:
    """기존 아트스타일 JSON → 확장 프리셋 형식으로 래핑."""
    return {
        "id": legacy.get("id", legacy.get("name", "unknown")),
        "name": legacy.get("name", ""),
        "description": legacy.get("description", ""),
        "channel": None,
        "image": {
            "staging": "cinematic",
            "reference_image": legacy.get("reference_image", ""),
            "scene_style_description": legacy.get("scene_style_description", ""),
            "style": legacy.get("style", {}),
            "critical_requirements": legacy.get("technical", {}).get("critical_requirements", []),
            "prompt_language": "ko",
        },
        "voice": {"voice_id": "", "voice_settings": {}},
        "creative": {},
        "scenes": {},
        "guidelines": "",
        # 원본 필드 보존 (하위 호환)
        **{k: v for k, v in legacy.items() if k not in ("style", "technical")},
    }
```

- [ ] **Step 2: quirky_cartoon.json 확장**

기존 필드 유지하면서 `image`, `voice`, `creative`, `scenes`, `guidelines` 추가.

```json
{
  "id": "quirky_cartoon",
  "name": "Quirky Cartoon",
  "description": "90년대 미국 카툰, 두껍고 삐뚤빼뚤한 선, 밝은 플랫 컬러",
  "channel": "이로미즘",

  "image": {
    "staging": "cinematic",
    "reference_image": "artstyle/styles/quirky_cartoon_base.jpg",
    "scene_style_description": "Loose quirky hand-drawn cartoon, doodle style, thick wobbly lines, bright flat colors, human characters only.",
    "style": { "(기존 style 객체 그대로)" },
    "critical_requirements": [],
    "prompt_language": "ko"
  },

  "voice": {
    "voice_id": "9Sj8ugvpK1DmcAXyvi3a",
    "voice_settings": { "stability": 1.0, "similarity_boost": 0.6, "style": 0.9, "speed": 1.1 }
  },

  "creative": {
    "headline_frequency": "20-30%",
    "mood_palette": ["dramatic", "suspense", "contemplative", "informative"],
    "preferred_layouts": ["cinematic", "before_after", "rank_list", "timeline", "flow", "metric_spotlight"]
  },

  "scenes": {
    "density": "moderate",
    "min_duration_sec": 4,
    "max_duration_sec": 15,
    "prefer_split_on": ["전환어", "감정 전환", "시각적 전환"]
  },

  "guidelines": "이로미즘은 시네마틱 내러티브 중심. 극적 전개와 여백을 중시한다. 텍스트보다 이미지가 강한 임팩트를 줄 때 cinematic 사용. 통계/비교는 before_after나 rank_list로."
}
```

- [ ] **Step 3: semoji.json 확장**

```json
추가 필드:
  "channel": "세모지",
  "image.staging": "flat",
  "voice": { "voice_id": "W7FnAxJNpD5WGjrF5GLp", "voice_settings": {...} },
  "creative": {
    "headline_frequency": "10-20%",
    "mood_palette": ["informative", "contemplative", "triumphant"],
    "preferred_layouts": ["items_grid", "items_list", "counter", "bar", "pie", "flow"]
  },
  "scenes": { "density": "high", "min_duration_sec": 3, "max_duration_sec": 12 },
  "guidelines": "세모지는 정보 전달 중심. 친근한 설명체, 데이터 시각화 적극 활용. flat staging으로 캐릭터 정면 배치."
```

- [ ] **Step 4: lego.json, stickman_cute.json 확장**

각각 기본값으로 확장. voice는 default voice_id 사용.

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/data/artstyle/
git commit -m "feat: 아트스타일 프리셋 확장 — voice/creative/scenes/guidelines 추가"
```

---

## Chunk 2: Director 도구 구현

### Task 2: Director 전용 도구 모듈

**Files:**
- Create: `auto_agent/orchestrator/director_tools.py`
- Modify: `auto_agent/orchestrator/tools.py` (TOOL_SCHEMAS 확장)

- [ ] **Step 1: director_tools.py 작성**

기존 runner.py의 함수를 래핑하는 도구 실행기.

```python
"""Director Agent 전용 도구.

기존 PipelineRunner의 함수들을 Director LLM이 호출할 수 있는 도구로 래핑.
"""
import json
from pathlib import Path
from typing import Optional


class DirectorToolExecutor:
    """Director Agent가 사용하는 도구 실행기."""

    def __init__(self, runner):
        self.runner = runner
        self.state = runner.state
        self.project_dir = runner.project_dir

    def execute(self, tool_name: str, tool_input: dict) -> str:
        handler = getattr(self, f"_exec_{tool_name}", None)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
        try:
            return handler(tool_input)
        except Exception as e:
            return json.dumps({"error": str(e)})

    def _exec_get_pipeline_state(self, inp: dict) -> str:
        return json.dumps({
            "completed": self.state.completed_steps,
            "failed": self.state.failed_steps,
            "skipped": self.state.skipped_steps,
            "current_step": self.state.current_step,
            "current_phase": self.state.current_phase,
        }, ensure_ascii=False)

    def _exec_get_step_info(self, inp: dict) -> str:
        step_id = inp["step_id"]
        for phase in self.runner.pipeline.get("phases", []):
            for step in phase.get("steps", []):
                if step["id"] == step_id:
                    return json.dumps(step, ensure_ascii=False)
        return json.dumps({"error": f"Step not found: {step_id}"})

    def _exec_run_step(self, inp: dict) -> str:
        step_id = inp["step_id"]
        step = self._find_step(step_id)
        if not step:
            return json.dumps({"error": f"Step not found: {step_id}"})
        result = self.runner._execute_step(step)
        result = self.runner._validate_step(step_id, result)
        self.state.results[step_id] = result.__dict__
        if result.status == "completed":
            self.state.completed_steps.append(step_id)
        elif result.status == "skipped":
            self.state.skipped_steps.append(step_id)
        else:
            self.state.failed_steps.append(step_id)
        self.runner._save_state()
        return json.dumps({
            "step_id": step_id,
            "status": result.status,
            "error": result.error,
            "duration": result.duration_sec,
        }, ensure_ascii=False)

    def _exec_run_steps_parallel(self, inp: dict) -> str:
        step_ids = inp["step_ids"]
        steps = [self._find_step(sid) for sid in step_ids]
        missing = [sid for sid, s in zip(step_ids, steps) if s is None]
        if missing:
            return json.dumps({"error": f"Steps not found: {missing}"})
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=min(len(steps), 10)) as pool:
            futures = {pool.submit(self.runner._execute_step, s): s for s in steps}
            for fut in as_completed(futures):
                step = futures[fut]
                result = fut.result()
                result = self.runner._validate_step(step["id"], result)
                self.state.results[step["id"]] = result.__dict__
                if result.status == "completed":
                    self.state.completed_steps.append(step["id"])
                elif result.status == "skipped":
                    self.state.skipped_steps.append(step["id"])
                else:
                    self.state.failed_steps.append(step["id"])
                results[step["id"]] = {"status": result.status, "error": result.error}
        self.runner._save_state()
        return json.dumps(results, ensure_ascii=False)

    def _exec_retry_step(self, inp: dict) -> str:
        step_id = inp["step_id"]
        feedback = inp.get("feedback", "")
        step = self._find_step(step_id)
        if not step:
            return json.dumps({"error": f"Step not found: {step_id}"})
        # feedback을 step에 임시 주입
        step["_director_feedback"] = feedback
        # failed에서 제거
        if step_id in self.state.failed_steps:
            self.state.failed_steps.remove(step_id)
        if step_id in self.state.completed_steps:
            self.state.completed_steps.remove(step_id)
        result = self.runner._execute_step(step)
        result = self.runner._validate_step(step_id, result)
        self.state.results[step_id] = result.__dict__
        if result.status == "completed":
            self.state.completed_steps.append(step_id)
        else:
            self.state.failed_steps.append(step_id)
        step.pop("_director_feedback", None)
        self.runner._save_state()
        return json.dumps({
            "step_id": step_id, "status": result.status,
            "error": result.error, "feedback_applied": feedback,
        }, ensure_ascii=False)

    def _exec_skip_step(self, inp: dict) -> str:
        step_id = inp["step_id"]
        reason = inp.get("reason", "")
        self.state.skipped_steps.append(step_id)
        self.state.results[step_id] = {
            "step_id": step_id, "status": "skipped", "error": reason,
        }
        self.runner._save_state()
        from auto_agent.orchestrator.runner import _notify
        _notify("Director", f"[SKIP] {step_id}: {reason}",
                phase=self.state.current_phase, project=self.runner.project_slug)
        return json.dumps({"step_id": step_id, "status": "skipped", "reason": reason})

    def _exec_review_output(self, inp: dict) -> str:
        file_path = inp["file_path"]
        full_path = self.project_dir / file_path
        if not full_path.exists():
            return json.dumps({"error": f"File not found: {file_path}"})
        text = full_path.read_text(encoding="utf-8")
        # 큰 파일은 요약
        if len(text) > 5000:
            text = text[:2000] + f"\n\n... ({len(text)}자 중 2000자만 표시) ...\n\n" + text[-1000:]
        return text

    def _exec_log_preference(self, inp: dict) -> str:
        note = inp["note"]
        preset_id = inp.get("preset_id", "general")
        pref_dir = Path(self.runner.workspace_dir) / ".vault" / "preferences"
        pref_dir.mkdir(parents=True, exist_ok=True)
        pref_file = pref_dir / f"{preset_id}.md"
        if pref_file.exists():
            content = pref_file.read_text(encoding="utf-8")
        else:
            content = f"# {preset_id} 선호도\n\n"
        from datetime import datetime
        date = datetime.now().strftime("%Y-%m-%d")
        project = self.runner.project_slug
        content += f"- {note} ({date}, {project})\n"
        pref_file.write_text(content, encoding="utf-8")
        return json.dumps({"status": "saved", "file": str(pref_file)})

    def _exec_send_message(self, inp: dict) -> str:
        text = inp["text"]
        level = inp.get("level", "info")
        from auto_agent.orchestrator.runner import _notify
        _notify("Director", text,
                phase=self.state.current_phase,
                project=self.runner.project_slug, level=level)
        return json.dumps({"status": "sent"})

    def _find_step(self, step_id: str) -> Optional[dict]:
        for phase in self.runner.pipeline.get("phases", []):
            for step in phase.get("steps", []):
                if step["id"] == step_id:
                    return step
        return None
```

- [ ] **Step 2: TOOL_SCHEMAS에 Director 도구 스키마 추가**

`tools.py`에 DIRECTOR_TOOL_SCHEMAS 리스트 추가.

```python
DIRECTOR_TOOL_SCHEMAS = [
    {
        "name": "get_pipeline_state",
        "description": "현재 파이프라인 진행 상황 — 완료/실패/스킵된 스텝 목록 반환",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_step_info",
        "description": "특정 스텝의 정의 — 입력/출력/에이전트/스킬/의존성 정보",
        "input_schema": {
            "type": "object",
            "properties": {"step_id": {"type": "string", "description": "스텝 ID (예: step_1)"}},
            "required": ["step_id"]
        }
    },
    {
        "name": "run_step",
        "description": "스텝 실행. 서브 에이전트/모듈을 호출하고 결과를 반환",
        "input_schema": {
            "type": "object",
            "properties": {"step_id": {"type": "string"}},
            "required": ["step_id"]
        }
    },
    {
        "name": "run_steps_parallel",
        "description": "의존성 없는 스텝 여러 개를 동시 실행",
        "input_schema": {
            "type": "object",
            "properties": {"step_ids": {"type": "array", "items": {"type": "string"}}},
            "required": ["step_ids"]
        }
    },
    {
        "name": "retry_step",
        "description": "실패한 스텝을 피드백과 함께 재실행",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_id": {"type": "string"},
                "feedback": {"type": "string", "description": "Director의 수정 지시"}
            },
            "required": ["step_id"]
        }
    },
    {
        "name": "skip_step",
        "description": "스텝 스킵 + 사유 기록",
        "input_schema": {
            "type": "object",
            "properties": {
                "step_id": {"type": "string"},
                "reason": {"type": "string"}
            },
            "required": ["step_id", "reason"]
        }
    },
    {
        "name": "review_output",
        "description": "결과물 파일을 읽어서 내용 반환 (프로젝트 디렉토리 기준 상대경로)",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"]
        }
    },
    {
        "name": "log_preference",
        "description": "사용자 선호도/피드백을 볼트에 기록",
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {"type": "string", "description": "선호도 내용"},
                "preset_id": {"type": "string", "description": "아트스타일 ID (기본: general)"}
            },
            "required": ["note"]
        }
    },
    {
        "name": "send_message",
        "description": "메신저에 진행 상황 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "level": {"type": "string", "enum": ["info", "success", "warning", "error"]}
            },
            "required": ["text"]
        }
    },
]
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/orchestrator/director_tools.py auto_agent/orchestrator/tools.py
git commit -m "feat: Director Agent 도구 모듈 — 9개 도구 정의 + 실행기"
```

---

## Chunk 3: Director 하네스 (시스템 프롬프트 + 실행 루프)

### Task 3: Director 시스템 프롬프트

**Files:**
- Create: `auto_agent/data/prompts/director-system.md`

- [ ] **Step 1: Director 시스템 프롬프트 작성**

```markdown
# Director Agent — 사감독

당신은 영상 제작 파이프라인의 사감독(Director)입니다.
프리셋과 볼트 선호도를 참고하여 파이프라인을 직접 이끌어갑니다.

## 역할
- 각 스텝의 실행 순서를 판단합니다
- 결과물의 품질을 검토하고 재시도/스킵을 결정합니다
- 의존성 없는 스텝은 run_steps_parallel로 동시 실행합니다
- 사용자 피드백을 볼트에 기록합니다

## 판단 기준
1. pipeline.json의 스텝 정의와 depends_on 관계를 참고합니다
2. 프리셋의 guidelines를 기본 방향으로 따릅니다
3. 볼트 선호도가 있으면 프리셋보다 우선 참고합니다
4. 특정 씬에서 프리셋 기본값을 오버라이드할 수 있습니다

## 실행 규칙
- 매 스텝 완료 후 review_output으로 결과를 확인합니다
- 결과가 불만족이면 retry_step으로 피드백과 함께 재시도합니다
- 재시도는 최대 2회. 3회 실패하면 send_message로 알리고 다음으로 넘어갑니다
- 의존성이 같은 스텝은 run_steps_parallel로 동시 실행합니다
- 진행 상황을 send_message로 주기적으로 알립니다

## 금지 사항
- 도구 목록 외의 행동 금지
- 프리셋의 image.reference_image를 변경하지 마세요
- 프리셋의 voice.voice_id를 변경하지 마세요
- 이미지 파일 삭제 금지 (버전 관리로 처리)

## 진행 보고
- 스텝 시작 시: send_message("[step_id] 시작")
- 스텝 완료 시: send_message("[step_id] 완료 — 요약")
- 품질 이슈 시: send_message("[step_id] 재시도 — 사유")
- 스킵 시: send_message("[step_id] 스킵 — 사유")
```

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/data/prompts/director-system.md
git commit -m "feat: Director Agent 시스템 프롬프트"
```

### Task 4: Director 실행 루프

**Files:**
- Create: `auto_agent/orchestrator/director.py`
- Modify: `auto_agent/orchestrator/runner.py` (run_director 메서드 추가)

- [ ] **Step 1: director.py 작성**

Director Agent를 Claude CLI로 실행하는 루프.

```python
"""Director Agent 실행기.

PipelineRunner를 래핑하여 Director LLM이 도구를 호출하며
파이프라인을 이끌어가는 구조.
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from auto_agent.orchestrator.director_tools import DirectorToolExecutor
from auto_agent.orchestrator.tools import DIRECTOR_TOOL_SCHEMAS
from auto_agent.data.artstyle.preset_schema import load_preset, validate_preset


def build_director_context(runner) -> str:
    """Director에게 주입할 컨텍스트 조립."""
    config = runner.state.config
    preset_path = config.get("art_style", "")

    # 1. 프리셋 로드
    preset_text = ""
    if preset_path:
        from auto_agent.paths import get_workspace_dir, get_data_dir
        for base in [get_workspace_dir(), get_data_dir()]:
            full = base / preset_path
            if full.exists():
                preset = load_preset(full)
                preset_text = json.dumps(preset, indent=2, ensure_ascii=False)
                break

    # 2. 볼트 선호도 로드
    vault_prefs = ""
    preset_id = Path(preset_path).stem if preset_path else "general"
    pref_file = get_workspace_dir() / ".vault" / "preferences" / f"{preset_id}.md"
    if pref_file.exists():
        vault_prefs = pref_file.read_text(encoding="utf-8")

    # 3. pipeline.json 요약
    pipeline_summary = []
    for phase in runner.pipeline.get("phases", []):
        for step in phase.get("steps", []):
            deps = step.get("depends_on", "")
            skip = " (skip)" if step.get("skip") else ""
            pipeline_summary.append(
                f"  {step['id']}: {step.get('name', '')} — {step.get('type', '')} "
                f"[agent: {step.get('agent', step.get('module', ''))}]"
                f"{f' depends_on: {deps}' if deps else ''}{skip}"
            )

    # 4. 프로젝트 정보
    topic = runner.project.get("topic") or config.get("topic", runner.project_slug)

    return f"""<project>
프로젝트: {runner.project_slug}
주제: {topic}
분량: {config.get('duration_minutes', '?')}분
문체: {config.get('writing_style', 'N/A')}
작업 디렉토리: {runner.project_dir}
</project>

<preset>
{preset_text}
</preset>

<vault_preferences>
{vault_prefs if vault_prefs else "(축적된 선호도 없음)"}
</vault_preferences>

<pipeline_steps>
{chr(10).join(pipeline_summary)}
</pipeline_steps>

<current_state>
완료: {runner.state.completed_steps}
실패: {runner.state.failed_steps}
스킵: {runner.state.skipped_steps}
</current_state>
"""


def run_director(runner, from_step: Optional[str] = None) -> None:
    """Director Agent를 Claude CLI로 실행."""
    from auto_agent.orchestrator.runner import _notify

    # 1. 프리셋 preflight 검증
    config = runner.state.config
    preset_path = config.get("art_style", "")
    if preset_path:
        from auto_agent.paths import get_workspace_dir, get_data_dir
        for base in [get_workspace_dir(), get_data_dir()]:
            full = base / preset_path
            if full.exists():
                preset = load_preset(full)
                errors = validate_preset(preset)
                if errors:
                    print(f"\n  [ERROR] 프리셋 검증 실패:")
                    for e in errors:
                        print(f"    - {e}")
                    raise SystemExit(1)
                # 도구-프리셋 교차 검증
                staging = preset.get("image", {}).get("staging", "")
                if staging and staging not in ("cinematic", "flat"):
                    print(f"\n  [ERROR] 지원하지 않는 staging: {staging}")
                    raise SystemExit(1)
                break

    # 2. 컨텍스트 빌드
    context = build_director_context(runner)

    # 3. 시스템 프롬프트 로드
    system_prompt_path = Path(__file__).parent.parent / "data" / "prompts" / "director-system.md"
    system_prompt = system_prompt_path.read_text(encoding="utf-8")

    # 4. 도구 실행기
    tool_executor = DirectorToolExecutor(runner)

    # 5. 초기 메시지
    cfg = runner.state.config
    config_summary = (
        f"파이프라인 시작 | "
        f"문체: {cfg.get('writing_style', 'N/A')} | "
        f"아트: {Path(cfg.get('art_style', '')).stem if cfg.get('art_style') else 'N/A'} | "
        f"분량: {cfg.get('duration_minutes', '?')}분"
    )
    _notify("Director", config_summary,
            phase="pipeline", project=runner.project_slug, level="info")

    # 6. from_step 처리
    start_instruction = ""
    if from_step:
        start_instruction = f"\n\n{from_step}부터 시작하세요. 이전 스텝은 이미 완료되어 있습니다."

    # 7. 프롬프트 파일 저장
    prompt = f"{system_prompt}\n\n{context}{start_instruction}"
    prompt_file = runner.project_dir / ".director_prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    # 8. Claude CLI 실행 (도구 루프)
    # Director는 Anthropic API 직접 호출로 도구 루프 실행
    # (Claude CLI --print 모드는 도구 호출을 지원하지 않으므로 API 사용)
    _run_tool_loop(runner, tool_executor, prompt, DIRECTOR_TOOL_SCHEMAS)


def _run_tool_loop(runner, executor, initial_prompt, tool_schemas):
    """Anthropic API로 Director 도구 루프 실행."""
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": initial_prompt}]

    model = os.environ.get("DIRECTOR_MODEL", "claude-sonnet-4-5-20250929")
    max_iterations = 100  # 안전 상한

    for i in range(max_iterations):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            tools=tool_schemas,
            messages=messages,
        )

        # 응답 처리
        assistant_content = response.content
        messages.append({"role": "assistant", "content": assistant_content})

        # 도구 호출 수집
        tool_calls = [b for b in assistant_content if b.type == "tool_use"]

        if not tool_calls:
            # 도구 호출 없음 = Director가 완료 판단
            # 텍스트 응답 출력
            for block in assistant_content:
                if hasattr(block, "text"):
                    print(f"  [Director] {block.text[:200]}")
            break

        # 도구 실행 + 결과 반환
        tool_results = []
        for tc in tool_calls:
            print(f"  [Director] -> {tc.name}({json.dumps(tc.input, ensure_ascii=False)[:100]})")
            result = executor.execute(tc.name, tc.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc.id,
                "content": result,
            })

        messages.append({"role": "user", "content": tool_results})

    # 파이프라인 완료 처리
    runner._finalize()
```

- [ ] **Step 2: runner.py에 run_director 진입점 추가**

`PipelineRunner.run()` 메서드에 `mode="director"` 분기 추가.

```python
# runner.py run() 메서드 수정
def run(self, from_step=None, only_step=None, dry_run=False, mode="legacy"):
    if mode == "director":
        from auto_agent.orchestrator.director import run_director
        run_director(self, from_step=from_step)
        return
    # 기존 로직 유지 ...
```

- [ ] **Step 3: _finalize 메서드 추출**

기존 run() 메서드 끝부분의 완료 처리를 `_finalize()`로 추출하여 Director에서도 재사용.

- [ ] **Step 4: _director_feedback 프롬프트 주입**

`_build_agent_prompt()`에서 `step.get("_director_feedback")`이 있으면 프롬프트에 추가.

```python
# _build_agent_prompt 수정
director_feedback = step.get("_director_feedback", "")
if director_feedback:
    prompt += f"\n\n<director_feedback>\n{director_feedback}\n</director_feedback>\n"
```

- [ ] **Step 5: 커밋**

```bash
git add auto_agent/orchestrator/director.py auto_agent/orchestrator/runner.py
git commit -m "feat: Director Agent 실행 루프 — Anthropic API 도구 루프 + 하네스"
```

---

## Chunk 4: CLI 통합 + Preflight 강화

### Task 5: CLI에 Director 모드 추가

**Files:**
- Modify: `auto_agent/cli.py` (cmd_run, cmd_bg)

- [ ] **Step 1: cmd_run에 --mode 플래그 추가**

```python
parser.add_argument("--mode", choices=["director", "legacy"], default="director",
                    help="실행 모드 (director: LLM 판단, legacy: 기존 for loop)")
# ...
runner.run(from_step=..., only_step=..., dry_run=..., mode=parsed.mode)
```

- [ ] **Step 2: cmd_bg에도 --mode 전달**

session_manager의 start()에 mode 파라미터 추가.

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/cli.py auto_agent/session_manager.py
git commit -m "feat: CLI에 --mode director/legacy 플래그 추가"
```

### Task 6: Preflight 강화 — 프리셋 + 도구 교차 검증

**Files:**
- Modify: `auto_agent/scripts/preflight_check.py`

- [ ] **Step 1: preflight에 프리셋 검증 추가**

```python
def check_preset(project_dir: Path) -> bool:
    """아트스타일 프리셋 완전성 검증."""
    art_style_path = project_dir / "art_style.json"
    if not art_style_path.exists():
        print("  [FAIL] art_style.json -- 누락")
        return False
    from auto_agent.data.artstyle.preset_schema import load_preset, validate_preset
    preset = load_preset(art_style_path)
    errors = validate_preset(preset)
    if errors:
        for e in errors:
            print(f"  [FAIL] preset -- {e}")
        return False
    print("  [OK] preset -- 검증 통과")
    return True
```

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/scripts/preflight_check.py
git commit -m "feat: preflight에 프리셋 완전성 + 도구 교차 검증 추가"
```

---

## Chunk 5: 볼트 선호도 + 통합 테스트

### Task 7: 볼트 preferences 초기 구조

**Files:**
- Create: `.vault/preferences/.gitkeep`

- [ ] **Step 1: preferences 디렉토리 생성 + README 업데이트**

`.vault/README.md`에 preferences 섹션 추가.

- [ ] **Step 2: 커밋**

```bash
git add .vault/
git commit -m "feat: 볼트 preferences 구조 추가"
```

### Task 8: 통합 테스트 — Director dry run

**Files:**
- 없음 (CLI 실행 테스트)

- [ ] **Step 1: Director 모드 dry run 테스트**

```bash
# 기존 프로젝트로 Director 모드 테스트
auto-agent run --project 배의_역사_1min_v2 --mode director --from step_10
```

Director가 도구를 호출하면서 step_10~12b를 이끌어가는지 확인.

- [ ] **Step 2: 레거시 모드 동작 확인**

```bash
auto-agent run --project 배의_역사_1min_v2 --mode legacy --from step_10
```

기존 방식이 그대로 동작하는지 확인.

- [ ] **Step 3: 메신저 출력 확인**

대시보드 메신저에 Director의 판단 메시지가 표시되는지 확인.

- [ ] **Step 4: 최종 커밋 + 푸시**

```bash
git push origin main
```

---

## 요약

| Chunk | Task | 핵심 산출물 |
|-------|------|------------|
| 1 | 프리셋 확장 | 4개 아트스타일 JSON + 스키마 검증 모듈 |
| 2 | Director 도구 | director_tools.py (9개 도구) + 스키마 |
| 3 | Director 하네스 | director.py (실행 루프) + 시스템 프롬프트 |
| 4 | CLI 통합 | --mode director/legacy + preflight 강화 |
| 5 | 볼트 + 테스트 | preferences 구조 + 통합 테스트 |
