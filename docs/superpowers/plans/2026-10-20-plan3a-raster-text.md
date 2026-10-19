# 계획 3a: 일러스트·이미지 속 한글 → 영어 교체 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** 코스트코(B209) 영어판에서 화면에 보이는 일러스트(.ai 레이어)·이미지 속 한글을 영어로 바꿔, 영상 전체 OCR 한글 0자(실제 브랜드 간판 예외)를 만든다.

**Architecture:** AE에서 실제 렌더에 쓰이는 footage(일러스트 레이어·이미지)를 k배 TIFF로 내보내고(렌더 큐 + aerender, 화면 잠김 무관) → macOS Vision OCR(`tools/ocr`, 사변형 좌표)로 한글 레이어 선별 → 맥락 붙인 번역(`claude -p`) → `sg/raster.py`가 글자·그림자를 RGBA 배경 추정 + 인페인팅으로 지우고 원래 색·기울기(두 색 강조 포함)로 영어를 그림 → AE에서 같은 크기 프리컴프(k배 PNG를 1/k로)로 레이어 소스 교체 → 기존 워프·자막·렌더 → 전체 OCR 검사.

**Tech Stack:** Python 3(numpy, PIL, opencv-python-headless 5.0), Swift(Vision), AE 2026 ExtendScript, aerender.

**Spec:** `docs/superpowers/specs/2026-10-19-semoji-global-localization-design.md` §8 (+ 사용자 결정 2026-10-20: 실제 브랜드 간판·로고는 유지, 뉴스 캡처는 큰 문구만 영어·작은 본문은 흐림, 손글씨는 Noteworthy)

## Global Constraints
- 프로토타입(검증됨): `scratchpad/proto_raster.py` — 바·카드·띠 5종 교체 성공. 본 구현은 이 알고리즘을 모듈화·테스트.
- 폰트: 고딕 `~/Library/Fonts/SBAggroOTF-B.otf`, 손글씨 `/System/Library/Fonts/Noteworthy.ttc`(Bold). 렌더 전 모든 글자가 폰트에 있는지 검사(없으면 번역 재요청).
- 유지 대상: OCR 문구 전체가 브랜드 표기(`롯데마트`, `이마트`, `홈플러스`, `코스트코`, `emart`, `LOTTE` 등 `brands` 목록)인 항목. 뉴스 캡처(래스터 이미지 1920폭 이상): 글자 높이 ≥ 이미지 높이 3%만 교체, 나머지 한글 영역은 가우시안 흐림.
- 내보내기 배율 k=4(벡터만), 최장변 3000px 상한. 래스터는 원래 해상도.
- AE 규칙(계획 1·2와 동일), NAS 원본 수정 금지, 디스크 10GB 미만 중단.

## Review Focus
1. 반투명 그라데이션 바 위 흰 글자 + 어두운 그림자 — 잔상 없이 지워져야 함(테스트).
2. 기울어진 카드의 두 색 강조 — 강조 위치·색 유지, 모양 가장자리 훼손 없음(테스트).
3. 폰트에 없는 글자(₩ 등) — 그리기 전에 걸러야 함(테스트).
4. 같은 footage를 여러 레이어가 쓰는 경우 — 교체 프리컴프가 모든 사용처에 같은 크기로 적용.
5. OCR이 놓친 한글 — 최종 영상 OCR 검사에서 잡혀야 함.

---

### Task 1: `sg/raster.py` (교체 알고리즘) + 테스트
**Files:** Create `sg/raster.py`, `tests/test_raster.py`
**Produces:** `quad_geom(quad)->(angle,w,h,cx,cy)`, `erase_text(rgba, quad)->(rgba, colors:list, two_tone:bool)`, `missing_glyphs(text, font_path)->list[str]`, `draw_text(rgba, quad, text, colors, two_tone, font_path, size_ratio=0.72)->rgba`(텍스트 안 `[[…]]`은 강조색), `replace_items(png_in, png_out, items, font_path)`.
- [ ] 실패하는 테스트(합성 이미지): 반투명 어두운 바(알파 200) 위 흰 사각형 글자+검은 그림자 → `erase_text` 후 사변형 안 픽셀이 배경 ±12 이내·알파 ±15 이내 / 기울어진 흰 카드 위 검정·빨강 막대 → two_tone True, 두 색이 검정·빨강 / 카드 경계 밖 알파 불변 / `missing_glyphs("₩5", SB어그로) == ["₩"]` / `draw_text`가 강조 부분을 빨강으로 그림(해당 영역 빨강 픽셀 존재).
- [ ] 실패 확인 → 프로토타입 알고리즘으로 구현 → 통과 → 커밋.

