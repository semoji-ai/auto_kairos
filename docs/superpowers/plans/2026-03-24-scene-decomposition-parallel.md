# step_5 씬 분할 챕터별 병렬화 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** step_5(scene_decomposition)를 원고 챕터 기준으로 병렬 호출하여 9분 → ~2분으로 단축

**Architecture:** 기존 `_run_chunked_parallel`은 scene_specs.json(씬 목록)을 입력으로 받아 챕터별 분할하지만, step_5는 아직 씬 목록이 없는 상태. 따라서 `final_manuscript.md`를 챕터별로 분할 → 각 챕터를 병렬로 씬 분할 CLI 호출 → 결과를 하나의 `scene_decomposition.json`으로 병합하는 새 메서드 `_run_manuscript_chunked_parallel`을 추가한다. pipeline.json에서 step_5에 `"chunked_parallel_manuscript": true` 플래그로 분기.

**Tech Stack:** Python 3.12, ThreadPoolExecutor, Claude CLI subprocess

---

## 파일 구조

| 파일 | 변경 | 역할 |
|------|------|------|
| `auto_agent/orchestrator/runner.py` | Modify | 새 메서드 추가 + step 분기 로직 |
| `auto_agent/data/pipeline.json` | Modify | step_5에 플래그 추가 |
| `auto_agent/data/prompts/single-call/scene-decomposition.md` | Create | 챕터별 씬 분할 전용 프롬프트 |

---

### Task 1: pipeline.json에 step_5 플래그 추가

**Files:**
- Modify: `auto_agent/data/pipeline.json:109-125`

- [ ] **Step 1: step_5에 `chunked_parallel_manuscript` 플래그 추가**

```json
{
  "id": "step_5",
  "name": "scene_decomposition",
  "description": "원고 → 씬 분할 (scene_decomposition.json 생성)",
  "type": "agent",
  "chunked_parallel_manuscript": true,
  "agent": "visual-composer",
  "input": [
    "final_manuscript.md",
    "outline.json",
    "research_report.json"
  ],
  "output": "scene_decomposition.json",
  "skills": [
    "shared/scene-segmentation"
  ],
  "notes": "원고를 챕터별로 분할 → 병렬 씬 분할 → 병합. 챕터 구분 없으면 단일 호출 폴백."
}
```

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/data/pipeline.json
git commit -m "feat: step_5에 chunked_parallel_manuscript 플래그 추가"
```

---

### Task 2: 챕터별 씬 분할 프롬프트 생성

**Files:**
- Create: `auto_agent/data/prompts/single-call/scene-decomposition.md`

- [ ] **Step 1: 프롬프트 파일 작성**

scene-segmentation 스킬의 핵심 규칙을 인라인으로 집약한 1턴 프롬프트.
프롬프트는 `{context_block}`, `{chapter_num}`, `{total_chapters}`, `{art_style_override}` 변수를 사용.

씬 분할 결과는 JSON으로 출력:
```json
{
  "scenes": [
    {
      "sceneNumber": 1,
      "chapter": 1,
      "narration": "...",
      "durationFrames": 270,
      "sceneIntent": "..."
    }
  ]
}
```

핵심 규칙:
- 1씬 = 1개념, 나레이션 80자 상한 (아트스타일 기준)
- sceneNumber는 챕터 내 로컬 번호 (병합 시 runner가 글로벌 번호로 재정렬)
- chapter 필드 필수 (병합 키로 사용)

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/data/prompts/single-call/scene-decomposition.md
git commit -m "feat: 챕터별 씬 분할 전용 프롬프트 추가"
```

---

### Task 3: runner.py에 원고 분할 + 병렬 처리 메서드 추가

**Files:**
- Modify: `auto_agent/orchestrator/runner.py`

- [ ] **Step 1: `_split_manuscript_by_chapter` 메서드 추가**

