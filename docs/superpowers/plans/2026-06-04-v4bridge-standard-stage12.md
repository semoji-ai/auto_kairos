# v4-bridge 표준 Stage 1/2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v4 리서치+원고 워크플로를 v3 Stage 1/2의 표준 경로로 만들고, 그 사이를 얇은 번역층(어댑터 + finalize-for-bridge)으로 잇되, 네이티브 v3 stage 1/2는 플래그 뒤로 보존하여 git pull만으로 적용되게 한다.

**Architecture:** v4와 v3는 데이터 포맷이 다르다(v4=마크다운 스킬 산출물, v3=JSON+마커 원고). "교체"의 본질은 이 둘 사이 번역층 2개다 — ① `adapter`(마크다운 리서치 → JSON, 기존 모듈, 파이프라인 스텝으로 승격) ② `finalize-for-bridge`(v4 draft prose → v3 마커 원고 + outline.json, LLM 판단, 신규 스킬). 네이티브 stage 1/2 스텝은 `legacy_only: true` + `ENABLE_LEGACY_V3` 게이팅으로 기본 스킵.

**Tech Stack:** Python 3.12, pytest, JSON pipeline 설정, Claude Code 스킬(마크다운), subprocess 모듈 디스패치.

선행 spec: `docs/superpowers/specs/2026-06-04-v4bridge-standard-stage12-design.md`

---

## File Structure

| 파일 | 책임 | 작업 |
|------|------|------|
| `auto_agent/orchestrator/runner.py` | 레거시 게이팅 순수함수 + 어댑터 모듈 디스패치 | 수정 |
| `tests/test_runner_legacy_gating.py` | 게이팅/어댑터 cmd 순수함수 단위 테스트 | 생성 |
| `auto_agent/data/pipeline.json` | `step_1_v4bridge` 추가 + 네이티브 12스텝 `legacy_only` | 수정 |
| `tests/test_pipeline_v4bridge_config.py` | pipeline.json 구조 검증 | 생성 |
| `.claude/skills/v4/finalize-for-bridge/SKILL.md` | v4 draft → 마커 원고 + outline.json | 생성 |
| `.claude/skills/v4/deep-research/SKILL.md` | 외부 실행기 → 내장 WebSearch/Fetch/Workflow | 수정 |
| `.claude/skills/auto-kairos.md` | 실행부를 v4 워크플로 오케스트레이션으로 개정 | 수정 |

---

## Task 1: 레거시 게이팅 순수함수 + _execute_step 배선

**Files:**
- Modify: `auto_agent/orchestrator/runner.py` (모듈 레벨 함수 추가 + `_execute_step` 3282줄 근처)
- Test: `tests/test_runner_legacy_gating.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_runner_legacy_gating.py` 생성:

```python
from auto_agent.orchestrator.runner import is_legacy_gated


def test_legacy_only_step_gated_when_flag_off():
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=False) is True


def test_legacy_only_step_runs_when_flag_on():
    step = {"id": "step_2_draft", "legacy_only": True}
    assert is_legacy_gated(step, enable_legacy=True) is False


def test_non_legacy_step_never_gated():
    step = {"id": "step_2", "name": "chapters"}
    assert is_legacy_gated(step, enable_legacy=False) is False
    assert is_legacy_gated(step, enable_legacy=True) is False
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_runner_legacy_gating.py -v`
Expected: FAIL — `ImportError: cannot import name 'is_legacy_gated'`

- [ ] **Step 3: 순수함수 구현**

`auto_agent/orchestrator/runner.py` 모듈 레벨(클래스 정의 위, import 직후 적당한 위치)에 추가:

```python
def is_legacy_gated(step: dict, enable_legacy: bool) -> bool:
    """legacy_only 스텝인데 ENABLE_LEGACY_V3가 꺼져 있으면 True(스킵 대상).

    v4-bridge가 표준 Stage 1/2 경로이므로 네이티브 v3 스텝은 기본 스킵.
    ENABLE_LEGACY_V3=1 일 때만 네이티브 경로 복구.
    """
    return bool(step.get("legacy_only")) and not enable_legacy
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_runner_legacy_gating.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: _execute_step에 배선**

`auto_agent/orchestrator/runner.py`의 `_execute_step` 안, 기존 sentinel skip 블록(`_v4_bridge_skip_steps` 처리, 3277-3281줄) **바로 다음**에 추가:

```python
        # 레거시 v3 stage 1/2 게이팅 — v4-bridge가 표준 경로.
        # ENABLE_LEGACY_V3=1 일 때만 네이티브 스텝 실행.
        if is_legacy_gated(step, os.environ.get("ENABLE_LEGACY_V3") == "1"):
            print(f"  [SKIP] {step_id}: legacy_only — v4-bridge 표준 (복구: ENABLE_LEGACY_V3=1)")
            return StepResult(step_id=step_id, status="skipped")
