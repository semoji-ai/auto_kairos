# 이미지 배치 생성 & 캐릭터 라이브러리 설계

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan.

**Goal:** FAL AI 이미지 생성을 Claude CLI 에이전트 방식에서 직접 FAL queue + 폴링 배치 방식으로 전환하고, 캐릭터 이미지를 글로벌 라이브러리에 저장해 프로젝트 간 재활용한다.

**Architecture:** 기존 `image-painter` 에이전트(Claude CLI subprocess)를 새 Python 모듈로 대체. 프롬프트 빌딩 로직(`image_generate.py`)은 그대로 재사용하고, FAL 호출 레이어만 동기 `subscribe()` → 비동기 queue `submit()`+`poll()`로 교체. 캐릭터는 PNG `tEXt` 메타데이터 + 별도 SQLite 인덱스로 관리.

**Tech Stack:** Python 3.12, fal-client SDK (queue API), Pillow (PNG tEXt 청크), SQLite (`~/.auto_agent/characters.db` — 프로젝트 DB와 분리), 기존 image_generate.py 재사용

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
| `auto_agent/data/pipeline.json` | step_8b를 image_batch 모듈로 교체, 기존은 step_8b_legacy 보존 |
| `auto_agent/tools/image_generate.py` | `_build_character_fal_input()`, `_build_scene_fal_input()` 추출 함수 추가 (기존 함수 보존) |
| `auto_agent/orchestrator/runner.py` | `script_map`에 `"image_batch": "modules/image_batch_module.py"` 추가 |

### 글로벌 디렉토리 & DB

```
~/.auto_agent/
├── characters/
│   └── {name}__{style}__{hash8}.png    ← PNG + tEXt 메타데이터
└── characters.db                        ← SQLite 인덱스 (프로젝트 DB와 분리)
```

프로젝트 DB(`auto_agent.db`)와 분리하는 이유: 여러 프로젝트 동시 실행 시 WAL 충돌 방지, 캐릭터 라이브러리가 프로젝트 생명주기와 독립적임.

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
      handle = fal_client.submit(job.endpoint, arguments=job.arguments)
      request_ids.append(handle.request_id)
  return request_ids

poll_all():
  # pending: {request_id: (job, retry_count)}
  pending = {rid: (job, 0) for rid, job in zip(request_ids, jobs)}

  while pending and elapsed < timeout:
      sleep(poll_interval)
      for req_id in list(pending):
          job, retry_count = pending[req_id]
          status = fal_client.status(req_id)

          if status == COMPLETED:
              result = fal_client.result(req_id)
              try:
                  on_done(FalResult(idx=job.idx, success=True, ...))
              except Exception as e:
                  log_warning(f"on_done 콜백 실패 (job {job.idx}): {e}")
                  # 콜백 실패는 저장 실패로 처리 — 해당 job을 failed로 기록, 계속 진행
              del pending[req_id]

          elif status == FAILED:
              if retry_count < max_retries:
                  # 새 request_id로 재제출
                  new_handle = fal_client.submit(job.endpoint, arguments=job.arguments)
                  del pending[req_id]
                  pending[new_handle.request_id] = (job, retry_count + 1)
              else:
                  on_done(FalResult(idx=job.idx, success=False, error=...))
                  del pending[req_id]

  # timeout 초과 잔여 → success=False로 일괄 처리
  for req_id, (job, _) in pending.items():
      on_done(FalResult(idx=job.idx, success=False, error="timeout"))
```

### 나중에 진짜 웹훅으로 전환 시

`submit_batch()`에서 `fal_client.submit(..., webhook_url=WEBHOOK_URL)` 한 줄 추가, `poll_all()` 대신 웹훅 수신 대기로 교체. `FalJob`, `FalResult`, `on_done` 콜백 인터페이스는 동일하게 유지.

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

### SQLite characters 테이블 (`~/.auto_agent/characters.db`)

```sql
CREATE TABLE IF NOT EXISTS characters (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    art_style    TEXT NOT NULL,
    tags         TEXT DEFAULT '',        -- 콤마 구분
    features     TEXT DEFAULT '',
    features_hash TEXT NOT NULL DEFAULT '', -- SHA-8 (features 앞 64자)
    file_path    TEXT NOT NULL UNIQUE,
    source_project TEXT,
    created_at   TEXT NOT NULL
    -- UNIQUE 제약 없음: 동일 이름+스타일이라도 features가 다르면 별도 레코드
);
CREATE INDEX idx_characters_name_style ON characters(name, art_style);
```

`UNIQUE(name, art_style)` 제약을 두지 않는 이유: 같은 인물이 시대별·역할별로 다른 외형을 가질 수 있음(예: "일론 머스크" 젊은 시절 vs. 현재). `features_hash`는 중복 등록 감지 용도로만 사용.

### 매칭 로직

```
search(name, art_style, tags=[]):
  1. name(exact) + art_style(exact) → 후보 전체 조회 (복수 가능)
  2. 후보 없음 → None (신규 생성 필요)
  3. 후보 1개 → 바로 반환
  4. 후보 복수 + tags 없음 → created_at 최신 순 첫 번째 반환
  5. 후보 복수 + tags 있음 → tags 포함도 점수로 정렬, 최고 매칭 반환