### Task 2: 전체 내보내기 + OCR + 대상 선별
**Files:** Create `scripts/raster_scan.py`
- `python3 scripts/raster_scan.py episodes/B209` : 파트별 `reach_items`로 이미지·.ai footage id 수집 → `build_export.jsx`(k=4, max_px=3000) → `aerender -project raster/export.aep` → TIFF→PNG → `tools/ocr` → `raster/items.json` `[{id, name, kind: "ai"|"image", w, h, k, mode: "replace"|"keep_brand"|"news", items:[{text, quad, keep: bool}]}]` (한글 없는 레이어 제외).
- [ ] Expected: 내보내기 오류 0, 한글 레이어 수 보고(오프닝 시험 기준 51개 중 14개 비율), 브랜드 유지 항목 목록 출력.

### Task 3: 문구 번역
**Files:** Create `scripts/raster_translate.py` (sg.translate 재사용)
- 항목마다 `{id: "<footage>#<n>", ko, max_chars(원래 글자수×2.2와 폭 기준 중 작은 값), two_tone, hint: 레이어 이름, context: 그 레이어가 보이는 시각의 내레이션 한국어}` → `l10n/en.json`의 `raster` 섹션. two_tone이면 "강조 부분을 [[ ]]로 표시" 지시. 결과 글자가 폰트에 없으면 그 항목만 재요청(최대 2회).
- [ ] Expected: 모든 대상 번역, missing_glyphs 0.

### Task 4: 교체 PNG 생성 + 검수 시트
**Files:** Create `scripts/raster_render.py`
- 이름에 `말`/`말풍`이 들어가거나 OCR 높이 대비 획이 가는 항목 → Noteworthy, 그 외 SB 어그로 B. 뉴스 모드는 큰 글자만 교체, 나머지 한글 영역 흐림. → `raster/en/<id>.png`, `raster/review_sheet_*.png`(원본|교체 쌍).
- [ ] Expected: 시트를 눈으로 검수, 어색한 항목은 수동 보정 목록(`raster/manual.json`)으로 기록 → 재생성. 남은 문제 항목만 `$imagegen` 편집(공냥 규격) 대상으로 표시.

### Task 5: AE 교체 + 재빌드
**Files:** Create `scripts/ae/replace_items.jsx`, `scripts/raster_apply.py`
- JSX: PNG 가져오기 → 원래 footage와 같은 w×h 컴프 `__en_<id>`(PNG 레이어 scale 100/k) → 그 footage를 쓰는 모든 레이어 `replaceSource(comp,false)` → save_as `build/en/B209_en_text_raster.aep`. 로그 replaced·errors.
- 이후 계획 2 런북 5~8단계(워프 `--aep …_raster.aep` → 자막 → 파트 렌더 → 미리보기).
- [ ] Expected: errors 0, 미리보기 길이 886.15±0.1.

### Task 6: 전체 OCR 검사 (한글 0자 게이트)
**Files:** Create `scripts/qa_hangul.py`
- 미리보기를 1초 간격 프레임 추출 → `tools/ocr` → 한글 포함 항목 중 brands·자막바 영역 외 → `render/en/qa/hangul.json` + 문제 프레임 시트.
- [ ] Expected: 브랜드 예외 외 0건. 남으면 원인(OCR 누락·영상 클립 속 글자)을 분류해 보고하고 Task 2~5 반복 또는 사용자 판단 요청.
