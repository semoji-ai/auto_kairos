# 이미지 배치 생성 & 캐릭터 라이브러리 설계

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.

**Goal:** FAL AI 이미지 생성을 Claude CLI 에이전트 방식에서 직접 FAL queue + 폴링 배치 방식으로 전환하고, 캐릭터 이미지를 글로벌 라이브러리에 저장해 프로젝트 간 재활용한다.

**Architecture:** 기존 `image-painter` 에이전트(Claude CLI subprocess)를 새 Python 모듈로 대체. 프롬프트 빌딩 로직(`image_generate.py`)은 그대로 재사용하고, FAL 호출 레이어만 동기 `subscribe()` → 비동기 queue `submit()`+`poll()`로 교체. 캐릭터는 PNG `tEXt` 메타데이터 + SQLite 인덱스로 관리.

**Tech Stack:** Python 3.12, fal-client SDK (queue API), Pillow (PNG tEXt 청크), SQLite (auto_agent.db), 기존 image_generate.py 재사용

---

## 1. 파일 구조

### 신규 파일

| 파일 | 역할 |
|------|------|
| `auto_agent/tools/fal_queue.py` | FAL queue 클라이언트 — submit_batch / poll_all |
| `auto_agent/tools/character_library.py` | 캐릭터 라이브러리 — 검색/저장/재건 |
| `auto_agent/modules/image_batch_module.py` | 파이프라인 모듈 — 캐릭터→씬 배치 오케스트레이션 |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `auto_agent/data/pipeline.json` | step_8b를 image_batch_module로 교체, 기존은 step_8b_legacy 보존 |
| `auto_agent/db/schema.py` | characters 테이블 추가 |
| `auto_agent/orchestrator/runner.py` | image_batch_module 모듈 라우팅 추가 |

### 글로벌 디렉토리

```
~/.auto_agent/characters/
    {name}__{style}__{hash8}.png    ← PNG + tEXt 메타데이터
```

---

## 2. fal_queue.py

### 인터페이스

```python
@dataclass
class FalJob:
    idx: int            # 호출자 식별용 인덱스
    endpoint: str       # "fal-ai/nano-banana-2" 또는 "/edit"
    arguments: dict     # FAL API 입력

@dataclass
class FalResult:
    idx: int
    success: bool
    images: list[dict]  # [{"url": ..., "width": ..., "height": ...}]
    error: str | None

def submit_batch(jobs: list[FalJob]) -> list[str]:
    """모든 job을 FAL queue에 제출. request_id 목록 반환."""

def poll_all(
    jobs: list[FalJob],
    request_ids: list[str],
    on_done: Callable[[FalResult], None],
    poll_interval: float = 2.0,
    timeout: float = 3600.0,
    max_retries: int = 2,
) -> list[FalResult]:
    """모든 request_id 폴링. 완료마다 on_done 콜백 호출."""
```

### 동작 흐름

```
submit_batch():
  for job in jobs:
      request_id = fal_client.submit(job.endpoint, arguments=job.arguments).request_id
  return request_ids

poll_all():
  pending = {request_id: job for ...}
  while pending and not timeout:
      sleep(poll_interval)
      for req_id in list(pending):
          status = fal_client.status(req_id)
          if status == COMPLETED:
              result = fal_client.result(req_id)
              on_done(FalResult(success=True, ...))
              del pending[req_id]
          elif status == FAILED:
              if retry_count < max_retries:
                  # 재제출
              else:
                  on_done(FalResult(success=False, ...))
                  del pending[req_id]
  # timeout 초과 미완료 → success=False로 처리
```

### 나중에 진짜 웹훅으로 전환 시

`submit_batch()`에서 `fal_client.submit(..., webhook_url=WEBHOOK_URL)` 한 줄 추가, `poll_all()` 대신 웹훅 수신 대기로 교체. 인터페이스(`FalJob`, `FalResult`, `on_done` 콜백)는 동일.

---

## 3. character_library.py

### PNG 메타데이터 (tEXt 청크)

```
character_name   = "일론 머스크"
art_style        = "quirky_cartoon"
tags             = "기업인,테슬라,실존인물"
features         = "짧은 머리, 정장, 자신감 있는 표정"
source_project   = "gpt54_ai"
created_at       = "2026-03-21T17:00:00"
```

Pillow `PngImagePlugin.PngInfo`로 embed, 읽을 때 `Image.open().text` 딕셔너리로 파싱.

### SQLite characters 테이블

```sql
CREATE TABLE IF NOT EXISTS characters (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    art_style   TEXT NOT NULL,
    tags        TEXT DEFAULT '',       -- 콤마 구분
    features    TEXT DEFAULT '',
    file_path   TEXT NOT NULL UNIQUE,
    source_project TEXT,
    created_at  TEXT NOT NULL,
    UNIQUE(name, art_style)            -- 이름+스타일 조합 고유
);
CREATE INDEX idx_characters_name_style ON characters(name, art_style);
```

### 매칭 로직

```
search(name, art_style, tags=[]):
  1. name(exact) + art_style(exact) → 후보 조회
  2. 후보 없음 → None (신규 생성 필요)
  3. 후보 있음 + tags 없음 → 첫 번째 반환
  4. 후보 있음 + tags 있음 → tags 포함도로 정렬, 최고 매칭 반환
```

