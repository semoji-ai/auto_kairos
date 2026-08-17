# scene-analyze 실사 자료 자동 배정 — 설계

작성일: 2026-06-18
상태: 승인됨 (구현 계획 대기)

## 배경 / 문제

P4b 씬 분석은 모든 씬을 **AI 생성(image_prompt) 전제**로만 연출한다. 특허 문서(US 3,691,140)·역사 인물 사진·실존 제품/장소처럼 **실재하는 구체물**은 AI 생성 일러스트보다 **실사 자료**가 낫다(e2e 검수에서 사용자 지적).

- v3는 `imageAsset.source=generate|search`로 실사/생성을 구분하고 enricher가 실사를 검색한다.
- adobe는 실사 검색 인프라(`backend/search.py`: serper/pixabay)가 있으나 **수동 갤러리에만** 연결돼 있고, **자동 scene-analyze는 미사용**.

## 목표

scene-analyze가 씬을 **실사(search) vs AI 생성(generate)** 으로 분류하고, search 씬은 기존 `search.py`로 실사 1장을 받아 `imageRef`에 자동으로 채운다. adobe 검색 인프라 재사용이라 신규 코드 최소.

**범위 밖(YAGNI):** 이미지 품질·라이선스 검수(수동 갤러리에서 교체), Stage 3 생성/컴프, 동영상/차트 에셋.

## 결정사항 (확정)

- **엔진 = serper(Google 이미지) 기본** — 특허·실존 인물 같은 특정 실물을 찾아야 하므로. pixabay(일반 스톡)는 부적합 → 옵션만.
- **분류는 LLM(scene-analyze)이 결정**: 실재 구체물 → search(구체 `search_query` 포함), 추상/감정/세모지 톤 → generate. v3 관례대로 ~40~50% 실사 목표하되 내용 우선.
- **enrich는 선택 비활성 가능**: 키 없음/오프라인이면 스킵(생성 폴백). 비블로킹.

## 이식/재사용 (런타임 v3 의존 0)

- `backend/search.py`: `search_images(query, engine="serper", count=12) -> {images:[{title,url,thumb,source}], error?}`, `save_image(proj_dir, url, name, subdir="images/search") -> {status, path, rel}`.
- `backend/scenes.py`: scene의 `imageRef` 필드(`_map_scene` 출력에 존재), `set_image_ref`.

## 아키텍처

### 구성요소
| 단위 | 변경 |
|---|---|
| `skills/scene-analyze/SKILL.md` | 출력에 `asset_source`(generate\|search) + `search_query`(string) 추가 + 분류 가이드. narration·연출은 기존대로. |
| `backend/schemas/scene_specs.schema.json` | scene item에 `asset_source`(enum [generate, search]) + `search_query`(string) 추가 |
| `backend/scene_analysis.py` | scene_specs에 두 필드 통과 + adobe scene에 보존 + **enrich 루프** |

### `analyze_scenes` 인터페이스 변화
- `analyze_scenes(proj_dir, *, enrich=True, on_event=None) -> {scenes, count, searched} | {error}`.
  - `enrich=True`(기본): search 씬마다 실사 검색·다운로드·imageRef 설정.
  - `searched`: 실사가 붙은 씬 수.
  - 시그니처는 기존 호출(키워드 추가)과 호환.

### 데이터 흐름 (analyze_scenes, 변경분)
```
... split_manuscript + _direct_scenes(연출) ...
specs[i]에 asset_source(기본 'generate'), search_query 통과
adobe = [_map_scene(s) ... + layout 보존 + asset_source 보존]
scenes.json 기록 + ensure_scene_ids
if enrich:
    for 각 씬 where asset_source=='search':
        q = search_query or visual_summary
        res = search.search_images(q, engine='serper')         # 키 없음/결과0 → 스킵(폴백)
        if res.images:
            dl = search.save_image(proj_dir, images[0].url, f"real_{sceneId}.jpg")
            if dl.status=='completed': set imageRef = dl.rel; searched += 1
return {scenes, count, searched}
```
- imageRef는 scenes.json에 직접 기록(enrich 후 1회 더 저장) 또는 `scenes.set_image_ref` 재사용.

## scene_specs 스키마 (연출 + 에셋 분류)
```json
{
  "type":"object","additionalProperties":true,"required":["scenes"],
  "properties":{"scenes":{"type":"array","items":{"type":"object","additionalProperties":true,
    "properties":{
      "visual_summary":{"type":"string"},"image_prompt":{"type":"string"},
      "characters":{"type":"array"},
      "layout":{"type":"string","enum":["headline_only","items_list","metric_spotlight","quote","map","cinematic"]},
      "asset_source":{"type":"string","enum":["generate","search"]},
      "search_query":{"type":"string"}
    }}}}
}
```

## 에러 처리
- SERPER_API_KEY 없음 / 검색 결과 0 / 다운로드 실패 → 해당 씬 imageRef 비움(generate 폴백), 비블로킹 + on_event 통지.
- `asset_source` 누락/이상값 → generate 취급.
- `search_query` 누락된 search 씬 → visual_summary로 검색.
- enrich=False → 검색 완전 스킵(searched=0).
- 무삭제: `images/search/`에 versioned 저장.

## 테스트 전략 (stdlib·monkeypatch, 실 검색/LLM 0)
1. **스킬 자산**: scene-analyze SKILL.md에 `asset_source`·`search_query` 지시 + 분류 가이드 존재.
2. **스키마**: asset_source enum [generate, search], search_query 존재.
3. **analyze_scenes 실사 enrich**: `_direct_scenes` monkeypatch(일부 씬 asset_source=search) + `search.search_images`/`save_image` monkeypatch → search 씬 imageRef 채워지고 generate 씬 비움, `searched` 카운트.
4. **검색 실패 폴백**: search_images가 error/빈 결과 → imageRef 비움(폴백), 비블로킹.
5. **enrich=False**: search_images 미호출(searched=0).
6. **asset_source 보존**: scenes.json에 asset_source 통과.
7. 기존 P4b 테스트 회귀 없음.

## 범위 밖 (후속)
- pixabay 폴백 자동 전환(현재 serper 기본만).
- 이미지 적합성 LLM 재검수(현재 상위 1장 채택).
