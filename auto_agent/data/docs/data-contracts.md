# 에이전트 간 데이터 계약 (Data Contracts)

> 각 에이전트가 생성/소비하는 파일의 **JSON 스키마, 필수 필드, 검증 규칙**을 정의합니다.
>
> **v3.0** — 에이전트/스킬 분리 재구조화 반영 (11→6 LLM 에이전트)

---

## 파일 흐름 요약

```
research_report.json ──→ outline.json + final_manuscript.md
   (Research                  (Write Manuscript가
    Orchestrator)              아웃라인+원고 통합 생성)
                                       │
                          ┌────────────┼────────────┐
                          ▼            │            ▼
                   Fact Verifier       │    Character Planner
                   (교차 검증)          │    → character_plan.json
                                       │
                                       ▼
                              Visual Composer (4-in-1)
                              ├─ scene_decomposition.json
                              ├─ scene_specs.json
                              └─ motion_plan.json
                                       │
                    ┌──────────────┬────┴────┬────────────┐
                    ▼              ▼         ▼            ▼
              audio/         images/   characters/   subtitles/
                    │              │         │            │
                    └──────┬───────┴─────────┘            │
                           ▼                              │
                    manifest.json ←────────────────────────┘
                           │
                    qa_report_pre.json
                           │
                    final_video.mp4
                           │
                    qa_report_post.json
```

---

## 1. research_report.json

**생성자**: Research Orchestrator (리서치 + 합성 통합)
**소비자**: Write Manuscript (아웃라인+원고), Visual Composer (데이터 보강), Fact Verifier (검증), Character Planner (인물 정보)

```json
{
  "topic": "string (필수)",
  "summary": "string — executive summary 마크다운 (필수)",
  "key_figures": [
    {
      "name": "string (필수)",
      "role": "string",
      "relevance": "string",
      "quotes": ["string"]
    }
  ],
  "timeline": [
    {
      "date": "string — YYYY 또는 YYYY-MM (필수)",
      "event": "string (필수)",
      "significance": "string"
    }
  ],
  "statistics": [
    {
      "metric": "string (필수)",
      "value": "string | number (필수)",
      "unit": "string (필수)",
      "source": "string — source id (필수)",
      "year": "string",
      "context": "string"
    }
  ],
  "episodes": [
    {
      "title": "string (필수)",
      "content": "string — 핵심 내용 요약 (필수)",
      "narrative_draft": "string — 대본 수준 상세 서술 초안. 리서치 원문의 핵심 논점, 수치, 인용을 자연스러운 문장으로 풀어쓴 것. 200-500자 (필수)",
      "must_include": [
        {
          "fact": "string — 반드시 원고에 포함되어야 할 핵심 팩트/문장",
          "source": "string — source id",
          "reason": "string — 왜 중요한지"
        }
      ],
      "subtopic": "string",
      "sources": ["string — source ids"],
      "visual_hints": ["chart | quote | timeline | comparison | list | image"]
    }
  ],
  "comparisons": [
    {
      "subject_a": "string (필수)",
      "subject_b": "string (필수)",
      "dimensions": [
        {
          "dimension": "string (필수)",
          "a_value": "string (필수)",
          "b_value": "string (필수)"
        }
      ]
    }
  ],
  "sources": [
    {
      "id": "string — src_NNN (필수)",
      "title": "string (필수)",
      "url": "string",
      "author": "string",
      "date": "string",
      "quality_grade": "A | B | C | D (필수, E 제외)",
      "type": "academic | news | official | blog"
    }
  ],
  "source_grades": {
    "A": "number",
    "B": "number",
    "C": "number",
    "D": "number"
  },
  "raw_content": {
    "full_report_sections": ["string — 마크다운 섹션"],
    "total_word_count": "number"
  }
}
```

### 검증 규칙
- `topic`, `summary` 필수
- `statistics[].source`는 `sources[].id`와 매칭되어야 함
- `source_grades`에 E등급 없어야 함
- `episodes` 최소 3개
- `episodes[].narrative_draft` 200-500자 범위
- `episodes[].must_include` 에피소드당 최소 1개

---

## 2. outline.json