```

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/orchestrator/runner.py tests/test_runner_legacy_gating.py
git commit -m "feat(runner): legacy_only 게이팅 — v4-bridge 표준, ENABLE_LEGACY_V3로 복구

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: 어댑터를 파이프라인 모듈 스텝으로 등록

어댑터는 상대 임포트(`from .build_research_report import ...`) 때문에 `script_map`의 `[python, script.py]` 방식으로는 못 돌리고 `-m auto_agent.modules.v4_bridge.adapter`로 호출해야 한다.

**Files:**
- Modify: `auto_agent/orchestrator/runner.py` (`_run_module_step` 4311줄 근처 + 신규 메서드 + cmd 순수함수)
- Test: `tests/test_runner_legacy_gating.py` (cmd 빌더 테스트 추가)

- [ ] **Step 1: cmd 빌더 실패 테스트 추가**

`tests/test_runner_legacy_gating.py`에 추가:

```python
import sys
from auto_agent.orchestrator.runner import build_adapter_cmd


def test_build_adapter_cmd_basic():
    cmd = build_adapter_cmd("/proj/abc_slug", "quirky_cartoon", None)
    assert cmd == [
        sys.executable, "-m", "auto_agent.modules.v4_bridge.adapter",
        "--project", "/proj/abc_slug", "--style-id", "quirky_cartoon",
    ]


def test_build_adapter_cmd_strips_json_and_path():
    cmd = build_adapter_cmd("/proj/x", "styles/semoji.json", "dark")
    assert "--style-id" in cmd
    assert cmd[cmd.index("--style-id") + 1] == "semoji"
    assert cmd[-2:] == ["--theme", "dark"]


def test_build_adapter_cmd_ignores_invalid_theme():
    cmd = build_adapter_cmd("/proj/x", "lego", "weird")
    assert "--theme" not in cmd
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_runner_legacy_gating.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_adapter_cmd'`

- [ ] **Step 3: cmd 빌더 순수함수 구현**

`auto_agent/orchestrator/runner.py` 모듈 레벨(`is_legacy_gated` 옆)에 추가:

```python
def build_adapter_cmd(project_dir: str, art_style: str, theme: str | None) -> list[str]:
    """v4_bridge adapter를 -m 모듈로 실행하는 커맨드 빌드.

    art_style은 'styles/semoji.json' 같은 형태일 수 있어 stem만 추출.
    theme은 dark|light 만 전달, 그 외(None 포함)는 생략.
    """
    style_id = (art_style or "quirky_cartoon").replace(".json", "").split("/")[-1]
    cmd = [
        sys.executable, "-m", "auto_agent.modules.v4_bridge.adapter",
        "--project", project_dir, "--style-id", style_id,
    ]
    if theme in ("dark", "light"):
        cmd += ["--theme", theme]
    return cmd
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_runner_legacy_gating.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: _run_module_step에 어댑터 특례 + 실행 메서드 추가**

`auto_agent/orchestrator/runner.py`의 `_run_module_step` 안, `if module_name == "video-assembler":` 블록(4311줄) **바로 위**에 추가:

```python
        if module_name == "v4_bridge_adapter":
            return self._run_v4_bridge_adapter(step, env)
```

그리고 `_run_module_step` 메서드 **바로 아래**에 신규 메서드 추가:

```python
    def _run_v4_bridge_adapter(self, step: dict, env: dict) -> StepResult:
        """v4 산출물(marked manuscript + outline) → v3 입력 변환.

        v4 산출물이 없으면(예: 레거시 실행) graceful skip.
        """
        step_id = step["id"]
        marked = self.project_dir / "final_manuscript_marked.md"
        if not marked.exists():
            print(f"  [SKIP] {step_id}: v4 산출물 없음(final_manuscript_marked.md)")
            return StepResult(step_id=step_id, status="skipped")

        cmd = build_adapter_cmd(
            str(self.project_dir),
            self.state.config.get("art_style", ""),
            self.state.config.get("video_theme"),
        )
        ws = str(get_workspace_dir())
        env = dict(env)
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (ws + os.path.pathsep + existing) if existing else ws

        result = subprocess.run(
            cmd, cwd=ws, env=env,
            capture_output=True, text=True, encoding="utf-8",
            timeout=600, **subprocess_kwargs(),
        )
        if result.returncode == 0:
            return StepResult(step_id=step_id, status="completed")
        print(f"\n    [ERROR] v4_bridge_adapter stderr:\n{result.stderr}", flush=True)
        return StepResult(
            step_id=step_id, status="failed",
            error=result.stderr or result.stdout[-2000:],
        )