`final_manuscript.md`를 `# Ch1.`, `# Ch2.`, `# 프롤로그`, `# 에필로그` 등 `#` 헤딩 기준으로 분할.
반환: `{chapter_num: chapter_text}` dict.

```python
def _split_manuscript_by_chapter(self, manuscript_text: str) -> Optional[dict[int, str]]:
    """원고를 # 헤딩 기준 챕터로 분할.

    Returns:
        {1: "# 프롤로그: ...\n...", 2: "# Ch1. ...\n...", ...} 또는
        헤딩이 2개 미만이면 None (병렬화 불가)
    """
    heading_pattern = re.compile(r'^(#{1,2})\s+(.+)', re.MULTILINE)
    matches = list(heading_pattern.finditer(manuscript_text))

    if len(matches) < 2:
        return None

    chapters = {}
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(manuscript_text)
        chapter_num = i + 1  # 1-based
        chapters[chapter_num] = manuscript_text[start:end].strip()

    return chapters
```

- [ ] **Step 2: `_run_manuscript_chunked_parallel` 메서드 추가**

기존 `_run_chunked_parallel`과 유사하지만:
- 입력: `final_manuscript.md` (scene_specs.json 대신)
- 분할: `_split_manuscript_by_chapter`로 챕터별 텍스트 추출
- 각 챕터: Claude CLI 1턴 호출 (`scene-decomposition.md` 프롬프트 사용)
- 병합: 각 챕터의 scenes를 모아서 sceneNumber를 글로벌 연번으로 재정렬
- 출력: `scene_decomposition.json`
- 폴백: 챕터 2개 미만 → 기존 `_run_agent_step` 호출

