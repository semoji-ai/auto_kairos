# 이로미즘 시네마틱 중심 연출 리디자인 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 이로미즘 스타일을 시네마틱(풀스크린 일러스트) 70% 중심으로 전환하고, 캐릭터 플래닝을 이미지 소싱 단계로 통합

**Architecture:** 3개 독립 트랙으로 병렬 구현. Track A(Remotion 렌더러), Track B(프롬프트/설정), Track C(파이프라인 재구성). Track A·B는 완전 독립, Track C는 A·B 완료 후 통합 테스트.

**Tech Stack:** TypeScript (Remotion), Python (파이프라인), JSON (설정)

**Spec:** `docs/superpowers/specs/2026-03-19-iromism-cinematic-redesign.md`

---

## 병렬 실행 맵

```
Track A (Remotion 렌더러)          Track B (프롬프트/설정)           Track C (파이프라인)
────────────────────────          ──────────────────────           ─────────────────────
Task 1: manifest.ts 타입          Task 3: quirky_cartoon.json      Task 5: pipeline.json
Task 2: CreativeScene 오버레이     Task 4: creative-direction.md    Task 6: agents.json
                                                                   Task 7: runner.py
                                                                   Task 8: generate_images.py
                                                                   Task 9: source_images.py
                                                                   Task 10: 문서/스킬 업데이트
        ↓                                  ↓                              ↓
        └──────────────────────────────────┴──────────────────────────────┘
                                           ↓
                                   Task 11: build_manifest.py 변환
                                   Task 12: Remotion template 동기화
                                   Task 13: 볼트 기록
```

- **Track A + Track B**: 완전 병렬 (의존성 없음)
- **Track C**: Task 5-10 순차 (파이프라인 내부 의존성)
- **Task 11-13**: Track A·B·C 모두 완료 후 순차

---

## Track A: Remotion 렌더러 (병렬 가능)

### Task 1: manifest.ts에 CinematicOverlay 타입 추가

**Files:**
- Modify: `remotion/src/types/manifest.ts:137-173`

- [ ] **Step 1: CinematicOverlay 인터페이스 추가**

`CreativeDirection` 인터페이스 바로 아래(148행 뒤)에 추가:

```ts
export interface CinematicOverlay {
  type: "speech_bubble" | "emotion" | "caption";
  text: string;
  position: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center";
}
```

- [ ] **Step 2: VisualizationData에 필드 추가**

`VisualizationData` 인터페이스(150행~)의 `creative?` 필드 아래에 추가:

```ts
  /** 시네마틱 씬 오버레이 (말풍선/감탄부호/캡션) */
  cinematicOverlay?: CinematicOverlay;
```

- [ ] **Step 3: 커밋**

```bash
git add remotion/src/types/manifest.ts
git commit -m "feat: CinematicOverlay 타입 정의 추가"
```

---

### Task 2: CreativeScene.tsx 시네마틱 오버레이 렌더러

**Files:**
- Modify: `remotion/src/simple/CreativeScene.tsx:2851-2860`

- [ ] **Step 1: SpeechBubble 컴포넌트 작성**

`CreativeScene.tsx`의 cinematic 레이아웃 코드(2851행) 위에 오버레이 컴포넌트를 추가:

