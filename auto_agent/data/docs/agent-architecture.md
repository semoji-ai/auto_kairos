# Auto Agent V2 - 에이전트 팀 아키텍처

> **v3.0** — 에이전트/스킬 분리 재구조화 반영 (11→6 LLM 에이전트 + 8 공유 스킬)

## 설계 철학: "Simple is Best"

> AI 이미지 생성에 의존하지 않고, **Remotion의 프로그래밍 렌더링 능력을 최대한 활용**하여
> 아이콘 + 타이포그래피 + 데이터 시각화 + 모션으로 깔끔한 정보 전달 영상을 제작한다.

### 핵심 원칙

1. **Remotion-First**: 모든 씬을 React 컴포넌트로 렌더링. 이미지 생성은 최후의 수단
2. **Icon-Driven**: Lucide React 아이콘으로 개념을 시각화. 일러스트레이션 대체
3. **제한된 컬러**: 씬당 최대 2-3색. 테마 팔레트에서 primary + accent + neutral만 사용
4. **여백의 미**: padding 32px+, 한 씬에 하나의 핵심 정보만. 과적 금지
5. **미묘한 모션**: spring(damping: 200) 기반. 바운스 없이 부드럽고 자연스러운 움직임
6. **데이터로 말하기**: 수치/통계는 반드시 시각화 컴포넌트로 표현

---

## 전체 아키텍처

```
                    ┌───────────────────────┐
                    │   Gateway (haiku)     │
                    │   에이전트 감시/복구    │
                    │   무한루프 탐지+재시작  │
                    └───────────┬───────────┘
                                │ 모니터링
┌───────────────────────────────▼──────────────────────────────────┐
│                     Pipeline Controller                          │
│                  (Python async 오케스트레이터)                      │
└─────┬──────────┬──────────────┬───────────────┬─────────────────┘
      │          │              │               │
 ┌────▼────┐ ┌──▼──────┐ ┌────▼──────────┐ ┌──▼──────────────┐
 │리서치 (A)│ │원고 (B)  │ │씬 설계 (C)    │ │에셋+조립 (D)    │
 │ 1 agent │ │ 1 agent │ │ 2 agent       │ │ 5 module       │
 │ +2 모듈  │ │         │ │ Remotion-First │ │ 스킬 기반      │
 └─────────┘ └─────────┘ └───────────────┘ └────────────────┘

총 15개 (LLM 서브에이전트 6 + Gateway 1 + API/프로그래밍 모듈 8)
```

---

## 에이전트 vs 스킬 아키텍처

### 설계 원칙

- **에이전트**: 자율적 판단, 외부 도구 사용, 창작/분석이 필요한 전문가
- **공유 스킬**: 재사용 가능한 업무 매뉴얼. 여러 에이전트가 참조하는 고정 규칙

### 공유 스킬 참조 매핑

```
shared/remotion-design-system ──→ visual-composer, qa-reviewer
shared/scene-types ─────────────→ visual-composer, write-manuscript, qa-reviewer
shared/writing-style ───────────→ write-manuscript, qa-reviewer
shared/motion-rhythm ───────────→ visual-composer, qa-reviewer
shared/korean-tts-rules ────────→ tts-preprocess 모듈
shared/data-mapping ────────────→ visual-composer, qa-reviewer
shared/research-format ─────────→ research-orchestrator
shared/outline-template ────────→ write-manuscript
```

---

## Gateway Agent (haiku) — 에이전트 감시/복구 시스템

> **모든 서브에이전트의 실행 상태를 실시간 감시**하여,
> 무한 사고(infinite thinking), stuck, 무한 루프 상태에 빠진 에이전트를 탐지하고
> 강제 종료 → 재시작 → 역할 재배정까지 자동으로 수행합니다.

### 왜 Haiku인가

| 기준 | 이유 |
|------|------|
| **비용** | Gateway는 파이프라인 전체에 걸쳐 상시 실행. opus/sonnet 대비 10-20x 저렴 |
| **속도** | 상태 점검은 빠른 판단만 필요. Haiku의 저지연이 최적 |
| **역할** | 창작/분석이 아닌 **패턴 매칭 + 규칙 기반 판단**. 고성능 모델 불필요 |

### 감시 대상 및 탐지 패턴

