# 이로미즘 시네마틱 중심 연출 리디자인

> 날짜: 2026-03-19
> 적용 범위: 이로미즘(quirky_cartoon) 전용 + 캐릭터 플래닝 이동(글로벌)

## 배경

현재 이로미즘 스타일은 텍스트 중심 레이아웃(headline, items_grid 등)이 ~70%를 차지하여 "클로드로 만든 전형적인 영상" 느낌이 강함. 이로미즘의 강점인 재미있는 그림체를 살리기 위해 시네마틱(풀스크린 일러스트) 중심으로 전환.

## 변경 사항

### 1. 이로미즘 씬 비율 규칙 (quirky_cartoon만)

| 타입 | 현재 | 변경 |
|------|------|------|
| 시네마틱 (이로미즘 일러스트 풀스크린) | ~0% | **~70%** |
| 차트/표/맵 | ~15% | **20-30%** |
| 텍스트/인용문/핵심정리 | ~70% | **~10%** |
| 실사 자료화면 | 0% | 적합한 경우만 |

**실사 자료화면 규칙**: 기본은 generate(이로미즘 일러스트) 우선. 한 장의 실사가 많은 글과 그림보다 힘 있는 순간에만 search 사용. 난발 금지 — 톤앤매너 유지.

### 2. 시네마틱 오버레이 (quirky_cartoon만, 렌더러는 글로벌)

현재 `cinematic` 레이아웃은 텍스트 없는 순수 이미지만 렌더링. 이로미즘의 만화적 표현을 위해 오버레이 지원 추가.

#### 데이터 위치

```
scene_specs.json:  scenes[].visualization.cinematic_overlay
manifest.json:     scenes[].cinematicOverlay (camelCase 변환)
CreativeScene.tsx:  props.cinematicOverlay
```

- `build_manifest.py`에서 `visualization.cinematic_overlay` → `cinematicOverlay`로 변환
- `remotion/src/types/manifest.ts`에 `CinematicOverlay` 타입 정의 추가

#### 데이터 스키마

```ts
// manifest.ts
interface CinematicOverlay {
  type: "speech_bubble" | "emotion" | "caption";
  text: string;        // 10자 이내
  position: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center";
}
```

#### 오버레이 3종

| type | 형태 | 용도 | 예시 |
|------|------|------|------|
| `speech_bubble` | 만화 말풍선 (흰 배경, 굵은 검정 테두리, 꼬리) | 반응/대사 | "뭐?!", "진짜?" |
| `emotion` | 큰 글자 + shake 애니메이션, 약간 기울어짐 | 감탄/충격 | "!!!", "?!" |
| `caption` | 반투명 검정 박스 + 흰 텍스트 | 장소/설명 | "테슬라 기가팩토리" |

#### 렌더링 규칙
- 이미지는 opacity 1 (반투명 처리 안 함)
- 오버레이는 씬 시작 후 0.3~0.5초에 pop-in 등장
- speech_bubble 꼬리 방향은 position에 따라 자동 결정
- speech_bubble/emotion은 이로미즘 선화 느낌 (굵고 불규칙한 선)

### 3. 캐릭터 플래닝 step_8b 통합 (글로벌)

**문제**: 현재 step_5b(씬 분해 직후)에서 캐릭터를 플래닝하지만, 이 시점에는 어떤 씬이 generate인지 결정 전. 불필요한 캐릭터를 생성하거나, 필요한 캐릭터를 놓칠 수 있음.

**변경**: step_5b 제거 → step_8b(이미지 소싱) 내부에서 일괄 처리.

**주의: 의존성 체인**: step_6의 `depends_on`이 현재 `"step_5b"` → `"step_5"`로 변경 필요.

**Phase A 구현 방식**: source_images.py 내에서 scene_specs.json의 generate 씬을 파싱하여 narration/concept에서 인물명을 규칙 기반으로 추출. 2씬+ 등장 인물에 대해 character_plan.json 생성. 기존 character-planner 에이전트의 LLM 호출 대신 Python 규칙 기반 + 필요시 Sonnet 1회 호출로 경량화.

#### 변경 전

```
step_5:  씬 분해
step_5b: 캐릭터 플래닝 → character_plan.json
step_6:  크리에이티브 디렉션 → scene_specs.json (layout, imageAsset.source 결정)
...
step_8b: 이미지 소싱
         - 캐릭터 생성 (character_plan.json 기반)
         - 이미지 검색/생성
```

#### 변경 후

```
step_5:  씬 분해
step_6:  크리에이티브 디렉션 → scene_specs.json (layout, imageAsset.source 결정)
...
step_8b: 이미지 소싱 (통합)
         Phase A: generate 씬에서 2씬+ 등장 캐릭터 식별 → character_plan.json
         Phase B: 캐릭터 생성 (FAL.ai + 아트스타일 + 인물 참조)
         Phase C: 씬 이미지 생성 (캐릭터 참조 첨부)
         Phase D: search 씬 이미지 검색/다운로드
```

#### 캐릭터 분석 입력 변경

| | 현재 (step_5b) | 변경 (step_8b Phase A) |
|---|---|---|
| 입력 | scene_decomposition.json | scene_specs.json (creative direction 완료) |
| 판단 기준 | 원고 텍스트에서 인물명 추출 | generate 씬의 concept/narration에서 인물 추출 |
| 판단 대상 | 전체 씬 | generate 씬만 |
| 정확도 | 불필요한 캐릭터 생성 가능 | 실제 필요한 캐릭터만 |

### 4. 수정 대상 파일

#### 이로미즘 전용
- `auto_agent/data/artstyle/styles/quirky_cartoon.json` — prompt_overrides 필드 신규 추가

#### 글로벌 (프롬프트/렌더러)
- `auto_agent/data/prompts/single-call/creative-direction.md` — cinematic_overlay 스키마 추가
- `remotion/src/simple/CreativeScene.tsx` — cinematic 오버레이 렌더러 추가
- `auto_agent/remotion_template/src/simple/CreativeScene.tsx` — 동기화 (CLAUDE.md 규칙)
- `remotion/src/types/manifest.ts` — CinematicOverlay 타입 정의 추가
- `auto_agent/remotion_template/src/types/manifest.ts` — 동기화

#### 글로벌 (파이프라인)
- `auto_agent/data/pipeline.json` — step_5b 제거, step_6.depends_on → "step_5"로 변경
- `auto_agent/data/agents.json` — step_5b 항목 제거, character-planner 에이전트 역할 재정의
- `auto_agent/orchestrator/runner.py` — step_5b 관련 코드 제거, step_8b에 Phase A 추가
- `auto_agent/scripts/source_images.py` — 캐릭터 분석 Phase A 로직 추가
- `auto_agent/scripts/generate_images.py` — 캐릭터 생성 호출 시점 조정 (step_8b 내부 Phase B)
- `auto_agent/scripts/build_manifest.py` — cinematic_overlay → cinematicOverlay 변환 추가

#### 글로벌 (문서/스킬)
- `auto_agent/data/skills/agents/character-planner/SKILL.md` — 입력 변경 (scene_specs.json 기반)
- `auto_agent/data/skills/agents/image-sourcer/SKILL.md` — Phase A 통합 반영
- `auto_agent/data/CLAUDE.md.template` — 캐릭터 플래닝 순서 업데이트

#### 볼트 기록
- `kairos-vault/08-dev/이로미즘-시네마틱-연출-패턴.md` — 제작 패턴 기록 (위키링크 연결)
