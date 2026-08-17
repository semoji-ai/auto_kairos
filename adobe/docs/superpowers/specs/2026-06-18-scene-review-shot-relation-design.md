# 씬 검토(advisory) + shot_relation + 엔티티 태그 — 설계 (S1)

작성일: 2026-06-18
상태: 승인됨 (구현 계획 대기)

## 배경 / 문제

씬 분석(P4b)은 단일 패스로 scenes.json을 내고 **검토 과정이 없다**. 사용자 요구:
1. **씬별 레이아웃 설정이 잘됐는지 검토** — 내용↔layout 적합성.
2. **cinematic 씬의 연속/전환 구분** — 이전 씬과 시각적으로 이어지는지(continue) 새 시퀀스인지(cut). 이 판단을 **씬분석 시점에도 고려**.
3. (S2로 이어지는 토대) **엔티티 태그** — 씬별 캐릭터/장소/소품. 일관성 시트(S2) 연동의 기반.

**래칫은 쓰지 않는다(사용자 확정)** — 자동 재생성 없이 advisory 리포트만.

## 큰 그림 / 분해

전체 요구는 둘로 나뉜다:
- **S1(이 문서)**: shot_relation + 엔티티 태그(scene-analyze) + advisory 검토(review_scenes).
- **S2(별도)**: 일관성 시트 시스템 — 캐릭터(턴어라운드+표정)/장소(멀티앵글)/소품(멀티뷰) 시트 **생성** + 씬↔시트 링크 + Stage3 image_gen이 시트 첨부해 일관 렌더. (참조 시트 양식: `/Volumes/jleavens/007_AI프로젝트/special_haru/.../references/{characters,locations}/*.png` — 캐릭터=턴어라운드+표정, 장소=멀티앵글·주야.)

S1은 씬에 엔티티 태그를 미리 넣어 S2로 자연 연결된다.

## S1 범위 / 목표

scene-analyze가 씬별 `shot_relation`·`location`·`props`를 추가로 결정하고, 별도 `review_scenes`가 scenes.json을 검토해 **권고 리포트** `scene_review.json`을 낸다. 자동 수정 없음.

**범위 밖(YAGNI):** 시트 생성·렌더 연동(S2), 래칫/자동 수정.

## 결정사항

- **shot_relation** enum: `cut`(새 시퀀스) | `continue`(이전 씬 시각 연속). 첫 씬은 cut. 특히 cinematic 연출 시 판단.
- **엔티티 태그**: `location`(string), `props`(array). `characters`는 기존 유지.
- **검토 = advisory**(래칫 아님): 결정적 체크 + LLM 검토 → scene_review.json. 자동 수정 없음.
- 엔진 = `llm.run_orchestrator`(claude). LLM 실패 → 결정적 체크만으로 리포트(비블로킹).

## 아키텍처

### 구성요소
| 단위 | 변경 |
|---|---|
| `skills/scene-analyze/SKILL.md` | 출력에 `shot_relation`·`location`·`props` 추가 + 분류 가이드(연속/전환 판단, 엔티티 추출) |
| `backend/schemas/scene_specs.schema.json` | `shot_relation`(enum [cut, continue]), `location`(string), `props`(array) 추가 |
| `skills/scene-review/SKILL.md` (신규) | 씬 검토 프롬프트 — 레이아웃 적합·shot_relation 타당·엔티티 일관 |
| `backend/schemas/scene_review.schema.json` (신규) | 검토 출력 계약 |
| `backend/scene_analysis.py` | specs에 3필드 통과+adobe 보존 + `review_scenes` 추가(결정적 체크 + LLM 검토 → scene_review.json) |

### analyze_scenes 변경(필드만)
`specs`에 `shot_relation`(기본 "cut", 유효값만), `location`(str), `props`(list) 추가. adobe scene에 보존(_map_scene 후 부착). 기존 enrich/시그니처 유지.

### `review_scenes(proj_dir, *, on_event=None) -> dict`
```
scenes.json/final_manuscript.md 없으면 → {error}
det = 결정적 체크(Python):
   - 모든 씬 visual_summary 비지 않음
   - 모든 씬 layout이 enum 6종 중 하나
   - 모든 씬 shot_relation in {cut, continue}, scenes[0].shot_relation == cut
   - 분당 씬 수(plan duration 기준) 2~12 범위
   - narration 커버리지: 각 씬 narration이 원고(마커 제거)에 존재
   → issues 리스트
llm = scene-review 스킬(scenes 요약 + 원고) → {scenes:[{sceneNumber, layout_fit, shot_relation_fit, note}], flags:[...]}  (실패 시 {scenes:[], flags:[]})
report = {overall, deterministic:{scenes:N, per_minute:x, narration_coverage:bool, issues:[...]}, scenes: llm.scenes, flags: llm.flags}
→ scene_review.json 기록
return {report: 경로, flags: len(flags), det_issues: len(issues)}
```

### scene_specs 스키마 추가분
```json
"shot_relation": {"type":"string","enum":["cut","continue"]},
"location": {"type":"string"},
"props": {"type":"array"}
```

### scene_review 스키마 (LLM 출력)
```json
{
  "type":"object","additionalProperties":true,"required":["scenes"],
  "properties":{
    "scenes":{"type":"array","items":{"type":"object","additionalProperties":true,
      "properties":{"sceneNumber":{"type":"number"},
        "layout_fit":{"type":"string"},"shot_relation_fit":{"type":"string"},"note":{"type":"string"}}}},
    "flags":{"type":"array","items":{"type":"string"}},
    "overall":{"type":"string"}
  }
}
```

## 에러 처리
- scenes.json 또는 final_manuscript.md 없음 → `{error}`.
- LLM 검토 실패/파싱 실패 → llm 부분 비우고(scenes=[], flags=[]) 결정적 체크만으로 리포트(비블로킹).
- shot_relation 누락/이상값 → analyze_scenes에서 "cut"로 기본.
- 분당 씬 수 계산 시 duration 파싱 실패 → per_minute=None, 범위 체크 스킵.

## 테스트 전략 (stdlib·monkeypatch, 실 LLM 0)
1. **scene-analyze 필드**: `_direct_scenes` monkeypatch → scenes.json에 shot_relation/location/props 통과, 기본 shot_relation="cut", 유효성(이상값→cut).
2. **review_scenes 결정적**: visual 누락·layout enum 밖·첫 씬 continue·분당 씬 수 초과를 issues로 감지. (LLM monkeypatch로 빈 검토.)
3. **review_scenes LLM 병합**: scene-review monkeypatch(flags/scenes 반환) → scene_review.json에 병합, flags 카운트.
4. **LLM 실패 폴백**: run_orchestrator rc≠0 → 결정적만, flags=[], 비블로킹.
5. **에러**: scenes.json 없음 → error.
6. 스킬/스키마 자산 검증. 기존 P4b/실사 테스트 회귀 없음.

## 범위 밖 (S2)
- 캐릭터/장소/소품 시트 생성, 씬↔시트 링크, Stage3 시트 첨부 렌더.
- 검토 결과 자동 반영(래칫).