```
Gateway Agent (haiku, 상시 실행)
│
├─ 감시 대상: 모든 LLM 서브에이전트 (6개)
│
├─ 탐지 패턴:
│   │
│   ├─ 1. 시간 초과 (Timeout)
│   │   └─ 에이전트별 max_duration 초과 시 stuck 판정
│   │
│   ├─ 2. 무한 출력 루프 (Repetition)
│   │   └─ 최근 N턴의 출력을 비교하여 반복 패턴 탐지
│   │      ├─ 동일 텍스트 3회 이상 반복
│   │      ├─ 동일 도구 호출 5회 이상 연속
│   │      └─ 출력 없이 도구만 반복 호출
│   │
│   ├─ 3. 토큰 폭주 (Token Explosion)
│   │   └─ 단일 턴에서 비정상적 토큰 소비 감지
│   │      ├─ 입력 토큰 > 100K (컨텍스트 과적재)
│   │      └─ 누적 비용 > 에이전트별 budget 초과
│   │
│   ├─ 4. 무응답 (No Progress)
│   │   └─ 마지막 출력 이후 2분간 새 출력 없음
│   │
│   └─ 5. 오류 반복 (Error Loop)
│       └─ 동일 오류 메시지 3회 이상 발생
│
└─ 복구 액션:
    │
    ├─ Level 1: 경고 로깅
    │   └─ pipeline_state.json에 warning 기록
    │
    ├─ Level 2: 강제 종료 + 재시작
    │   ├─ 현재 에이전트 프로세스 kill
    │   ├─ 동일 프롬프트로 새 에이전트 시작
    │   └─ 재시작 횟수 기록 (max 2회)
    │
    ├─ Level 3: 프롬프트 축소 재시작
    │   ├─ 입력 데이터를 요약/축소하여 재시도
    │   ├─ 예: 원고 전문 대신 챕터별 분할 투입
    │   └─ max_turns 50% 감소
    │
    └─ Level 4: 스킵 + 알림
        ├─ 해당 step을 "skipped_by_gateway"로 표기
        ├─ 사용자에게 알림 (어떤 에이전트가 왜 실패했는지)
        └─ 후속 step에서 누락 데이터 대체 처리
```

### Gateway 실행 방식

```python
# Gateway는 Pipeline Controller와 별도 코루틴으로 상시 실행
async def gateway_monitor(pipeline_state, active_agents):
    """
    2초 간격으로 모든 활성 에이전트 상태 점검.
    Haiku에게 판단을 위임하는 것은 복잡한 케이스만.
    단순 timeout/반복은 Python 로직으로 직접 처리.
    """
    while pipeline_running:
        for agent_id, agent_info in active_agents.items():
            # 1차: Python 규칙 기반 점검 (빠름, 비용 0)
            if check_timeout(agent_info):
                await handle_stuck(agent_id, reason="timeout")
            elif check_repetition(agent_info):
                await handle_stuck(agent_id, reason="repetition")
            elif check_token_explosion(agent_info):
                await handle_stuck(agent_id, reason="token_explosion")

            # 2차: 애매한 케이스만 Haiku에게 판단 위임
            elif check_ambiguous(agent_info):
                verdict = await ask_haiku_gateway(agent_info)
                if verdict == "stuck":
                    await handle_stuck(agent_id, reason=verdict.detail)

        await asyncio.sleep(2)  # 2초 간격 폴링
```

### 에이전트별 감시 설정

| 에이전트 | max_duration | max_turns | budget | 재시작 전략 |
|---------|-------------|-----------|--------|-----------|
| Research Orchestrator | 20분 | 70 | $2.5 | 프롬프트 축소 |
| Write Manuscript | 15분 | 60 | $2.5 | 챕터별 분할 재시작 |
| Visual Composer | 20분 | 60 | $3.0 | 씬 범위 축소 |
| Character Planner | 8분 | 20 | $0.5 | 재시작 |
| Fact Verifier | 5분 | 20 | $0.5 | 스킵 가능 |
| QA Reviewer | 5분 | 25 | $0.5 | 재시작 |

---

### v1(auto_semoji) 대비 핵심 변화

| 영역 | v1 (auto_semoji) | v2→v3 (auto_agent_v2) |
|------|-----------------|-------------------|
| **씬 렌더링** | AI 이미지 + Ken Burns | Remotion 컴포넌트 코드 렌더링 |
| **시각 요소** | 생성 이미지 중심 | 아이콘 + 타이포 + 차트 중심 |
| **에이전트 수** | 25개 | 15개 (LLM 6 + Gateway 1 + 모듈 8) |
| **이미지 생성** | 필수 (모든 씬) | 선택 (스킬로 필요시만) |
| **디자인** | 테마별 다양 | "Simple is Best" 단일 철학 |
| **컬러** | 테마당 10색 팔레트 | 씬당 2-3색 제한 |
| **스킬 구조** | 에이전트 1:1 전용 | 공유 스킬 다대다 |