### API

```python
class CharacterLibrary:
    LIBRARY_DIR = Path.home() / ".auto_agent" / "characters"

    def search(self, name: str, art_style: str, tags: list[str] = []) -> CharacterRecord | None
    def register(self, png_path: Path, metadata: dict) -> CharacterRecord
        # PNG tEXt embed + DB INSERT OR REPLACE + 라이브러리에 파일 복사
    def copy_to_project(self, record: CharacterRecord, project_dir: Path) -> Path
        # 라이브러리 → 프로젝트 images/ 디렉토리로 복사
    def rebuild_index(self) -> int
        # LIBRARY_DIR 스캔 → PNG tEXt 읽어 DB 재구성, 복구된 레코드 수 반환
```

---

## 4. image_batch_module.py

### 실행 흐름

```
run(project_dir, config):

  ## Phase 1: 캐릭터 배치
  character_plan = load(project_dir / "character_plan.json")

  reused, to_generate = [], []
  for char in character_plan.characters:
      record = library.search(char.name, char.art_style, char.tags)
      if record:
          library.copy_to_project(record, project_dir)
          reused.append(char)
      else:
          job = build_character_job(char)   # image_generate.py 재사용
          to_generate.append((char, job))

  if to_generate:
      request_ids = fal_queue.submit_batch([job for _, job in to_generate])
      results = fal_queue.poll_all(
          jobs, request_ids,
          on_done=lambda r: save_character(r) + library.register(r)
      )

  notify("캐릭터 완료: 재사용 {N}개, 신규 생성 {M}개, 실패 {K}개")

  ## Phase 2: 씬 배치
  scene_plan = load(project_dir / "scene_plan.json")

  scene_jobs = []
  for scene in scene_plan.scenes:
      if scene.source != "generate":
          continue
      # 캐릭터 참조 이미지 주입 (Phase 1 결과 사용)
      job = build_scene_job(scene, project_dir)   # image_generate.py 재사용
      scene_jobs.append((scene, job))

  request_ids = fal_queue.submit_batch([job for _, job in scene_jobs])
  results = fal_queue.poll_all(
      scene_jobs, request_ids,
      on_done=lambda r: image_assets.add_version(r)
  )

  notify("씬 이미지 완료: {N}개 성공, {K}개 실패")

  return summary
```

### image_generate.py 재사용 포인트

- `_build_character_fal_input(char) -> (endpoint, arguments)` — 기존 `generate_character()` 에서 FAL 호출 직전까지의 로직 추출
- `_build_scene_fal_input(scene, project_dir) -> (endpoint, arguments)` — 기존 `generate_scene()` / `generate_scene_flat()` 에서 동일하게 추출

기존 함수들은 **그대로 보존** (레거시 에이전트 경로에서 계속 사용).

---

## 5. pipeline.json 변경

```json
// 기존 step_8b → step_8b_legacy (보존)
{
  "id": "step_8b_legacy",
  "name": "image_asset_sourcing_legacy",
  "agent": "image-painter",
  "skip": true,            // 기본 비활성화
  ...
}

// 신규 step_8b (교체)
{
  "id": "step_8b",
  "name": "image_asset_sourcing",
  "type": "module",
  "module": "image_batch",
  "description": "이미지 배치 생성 — 캐릭터 라이브러리 조회 → FAL queue 배치 제출 → 폴링",
  "input": ["character_plan.json", "scene_plan.json", "scene_specs.json", "art_style.json"],
  "output": ["images/image_assets.json", "characters/"]
}
```

---

## 6. 에러 처리

| 상황 | 동작 |
|------|------|
| 개별 씬 이미지 실패 (max_retries 초과) | 실패 씬 기록, 나머지 계속 진행 |
| 캐릭터 생성 실패 | 해당 캐릭터 참조하는 씬도 캐릭터 없이 생성 |
| 전체 timeout 초과 | 완료된 이미지만 저장, 미완료 목록 경고 알림 |
| FAL API 키 없음 | 즉시 실패 (재시도 없음) |
| 라이브러리 디렉토리 없음 | 자동 생성 |
| DB 손실 | `rebuild_index()` 자동 실행 후 재시도 |

---

## 7. 테스트 계획

1. `test_fal_queue.py` — mock fal_client로 submit_batch / poll_all 단위 테스트
2. `test_character_library.py` — PNG tEXt embed/read, DB search/register, rebuild_index
3. `test_image_batch_module.py` — 캐릭터 재사용 경로 / 신규 생성 경로 / 실패 처리
4. 통합 테스트 — 실제 프로젝트로 배치 모듈 실행, 결과 image_assets.json 검증

---

## 8. 마이그레이션 & 롤백

- **기존 에이전트 보존**: `step_8b_legacy` + `skip: true` 플래그로 비활성화
- **롤백**: pipeline.json에서 step_8b를 legacy로 교체 (코드 변경 불필요)
- **점진 전환**: 특정 프로젝트에서만 배치 모듈 사용 → 검증 후 전체 전환
