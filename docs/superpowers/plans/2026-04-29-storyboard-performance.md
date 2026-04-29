# Storyboard 성능 개선 계획

작성일: 2026-04-29
보고: 사용자 (대시보드 사용 중 발생)
대상: `auto_agent/dashboard/static/scene-editor.js`, `auto_agent/dashboard/templates/partials/_storyboard.html`

---

## 목표

스토리보드 탭 진입 시 **첫 페인트 < 1초**, 메인 스레드 점유 0초, 서버 동시 요청 ≤ 10개.

## 6개 이슈 (원인 → 해결)

### 1. JS 번들 매번 재다운로드 (14MB)
- **원인**: 캐시버스터가 `{{ range(100000)|random }}` — 매 로드마다 다른 번호
- **해결**: 파일 mtime을 버전 번호로 사용 (`{{ static_file('...') | mtime }}` 헬퍼)
- **영향**: 14MB → 0 (브라우저 캐시 히트)
- **난이도**: 매우 쉬움 (helper 한 개 + 템플릿 1줄)

### 2. 후보 이미지 API 풀 응답 큼
- **원인**: `loadAllImageGrids()`가 후보 이미지 API까지 페이지 로드 시 호출. 응답에 다른 씬 후보까지 포함
- **해결**: "후보 ▼" 버튼 클릭 시 해당 씬 1건만 lazy fetch. 한 번 로드 후 캐시
- **난이도**: 쉬움

### 3. "다른 비디오" 드롭다운 항상 펼침
- **원인**: 인라인 `display:none` + `display:flex` 동시 선언 → flex가 덮어씀. 토글 로직도 `''`(빈값)으로 복원
- **해결**: 초기 `display:none` 단일 선언. 토글은 `none ↔ flex` 명확히
- **난이도**: 매우 쉬움

### 4. 이미지 버전 전체 항상 노출
- **원인**: 모든 버전을 한 번에 렌더. 접힘 없음. 선택 후 자동 닫기 없음
- **해결**: 현재 선택만 노출 + "다른 이미지 N개 ▾" 접기. 선택/드래그앤드롭 시 자동 close
- **난이도**: 쉬움

### 5. 🔴 `<video>` 요소 810개 동시 생성
- **진짜 원인**: 단순히 video 요소 형식 문제가 아니라 **"다른 비디오 N개" 드롭다운이 모든 비디오를 한 번에 렌더**.
  - `_storyboard.html:1088` — `fetch('.../editor/videos')`가 프로젝트 전체 비디오(45개) 반환
  - `_storyboard.html:1100` — `otherVideos = videos.filter(v => v.file !== currentFile)` (44개)
  - `_storyboard.html:1120` — 모두 `<video preload="metadata">` 카드로 렌더
  - 18 씬 × 45 = 810개 `<video>` 요소가 동시 헤더 fetch → 브라우저 멈춤
- **사용자 의도**: 씬별로는 그 씬에 배정된 비디오만 보면 됨. 다른 비디오 변경은 드물게만 필요
- **해결**:
  1. **드롭다운 lazy 렌더링** — 페이지 로드 시 `currentVideo`만 렌더. `다른 비디오 N개 ▾` 버튼 클릭 시에만 `otherVideos.forEach(makeCard)` 실행
  2. **카드는 `<video>` 대신 `<img src="_thumb.jpg">`** — `assembly-director`가 이미 `_thumb.jpg`를 만들고 있음. 없으면 🎬 아이콘 fallback
  3. 합치면 페이지 로드 시 18개 video 요소 → 18개 img 요소, 추가 비디오는 클릭 시 1씬만 lazy 생성
- **영향**: 페이지 로드 시 video 헤더 fetch 0개. 브라우저 멈춤 해소
- **난이도**: 쉬움 (lazy 분기 한 군데 + img 교체)

### 6. 🔴 페이지 진입 시 API 164개 동시 발사
- **원인**:
  - `_storyboard.html:529` — `setTimeout(loadAllImageGrids, 500)`이 모든 이미지 씬(64개) 즉시 fetch
  - `sbLoadImageGrid` 씬당 fetch 2개 (`/images/versions/<n>` + `/images/candidates/<n>`) = **64 × 2 = 128**
  - `_storyboard.html:1244` — 모든 비디오 패널(18개) `sbLoadVideoPanel` 즉시 호출 = **18**
  - 합계 **146개** (보고서 164는 +α 포함)
- **해결**: **IntersectionObserver** — 화면에 들어온 씬만 lazy load. 스크롤하면서 순차
  - 보이지 않는 씬은 fetch 자체 안 함
  - rootMargin 200px로 약간 미리 로드해서 스크롤 끊김 방지
  - tab 전환 시 observer disconnect로 메모리 누수 방지
- **영향**: 동시 요청 ~10개 이하로 분산
- **난이도**: 중간 (observer 등록 + 정리 로직 + 한 번 로드한 씬 재호출 방지)

## 작업 순서 (제안)

### Pass 1 — 메인 스레드 멈춤 즉시 해소 (~2시간)
1. **#5 비디오 드롭다운 lazy + 썸네일** (가장 큰 효과)
   - 페이지 로드 시 currentVideo만 렌더 (썸네일 img)
   - "다른 비디오 ▾" 클릭 시 그 씬의 카드만 lazy 생성
   - 결과: 페이지 진입 시 video 헤더 fetch 0개
2. **#6 IntersectionObserver lazy load** (5와 묶어서 — 보이는 씬만 처리)
   - 이미지 그리드 + 비디오 패널 둘 다 IO로 묶음
   - 한 번 로드한 씬은 dataset 플래그로 재호출 방지

이 두 개만 끝내도 사용자 체감 90% 이상 개선.

### Pass 2 — 캐싱과 UI 정리 (~1시간)
3. **#1 mtime 캐시버스터** (네트워크 부하)
4. **#2 후보 이미지 lazy 드롭다운**
5. **#3 + #4 UI 접기/토글 정리**

총 ~3시간 작업.

## 검증

- Chrome DevTools Network 탭: 첫 로드 동시 요청 수
- Performance 탭: Long Tasks 0개 목표
- 시각적: 펩시 또는 유한양행 프로젝트(46씬 / 89씬)로 진입 시 즉시 응답하는지

## 위험 / 주의

- **#5 썸네일 교체** — `_thumb.jpg`가 없는 비디오에 대한 fallback 처리 필수 (없으면 빈 칸)
- **#6 IntersectionObserver** — observer cleanup 누락 시 메모리 누수. 탭 전환 시 observer 해제
- **#3 토글 로직** — 다른 곳에서도 같은 패턴 있을 수 있어, 검색해서 일괄 정리 권장
- **#4 자동 close** — 사용자가 의도적으로 펼쳐둔 경우 닫히면 거슬릴 수 있음. UX 검토 필요

## 다음

`feature/live-doc-snapshot` 브랜치는 리서치 재설계 진행 중이라, 별도 브랜치 `fix/storyboard-perf`에서 진행 권장.
