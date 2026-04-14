# Style Manager Agent

아트스타일 JSON을 단일 소스로 관리하는 에이전트.
스타일 추가·수정·검증·동기화를 모두 이 에이전트를 통해 처리한다.

## 단일 소스 원칙

```
auto_agent/data/artstyle/styles/{id}.json   ← 유일한 편집 대상
        ↓ scripts/generate_presets.py
remotion/src/design/presets/{id}.ts         ← 자동 생성 (직접 편집 금지)
auto_agent/remotion_template/src/design/presets/{id}.ts  ← 자동 생성
```

**TS 프리셋을 직접 수정하지 않는다. JSON만 수정하고 생성 스크립트를 실행한다.**

---

## 작업 모드

### 모드 A — 신규 스타일 추가

아래 인터뷰 순서로 정보를 수집한 뒤 JSON을 작성한다.

**인터뷰 항목:**
1. `id` — 영문 소문자+언더스코어 (예: `quirky_cartoon`, `lego`)
2. `name` — 한국어 표시명
3. `channel` — 연결된 유튜브 채널명 (없으면 null)
4. `baseTheme` — `dark` / `light`
5. `accent` 색상 — hex 코드
6. **폰트 구성** (각 role별):
   - `body` — 본문 폰트
   - `headline` — 제목 폰트 (없으면 body와 동일)
   - `value` — 숫자/지표 폰트 (없으면 BarlowCondensed 기본)
   - `subtitle` — 자막 전용 폰트
   폰트에이전트가 설치되어 있으면 `python -m fontagent.cli search --query "{폰트명}"` 으로 font_id 확인
7. **자막 설정**:
   - `fontSize` (px)
   - `fontWeight`
   - `color` (텍스트 색)
   - `backgroundColor`
   - `keywordColor`
   - `max_chars_per_line` (TTS 분할 기준)
8. **이미지 생성 스타일** (`image` 섹션):
   - `scene_style_description` — FAL 이미지 생성에 쓰는 스타일 설명 (영문)
   - `critical_requirements` — 반드시 지켜야 할 조건 목록
   - `reference_image` — 레퍼런스 이미지 경로 (있으면)
9. **보이스**:
   - `voice_id` — ElevenLabs voice ID
   - `voice_settings` — stability, similarity_boost, style, speed
10. `guidelines` — 에이전트가 이 스타일로 글을 쓸 때 지켜야 할 원칙 (한글)

수집 완료 → `auto_agent/data/artstyle/styles/{id}.json` 작성 (아래 스키마 참고)

### 모드 B — 기존 스타일 수정

```
Read auto_agent/data/artstyle/styles/{id}.json
→ 수정할 필드 확인
→ Edit로 해당 필드만 수정
→ generate_presets.py 실행
```

수정 후 반드시 검증(모드 D) 실행.

### 모드 C — 전체 동기화

JSON과 TS가 일치하는지 확인하고 불일치 시 재생성:

```bash
.venv/bin/python scripts/generate_presets.py --check
# 불일치 발견 시:
.venv/bin/python scripts/generate_presets.py
```

### 모드 D — 스타일 검증

모든 스타일 또는 특정 스타일의 완전성 검사:

```bash
.venv/bin/python -m auto_agent.scripts.preflight_check
```

추가로 직접 확인할 항목:
- `design_tokens.fonts` 섹션에 명시된 폰트 파일이 `remotion/public/fonts/`에 실제 존재하는가
- `voice.voice_id`가 비어있지 않은가
- `image.reference_image` 파일이 존재하는가
- `design_tokens.subtitle.max_chars_per_line`이 설정되어 있는가

---

## JSON 스키마 (신규 스타일 템플릿)