---

## Team A: 리서치팀 (1 에이전트 + 2 모듈)

deep-research-kit(설치 완료)으로 7단계 심층 리서치 + Light 모드 3단계 빠른 리서치 지원.
Research Synthesizer를 Research Orchestrator에 통합 (리서치 + 합성 = 1 에이전트).

| # | 구성 요소 | 역할 | 타입 | 모델 |
|---|----------|------|------|------|
| A1 | **Research Orchestrator** | deep-research 실행 + research_report.json 합성 | LLM 에이전트 | `opus-4-6` |
| A2 | **Explorer Agent** (xN) | Phase 3 병렬 웹 검색 | 모듈 (deep-research 내장) | `sonnet-4-5` |
| A3 | **Librarian Agent** | 소스 분류/등급 평가 (A-E) | 모듈 (deep-research 내장) | `sonnet-4-5` |

> Explorer/Librarian은 deep-research-kit 내장 에이전트로, Research Orchestrator가 직접 조율합니다.

### Research Orchestrator 통합 흐름

```
Phase 1: deep-research 실행
  ├─ Explorer Agent (병렬 웹 검색)
  ├─ Librarian Agent (소스 분류)
  └─ RESEARCH/{topic}_{timestamp}/ 생성

Phase 2: 합성 (기존 Research Synthesizer 흡수)
  ├─ outputs/ 읽기
  ├─ sources.jsonl 파싱
  └─ research_report.json 생성 (shared/research-format 규칙 참조)
```

---

## Team B: 원고팀 (1 에이전트 + 1 모듈)

Outline Builder를 Write Manuscript에 통합 (아웃라인 + 원고 = 1 에이전트).

| # | 구성 요소 | 역할 | 타입 | 모델 |
|---|----------|------|------|------|
| B1 | **Write Manuscript** | 3막 구조 아웃라인 설계 + 원고 작성 | LLM 에이전트 | `opus-4-6` |
| B2 | **Duplicate Checker** | N-gram 중복 감지 | Python 모듈 | — |

### Write Manuscript 통합 흐름

```
Phase 1: 아웃라인 설계 (기존 Outline Builder 흡수)
  ├─ research_report.json → 3막 구조 분석
  ├─ shared/outline-template 규칙 참조
  └─ outline.json 생성

Phase 2: 원고 작성
  ├─ outline.json → 챕터별 원고 작성
  ├─ shared/writing-style 문체 규칙 참조
  ├─ shared/scene-types 씬 타입별 글자 수 제한 참조
  └─ final_manuscript.md 생성
```

---

## Team C: 씬 설계팀 (2 에이전트) — 핵심 재설계

Scene Decomposer, Data Enricher, Motion Choreographer를 Visual Composer에 통합.
Character Planner는 독립 유지 (실존 인물 WebSearch 필요).

| # | 에이전트 | 역할 | 모델 |
|---|---------|------|------|
| C1 | **Character Planner** | 원고 기반 캐릭터 추출 + 변이 분석 | `sonnet-4-5` |
| C2 | **Visual Composer** | 씬 분할 → 시각 구성 → 데이터 보강 → 모션 설계 (4-in-1) | `opus-4-6` |

### Visual Composer 4-in-1 흐름

```
Phase 1: 씬 분할 (기존 Scene Decomposer 흡수)
  ├─ final_manuscript.md → 씬 단위 분할
  ├─ 씬 타입 배정 (shared/scene-types 참조)
  └─ scene_decomposition.json 생성

Phase 2: 시각 구성 (기존 핵심 역할)
  ├─ 컬러/아이콘/레이아웃 결정
  ├─ shared/remotion-design-system 규칙 참조
  └─ scene_specs.json 생성

Phase 3: 데이터 보강 (기존 Data Enricher 흡수)
  ├─ 시각화 수치 ↔ research_report.json 대조
  ├─ shared/data-mapping 규칙 참조
  └─ scene_specs.json 업데이트

Phase 4: 모션 설계 (기존 Motion Choreographer 흡수)
  ├─ 전환 패턴, 타이밍, 리듬 설계
  ├─ shared/motion-rhythm 규칙 참조
  └─ motion_plan.json 생성
```