**생성자**: Write Manuscript (Phase 1: 아웃라인 설계)
**소비자**: Write Manuscript (Phase 2: 원고 작성), Visual Composer (씬 타입 힌트 참조)

```json
{
  "title": "string (필수)",
  "estimated_duration_sec": "number — 300-900 (필수)",
  "total_scenes_estimate": "number — 70-100 (필수)",
  "structure": {
    "act_1": "string — 도입부 설명",
    "act_2": "string — 전개부 설명",
    "act_3": "string — 결말부 설명"
  },
  "chapters": [
    {
      "chapter_number": "number (필수)",
      "title": "string (필수)",
      "act": "1 | 2 | 3 (필수)",
      "purpose": "string (필수)",
      "duration_ratio": "number — 0.0-1.0 (필수)",
      "key_points": ["string"],
      "episodes": ["string — episode ids"],
      "scene_hints": [
        {
          "type": "string — 19개 씬 타입 중 (필수)",
          "icon": "string — Lucide 아이콘명",
          "data_needed": "boolean",
          "concepts": ["string"],
          "metric": "string",
          "note": "string"
        }
      ],
      "image_scenes": [
        {
          "type": "image_scene",
          "subject": "string (필수)",
          "reason": "string (필수)",
          "source_hint": "wikimedia | search | generate (필수)"
        }
      ]
    }
  ],
  "flow_notes": {
    "hooks": "string",
    "pacing": "string",
    "transitions": "string"
  }
}
```

### 검증 규칙
- `chapters` 최소 4개, 최대 8개
- `duration_ratio` 합계 = 1.0 (±0.02 오차 허용)
- `scene_hints[].type`은 유효한 19개 타입 중 하나
- 같은 `scene_hints.type` 연속 배치 지양

---

## 3. final_manuscript.md

**생성자**: Write Manuscript (Phase 2: 원고 작성)
**소비자**: Fact Verifier (교차 검증), Visual Composer (씬 분할), Character Planner (인물 추출)

### 포맷 규칙
- 마크다운
- 챕터: `# Ch{N}. 챕터 제목`
- 씬: `## Scene {N}: 씬 제목`
- VIZ 마커: `[VIZ:타입 key=value]` (씬 시작)
- IMG 마커: `[IMG:소스 subject=대상 query=검색어]` (이미지 필요 시)
- 나레이션 텍스트: 마커 다음 줄부터

### 검증 규칙
- 모든 씬에 `[VIZ:...]` 마커 존재
- 마커 없는 텍스트 블록 없음
- 챕터 수 = outline.json의 chapters 수

---

## 4. scene_decomposition.json

**생성자**: Visual Composer (Phase 1: 씬 분할)
**소비자**: Visual Composer (Phase 2: Creative Direction — 같은 에이전트 내부 연결)

```json
{
  "total_scenes": "number (필수)",
  "total_chapters": "number (필수)",
  "image_scene_count": "number (필수)",
  "image_ratio": "number — 0.0-0.3 (필수)",
  "scenes": [
    {
      "scene_number": "number — 1부터 연속 (필수)",
      "chapter": "number (필수)",
      "title": "string (필수)",
      "narration": "string (필수)",
      "narration_char_count": "number (필수)",
      "estimated_duration_sec": "number (필수)",
      "has_image_asset": "boolean (필수)",
      "image_asset": {
        "type": "portrait | screenshot | photo | viz_background | asset | null",
        "subject": "string",
        "source_hint": "wikimedia | search | generate",
        "search_query": "string",
        "reason": "string",
        "fallback": "string"
      },
      "viz_marker": "string — [VIZ:...] 원본",
      "data_dependencies": ["string — statistics.{metric}"],
      "notes": "string"
    }
  ],
  "density_check": {
    "scenes_split": "number — 과밀로 분할된 원본 씬 수 (필수)",
    "original_scene_count": "number — 분할 전 씬 수 (필수)",
    "final_scene_count": "number — 분할 후 최종 씬 수 (필수)",
    "split_details": [
      {
        "original_scene": "number — 분할된 원본 씬 번호",
        "split_into": ["number — 분할 결과 씬 번호들"],
        "reason": "string — 분할 사유 (전환어, 인물 수, 시간/장소 전환, 글자 수 초과)"
      }
    ]
  }
}
```

