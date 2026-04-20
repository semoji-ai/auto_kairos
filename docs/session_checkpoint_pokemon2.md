# 세션 체크포인트 — 포켓몬스터 30주년 브랜드백과사전 2편
> 저장일: 2026-04-20
> 재개 시 이 파일을 읽고 작업 이어가기

---

## 프로젝트 경로
```
output/bd0b7143_포켓몬스터_30주년_브랜드백과사전_2편/
```

---

## 완료된 작업

### 1. 씬 이미지 검색 쿼리 개선
- `scene_specs.json`의 ❌ 씬들에 영어 구체적 쿼리 추가
- `image_batch_module.py` 스킵 로직: 파일 존재 → `image_assets.has_search_version()` 기반으로 변경
- `image_assets.py`에 `has_search_version()` 함수 추가

### 2. chartagent artstyle 자동 연결 시스템화
- `chart_batch_module.py` 수정:
  - `meta.artStyle` 또는 `meta.art_style` 파싱 (경로 → 파일명 stem 추출)
  - DB fallback: `ProjectManager.get_project(slug=slug)` (keyword 인자 필수!)
  - 기본값: "semoji"
- `scene_specs.json`에 meta 추가:
  ```json
  "meta": {
    "artStyle": "artstyle/styles/semoji_3D.json"
  }
  ```
- `assembly-director/SKILL.md`에 Phase B-2b (차트 디자인 명세서 생성) 추가

### 3. 씬67 바 차트 바 시작점 불일치 버그 수정
**파일:** `remotion/src/simple/CreativeScene.tsx` + `auto_agent/remotion_template/src/simple/CreativeScene.tsx`

**원인:** `BarDisplay` 컴포넌트에서 레이블 div가 `minWidth: L.barLabelWidth`로 되어 있어
텍스트가 길면 그 행의 레이블 영역이 넓어져 바 시작점이 밀림.

**수정:** 동적 `labelWidth` 계산 + `width: labelWidth` 고정
```tsx
// hasNegative 선언 직후에 추가
const _fs = typeof T.labelText === "number" ? T.labelText : parseInt(String(T.labelText)) || 16;
const labelWidth = Math.max(
  ...items.map(it =>
    [...it].reduce((s, c) => s + (c.charCodeAt(0) > 0x7f ? _fs : _fs * 0.6), 0)
  ),
  L.barLabelWidth,
) + 12;

// 레이블 div: minWidth → width
style={{ width: labelWidth, textAlign: "right", ... whiteSpace: "nowrap" }}
```
**위치:** CreativeScene.tsx 약 2204번줄 (`_fs` / `labelWidth` 계산), 2320번줄 (width 적용)

### 4. 씬66 MetricCard 숫자 줄바꿈 버그 수정
**파일:** `remotion/src/simple/BuildingBlocks.tsx` + `auto_agent/remotion_template/src/simple/BuildingBlocks.tsx`

**원인:** MetricCard value div가 `fontSize: 100` 고정 + `whiteSpace` 없음 → 긴 숫자 줄바꿈

**수정:** 동적 폰트 크기 + 줄바꿈 방지
```tsx
// BuildingBlocks.tsx MetricCard 컴포넌트 value div (~958번줄)
fontSize: Math.max(48, Math.min(100, Math.floor(600 / Math.max(value.length, 6)))),
whiteSpace: "nowrap",
```

---

## 이미지 현황 (image_assets.json 등록 씬)

등록 완료 (25개): [2, 5, 6, 11, 12, 15, 20, 22, 23, 33, 34, 35, 37, 38, 39, 44, 45, 48, 51, 52, 58, 62, 63, 66, 82]

- 씬37: 씬34 이미지 재활용 (`search/scene_034_search_01.jpg`)
- 씬01, 03, 10: `source: "generate"` (fal-client 필요)
- 씬41, 65, 67, 70, 73: `source: "none"` (데이터씬 — 이미지 불필요)

## 사용자 확인 대기 씬 (△)
- 씬12 (두 아이 공원)
- 씬22 (인터뷰 스튜디오)
- 씬48 (개구리 피규어)
- 씬52 (Nintendo Switch 로고)
- 씬66 (Logic 래퍼)

---

## 미완료 작업

### [우선순위 높음]
1. **fal-client 설치 후 generate 씬 이미지 생성**
   - 씬01, 03, 10 포함 source=generate 씬들
   - `pip install fal-client` 또는 requirements 확인 필요

2. **매니페스트 재빌드**
   - 차트 디자인 명세서 반영 후 매니페스트 재빌드 필요
   ```bash
   cd ~/Projects/auto_kairos_v3
   python3 -m auto_agent.modules.build_manifest --project 포켓몬스터_30주년_브랜드백과사전_2편
   ```

### [확인 필요]
3. 씬67 차트 시각적 확인 (바 시작점 정렬 수정 후)
4. 씬66 MetricCard 숫자 표시 확인 (줄바꿈 수정 후)

---

## 핵심 기술 메모

### image_assets.json 동작 방식
- 파일시스템 자동 스캔으로 파일이 있으면 복원됨
- 재검색 트리거는 `has_search_version()` 등록 여부로 판단
- 파일 삭제 절대 금지 — `.bak` 리네임 사용

### chart_batch_module 아트스타일 연결 우선순위
1. `scene_specs.meta.artStyle` 또는 `meta.art_style`
2. ProjectDB config의 `art_style`/`artstyle`
3. 기본값 "semoji"

### ProjectManager 주의사항
```python
# 올바름 (keyword 인자)
proj = pm.get_project(slug=slug)
# 틀림 (positional → project_id로 처리됨)
proj = pm.get_project(slug)
```

### Remotion 양쪽 동기화 필수
- `remotion/src/` 수정 시 → `auto_agent/remotion_template/src/` 동일 적용
- Vite 빌드 2종 필수:
  ```bash
  cd remotion
  node node_modules/vite/bin/vite.js build --config vite.thumb.config.ts
  node node_modules/vite/bin/vite.js build --config vite.editor.config.ts
  ```
