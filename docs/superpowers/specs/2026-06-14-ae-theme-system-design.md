# AE 통합 테마 시스템 설계

> 작성: 2026-06-14 · 범위: 차트/지도 디자인 테마(추후 전체 아트스타일 확장)

## 1. 목적

AE 패널 안에서 차트·지도 디자인을 **테마 단위로 손쉽게 전환**하고, 괜찮은 디자인 셋을
**리서치(참고 이미지 분석)로 수집·확장**할 수 있게 한다.

현재 상태:
- `data/artstyle/ae_tokens.json` 한 파일이 `colors/fonts/type/map/chartagent`를 모두 보유
- chartagent 명세서(`chart_{sid}.spec.json`)와 지도 테마(`map.defaultTheme`)를 각각 토큰으로 주입
- 빠진 것: **테마 셋을 통째로 갈아끼우는 개념**과 **패널에서 고르는 UI**, **리서치 수집 경로**

## 2. 결정 사항 (확정)

| 항목 | 결정 |
|---|---|
| 적용 범위 | 차트/지도 먼저, 나중에 전체 아트스타일로 확장 |
| 수집 방식 | 카탈로그 기본(검증된 셋) + 리서치 신규 추가 |
| 적용 단위 | 프로젝트 전역 1개 + 씬별 예외(override) |
| 테마 구조 | **통합 테마**(A) — 차트+지도를 한 테마에, 단 내부 섹션은 분리 |
| 시드 테마 | 3개로 시작(세모지 / 모던클린 / 다크방송) → 리서치로 확장 |

## 3. 테마 카탈로그 구조

**저장**: `data/artstyle/themes/<id>.json` — 테마 1개 = 파일 1개, 무삭제·추가형.

**스키마**:
```jsonc
{
  "id": "semoji",
  "label": "세모지",
  "source": "내장 시드" | "리서치: <레퍼런스>",
  "colors": { "accentRgb": [..], "textRgb": [..], "mutedRgb": [..], "bgRgb": [..] },
  "chart": {
    "theme_set": "gallery_infographic",
    "theme_overrides": { "pattern_mode": "outline_plus_hatch" }
  },
  "map": {
    "tile": "bright",                                   // "bright" | "dark"
    "overrides": [ { "match": "background", "paint": {..} } ],
    "rasterFilter": "sepia(0.32) saturate(0.85)"
  }
}
```

- 차트/지도 토큰은 각자 섹션 → 나중에 독립 선택(B)이 필요해져도 쪼갤 수 있음
- `ae_tokens.json`은 **default 테마**로 유지(하위호환 시드)

**시드 매핑**:
| 테마 id | 차트 theme_set | 지도 tile/overrides |
|---|---|---|
| `semoji` | gallery_infographic + outline_plus_hatch | bright + warm_earth |
| `modern_clean` | neutral_white | bright + clean_white |
| `dark_broadcast` | broadcast_signal | dark + matte_slate |

## 4. 적용 해석 (단일 지점)

**저장**:
- 프로젝트 전역: `scenes.json` 최상위 `"theme": "<id>"`
- 씬별 예외: 씬 객체 `"themeOverride": "<id>"`

**해석 우선순위**: `씬.themeOverride` → `프로젝트.theme` → `ae_tokens 기본값`

**단일 해석 지점**: 새 `backend/themes.py`
```python
list_themes() -> list[dict]                  # 카탈로그 목록(미리보기 메타 포함)
load_theme(theme_id) -> dict | None          # 카탈로그 단건
resolve_theme(proj_dir, scene=None) -> dict  # 우선순위 병합 → {colors, chart, map}
set_project_theme(proj_dir, theme_id)
set_scene_theme(proj_dir, scene_number, theme_id | None)
```
- `chartgen.gen_chart_spec`, `mapgen`(geo 라벨색·테마), `manifest`가 **전부 `resolve_theme` 경유**
- chartgen은 `resolve_theme`의 `chart`를, mapgen은 `map`을, 공유 색은 `colors`를 사용

## 5. 패널 UI

- 스토리보드 상단(설정 영역)에 **프로젝트 테마 드롭다운** — `/api/themes`로 카탈로그 로드,
  각 옵션에 차트 해칭+지도 색 **미니 미리보기**(시트 `_previewHTML` 재활용)
- 씬 도구상자에 **"🎨 씬 테마"** — 체크 씬에 `themeOverride` 지정/해제
- 테마 변경 시 차트/지도 사이드카는 다음 생성·컴프 때 `resolve_theme`로 재해석(즉시 강제 재생성은 안 함 — 무삭제 원칙)

**API**:
```
GET  /api/themes                      # 카탈로그 목록
POST /api/themes/set-project          # {project_id, theme_id}
POST /api/themes/set-scene            # {project_id, sceneNumber, theme_id|null}
POST /api/themes/research             # {project_id, image_paths[], label} → 신규 테마
```

## 6. 리서치 수집

- **시드**: `scripts/seed_themes.py` — chartagent theme_set 메타 + 지도 5종을 읽어 `themes/*.json` 3개 생성(멱등)
- **신규 추가**:
  1. 패널에서 참고 이미지 업로드(갤러리/파일) → `/api/themes/research`
  2. codex 비전(기존 adobe codex 경로)이 이미지 분석 → `{accent/text 색, 차트 패턴 성향, 지도 톤}` 추출
  3. 추출값을 가장 가까운 chartagent theme_set에 매핑 + 색/지도 오버라이드 생성
  4. 사용자가 라벨 지정 → `themes/<slug>.json` 저장(무삭제, 충돌 시 버전 접미사)

## 7. 테스트 / 마이그레이션

- `backend/themes.py`: `resolve_theme` 우선순위 단위테스트, `list/load/set` 테스트
- `/api/themes*` 라우트 테스트(set-project/set-scene/목록)
- 시드 스크립트 멱등성 테스트
- **하위호환**: 카탈로그·`theme` 필드가 없으면 기존 `ae_tokens` 동작 그대로(default 테마)
- chartgen/mapgen/manifest를 `resolve_theme` 경유로 수정(기존 동작 보존 회귀 테스트)

## 8. 범위 밖 (YAGNI)

- 전체 아트스타일(폰트/타이포/레이아웃) 테마화 — 차트/지도 검증 후
- 차트/지도 테마 독립 선택(B) — 통합 테마로 충분
- 테마 변경 시 기존 사이드카 일괄 강제 재생성 — 다음 생성 때 재해석으로 갈음
- line/pie/timeline 차트 레이아웃 — AE 레이아웃 추가 시