```

- [ ] **Step 6: 전체 테스트 확인**

Run: `python -m pytest tests/test_runner_legacy_gating.py -v`
Expected: PASS (6 passed)

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/orchestrator/runner.py tests/test_runner_legacy_gating.py
git commit -m "feat(runner): v4_bridge_adapter 모듈 스텝 등록 (-m 호출, 산출물 없으면 skip)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: pipeline.json — step_1_v4bridge 추가 + 네이티브 legacy_only

**Files:**
- Modify: `auto_agent/data/pipeline.json`
- Test: `tests/test_pipeline_v4bridge_config.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_pipeline_v4bridge_config.py` 생성:

```python
import json
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1] / "auto_agent" / "data" / "pipeline.json"

LEGACY_STEPS = {
    "step_1a", "step_1_strategy", "step_1_fresh", "step_1_vault_lookup",
    "step_1d_wiki_compile", "step_1b", "step_1c",
    "step_2_draft", "step_2_target", "step_2_target_register",
    "step_2_target_deepen", "step_2_manuscript",
}


def _all_steps():
    p = json.loads(PIPELINE.read_text(encoding="utf-8"))
    out = {}
    for ph in p["phases"]:
        for s in ph.get("steps", []):
            out[s["id"]] = s
    return out


def test_v4bridge_step_exists_and_is_module():
    steps = _all_steps()
    assert "step_1_v4bridge" in steps
    s = steps["step_1_v4bridge"]
    assert s["type"] == "module"
    assert s["module"] == "v4_bridge_adapter"
    assert not s.get("legacy_only")  # 표준 스텝은 게이팅 안 됨


def test_v4bridge_is_first_in_stage_1():
    p = json.loads(PIPELINE.read_text(encoding="utf-8"))
    stage1 = next(ph for ph in p["phases"] if ph["id"] == "stage_1")
    assert stage1["steps"][0]["id"] == "step_1_v4bridge"


def test_native_stage12_steps_are_legacy_only():
    steps = _all_steps()
    for sid in LEGACY_STEPS:
        assert steps.get(sid, {}).get("legacy_only") is True, f"{sid} legacy_only 누락"


def test_chapters_step_not_legacy():
    steps = _all_steps()
    assert not steps["step_2"].get("legacy_only")  # 씬분할은 v4-bridge 경로에서도 실행
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_pipeline_v4bridge_config.py -v`
Expected: FAIL — `step_1_v4bridge` 부재 + legacy_only 누락

- [ ] **Step 3: step_1_v4bridge 추가**

`auto_agent/data/pipeline.json`의 `stage_1` phase `steps` 배열 **맨 앞**에 삽입:

```json
{
  "id": "step_1_v4bridge",
  "name": "v4_bridge_adapter",
  "description": "v4 워크플로 산출물(marked manuscript + outline + research_*)을 v3 Stage 2 입력(research_report.json/targeted_claims.json/art_style.json/final_manuscript.md)으로 변환. v4 산출물 없으면 graceful skip.",
  "type": "module",
  "module": "v4_bridge_adapter",
  "input": [
    "final_manuscript_marked.md",
    "outline.json",
    "research_reports/",
    "research_targeted/"
  ],
  "output": [
    "research_report.json",
    "targeted_claims.json",
    "art_style.json",
    "final_manuscript.md"
  ],
  "resumable": true,
  "notes": "PD가 finalize-for-bridge로 만든 v4 산출물 전제. 어댑터가 .v4_bridge_origin sentinel을 떨궈 step_2b/2c 자동 스킵."
}
```

- [ ] **Step 4: 네이티브 12스텝에 legacy_only 추가**

다음 스텝 각 객체에 `"legacy_only": true` 필드를 추가한다 (stage_1: `step_1a`, `step_1_strategy`, `step_1_fresh`, `step_1_vault_lookup`, `step_1d_wiki_compile`, `step_1b`, `step_1c` / stage_2: `step_2_draft`, `step_2_target`, `step_2_target_register`, `step_2_target_deepen`, `step_2_manuscript`). 예시(step_1a):

```json
{
  "id": "step_1a",
  "name": "skeleton_research",
  "legacy_only": true,
  "type": "module",
  ...
}
```

> 주의: `step_1_ingest`(LEGACY)는 이미 ENABLE_LEGACY_INGEST 게이팅이라 건드리지 않는다. `step_2`(chapters), `step_2_consistency`, `step_2_data`, `step_2d`, `step_2_vault_sync`는 v4-bridge 경로에서도 실행되므로 legacy_only를 붙이지 않는다.

- [ ] **Step 5: JSON 유효성 + 테스트 통과 확인**

Run: `python -c "import json; json.load(open('auto_agent/data/pipeline.json')); print('valid json')"`
Expected: `valid json`

Run: `python -m pytest tests/test_pipeline_v4bridge_config.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: 커밋**