```python
def _run_manuscript_chunked_parallel(self, step: dict) -> StepResult:
    """원고를 챕터별로 분할 → 병렬 씬 분할 → scene_decomposition.json 병합."""
    step_id = step["id"]
    step_name = step.get("name", step_id)
    agent_name = step.get("agent", "visual-composer")

    # 원고 로드
    manuscript_path = self.project_dir / "final_manuscript.md"
    if not manuscript_path.exists():
        return StepResult(step_id=step_id, status="failed",
                          error="final_manuscript.md 없음")

    manuscript_text = manuscript_path.read_text(encoding="utf-8")
    chapters = self._split_manuscript_by_chapter(manuscript_text)

    # 챕터 2개 미만 → 단일 호출 폴백
    if chapters is None:
        _notify(agent_name, "챕터 구분 불가 → 단일 호출로 전환합니다",
                phase=self.state.current_phase, project=self.project_slug,
                level="warning")
        return self._run_agent_step(step)

    n_chapters = len(chapters)
    _notify(agent_name,
            f"씬 분할 시작합니다 ({n_chapters} 챕터 병렬)",
            phase=self.state.current_phase, project=self.project_slug)

    self.state.current_step = step_id
    print(f"  [{step_id}] {step_name} ({n_chapters} 챕터 병렬) ... ", flush=True)

    run_id = self.pm.start_pipeline_run(
        project_id=self.project["id"],
        phase=self.state.current_phase,
        step=step_id, step_name=step_name,
        agent_or_module=agent_name,
    )

    t0 = time.time()
    chapter_results = {}
    total_cost = {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0}

    # 병렬 실행
    workers = min(n_chapters, 10)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        for ch_num, ch_text in chapters.items():
            fut = pool.submit(
                self._execute_manuscript_chapter,
                step, ch_num, ch_text, n_chapters,
            )
            futures[fut] = ch_num

        for fut in as_completed(futures):
            ch_num = futures[fut]
            try:
                ch_result = fut.result()
            except Exception as e:
                ch_result = ChapterResult(
                    chapter=ch_num, status="failed", error=str(e),
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
                    f"씬 분할 Ch{ch_num} 재시도합니다 ({retry}/2)",
                    phase=self.state.current_phase,
                    project=self.project_slug)
            time.sleep(5)
            try:
                ch_result = self._execute_manuscript_chapter(
                    step, ch_num, chapters[ch_num], n_chapters,
                )
                if ch_result.status == "completed":
                    chapter_results[ch_num] = ch_result
                    del failed_chapters[ch_num]
            except Exception:
                pass

    # 비용 합산
    for ch_result in chapter_results.values():
        for k in ("tokens_in", "tokens_out", "cost_usd"):
            total_cost[k] += ch_result.cost_info.get(k, 0)

    # 병합: 각 챕터의 scenes를 모아서 sceneNumber 재정렬
    all_scenes = []
    for ch_num in sorted(chapter_results.keys()):
        ch_result = chapter_results[ch_num]
        if ch_result.status == "completed" and ch_result.scenes:
            all_scenes.extend(ch_result.scenes)

    # sceneNumber 글로벌 재정렬
    for i, scene in enumerate(all_scenes, 1):
        scene["sceneNumber"] = i

    decomposition = {
        "version": "1.0",
        "total_scenes": len(all_scenes),
        "scenes": all_scenes,
    }

    decomp_path = self.project_dir / "scene_decomposition.json"
    decomp_path.write_text(
        json.dumps(decomposition, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    elapsed = time.time() - t0
    succeeded = sum(1 for r in chapter_results.values()
                    if r.status == "completed")
    failed_count = n_chapters - succeeded

    if failed_count == 0:
        msg = f"씬 분할 병합 완료 ({succeeded}/{n_chapters} 챕터, {len(all_scenes)}씬, {elapsed:.1f}s)"
        level = "success"
    elif succeeded > 0:
        msg = f"씬 분할 부분 완료 ({succeeded}/{n_chapters} 챕터, {failed_count} 실패)"
        level = "warning"
    else:
        msg = f"씬 분할 전체 실패 ({n_chapters} 챕터)"
        level = "error"

    _notify(agent_name, msg, phase=self.state.current_phase,
            project=self.project_slug, level=level)
    print(f"    {msg}")

    if succeeded > 0:
        self.pm.complete_pipeline_run(
            run_id,
            cost_tokens_in=total_cost.get("tokens_in", 0),
            cost_tokens_out=total_cost.get("tokens_out", 0),
            cost_usd=total_cost.get("cost_usd", 0.0),
        )
        return StepResult(
            step_id=step_id, status="completed",
            duration_sec=elapsed,
            output_files=[str(decomp_path)],
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
```

- [ ] **Step 3: `_execute_manuscript_chapter` 메서드 추가**

단일 챕터에 대해 Claude CLI 1턴 호출. `_execute_chapter`를 참고하되, 입력이 scene_specs가 아니라 원고 텍스트인 점이 다름.

```python
def _execute_manuscript_chapter(
    self, step: dict, chapter_num: int,
    chapter_text: str, total_chapters: int,
) -> ChapterResult:
    """원고 챕터 1개에 대해 Claude CLI 씬 분할 호출."""
    step_id = step["id"]
    step_name = step.get("name", step_id)
    agent_name = step.get("agent", "visual-composer")

    _notify(agent_name,
            f"씬 분할 시작합니다 (Ch{chapter_num}/{total_chapters})",
            phase=self.state.current_phase,
            project=self.project_slug)

    t0 = time.time()

    # 프롬프트 빌드
    prompt = self._build_manuscript_chapter_prompt(
        step, chapter_num, chapter_text, total_chapters,
    )

    # Claude CLI 호출 (1턴, 도구 비활성화)
    try:
        cli_result = self._call_claude_cli(
            prompt=prompt,
            agent_name=agent_name,
            step=step,
            tools_disabled=True,
            output_format="json",
        )
    except Exception as e:
        return ChapterResult(
            chapter=chapter_num, status="failed", error=str(e),
        )

    # JSON 파싱
    try:
        result_data = json.loads(cli_result.output)
        scenes = result_data.get("scenes", [])
        # chapter 필드 보장
        for scene in scenes:
            scene["chapter"] = chapter_num
    except (json.JSONDecodeError, AttributeError) as e:
        return ChapterResult(
            chapter=chapter_num, status="failed",
            error=f"JSON 파싱 실패: {e}",
        )

    elapsed = time.time() - t0
    cost_info = cli_result.cost_info if hasattr(cli_result, 'cost_info') else {}

    _notify(agent_name,
            f"씬 분할 완료 (Ch{chapter_num}, {len(scenes)}씬, {elapsed:.1f}s)",
            phase=self.state.current_phase,
            project=self.project_slug, level="success")

    return ChapterResult(
        chapter=chapter_num, status="completed",
        scenes=scenes,
        cost_info=cost_info, duration_sec=elapsed,
    )
```

