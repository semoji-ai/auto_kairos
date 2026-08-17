# S2b — 시트 생성 설계

> auto_kairos_adobe 독립 Stage 1-2 일관성 시트 시스템(S2) 2단계.
> `entities.json`(S2a)의 엔티티별 멀티패널 일관성 시트를 codex로 1장씩 생성하고 `references/`에 저장, `entities.json`에 `sheet` 경로를 역기록한다. 이 시트는 다음 단계 **S2c가 씬 생성 시 첨부**해 일관 렌더에 쓴다.

## 배경·목표

S2a가 `entities.json`(canonical 엔티티 + 풍부 `visual` 명세) + 각 씬의 `character_ids`/`location_id`/`prop_ids`를 만들었다. S2b는 엔티티별 **기준 시트 이미지**를 만든다. 최종 사용처는 S2c: "씬 → 엔티티 ID → 시트 파일"로 해석해 씬 렌더러(`imagegen.generate_one`/`generate_asset`)에 시트를 `-i`로 첨부 → 캐릭터·장소·소품이 씬마다 일관되게 그려진다.

## 핵심 결정 (사용자 확정)

- **캐릭터**: 세모지 베이스를 1회성으로 "시트화"한 기준 시트(`data/artstyle/semoji_base_sheet.png`)를 첨부해 **한 번의 codex 호출로 리스타일**("이 시트의 캐릭터를 OO로 변경, 레이아웃·포즈·표정 구성·비율 유지, 헤어·의상만 변경"). 레이아웃·정체성·비율을 베이스 시트가 **단일 소스로 락** → 패널별 생성·합성·드리프트 없음.
- **장소·소품**: 공유 기준 베이스가 없으므로 **단일샷 멀티패널**(장소 6패널, 소품 4뷰)을 codex 1호출로. 세모지 베이스는 그림체 참고로만 첨부, 인물 없음.
- **소품 선별**: `scenes` 길이 **≥ 2**(재등장)인 소품만. 1씬 소품은 일관성 비교 대상이 없어 시트 불필요.
- 전략 근거: 메모리 "비율·정체성=첨부 이미지가 단일 소스(텍스트 비율 지시 금지)"와 일치.

## 범위

**In scope** — 베이스 캐릭터 시트 1회성 생성 함수 + 엔티티별 시트 생성(캐릭터/장소/소품) + `entities.json` `sheet` 역기록.

**Out of scope** — S2c(씬↔시트 첨부, 씬 렌더 통합), P5(패널/SSE). 레이어 분리·모션은 기존 Stage 3.

## 아키텍처

| 파일 | 책임 |
|------|------|
| `backend/sheets.py` (생성) | 프롬프트 빌더 + 엔티티별 시트 생성 + 레지스트리 역기록 |
| `data/artstyle/semoji_base_sheet.png` (생성·커밋) | 1회성 기준 캐릭터 시트(턴어라운드+표정 레이아웃) |
| `tests/test_sheets.py` (생성) | monkeypatch 단위 테스트(실 codex 없음) |

기존 `imagegen` 재사용: `_run_codex_image`(세마포어+rate limit 백오프), `versioned_path`(무삭제), `base_img`, `load_style`. Pillow 합성은 **불필요**(codex가 시트 1장을 통째 생성).

### 출력 경로

`references/characters/<id>.png` · `references/locations/<id>.png` · `references/props/<id>.png` (proj_dir 기준, versioned).

## 공개 API

```python
def base_sheet() -> Path | None
    # data/artstyle/semoji_base_sheet.png 경로(없으면 None)

def build_base_character_sheet(*, on_line=None) -> dict
    # 1회성: semoji_base.jpg → 턴어라운드+표정 기준 시트 생성(실 codex). 수동 실증 후 자산 커밋.

def generate_sheet(proj_dir, entity, *, on_line=None) -> dict
    # 엔티티 1개 → type별 디스패치 → codex 1호출 → references/<type>/<id>.png.
    # {status:"completed", path, rel} | {status:"failed", error}

def generate_all_sheets(proj_dir, *, types=("character","location","prop"), on_event=None) -> dict
    # entities.json 읽기 → 대상 필터(소품 ≥2씬) → 엔티티별 generate_sheet → sheet 역기록.
    # {sheets:{character,location,prop}, skipped:[{id,error}]} | {error}
```

순수 헬퍼(테스트 용이): `_looks_from_visual(visual)`, `build_character_sheet_prompt`, `build_location_sheet_prompt`, `build_prop_sheet_prompt`, `_wants_sheet(entity)`.