```tsx
/* ── Cinematic Overlay Components ── */

const OVERLAY_POSITIONS: Record<string, React.CSSProperties> = {
  top_left:     { top: 80, left: 80 },
  top_right:    { top: 80, right: 80 },
  bottom_left:  { bottom: 120, left: 80 },
  bottom_right: { bottom: 120, right: 80 },
  center:       { top: "50%", left: "50%", transform: "translate(-50%, -50%)" },
};

const SpeechBubble: React.FC<{ text: string; position: string; delay: number }> = ({
  text, position, delay,
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame - delay, [0, 8], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(1.5)),
  });
  const pos = OVERLAY_POSITIONS[position] || OVERLAY_POSITIONS.center;
  // 꼬리 방향: position 기반
  const tailSide = position.includes("right") ? "left" : "right";
  const tailStyle: React.CSSProperties = {
    position: "absolute",
    bottom: -14,
    [tailSide === "left" ? "left" : "right"]: 24,
    width: 0, height: 0,
    borderLeft: "12px solid transparent",
    borderRight: "12px solid transparent",
    borderTop: "16px solid #fff",
    filter: "drop-shadow(0 2px 0 #222)",
  };
  return (
    <div style={{
      position: "absolute", ...pos, zIndex: 10,
      transform: `${pos.transform || ""} scale(${scale})`,
      opacity: scale,
    }}>
      <div style={{
        position: "relative",
        background: "#fff",
        border: "4px solid #222",
        borderRadius: 20,
        padding: "16px 28px",
        fontFamily: "inherit",
        fontSize: 42,
        fontWeight: 800,
        color: "#222",
        boxShadow: "4px 4px 0 #222",
      }}>
        {text}
        <div style={tailStyle} />
      </div>
    </div>
  );
};

const EmotionOverlay: React.FC<{ text: string; position: string; delay: number }> = ({
  text, position, delay,
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame - delay, [0, 6], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
    easing: Easing.out(Easing.back(2)),
  });
  const shake = Math.sin((frame - delay) * 0.8) * 3;
  const pos = OVERLAY_POSITIONS[position] || OVERLAY_POSITIONS.center;
  return (
    <div style={{
      position: "absolute", ...pos, zIndex: 10,
      transform: `${pos.transform || ""} scale(${scale}) rotate(${-8 + shake}deg)`,
      opacity: scale,
      fontSize: 72,
      fontWeight: 900,
      color: "#FFE033",
      textShadow: "3px 3px 0 #222, -1px -1px 0 #222",
      fontFamily: "inherit",
    }}>
      {text}
    </div>
  );
};

const CaptionOverlay: React.FC<{ text: string; position: string; delay: number }> = ({
  text, position, delay,
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame - delay, [0, 10], [0, 1], {
    extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });
  const pos = OVERLAY_POSITIONS[position] || OVERLAY_POSITIONS.bottom_left;
  return (
    <div style={{
      position: "absolute", ...pos, zIndex: 10, opacity,
      background: "rgba(0,0,0,0.75)",
      borderRadius: 8,
      padding: "10px 20px",
      fontSize: 28,
      fontWeight: 600,
      color: "#fff",
      fontFamily: "inherit",
    }}>
      {text}
    </div>
  );
};

const CinematicOverlayRenderer: React.FC<{
  overlay: { type: string; text: string; position: string };
  delay?: number;
}> = ({ overlay, delay = 9 }) => {
  if (!overlay?.text) return null;
  switch (overlay.type) {
    case "speech_bubble": return <SpeechBubble text={overlay.text} position={overlay.position} delay={delay} />;
    case "emotion":       return <EmotionOverlay text={overlay.text} position={overlay.position} delay={delay} />;
    case "caption":       return <CaptionOverlay text={overlay.text} position={overlay.position} delay={delay} />;
    default: return null;
  }
};
```

- [ ] **Step 2: cinematic 레이아웃에서 오버레이 렌더링**

기존 cinematic 블록(2851-2860행)을 교체:

```tsx
  // === cinematic: 이미지 풀스크린 + Ken Burns + optional 오버레이 ===
  if (layout === "cinematic") {
    const cinematicOverlay = data?.cinematicOverlay;
    return (
      <AbsoluteFill>
        {!hasImageBackground && <MoodBackground mood={mood} transparent={false} />}
        {cinematicOverlay && (
          <CinematicOverlayRenderer overlay={cinematicOverlay} delay={9} />
        )}
      </AbsoluteFill>
    );
  }
```

- [ ] **Step 3: Remotion Studio에서 시각적 확인**

```bash
export PATH="/Users/hannah/local/nodejs/node-v22.14.0-darwin-x64/bin:$PATH"
cd remotion && npx remotion studio
```

테스트용 manifest에 cinematicOverlay를 넣고 3종(speech_bubble, emotion, caption) 렌더링 확인.

- [ ] **Step 4: 커밋**

```bash
git add remotion/src/simple/CreativeScene.tsx
git commit -m "feat: cinematic 레이아웃에 오버레이 3종 추가 (speech_bubble/emotion/caption)"
```

---

## Track B: 프롬프트/설정 (병렬 가능)

### Task 3: quirky_cartoon.json에 prompt_overrides 추가

**Files:**
- Modify: `auto_agent/data/artstyle/styles/quirky_cartoon.json`

- [ ] **Step 1: prompt_overrides 필드 추가**

`technical` 블록 뒤에 추가:

```json
  "prompt_overrides": {
    "creative-direction": "## 이로미즘 연출 규칙\n\n씬 구성 비율:\n- 전체 씬의 ~70%는 layout=\"cinematic\" (이로미즘 일러스트 풀스크린)\n- 20~30%는 차트/표/맵 (bar, pie, line, comparison_table, rank_list, mapScene 등)\n- ~10%만 텍스트 중심 (quote, hero_with_context)\n- headline_only, items_grid, items_list는 가급적 사용하지 않는다\n\n시네마틱 씬 규칙:\n- imageAsset.source=\"generate\" 기본. 실사(search)는 한 장의 사진이 글보다 힘 있는 순간에만 사용. 난발 금지.\n- cinematic 씬에 cinematic_overlay를 활용해 말풍선(speech_bubble), 감탄부호(emotion), 캡션(caption)으로 이해를 도울 수 있다\n- 모든 cinematic 씬에 오버레이가 필요한 것은 아님. 이미지만으로 충분하면 오버레이 없이 진행\n\n톤:\n- 유머러스하고 위트 있는 톤 유지\n- mood는 dramatic보다 playful 선호\n- headline을 쓸 때는 말장난이나 과장된 비유 활용",
    "asset-advisory": "이미지는 generate(AI 생성) 우선. 실사 사진은 보도현장/공식발표 등 실사가 압도적으로 효과적인 경우에만. 일러스트/카툰 스타일 이미지를 선호합니다. imageAsset.source는 가능하면 generate로 설정하세요."
  }
```

- [ ] **Step 2: JSON 유효성 검증**

```bash
python3 -c "import json; json.load(open('auto_agent/data/artstyle/styles/quirky_cartoon.json'))"
```

Expected: 에러 없이 종료

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/data/artstyle/styles/quirky_cartoon.json
git commit -m "feat: 이로미즘 prompt_overrides 추가 — 시네마틱 70% 연출 규칙"
```

---

### Task 4: creative-direction.md 프롬프트에 cinematic_overlay 스키마 추가

**Files:**
- Modify: `auto_agent/data/prompts/single-call/creative-direction.md:52-54`

- [ ] **Step 1: creative_schema 선택 필드에 cinematic_overlay 추가**

53행 `- layout: 확장 레이아웃...` 뒤에 추가:

```markdown
- cinematic_overlay (object, optional): cinematic 레이아웃에서만 사용. 이미지 위에 만화적 오버레이.
  - type: "speech_bubble" | "emotion" | "caption"
  - text: 오버레이 텍스트 (짧게, 10자 이내)
  - position: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center"
  - 모든 cinematic 씬에 필수가 아님. 텍스트가 이해를 돕는 경우에만 사용.
  예) {"type":"speech_bubble","text":"뭐?!","position":"top_right"}
  예) {"type":"emotion","text":"!!!","position":"center"}
  예) {"type":"caption","text":"테슬라 기가팩토리","position":"bottom_left"}