```

### API

```python
class CharacterLibrary:
    LIBRARY_DIR = Path.home() / ".auto_agent" / "characters"
    DB_PATH     = Path.home() / ".auto_agent" / "characters.db"

    def search(self, name: str, art_style: str, tags: list[str] = []) -> CharacterRecord | None
    def register(self, png_path: Path, metadata: dict) -> CharacterRecord
        # 중복 체크: features_hash 동일 레코드 있으면 skip
        # PNG tEXt embed → LIBRARY_DIR에 파일 복사 → DB INSERT
    def copy_to_project(self, record: CharacterRecord, project_dir: Path) -> Path
        # 라이브러리 → 프로젝트 characters/ 디렉토리로 복사
    def rebuild_index(self) -> int
        # LIBRARY_DIR 스캔 → PNG tEXt 읽어 DB 재구성
        # tEXt 청크 없는 파일은 건너뜀 (경고 로그만)
        # 복구된 레코드 수 반환
```

---

## 4. image_generate.py 추출 함수

기존 `generate_character()` / `generate_scene()` / `generate_scene_flat()`에서 FAL 호출 직전까지의 로직을 다음 두 함수로 추출. **기존 함수는 그대로 보존** (레거시 에이전트 경로에서 계속 사용).

```python
def _build_character_fal_input(char: dict, art_style: dict) -> tuple[str, dict]:
    """캐릭터 FAL 입력 빌드. (endpoint, arguments) 반환."""
    # 기존 generate_character() 내 프롬프트 빌딩 + IP-Adapter 이미지 구성 로직
    # fal_client.subscribe() 호출 직전에서 중단
    return endpoint, fal_input

def _build_scene_fal_input(scene: dict, project_dir: Path, char_paths: dict) -> tuple[str, dict]:
    """씬 FAL 입력 빌드. (endpoint, arguments) 반환.
    char_paths: {char_id: Path | None}  — None이면 캐릭터 참조 없이 생성
    """
    # generate_scene() 또는 generate_scene_flat() 내 로직
    # viz_background 씬이면 generate_viz_background() 로직 사용
    return endpoint, fal_input

# image_generate.py의 _save_fal_result()는 image_batch_module.py에서 직접 import 재사용
from auto_agent.tools.image_generate import _save_fal_result
```

---

## 5. image_batch_module.py

### 전제: character_plan.json 생성 주체

`character_plan.json`은 기존 pipeline의 `character-planner` 에이전트(step_6d)가 생성함. `image_batch_module`은 이 파일을 읽기만 함. step_8b의 `input` 목록에 `character_plan.json` 추가.

### 실행 흐름

```python
def run(project_dir: Path, config: dict) -> dict:

    ## Phase 1: 캐릭터 배치
    character_plan = json.loads((project_dir / "character_plan.json").read_text())
    art_style      = json.loads((project_dir / "art_style.json").read_text())

    reused, to_generate = [], []
    for char in character_plan.get("characters", []):
        tags = char.get("tags", [])
        record = library.search(char["name"], art_style["id"], tags)
        if record:
            dest = library.copy_to_project(record, project_dir)
            # char_paths[char_id] = dest
            reused.append(char)
        else:
            endpoint, arguments = _build_character_fal_input(char, art_style)
            to_generate.append((char, FalJob(idx=len(to_generate), endpoint=endpoint, arguments=arguments)))

    char_paths = {char["id"]: None for char in character_plan.get("characters", [])}

    if to_generate:
        jobs = [job for _, job in to_generate]
        request_ids = fal_queue.submit_batch(jobs)

        def on_char_done(result: FalResult):
            char, _ = to_generate[result.idx]
            if result.success:
                save_path = _save_fal_result(result.images, project_dir / "characters" / ...)
                library.register(save_path, {
                    "character_name": char["name"],
                    "art_style": art_style["id"],
                    "tags": ",".join(char.get("tags", [])),
                    "features": char.get("description", ""),
                    "source_project": project_dir.name,
                })
                char_paths[char["id"]] = save_path

        fal_queue.poll_all(jobs, request_ids, on_done=on_char_done)

    notify(f"캐릭터 완료: 재사용 {len(reused)}개, 신규 생성 {len(to_generate)}개")

    ## Phase 2: 씬 배치
    scene_specs = json.loads((project_dir / "scene_specs.json").read_text())

    scene_jobs = []
    for scene in scene_specs.get("scenes", []):
        if scene.get("imageAsset", {}).get("source") != "generate":
            continue
        # 씬에 등장하는 캐릭터 경로 주입 (실패한 캐릭터는 None → 캐릭터 참조 없이 생성)
        scene_char_paths = {
            cid: char_paths.get(cid)
            for cid in scene.get("characters", [])
        }
        endpoint, arguments = _build_scene_fal_input(scene, project_dir, scene_char_paths)
        scene_jobs.append((scene, FalJob(idx=len(scene_jobs), endpoint=endpoint, arguments=arguments)))

    if scene_jobs:
        jobs = [job for _, job in scene_jobs]
        request_ids = fal_queue.submit_batch(jobs)

        def on_scene_done(result: FalResult):
            scene, _ = scene_jobs[result.idx]
            if result.success:
                save_path = _save_fal_result(result.images, project_dir / "images" / ...)
                image_assets.add_version(scene["sceneNumber"], save_path, source="generate")

        fal_queue.poll_all(jobs, request_ids, on_done=on_scene_done)

    notify(f"씬 이미지 완료: {success_count}개 성공, {fail_count}개 실패")
    return summary
