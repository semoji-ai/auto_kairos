# S2c — 씬↔시트 첨부 렌더 설계

> auto_kairos_adobe 독립 Stage 1-2 일관성 시트 시스템(S2) 3단계(마지막).
> `scenes.json`의 엔티티 ID를 `entities.json`의 시트 파일로 해석해, 각 씬을 **관련 시트를 `-i`로 첨부**해 일관 렌더한다. `shot_relation=="continue"` 씬은 직전 렌더 씬도 첨부해 시각 연속성을 잇는다. **"시트를 만들면 그 시트로 씬을 만든다"의 실행부.** 런타임 v3 의존 0.

## 배경

- S2a: `scenes.json` 각 씬에 `character_ids`/`location_id`/`prop_ids`(안정적 엔티티 ID).
- S2b: `entities.json` 각 엔티티에 `sheet`(rel 경로) + `references/{characters,locations,props}/<id>.png`.
- 기존 렌더(`imagegen.generate_one`/`generate_many`)는 **단일 character_ref**만 받고 장소/소품 시트는 첨부하지 않음. 기존 `/api/storyboard/generate`(router)는 body의 단일 `character` 이름으로 `characters/char_<name>.png` 하나를 모든 씬에 첨부 — 레거시 단일 캐릭터 모델.

S2c는 **씬별로 그 씬의 캐릭터/장소/소품 시트를 정확히 첨부**하는 새 렌더 경로를 더한다. Session B의 storyboard 핸들러는 건드리지 않는다(별도 모듈, P5에서 패널 연결).

## 범위

**In scope** — 씬→시트 해석(resolver), 멀티시트 프롬프트 빌더, 순차 렌더 오케스트레이터(continue 연속 포함), `scenes/scene_<n>.png` 산출 + `imageRef` 링크.

**Out of scope** — 패널/SSE 노출(P5), 레이어 분리·모션(기존 Stage 3), storyboard 핸들러 변경.

## 아키텍처

| 파일 | 책임 |
|------|------|
| `backend/scene_render.py` (생성) | resolver + 프롬프트 빌더 + render_scenes |
| `tests/test_scene_render.py` (생성) | monkeypatch 단위 테스트(실 codex 없음) |

기존 재사용: `imagegen`(`_run_codex_image`, `versioned_path`, `base_img`, `load_style`), `scenes.set_image_ref`(sceneNumber 매칭 + 경로 검증).

## 공개 API

```python
def resolve_scene_refs(scene, entities_by_id, proj_dir) -> dict
    # {character_sheets:[{rel,name}], location_sheet:{rel,name}|{}, prop_sheets:[{rel,name}]}
    # entities_by_id[id]["sheet"]가 실제 존재하는 파일만 포함.

def build_scene_prompt(scene, descriptors, style_desc, rel_out, *, has_prev=False) -> str
    # descriptors(첨부 순서와 일치하는 설명문 리스트)를 합쳐 씬 프롬프트 생성.

def render_scenes(proj_dir, *, subdir="scenes", on_event=None) -> dict
    # {rendered, total, skipped:[{scene,error}]} | {error}
```

## 렌더 흐름 (sceneNumber 순차)

순차 렌더 — continue 연속 의존 + codex 동시 실행 시 출력 섞임(router 주석 실증)을 둘 다 회피.

1. `scenes.json`(없으면 `{error}`) + `entities.json`(없으면 `{error}`) 읽기 → `entities_by_id`.
2. `base = imagegen.base_img()`. `scenes/` 디렉터리 보장.
3. 각 씬(`sceneNumber` 오름차순):
   - `resolve_scene_refs` → 존재 시트만.
   - **첨부 `-i` 목록 + 설명문**(순서 = 번호): `[*캐릭터시트, 장소시트?, *소품시트, (continue && 직전 렌더됨 → 직전 씬), 세모지 베이스]`.
   - 캐릭터 시트 0개면 "인물 없음(배경/사물만)" 지시 추가.
   - `build_scene_prompt` → `imagegen._run_codex_image(proj_dir, out, prompt, images=...)`.
   - 성공: `scenes.set_image_ref(sceneNumber, rel)`, `prev_rel = rel`(다음 continue 참조).
   - 실패: `skipped`에 `{scene,error}`, 계속(비블로킹).
