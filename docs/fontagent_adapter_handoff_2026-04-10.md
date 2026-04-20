# FontAgent Adapter Handoff

대상 파일:
- `/Users/jleavens_macmini/Projects/auto_kairos_v3/auto_agent/modules/fontagent_adapter.py`

목표:
- `fontagent`는 범용 typography service로 유지한다.
- `auto_kairos_v3` 프로젝트 문맥 해석은 전부 adapter가 담당한다.
- `fontagent` CLI 계약, 특히 `recommend-use-case` 호출 방식과 JSON 출력 shape를 깨지 않는다.

현재 전제:
- `fontagent` 쪽에는 더 이상 project-specific inference가 없다.
- `prepare-font-system`은 명시적 `task` 또는 `use_case`를 받아야 한다.
- 따라서 adapter가 반드시 프로젝트 문맥을 읽어서 `task` / `use_case` / `tones`를 결정해야 한다.

## 유지해야 하는 FontAgent CLI 계약

### 1. 추천 호출

```bash
python3 -m fontagent.cli --root <FONTAGENT_ROOT> recommend-use-case \
  --medium <medium> \
  --surface <surface> \
  --role <role> \
  --tone <tone> \
  --language <language> \
  --count <n> \
  --commercial-use \
  --video-use \
  --detail compact
```

### 2. 출력 JSON shape

```json
{
  "request": {
    "medium": "video",
    "surface": "scene_overlay",
    "role": "title",
    "tones": ["knowledge", "clean"],
    "languages": ["ko"],
    "constraints": {
      "commercial_use": true,
      "video_use": true,
      "web_embedding": false,
      "redistribution": false
    }
  },
  "query": "video scene overlay title knowledge clean ko",
  "preview_preset": "title-ko",
  "results": [
    {
      "font_id": "example-font",
      "family": "Example Font",
      "source_site": "example_source",
      "score": 42
    }
  ]
}
```

### 3. adapter가 최소 기대하는 필드
- `font_id`
- `family`
- `source_site`
- `score`

## Adapter에서 구현할 것

### 1. 프로젝트 문맥 읽기
- project config
- `art_style.json`
- `scene_specs.json`
- 필요시 final manuscript / scene overlay 용도

위 파일을 읽어 아래를 결정한다.
- 대표 `use_case`
- 대표 `tones`
- `language`
- `medium`
- role별 `surface`

### 2. V3 전용 매핑 테이블 추가

예시:
- `iromism`, `quirky_cartoon`, `playful`, `cartoon` -> `knowledge-video-quirky-ko`
- `knowledge`, `documentary`, `clean`, `editorial`, `explainer` -> `knowledge-video-white-ko`
- 썸네일 중심 -> `youtube-thumbnail-ko`
- 자막 중심 -> `video-subtitle`

이 매핑은 adapter 내부 상수/함수로 둔다.

### 3. role별 추천 호출 분리

최소 role:
- `title`
- `subtitle`
- `body`

권장 surface:
- `title`: `scene_overlay` 또는 `thumbnail`
- `subtitle`: `subtitle_track`
- `body`: `body_copy` 또는 `scene_overlay`

프로젝트 성격에 따라 adapter가 고른다.

### 4. helper 함수 추가

권장 함수:
- `resolve_fontagent_context(project_dir) -> dict`
- `infer_fontagent_use_case(project_dir, art_style_payload, scene_specs_payload) -> dict`
- `recommend_role_font(role, context) -> dict | None`
- `recommend_fonts_for_video(...) -> dict`
- `fonts_to_design_preset(...) -> dict`

### 5. fallback 유지
- fontagent 호출 실패 시 기존 Pretendard fallback 유지
- 빈 결과도 안전하게 처리

### 6. prepare-font-system / typography-handoff 사용 시 명시적 입력 전달
- adapter가 결정한 `use_case` 또는 `task`를 넘긴다
- `fontagent`가 프로젝트 파일을 해석하게 하지 않는다

### 7. 출력 계약 유지
- `auto_kairos_v3` 내부 `DesignPreset.fonts` 형식 유지
- 기존 호출부가 깨지지 않게 `get_project_fonts()` 계열 진입점 호환 유지

## 권장 구현 순서

1. `fontagent_adapter.py`에 context resolver 추가
2. `art_style.json` / `scene_specs.json` -> `use_case` 매핑 함수 추가
3. `title/subtitle/body`별 `recommend-use-case` 호출 분리
4. 결과를 `DesignPreset.fonts`로 변환
5. fallback / 예외 처리 정리
6. 최소 테스트 추가

## 주의

- `fontagent` 내부 코드는 수정하지 말 것
- `recommend-use-case` CLI 인자와 JSON shape에 의존하되, 그 계약은 깨지 말 것
- project-specific path/field 해석은 adapter 책임으로 둘 것
- `fontagent`는 범용 서비스이고, V3-specific 해석은 adapter에만 둔다
