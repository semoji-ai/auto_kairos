# scene_specs 및 데이터 규칙

## 플랫 스키마
- 모든 필드는 최상위 (layout, motion, mood, headline, items 등)
- `visualization.creative` 중첩 구조 사용하지 않음
- `imageAsset.prompt`로 장면 묘사 (한글), 아트스타일 키워드 넣지 않음
- `imageAsset.source`를 반드시 존중 (search/generate)

## mapScene 좌표
- scene_specs: `[위도, 경도]` (LLM 자연 순서)
- Remotion/MapLibre: `[경도, 위도]` — build_manifest.py가 swap 담당
- **절대 프롬프트에서 [lng, lat] 순서를 강제하지 말 것**

## 이미지 파일 삭제 절대 금지
- 재생성/재검색 시 기존 파일 유지
- 새 이미지는 버전 번호로 생성 (`_gen_02`, `_gen_03`)
- `image_assets.json`의 `selected` 필드만 전환
- `rm -f scene_*.png` 같은 명령 **절대 금지**

## 디자인 시스템
- 단일 소스: `auto_agent/data/artstyle/styles/<style>.json`의 `design_tokens`
- TypeScript: `resolvePreset.ts` → `DesignPresetProvider`
- Python: `helpers.py` → `_load_design_tokens()` → `get_mood_color()`
- 하드코딩 색상 금지 — 프리셋에서 읽을 것

## 에이전트 턴 소진 방지
- 대용량 JSON 수정 시 **Edit 도구** 사용 (Write로 전체 재작성 금지)
- max_turns 부족 시 `agents.json` + CLI 하드코딩 양쪽 모두 수정

## 파일 추가 시 체크
- `pyproject.toml` package-data에 포함되는지 확인
- `.gitignore`에 의해 제외되지 않는지 확인
- 스킬 추가: .md 파일 + agents.json shared_skills + rule_manager.py RULE_MANIFEST