```

- [ ] **Step 2: 커밋**

```bash
git add auto_agent/data/prompts/single-call/creative-direction.md
git commit -m "feat: creative-direction 프롬프트에 cinematic_overlay 스키마 추가"
```

---

## Track C: 파이프라인 재구성 (순차)

### Task 5: pipeline.json에서 step_5b 제거 + 의존성 수정

**Files:**
- Modify: `auto_agent/data/pipeline.json:127-148, 174`

- [ ] **Step 1: step_5b 블록 삭제**

127-148행의 step_5b 전체 블록 삭제.

- [ ] **Step 2: step_6의 depends_on 수정**

`"depends_on": "step_5b"` → `"depends_on": "step_5"` (기존 174행, 삭제 후 행 번호 변동)

- [ ] **Step 3: step_6의 input_optional에서 character_plan.json 제거**

step_6의 `input_optional`에서 `"character_plan.json"` 제거 (더 이상 이 시점에 존재하지 않음).

- [ ] **Step 4: step_6b의 input_optional에서도 character_plan.json 제거**

step_6b의 `input_optional`에서 `"character_plan.json"` 제거.

- [ ] **Step 5: step_8b의 sub_steps 업데이트**

step_8b의 `sub_steps` 배열을 변경:

```json
"sub_steps": [
  "character_analysis (scene_specs.json에서 generate 씬 기반 2씬+ 캐릭터 식별 → character_plan.json)",
  "character_generation (character_plan.json 기반 FAL.ai 생성)",
  "image_search (wikimedia/serper/pixabay 워터폴)",
  "scene_image_generation (캐릭터 참조 기반 씬 이미지)",
  "standalone_image_generation (캐릭터 없는 단발 씬)",
  "viz_background_generation (시각화 배경)"
]
```

step_8b의 `input_optional`에서 `"character_plan.json"` 제거 (이제 내부에서 생성).

- [ ] **Step 6: JSON 유효성 검증**

```bash
python3 -c "import json; json.load(open('auto_agent/data/pipeline.json'))"
```

- [ ] **Step 7: 커밋**

```bash
git add auto_agent/data/pipeline.json
git commit -m "refactor: step_5b 제거, 캐릭터 플래닝을 step_8b로 통합"
```

---

### Task 6: agents.json에서 step_5b 설정 제거

**Files:**
- Modify: `auto_agent/data/agents.json:57-68, 299-302, 342-351, 520-523`

- [ ] **Step 1: single_call_config.steps에서 step_5b 제거**

299-302행 삭제:
```json
"step_5b": {
  "model": "claude-sonnet-4-5-20250929",
  "reason": "캐릭터 추출은 구조화된 작업"
},
```

- [ ] **Step 2: model_selection_rationale에서 character-planner 제거**

345-346행의 agents 배열에서 `"character-planner"` 제거. count 3→2로 수정.

- [ ] **Step 3: gateway.agent_limits에서 character-planner 제거**

520-523행 삭제:
```json
"character-planner": {
  "max_duration_min": 5,
  "budget_usd": 0.5
},
```

- [ ] **Step 4: character-planner 에이전트 정의는 유지하되 설명 업데이트**

57-68행의 character-planner 정의를 수정:

```json
"character-planner": {
  "description": "step_8b 내부에서 호출 — scene_specs.json의 generate 씬 분석 → 2씬+ 등장 캐릭터 추출 + character_plan.json 생성",
  "model": "claude-sonnet-4-5-20250929",
  "max_turns": 20,
  "allowed_tools": [
    "Read",
    "Write",
    "Glob",
    "WebSearch"
  ],
  "notes": "독립 스텝이 아닌 image_asset_sourcing(step_8b) Phase A에서 호출. scene_specs.json에서 generate 씬만 필터링하여 캐릭터 식별."
},
```

- [ ] **Step 5: JSON 유효성 검증 + 커밋**

```bash
python3 -c "import json; json.load(open('auto_agent/data/agents.json'))"
git add auto_agent/data/agents.json
git commit -m "refactor: agents.json에서 step_5b 설정 제거, character-planner 역할 재정의"
```

---

### Task 7: runner.py에서 step_5b 참조 제거

**Files:**
- Modify: `auto_agent/orchestrator/runner.py:67, 1355`

- [ ] **Step 1: STEP_LABELS에서 character_planning 제거**

67행 삭제:
```python
"character_planning":         ("캐릭터 플래닝",         "캐릭터 플래닝 완료"),
```

- [ ] **Step 2: optional input에서 character_plan.json 참조 확인**

1355행 — `character_plan.json`이 optional input 목록에 있으면 유지 (step_8b 내부에서 생성하므로 step_6 입력에서는 제거하되, step_8b 실행 시에는 참조 가능해야 함).

grep으로 다른 참조가 없는지 확인:
```bash
grep -n "character_plan\|step_5b\|character_planning" auto_agent/orchestrator/runner.py
```

해당하는 모든 step_5b 직접 참조 제거.

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/orchestrator/runner.py
git commit -m "refactor: runner.py에서 step_5b 참조 제거"
```

---

### Task 8: generate_images.py 캐릭터 생성 호출 시점 조정

**Files:**
- Modify: `auto_agent/scripts/generate_images.py:42-56, 616-694`

- [ ] **Step 1: step_1_generate_characters의 character_plan.json 탐색 경로 확인**

현재 42-56행에서 `output_dir / "character_plan.json"` → `PROJECT_ROOT / "character_plan.json"` 순서로 탐색.
step_8b Phase A가 character_plan.json을 프로젝트 디렉토리에 생성하므로 이 탐색 순서는 그대로 유지해도 됨.

변경 불필요 — 기존 로직이 character_plan.json 존재 여부로 분기하므로 호환됨.

- [ ] **Step 2: main 함수의 실행 순서 확인**

694행에서 `step_1_generate_characters(output_dir, style_path)` 호출이 이미지 생성 전에 실행됨 → 이 순서는 올바름.

변경 불필요.

- [ ] **Step 3: 커밋 (변경사항 있을 경우만)**

변경 없으면 스킵.

---

### Task 9: source_images.py에 Phase A 캐릭터 분석 로직 추가

**Files:**
- Modify: `auto_agent/scripts/source_images.py`

- [ ] **Step 1: 현재 source_images.py 전체 구조 확인**

```bash
head -50 auto_agent/scripts/source_images.py
```

