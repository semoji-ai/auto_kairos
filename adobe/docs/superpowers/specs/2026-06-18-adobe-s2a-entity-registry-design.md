# S2a — 엔티티 레지스트리 설계

> auto_kairos_adobe 독립 Stage 1-2의 일관성 시트 시스템(S2) 1단계.
> 씬별 free-text 엔티티 태그를 비디오 전체에 걸쳐 정규화된 레지스트리로 통합하고, 안정적 ID를 각 씬에 역링크한다. 텍스트 전용·런타임 v3 의존 0.

## 배경

`backend/scene_analysis.py`가 산출하는 `scenes.json`의 각 씬은 이미 다음을 갖는다:
- `characters` (list[str]) · `location` (str) · `props` (list[str]) — 모두 free-text
- `shot_relation` (cut|continue)

문제: 같은 엔티티가 씬마다 다르게 표기될 수 있고(예: "할머니" / "할머니 캐릭터" / "노인"), 비디오 전체의 정규화된 엔티티 목록·시각 명세가 없다. 이후 S2b(시트 생성)·S2c(씬↔시트 첨부)는 안정적 엔티티 ID와 시각 명세를 입력으로 요구한다.

S2a는 그 **계약(`entities.json`)** 과 **씬 역링크**를 만든다. 이미지 생성은 하지 않는다.

## 범위

**In scope**
- `scenes.json` + `final_manuscript.md` + `editorial_brief.json`에서 엔티티 출현 수집
- LLM 통합: 표기 변형 dedupe + canonical id/type/name/aliases + **풍부 시각 명세** 합성
- `entities.json`(canonical 레지스트리) 기록
- 각 씬에 안정적 엔티티 ID 역링크(`character_ids`/`location_id`/`prop_ids` 추가, 원본 free-text 보존)

**Out of scope (후속)**
- S2b: 시트 이미지 생성(턴어라운드/멀티앵글/멀티뷰)
- S2c: 씬↔시트 첨부 및 Stage3 렌더 통합
- 패널/SSE 노출(P5)

## 아키텍처

기존 Stage 1-2 모듈 패턴(모듈 전역 함수, `llm.run_orchestrator`, `_extract_json`, monkeypatch 테스트)을 그대로 따른다.

| 파일 | 책임 |
|------|------|
| `backend/entities.py` (생성) | 수집·통합·폴백·역링크 오케스트레이션 |
| `backend/schemas/entities.schema.json` (생성) | LLM 출력 계약 |
| `skills/entity-registry/SKILL.md` (생성) | 통합·시각명세 합성 프롬프트 |
| `tests/test_entities.py` (생성) | monkeypatch 단위 테스트 |

공개 함수:
```python
def build_entity_registry(proj_dir, *, on_event=None) -> dict:
    """scenes.json의 엔티티 태그를 정규화 레지스트리로 통합하고 씬에 ID 역링크.
    반환 {entities, scenes_updated} 또는 {error}."""
```

## 데이터 흐름

1. **읽기** — `scenes.json`(필수, 없으면 `{error}`), `final_manuscript.md`, `editorial_brief.json`(있으면 묘사 출처).
2. **결정적 수집** — 각 씬을 순회하며 출현 모음:
   - `characters`(list) → 각 항목 `{type:"character", raw, scene}`
   - `location`(str, 비어있지 않으면) → `{type:"location", raw, scene}`
   - `props`(list) → 각 항목 `{type:"prop", raw, scene}`
   - 출현이 0건이면 `{entities:0, scenes_updated:0}` 반환(통합 호출 생략).
3. **LLM 통합** — `entity-registry` 스킬 + 출현목록 + 원고 + 브리프 → `run_orchestrator(output_schema=entities.schema.json, output_last=entities_llm.json)`. (`scene_analysis._review_scenes_llm`가 `scene_review_llm.json`에 쓰는 패턴과 동일 — LLM 원출력은 별도 파일.)
4. **파싱·검증** — `entities_llm.json`에서 `entities[]` 로드. `returncode != 0` 또는 파싱 실패 또는 빈 배열 → **결정적 폴백**(아래).
5. **결정적 역링크** — alias→id 매핑 구성 후 각 씬에:
   - `character_ids` = 매칭된 character 엔티티 id 리스트
   - `location_id` = 매칭된 location 엔티티 id(없으면 `""`)
   - `prop_ids` = 매칭된 prop 엔티티 id 리스트
   - 매칭 실패한 raw 태그는 free-text 유지·ID 없음, `on_event`로 로깅.