4. 반환 `{rendered, total, skipped}`.

### continue 연속

`scene.shot_relation == "continue"` && 직전 씬이 실제 렌더됨(`prev_rel`) → 직전 씬 이미지 첨부 + 프롬프트에 "카메라·배경·톤 연속" 지시(`has_prev=True`). 첫 씬·`cut`은 미첨부.

## 프롬프트 (멀티시트)

```
<style_desc>

## 장면
<scene.image_prompt | visual_summary | narration>

[첨부 이미지 — 순서대로]
- 1번 캐릭터 시트 '<name>': 이 인물을 그대로 사용(비율·얼굴·헤어·의상 100% 유지).
- 2번 장소 시트 '<name>': 이 장소를 배경으로 사용.
- 3번 소품 시트 '<name>': 이 소품을 그대로 사용.
- (continue) 4번 직전 씬: 카메라·배경·톤이 이어지는 연속 장면.
- (캐릭터 없음 시) 인물(사람)은 포함하지 말 것 — 배경/사물만.
- 마지막 세모지 베이스: 전체 그림체·색감 기준(베이스 인물 정체성 복사 금지).

## 생성 지시
... 첨부 시트 정체성 유지, 비율 텍스트 지시 금지, 텍스트 없음, <rel_out> 저장.
```

## 에러 처리 (비블로킹)

| 상황 | 처리 |
|------|------|
| `scenes.json` 없음/파싱 실패 | `{error}` |
| `entities.json` 없음 | `{error}` (S2a 먼저) |
| 시트 파일 없음 | resolver에서 제외 — 씬은 남은 시트(또는 베이스)로 렌더 |
| codex 실패 | `skipped`, 다음 씬 계속 |
| continue인데 직전 렌더 실패 | 직전 참조 없이 시트만으로 렌더 |

## 테스트 (monkeypatch, 실 codex 없음)

`tests/test_scene_render.py` — `imagegen._run_codex_image`를 더미 PNG 생성 + 호출 캡처로 패치:
1. **resolve 존재 파일만** — 시트 파일 있는 엔티티만 반환, 없는 엔티티 제외, name 동반.
2. **build_scene_prompt** — 씬 묘사·descriptors·rel_out 포함.
3. **render 정상** — 캐릭터+장소 시트 더미 → rendered 1, 첨부 목록에 두 시트+베이스, `imageRef="scenes/scene_1.png"`, 파일 존재.
4. **continue 연속** — 씬1(cut)·씬2(continue). 씬2 호출 images에 `scene_1.png` 포함 + 프롬프트에 "직전/연속". 씬1 images엔 prev(scene_*) 없음.
5. **실패 격리** — 씬1 codex 실패 → skipped, 씬2 렌더(rendered 1).
6. **entities.json 없음** → `{error}`.
7. **scenes.json 없음** → `{error}`.

**실 검증**: S2a→S2b→S2c를 작은 프로젝트로 실제 1회 돌려 씬이 시트와 일관 렌더되는지 수동 실증(컨트롤러+사용자).

## 격리·병합

격리 워크트리(`worktree-s2c-scene-render`, `git reset --hard main`) → 코드 TDD(subagent) → 실 검증(컨트롤러+사용자) → 전체 테스트 통과 → ff `git branch -f main <wt>`(Session B 무영향) → ExitWorktree.

## 후속

S2 완결. 다음은 **P5 패널·파이프라인 통합** — `run_brief_ratchet`/`run_research`/`run_manuscript_pipeline`/`analyze_scenes`/`review_scenes`/`build_entity_registry`/`generate_all_sheets`/`render_scenes`를 패널·jobs(SSE)에 노출하고 Stage1→2→3 체이닝.