### 검증 규칙
- `scene_number` 1부터 연속
- `image_ratio` ≤ 0.3
- `density_check` 필수. `final_scene_count` = `total_scenes`
- `narration_char_count` ≤ 100자 (범용 상한, 초과 시 분할)

---

## 5. scene_specs.json

**생성자**: Visual Composer (Phase 2: Creative Direction + Phase 3: 데이터 보강)
**소비자**: TTS 모듈 (나레이션 전처리), TTS Generator, Image Generator, QA Reviewer, Manifest Builder

```json
{
  "version": "4.0",
  "theme": "simple",
  "total_scenes": "number (필수)",
  "scenes": [
    {
      "sceneNumber": "number (필수)",
      "chapter": "number (필수)",
      "title": "string (필수)",
      "narration": "string — 원본 나레이션 (필수)",
      "narration_tts": "string — TTS 전처리된 나레이션 (tts-preprocess 모듈 후 추가)",
      "tts_changes": [
        {
          "original": "string",
          "converted": "string",
          "rule": "string"
        }
      ],
      "durationFrames": "number — 120-600 (필수)",
      "visualization": {
        "title": "string",
        "items": ["string"],
        "values": ["number"],
        "unit": "string",
        "source": "string",
        "creative": {
          "concept": "string — 시각 연출 의도 (필수)",
          "reveal": "string — 정보 공개 패턴 (필수)",
          "emphasis": "string — 핵심 강조 요소 (필수)",
          "headline": "string — 화면 표시 텍스트, {{accent}} 마크업 (필수)",
          "mood": "string — 감정적 톤 (필수)"
        }
      },
      "vizAnimation": {
        "stagger": "number",
        "itemDuration": "number",
        "easing": "string",
        "backgroundPattern": "dots | grid | lines | none",
        "backgroundOpacity": "number — 0.01-0.03"
      },
      "transition": {
        "type": "fade | slide | wipe (필수)",
        "direction": "left | right (slide/wipe일 때)",
        "durationFrames": "number — 10-20 (필수)"
      },
      "imageAsset": {
        "source": "wikimedia | search | generate | character | null",
        "query": "string",
        "subject": "string",
        "placement": "background | center | left | right | inline",
        "opacity": "number",
        "overlay": "boolean",
        "usage": "asset | background",
        "characters": ["string"],
        "license": "string | null"
      },
      "enrichment": {
        "status": "verified | adjusted | unverified",
        "original_values": [],
        "corrected_values": [],
        "source_matched": "string",
        "notes": "string"
      },
      "mapScene": {
        "mapType": "location_reveal | route_animation | territory_overlay | fly_through",
        "mapStyle": "modern_clean | historical | dark_cyber | satellite",
        "title": "string",
        "source": "string",
        "camera": { "keyframes": [], "easing": "string" },
        "markers": [],
        "route": {},
        "territories": [],
        "labels": []
      }
    }
  ]
}
```

### 검증 규칙
- `durationFrames` 120-600 범위
- `transition.type` 같은 타입 3회 연속 금지
- `visualization.creative` 필수 (모든 씬에)
- `visualization.creative.reveal` 같은 값 3회 연속 금지
- `map_scene`은 `visualization` 대신 `mapScene` 필드 사용 (둘 중 하나는 반드시 존재)
- `narration_tts`는 tts-preprocess 모듈 실행 이후에만 존재

---

## 6. motion_plan.json

**생성자**: Visual Composer (Phase 4: 모션 설계)
**소비자**: Manifest Builder, Video Assembler