6. **기록** — 최종 `entities.json`(canonical) 기록, `scenes.json` 역링크 반영해 다시 기록(기존 필드 전부 보존).
7. 반환 `{entities: <count>, scenes_updated: <count>}`.

### 결정적 폴백 (비블로킹)

LLM 통합 실패 시 파이프라인을 멈추지 않는다. unique `(type, normalized_raw)`마다 자기 자신 엔티티 생성:
- `id` = `f"{type}-{n}"`(타입별 1부터; 예 `character-1`, `location-1`, `prop-1`)
- `name` = raw, `aliases` = `[raw]`, `visual` = `{}`, `first_scene` = 최초 등장 씬, `scenes` = 등장 씬들
- dedupe는 정확 일치(정규화 후)만. 표기 변형 통합은 못 하지만 ID 역링크는 동작.

## 엔티티 스키마 (`entities.schema.json`)

```json
{
  "type": "object",
  "additionalProperties": true,
  "required": ["entities"],
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true,
        "required": ["id", "type", "name"],
        "properties": {
          "id": { "type": "string" },
          "type": { "type": "string", "enum": ["character", "location", "prop"] },
          "name": { "type": "string" },
          "aliases": { "type": "array" },
          "visual": { "type": "object" },
          "first_scene": { "type": "integer" },
          "scenes": { "type": "array" }
        }
      }
    }
  }
}
```

`visual`는 type별 자유 구조(스킬이 지시, 스키마는 느슨):
- character → `{appearance, hair, outfit, expressions[]}`
- location → `{space, mood, lighting}`
- prop → `{form, material, color}`

## 역링크 매칭 규칙 (결정적)

- 정규화 `_norm(s)` = 공백 collapse + strip(한국어라 대소문자 무관).
- raw 태그를 같은 type의 엔티티 `name`·각 `alias`와 정규화 후 정확 일치 비교. 첫 일치 id 채택.
- type 교차 매칭 금지(character raw는 character 엔티티만).
- 일치 없으면 ID 미부여 + 로깅.

## 에러 처리

| 상황 | 처리 |
|------|------|
| `scenes.json` 없음 | `{error: "scenes.json 필요 (씬 분석 먼저)"}` |
| `scenes.json` 파싱 실패 | `{error: "scenes.json 파싱 실패"}` |
| 출현 0건 | `{entities:0, scenes_updated:0}` (정상) |
| LLM returncode≠0 / 파싱 실패 / 빈 배열 | 결정적 폴백, 비블로킹 |
| 역링크 미매칭 raw | free-text 유지, 로깅 |

## 테스트 (monkeypatch, 실제 LLM 없음)

`tests/test_entities.py` — `llm.run_orchestrator`를 가짜 통합 JSON으로 패치하는 기존 패턴 사용:

1. **정상 통합·역링크** — 두 씬에 character "할머니"/"할머니 캐릭터", location "거실". 가짜 LLM이 둘을 한 엔티티(aliases 둘 다)로 통합. `entities.json`에 character 1·location 1, 각 씬 `character_ids`가 같은 id, `location_id` 채워짐.
2. **dedupe(표기 변형 → 한 id)** — 서로 다른 raw 두 개가 같은 엔티티 id로 역링크됨 검증.
3. **폴백(LLM 실패)** — `returncode:1` 패치 → 결정적 폴백으로 unique 태그마다 엔티티 생성, 씬 역링크 동작, 파이프라인 정상 반환.
4. **출현 0건** — 엔티티 태그 없는 scenes.json → `{entities:0, scenes_updated:0}`, LLM 미호출.
5. **scenes.json 없음** — `{error}` 반환.
6. **원본 보존** — 역링크 후에도 씬의 기존 필드(`characters`/`location`/`props`/`narration`/`sceneNumber`/`layout` 등) 전부 유지.

## 격리·병합

격리 워크트리(`worktree-s2a-entity-registry`, `git reset --hard main`) → 구현 → 전체 테스트 통과 → ff `git branch -f main <wt>`(Session B `feat/tylenol-motion-recreation` 무영향) → ExitWorktree(remove).

## 후속 (S2 나머지)

- **S2b** — 엔티티별 멀티패널 시트 생성(codex). reference: `H00_modern_haru_sheet.png`(캐릭터 턴어라운드+표정), `L00_present_gyeongcheonseom_sheet.png`(장소 멀티앵글). `entities.json`의 `visual` 명세를 프롬프트 입력으로.
- **S2c** — 씬의 `character_ids`/`location_id`/`prop_ids` → 시트 파일 해석, `imagegen.generate_one`/`generate_asset`이 관련 시트 첨부해 일관 렌더.