```

---

## 6. pipeline.json 변경

```json
// 기존 step_8b → step_8b_legacy (보존, skip)
{
  "id": "step_8b_legacy",
  "name": "image_asset_sourcing_legacy",
  "agent": "image-painter",
  "skip": true
}

// 신규 step_8b
{
  "id": "step_8b",
  "name": "image_asset_sourcing",
  "type": "module",
  "module": "image_batch",
  "description": "이미지 배치 생성 — 캐릭터 라이브러리 조회 → FAL queue 배치 제출 → 폴링",
  "input": [
    "character_plan.json",
    "scene_specs.json",
    "art_style.json"
  ],
  "output": ["images/image_assets.json", "characters/"]
}
```

## 7. runner.py 변경

```python
# _run_module_step()의 script_map에 추가
script_map = {
    ...
    "image_batch": "modules/image_batch_module.py",
}
```

---

## 8. 에러 처리

| 상황 | 동작 |
|------|------|
| 개별 씬 이미지 실패 (max_retries 초과) | 실패 씬 기록, 나머지 계속 진행 |
| 캐릭터 생성 실패 | char_paths[id]=None → 해당 씬을 캐릭터 참조 없이 생성 |
| on_done 콜백 예외 (저장/DB 실패) | 경고 로그 + 해당 job failed 처리, 폴링 루프 계속 |
| FAILED 재제출 시 새 request_id로 pending 교체 | retry_count 누적 추적, max_retries 초과 시 중단 |
| 전체 timeout 초과 | 완료된 이미지만 저장, 미완료 목록 경고 알림 |
| FAL API 키 없음 | 즉시 실패 (재시도 없음) |
| 라이브러리/DB 없음 | 자동 생성 (mkdir + schema 초기화) |
| DB 손실 | `rebuild_index()` 자동 실행 후 재시도 |
| PNG tEXt 없는 파일 (rebuild_index) | 건너뜀 + 경고 로그 |

---

## 9. 테스트 계획

1. `test_fal_queue.py`
   - mock fal_client로 submit_batch / poll_all 단위 테스트
   - FAILED 재제출 시 새 request_id로 교체되는지 검증
   - on_done 콜백 예외 발생 시 폴링 루프가 계속되는지 검증
   - timeout 초과 시 미완료 job이 success=False로 처리되는지 검증

2. `test_character_library.py`
   - PNG tEXt embed / read 왕복 검증
   - 동일 name+style, 다른 features로 register() 2회 → 별도 레코드 생성 확인
   - search() 복수 후보에서 tags 점수로 올바른 레코드 반환 확인
   - rebuild_index(): tEXt 없는 PNG 있어도 오류 없이 나머지 처리
   - rebuild_index() 후 search()가 올바른 결과 반환

3. `test_image_batch_module.py`
   - 캐릭터 재사용 경로 (library hit → copy, 생성 스킵)
   - 신규 생성 경로 (library miss → FAL 제출 → 저장 → register)
   - 캐릭터 실패 시 씬이 char_paths=None으로 생성되는지 확인

4. 통합 테스트 — 실제 프로젝트로 배치 모듈 실행, image_assets.json 검증

---

## 10. 마이그레이션 & 롤백

- **기존 에이전트 보존**: `step_8b_legacy` + `skip: true` → 코드 변경 없이 롤백 가능
- **롤백**: pipeline.json에서 step_8b ↔ step_8b_legacy id 교체만으로 복구
- **기존 캐릭터 흡수**: 기존 프로젝트의 `characters/` 디렉토리에서 `library.register()` 호출하는 one-time 마이그레이션 스크립트 제공 (`scripts/migrate_characters.py`)
- **점진 전환**: 특정 프로젝트에서만 배치 모듈 테스트 → 검증 후 step_8b_legacy 삭제