```json
{
  "total_duration_frames": "number (필수)",
  "total_duration_sec": "number (필수)",
  "fps": 30,
  "transition_series": [
    {
      "scene_number": "number (필수)",
      "scene_type": "string (필수)",
      "duration_frames": "number (필수)",
      "transition_in": {
        "type": "fade | slide | wipe (필수)",
        "duration_frames": "number (필수)",
        "params": {}
      },
      "transition_out": {
        "type": "fade | slide | wipe (필수)",
        "duration_frames": "number (필수)",
        "params": {}
      },
      "internal_timing": {
        "content_start": "number (필수)",
        "content_end": "number (필수)",
        "hold_duration": "number — ≥90 (필수)"
      }
    }
  ],
  "rhythm_analysis": {
    "avg_scene_duration_sec": "number",
    "breathing_points": ["number — scene numbers"],
    "intensity_curve": [
      {
        "scene_range": ["number", "number"],
        "intensity": "low | medium | high",
        "note": "string"
      }
    ],
    "warnings": [
      {
        "type": "string",
        "scenes": ["number"],
        "scene_type": "string",
        "suggestion": "string"
      }
    ]
  },
  "global_settings": {
    "default_spring": { "damping": "number — ≥150", "stiffness": "number" },
    "min_scene_duration_frames": 120,
    "max_scene_duration_frames": 600,
    "transition_overlap_frames": "number"
  }
}
```

### 검증 규칙
- `hold_duration` ≥ 90 프레임
- `default_spring.damping` ≥ 150
- 같은 전환 타입 3회 연속 없음
- `breathing_points` 3-5씬 간격

---

## 7. factcheck_report.json

**생성자**: Fact Verifier
**소비자**: Pipeline Controller (참고용, blocking 아님)

```json
{
  "total_claims": "number",
  "verified": "number",
  "adjusted": "number",
  "unverified": "number",
  "claims": [
    {
      "id": "string — claim_NNN",
      "text": "string — 원문 주장",
      "scene": "number",
      "type": "statistic | quote | date | comparison | ranking",
      "verdict": "verified | adjusted | unverified",
      "confidence": "high | medium | low",
      "sources": [{ "id": "string", "title": "string", "url": "string", "matches": "boolean" }],
      "original": "string (adjusted일 때)",
      "corrected": "string (adjusted일 때)",
      "notes": "string"
    }
  ],
  "summary": {
    "accuracy_score": "number — 0.0-1.0",
    "critical_issues": "number",
    "recommendations": ["string"]
  }
}
```

---

## 8. qa_report_pre.json / qa_report_post.json

**생성자**: QA Reviewer
**소비자**: Pipeline Controller, 사용자

```json
{
  "phase": "pre_render | post_render",
  "timestamp": "string — ISO 8601",
  "overall_score": "number — 0-100",
  "pass": "boolean",
  "issues": [
    {
      "id": "string — QA-NNN",
      "severity": "critical | warning | info",
      "category": "string",
      "scene": "number | null",
      "description": "string",
      "suggestion": "string",
      "auto_fixable": "boolean"
    }
  ],
  "stats": {
    "total_scenes": "number",
    "scenes_checked": "number",
    "critical_count": "number",
    "warning_count": "number",
    "info_count": "number",
    "auto_fixed": "number"
  }
}
```

### Gate 규칙
- 사전 검수: `critical_count == 0` → `pass: true`
- 사후 검수: 리포트 생성만 (gate 아님, 사용자 알림)

---

## 9. art_style.json

**생성자**: 사용자 또는 파이프라인 시작 시 자동 결정
**소비자**: Character Planner, Visual Composer, Image Generator

```json
{
  "name": "string — 스타일 이름 (예: Quirky Cartoon, Cinematic Realism)",
  "description": "string — 스타일 설명",
  "reference_image": "string — IP-Adapter 스타일 베이스 이미지 경로",
  "staging_mode": "cinematic | flat",
  "style": {
    "art_style": "string — 시각적 스타일 묘사",
    "linework": {
      "outline": "string",
      "variation": "string"
    },
    "shapes": "string — 비율/기하학",
    "color_palette": "string — 색상 사양",
    "shading": "string — 음영/조명",
    "character_design": "string — 캐릭터 특성",
    "mood_and_tone": "string — 분위기",
    "background": "string — 배경 처리"
  },
  "technical": {
    "no_text": "boolean — true (기본)",
    "resolution": "string",
    "scene_style": "string — 씬 프롬프트에 삽입될 스타일 요약"
  },
  "historical_period": "string | null — 시대 고증 (선택, 예: 조선시대 15세기)"
}
```

**위치**: 프로젝트 루트 `art_style.json` (또는 `output/{project}/art_style.json` 폴백)
**프리셋**: `.claude/art_styles/*.json`

