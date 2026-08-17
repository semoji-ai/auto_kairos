# 모션 학습 파이프라인 설계 (수집→분석→기법화→검증→개선→평가)

> 작성: 2026-06-16 · 범위: 전체 비전 + Phase A(수집·분석·기법화) 상세. B/C 개요.

## 1. 목적

퀄리티 좋은 모션그래픽 레퍼런스 영상을 수집·분석해 **모션 프리셋 라이브러리를 자동 성장**시키고, 만든 결과물을 렌더·대조로 검증한다. gemini 동영상이해 + aerender 헤드리스 렌더 + ffmpeg + gemini 멀티모달 대조가 모두 가용(환경 확인됨).

기존 자산: 모션 라이브러리(`data/artstyle/motion/`, P1 7프리셋), 빌더 `build_from_json.jsx`.

## 2. 전체 흐름 (단계별 체크포인트)

```
① 수집   큐레이션 URL → yt-dlp → refs/{slug}.mp4 + meta
② 분석   gemini 동영상이해 → 컷·프리셋 매핑 + 신규 프리셋 후보 제안
③ 기법화  신규 후보 → [체크포인트: 검토] → motion_presets.json 확장
④ 빌드   motion.json → build_from_json.jsx
⑤ 검증   aerender 렌더 → ffmpeg 프레임 → gemini 원본↔렌더 대조 → 충실도 점수+차이
⑥ 개선   차이 기반 프리셋/빌더 보정 → 재빌드·재렌더
⑦ 평가   점수 기준 통과/재시도 [체크포인트]
⑧ 완료   라이브러리 확정 + 학습 노트
```

**Phase 분해**: A(①②③) / B(④⑤⑦) / C(⑥ 개선 루프). 각 독립 동작.

## 3. Phase A — 수집·분석·기법화 (이 스펙의 구현 대상)

### 3.1 모듈 (`scripts/motion_learn/`)
- `collect.py` — yt-dlp로 큐레이션 URL 다운 + 메타 기록
- `analyze.py` — gemini 동영상이해 → motion.json(컷·프리셋) + 신규 프리셋 후보
- `merge_presets.py` — 후보를 라이브러리에 머지(검토 게이트)
- `state.py` — 레퍼런스별 진행 상태(수집/분석/검토)

### 3.2 수집 (`collect.py`)
- 입력: URL 목록(`refs/urls.txt` 한 줄 1 URL, 또는 함수 인자)
- 동작: 각 URL → `yt-dlp -f "bv*[height<=1080]+ba/b[height<=1080]" -o refs/{slug}.mp4` (slug=영상 id 해시). 메타(`refs/{slug}.meta.json`: url/title/duration/width/height).
- 무삭제·멱등: 이미 받은 slug는 스킵.
- 함수: `collect(urls: list[str], refs_dir: Path) -> list[dict]` (각 {slug, path, title, dur})

### 3.3 분석 (`analyze.py`)
- gemini File API 업로드 → 프롬프트에 **기존 프리셋 카탈로그**(motion_presets.json 키+설명) 주입:
  - "영상 모션을 컷·레이어로 분해. 모션은 가능한 한 기존 프리셋명으로 매핑.
     기존으로 표현 안 되는 모션은 `new_presets`에 후보로 제안: {name(snake_case), props, ease, params, why(왜 기존으로 안 되는지)}."
- 출력 JSON: `{ "cuts": [...빌더 스키마...], "new_presets": [...후보...] }`
- 저장: `refs/{slug}/motion.json`(컷), `refs/{slug}/new_presets.json`(후보)
- 함수: `analyze(slug, refs_dir, lib_dir) -> dict`. gemini 모델 폴백(2.5-flash→2.0-flash→2.5-pro), 파일 직접 저장(파이프 잘림 방지), JSON 검증.

### 3.4 기법화 검토 (`merge_presets.py`)
- 후보(`new_presets.json`)를 **체크포인트**: 사람이 검토. 승인 목록을 `motion_presets.json`에 머지(중복 이름 스킵, 무삭제).
- 함수: `list_candidates(slug)` → 후보 출력; `merge(slug, approved_names: list[str])` → 라이브러리 추가.
- 빌더가 새 프리셋을 적용하려면 P1 빌더의 `applyPreset`이 그 프리셋을 처리해야 함 — **신규 프리셋은 기존 props(opacity/scale/position/rotationY/trimEnd/textOffset) 조합으로 표현**되도록 후보 스키마 제약(빌더 코드 수정 없이 데이터로 동작). props가 새 종류면 "빌더 확장 필요" 플래그.

### 3.5 상태 (`state.py`)
- `refs/{slug}/state.json`: `{stage: "collected"|"analyzed"|"reviewed", ...}`. 멱등 진행.

### 3.6 단일 소스 / 테스트
- 라이브러리는 `data/artstyle/motion/`(P1). collect/analyze는 `refs/`에 산출.
- 테스트: slug 생성·멱등, meta 파싱, merge 로직(중복 스킵·무삭제·props 제약 플래그), 후보 스키마 검증. yt-dlp/gemini는 외부라 모킹/구문 검증.

## 4. Phase B — 검증·평가 (개요, 별도 스펙)

- `verify.py`: aerender로 컴프 렌더(`aerender -project ... -comp TYL_Final -output ...mp4`) → ffmpeg 프레임 → gemini가 원본 프레임과 대조 → 충실도 점수(0~100)+차이 목록.
- 평가 게이트: 점수 임계(예 75) 미만이면 Phase C로.

## 5. Phase C — 개선 루프 (개요, 별도 스펙)

- 차이 목록 → 프리셋 파라미터/빌더 보정 → 재빌드·재렌더·재대조. K회 또는 점수 수렴까지. 통과 시 완료.

## 6. 범위 밖 (YAGNI, Phase A)

- aerender 렌더/대조(B), 개선 루프(C)
- 검색어 자동 수집(큐레이션 URL만)
- 신규 props 종류가 필요한 프리셋의 빌더 자동 확장(플래그만 — 빌더 수정은 사람)

## 7. 법적/윤리

- yt-dlp 다운로드는 **내부 학습·분석 목적**(로컬). 산출물(라이브러리)은 추상 모션 파라미터이지 원본 복제 아님. 레퍼런스 영상은 refs/(로컬, git 비추적).