### Character Planner

```
입력: final_manuscript.md + research_report.json + art_style.json
  ├─ ## Scene N: 구조에서 인물명 추출
  ├─ 2씬 이상 등장 캐릭터 → 변이 분석
  ├─ 실존 인물 → WebSearch로 참조 사진 검색
  └─ character_plan.json 생성
```

---

## Team D: 에셋 생산 + 조립팀 (모듈 기반)

이미지 생성, TTS, 자막, 검증, 렌더링을 **독립 모듈**로 운영합니다.
TTS Preprocessor는 LLM 에이전트에서 Python 모듈로 전환 (규칙 기반, LLM 불필요).

| # | 모듈 | 역할 | 기술 | 타입 |
|---|------|------|------|------|
| D1 | **TTS Preprocessor** | 한국어 TTS 전처리 (발음 교정, 숫자 변환) | Python 스크립트 | 모듈 |
| D2 | **TTS Generator** | 씬별 나레이션 음성 생성 | ElevenLabs / Gemini TTS | API 모듈 |
| D3 | **Subtitle Sync** | Whisper 기반 단어 레벨 타임스탬프 | OpenAI Whisper | API 모듈 |
| D4 | **Image Generator** | image_scene 타입 씬용 이미지 생성/검색 | Gemini Image / Serper | API 모듈 |
| D5 | **Data Validator** | 전 단계 데이터 정합성 검증 | Python | 모듈 |
| D6 | **Video Assembler** | Remotion manifest 생성 + 최종 렌더링 | Remotion CLI | 모듈 |

### D4: Image Generator — 전략적 에셋

**기본 레이어**(아이콘 + 타이포 + 차트 + 모션)로 정보를 전달하되,
**이미지 에셋을 전략적으로 배치**하여 정보 전달을 극대화합니다.

#### 이미지 배치 판단 기준 (Visual Composer Phase 1에서 결정)

| 상황 | Remotion 컴포넌트 | + 이미지 에셋 |
|------|-----------------|-------------|
| 통계/수치 전달 | bar_chart, line_chart | 불필요 |
| 개념 설명 | icon_grid, icon_flow | 불필요 |
| 핵심 인물 소개 | quote_card | + 인물 사진 (신뢰감 ↑) |
| 제품/기술 소개 | list_card | + 스크린샷/제품 이미지 (구체성 ↑) |
| 역사적 사건 | timeline | + 당시 사진 (맥락 ↑) |
| 챕터 전환 | title_card | + 대표 이미지 (분위기 전환 ↑) |
| 비교 분석 | compare_card | + 좌우 제품 이미지 (직관성 ↑) |
| 흐름/프로세스 | icon_flow, diagram | 불필요 |

#### 이미지 에셋 소싱 전략 (우선순위)

```
1순위: wikimedia (저작권 프리, 최우선)
2순위: search (웹 검색 보완)
3순위: generate (AI 생성, 최후 수단)
4순위: reference (로컬 에셋)
```

#### 예상 비율

```
전체 30-50씬 중:
  ├─ 순수 Remotion 컴포넌트: 70% (아이콘+차트+텍스트)
  ├─ Remotion + 이미지 에셋: 20% (컴포넌트 + 보조 이미지)
  └─ 이미지 중심: 10% (인물, 제품 클로즈업)
```

---

## QA Reviewer — 결과물 품질 검수 시스템

> 파이프라인 산출물의 **품질을 체계적으로 검증**하여,
> 렌더링 전 사전 검수와 렌더링 후 사후 검수를 통해 최종 영상 품질을 보장합니다.
>
> 검증 기준은 공유 스킬 참조: `remotion-design-system`, `writing-style`, `scene-types`, `motion-rhythm`, `data-mapping`

| 에이전트 | 모델 | 실행 시점 |
|---------|------|---------|
| QA Reviewer | `sonnet-4-5` | Phase 5 내 2회 (사전/사후) |

### 2단계 검수 프로세스