---

## 10. character_plan.json

**생성자**: Character Planner
**소비자**: Image Generator (scripts/generate_images.py), Visual Composer (캐릭터 이미지 경로 참조)

```json
{
  "characters": [
    {
      "name": "string — 인물명 (필수)",
      "name_en": "string — English Name (필수)",
      "is_real_person": "boolean (필수)",
      "person_photo": "string | null — characters/ref_photos/name_ref.jpg",
      "variants": [
        {
          "variant_id": "string — name_context (필수)",
          "label": "string — 맥락 레이블 (필수)",
          "scenes": ["number — 등장 씬 번호들 (필수)"],
          "visual_guide": {
            "clothing": "string",
            "hair": "string",
            "expression": "string",
            "distinctive_features": "string"
          },
          "prompt_base": "string — 캐릭터 생성 프롬프트 (영어, 필수)",
          "output": "string — characters/variant_id.png (필수)"
        }
      ]
    }
  ],
  "summary": {
    "total_characters": "number",
    "total_variants": "number",
    "real_persons": "number",
    "fictional": "number"
  }
}
```

### 검증 규칙
- 모든 캐릭터의 `scenes` 길이 ≥ 2 (2씬 미만 등장 캐릭터는 포함하지 않음)
- `variant_id`는 프로젝트 내 고유
- `name_en` 필수 (FAL 프롬프트, Wikipedia 검색용)

---

## 11. character_casting.json

**생성자**: Image Generator (src/skills/image_gen.py)
**소비자**: Visual Composer, Image Generator (씬 생성 시 IP-Adapter 참조)

```json
{
  "characters": [
    {
      "name": "string — 인물명 (필수)",
      "is_real_person": "boolean",
      "person_photo": "string | null — 참조 사진 경로",
      "variants": [
        {
          "variant_id": "string (필수)",
          "context": "string — 맥락 설명",
          "image": "string | null — 생성된 캐릭터 이미지 경로",
          "scenes": ["number — 등장 씬 번호들"]
        }
      ]
    }
  ]
}
```

---

## 12. 에셋 파일 규약

### 프로젝트 디렉토리 구조

모든 생성 에셋은 `output/{project_name}/` 하위에 저장된다.
프로젝트명 결정 우선순위: `--project` CLI → `PROJECT_NAME` 환경변수 → 자동감지 → scene_specs.json theme.
공통 유틸리티: `scripts/project_paths.py` → `get_project_dir()`

```
output/{project_name}/
├── audio/                     ← TTS 오디오
│   ├── scene_001.mp3
│   └── scene_002.mp3
├── subtitles/                 ← 자막
│   ├── scene_001.srt
│   └── scene_002.srt
├── images/                    ← 씬 이미지
│   ├── scene_005.png
│   └── viz_bg/                ← 시각화 배경
│       └── scene_008_bg.png
├── characters/                ← 캐릭터 이미지
│   ├── danjong_king.png
│   └── ref_photos/            ← 실존 인물 참조 사진
│       └── andrew_ng_ref.jpg
├── tts_results.json           ← TTS 결과 메타데이터
├── subtitles.json             ← 자막 집계 메타데이터
├── character_casting.json     ← 캐릭터 캐스팅 (image_gen 생성)
├── image_licenses.json        ← 이미지 라이선스 기록
├── image_gen_results.json     ← 이미지 생성 결과 요약
├── validation_report.json     ← 데이터 검증 결과
├── qa_report_pre.json         ← 사전 검수 결과
├── qa_report_post.json        ← 사후 검수 결과
└── final_video.mp4            ← 최종 렌더링 영상
```

파이프라인 설정 파일(scene_specs.json, outline.json 등)은 **프로젝트 루트**에 위치한다.

### 오디오
```
output/{project}/audio/scene_001.mp3
output/{project}/audio/scene_002.mp3
...
포맷: MP3, 44.1kHz, 128kbps
네이밍: scene_{NNN} (3자리 zero-padded)
```

### 자막
```
output/{project}/subtitles/scene_001.srt
output/{project}/subtitles/scene_002.srt
...
포맷: SRT (SubRip), UTF-8
```