## 프롬프트 설계

- **캐릭터**(베이스 시트 첨부): "첨부 1번은 캐릭터 기준 시트(전신 턴어라운드+얼굴 클로즈업+표정 5컷). 이 시트의 캐릭터를 '<name>'으로 변경, **패널 구성·포즈·표정 칸 배치·비율·얼굴 구조·그림체 그대로 유지, 헤어·의상만 변경**: <looks>. 표정 칸 정서: <expressions>. 비율 텍스트 지시 금지. 글자·로고 없음. <rel_out> 저장."
  - `looks` = visual의 hair/outfit/appearance 합성. expressions = visual.expressions.
- **장소**(세모지 베이스 스타일 첨부): "<style>. '<name>' 장소를 한 이미지 6패널(2×3): 항공 와이드/각도2/지상 아이레벨/랜드마크 디테일/수면 원경/야경. 공간·분위기·조명=<visual>. 첨부는 그림체 참고용 — **인물 절대 금지, 배경만**. 1장 생성 <rel_out> 저장."
- **소품**(세모지 베이스 스타일 첨부): "<style>. '<name>' 소품을 한 이미지 4뷰(2×2): 정면/측면/디테일/인컨텍스트. 형태·재질·색=<visual>. **인물 금지, 사물만**. <rel_out> 저장."

## 데이터 흐름

1. `generate_all_sheets` → `entities.json` 로드(없으면 `{error}`).
2. 각 엔티티: `type in types` && `_wants_sheet`(소품 ≥2씬) 아니면 skip.
3. `generate_sheet` → type별 프롬프트 + 첨부 → `imagegen._run_codex_image` → `references/<type>/<id>.png`.
4. 성공 → `entity["sheet"] = rel`, 카운트++. 실패 → `skipped`에 `{id,error}`, 계속(비블로킹).
5. `entities.json` 다시 기록(기존 필드 보존).

## 에러 처리

| 상황 | 처리 |
|------|------|
| `entities.json` 없음/파싱 실패 | `{error}` |
| 캐릭터인데 `base_sheet()` 없음 | 그 엔티티 `{status:failed, error}` → skipped, 계속 |
| codex 실패(no_file/rate_limit) | skipped, 계속(`_run_codex_image` 백오프 후에도 실패 시) |
| unknown type | `{status:failed}` → skipped |

## 테스트 (monkeypatch, 실 codex 없음)

`tests/test_sheets.py`:
1. **프롬프트 빌더(순수)** — 캐릭터: 베이스시트 전제·"레이아웃 유지"·name·looks 포함. 장소: 6패널·"인물" 금지. 소품: 4뷰·"인물" 금지.
2. **generate_all_sheets 정상** — char1/loc1/prop(2씬)1/prop(1씬) 엔티티. `imagegen._run_codex_image`·`base_sheet` 더미 패치 → counts {char1,loc1,prop1}, 1씬 prop 미생성, `entities.json` 3개에 `sheet`, references 파일 존재.
3. **소품 ≥2씬 필터** — 1씬 prop은 counts·skipped 어디에도 없음(대상 아님).
4. **캐릭터 base_sheet 없음** — `base_sheet()`가 None → 그 캐릭터 skipped(error 포함), 나머지 진행.
5. **codex 실패 격리** — 한 엔티티만 `{status:failed}` 반환하도록 패치 → skipped에 담기고 나머지 완료.
6. **entities.json 없음** → `{error}`.
7. **build_base_character_sheet** — `imagegen.base_img`·`_run_codex_image` 패치 → 프롬프트에 턴어라운드+표정 5컷 지시 포함, base 없으면 failed.

실 이미지 품질(베이스 시트 + 캐릭터 시트 1건)은 **실 codex 1회 생성 후 수동 실증**(character-sheet "확정·실증" 방식).

## 격리·병합

격리 워크트리(`worktree-s2b-sheet-generation`, `git reset --hard main`) → 코드 TDD(subagent) → **베이스 시트 실 생성·실증·커밋(컨트롤러+사용자 검증)** → 전체 테스트 통과 → ff `git branch -f main <wt>`(Session B 무영향) → ExitWorktree.

## 후속 (S2c)

씬의 `character_ids`/`location_id`/`prop_ids` → `entities.json`의 해당 `sheet` 경로 해석 → `imagegen.generate_one`(캐릭터 시트 `-i`)·`generate_asset`(장소/소품 시트 `-i`)이 첨부해 씬을 일관 렌더. **시트를 만들면 그 시트로 씬을 만든다**는 사용자 방향의 실행부.