```
1차 검수: 사전 검수 (Pre-render QA)
     │  manifest.json 생성 직후, 렌더링 전
     │
     │  검증 항목:
     │  ├─ 씬 스펙 완전성 (shared/scene-types 참조)
     │  ├─ 아이콘명 유효성 (shared/remotion-design-system 참조)
     │  ├─ 컬러 규칙 (shared/remotion-design-system 참조)
     │  ├─ 데이터 정확도 (shared/data-mapping 참조)
     │  ├─ 나레이션 ↔ 씬 매칭 (shared/writing-style 참조)
     │  ├─ 자막 타이밍 정합성
     │  ├─ 이미지 에셋 (해상도, 라이선스, 파일 존재)
     │  └─ 모션 플랜 일관성 (shared/motion-rhythm 참조)
     │
     │  → qa_report_pre.json
     │  → gate: 심각도 "critical" 있으면 렌더링 차단
     │
     ▼
렌더링 (Video Assembler)
     │
     ▼
2차 검수: 사후 검수 (Post-render QA)
     │
     │  검증 항목:
     │  ├─ 영상 메타데이터 (해상도 1920x1080, fps 30, 코덱)
     │  ├─ 전체 재생 시간 적정성 (예상 vs 실제)
     │  └─ 파일 크기 적정성
     │
     │  → qa_report_post.json
     │  → 문제 발견 시 사용자 알림 + 재렌더링 제안
     │
     ▼
final_video.mp4 (검수 완료)
```

---

## 파이프라인 실행 흐름

```
Phase 0: Preflight
     │  API키, node, Remotion, Lucide 의존성 검증
     │
Phase 1: 리서치 + 원고 (순차)
     │  Step 1:  Research Orchestrator (리서치 + 합성 통합)
     │           → research_report.json
     │  Step 2:  Write Manuscript (아웃라인 + 원고 통합)
     │           → outline.json + final_manuscript.md
     │
Phase 2: 분석 ─── 병렬 그룹 A ──────────────────────
     │  ├─ Step 3a: Duplicate Checker (N-gram 중복)
     │  └─ Step 3b: Fact Verifier (교차 검증, blocking: false)
     │
Phase 3: 씬 설계 (순차)
     │  Step 4:  Character Planner → character_plan.json
     │           (입력: final_manuscript.md)
     │  Step 5:  Visual Composer (4-in-1)
     │           → scene_decomposition.json
     │           → scene_specs.json
     │           → motion_plan.json
     │
Phase 4: 에셋 생산 ─── 병렬 그룹 B ─────────────────
     │  ├─ Step 6a: TTS Preprocessor (모듈) → narration_tts
     │  ├─ Step 6b: TTS Generator → audio/scene_*.mp3
     │  ├─ Step 6c: Image Generator → images/ (3-5개)
     │  ├─ Step 6d: Character Generator → characters/
     │  └─ Step 6e: Subtitle Sync → subtitles/scene_*.srt
     │
Phase 5: 조립 + 검수 (순차)
     │  Step 7:  Data Validator (정합성 검증)
     │  Step 8:  Manifest Builder → remotion/public/manifest.json
     │  Step 9:  QA Reviewer 사전 검수 → qa_report_pre.json [GATE]
     │  Step 10: Video Assembler → final_video.mp4
     │  Step 11: QA Reviewer 사후 검수 → qa_report_post.json
     │
     ▼
final_video.mp4 (검수 완료)
```

---

## 에이전트 간 데이터 계약

### 핵심 데이터 흐름

```
Research Orchestrator
        │
        ▼
research_report.json
        │
        ▼
Write Manuscript
        │
        ├─→ outline.json (내부)
        │
        ▼
final_manuscript.md
        │
        ├─────────────────────┬──────────────────┐
        ▼                     ▼                  ▼
Character Planner      Fact Verifier      Visual Composer
        │                (참고용)          (4-in-1)
        ▼                                    │
character_plan.json              ┌───────────┼───────────┐
        │                        ▼           ▼           ▼
        │              scene_decomp.    scene_specs.  motion_plan.
        │                  json            json         json
        │                                    │
        │                    ┌───────────────┼───────────────┐
        ▼                    ▼               ▼               ▼
Image Generator        TTS Module      Image Generator   Subtitle Sync
(캐릭터 생성)          + TTS Gen       (씬 이미지)
        │                    │               │               │
        └────────┬───────────┴───────────────┘               │
                 ▼                                           │
          Manifest Builder ←─────────────────────────────────┘
                 │
                 ▼
          QA Reviewer (사전) → qa_report_pre.json [GATE]
                 │
                 ▼
          Video Assembler → final_video.mp4
                 │
                 ▼
          QA Reviewer (사후) → qa_report_post.json
```

