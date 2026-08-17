# adobe 독립 Stage 1-2 — P4b: 씬 분석 — 설계

작성일: 2026-06-17
상태: 승인됨 (구현 계획 대기)

## 큰 그림

auto_kairos_adobe 독립 Stage 1-2의 마지막 조각(P4b). 런타임 v3 의존 0.
전체 흐름:
> 기획 → 브리프 래칫(P2) → 리서치(P3) → 원고 초안→타겟쿼리→타겟리서치→적용→원고 래칫(P4a) → **씬 분석(P4b)** → (P5 통합)

P4b가 끝나면 사용자가 지정한 9단계 흐름이 완결되고, adobe 단독으로 기획~씬까지 산출한다.

## P4b 범위 / 목표

`final_manuscript.md`(P4a 잠금본)를 **씬으로 분할하고 씬별 시각 연출을 결정**해 **adobe 네이티브 `scenes.json`**(Stage 3 입력)을 산출한다.

**핵심 설계(마커 기반):** 원고 작성 단계(P4a)에서 작가 LLM이 자연스러운 씬 경계에 마커를 삽입하고, P4b는 **마커로 결정적 분할**한다. narration은 원고의 정확한 부분문자열로 자동 보장되고, P4b의 LLM은 **연출만** 결정한다(narration 미생성).

**P4b가 하지 않는 것(YAGNI):** 최종 레이아웃/이미지 생성·패널 통합(P5/기존 Stage3). layout은 *제안*만.

## 결정사항 (확정)

- **마커**: 씬 경계 `<!--SCENE-->`(단독 줄), 선택 캐릭터 `<!--CHARS: 이름1, 이름2-->`. HTML 주석이라 렌더 시 비표시·분할 명확.
- **narration 무결성**: Python이 마커로 분할 → 각 세그먼트 텍스트가 narration(정확한 부분문자열). LLM이 원고를 못 바꿈.
- **LLM은 연출만**: scene-analyze 스킬이 narration 목록을 받아 씬별 `{visual_summary, image_prompt, characters?, layout?}`만 반환.
- **출력 = adobe 네이티브 scenes.json**: 기존 `backend/v3_import._map_scene` 재사용으로 Stage 3 호환 보장(DRY).
- 엔진 = `llm.run_orchestrator`(기본 claude). 단일 패스(래칫 없음 — 원고 품질은 P4a 래칫이 보증).

## 이식 원본 (읽기 전용)

`/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/data/skills/agents/script-director/SKILL.md`의 **chapters 모드**(씬 분할·연출 결정, narration 재작성 금지). adobe는 경계를 마커로 받으므로 "연출만" 부분을 이식.

## 아키텍처

### 구성요소
| 단위 | 책임 | 비고 |
|---|---|---|
| `skills/manuscript-write/SKILL.md` (P4a 보정) | 자연스러운 씬 경계에 `<!--SCENE-->` 삽입(+선택 `<!--CHARS: ...-->`) | 기존 "마커 불필요" 지시를 "마커 삽입"으로 교체 |
| `skills/scene-analyze/` (SKILL.md+skill.json) | narration 목록 → 씬별 연출(JSON) | chapters 모드 이식, narration 미출력 |
| `backend/schemas/scene_specs.schema.json` | 연출 출력 계약 | `{scenes:[{visual_summary, image_prompt, characters?, layout?}]}` |
| `backend/scene_analysis.py` | 분할·LLM연출·매핑 오케스트레이터 | `split_manuscript`, `analyze_scenes`; `v3_import._map_scene`·`scenes.ensure_scene_ids` 재사용 |

### `backend/scene_analysis.py` 인터페이스
- `split_manuscript(text: str) -> list[dict]` — `<!--SCENE-->`로 분할 → `[{narration, characters}]`. 각 세그먼트에서 `<!--CHARS: ...-->`를 정규식으로 추출(있으면)하고 narration에서 제거. 마커 없으면 전체가 1씬.
- `analyze_scenes(proj_dir, *, on_event=None) -> {scenes: path, count} | {error}`.

### 데이터 흐름 (analyze_scenes)
```
final_manuscript.md 없으면 → {error}
segments = split_manuscript(text)            # [{narration, characters}], 결정적
if not segments → {error}
directions = scene-analyze 스킬(LLM, narration 목록 입력) → [{visual_summary, image_prompt, characters?, layout?}]
# 인덱스로 zip(개수 불일치 시 누락분은 빈 연출). characters는 마커 우선, 없으면 LLM.
scene_specs = [{sceneNumber:i+1, narration, visual_summary, image_prompt, characters, layout?} ...]
adobe_scenes = [v3_import._map_scene(s) for s in scene_specs]
scenes.json 기록({scenes: adobe_scenes}) + scenes.ensure_scene_ids(proj_dir)
→ {scenes: scenes.json 경로, count}
```

## 마커 규약 (P4a manuscript-write 보정)
- 씬 경계: 씬과 씬 사이에 **단독 줄 `<!--SCENE-->`**. 분량(editorial_brief duration)에 맞는 적정 씬 수로 분할(예: 분당 4~8씬 안내).
- 캐릭터(선택): 해당 씬 안에 `<!--CHARS: 이름1, 이름2-->` 줄.
- 마커 외 본문은 순수 prose 유지. (기존 "마커 불필요" 지시 줄 교체.)

## scene_specs 스키마 (연출, narration 미포함)
```json
{
  "type":"object","additionalProperties":true,"required":["scenes"],
  "properties":{"scenes":{"type":"array","items":{"type":"object","additionalProperties":true,
    "properties":{"visual_summary":{"type":"string"},"image_prompt":{"type":"string"},
      "characters":{"type":"array"},"layout":{"type":"string"}}}}}
}
```

## 에러 처리
- final_manuscript.md 없음 → `{error: "final_manuscript.md 필요 (P4a 먼저)"}`.
- 세그먼트 0 → `{error}`.
- 스킬 rc≠0/파싱 실패 → 연출 없이 narration만으로 최소 scene_specs 생성(visual_summary=narration 앞부분 폴백) + 경고(비블로킹).
- directions 개수 < segments → 부족분 빈 연출. > segments → 초과분 무시.
- 기존 scenes.json 있으면 덮어씀(생성 산출물).

## 테스트 전략 (stdlib·monkeypatch, 실 LLM 0)
1. **split_manuscript**: `<!--SCENE-->` 분할 개수, narration 부분문자열 정확성, `<!--CHARS-->` 추출·제거, 마커 없을 때 1씬.
2. **analyze_scenes**: llm.run_orchestrator monkeypatch(연출 JSON 주입) → scenes.json 생성, sceneNumber/narration/visual_summary 매핑, sceneId 발급(ensure_scene_ids), count.
3. **연출 개수 불일치**: directions < segments → 빈 연출 채움; > → 무시.
4. **폴백**: 스킬 실패 → narration만으로 최소 scenes 생성.
5. **에러**: 원고 없음/세그먼트 0 → error.
6. **P4a 마커 보정**: manuscript-write SKILL.md에 `<!--SCENE-->` 지시 존재, "마커 불필요" 문구 제거.
7. 스킬/스키마 자산 검증.

## 범위 밖 (P5)
패널·파이프라인 UI 통합, 전체 Stage1→2→3 체이닝, run 버튼.