```bash
git add auto_agent/data/pipeline.json tests/test_pipeline_v4bridge_config.py
git commit -m "feat(pipeline): step_1_v4bridge 추가 + 네이티브 stage1/2 legacy_only

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: finalize-for-bridge 스킬 신규 작성

v4 draft(순수 prose)에 v3 마커를 박고 outline.json을 만드는 LLM 스킬. 마커 규약은 script-director가 단일 소스이므로 **참조만** 한다(중복 기재 금지).

**Files:**
- Create: `.claude/skills/v4/finalize-for-bridge/SKILL.md`

- [ ] **Step 1: SKILL.md 작성**

`.claude/skills/v4/finalize-for-bridge/SKILL.md` 생성:

```markdown
---
name: finalize-for-bridge
description: v4 draft(순수 prose)를 v3 Stage 2 입력으로 변환. 씬/챕터/캐릭터 마커 삽입 + outline.json 생성. v4 원고 작성 완료 후 adapter 실행 직전에 호출.
---

# finalize-for-bridge

v4 워크플로의 마지막 단계. draft의 순수 prose에 v3 씬분할이 요구하는 마커를 박고
outline.json을 생성한다. **narration 텍스트는 한 글자도 바꾸지 않는다**(마커/주석/헤더만 추가).

## Reads
- 최신 `drafts/v{n}.md` (순수 prose)
- `research_reports/*.md`, `research_targeted/*.md` (캐릭터·챕터 판단 근거)
- (선택) `plan.md`, `pd_notebook.md` (톤·기획 의도)

## Writes
- `final_manuscript.md` — draft prose 그대로(클린, frontmatter 제거)
- `final_manuscript_marked.md` — 마커 삽입본
- `outline.json` — 챕터 메타데이터

## 마커 규약 (단일 소스: auto_agent/data/skills/agents/script-director/SKILL.md "마커" 절)
- `# Ch N. 제목` — 챕터 경계 (outline 챕터와 1:1)
- `---` — 씬 경계 (의미 단위 1개 = `---` 1개. 8분 분량 기준 40~50개)
- `<!-- chars: ID1, ID2 -->` — 대명사/주어생략 씬의 등장 인물(2씬+ 등장만)
  - `---` 다음 줄 또는 씬 시작 직후 배치
  - 동일 인물은 전체에서 동일 문자열

상세 삽입 기준·예시는 script-director SKILL.md를 따른다. 여기서 중복 기재하지 않는다.

## outline.json 스키마
`auto_agent/modules/v4_bridge/schema_samples/outline.example.json` 형식을 따른다.

## 불변 보장
final_manuscript_marked.md에서 마커(`#`/`---`/`<!-- -->`)와 frontmatter를 제거하면
final_manuscript.md와 정확히 일치해야 한다. adapter의 substring 검증을 통과해야 하며,
실패 시 ValueError로 차단된다.

## 실행 절차
1. 최신 draft 발견 → frontmatter 제거하여 final_manuscript.md 저장
2. research로 챕터 구조·등장 인물 파악 → outline.json 작성
3. final_manuscript.md 복사본에 # Ch / --- / <!-- chars: --> 삽입 → final_manuscript_marked.md
4. 자체 검증: marked에서 마커 제거 → final_manuscript.md와 일치 확인

