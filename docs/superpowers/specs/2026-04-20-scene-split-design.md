# 씬 분할 기능 설계

작성일: 2026-04-20

---

## 개요

스토리보드 씬 상세 패널에서 하나의 씬을 두 개로 나누는 편집 기능.
분할 후 양쪽 씬에 대해 TTS 재생성 + AI 씬 재분석을 자동 실행한다.

---

## 핵심 설계 결정

### sceneId 도입 (레거시 호환)

현재 `sceneNumber`가 순서와 식별자를 겸하고 있어 씬 삽입 시 연동 파일이 밀리는 문제가 있다.
`sceneId` (UUID)를 도입해 식별자를 분리한다.

- **sceneId**: 씬의 고유 식별자 — 변하지 않음
- **sceneNumber**: 재생 순서 — 삽입/분할 시 재번호 가능

**레거시 호환:** sceneId가 없는 기존 프로젝트는 sceneNumber 기반 폴백으로 동작.

---

## sceneId 스키마

### scene_specs.json

```json
{
  "sceneId": "a3f9b2c1-...",
  "sceneNumber": 5,
  "narration": "...",
  ...
}
```

### image_assets.json (sceneId 기반)

```json
{
  "scenes": [
    {
      "sceneId": "a3f9b2c1-...",
      "sceneNumber": 5,
      "images": [
        { "file": "generated/scene_a3f9b2c1_gen_01.png", "type": "generate", "selected": true }
      ]
    }
  ]
}
```

레거시 폴백: sceneId 없는 항목은 sceneNumber로 매칭.

### 파일명 규칙

| 파일 종류 | sceneId 있을 때 | 레거시 폴백 |
|-----------|----------------|------------|
| 오디오 | `audio/scene_{sceneId}.mp3` | `audio/scene_005.mp3` |
| 자막 | `subtitles/scene_{sceneId}.json` | `subtitles/scene_005.json` |
| 생성 이미지 | `images/generated/scene_{sceneId}_gen_01.png` | `scene_005_gen_01.png` |
| 검색 이미지 | `images/search/scene_{sceneId}_search_01.jpg` | `scene_005_search_01.jpg` |

---

## UI

### 진입점

스토리보드 씬 상세 패널(`_storyboard_scene.html`)에 "✂️ 씬 분할" 버튼 추가.

### 분할 UI 흐름

버튼 클릭 시 씬 상세 패널 내에 분할 편집기 표시:

```
┌─────────────────────────────────┐
│  앞 씬 나레이션 (textarea)        │
│  (원본 앞 절반 자동 채움)          │
├──────────── 분할선 ──────────────┤
│  뒷 씬 나레이션 (textarea)        │
│  (원본 뒷 절반 자동 채움)          │
└─────────────────────────────────┘
         [취소]  [분할 실행]
```

- 초기값: 원본 나레이션을 문장 단위로 절반 분할
- 사용자가 두 textarea 모두 자유 편집 가능
- 분할 실행 후: 두 씬 카드에 스피너 표시 (백그라운드 처리 중)

---

## 백엔드

### API

```
POST /api/p/{slug}/editor/scenes/{num}/split
Body: { "narration_a": "...", "narration_b": "..." }
Response: { "status": "splitting", "scene_a": N, "scene_b": N+1 }
```

### 1단계 — 즉시 처리 (동기)

1. `scene_specs.json` 백업 (`scene_specs.bak.{timestamp}.json`)
2. 원본 씬(num) narration → `narration_a`로 교체, sceneId 유지
3. 새 씬 객체 생성: narration_b, 신규 UUID sceneId, sceneNumber = num+1, 이미지 없음
4. num+1 이후 모든 씬 sceneNumber +1
5. `image_assets.json` / `video_assets.json` sceneNumber 필드 +1 (sceneId 기반이면 불필요하지만 sceneNumber 필드 동기화)
6. 레거시 파일명 기반 프로젝트: 오디오·자막·이미지 파일 rename (num+1 이후 역순으로)
7. `scene_specs.json` 저장
8. 매니페스트 재빌드
9. 백그라운드 태스크 시작 → 즉시 응답 반환

### 2단계 — 백그라운드 처리 (비동기)

두 씬(num, num+1) 병렬 실행:

**TTS 재생성 (각 씬):**
- 나레이션 전처리 (숫자 변환 등)
- ElevenLabs TTS 생성
- Whisper 자막 동기화
- `audio/scene_{sceneId}.mp3`, `subtitles/scene_{sceneId}.json` 저장

**씬 재분석 (각 씬):**
- script-director 에이전트로 양쪽 씬 재연출
- title, concept, layout, mood, imageAsset.prompt 등 전체 재생성

완료 후:
- 매니페스트 재빌드
- `storyboard:invalidate` 이벤트 발생 → 스토리보드 자동 갱신

**실패 처리:** TTS 또는 씬 분석 실패 시 해당 씬에 에러 배지 표시. 씬 구조(1단계)는 이미 저장된 상태이므로 롤백하지 않음. 사용자가 개별 재시도 가능.

### 파일 rename 로직 (레거시 프로젝트)

삽입 지점(num) 이후 씬들을 **역순**으로 rename해 충돌 방지:

```python
for n in range(max_scene, num, -1):
    rename(f"audio/scene_{n:03d}.mp3", f"audio/scene_{n+1:03d}.mp3")
    rename(f"subtitles/scene_{n:03d}.json", f"subtitles/scene_{n+1:03d}.json")
    # images: generated/search glob으로 처리
```

---

## 마이그레이션 스크립트

선택 실행 (`python3.12 -m auto_agent.scripts.migrate_scene_ids --project <slug>`):

1. scene_specs.json 각 씬에 UUID sceneId 부여
2. image_assets.json 항목에 sceneId 추가
3. video_assets.json 항목에 sceneId 추가
4. 오디오·자막 파일명은 그대로 유지 (레거시 폴백으로 동작)

---

## 영향 범위

| 컴포넌트 | 변경 내용 |
|---------|---------|
| `scene_specs.json` 스키마 | `sceneId` 필드 추가 |
| `image_assets.json` 스키마 | `sceneId` 필드 추가, 폴백 유지 |
| `video_assets.json` 스키마 | `sceneId` 필드 추가, 폴백 유지 |
| `build_manifest.py` | sceneId 우선 조회 + sceneNumber 폴백 |
| `app.py` | `/split` 엔드포인트, 백그라운드 태스크 |
| `_storyboard_scene.html` | 분할 UI |
| `auto_agent/scripts/migrate_scene_ids.py` | 신규 마이그레이션 스크립트 |

---

## 미구현 범위 (이번 스펙 외)

- 씬 순서 변경 (drag & drop)
- 씬 병합 (merge)
- 씬 삭제

---

## 성공 기준

1. 씬 분할 후 대시보드 즉시 갱신 (1단계 완료 기준 3초 이내)
2. TTS + 씬 분석 완료 후 스토리보드 자동 갱신
3. 기존 레거시 프로젝트 정상 동작 유지
4. sceneId 없는 씬도 분할 가능
