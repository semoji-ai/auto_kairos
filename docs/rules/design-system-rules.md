# 디자인 시스템 설정 일원화 규칙

> 스타일 관련 설정은 반드시 아래 **단일 소스**에서만 변경하세요.
> 여러 곳을 수정하면 혼선이 발생합니다.

---

## 1. 레이아웃 스타일 (ItemsList, ItemsGrid 등 컴포넌트 변형)

**단일 소스: `ComponentVariants` (variant 시스템)**

| 설정 위치 | 파일 |
|-----------|------|
| **기본값** | `auto_agent/remotion_template/src/design/defaults.ts` — `variants` 섹션 |
| **스타일별 오버라이드** | `auto_agent/data/artstyle/styles/<style>.json` — `design_tokens.variants` |
| **TypeScript 타입** | `auto_agent/remotion_template/src/design/types.ts` — `ComponentVariants` |

**규칙:**
- `ItemsList` 스타일 변경 → `variants.itemsList: "default" | "accent-filled"`
- `ItemsGrid` 스타일 변경 → `variants.itemsGrid: "default" | "accent-filled"`
- 컴포넌트 내부에서 `const V = usePresetVariants()` 로 읽음
- **절대로 컴포넌트 내부에 하드코딩하지 말 것**

**JSON 수정 후 필수 실행:**
```bash
python3 scripts/generate_presets.py <style_id>
cd remotion && node node_modules/vite/bin/vite.js build --config vite.thumb.config.ts && node node_modules/vite/bin/vite.js build --config vite.editor.config.ts
```

---

## 2. 색상/테마 설정

**단일 소스: `PresetColors`**

| 설정 위치 | 파일 |
|-----------|------|
| **기본 다크 테마** | `auto_agent/remotion_template/src/design/defaults.ts` — `colors` 섹션 |
| **기본 라이트 테마** | `auto_agent/remotion_template/src/design/defaults.ts` — `WHITE_OVERRIDE` |
| **스타일별 accent 색상** | `auto_agent/data/artstyle/styles/<style>.json` — `design_tokens.colors` |
| **무드별 색상** | `auto_agent/data/artstyle/styles/<style>.json` — `design_tokens.moods` |

**규칙:**
- `bg`, `text` 등 기본 색상은 `baseTheme: "dark" | "light"` 에서 자동 결정
- accent 계열만 artstyle JSON에서 오버라이드
- Python 에이전트는 `helpers.py` → `get_mood_color()` 로 읽음

---

## 3. 폰트 설정

**단일 소스: `PresetFonts`**

| 설정 위치 | 파일 |
|-----------|------|
| **기본 폰트** | `auto_agent/remotion_template/src/design/defaults.ts` — `fonts` 섹션 |
| **스타일별 폰트** | `auto_agent/data/artstyle/styles/<style>.json` — `design_tokens.fonts` |

**폰트 역할:**
- `body` — 본문 전반
- `headline` — 헤드라인/타이틀 전용
- `value` — 숫자/지표 전용
- `subtitle` — 자막 전용
- `mono` — 장식 따옴표 등

**JSON 수정 후 필수 실행:**  
`generate_presets.py` + Vite 빌드 (위와 동일)

---

## 4. 타이포그래피 크기

**단일 소스: `PresetTypography`**

| 설정 위치 | 파일 |
|-----------|------|
| **기본 크기** | `auto_agent/remotion_template/src/design/defaults.ts` — `typography` 섹션 |
| **스타일별 오버라이드** | artstyle JSON `design_tokens.typography` (현재 대부분 기본값 사용) |

---

## 5. 차트 스타일 (ChartAgent)

**단일 소스: `chartagent` 섹션**

| 설정 위치 | 파일 |
|-----------|------|
| **스타일별 차트 테마** | `auto_agent/data/artstyle/styles/<style>.json` — `design_tokens.chartagent` |

**설정 예시:**
```json
"chartagent": {
  "theme_set": "gallery_infographic",
  "theme_overrides": { "pattern_mode": "outline_plus_hatch" }
}
```

---

## 6. 배경/텍스처

**단일 소스: `DesignPreset` 루트 필드**

| 설정 위치 | 파일 |
|-----------|------|
| **기본 배경 이미지** | artstyle JSON `design_tokens.defaultBackground` |
| **배경 오퍼시티** | artstyle JSON `design_tokens.defaultBgOpacity` |
| **텍스처 오버레이** | artstyle JSON `design_tokens.texture` |

---

## 7. 애니메이션/등장 효과

**단일 소스: `PresetAnimation` + `defaultItemEntrance`**

| 설정 위치 | 파일 |
|-----------|------|
| **기본 아이템 등장** | artstyle JSON `design_tokens.defaultItemEntrance` |
| **전역 애니메이션 속도** | artstyle JSON `design_tokens.animation` |

---

## 요약: 스타일 추가/변경 시 체크리스트

1. **TypeScript 타입** 추가 필요하면 → `types.ts` (양쪽 동기화)
2. **기본값** → `defaults.ts`
3. **스타일별 오버라이드** → `artstyle/styles/<style>.json`의 `design_tokens`
4. **generate_presets.py** 지원 추가 (필요 시)
5. `python3 scripts/generate_presets.py` 실행
6. Vite 빌드 2종 실행
7. `remotion/src/` ↔ `auto_agent/remotion_template/src/` 양쪽 동기화 확인