### 이미지
```
output/{project}/images/scene_005.png         ← 씬 이미지 (에셋/검색/생성)
output/{project}/images/scene_012.png
output/{project}/images/viz_bg/               ← 시각화 배경 이미지
  scene_008_bg.png
  scene_015_bg.png
...
포맷: PNG, 최소 960x540, 권장 1920x1080
네이밍: scene_{NNN} (해당 씬 번호)
```

### 캐릭터
```
output/{project}/characters/                  ← 생성된 캐릭터 이미지
  danjong_king.png
  danjong_exile.png
  suyang_general.png
output/{project}/characters/ref_photos/       ← 실존 인물 참조 사진 (Wikipedia 등)
  andrew_ng_ref.jpg
  ...
character_plan.json          ← 캐릭터 계획 (프로젝트 루트, character-planner 생성)
포맷: PNG, 1:1 비율 권장
```

### 라이선스
```
output/{project}/image_licenses.json
[
  {
    "scene": "scene_005",
    "source_url": "https://commons.wikimedia.org/...",
    "source": "wikimedia",
    "license": "CC-BY-SA-4.0",
    "title": "이미지 제목"
  }
]
```

---

## 렌더링 방식

v4.0에서는 rigid한 타입 매핑이 폐지되었습니다.
모든 시각화는 **creative 필드 + 데이터 구조**로 자동 결정됩니다.
렌더러(CreativeScene)가 reveal, emphasis, mood, headline, items/values 패턴을 분석하여 최적의 레이아웃을 선택합니다.

### 특수 씬 유형
```
map_scene → mapScene 필드 사용 (visualization 대신)
narration_only → visualization 없음
image_scene → 외부 이미지 전용
```

### art_style.json 제공 방식

`art_style.json`은 **사용자 제공 설정 파일**이다 (파이프라인이 자동 생성하지 않음).
- 위치: 프로젝트 루트 `art_style.json`
- 프리셋: `.claude/art_styles/*.json`
- 없을 경우: 이미지 생성에서 기본 스타일 적용, 캐릭터 생성 시 스타일 참조 생략

---

## v3.0 → v4.0 변경 요약

| 변경 항목 | v3.0 | v4.0 | 변경 사유 |
|----------|------|------|----------|
| scene_decomposition.json | scene_type (19개 rigid) | 분류 필드 제거 (순수 분할만) | Creative Direction 도입 |
| scene_specs.json | sceneType 필드 | 제거 (creative 필드로 대체) | rigid 매핑 폐지 |
| visualization | rigid 타입 필드만 | creative 필드 필수 (자동 레이아웃) | 씬별 창의적 연출 지원 |
| 렌더링 방식 | 19개 타입 1:1 매핑 | creative 필드 + 데이터 구조 자동 감지 | 다양한 시각 표현 |
| version | "3.0" | "4.0" | Creative Direction 스키마 |
| theme | "kairos" | "simple" | SimpleVideo 기본 |
| shared skill | scene-types.md | scene-segmentation.md + creative-direction.md | 분리 |

### v2.0 → v3.0 변경 요약

| 데이터 파일 | v2.0 생성자 | v3.0 생성자 | 변경 사유 |
|------------|-----------|-----------|----------|
| research_report.json | Research Synthesizer (A6) | Research Orchestrator | 리서치+합성 통합 |
| outline.json | Outline Builder (B1) | Write Manuscript (Phase 1) | 아웃라인+원고 통합 |
| final_manuscript.md | Manuscript Writer (B2) | Write Manuscript (Phase 2) | 아웃라인+원고 통합 |
| scene_decomposition.json | Scene Decomposer (C1) | Visual Composer (Phase 1) | 4-in-1 통합 |
| scene_specs.json | Visual Composer→Data Enricher→TTS Preproc | Visual Composer (Phase 2+3) | 4-in-1 통합 |
| motion_plan.json | Motion Choreographer (C4) | Visual Composer (Phase 4) | 4-in-1 통합 |
| character_plan.json | Character Planner | Character Planner (변경 없음) | 입력만 변경 |
| factcheck_report.json | Fact Verifier | Fact Verifier (변경 없음) | — |