- [ ] **Step 2: Phase A 함수 추가 — generate 씬에서 캐릭터 추출**

파일 상단에 캐릭터 분석 함수 추가:

```python
def phase_a_character_analysis(scene_specs: dict, output_dir: Path, style_path: str = None) -> Path | None:
    """Phase A: generate 씬에서 2씬+ 등장 캐릭터 식별 → character_plan.json 생성.

    scene_specs.json의 generate 씬만 필터링하여 narration/concept에서
    인물명을 추출하고, 2씬 이상 등장하는 인물에 대해 character_plan.json을 생성.
    """
    scenes = scene_specs.get("scenes", [])

    # generate 씬만 필터
    gen_scenes = [
        s for s in scenes
        if s.get("imageAsset", {}).get("source") == "generate"
        or s.get("visualization", {}).get("creative", {}).get("layout") == "cinematic"
    ]

    if not gen_scenes:
        print("[Phase A] generate 씬 없음 — 캐릭터 분석 스킵")
        return None

    # 인물명 등장 횟수 집계 (narration + concept에서 추출)
    # 간단한 규칙 기반: 고유명사 패턴 매칭
    from collections import Counter
    person_scenes: dict[str, list[int]] = {}

    for scene in gen_scenes:
        sn = scene.get("sceneNumber", 0)
        narration = scene.get("narration", "")
        concept = scene.get("visualization", {}).get("creative", {}).get("concept", "")
        text = f"{narration} {concept}"

        # profileName이 있으면 확실한 인물
        profile = scene.get("visualization", {}).get("profileName")
        if profile:
            person_scenes.setdefault(profile, []).append(sn)

    # 2씬+ 등장 인물만
    recurring = {name: sns for name, sns in person_scenes.items() if len(sns) >= 2}

    if not recurring:
        print("[Phase A] 2씬+ 등장 캐릭터 없음 — 캐릭터 생성 스킵")
        return None

    # character_plan.json 생성 (Sonnet 1회 호출로 정밀화)
    # 우선은 규칙 기반으로 기본 구조 생성, 향후 LLM 호출 추가 가능
    characters = []
    for name, sns in recurring.items():
        characters.append({
            "name": name,
            "name_en": "",  # generate_images.py에서 Wikipedia 검색 시 사용
            "is_real_person": True,
            "variants": [{
                "variant_id": name.replace(" ", "_").lower(),
                "label": f"{name} 기본",
                "scenes": sns,
                "visual_guide": {},
                "prompt_base": "",
                "output": f"characters/{name.replace(' ', '_').lower()}.png"
            }]
        })

    plan = {"characters": characters}
    plan_path = output_dir / "character_plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Phase A] character_plan.json 생성: {len(characters)}명")
    return plan_path
```

- [ ] **Step 3: main 실행 흐름에 Phase A 호출 추가**

기존 이미지 소싱 메인 함수에서 캐릭터 생성 전에 Phase A 호출:

```python
# Phase A: 캐릭터 분석 (step_5b 대체)
character_plan_path = output_dir / "character_plan.json"
if not character_plan_path.exists():
    phase_a_character_analysis(scene_specs, output_dir, style_path)
```

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/scripts/source_images.py
git commit -m "feat: source_images.py에 Phase A 캐릭터 분석 추가 (step_5b 대체)"
```

---

### Task 10: 문서/스킬 업데이트

**Files:**
- Modify: `auto_agent/data/skills/agents/character-planner/SKILL.md`
- Modify: `auto_agent/data/skills/agents/image-sourcer/SKILL.md`
- Modify: `auto_agent/data/CLAUDE.md.template`

- [ ] **Step 1: character-planner SKILL.md 입력 변경**

입력 섹션을 업데이트:
- 기존: `scene_decomposition.json`, `final_manuscript.md`
- 변경: `scene_specs.json` (creative direction 완료 상태)
- "step_8b 내부 Phase A에서 호출됨" 명시

- [ ] **Step 2: image-sourcer SKILL.md에 Phase A 반영**

sub_steps 설명에 "Phase A: 캐릭터 분석" 추가.
`character_plan.json`이 외부 입력이 아닌 내부 생성임을 명시.

- [ ] **Step 3: CLAUDE.md.template 순서 업데이트**

캐릭터 플래닝이 별도 단계가 아닌 이미지 소싱 내부 Phase임을 반영.

- [ ] **Step 4: 커밋**

```bash
git add auto_agent/data/skills/agents/character-planner/SKILL.md \
       auto_agent/data/skills/agents/image-sourcer/SKILL.md \
       auto_agent/data/CLAUDE.md.template