- [ ] **Step 4: `_build_manuscript_chapter_prompt` 메서드 추가**

```python
def _build_manuscript_chapter_prompt(
    self, step: dict, chapter_num: int,
    chapter_text: str, total_chapters: int,
) -> str:
    """씬 분할용 챕터 프롬프트 빌드."""
    # 프롬프트 템플릿 로드
    prompt_key = "prompts/single-call/scene-decomposition.md"
    template = self.rule_manager.load(prompt_key)

    # 컨텍스트
    context_block = ""
    for fname in ["research_report.json", "outline.json"]:
        fpath = self.project_dir / fname
        if fpath.exists():
            context_block += (
                f"\n<file name=\"{fname}\">\n"
                f"{fpath.read_text(encoding='utf-8')[:30000]}\n"
                f"</file>\n"
            )

    art_style_override = self._load_art_style_override("scene_decomposition")

    prompt = template.replace("{context_block}", context_block)
    prompt = prompt.replace("{chapter_text}", chapter_text)
    prompt = prompt.replace("{chapter_num}", str(chapter_num))
    prompt = prompt.replace("{total_chapters}", str(total_chapters))
    prompt = prompt.replace("{art_style_override}", art_style_override)

    return prompt
```

- [ ] **Step 5: step 실행 분기에 `chunked_parallel_manuscript` 추가**

`runner.py`의 step 실행 분기 (라인 1972 부근)에서:

```python
# chunked_parallel_manuscript 분기 (step_5 씬 분할 병렬)
if step.get("chunked_parallel_manuscript"):
    return self._run_manuscript_chunked_parallel(step)

# chunked_parallel 분기 (step_6 등 기존)
if step.get("chunked_parallel"):
    return self._run_chunked_parallel(step)
```

- [ ] **Step 6: SINGLE_CALL_PROMPTS에 scene_decomposition 추가**

```python
SINGLE_CALL_PROMPTS = {
    "creative_direction": "creative-direction.md",
    "data_enrichment": "data-enrichment.md",
    "motion_planning": "motion-planning.md",
    "tts_preprocess": "tts-preprocess.md",
    "scene_decomposition": "scene-decomposition.md",  # 추가
}
```

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "feat: step_5 씬 분할 챕터별 병렬 처리 구현"
```

---

### Task 4: 통합 테스트

- [ ] **Step 1: 기존 완료된 프로젝트로 씬 분할만 재실행**

```bash
auto-agent run --project 삼성vs하이닉스_70조전쟁_10min --only-step step_5
```

- [ ] **Step 2: 결과 검증**

- `scene_decomposition.json`이 생성되었는지
- 모든 챕터의 씬이 포함되었는지
- sceneNumber가 1부터 연속인지
- chapter 필드가 올바른지

- [ ] **Step 3: 후속 step_6과 호환 확인**

step_6(creative_direction)이 새 scene_decomposition.json을 정상적으로 읽는지 확인.
`_run_chunked_parallel`이 `_decomp_to_specs`로 변환하는 부분과 호환되어야 함.