## 금지
- narration 텍스트 변경(요약/재작성/오탈자 수정 포함 — proofread 단계에서 이미 완료)
- layout/motion/imageAsset/headline 등 연출 결정(v3 step_2 책임)

## 한국어 작성 규칙
- 가타카나/히라가나/한자 금지
```

- [ ] **Step 2: 마커 규약이 script-director와 일치하는지 교차 확인**

Run: `grep -nE "# Ch N|<!-- chars|^---" auto_agent/data/skills/agents/script-director/SKILL.md | head`
Expected: 3종 마커가 script-director에 존재함을 확인 (SKILL.md가 규약 단일 소스)

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/v4/finalize-for-bridge/SKILL.md
git commit -m "feat(v4): finalize-for-bridge 스킬 — draft prose에 v3 마커 + outline.json

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: deep-research SKILL.md — 외부 실행기 → 내장 도구

외부 deep-research 실행기 의존을 제거하고 Claude Code 내장(WebSearch/WebFetch/Workflow)로 대체.

**Files:**
- Modify: `.claude/skills/v4/deep-research/SKILL.md`

- [ ] **Step 1: description + 실행 절차 재작성**

`.claude/skills/v4/deep-research/SKILL.md`에서 다음을 변경:

(1) frontmatter `description` 줄 — `"외부 deep-research 스킬을 실행기로 사용"` 부분을 삭제하고:
```
description: 주제의 깊은 맥락·역사·구조·논쟁·핵심 근거를 수집. 역사·인물·기업·논쟁적 주제·다큐형 영상에 사용. Claude Code 내장 도구(WebSearch/WebFetch/Workflow)로 직접 수행.
```

(2) `## 반환` 절 **바로 앞**에 `## 실행 방법` 절을 신규 삽입:
```markdown
## 실행 방법 (내장 도구)

외부 실행기를 쓰지 않는다. Claude Code 내장 도구로 직접 수행:

1. **fan-out**: Workflow 도구로 주제 갈래(역사/구조/논쟁/인물 등)별 병렬 리서처를 띄운다.
   각 리서처는 WebSearch로 후보 출처를 찾고 WebFetch로 본문을 가져온다.
2. **adversarial verify**: 핵심 주장마다 회의적 검증 에이전트를 붙여 반론 시도.
   다수가 반박하면 주장 폐기.
3. **synthesize**: 검증 통과 주장만 인용과 함께 `research_reports/{slug}.md`로 합성.

Workflow 미사용 환경(경량 호출)에서는 메인 컨텍스트에서 WebSearch/WebFetch를
순차 사용하여 동일 산출물을 만든다.
```

- [ ] **Step 2: 외부 실행기 잔존 참조 0 확인**

Run: `grep -niE "외부.*실행기|외부 deep-research 스킬을 실행" .claude/skills/v4/deep-research/SKILL.md`
Expected: 출력 없음 (잔존 참조 0)

- [ ] **Step 3: 커밋**

```bash
git add .claude/skills/v4/deep-research/SKILL.md
git commit -m "refactor(v4): deep-research 외부 실행기 의존 제거 → 내장 WebSearch/Fetch/Workflow

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: auto-kairos 스킬 실행부 개정

인터뷰(기존 유지) 후 v4 워크플로 오케스트레이션 → finalize-for-bridge → `auto-agent run`으로 개정.

**Files:**
- Modify: `.claude/skills/auto-kairos.md`

- [ ] **Step 1: 현재 실행부 확인**

Run: `grep -nE "auto-agent run|step_|파이프라인 실행|### [0-9]단계" .claude/skills/auto-kairos.md`
Expected: 인터뷰 단계 + `auto-agent run` 호출 위치 파악

- [ ] **Step 2: 파이프라인 실행 단계를 v4 워크플로로 교체**

`.claude/skills/auto-kairos.md`에서 인터뷰/브리프 게이트 다음의 "파이프라인 실행" 단계를 다음 흐름으로 개정한다 (정확한 줄 위치는 Step 1 결과로 확인):

```markdown
### N단계: v4 워크플로 (PD 오케스트레이션)

프로젝트 디렉토리 생성 후, PD가 v4 스킬을 순서대로 진행한다:

1. `strategy-explore` — 각도/훅/구조 옵션
2. `fresh-research`(가벼운 경로) 또는 `deep-research`(깊은 경로) — research_reports/
3. `target-research` — research_targeted/
4. `draft-write` — drafts/v{n}.md
5. `proofread` — 언어 검토
6. `finalize-for-bridge` — final_manuscript_marked.md + final_manuscript.md + outline.json

### N+1단계: v3 파이프라인 (씬분할 + 소스 제작)

```bash
auto-agent run --project <slug>
```

- step_1_v4bridge(어댑터)가 v4 산출물을 v3 입력으로 변환
- 네이티브 stage 1/2는 legacy_only로 자동 스킵 (ENABLE_LEGACY_V3 미설정 시)
- step_2(씬분할) → Stage 3(조립/렌더)로 진행
```

네이티브 v3 stage 1/2를 직접 호출하던 기존 서술이 있으면 제거한다.

- [ ] **Step 3: 정합성 확인**

Run: `grep -nE "finalize-for-bridge|v4_bridge|legacy_only|auto-agent run" .claude/skills/auto-kairos.md`
Expected: v4 워크플로 단계 + `auto-agent run` 호출이 존재

- [ ] **Step 4: 커밋**

```bash
git add .claude/skills/auto-kairos.md
git commit -m "feat(skill): auto-kairos 실행부를 v4 워크플로 오케스트레이션으로 개정

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: .claude/skills/v4 전체 git 추적 (자체완결성)

현재 13개 untracked → git pull 전파 위해 전부 커밋.

**Files:**
- Add (track): `.claude/skills/v4/` 트리 전체

- [ ] **Step 1: 추적 누락 파일 확인**

Run: `git status --porcelain .claude/skills/v4/ | head -30`
Expected: deep-research/draft-write/finalize-for-bridge 등 다수 `??`/`A` 표시

- [ ] **Step 2: gitignore 제외 여부 재확인**

Run: `git check-ignore -v .claude/skills/v4/draft-write/SKILL.md || echo "추적 가능"`
Expected: `추적 가능`

- [ ] **Step 3: 전체 add + 커밋**

```bash
git add .claude/skills/v4/
git status --short .claude/skills/v4/ | wc -l
git commit -m "feat(v4): .claude/skills/v4 전체 git 추적 — git pull 자체완결성

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 4: 자체완결성 검증 (추적 누락 0)**

Run: `git status --porcelain .claude/skills/v4/`
Expected: 출력 없음 (모두 추적됨)

Run: `grep -rhoE "^(import|from) [a-zA-Z_]+" .claude/skills/v4/shared/lib/*.py | sort -u`
Expected: 표준 라이브러리만 (외부 pip 패키지 없음 — 자체완결 확인)

---

## Task 8: 통합 검증

**Files:** (변경 없음 — 검증만)

- [ ] **Step 1: 전체 단위 테스트 통과**

Run: `python -m pytest tests/test_runner_legacy_gating.py tests/test_pipeline_v4bridge_config.py -v`
Expected: PASS (10 passed)

- [ ] **Step 2: pipeline.json 로드 정상**

Run: `python -c "import json; p=json.load(open('auto_agent/data/pipeline.json')); ids=[s['id'] for ph in p['phases'] for s in ph['steps']]; assert 'step_1_v4bridge' in ids; print('OK', len(ids), 'steps')"`
Expected: `OK <n> steps`

- [ ] **Step 3: runner import 정상 (순수함수 노출)**

Run: `python -c "from auto_agent.orchestrator.runner import is_legacy_gated, build_adapter_cmd; print('imports OK')"`
Expected: `imports OK`

- [ ] **Step 4: 어댑터 모듈 -m 호출 가능 확인 (--help)**

Run: `python -m auto_agent.modules.v4_bridge.adapter --help`
Expected: argparse usage 출력 (`--project`, `--style-id`, `--theme`)

---

## Self-Review (작성자 체크 완료)

- **Spec coverage**: §5.1 finalize→Task4, §5.2 deep-research→Task5, §5.3 pipeline→Task3,
  §5.4 runner→Task1+2, §5.5 auto-kairos→Task6, §5.6 git→Task7. 전부 매핑됨.
- **Placeholder scan**: TBD/TODO 없음. 모든 코드 스텝에 실제 코드 포함.
- **Type consistency**: `is_legacy_gated`, `build_adapter_cmd`, `_run_v4_bridge_adapter`,
  모듈명 `v4_bridge_adapter` — Task 간 명칭 일치 확인.