### 파일 목록

| 파일 | 생성자 | 소비자 | 포맷 |
|------|-------|--------|------|
| `RESEARCH/{topic}/` | Research Orchestrator (Phase 1) | Research Orchestrator (Phase 2) | deep-research-kit 구조 |
| `research_report.json` | Research Orchestrator | Write Manuscript, Visual Composer | JSON |
| `outline.json` | Write Manuscript (Phase 1) | Write Manuscript (Phase 2) | JSON (씬 힌트 포함) |
| `final_manuscript.md` | Write Manuscript (Phase 2) | Fact Verifier, Visual Composer, Character Planner | Markdown |
| `character_plan.json` | Character Planner | Image Generator | JSON |
| `scene_decomposition.json` | Visual Composer (Phase 1) | Visual Composer (Phase 2) | JSON (씬 배열 + 타입) |
| `scene_specs.json` | Visual Composer (Phase 2+3) | TTS Module, TTS Gen, Image Gen, QA Reviewer | JSON (Remotion 렌더링 스펙) |
| `motion_plan.json` | Visual Composer (Phase 4) | Manifest Builder, Video Assembler | JSON (전환/타이밍) |
| `audio/scene_*.mp3` | TTS Generator | Subtitle Sync, Video Assembler | MP3 |
| `subtitles/scene_*.srt` | Subtitle Sync | Video Assembler | SRT |
| `images/scene_*.png` | Image Generator (선택) | Video Assembler | PNG (image_scene만) |
| `manifest.json` | Manifest Builder | Remotion | JSON |
| `final_video.mp4` | Video Assembler | 최종 산출물 | MP4 |

---

## 모델 선택 기준

| 모델 | 기준 | 해당 에이전트 |
|------|------|-------------|
| **opus-4-6** | 창작/전략 판단. 핵심 파이프라인 에이전트 | Research Orchestrator, Write Manuscript, **Visual Composer** |
| **sonnet-4-5** | 분석/처리. 보조 에이전트 | Character Planner, Fact Verifier, **QA Reviewer** |
| **haiku-4-5** | 감시/판단. 상시 실행 | **Gateway** (에이전트 상태 점검, stuck 탐지) |
| **Non-LLM** | 결정론적 작업 | TTS Preprocessor, TTS Generator, Subtitle Sync, Image Generator, Data Validator, Video Assembler, Duplicate Checker, Detail Researcher |

### Visual Composer에 opus를 사용하는 이유

Visual Composer는 **원고의 의미를 시각적 구성으로 번역**하는 창작 작업이며,
v3.0에서 4단계를 통합 수행하여 파이프라인의 핵심 에이전트입니다:
- 추상적 개념 → 구체적 아이콘 매핑
- 텍스트 정보 → 적절한 차트 타입 선택
- 전체 영상의 시각적 통일성 유지
- "Simple is Best" 철학에 맞는 절제된 디자인 판단
- 데이터 정확도 검증 + 모션 리듬 설계까지 일관된 맥락 유지

---

## Remotion 기술 스택

```
@remotion/core              — 핵심 (Composition, Sequence, useCurrentFrame)
@remotion/transitions       — TransitionSeries (fade, slide, wipe)
@remotion/shapes            — SVG 기하학 도형 (circle, rect, star)
@remotion/paths             — SVG 경로 애니메이션 (evolvePath)
@remotion/google-fonts      — 웹 폰트 (Pretendard는 별도 로드)
@remotion/tailwind-v4       — Tailwind CSS v4 통합
@remotion/renderer          — CLI 렌더링
lucide-react                — 1500+ SVG 아이콘
tailwindcss                 — 유틸리티 CSS
```

---

## v2.0 → v3.0 변경 요약

| 항목 | v2.0 | v3.0 |
|------|------|------|
| LLM 에이전트 수 | 11 + gateway | 6 + gateway |
| Opus 호출 | 5회/파이프라인 | 3회 |
| Sonnet 호출 | 6회 | 3회 |
| 스킬 파일 수 | 11 (전용) | 8 (공유) + 6 (에이전트별) |
| 스킬 재사용성 | 0% (1:1) | 다대다 |
| 파이프라인 단계 수 | 16 steps | 11 steps |
| 흡수된 에이전트 | — | research-synthesizer, outline-builder, scene-decomposer, data-enricher, motion-choreographer |
| 모듈로 전환 | — | tts-preprocess (LLM→Python) |