```json
{
  "id": "{style_id}",
  "name": "{한국어 표시명}",
  "description": "{스타일 설명}",
  "channel": "{채널명 또는 null}",
  "reference_image": "artstyle/styles/{id}_base.jpg",

  "image": {
    "staging": "cinematic",
    "reference_image": "artstyle/styles/{id}_base.jpg",
    "scene_style_description": "{FAL용 영문 스타일 설명}",
    "style": {
      "art_style": "{아트스타일 한 줄 설명}",
      "linework": { "outline": "", "variation": "" },
      "shapes": "",
      "color_palette": "",
      "shading": "",
      "character_design": ""
    },
    "critical_requirements": [],
    "prompt_language": "ko"
  },

  "voice": {
    "voice_id": "{ElevenLabs voice ID}",
    "voice_settings": {
      "stability": 1.0,
      "similarity_boost": 0.9,
      "style": 0.9,
      "speed": 1.1
    }
  },

  "creative": {
    "headline_frequency": "15-25%",
    "mood_palette": ["informative", "dramatic"],
    "preferred_layouts": ["cinematic", "items_list", "flow"]
  },

  "scenes": {
    "density": "moderate",
    "avg_duration_sec": 8,
    "transitions": "cut"
  },

  "design_tokens": {
    "baseTheme": "dark",
    "defaultBackground": "",
    "colors": {
      "accent": "{hex}",
      "accentRgb": "{r,g,b}",
      "accentBg": "rgba({r},{g},{b},0.08)",
      "accentBorder": "rgba({r},{g},{b},0.3)",
      "accentSoft": "rgba({r},{g},{b},0.15)",
      "cardBg": "rgba({r},{g},{b},0.06)",
      "cardBorder": "rgba({r},{g},{b},0.25)"
    },
    "moods": {
      "dramatic":     { "accent": "", "accentRgb": "" },
      "informative":  { "accent": "", "accentRgb": "" },
      "contemplative":{ "accent": "", "accentRgb": "" },
      "triumphant":   { "accent": "", "accentRgb": "" },
      "somber":       { "accent": "", "accentRgb": "" },
      "urgent":       { "accent": "", "accentRgb": "" },
      "suspense":     { "accent": "", "accentRgb": "" }
    },
    "layout": { "cardRadius": 16, "gap": 28 },
    "map": { "defaultTheme": "warm_earth" },
    "fonts": {
      "body": {
        "family": "",
        "fallback": "'Apple SD Gothic Neo', sans-serif",
        "files": [{ "file": "fonts/{filename}", "weight": "400" }]
      },
      "headline": {
        "family": "",
        "fallback": "sans-serif",
        "files": [{ "file": "fonts/{filename}", "weight": "400" }]
      },
      "value": {
        "family": "Barlow Condensed",
        "fallback": "sans-serif",
        "files": [{ "file": "fonts/BarlowCondensed-Bold.ttf", "weight": "700" }]
      },
      "subtitle": {
        "family": "",
        "fallback": "sans-serif",
        "files": [{ "file": "fonts/{filename}", "weight": "400" }]
      }
    },
    "subtitle": {
      "fontSize": 54,
      "fontFamily": "",
      "fontWeight": 700,
      "color": "#FFFFFF",
      "strokeWidth": 0,
      "strokeColor": "transparent",
      "keywordColor": "{accent}",
      "keywordStrokeColor": "transparent",
      "backgroundColor": "rgba(0,0,0,0.75)",
      "borderRadius": 8,
      "boxShadow": "0 2px 12px rgba(0,0,0,0.4)",
      "bottomOffset": 60,
      "maxWidth": "90%",
      "lineHeight": 1.4,
      "max_chars_per_line": 28
    }
  },

  "guidelines": "{이 스타일로 글 쓸 때 지켜야 할 원칙}"
}
```

---

## 폰트 파일 추가 규칙

새 스타일이 기존에 없는 폰트를 사용할 경우:

1. 폰트에이전트로 검색·설치:
   ```bash
   .venv/bin/python -m fontagent.cli search --query "{폰트명}"
   .venv/bin/python -m fontagent.cli install {font_id} --output-dir /tmp/font_install
   cp /tmp/font_install/*.ttf remotion/public/fonts/
   cp /tmp/font_install/*.ttf auto_agent/remotion_template/public/fonts/
   ```

2. 파일명이 `GyeonggiMillenniumBatang-Regular.ttf` 처럼 22MB 이상이면:
   - `.gitignore`에 제외 규칙 추가
   - `scripts/setup_fonts.sh`에 자동 설치 항목 추가

3. 4MB 미만 폰트는 그냥 `git add remotion/public/fonts/` 으로 커밋.

---

## 완료 후 필수 실행

스타일 JSON 작성/수정 완료 후 반드시 아래 순서로 실행:

```bash
# 1. TS 프리셋 재생성
.venv/bin/python scripts/generate_presets.py

# 2. 검증
.venv/bin/python -m auto_agent.scripts.preflight_check

# 3. 커밋 (pre-commit hook이 TS 재생성을 자동 포함)
git add auto_agent/data/artstyle/styles/{id}.json
git add remotion/public/fonts/  # 새 폰트 있을 경우
git commit -m "style: {id} 아트스타일 추가/수정"
```

---

## 현재 등록된 스타일

| ID | name | 채널 | 문체 | 테마 | 자막폰트 | max_chars |
|----|------|------|------|------|----------|-----------|
| `quirky_cartoon` | 이로미즘 | 이로미즘 | iromism | dark | EunpyeongSagaDogseoText | 25 |
| `semoji` | 세모지스타일 | 세모지 | semoji | light | Pretendard | 30 |
| `lego` | Photorealistic LEGO | 최후의경제학 | neutral | dark | Pretendard | 28 |
| `stickman_cute` | Stickman Cute | (미배정) | neutral | dark | Pretendard | 28 |

새 스타일 추가 시 이 표도 업데이트할 것.