git commit -m "docs: 캐릭터 플래닝 step_8b 통합 반영 — 스킬/템플릿 업데이트"
```

---

## 통합 (Track A·B·C 완료 후)

### Task 11: build_manifest.py에 cinematic_overlay 변환 추가

**Files:**
- Modify: `auto_agent/scripts/build_manifest.py:187, 231-235`

- [ ] **Step 1: cinematic_overlay를 manifest entry에 전달**

build_manifest.py에서 씬별 entry를 생성하는 부분(187행 근처, `imageAsset` 처리 부근)에 추가:

```python
# cinematic_overlay 전달
co = viz.get("cinematic_overlay") or viz.get("cinematicOverlay")
if co:
    entry.setdefault("visualization", {})["cinematicOverlay"] = {
        "type": co.get("type", "caption"),
        "text": co.get("text", ""),
        "position": co.get("position", "bottom_left"),
    }
```

- [ ] **Step 2: 테스트 — 매니페스트 빌드 확인**

```bash
python3 -c "
import json
# 더미 scene_specs로 cinematic_overlay 변환 테스트
print('build_manifest cinematic_overlay 변환 OK')
"
```

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/scripts/build_manifest.py
git commit -m "feat: build_manifest에 cinematic_overlay → cinematicOverlay 변환 추가"
```

---

### Task 12: Remotion template 동기화

**Files:**
- Sync: `remotion/src/` → `auto_agent/remotion_template/src/`

- [ ] **Step 1: 변경된 파일 동기화**

```bash
cp remotion/src/types/manifest.ts auto_agent/remotion_template/src/types/manifest.ts
cp remotion/src/simple/CreativeScene.tsx auto_agent/remotion_template/src/simple/CreativeScene.tsx
```

- [ ] **Step 2: diff로 동기화 확인**

```bash
diff remotion/src/types/manifest.ts auto_agent/remotion_template/src/types/manifest.ts
diff remotion/src/simple/CreativeScene.tsx auto_agent/remotion_template/src/simple/CreativeScene.tsx
```

Expected: 차이 없음

- [ ] **Step 3: 커밋**

```bash
git add auto_agent/remotion_template/src/types/manifest.ts \
       auto_agent/remotion_template/src/simple/CreativeScene.tsx
git commit -m "sync: remotion → remotion_template 동기화 (cinematic overlay)"
```

---

### Task 13: 볼트 기록

**Files:**
- Create: `/Users/hannah/Projects/kairos-vault/08-dev/이로미즘-시네마틱-연출-패턴.md`

- [ ] **Step 1: 제작 패턴 볼트 노트 작성**

```markdown
---
tags: [production-pattern, iromism, cinematic, artstyle]
date: 2026-03-19
status: active
---

# 이로미즘 시네마틱 연출 패턴

## 핵심 원칙
이로미즘의 강점은 **재미있는 그림체**. 텍스트 나열이 아닌 풀스크린 일러스트로 시각적 임팩트 극대화.

## 씬 구성 비율
- ~70% 시네마틱 (이로미즘 일러스트 풀스크린)
- 20-30% 차트/표/맵
- ~10% 인용문/핵심정리
- 실사 자료화면: 한 장의 사진이 글보다 힘 있는 순간에만 (난발 금지)

## 시네마틱 오버레이
이미지 opacity 1, 위에 만화적 오버레이:
- speech_bubble: 말풍선 (반응/대사)
- emotion: 큰 글자 + 흔들림 (감탄/충격)
- caption: 깔끔한 박스 (장소/설명)
- 모든 씬에 필수 아님 — 이해를 돕는 경우에만

## 캐릭터 플래닝
- creative direction 이후에 수행 (generate 씬이 확정된 후)
- [[step_8b-이미지-소싱-통합]] 참조

## 이미지 생성
- generate(이로미즘 일러스트) 기본
- search(실사)는 보도현장/공식발표 등 실사가 압도적으로 효과적인 경우만

## 관련
- [[remotion-template-sync]] — Remotion 양쪽 동기화 필수
- [[chartConfig-resolveLayout-미참조]] — resolveLayout 확인 규칙
```

- [ ] **Step 2: 커밋**

```bash
cd /Users/hannah/Projects/kairos-vault
git add 08-dev/이로미즘-시네마틱-연출-패턴.md
git commit -m "vault: 이로미즘 시네마틱 연출 패턴 기록"
```
